# routes/handlers/equipment_handler.py
#
# Phase 5 dispatch handlers — equipment domain (canonical, all actions merged here).
# Translated from p0_actions_routes.py elif blocks.
# Phase C: merged unique adapters from equipment_handlers.py (class-based) into this file.
#
# Handler contract (Phase 5 flat functions):
#   async def handler(payload, context, yacht_id, user_id, user_context, db_client) -> dict
#
# Handler contract (Phase C adapter functions, registered directly in HANDLERS):
#   async def handler(**params) -> dict

from datetime import datetime, timezone
import hashlib
import math
import uuid as uuid_lib
import logging
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from supabase import Client
from handlers.ledger_utils import build_ledger_event

# Phase C: imports for adapter functions merged from equipment_handlers.py
from handlers.equipment_utils import (
    validate_storage_path_for_equipment,
    extract_audit_metadata,
    validate_status_transition,
    validate_work_order_for_oos,
    is_prepare_mode,
    generate_confirmation_token,
    VALID_EQUIPMENT_STATUSES,
    OOS_STATUS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PHASE C: AUDIT LOG HELPER (ported from equipment_handlers.py)
# =============================================================================

def _write_audit_log(db, entry: Dict):
    """
    Write entry to pms_audit_log.

    INVARIANT: signature is NEVER NULL - {} for non-signed, full payload for signed.
    """
    try:
        audit_payload = {
            "yacht_id": entry["yacht_id"],
            "entity_type": entry["entity_type"],
            "entity_id": entry["entity_id"],
            "action": entry["action"],
            "user_id": entry["user_id"],
            "old_values": entry.get("old_values"),
            "new_values": entry["new_values"],
            "signature": entry.get("signature", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.table("pms_audit_log").insert(audit_payload).execute()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


async def update_equipment_status(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # RBAC: chief_engineer, chief_officer, captain, manager only
    equipment_roles = ["chief_engineer", "chief_officer", "captain", "manager"]
    user_role = user_context.get("role", "")
    if user_role not in equipment_roles:
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to update equipment status",
            "required_roles": equipment_roles,
        }

    equipment_id = payload.get("equipment_id")
    new_status = payload.get("new_status")
    reason = payload.get("reason", "")

    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    if not new_status:
        raise HTTPException(status_code=400, detail="new_status is required")

    valid_statuses = ("operational", "degraded", "failed", "maintenance", "decommissioned")
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    check = (
        db_client.table("pms_equipment")
        .select("id, status")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    old_status = check.data.get("status", "operational")

    update_data = {
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        db_client.table("pms_equipment").update(update_data).eq(
            "id", equipment_id
        ).eq("yacht_id", yacht_id).execute()

        result = {
            "status": "success",
            "success": True,
            "equipment_id": equipment_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": f"Equipment status updated from {old_status} to {new_status}",
        }

        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id,
                user_id=user_id,
                event_type="status_change",
                entity_type="equipment",
                entity_id=equipment_id,
                action="update_equipment_status",
                user_role=user_context.get("role"),
                change_summary="Equipment status updated",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" in str(ledger_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed to record update_equipment_status: {ledger_err}")

        return result

    except HTTPException:
        raise
    except Exception as db_err:
        error_str = str(db_err)
        if "status" in error_str.lower() and "column" in error_str.lower():
            raise HTTPException(
                status_code=501,
                detail="Action blocked: pms_equipment.status column not found. Run migration 00000000000018.",
            )
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")


async def view_equipment(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    eq_result = (
        db_client.table("pms_equipment")
        .select("*")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not eq_result.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return {
        "status": "success",
        "success": True,
        "equipment": eq_result.data,
    }


async def view_equipment_detail(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    eq_result = (
        db_client.table("pms_equipment")
        .select("*")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not eq_result.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    faults = (
        db_client.table("pms_faults")
        .select("id, title, status, severity, detected_at")
        .eq("equipment_id", equipment_id)
        .eq("yacht_id", yacht_id)
        .order("detected_at", desc=True)
        .limit(10)
        .execute()
    )

    work_orders = (
        db_client.table("pms_work_orders")
        .select("id, title, status, priority, created_at")
        .eq("equipment_id", equipment_id)
        .eq("yacht_id", yacht_id)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "equipment": eq_result.data,
        "faults": faults.data or [],
        "work_orders": work_orders.data or [],
    }


async def view_equipment_history(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    equip_check = (
        db_client.table("pms_equipment")
        .select("id")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )
    if not equip_check.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    work_orders = (
        db_client.table("pms_work_orders")
        .select("id, wo_number, title, status, priority, created_at, completed_at")
        .eq("equipment_id", equipment_id)
        .eq("yacht_id", yacht_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "maintenance_history": work_orders.data or [],
        "count": len(work_orders.data) if work_orders.data else 0,
    }


async def view_equipment_parts(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    parts = (
        db_client.table("pms_parts")
        .select("id, part_number, name, quantity_on_hand, minimum_quantity, location")
        .eq("yacht_id", yacht_id)
        .eq("equipment_id", equipment_id)
        .limit(50)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "parts": parts.data or [],
        "count": len(parts.data) if parts.data else 0,
    }


async def view_linked_faults(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    faults = (
        db_client.table("pms_faults")
        .select("id, title, description, status, severity, detected_at")
        .eq("equipment_id", equipment_id)
        .eq("yacht_id", yacht_id)
        .order("detected_at", desc=True)
        .limit(50)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "faults": faults.data or [],
        "count": len(faults.data) if faults.data else 0,
    }


async def view_equipment_manual(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")

    equipment = (
        db_client.table("pms_equipment")
        .select("id, name, manufacturer, model, metadata")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )
    if not equipment.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    docs = (
        db_client.table("documents")
        .select("id, filename, storage_path, doc_type")
        .eq("yacht_id", yacht_id)
        .limit(10)
        .execute()
    )

    return {
        "status": "success",
        "success": True,
        "equipment": {
            "id": equipment.data.get("id"),
            "name": equipment.data.get("name"),
            "manufacturer": equipment.data.get("manufacturer"),
            "model": equipment.data.get("model"),
        },
        "manuals": docs.data or [],
        "manual_count": len(docs.data) if docs.data else 0,
    }


async def add_equipment_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    note_text = payload.get("note_text", "")

    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    current = (
        db_client.table("pms_equipment")
        .select("id, metadata")
        .eq("id", equipment_id)
        .eq("yacht_id", yacht_id)
        .single()
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Equipment not found")

    metadata = current.data.get("metadata", {}) or {}
    notes = metadata.get("notes", []) or []

    notes.append(
        {
            "text": note_text,
            "added_by": user_id,
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    metadata["notes"] = notes

    update_result = db_client.table("pms_equipment").update({
        "metadata": metadata,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).eq("yacht_id", yacht_id).execute()

    if not update_result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add equipment note"}

    result = {
        "status": "success",
        "success": True,
        "message": "Note added to equipment",
        "notes_count": len(notes),
    }

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id,
            user_id=user_id,
            event_type="update",
            entity_type="equipment",
            entity_id=payload.get("equipment_id"),
            action="add_equipment_note",
            user_role=user_context.get("role"),
            change_summary="Note added to equipment",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" in str(ledger_err):
            pass
        else:
            logger.warning(f"[Ledger] Failed to record add_equipment_note: {ledger_err}")

    return result


async def suggest_parts(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    fault_id = payload.get("fault_id")
    if not fault_id:
        raise HTTPException(status_code=400, detail="fault_id is required")

    fault = (
        db_client.table("pms_faults")
        .select("id, equipment_id, fault_code, title")
        .eq("id", fault_id)
        .eq("yacht_id", yacht_id)
        .maybe_single()
        .execute()
    )
    if not fault.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    equipment_id = fault.data.get("equipment_id")

    parts = []
    if equipment_id:
        # Parts linked to equipment via BOM table
        bom_result = (
            db_client.table("pms_equipment_parts_bom")
            .select("part_id")
            .eq("equipment_id", equipment_id)
            .limit(10)
            .execute()
        )
        part_ids = [r["part_id"] for r in (bom_result.data or []) if r.get("part_id")]
        if part_ids:
            parts_result = (
                db_client.table("pms_parts")
                .select("id, part_number, name, quantity_on_hand, location")
                .eq("yacht_id", yacht_id)
                .in_("id", part_ids)
                .execute()
            )
            parts = parts_result.data or []

    return {
        "status": "success",
        "success": True,
        "suggested_parts": parts,
        "message": f"Found {len(parts)} potentially relevant parts",
    }


# =============================================================================
# PHASE C: ADAPTER FUNCTIONS (merged from equipment_handlers.py)
# All adapters accept **params and delegate to domain logic.
# =============================================================================

async def _set_equipment_status(**params) -> dict:
    """
    Update equipment status (set_equipment_status / update_equipment_status v2).
    Required: equipment_id, status (or new_status)
    Optional: attention_reason, clear_attention, linked_work_order_id
    """
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    new_status = params.get("status") or params.get("new_status")
    if not new_status:
        return {"status": "error", "error_code": "VALIDATION_ERROR", "message": "status is required"}
    attention_reason = params.get("attention_reason")
    clear_attention = params.get("clear_attention", False)
    linked_work_order_id = params.get("linked_work_order_id")
    request_context = params.get("request_context")

    eq_result = db.table("pms_equipment").select(
        "id, name, status, yacht_id"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")

    is_valid, error_msg = validate_status_transition(old_status, new_status, linked_work_order_id)
    if not is_valid:
        return {"status": "error", "error_code": "INVALID_STATUS_TRANSITION", "message": error_msg}

    if new_status == OOS_STATUS:
        wo_valid, wo_error = validate_work_order_for_oos(db, linked_work_order_id, equipment_id, yacht_id)
        if not wo_valid:
            return {"status": "error", "error_code": "INVALID_WORK_ORDER", "message": wo_error}

    update_payload: dict = {
        "status": new_status,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if new_status in ("failed", "degraded") and attention_reason:
        update_payload["attention_flag"] = True
        update_payload["attention_reason"] = attention_reason
    elif clear_attention or new_status == "operational":
        update_payload["attention_flag"] = False
        update_payload["attention_reason"] = None

    db.table("pms_equipment").update(update_payload).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "set_equipment_status", "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": new_status, "attention_reason": attention_reason, "work_order_id": linked_work_order_id},
        "signature": {}, **audit_meta,
    })

    if new_status in ("failed", "degraded"):
        equipment_name = eq_result.data.get("name", "Equipment")
        try:
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id, "p_user_id": user_id,
                "p_notification_type": "equipment_status_degraded",
                "p_title": f"Action required: {equipment_name} is {new_status}",
                "p_body": "Create a work order to address this issue before it worsens.",
                "p_priority": "high" if new_status == "failed" else "normal",
                "p_entity_type": "equipment", "p_entity_id": equipment_id,
                "p_cta_action_id": "create_work_order_for_equipment",
                "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:degraded:{datetime.now(timezone.utc).date()}",
            }).execute()
        except Exception:
            pass

    return {"status": "success", "equipment_id": equipment_id, "old_status": old_status, "new_status": new_status, "work_order_id": linked_work_order_id}


async def _attach_file_to_equipment(**params) -> dict:
    """Attach a file (photo/document) to equipment."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    description = params.get("description")
    tags = params.get("tags", [])
    filename = params.get("filename")
    original_filename = params.get("original_filename")
    mime_type = params.get("mime_type")
    file_size = params.get("file_size")
    storage_path = params.get("storage_path")

    if not storage_path:
        return {"status": "error", "error_code": "MISSING_FILE", "message": "File upload required"}

    eq_result = db.table("pms_equipment").select("id").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    # Determine bucket
    category = (params.get("category") or "").lower()
    mt = (mime_type or "").lower()
    if category in ("photo", "image") or mt.startswith("image/"):
        bucket = "pms-work-order-photos"
    elif category in ("manual", "document", "pdf") or mt == "application/pdf":
        bucket = "documents"
    else:
        bucket = "attachments"

    attachment_payload = {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "filename": filename, "original_filename": original_filename,
        "mime_type": mime_type, "file_size": file_size, "storage_path": storage_path,
        "storage_bucket": bucket, "description": description,
        "tags": tags if tags else None,
        "uploaded_by": user_id, "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    ins = db.table("pms_attachments").insert(attachment_payload).execute()
    attachment_id = (ins.data or [{}])[0].get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_file_attached", "user_id": user_id,
        "old_values": None, "new_values": {"attachment_id": attachment_id, "filename": original_filename}, "signature": {},
    })

    return {"status": "success", "attachment_id": attachment_id, "equipment_id": equipment_id, "storage_path": storage_path}


async def _create_work_order_for_equipment(**params) -> dict:
    """Create a work order for equipment (prepare/execute pattern)."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    title = params["title"]
    wo_type = params["type"]
    priority = params["priority"]
    description = params.get("description")
    assigned_to = params.get("assigned_to")
    due_date = params.get("due_date")
    fault_severity = params.get("fault_severity")
    request_context = params.get("request_context")

    eq_result = db.table("pms_equipment").select("id, name, status").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")
    equipment_status = eq_result.data.get("status")

    valid_types = ["corrective", "preventive", "predictive", "emergency", "project"]
    if wo_type not in valid_types:
        return {"status": "error", "error_code": "INVALID_TYPE", "message": f"Invalid type: must be one of {valid_types}"}

    if is_prepare_mode(params):
        confirmation_token = generate_confirmation_token("create_work_order_for_equipment", equipment_id)
        wo_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        will_create_fault = fault_severity and wo_type in ("corrective", "emergency")
        return {
            "status": "success", "mode": "prepare", "confirmation_token": confirmation_token,
            "proposed_work_order": {
                "wo_number": wo_number, "equipment_id": equipment_id, "equipment_name": equipment_name,
                "equipment_status": equipment_status, "title": title, "description": description,
                "type": wo_type, "priority": priority, "status": "open",
                "assigned_to": assigned_to, "due_date": due_date,
            },
            "will_create_fault": bool(will_create_fault),
            "fault_severity": fault_severity if will_create_fault else None,
            "validation": {"equipment_exists": True, "type_valid": True},
        }

    wo_number = f"WO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
    wo_payload = {
        "yacht_id": yacht_id, "wo_number": wo_number, "equipment_id": equipment_id,
        "title": title, "description": description, "wo_type": wo_type, "priority": priority,
        "status": "open", "assigned_to": assigned_to, "due_date": due_date,
        "created_by": user_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ins = db.table("pms_work_orders").insert(wo_payload).execute()
    wo_id = (ins.data or [{}])[0].get("id")

    fault_id = None
    if fault_severity and wo_type in ("corrective", "emergency"):
        fault_code = f"FLT-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        try:
            fault_ins = db.table("pms_faults").insert({
                "yacht_id": yacht_id, "fault_code": fault_code, "equipment_id": equipment_id,
                "work_order_id": wo_id, "title": title, "severity": fault_severity,
                "status": "open", "detected_by": user_id,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
            fault_id = (fault_ins.data or [{}])[0].get("id")
            db.table("pms_work_orders").update({"fault_id": fault_id}).eq("id", wo_id).execute()
        except Exception as e:
            logger.warning(f"Failed to create fault: {e}")

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "create_work_order_for_equipment", "user_id": user_id,
        "old_values": None,
        "new_values": {"work_order_id": wo_id, "wo_number": wo_number, "fault_id": fault_id, "type": wo_type, "priority": priority},
        "signature": {}, **audit_meta,
    })

    return {"status": "success", "mode": "execute", "work_order_id": wo_id, "wo_number": wo_number, "equipment_id": equipment_id, "equipment_name": equipment_name, "fault_id": fault_id}


async def _link_part_to_equipment(**params) -> dict:
    """Link a part to equipment (BOM entry)."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    part_id = params["part_id"]
    quantity_required = params.get("quantity_required", 1)
    notes = params.get("notes")

    eq_result = db.table("pms_equipment").select("id").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    part_result = db.table("pms_parts").select("id, name").eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not part_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Part not found"}

    part_name = part_result.data.get("name")

    existing = db.table("pms_equipment_parts_bom").select("id").eq("equipment_id", equipment_id).eq("part_id", part_id).maybe_single().execute()
    if existing.data:
        return {"status": "error", "error_code": "DUPLICATE", "message": "Part is already linked to this equipment"}

    ins = db.table("pms_equipment_parts_bom").insert({
        "yacht_id": yacht_id, "equipment_id": equipment_id, "part_id": part_id,
        "quantity_required": quantity_required, "notes": notes,
        "created_by": user_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    bom_id = (ins.data or [{}])[0].get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_part_linked", "user_id": user_id,
        "old_values": None, "new_values": {"bom_id": bom_id, "part_id": part_id, "part_name": part_name}, "signature": {},
    })

    return {"status": "success", "bom_id": bom_id, "equipment_id": equipment_id, "part_id": part_id, "part_name": part_name}


async def _flag_equipment_attention(**params) -> dict:
    """Flag equipment for attention."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    attention_flag = params["attention_flag"]
    attention_reason = params.get("attention_reason")

    eq_result = db.table("pms_equipment").select("id, attention_flag").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_flag = eq_result.data.get("attention_flag", False)
    db.table("pms_equipment").update({
        "attention_flag": attention_flag,
        "attention_reason": attention_reason if attention_flag else None,
        "updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).execute()

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_attention_flagged", "user_id": user_id,
        "old_values": {"attention_flag": old_flag},
        "new_values": {"attention_flag": attention_flag, "attention_reason": attention_reason}, "signature": {},
    })

    if attention_flag:
        try:
            eq_name_r = db.table("pms_equipment").select("name").eq("id", equipment_id).maybe_single().execute()
            eq_name = (eq_name_r.data or {}).get("name", "Equipment") if eq_name_r else "Equipment"
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id, "p_user_id": user_id,
                "p_notification_type": "equipment_attention_flagged",
                "p_title": f"Follow up: {eq_name} flagged for attention",
                "p_body": attention_reason or "Equipment has been flagged — assign a responsible party and create a work order if needed.",
                "p_priority": "normal", "p_entity_type": "equipment", "p_entity_id": equipment_id,
                "p_cta_action_id": "create_work_order_for_equipment",
                "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:attention:{datetime.now(timezone.utc).date()}",
            }).execute()
        except Exception:
            pass

    return {"status": "success", "equipment_id": equipment_id, "attention_flag": attention_flag}


async def _decommission_equipment(**params) -> dict:
    """Decommission equipment (SIGNED action). Required: equipment_id, reason, signature."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    reason = params["reason"]
    signature = params["signature"]
    replacement_equipment_id = params.get("replacement_equipment_id")

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature"}

    eq_result = db.table("pms_equipment").select("id, name, status").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")
    equipment_name = eq_result.data.get("name")

    if old_status == "decommissioned":
        return {"status": "error", "error_code": "ALREADY_DECOMMISSIONED", "message": "Equipment is already decommissioned"}

    now = datetime.now(timezone.utc).isoformat()
    db.table("pms_equipment").update({
        "status": "decommissioned", "deletion_reason": reason,
        "deleted_by": user_id, "deleted_at": now, "updated_by": user_id, "updated_at": now,
    }).eq("id", equipment_id).execute()

    if replacement_equipment_id:
        try:
            db.table("pms_entity_links").insert({
                "yacht_id": yacht_id, "source_entity_type": "equipment", "source_entity_id": equipment_id,
                "target_entity_type": "equipment", "target_entity_id": replacement_equipment_id,
                "link_type": "replaced_by", "note": f"Decommissioned and replaced: {reason}",
                "created_by": user_id, "created_at": now,
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to create replacement link: {e}")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_decommissioned", "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": "decommissioned", "reason": reason},
        "signature": signature,
    })

    return {"status": "success", "equipment_id": equipment_id, "equipment_name": equipment_name, "decommissioned": True, "replacement_equipment_id": replacement_equipment_id}


async def _record_equipment_hours(**params) -> dict:
    """Record equipment running hours. Required: equipment_id, hours_reading."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    hours_reading = params["hours_reading"]
    reading_type = params.get("reading_type", "manual")
    notes = params.get("notes")

    try:
        hours_reading = float(hours_reading)
        if hours_reading < 0:
            raise ValueError("Hours must be positive")
    except (TypeError, ValueError):
        return {"status": "error", "error_code": "INVALID_HOURS", "message": "Hours reading must be a positive number"}

    eq_result = db.table("pms_equipment").select("id, name, running_hours").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_hours = eq_result.data.get("running_hours", 0) or 0

    ins = db.table("pms_equipment_hours_log").insert({
        "yacht_id": yacht_id, "equipment_id": equipment_id,
        "hours_reading": hours_reading, "reading_type": reading_type,
        "notes": notes, "source": "celeste",
        "recorded_by": user_id, "recorded_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    log_id = (ins.data or [{}])[0].get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_hours_recorded", "user_id": user_id,
        "old_values": {"running_hours": old_hours},
        "new_values": {"running_hours": hours_reading, "reading_type": reading_type}, "signature": {},
    })

    return {"status": "success", "log_id": log_id, "equipment_id": equipment_id, "hours_reading": hours_reading, "hours_delta": hours_reading - old_hours if old_hours else None}


async def _create_equipment(**params) -> dict:
    """Create new equipment. Required: name, category."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    name = params["name"]
    category = params["category"]
    manufacturer = params.get("manufacturer")
    model = params.get("model")
    serial_number = params.get("serial_number")
    location = params.get("location")
    parent_id = params.get("parent_id")
    running_hours = params.get("running_hours")

    if parent_id:
        parent_result = db.table("pms_equipment").select("id").eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not parent_result.data:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Parent equipment not found in this yacht"}

    ins = db.table("pms_equipment").insert({
        "yacht_id": yacht_id, "name": name, "category": category,
        "manufacturer": manufacturer, "model": model, "serial_number": serial_number,
        "location": location, "parent_id": parent_id, "running_hours": running_hours,
        "status": "operational", "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    equipment = (ins.data or [{}])[0]
    equipment_id = equipment.get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_created", "user_id": user_id,
        "old_values": None, "new_values": {"name": name, "category": category}, "signature": {},
    })

    _missing = []
    if not manufacturer: _missing.append("manufacturer")
    if not model: _missing.append("model")
    if not serial_number: _missing.append("serial number")
    if running_hours is None: _missing.append("running hours")
    if _missing and equipment_id:
        try:
            db.rpc("upsert_notification", {
                "p_yacht_id": yacht_id, "p_user_id": user_id,
                "p_notification_type": "equipment_record_incomplete",
                "p_title": f"Complete record: {name}",
                "p_body": f"Missing: {', '.join(_missing)}. Open the equipment card to fill in these details.",
                "p_priority": "low", "p_entity_type": "equipment", "p_entity_id": equipment_id,
                "p_cta_action_id": "view_equipment", "p_cta_payload": {"equipment_id": equipment_id},
                "p_idempotency_key": f"equip:{equipment_id}:incomplete:created",
            }).execute()
        except Exception:
            pass

    return {"status": "success", "equipment_id": equipment_id, "name": name, "category": category}


async def _assign_parent_equipment(**params) -> dict:
    """Assign parent equipment (set parent_id). Required: equipment_id, parent_id (or null to clear)."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    parent_id = params.get("parent_id")

    eq_result = db.table("pms_equipment").select("id, name, parent_id").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_parent_id = eq_result.data.get("parent_id")

    if parent_id:
        if parent_id == equipment_id:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Equipment cannot be its own parent"}
        parent_result = db.table("pms_equipment").select("id, name").eq("id", parent_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not parent_result.data:
            return {"status": "error", "error_code": "INVALID_PARENT", "message": "Parent equipment not found in this yacht"}

    db.table("pms_equipment").update({
        "parent_id": parent_id, "updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", equipment_id).execute()

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_parent_assigned", "user_id": user_id,
        "old_values": {"parent_id": old_parent_id}, "new_values": {"parent_id": parent_id}, "signature": {},
    })

    return {"status": "success", "equipment_id": equipment_id, "parent_id": parent_id, "previous_parent_id": old_parent_id}


async def _archive_equipment(**params) -> dict:
    """Archive equipment (status flip, reversible). Required: equipment_id, reason."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    reason = params["reason"]
    request_context = params.get("request_context")

    eq_result = db.table("pms_equipment").select("id, name, status").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")
    if old_status == "archived":
        return {"status": "error", "error_code": "ALREADY_ARCHIVED", "message": "Equipment is already archived"}
    if old_status == "decommissioned":
        return {"status": "error", "error_code": "CANNOT_ARCHIVE", "message": "Decommissioned equipment cannot be archived"}

    equipment_name = eq_result.data.get("name")
    now = datetime.now(timezone.utc).isoformat()
    db.table("pms_equipment").update({"status": "archived", "updated_by": user_id, "updated_at": now}).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_archived", "user_id": user_id,
        "old_values": {"status": old_status}, "new_values": {"status": "archived", "reason": reason},
        "signature": {}, **audit_meta,
    })

    return {"status": "success", "equipment_id": equipment_id, "equipment_name": equipment_name, "archived": True, "old_status": old_status, "new_status": "archived"}


async def _restore_archived_equipment(**params) -> dict:
    """Restore archived equipment (SIGNED). Required: equipment_id, signature."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    signature = params["signature"]
    restore_reason = params.get("restore_reason", "Restored by authorized user")
    request_context = params.get("request_context")

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature"}

    eq_result = db.table("pms_equipment").select("id, name, status").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_status = eq_result.data.get("status")
    if old_status != "archived":
        return {"status": "error", "error_code": "NOT_ARCHIVED", "message": f"Equipment is not archived (current status: {old_status})"}

    equipment_name = eq_result.data.get("name")
    now = datetime.now(timezone.utc).isoformat()
    db.table("pms_equipment").update({"status": "in_service", "updated_by": user_id, "updated_at": now}).eq("id", equipment_id).execute()

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_restored", "user_id": user_id,
        "old_values": {"status": old_status}, "new_values": {"status": "in_service", "restore_reason": restore_reason},
        "signature": signature, **audit_meta,
    })

    return {"status": "success", "equipment_id": equipment_id, "equipment_name": equipment_name, "restored": True, "old_status": old_status, "new_status": "in_service"}


async def _get_open_faults_for_equipment(**params) -> dict:
    """Get open faults for equipment. Required: equipment_id."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    equipment_id = params["equipment_id"]
    limit = params.get("limit", 20)
    offset = params.get("offset", 0)
    include_historical = params.get("include_historical", False)

    eq_result = db.table("pms_equipment").select("id, name").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")
    query = db.table("pms_faults").select(
        "id, fault_code, title, severity, status, detected_at, created_at", count="exact"
    ).eq("yacht_id", yacht_id).eq("equipment_id", equipment_id)

    if not include_historical:
        query = query.not_.in_("status", ["closed", "resolved", "dismissed"])

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    faults = result.data or []
    total_count = result.count or len(faults)

    return {
        "status": "success", "equipment_id": equipment_id, "equipment_name": equipment_name,
        "faults": faults,
        "summary": {
            "total": total_count,
            "critical": len([f for f in faults if f.get("severity") == "critical"]),
            "major": len([f for f in faults if f.get("severity") == "major"]),
            "minor": len([f for f in faults if f.get("severity") == "minor"]),
        },
        "include_historical": include_historical,
        "pagination": {"offset": offset, "limit": limit, "total": total_count},
    }


async def _get_related_entities_for_equipment(**params) -> dict:
    """Get related entities for equipment. Required: equipment_id."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    equipment_id = params["equipment_id"]
    entity_types = params.get("entity_types")

    eq_result = db.table("pms_equipment").select("id, name").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    equipment_name = eq_result.data.get("name")

    outgoing_query = db.table("pms_entity_links").select(
        "id, target_entity_type, target_entity_id, relationship_type, notes, created_at"
    ).eq("yacht_id", yacht_id).eq("source_entity_type", "equipment").eq("source_entity_id", equipment_id)
    incoming_query = db.table("pms_entity_links").select(
        "id, source_entity_type, source_entity_id, relationship_type, notes, created_at"
    ).eq("yacht_id", yacht_id).eq("target_entity_type", "equipment").eq("target_entity_id", equipment_id)

    if entity_types:
        outgoing_query = outgoing_query.in_("target_entity_type", entity_types)
        incoming_query = incoming_query.in_("source_entity_type", entity_types)

    outgoing_result = outgoing_query.execute()
    incoming_result = incoming_query.execute()

    related = []
    for link in (outgoing_result.data or []):
        related.append({"link_id": link["id"], "entity_type": link["target_entity_type"], "entity_id": link["target_entity_id"], "relationship": link.get("relationship_type", "related"), "direction": "outgoing", "notes": link.get("notes"), "created_at": link.get("created_at")})
    for link in (incoming_result.data or []):
        related.append({"link_id": link["id"], "entity_type": link["source_entity_type"], "entity_id": link["source_entity_id"], "relationship": link.get("relationship_type", "related"), "direction": "incoming", "notes": link.get("notes"), "created_at": link.get("created_at")})

    by_type: dict = {}
    for r in related:
        t = r["entity_type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)

    return {"status": "success", "equipment_id": equipment_id, "equipment_name": equipment_name, "related_entities": related, "by_type": by_type, "total_count": len(related)}


async def _add_entity_link(**params) -> dict:
    """Add entity link (cross-entity relationship)."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    source_entity_type = params["source_entity_type"]
    source_entity_id = params["source_entity_id"]
    target_entity_type = params["target_entity_type"]
    target_entity_id = params["target_entity_id"]
    relationship_type = params.get("relationship_type", "related")
    notes = params.get("notes")

    if source_entity_type == target_entity_type and source_entity_id == target_entity_id:
        return {"status": "error", "error_code": "INVALID_LINK", "message": "Cannot link entity to itself"}

    existing = db.table("pms_entity_links").select("id").eq("yacht_id", yacht_id).eq(
        "source_entity_type", source_entity_type).eq("source_entity_id", source_entity_id).eq(
        "target_entity_type", target_entity_type).eq("target_entity_id", target_entity_id).maybe_single().execute()
    if existing.data:
        return {"status": "error", "error_code": "DUPLICATE_LINK", "message": "Link already exists"}

    ins = db.table("pms_entity_links").insert({
        "yacht_id": yacht_id, "source_entity_type": source_entity_type, "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type, "target_entity_id": target_entity_id,
        "relationship_type": relationship_type, "notes": notes,
        "created_by": user_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    link_id = (ins.data or [{}])[0].get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": source_entity_type, "entity_id": source_entity_id,
        "action": "entity_link_created", "user_id": user_id,
        "old_values": None,
        "new_values": {"link_id": link_id, "target_entity_type": target_entity_type, "target_entity_id": target_entity_id, "relationship_type": relationship_type},
        "signature": {},
    })

    return {"status": "success", "link_id": link_id, "source_entity_type": source_entity_type, "source_entity_id": source_entity_id, "target_entity_type": target_entity_type, "target_entity_id": target_entity_id, "relationship_type": relationship_type}


async def _link_document_to_equipment(**params) -> dict:
    """Link a doc_metadata entry to equipment. Required: equipment_id, document_id."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    document_id = params["document_id"]
    description = params.get("description")

    eq_result = db.table("pms_equipment").select("id").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result or not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    doc_result = db.table("doc_metadata").select("id, filename, storage_path, content_type, size_bytes").eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not doc_result or not doc_result.data:
        return {"status": "error", "error_code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}

    doc = doc_result.data
    existing = db.table("pms_equipment_documents").select("id").eq("equipment_id", equipment_id).eq("document_id", document_id).maybe_single().execute()
    if existing and existing.data:
        return {"status": "error", "error_code": "ALREADY_LINKED", "message": "Document is already linked to this equipment"}

    ins = db.table("pms_equipment_documents").insert({
        "yacht_id": yacht_id, "equipment_id": equipment_id, "document_id": document_id,
        "storage_path": doc.get("storage_path"), "filename": doc.get("filename"),
        "original_filename": doc.get("filename"), "mime_type": doc.get("content_type"),
        "file_size": doc.get("size_bytes"), "document_type": "general",
        "description": description, "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    eq_doc_id = (ins.data or [{}])[0].get("id")

    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "equipment_document_linked", "user_id": user_id,
        "old_values": None, "new_values": {"equipment_document_id": eq_doc_id, "document_id": document_id}, "signature": {},
    })

    return {"status": "success", "equipment_document_id": eq_doc_id, "equipment_id": equipment_id, "document_id": document_id}


async def _attach_image_with_comment(**params) -> dict:
    """Attach image to equipment with comment. Required: equipment_id, storage_path, comment."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    comment = params["comment"]
    tags = params.get("tags", [])
    request_context = params.get("request_context")
    filename = params.get("filename")
    original_filename = params.get("original_filename")
    mime_type = params.get("mime_type")
    file_size = params.get("file_size")
    storage_path = params.get("storage_path")

    if not storage_path:
        return {"status": "error", "error_code": "MISSING_FILE", "message": "File upload required"}

    path_valid, path_error = validate_storage_path_for_equipment(yacht_id, equipment_id, storage_path)
    if not path_valid:
        return {"status": "error", "error_code": "INVALID_STORAGE_PATH", "message": path_error}

    eq_result = db.table("pms_equipment").select("id").eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    ins = db.table("pms_equipment_documents").insert({
        "yacht_id": yacht_id, "equipment_id": equipment_id, "storage_path": storage_path,
        "filename": filename, "original_filename": original_filename, "mime_type": mime_type,
        "file_size": file_size, "document_type": "photo", "comment": comment,
        "tags": tags if tags else None, "uploaded_by": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    doc_id = (ins.data or [{}])[0].get("id")

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "attach_image_with_comment", "user_id": user_id,
        "old_values": None,
        "new_values": {"document_id": doc_id, "filename": original_filename, "comment": (comment or "")[:100]},
        "signature": {}, **audit_meta,
    })

    return {"status": "success", "document_id": doc_id, "equipment_id": equipment_id, "storage_path": storage_path, "comment": comment}


async def _decommission_and_replace_equipment(**params) -> dict:
    """Decommission equipment and create replacement (SIGNED, atomic, prepare/execute)."""
    db = params["db_client"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params["equipment_id"]
    reason = params["reason"]
    signature = params.get("signature")
    request_context = params.get("request_context")
    replacement_name = params.get("replacement_name")
    replacement_manufacturer = params.get("replacement_manufacturer")
    replacement_model = params.get("replacement_model")
    replacement_serial_number = params.get("replacement_serial_number")

    if not replacement_name:
        return {"status": "error", "error_code": "MISSING_REPLACEMENT_NAME", "message": "replacement_name is required"}

    eq_result = db.table("pms_equipment").select(
        "id, name, status, manufacturer, model, serial_number, system_type, location"
    ).eq("id", equipment_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not eq_result.data:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Equipment not found"}

    old_equipment = eq_result.data
    old_status = old_equipment.get("status")

    if old_status == "decommissioned":
        return {"status": "error", "error_code": "ALREADY_DECOMMISSIONED", "message": "Equipment is already decommissioned"}

    if is_prepare_mode(params):
        confirmation_token = generate_confirmation_token("decommission_and_replace", equipment_id)
        return {
            "status": "success", "mode": "prepare", "confirmation_token": confirmation_token,
            "proposed_changes": {
                "old_equipment": {"id": equipment_id, "name": old_equipment["name"], "current_status": old_status, "new_status": "decommissioned"},
                "replacement_equipment": {
                    "name": replacement_name,
                    "manufacturer": replacement_manufacturer or old_equipment.get("manufacturer"),
                    "model": replacement_model or old_equipment.get("model"),
                    "serial_number": replacement_serial_number,
                    "system_type": old_equipment.get("system_type"),
                    "location": old_equipment.get("location"),
                    "status": "operational",
                },
            },
            "validation": {"signature_required": True, "roles_allowed": ["captain", "manager"]},
            "warning": f"This will permanently decommission '{old_equipment['name']}' and create replacement '{replacement_name}'.",
        }

    if not signature or not isinstance(signature, dict):
        return {"status": "error", "error_code": "SIGNATURE_REQUIRED", "message": "This action requires a signature for execution"}

    now = datetime.now(timezone.utc).isoformat()
    db.table("pms_equipment").update({
        "status": "decommissioned", "deletion_reason": reason,
        "deleted_by": user_id, "deleted_at": now, "updated_by": user_id, "updated_at": now,
    }).eq("id", equipment_id).execute()

    replacement_result = db.table("pms_equipment").insert({
        "yacht_id": yacht_id, "name": replacement_name,
        "manufacturer": replacement_manufacturer or old_equipment.get("manufacturer"),
        "model": replacement_model or old_equipment.get("model"),
        "serial_number": replacement_serial_number,
        "system_type": old_equipment.get("system_type"),
        "location": old_equipment.get("location"),
        "status": "operational", "created_at": now,
    }).execute()
    replacement_equipment = (replacement_result.data or [{}])[0]
    replacement_id = replacement_equipment.get("id")

    try:
        db.table("pms_entity_links").insert({
            "yacht_id": yacht_id, "source_entity_type": "equipment", "source_entity_id": equipment_id,
            "target_entity_type": "equipment", "target_entity_id": replacement_id,
            "relationship_type": "replaced_by", "notes": f"Decommissioned and replaced: {reason}",
            "created_by": user_id, "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to create replacement link: {e}")

    audit_meta = extract_audit_metadata(request_context)
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": equipment_id,
        "action": "decommission_and_replace_equipment", "user_id": user_id,
        "old_values": {"status": old_status},
        "new_values": {"status": "decommissioned", "reason": reason, "replacement_id": replacement_id, "replacement_name": replacement_name},
        "signature": signature, **audit_meta,
    })
    _write_audit_log(db, {
        "yacht_id": yacht_id, "entity_type": "equipment", "entity_id": replacement_id,
        "action": "create_equipment", "user_id": user_id,
        "old_values": None, "new_values": {"name": replacement_name, "replaces_equipment_id": equipment_id},
        "signature": {}, **audit_meta,
    })

    return {
        "status": "success", "mode": "execute",
        "old_equipment_id": equipment_id, "old_equipment_name": old_equipment["name"],
        "replacement_equipment_id": replacement_id, "replacement_equipment_name": replacement_name,
        "decommissioned": True, "decommissioned_at": now,
    }


async def _view_maintenance_history(**params) -> dict:
    """
    View maintenance/work order history for equipment.
    Thin adapter: delegates to view_equipment_history which uses Phase 5 contract.
    """
    # view_equipment_history uses payload dict not **kwargs — bridge the gap
    equipment_id = params.get("equipment_id") or params.get("entity_id")
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    db = params["db_client"]

    return await view_equipment_history(
        payload={"equipment_id": equipment_id},
        context={},
        yacht_id=yacht_id,
        user_id=user_id,
        user_context={},
        db_client=db,
    )


HANDLERS: dict = {
    # Phase 5 flat-function handlers (original 10)
    "update_equipment_status": update_equipment_status,
    "view_equipment":          view_equipment,
    "view_equipment_detail":   view_equipment_detail,
    "view_equipment_details":  view_equipment_detail,   # alias — same function object
    "view_equipment_history":  view_equipment_history,
    "view_equipment_parts":    view_equipment_parts,
    "view_linked_faults":      view_linked_faults,
    "view_equipment_manual":   view_equipment_manual,
    "add_equipment_note":      add_equipment_note,
    "suggest_parts":           suggest_parts,
    # Phase C adapter handlers (merged from equipment_handlers.py)
    "set_equipment_status":                  _set_equipment_status,
    "attach_file_to_equipment":              _attach_file_to_equipment,
    "create_work_order_for_equipment":       _create_work_order_for_equipment,
    "link_part_to_equipment":                _link_part_to_equipment,
    "flag_equipment_attention":              _flag_equipment_attention,
    "decommission_equipment":                _decommission_equipment,
    "record_equipment_hours":                _record_equipment_hours,
    "create_equipment":                      _create_equipment,
    "assign_parent_equipment":               _assign_parent_equipment,
    "archive_equipment":                     _archive_equipment,
    "restore_archived_equipment":            _restore_archived_equipment,
    "get_open_faults_for_equipment":         _get_open_faults_for_equipment,
    "get_related_entities_for_equipment":    _get_related_entities_for_equipment,
    "add_entity_link":                       _add_entity_link,
    "link_document_to_equipment":            _link_document_to_equipment,
    "attach_image_with_comment":             _attach_image_with_comment,
    "decommission_and_replace_equipment":    _decommission_and_replace_equipment,
    "view_maintenance_history":              _view_maintenance_history,
}
