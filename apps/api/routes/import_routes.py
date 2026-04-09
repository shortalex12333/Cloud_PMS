"""
Import Pipeline Routes
======================
API endpoints for the PMS onboarding import pipeline.

Endpoints:
- POST /api/import/upload           — Upload files, create session, run detection
- GET  /api/import/session/{id}     — Get session state
- POST /api/import/session/{id}/confirm-mapping  — Save human-confirmed column map
- POST /api/import/session/{id}/dry-run          — Run preview against staging
- POST /api/import/session/{id}/commit           — Execute real import
- POST /api/import/session/{id}/rollback         — Reverse import within 48h

Auth: JWT with scope="import" from registration portal, verified against MASTER secret.
Dev bypass: X-Import-Dev-Token header with yacht_id UUID (requires IMPORT_DEV_MODE=true).
"""

import os
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Header
from fastapi.responses import JSONResponse

from parsers.csv_parser import parse_csv
from parsers.xlsx_parser import parse_xlsx, parse_xls
from parsers.sql_parser import parse_sql
from parsers.zip_handler import parse_zip
from parsers.base_parser import ParseResult
from mappers.column_matcher import match_columns
from services.import_service import dry_run_domain, commit_domain, rollback_domain

logger = logging.getLogger("import.routes")

router = APIRouter(prefix="/api/import", tags=["import"])

# Dev mode bypass for local testing
IMPORT_DEV_MODE = os.getenv("IMPORT_DEV_MODE", "false").lower() == "true"

# Import token verification (separate from Supabase auth)
IMPORT_JWT_SECRET = os.getenv("IMPORT_JWT_SECRET", "")

# Supabase client — use the shared client from integrations/supabase.py
def get_tenant_client():
    """Get the shared Supabase client for tenant DB (service role)."""
    from integrations.supabase import get_supabase_client
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Tenant Supabase client not available")
    return client


def resolve_auth(request: Request, x_import_dev_token: Optional[str] = Header(None)) -> dict:
    """
    Resolve yacht_id and email from auth.
    Production: JWT Bearer token verified against MASTER secret.
    Dev mode: X-Import-Dev-Token header with yacht_id UUID.
    """
    # Dev bypass
    if IMPORT_DEV_MODE and x_import_dev_token:
        logger.info(f"[Import] Dev mode auth bypass: yacht_id={x_import_dev_token}")
        return {"yacht_id": x_import_dev_token, "email": "dev@celeste7.ai"}

    # Production: extract Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    # Verify with IMPORT_JWT_SECRET (dedicated import signing key)
    if IMPORT_JWT_SECRET:
        try:
            import jwt as pyjwt
            payload = pyjwt.decode(
                token,
                IMPORT_JWT_SECRET,
                algorithms=["HS256"],
                audience="celeste-import",
                options={"verify_exp": True},
            )
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Import token expired. Please re-authenticate.")
        except pyjwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except pyjwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid import token: {str(e)}")
    else:
        # Fallback: verify with Supabase JWT secrets (legacy or dev)
        try:
            from middleware.auth import decode_jwt
            payload = decode_jwt(token)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

    # Validate scope
    if payload.get("scope") != "import" and not IMPORT_DEV_MODE:
        raise HTTPException(status_code=403, detail="Token does not have import scope")

    yacht_id = payload.get("yacht_id")
    email = payload.get("email") or payload.get("sub")

    if not yacht_id:
        raise HTTPException(status_code=403, detail="Token missing yacht_id claim")

    return {"yacht_id": yacht_id, "email": email}


