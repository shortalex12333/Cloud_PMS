# routes/handlers/equipment_handler.py
#
# Phase 5 dispatch handlers — equipment domain (10 actions).
# Translated from p0_actions_routes.py elif blocks.
#
# Handler contract:
#   async def handler(payload, context, yacht_id, user_id, user_context, db_client) -> dict

from datetime import datetime, timezone
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


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


HANDLERS: dict = {
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
}
