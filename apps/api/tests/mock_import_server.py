"""
Mock Import API Server for Playwright e2e tests.
Runs on port 8001 and returns realistic responses for all 6 import endpoints.
No Supabase dependency — entirely in-memory.

Usage:
    python tests/mock_import_server.py

Frontend Playwright tests point VITE_IMPORT_API_URL=http://localhost:8001
"""

import os
import sys
import uuid
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import parsers directly — avoid importing routes (which triggers Supabase init)
from parsers.csv_parser import parse_csv
from parsers.xlsx_parser import parse_xlsx, parse_xls
from parsers.sql_parser import parse_sql
from parsers.zip_handler import parse_zip
from mappers.column_matcher import match_columns

# Inline the vocabulary and helper to avoid importing routes.import_routes
CELESTE_VOCABULARY = {
    "equipment": {"mappable": ["name","description","code","manufacturer","model","serial_number","location","category","status","criticality","system_type","running_hours","service_interval_hours"], "auto_set": ["id","yacht_id","created_at","updated_at","source","source_id","import_session_id","imported_at"]},
    "work_orders": {"mappable": ["title","description","status","priority","type","work_order_type","due_date","completed_at","completion_notes","notes"], "auto_set": ["id","yacht_id","wo_number","created_by","created_at","updated_at","source","source_id","import_session_id","imported_at"]},
    "faults": {"mappable": ["title","description","severity","status","fault_code","detected_at","resolved_at","resolution_notes"], "auto_set": ["id","yacht_id","created_at","updated_at","source","source_id","import_session_id","imported_at"]},
    "parts": {"mappable": ["name","description","part_number","category","manufacturer","unit","quantity_on_hand","minimum_quantity","location"], "auto_set": ["id","yacht_id","created_at","updated_at","source","source_id","import_session_id","imported_at"]},
    "vessel_certificates": {"mappable": ["certificate_type","certificate_name","certificate_number","issuing_authority","issue_date","expiry_date","last_survey_date","next_survey_due","status"], "auto_set": ["id","yacht_id","created_at","source","source_id","import_session_id","imported_at"]},
    "crew_certificates": {"mappable": ["person_name","certificate_type","certificate_number","issuing_authority","issue_date","expiry_date"], "auto_set": ["id","yacht_id","created_at","source","source_id","import_session_id","imported_at"]},
    "certificates": {"mappable": ["certificate_type","certificate_name","certificate_number","issuing_authority","issue_date","expiry_date","last_survey_date","next_survey_due","status"], "auto_set": ["id","yacht_id","created_at","source","source_id","import_session_id","imported_at"], "required": ["certificate_type","certificate_name","issuing_authority"]},
    "crew": {"mappable": ["person_name","certificate_type","certificate_number","issuing_authority","issue_date","expiry_date"], "auto_set": ["id","yacht_id","created_at","source","source_id","import_session_id","imported_at"], "required": ["person_name","certificate_type"]},
}


def _parse_result_to_dict(result, source="generic"):
    domain = result.domain_hint
    column_mappings = {}
    if domain:
        vocab = CELESTE_VOCABULARY.get(domain, {}).get("mappable", [])
        mappings = match_columns([col.source_name for col in result.columns], domain, source, vocab)
        column_mappings = {m.source_name: m for m in mappings}
    return {
        "filename": result.filename, "domain": domain,
        "encoding_detected": result.encoding_detected, "delimiter_detected": result.delimiter_detected,
        "header_row": result.header_row, "row_count": result.row_count,
        "date_format_detected": result.date_format_detected,
        "columns": [{"source_name": c.source_name, "suggested_target": column_mappings[c.source_name].suggested_target if c.source_name in column_mappings else None, "confidence": column_mappings[c.source_name].confidence if c.source_name in column_mappings else 0.0, "action": column_mappings[c.source_name].action if c.source_name in column_mappings else "skip", "sample_values": c.sample_values[:5], "inferred_type": c.inferred_type} for c in result.columns],
        "warnings": [{"field": w.field, "message": w.message, "severity": w.severity, "row": w.row} for w in result.warnings],
    }