# CelesteOS column vocabulary — user-mappable fields per domain
# =============================================================================
# CelesteOS column vocabulary — verified against REAL tenant DB (2026-04-01)
# Includes required fields (NOT NULL constraints) and enum-typed fields
# =============================================================================
CELESTE_VOCABULARY = {
    # VERIFIED against real tenant DB (2026-04-06)
    "equipment": {
        "mappable": [
            "name", "description", "code", "manufacturer", "model", "serial_number",
            "location", "criticality", "system_type", "status", "running_hours",
            "installed_date",
        ],
        "auto_set": [
            "id", "yacht_id", "parent_id", "created_at", "updated_at", "metadata",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["name"],
        "enums": {},
    },
    "work_orders": {
        "mappable": [
            "title", "description", "status", "priority", "type",
            "due_date", "completed_at", "completion_notes",
            "source_assigned_to", "source_created_by",
        ],
        "auto_set": [
            "id", "yacht_id", "wo_number", "created_by", "created_at", "updated_at",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["title", "type", "priority", "status"],
        "enums": {
            "status": ["planned", "in_progress", "completed", "deferred", "cancelled", "closed"],
            "priority": ["routine", "important", "critical", "emergency"],
            "type": ["scheduled", "corrective", "unplanned", "preventive"],
        },
    },
    "faults": {
        "mappable": [
            "title", "description", "severity", "status", "fault_code",
            "detected_at", "resolved_at", "resolution_notes",
            "equipment_ref",  # virtual — resolved to equipment_id FK during commit
            "source_reported_by", "source_resolved_by",
        ],
        "auto_set": [
            "id", "yacht_id", "equipment_id", "created_at", "updated_at", "metadata",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["title", "severity"],
        "enums": {
            "severity": ["low", "medium", "high", "critical"],
        },
        "notes": "equipment_id is NOT NULL — map a source column to 'equipment_ref' (equipment name/code) for FK resolution",
    },
    "parts": {
        "mappable": [
            "name", "description", "part_number", "category", "manufacturer",
            "unit", "quantity_on_hand", "minimum_quantity", "location",
            "is_critical",
        ],
        "auto_set": [
            "id", "yacht_id", "created_at", "updated_at", "metadata",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["name", "quantity_on_hand"],
        "enums": {},
        "type_hints": {"quantity_on_hand": "integer", "minimum_quantity": "integer"},
    },
    "vessel_certificates": {
        "mappable": [
            "certificate_type", "certificate_name", "certificate_number",
            "issuing_authority", "issue_date", "expiry_date",
            "last_survey_date", "next_survey_due", "status",
        ],
        "auto_set": [
            "id", "yacht_id", "created_at",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["certificate_type", "certificate_name", "issuing_authority"],
        "enums": {},
    },
    "crew_certificates": {
        "mappable": [
            "person_name", "certificate_type", "certificate_number",
            "issuing_authority", "issue_date", "expiry_date",
        ],
        "auto_set": [
            "id", "yacht_id", "created_at",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["person_name", "certificate_type"],
        "enums": {},
    },
    # Domain aliases — parser detection returns these short names,
    # but the canonical vocabulary uses the full table-aligned names above.
    # These aliases ensure the mapping dropdown is populated correctly.
    "certificates": {
        "mappable": [
            "certificate_type", "certificate_name", "certificate_number",
            "issuing_authority", "issue_date", "expiry_date",
            "last_survey_date", "next_survey_due", "status",
        ],
        "auto_set": [
            "id", "yacht_id", "created_at",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["certificate_type", "certificate_name", "issuing_authority"],
        "enums": {},
    },
    "crew": {
        "mappable": [
            "person_name", "certificate_type", "certificate_number",
            "issuing_authority", "issue_date", "expiry_date",
        ],
        "auto_set": [
            "id", "yacht_id", "created_at",
            "source", "source_id", "import_session_id", "imported_at",
        ],
        "required": ["person_name", "certificate_type"],
        "enums": {},
    },
}


# =============================================================================
# POST /api/import/upload
# =============================================================================

@router.post("/upload")
async def upload_files(
    request: Request,
    source: str = Form(...),
    files: list[UploadFile] = File(...),
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Upload PMS export files and create an import session.
    Stores files in Supabase Storage, runs parse & detect, returns session_id.
    """
    # Auth
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    email = auth["email"]

    # Validate source
    valid_sources = ("idea_yacht", "seahub", "sealogical", "generic")
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {valid_sources}")

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    session_id = str(uuid.uuid4())
    sb = get_tenant_client()

    # 1. Create import_sessions row
    session_data = {
        "id": session_id,
        "yacht_id": yacht_id,
        "source": source,
        "status": "pending",
        "created_by": email,
    }
    result = sb.table("import_sessions").insert(session_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create import session")

    logger.info(f"[Import] Session {session_id[:8]} created for yacht {yacht_id[:8]} source={source}")

    # 2. Store files in Supabase Storage and parse
    stored_paths = []
    parsed_files = []
    documents = []

    # Data file extensions
    data_extensions = {".csv", ".sql", ".xlsx", ".xls"}
    # Document file extensions
    doc_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".docx", ".doc"}

    for upload_file in files:
        raw_data = await upload_file.read()
        filename = upload_file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        # Handle ZIP: extract and process contents
        if ext == ".zip":
            zip_result = parse_zip(raw_data, filename, source=source)
            # Store the zip itself
            zip_path = f"{yacht_id}/{session_id}/{filename}"
            try:
                sb.storage.from_("vessel-imports").upload(
                    zip_path, raw_data,
                    {"content-type": "application/zip", "upsert": "true"},
                )
                stored_paths.append(zip_path)
            except Exception as e:
                logger.error(f"[Import] ZIP storage failed: {e}")

            # Process extracted data files
            for pr in zip_result["parse_results"]:
                parsed_files.append(_parse_result_to_dict(pr, source=source))
            # Process extracted documents
            for doc in zip_result["documents"]:
                doc_path = f"{yacht_id}/{session_id}/documents/{doc.filename}"
                if doc.data:
                    try:
                        sb.storage.from_("vessel-imports").upload(
                            doc_path, doc.data,
                            {"content-type": doc.content_type, "upsert": "true"},
                        )
                        stored_paths.append(doc_path)
                    except Exception as e:
                        logger.warning(f"[Import] Doc storage failed for {doc.filename}: {e}")
                documents.append({
                    "filename": doc.filename,
                    "size_bytes": doc.size_bytes,
                    "type": doc.content_type,
                    "domain_hint": doc.domain_hint,
                    "storage_path": doc_path,
                })
            # Unclassified from ZIP
            for uc in zip_result["unclassified"]:
                documents.append({
                    "filename": uc.filename,
                    "size_bytes": uc.size_bytes,
                    "type": "unknown",
                    "domain_hint": None,
                })
            continue  # Skip the per-file processing below

        # Store in Supabase Storage
        storage_path = f"{yacht_id}/{session_id}/{filename}"
        try:
            sb.storage.from_("vessel-imports").upload(
                storage_path,
                raw_data,
                {"content-type": upload_file.content_type or "application/octet-stream", "upsert": "true"},
            )
            stored_paths.append(storage_path)
            logger.info(f"[Import] Stored {filename} ({len(raw_data)} bytes) at {storage_path}")
        except Exception as e:
            logger.error(f"[Import] Storage failed for {filename}: {e}")
            # Continue with other files — don't fail the whole upload
            parsed_files.append({
                "filename": filename,
                "error": f"Storage failed: {str(e)}",
            })
            continue

        # Route by file type
        if ext in data_extensions:
            # Parse data file
            if ext == ".csv":
                parse_result = parse_csv(raw_data, filename)
                parsed_files.append(_parse_result_to_dict(parse_result, source=source))
            elif ext == ".xlsx":
                parse_result = parse_xlsx(raw_data, filename)
                parsed_files.append(_parse_result_to_dict(parse_result, source=source))
            elif ext == ".xls":
                parse_result = parse_xls(raw_data, filename)
                parsed_files.append(_parse_result_to_dict(parse_result, source=source))
            elif ext == ".sql":
                sql_results = parse_sql(raw_data, filename)
                for sr in sql_results:
                    parsed_files.append(_parse_result_to_dict(sr, source=source))
        elif ext in doc_extensions:
            # Document — store metadata, don't parse
            content_type_map = {
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".tiff": "image/tiff", ".tif": "image/tiff",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".doc": "application/msword",
            }
            documents.append({
                "filename": filename,
                "size_bytes": len(raw_data),
                "type": content_type_map.get(ext, "application/octet-stream"),
                "domain_hint": _infer_doc_domain(filename),
                "storage_path": storage_path,
            })
        else:
            # Unknown file type — store but flag
            documents.append({
                "filename": filename,
                "size_bytes": len(raw_data),
                "type": "unknown",
                "domain_hint": None,
                "storage_path": storage_path,
            })

    # 3. Build detection result
    detection_result = {
        "source_detected": source,
        "data_files": parsed_files,
        "documents": documents,
        "unclassified": [d for d in documents if d.get("type") == "unknown"],
    }

    # 4. Update session with detection result
    update_status = "detecting" if any(f.get("status") in ("xlsx_parser_pending", "sql_parser_pending") for f in parsed_files) else "mapping"

    sb.table("import_sessions").update({
        "status": update_status,
        "file_paths": stored_paths,
        "detection_result": detection_result,
    }).eq("id", session_id).execute()

    logger.info(
        f"[Import] Session {session_id[:8]}: {len(parsed_files)} data files, "
        f"{len(documents)} documents, status={update_status}"
    )

    return JSONResponse(status_code=201, content={
        "import_session_id": session_id,
        "status": update_status,
        "files_received": [f.filename for f in files],
        "data_files_count": len(parsed_files),
        "documents_count": len(documents),
        "message": "Files received. Analysing structure.",
    })


# =============================================================================
# GET /api/import/session/{session_id}
# =============================================================================

@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """Get import session state including detection result and column vocabulary."""
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    result = sb.table("import_sessions").select("*").eq("id", session_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    session = result.data[0]

    # Include CelesteOS vocabulary for mapping dropdowns
    response = {**session, "celeste_vocabulary": CELESTE_VOCABULARY}
    return response


# =============================================================================
# POST /api/import/session/{session_id}/confirm-mapping
# =============================================================================

@router.post("/session/{session_id}/confirm-mapping")
async def confirm_mapping(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Save human-confirmed column mapping.
    NEVER auto-proceed past this gate — humans always in control.
    """
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    # Verify session exists and belongs to this yacht
    session = sb.table("import_sessions").select("id, status, yacht_id").eq("id", session_id).eq("yacht_id", yacht_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    current_status = session.data[0]["status"]
    if current_status not in ("detecting", "mapping"):
        raise HTTPException(status_code=400, detail=f"Cannot confirm mapping in status '{current_status}'")

    # Parse request body
    body = await request.json()
    mappings = body.get("mappings")
    if not mappings:
        raise HTTPException(status_code=400, detail="Missing 'mappings' in request body")

    # Store the column map
    sb.table("import_sessions").update({
        "column_map": mappings,
        "status": "mapping",
    }).eq("id", session_id).execute()

    logger.info(f"[Import] Session {session_id[:8]}: column mapping confirmed by user")

    return {"status": "mapping_confirmed", "message": "Column mapping saved. Ready for dry run."}


# =============================================================================
# POST /api/import/session/{session_id}/dry-run
# =============================================================================

@router.post("/session/{session_id}/dry-run")
async def dry_run(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Run the import against a staging view — preview what will be created.
    Does NOT write to production tables.
    """
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    # Load session
    session = sb.table("import_sessions").select("*").eq("id", session_id).eq("yacht_id", yacht_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    sess = session.data[0]
    if not sess.get("column_map"):
        raise HTTPException(status_code=400, detail="Column mapping not confirmed. Cannot dry-run.")

    detection = sess.get("detection_result", {})
    data_files = detection.get("data_files", [])
    column_map_data = sess.get("column_map", [])
    source = sess.get("source", "generic")

    domains = {}
    warnings = []
    first_10 = {}

    # Re-parse files and run dry-run transformation
    for file_info in data_files:
        domain = file_info.get("domain")
        if not domain:
            continue

        filename = file_info.get("filename", "")
        date_format = file_info.get("date_format_detected")

        # Find the column map for this file
        file_mappings = None
        for m in column_map_data:
            if m.get("file") == filename or m.get("domain") == domain:
                file_mappings = m.get("columns", [])
                break

        if not file_mappings:
            # Fall back to auto-generated mappings from detection
            file_mappings = [
                {"source": col["source_name"], "target": col.get("suggested_target"), "action": col.get("action", "skip")}
                for col in file_info.get("columns", [])
            ]

        # Re-parse the file to get row data (handles both direct CSV and ZIP)
        file_paths = sess.get("file_paths", [])
        rows = _reparse_rows_for_domain(filename, file_paths, sb)

        # Run dry-run
        if rows:
            domain_result = dry_run_domain(
                rows=rows,
                column_map=file_mappings,
                domain=domain,
                source=source,
                yacht_id=yacht_id,
                session_id=session_id,
                date_format=date_format,
                supabase_client=sb,
            )
            domains[domain] = {
                "total": domain_result["total"],
                "new": domain_result["new"],
                "duplicates": domain_result["duplicates"],
                "errors": domain_result["errors"],
                "warnings_count": domain_result["warnings_count"],
                "file_resolutions": domain_result.get("file_resolutions", []),
                "resolution_summary": domain_result.get("resolution_summary", {}),
            }
            warnings.extend(domain_result["warnings"])
            first_10[domain] = domain_result["first_10"]
        else:
            domains[domain] = {
                "total": file_info.get("row_count", 0),
                "new": file_info.get("row_count", 0),
                "duplicates": 0,
                "errors": 0,
                "warnings_count": 0,
            }

    total_records = sum(d["total"] for d in domains.values())
    has_errors = any(d["errors"] > 0 for d in domains.values())

    # Aggregate file reference resolution summary across all domains
    file_ref_total = sum(d.get("resolution_summary", {}).get("total", 0) for d in domains.values())
    file_ref_resolved = sum(d.get("resolution_summary", {}).get("resolved", 0) for d in domains.values())
    file_ref_summary = None
    if file_ref_total > 0:
        file_ref_summary = {
            "total": file_ref_total,
            "matched": file_ref_resolved,
            "placeholders": file_ref_total - file_ref_resolved,
        }

    preview_summary = {
        "domains": domains,
        "total_records": total_records,
        "can_commit": not has_errors and total_records > 0,
        "warnings": warnings,
        "first_10": first_10,
        "file_ref_summary": file_ref_summary,
    }

    # Store preview
    sb.table("import_sessions").update({
        "preview_summary": preview_summary,
        "status": "preview",
    }).eq("id", session_id).execute()

    logger.info(f"[Import] Session {session_id[:8]}: dry run complete. {total_records} records, can_commit={not has_errors}")

    return {"status": "preview", "preview_summary": preview_summary}


# =============================================================================
# POST /api/import/session/{session_id}/commit
# =============================================================================

@router.post("/session/{session_id}/commit")
async def commit_import(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Execute the real import — write to production tables.
    Requires status='preview' and can_commit=true.
    """
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    # Load session
    session = sb.table("import_sessions").select("*").eq("id", session_id).eq("yacht_id", yacht_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    sess = session.data[0]
    if sess["status"] != "preview":
        raise HTTPException(status_code=400, detail=f"Cannot commit in status '{sess['status']}'. Run dry-run first.")

    preview = sess.get("preview_summary", {})
    if not preview.get("can_commit"):
        raise HTTPException(status_code=400, detail="Cannot commit — dry run has errors. Fix issues and re-run.")

    # Mark as importing
    sb.table("import_sessions").update({"status": "importing"}).eq("id", session_id).execute()

    logger.info(f"[Import] Session {session_id[:8]}: commit started")

    # Resolve user UUID for uploaded_by on attachment tables
    user_id = None
    email = auth.get("email")
    if email:
        try:
            user_result = sb.table("auth_users_profiles").select("id").eq(
                "yacht_id", yacht_id
            ).limit(1).execute()
            if user_result.data:
                user_id = user_result.data[0]["id"]
        except Exception as e:
            logger.warning(f"[Import] Could not resolve user UUID: {e}")

    detection = sess.get("detection_result", {})
    data_files = detection.get("data_files", [])
    column_map_data = sess.get("column_map", [])
    source = sess.get("source", "generic")
    records_created = {}

    for file_info in data_files:
        domain = file_info.get("domain")
        if not domain:
            continue

        filename = file_info.get("filename", "")
        date_format = file_info.get("date_format_detected")

        # Find column map for this file
        file_mappings = None
        for m in column_map_data:
            if m.get("file") == filename or m.get("domain") == domain:
                file_mappings = m.get("columns", [])
                break

        if not file_mappings:
            file_mappings = [
                {"source": col["source_name"], "target": col.get("suggested_target"), "action": col.get("action", "skip")}
                for col in file_info.get("columns", [])
            ]

        # Re-parse file (handles both direct CSV and ZIP)
        file_paths = sess.get("file_paths", [])
        rows = _reparse_rows_for_domain(filename, file_paths, sb)

        if rows:
            try:
                count, _ = commit_domain(
                    rows=rows,
                    column_map=file_mappings,
                    domain=domain,
                    source=source,
                    yacht_id=yacht_id,
                    session_id=session_id,
                    supabase_client=sb,
                    date_format=date_format,
                    user_id=user_id,
                )
                records_created[domain] = count
            except Exception as e:
                logger.error(f"[Import] Commit failed for {domain}: {e}")
                # Mark session as failed
                sb.table("import_sessions").update({
                    "status": "failed",
                    "warnings": [{"field": None, "message": f"Commit failed for {domain}: {str(e)}", "severity": "red"}],
                }).eq("id", session_id).execute()
                raise HTTPException(status_code=500, detail=f"Import failed for {domain}: {str(e)}")

    sb.table("import_sessions").update({
        "status": "completed",
        "records_created": records_created,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()

    rollback_until = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()

    return {
        "status": "completed",
        "records_created": records_created,
        "message": f"Import complete. {sum(records_created.values())} records imported. Your vessel history is now searchable.",
        "rollback_available_until": rollback_until,
    }


# =============================================================================
# POST /api/import/session/{session_id}/rollback
# =============================================================================

@router.post("/session/{session_id}/rollback")
async def rollback_import(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Reverse an import within the 48-hour window.
    Deletes all records created by this import session.
    """
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    # Load session
    session = sb.table("import_sessions").select("*").eq("id", session_id).eq("yacht_id", yacht_id).execute()
    if not session.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    sess = session.data[0]
    if sess["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Cannot rollback in status '{sess['status']}'")

    if sess.get("rolled_back_at"):
        raise HTTPException(status_code=400, detail="Import already rolled back")

    # Check 48-hour window
    completed_at = datetime.fromisoformat(sess["completed_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - completed_at > timedelta(hours=48):
        raise HTTPException(status_code=400, detail="Rollback window expired (48 hours). Import is now permanent.")

    logger.info(f"[Import] Session {session_id[:8]}: rollback initiated")

    records_deleted = {}
    records_created = sess.get("records_created", {})

    for domain in records_created.keys():
        try:
            count = rollback_domain(
                domain=domain,
                session_id=session_id,
                yacht_id=yacht_id,
                supabase_client=sb,
            )
            records_deleted[domain] = count
        except Exception as e:
            logger.error(f"[Import] Rollback failed for {domain}: {e}")
            raise HTTPException(status_code=500, detail=f"Rollback failed for {domain}: {str(e)}")

    sb.table("import_sessions").update({
        "status": "rolled_back",
        "rolled_back_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()

    total_deleted = sum(records_deleted.values())
    logger.info(f"[Import] Session {session_id[:8]}: rollback complete. {total_deleted} records deleted.")

    return {
        "status": "rolled_back",
        "records_deleted": records_deleted,
        "message": "Import reversed. All imported records have been removed.",
    }


# =============================================================================
# GET /api/import/session/{session_id}/unresolved
# =============================================================================

@router.get("/session/{session_id}/unresolved")
async def get_unresolved_refs(
    session_id: str,
    request: Request,
    x_import_dev_token: Optional[str] = Header(None),
):
    """
    Get unresolved file references for an import session.
    Useful for manual resolution or reporting on missing documents.
    """
    auth = resolve_auth(request, x_import_dev_token)
    yacht_id = auth["yacht_id"]
    sb = get_tenant_client()

    result = sb.table("import_sessions").select(
        "id, status, metadata"
    ).eq("id", session_id).eq("yacht_id", yacht_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Import session not found")

    sess = result.data[0]
    metadata = sess.get("metadata") or {}
    unresolved = metadata.get("unresolved_file_refs", [])

    return {
        "session_id": session_id,
        "status": sess["status"],
        "unresolved_file_refs": unresolved,
        "count": len(unresolved),
    }


# =============================================================================
# HELPERS
# =============================================================================

def _reparse_rows_for_domain(filename: str, file_paths: list, sb) -> list[dict]:
    """
    Re-parse rows for a given filename from stored files.
    Handles both direct CSV paths and ZIP archives (where individual CSVs
    are extracted in memory but only the ZIP is stored).
    """
    # First try: direct match in file_paths
    matching_path = next((p for p in file_paths if filename in p), None)
    if matching_path:
        try:
            file_data = sb.storage.from_("vessel-imports").download(matching_path)
            ext = os.path.splitext(matching_path)[1].lower()
            if ext == ".csv":
                return parse_csv(file_data, filename).rows
            elif ext == ".xlsx":
                return parse_xlsx(file_data, filename).rows
            elif ext == ".xls":
                return parse_xls(file_data, filename).rows
        except Exception as e:
            logger.warning(f"[Import] Could not re-parse {filename} from {matching_path}: {e}")

    # Second try: look for a ZIP in file_paths and extract the CSV from it
    zip_path = next((p for p in file_paths if p.endswith(".zip")), None)
    if zip_path:
        try:
            zip_data = sb.storage.from_("vessel-imports").download(zip_path)
            zip_result = parse_zip(zip_data, os.path.basename(zip_path))
            for pr in zip_result["parse_results"]:
                if pr.filename == filename:
                    return pr.rows
            logger.warning(f"[Import] File '{filename}' not found inside ZIP")
        except Exception as e:
            logger.warning(f"[Import] Could not extract {filename} from ZIP: {e}")

    return []

def _parse_result_to_dict(result: ParseResult, source: str = "generic") -> dict:
    """Convert ParseResult to JSON-serializable dict for detection_result.
    Includes column mapping suggestions from the column matcher."""
    domain = result.domain_hint

    # Build sample values dict for file ref detection
    col_samples = {col.source_name: col.sample_values for col in result.columns}

    # Run column matcher if we have a domain
    column_mappings = {}
    if domain:
        vocab = CELESTE_VOCABULARY.get(domain, {}).get("mappable", [])
        # Map domain aliases for Seahub vocabulary mismatches
        domain_for_profile = domain
        mappings = match_columns(
            source_columns=[col.source_name for col in result.columns],
            domain=domain_for_profile,
            source=source,
            vocabulary=vocab,
            column_samples=col_samples,
        )
        column_mappings = {m.source_name: m for m in mappings}

    return {
        "filename": result.filename,
        "domain": domain,
        "encoding_detected": result.encoding_detected,
        "delimiter_detected": result.delimiter_detected,
        "header_row": result.header_row,
        "row_count": result.row_count,
        "date_format_detected": result.date_format_detected,
        "columns": [
            {
                "source_name": col.source_name,
                "suggested_target": column_mappings[col.source_name].suggested_target if col.source_name in column_mappings else None,
                "confidence": column_mappings[col.source_name].confidence if col.source_name in column_mappings else 0.0,
                "action": column_mappings[col.source_name].action if col.source_name in column_mappings else "skip",
                "sample_values": col.sample_values[:5],
                # Use column matcher's inferred_type (file_ref) if detected, otherwise parser's type
                "inferred_type": (
                    column_mappings[col.source_name].inferred_type
                    if col.source_name in column_mappings and column_mappings[col.source_name].inferred_type
                    else col.inferred_type
                ),
            }
            for col in result.columns
        ],
        "warnings": [
            {
                "field": w.field,
                "message": w.message,
                "severity": w.severity,
                "row": w.row,
            }
            for w in result.warnings
        ],
    }


def _infer_doc_domain(filename: str) -> Optional[str]:
    """Infer document domain from filename or path."""
    lower = filename.lower()
    if any(k in lower for k in ("manual", "handbook", "guide", "procedure")):
        return "manuals"
    if any(k in lower for k in ("certificate", "cert", "survey", "class")):
        return "certificates"
    if any(k in lower for k in ("photo", "image", "img", "pic")):
        return "photos"
    if any(k in lower for k in ("drawing", "schematic", "diagram", "plan")):
        return "drawings"
    if any(k in lower for k in ("report", "inspection", "audit")):
        return "reports"
    return None
