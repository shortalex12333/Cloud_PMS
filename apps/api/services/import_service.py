"""
Import Service
==============
Core business logic for the PMS import pipeline.
Handles: row transformation, dry-run validation, commit to entity tables,
search_index population, and rollback.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from mappers.date_normalizer import normalize_date
from mappers.status_mapper import map_status, CANONICAL_STATUSES
from handlers.schema_mapping import get_table

logger = logging.getLogger("import.service")

# Domain → object_type mapping for search_index
DOMAIN_TO_OBJECT_TYPE = {
    "equipment": "equipment",
    "work_orders": "work_order",
    "faults": "fault",
    "parts": "part",
    "vessel_certificates": "certificate",
    "crew_certificates": "crew_certificate",
    "certificates": "certificate",
}

# Domain → physical table name
DOMAIN_TO_TABLE = {
    "equipment": "pms_equipment",
    "work_orders": "pms_work_orders",
    "faults": "pms_faults",
    "parts": "pms_parts",
    "vessel_certificates": "pms_vessel_certificates",
    "crew_certificates": "pms_crew_certificates",
    "certificates": "pms_vessel_certificates",
}

# Date-type columns per domain (for date normalization)
DATE_COLUMNS = {
    "equipment": [],
    "work_orders": ["due_date", "completed_at"],
    "faults": ["detected_at", "resolved_at"],
    "parts": [],
    "vessel_certificates": ["issue_date", "expiry_date", "last_survey_date", "next_survey_due"],
    "crew_certificates": ["issue_date", "expiry_date"],
    "certificates": ["issue_date", "expiry_date", "last_survey_date", "next_survey_due"],
}

# Status columns per domain
STATUS_COLUMNS = {
    "equipment": "status",
    "work_orders": "status",
    "faults": "status",
    "certificates": "status",
    "vessel_certificates": "status",
}


def transform_row(
    source_row: dict,
    column_map: list[dict],
    domain: str,
    source: str,
    yacht_id: str,
    session_id: str,
    date_format: Optional[str] = None,
) -> tuple[dict, list[dict]]:
    """
    Transform a source row using the confirmed column map.

    Returns:
        (transformed_row, warnings)
        transformed_row has CelesteOS field names and auto-set fields.
        warnings is a list of {field, message, severity}.
    """
    warnings = []
    result = {}

    # Apply column mappings
    for mapping in column_map:
        source_col = mapping.get("source")
        target_col = mapping.get("target")
        action = mapping.get("action", "skip")

        if action == "skip" or not target_col:
            continue

        value = source_row.get(source_col, "")
        if not value or not str(value).strip():
            result[target_col] = None
            continue

        value = str(value).strip()

        # Normalize dates
        if target_col in DATE_COLUMNS.get(domain, []):
            user_date_format = mapping.get("date_format") or date_format
            normalized = normalize_date(value, user_date_format)
            if normalized:
                result[target_col] = normalized
            else:
                result[target_col] = None
                warnings.append({
                    "field": target_col,
                    "message": f"Could not parse date '{value}' for {target_col}",
                    "severity": "amber",
                })
            continue

        # Map status/priority/type values (enum-typed columns)
        status_col = STATUS_COLUMNS.get(domain)
        if target_col == status_col:
            mapped = map_status(value, domain, source)
            # Validate against real DB enum values
            valid_values = CANONICAL_STATUSES.get(domain, set())
            if valid_values and mapped not in valid_values:
                warnings.append({
                    "field": target_col,
                    "message": f"Value '{value}' mapped to '{mapped}' which is not a valid {domain} status. Defaulting to first valid value.",
                    "severity": "amber",
                })
                mapped = next(iter(valid_values)) if valid_values else mapped
            result[target_col] = mapped
            continue

        # Map priority (work_orders only)
        if target_col == "priority" and domain == "work_orders":
            mapped = map_status(value, "work_orders_priority", source)
            valid = CANONICAL_STATUSES.get("work_orders_priority", set())
            if valid and mapped not in valid:
                warnings.append({
                    "field": "priority",
                    "message": f"Priority '{value}' mapped to '{mapped}' which is not valid. Defaulting to 'routine'.",
                    "severity": "amber",
                })
                mapped = "routine"
            result[target_col] = mapped
            continue

        # Map type (work_orders only)
        if target_col == "type" and domain == "work_orders":
            mapped = map_status(value, "work_orders_type", source)
            valid = CANONICAL_STATUSES.get("work_orders_type", set())
            if valid and mapped not in valid:
                warnings.append({
                    "field": "type",
                    "message": f"Type '{value}' mapped to '{mapped}' which is not valid. Defaulting to 'unplanned'.",
                    "severity": "amber",
                })
                mapped = "unplanned"
            result[target_col] = mapped
            continue

        # Map severity (faults only)
        if target_col == "severity" and domain == "faults":
            mapped = map_status(value, "faults_severity", source)
            valid = CANONICAL_STATUSES.get("faults_severity", set())
            if valid and mapped not in valid:
                warnings.append({
                    "field": "severity",
                    "message": f"Severity '{value}' mapped to '{mapped}' which is not valid. Defaulting to 'medium'.",
                    "severity": "amber",
                })
                mapped = "medium"
            result[target_col] = mapped
            continue

        # Type casting for integer fields (real DB uses INTEGER, not TEXT)
        # Integer fields (real DB types verified 2026-04-06)
        # running_hours is NUMERIC (not integer) — keep as float
        integer_fields = {"quantity_on_hand", "minimum_quantity", "maximum_quantity",
                          "service_interval_hours"}
        # Numeric (decimal) fields
        numeric_fields = {"running_hours"}
        if target_col in integer_fields:
            try:
                result[target_col] = int(float(value))
            except (ValueError, TypeError):
                result[target_col] = None
                warnings.append({
                    "field": target_col,
                    "message": f"Could not convert '{value}' to integer for {target_col}",
                    "severity": "amber",
                })
            continue

        if target_col in numeric_fields:
            try:
                result[target_col] = float(value)
            except (ValueError, TypeError):
                result[target_col] = None
                warnings.append({
                    "field": target_col,
                    "message": f"Could not convert '{value}' to number for {target_col}",
                    "severity": "amber",
                })
            continue

        # Default: pass through as-is
        result[target_col] = value

    # Auto-set fields
    result["id"] = str(uuid.uuid4())
    result["yacht_id"] = yacht_id
    result["source"] = source
    result["import_session_id"] = session_id
    result["imported_at"] = datetime.now(timezone.utc).isoformat()

    # Extract source_id from the first ID-like column if not already mapped
    if "source_id" not in result:
        for mapping in column_map:
            source_col = mapping.get("source", "").lower()
            if any(k in source_col for k in ("_id", "equip_id", "defect_id", "task_id", "part_id", "cert_id")):
                val = source_row.get(mapping["source"], "")
                if val and str(val).strip():
                    result["source_id"] = str(val).strip()
                    break

    return result, warnings


def dry_run_domain(
    rows: list[dict],
    column_map: list[dict],
    domain: str,
    source: str,
    yacht_id: str,
    session_id: str,
    date_format: Optional[str] = None,
) -> dict:
    """
    Dry-run a domain: transform all rows, validate, count results.
    Does NOT write to database.

    Returns:
        {
            "total": int,
            "new": int,
            "duplicates": int,
            "errors": int,
            "warnings_count": int,
            "warnings": [...],
            "first_10": [...]
        }
    """
    all_warnings = []
    transformed = []
    errors = 0

    for row_idx, row in enumerate(rows):
        try:
            result, row_warnings = transform_row(
                row, column_map, domain, source, yacht_id, session_id, date_format
            )
            # Add row index to warnings
            for w in row_warnings:
                w["row"] = row_idx
                w["domain"] = domain
            all_warnings.extend(row_warnings)
            transformed.append(result)
        except Exception as e:
            errors += 1
            all_warnings.append({
                "field": None,
                "message": f"Row {row_idx}: {str(e)}",
                "severity": "red",
                "row": row_idx,
                "domain": domain,
            })

    return {
        "total": len(rows),
        "new": len(transformed),
        "duplicates": 0,  # TODO: check against existing data
        "errors": errors,
        "warnings_count": len(all_warnings),
        "warnings": all_warnings,
        "first_10": transformed[:10],
    }


def commit_domain(
    rows: list[dict],
    column_map: list[dict],
    domain: str,
    source: str,
    yacht_id: str,
    session_id: str,
    supabase_client,
    date_format: Optional[str] = None,
) -> tuple[int, list[str]]:
    """
    Commit a domain: transform rows and INSERT into entity table + search_index.

    Returns:
        (records_created, entity_ids)
    """
    table_name = DOMAIN_TO_TABLE.get(domain)
    object_type = DOMAIN_TO_OBJECT_TYPE.get(domain)

    if not table_name:
        logger.error(f"[Import] Unknown domain: {domain}")
        return 0, []

    transformed = []
    for row in rows:
        result, _ = transform_row(
            row, column_map, domain, source, yacht_id, session_id, date_format
        )
        transformed.append(result)

    if not transformed:
        return 0, []

    # Batch insert into entity table
    entity_ids = []
    batch_size = 100
    for i in range(0, len(transformed), batch_size):
        batch = transformed[i:i + batch_size]
        try:
            result = supabase_client.table(table_name).insert(batch).execute()
            if result.data:
                entity_ids.extend([r["id"] for r in result.data])
                logger.info(f"[Import] Inserted {len(result.data)} rows into {table_name}")
        except Exception as e:
            logger.error(f"[Import] Insert failed for {table_name} batch {i}: {e}")
            raise

    # Insert search_index rows for projection worker
    # Real DB requires search_text (NOT NULL) — build from entity fields
    # Projection worker will later enrich with full text + embedding
    if entity_ids and object_type:
        search_rows = []
        for idx, eid in enumerate(entity_ids):
            # Build basic search_text from the transformed row
            entity_row = transformed[idx] if idx < len(transformed) else {}
            search_parts = []
            for field in ("name", "title", "description", "manufacturer", "model",
                          "serial_number", "part_number", "fault_code", "certificate_name",
                          "certificate_number", "person_name", "wo_number", "code"):
                val = entity_row.get(field)
                if val:
                    search_parts.append(str(val))
            search_text = " ".join(search_parts) or f"Imported {object_type}"

            search_rows.append({
                "object_type": object_type,
                "object_id": eid,
                "yacht_id": yacht_id,
                "org_id": yacht_id,
                "search_text": search_text[:12000],  # max search_text length
                "embedding_status": "pending",
            })

        for i in range(0, len(search_rows), batch_size):
            batch = search_rows[i:i + batch_size]
            try:
                supabase_client.table("search_index").upsert(
                    batch,
                    on_conflict="object_type,object_id",
                ).execute()
            except Exception as e:
                logger.warning(f"[Import] search_index upsert warning for {domain}: {e}")
                # Non-fatal — projection worker will catch up

    return len(entity_ids), entity_ids


def rollback_domain(
    domain: str,
    session_id: str,
    yacht_id: str,
    supabase_client,
) -> int:
    """
    Soft-delete all records for a domain created by this import session.
    Uses deleted_at (NOT hard DELETE) — production DB has prevent_hard_delete() trigger.
    Returns count of rolled-back records.
    """
    table_name = DOMAIN_TO_TABLE.get(domain)
    if not table_name:
        return 0

    try:
        # Get IDs for search_index cleanup
        ids_result = supabase_client.table(table_name).select("id").eq(
            "import_session_id", session_id
        ).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

        entity_ids = [r["id"] for r in (ids_result.data or [])]
        if not entity_ids:
            return 0

        # Soft delete from entity table (set deleted_at, not DELETE)
        supabase_client.table(table_name).update({
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }).eq(
            "import_session_id", session_id
        ).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()

        # Remove from search_index (search_index may allow hard deletes)
        object_type = DOMAIN_TO_OBJECT_TYPE.get(domain)
        if object_type:
            for eid in entity_ids:
                try:
                    supabase_client.table("search_index").delete().eq(
                        "object_type", object_type
                    ).eq("object_id", eid).execute()
                except Exception:
                    # If hard delete blocked on search_index too, mark as failed
                    try:
                        supabase_client.table("search_index").update({
                            "embedding_status": "failed",
                        }).eq("object_type", object_type).eq("object_id", eid).execute()
                    except Exception:
                        pass

        logger.info(f"[Import] Rolled back (soft-deleted) {len(entity_ids)} records from {table_name}")
        return len(entity_ids)

    except Exception as e:
        logger.error(f"[Import] Rollback failed for {table_name}: {e}")
        raise