app = FastAPI(title="Import Pipeline Mock Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions = {}

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


@app.post("/api/import/upload")
async def upload(
    source: str = Form(...),
    files: list[UploadFile] = File(...),
):
    session_id = str(uuid.uuid4())

    parsed_files = []
    documents = []

    for upload_file in files:
        raw = await upload_file.read()
        filename = upload_file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".csv":
            result = parse_csv(raw, filename)
            parsed_files.append(_parse_result_to_dict(result, source=source))
        elif ext == ".xlsx":
            result = parse_xlsx(raw, filename)
            parsed_files.append(_parse_result_to_dict(result, source=source))
        elif ext == ".xls":
            result = parse_xls(raw, filename)
            parsed_files.append(_parse_result_to_dict(result, source=source))
        elif ext == ".sql":
            results = parse_sql(raw, filename)
            for r in results:
                parsed_files.append(_parse_result_to_dict(r, source=source))
        elif ext == ".zip":
            zip_result = parse_zip(raw, filename, source=source)
            for r in zip_result["parse_results"]:
                parsed_files.append(_parse_result_to_dict(r, source=source))
            for doc in zip_result["documents"]:
                documents.append({
                    "filename": doc.filename,
                    "size_bytes": doc.size_bytes,
                    "type": doc.content_type,
                    "domain_hint": doc.domain_hint,
                })

    sessions[session_id] = {
        "id": session_id,
        "yacht_id": TEST_YACHT_ID,
        "source": source,
        "status": "mapping",
        "file_paths": [f.filename for f in files],
        "detection_result": {
            "source_detected": source,
            "data_files": parsed_files,
            "documents": documents,
            "unclassified": [],
        },
        "column_map": None,
        "preview_summary": None,
        "records_created": None,
        "created_by": "test@celeste7.ai",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "rolled_back_at": None,
        "_raw_files": {},  # not stored for mock
    }

    return JSONResponse(status_code=201, content={
        "import_session_id": session_id,
        "status": "mapping",
        "files_received": [f.filename for f in files],
        "data_files_count": len(parsed_files),
        "documents_count": len(documents),
        "message": "Files received. Analysing structure.",
    })


@app.get("/api/import/session/{session_id}")
async def get_session(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})
    return {**sess, "celeste_vocabulary": CELESTE_VOCABULARY}


@app.post("/api/import/session/{session_id}/confirm-mapping")
async def confirm_mapping(session_id: str, request: Request):
    sess = sessions.get(session_id)
    if not sess:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})

    body = await request.json()
    sess["column_map"] = body.get("mappings", [])
    sess["status"] = "mapping"

    return {"status": "mapping_confirmed", "message": "Column mapping saved. Ready for dry run."}


@app.post("/api/import/session/{session_id}/dry-run")
async def dry_run(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})

    data_files = sess["detection_result"].get("data_files", [])
    domains = {}
    warnings = []

    for f in data_files:
        domain = f.get("domain")
        if domain:
            domains[domain] = {
                "total": f["row_count"],
                "new": f["row_count"],
                "duplicates": 0,
                "errors": 0,
                "warnings_count": len(f.get("warnings", [])),
            }

    total = sum(d["total"] for d in domains.values())
    preview = {
        "domains": domains,
        "total_records": total,
        "can_commit": total > 0,
        "warnings": warnings,
        "first_10": {},
    }

    sess["preview_summary"] = preview
    sess["status"] = "preview"

    return {"status": "preview", "preview_summary": preview}


@app.post("/api/import/session/{session_id}/commit")
async def commit(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})

    preview = sess.get("preview_summary", {})
    records = {d: info["total"] for d, info in preview.get("domains", {}).items()}

    sess["status"] = "completed"
    sess["records_created"] = records
    sess["completed_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "status": "completed",
        "records_created": records,
        "message": f"Import complete. {sum(records.values())} records imported. Your vessel history is now searchable.",
        "rollback_available_until": (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat(),
    }


@app.post("/api/import/session/{session_id}/rollback")
async def rollback(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        return JSONResponse(status_code=404, content={"detail": "Session not found"})

    if sess["status"] != "completed":
        return JSONResponse(status_code=400, content={"detail": f"Cannot rollback in status '{sess['status']}'"})

    records = sess.get("records_created", {})
    sess["status"] = "rolled_back"
    sess["rolled_back_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "status": "rolled_back",
        "records_deleted": records,
        "message": "Import reversed. All imported records have been removed.",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "mock", "sessions": len(sessions)}


if __name__ == "__main__":
    print("Starting Mock Import API Server on port 8001...")
    print("Point Playwright tests at: VITE_IMPORT_API_URL=http://localhost:8001")
    port = int(os.getenv("MOCK_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
