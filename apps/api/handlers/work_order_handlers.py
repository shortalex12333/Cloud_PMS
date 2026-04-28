"""
handlers/work_order_handlers.py — Work Order domain, single source of truth.

Consolidates all WO handler logic that was spread across:
  routes/handlers/work_order_handler.py
  routes/handlers/wo_completion_handler.py
  routes/handlers/checklist_handler.py

No delegation chains. Every action hits the DB in ≤1 hop from this file.

DB tables used by this domain:
  pms_work_orders          — primary WO record
  pms_work_order_notes     — notes / hours entries
  pms_work_order_parts     — part linkage (relational, upsert-safe)
  pms_work_order_checklist — flat checklist items per WO (NOT pms_checklist_items)
  pms_faults               — linked fault (create_from_fault, archive cascade)
  pms_parts                — part validation + stock check
  auth_users_profiles      — crew dept validation, note FK fallback
  auth_users_roles         — role-gating for signed mutations
  pms_audit_log            — signed action audit trail
  ledger_events            — all mutations

Column note for pms_work_order_checklist:
  id, yacht_id, work_order_id, title, description, sequence,
  is_completed, completed_by, completed_at, is_required,
  requires_photo, requires_signature, created_by, created_at,
  item_type, unit, actual_value   ← add via migration if absent
"""
from datetime import datetime, timezone
from typing import Optional
import uuid as uuid_module
import logging

from fastapi import HTTPException
from supabase import Client

from handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _audit(
    db_client: Client,
    yacht_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    signature: Optional[dict] = None,
) -> None:
    """Write to pms_audit_log; signature column is NOT NULL, default to {}."""
    try:
        db_client.table("pms_audit_log").insert({
            "yacht_id": yacht_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "old_values": old_values,
            "new_values": new_values,
            "signature": signature if signature else {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"[Audit] Failed for {action}/{entity_id}: {e}")


def _ledger(
    db_client: Client,
    yacht_id: str,
    user_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    user_role: str,
    summary: str,
    entity_name: str = "",
    previous_state: Optional[dict] = None,
    new_state: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Fire-and-forget ledger write. Never raises."""
    try:
        event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type=event_type,
            entity_type=entity_type, entity_id=entity_id, action=action,
            user_role=user_role, change_summary=summary, entity_name=entity_name,
            previous_state=previous_state, new_state=new_state, metadata=metadata,
        )
        db_client.table("ledger_events").insert(event).execute()
    except Exception as e:
        if "204" not in str(e):
            logger.warning(f"[Ledger] Failed for {action}/{entity_id}: {e}")


_PRIORITY_MAP = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}

def _map_priority(raw: str) -> str:
    return _PRIORITY_MAP.get(raw, raw if raw in ("routine", "emergency", "critical") else "routine")


def _wo_not_found() -> dict:
    return {"status": "error", "error_code": "NOT_FOUND", "message": "Work order not found"}


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

async def create_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    priority = _map_priority(payload.get("priority", "routine"))

    # Crew department gate
    if user_context.get("role") == "crew":
        wo_dept = payload.get("department")
        if not wo_dept:
            raise HTTPException(status_code=400, detail="department is required for crew")
        try:
            prof = db_client.table("auth_users_profiles").select("metadata").eq("id", user_id).eq("yacht_id", yacht_id).maybe_single().execute()
            user_dept = (prof.data or {}).get("metadata", {}).get("department", "").lower() if prof.data else ""
        except Exception:
            user_dept = ""
        if not user_dept:
            raise HTTPException(status_code=403, detail="Crew user must have a department assigned")
        if user_dept != wo_dept.lower():
            raise HTTPException(status_code=403, detail=f"Crew can only create work orders for their department (user: {user_dept}, wo: {wo_dept.lower()})")

    # Accept both 'type' and 'work_order_type' from callers
    wo_type = payload.get("work_order_type") or payload.get("type") or "corrective"
    status = payload.get("status", "planned")
    if status not in ("draft", "planned", "open", "in_progress"):
        status = "planned"

    wo_data: dict = {
        "yacht_id": yacht_id,
        "title": title,
        "description": payload.get("description", ""),
        "priority": priority,
        "status": status,
        "work_order_type": wo_type,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Optional FK fields — only set if non-empty (prevents FK violation on empty string)
    for field in ("equipment_id", "assigned_to", "fault_id"):
        val = payload.get(field)
        if val:
            wo_data[field] = val
    # Optional scalar fields
    for field in ("system_name", "due_date", "severity", "frequency"):
        val = payload.get(field)
        if val:
            wo_data[field] = val

    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}

    wo_id = wo_result.data[0]["id"]
    await _audit(db_client, yacht_id, "create_work_order", "work_order", wo_id, user_id, new_values=wo_data)
    _ledger(db_client, yacht_id, user_id, "create", "work_order", wo_id, "create_work_order",
            user_context.get("role", ""), f"Work order created: {title}", entity_name=title,
            new_state={"title": title, "status": status, "priority": priority, "work_order_type": wo_type})

    # Pre-create a note if provided (e.g. from CreateWorkOrderModal initial note)
    note_text = payload.get("note_text")
    if note_text and status != "draft":
        try:
            db_client.table("pms_work_order_notes").insert({
                "work_order_id": wo_id,
                "note_text": note_text,
                "note_type": "general",
                "created_by": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Initial note insert failed for {wo_id}: {e}")

    return {"status": "success", "work_order_id": wo_id, "message": "Work order created", "_ledger_written": True}


async def create_work_order_from_fault(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Create WO from fault — requires wet signature from captain/manager."""
    signature = payload.get("signature")
    if not signature or not isinstance(signature, dict):
        raise HTTPException(status_code=400, detail={"status": "error", "error_code": "signature_required",
                                                      "message": "Signature payload required for SIGNED action"})
    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type"}
    missing = required_sig_keys - set(signature.keys())
    if missing:
        raise HTTPException(status_code=400, detail={"status": "error", "error_code": "invalid_signature",
                                                      "message": f"Invalid signature: missing keys {sorted(missing)}"})
    if signature.get("role_at_signing") not in ("captain", "manager"):
        raise HTTPException(status_code=403, detail={"status": "error", "error_code": "invalid_signer_role",
                                                      "message": "Only captain/manager may sign this action"})

    fault_id = payload.get("fault_id")
    fault = db_client.table("pms_faults").select("*").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    if not fault.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    existing = db_client.table("pms_work_orders").select("id").eq("fault_id", fault_id).execute()
    if existing.data and not payload.get("override_duplicate", False):
        return {"status": "error", "error_code": "DUPLICATE_WO_EXISTS", "message": "Work order already exists for this fault"}

    wo_data = {
        "yacht_id": yacht_id,
        "fault_id": fault_id,
        "equipment_id": payload.get("equipment_id") or fault.data.get("equipment_id"),
        "title": payload.get("title", fault.data.get("title", "Work order from fault")),
        "description": payload.get("description", fault.data.get("description", "")),
        "priority": _map_priority(payload.get("priority", "routine")),
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}

    wo_id = wo_result.data[0]["id"]
    db_client.table("pms_faults").update({
        "work_order_id": wo_id, "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    await _audit(db_client, yacht_id, "create_work_order_from_fault", "work_order", wo_id, user_id,
                 new_values=wo_result.data[0], signature=signature)
    _ledger(db_client, yacht_id, user_id, "create", "work_order", wo_id, "create_work_order_from_fault",
            user_context.get("role", ""), "Work order created from fault")
    return {"status": "success", "work_order_id": wo_id, "message": "Work order created from fault"}


async def create_work_order_for_equipment(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id") or context.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    priority = payload.get("priority", "routine")
    if priority not in ("routine", "critical"):
        priority = "routine"
    wo_data = {
        "id": str(uuid_module.uuid4()),
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "title": payload.get("title", "Work Order"),
        "description": payload.get("description", ""),
        "priority": priority,
        "work_order_type": payload.get("type", "corrective"),
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "CREATE_FAILED", "message": "Failed to create work order"}
    wo_id = wo_result.data[0]["id"]
    await _audit(db_client, yacht_id, "create_work_order_for_equipment", "work_order", wo_id, user_id,
                 new_values=wo_data)
    _ledger(db_client, yacht_id, user_id, "create", "work_order", wo_id, "create_work_order_for_equipment",
            user_context.get("role", ""), f"Work order created for equipment {equipment_id}")
    return {"status": "success", "work_order_id": wo_id, "message": "Work order created for equipment"}


# ─────────────────────────────────────────────────────────────────────────────
# STATUS MUTATIONS
# ─────────────────────────────────────────────────────────────────────────────

async def update_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    prev = (db_client.table("pms_work_orders").select("id, title, description, priority, status")
            .eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute().data or {})

    update_data = {"updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.get("title"):
        update_data["title"] = payload["title"]
    if payload.get("description") is not None:
        update_data["description"] = payload["description"]
    if payload.get("priority"):
        update_data["priority"] = _map_priority(payload["priority"])
    if payload.get("status"):
        update_data["status"] = payload["status"]
    if payload.get("due_date"):
        update_data["due_date"] = payload["due_date"]

    res = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not res.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update work order"}
    await _audit(db_client, yacht_id, "update_work_order", "work_order", work_order_id, user_id,
                 old_values={k: prev.get(k) for k in ("title", "description", "priority", "status")},
                 new_values=update_data)
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "update_work_order",
            user_context.get("role", ""), "Work order updated", entity_name=prev.get("title", ""))
    return {"status": "success", "message": "Work order updated", "_ledger_written": True}


async def assign_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    assigned_to = payload.get("assigned_to")
    prev = (db_client.table("pms_work_orders").select("id, title, assigned_to")
            .eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute().data or {})

    res = db_client.table("pms_work_orders").update({
        "assigned_to": assigned_to,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not res.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to assign work order"}
    await _audit(db_client, yacht_id, "assign_work_order", "work_order", work_order_id, user_id,
                 old_values={"assigned_to": prev.get("assigned_to")},
                 new_values={"assigned_to": assigned_to})
    _ledger(db_client, yacht_id, user_id, "assignment", "work_order", work_order_id, "assign_work_order",
            user_context.get("role", ""), f"Assigned: {prev.get('assigned_to')} → {assigned_to}",
            entity_name=prev.get("title", ""))
    return {"status": "success", "message": "Work order assigned"}


async def start_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    prev = (db_client.table("pms_work_orders").select("id, title, status")
            .eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute().data or {})
    res = db_client.table("pms_work_orders").update({
        "status": "in_progress", "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not res.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to start work order"}
    await _audit(db_client, yacht_id, "start_work_order", "work_order", work_order_id, user_id,
                 old_values={"status": prev.get("status")}, new_values={"status": "in_progress"})
    _ledger(db_client, yacht_id, user_id, "status_change", "work_order", work_order_id, "start_work_order",
            user_context.get("role", ""), f"Status: {prev.get('status')} → in_progress",
            entity_name=prev.get("title", ""))
    return {"status": "success", "message": "Work order started"}


async def cancel_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    prev = (db_client.table("pms_work_orders").select("id, title, status")
            .eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute().data or {})
    res = db_client.table("pms_work_orders").update({
        "status": "cancelled", "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not res.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to cancel work order"}
    await _audit(db_client, yacht_id, "cancel_work_order", "work_order", work_order_id, user_id,
                 old_values={"status": prev.get("status")}, new_values={"status": "cancelled"})
    _ledger(db_client, yacht_id, user_id, "status_change", "work_order", work_order_id, "cancel_work_order",
            user_context.get("role", ""), f"Status: {prev.get('status')} → cancelled",
            entity_name=prev.get("title", ""))
    return {"status": "success", "message": "Work order cancelled"}


async def close_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    prev = (db_client.table("pms_work_orders").select("id, title, status")
            .eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute().data or {})
    update_data = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.get("completion_notes"):
        update_data["completion_notes"] = payload["completion_notes"]
    res = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not res.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close work order"}
    await _audit(db_client, yacht_id, "close_work_order", "work_order", work_order_id, user_id,
                 old_values={"status": prev.get("status")}, new_values={"status": "completed"})
    _ledger(db_client, yacht_id, user_id, "status_change", "work_order", work_order_id, "close_work_order",
            user_context.get("role", ""), f"Status: {prev.get('status')} → completed",
            entity_name=prev.get("title", ""))
    return {"status": "success", "message": "Work order closed", "_ledger_written": True}


# ─────────────────────────────────────────────────────────────────────────────
# SIGNED MUTATIONS (inlined from WorkOrderMutationHandlers)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_signature(signature: Optional[dict], user_id: str, required_keys: set) -> None:
    """Raise 400 if signature is missing or invalid."""
    if not signature or not isinstance(signature, dict):
        raise HTTPException(status_code=400, detail="signature is required")
    missing = required_keys - set(signature.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"invalid signature payload: missing required fields {sorted(missing)}")


async def mark_work_order_complete(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Mark WO complete, deduct parts from inventory. Requires signature."""
    work_order_id = payload.get("work_order_id")
    completion_notes = payload.get("completion_notes")
    signature = payload.get("signature")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not completion_notes:
        raise HTTPException(status_code=400, detail="completion_notes is required")
    _validate_signature(signature, user_id, {"signed_at", "user_id", "role_at_signing", "signature_type"})

    if signature.get("user_id") != user_id:
        return {"status": "error", "error_code": "INVALID_SIGNATURE", "message": "Signature does not match user"}

    wo_result = db_client.table("pms_work_orders").select("id, wo_number, status").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "WO_NOT_FOUND", "message": f"Work order not found: {work_order_id}"}
    wo = wo_result.data
    if wo["status"] in ("completed", "closed", "cancelled"):
        return {"status": "error", "error_code": "WO_CLOSED", "message": f"Work order is already {wo['status']}"}
    if len(completion_notes.strip()) < 10:
        return {"status": "error", "error_code": "VALIDATION_ERROR", "message": "Completion notes must be at least 10 characters"}

    # Deduct parts from inventory
    inventory_updates = []
    for part_usage in (payload.get("parts_used") or []):
        part_id = part_usage["part_id"]
        qty_used = int(part_usage["quantity_used"])
        part_result = db_client.table("pms_parts").select("id, name, part_number, quantity_on_hand").eq("id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not part_result.data:
            return {"status": "error", "error_code": "PART_NOT_FOUND", "message": f"Part not found: {part_id}"}
        part = part_result.data
        deduct = db_client.rpc("deduct_part_inventory", {
            "p_yacht_id": yacht_id, "p_part_id": part_id, "p_quantity": qty_used,
            "p_work_order_id": work_order_id, "p_equipment_id": None,
            "p_usage_reason": "work_order", "p_notes": f"Used for {wo.get('wo_number', wo['id'])}",
            "p_used_by": user_id,
        }).execute()
        if not deduct.data:
            return {"status": "error", "error_code": "INSUFFICIENT_STOCK", "message": f"Insufficient stock for {part['name']}"}
        inventory_updates.append({"part_id": part_id, "part_name": part["name"], "quantity_deducted": qty_used})

    completed_at = datetime.now(timezone.utc).isoformat()
    update_data = {"status": "completed", "completed_at": completed_at, "completed_by": user_id, "completion_notes": completion_notes}
    wo_update = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not wo_update.data:
        return {"status": "error", "error_code": "INTERNAL_ERROR", "message": "Failed to update work order"}

    await _audit(db_client, yacht_id, "mark_work_order_complete", "work_order", work_order_id, user_id,
                 old_values={"status": wo["status"]}, new_values={**update_data, "parts_deducted": inventory_updates},
                 signature=signature)
    _ledger(db_client, yacht_id, user_id, "status_change", "work_order", work_order_id, "mark_work_order_complete",
            user_context.get("role", ""), "Work order marked as complete",
            metadata={"completion_notes": completion_notes, "parts_used_count": len(inventory_updates)})

    return {"status": "success", "action": "mark_work_order_complete",
            "result": {"work_order": {**update_data, "id": work_order_id}, "inventory_updates": inventory_updates},
            "message": f"Work order marked as complete"}


async def reassign_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Reassign WO to different crew. Requires HoD signature."""
    signature = payload.get("signature")
    _validate_signature(signature, user_id, {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"})
    if signature.get("user_id") != user_id:
        return {"status": "error", "error_code": "INVALID_SIGNATURE", "message": "Signature does not match user"}

    work_order_id = payload.get("work_order_id")
    assignee_id = payload.get("assignee_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not assignee_id:
        raise HTTPException(status_code=400, detail="assignee_id is required")

    # Role gate
    role_row = db_client.table("auth_users_roles").select("role").eq("user_id", user_id).eq("yacht_id", yacht_id).eq("is_active", True).limit(1).execute()
    user_role_db = (role_row.data[0]["role"] if role_row.data else "") or ""
    if user_role_db not in ("captain", "chief_engineer", "chief_officer", "purser", "manager"):
        return {"status": "error", "error_code": "UNAUTHORIZED", "message": "Only HOD roles can reassign work orders"}

    wo_result = db_client.table("pms_work_orders").select("id, wo_number, status, assigned_to").eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "WO_NOT_FOUND", "message": f"Work order not found: {work_order_id}"}
    wo = wo_result.data[0]
    if wo["status"] in ("completed", "closed", "cancelled"):
        return {"status": "error", "error_code": "WO_CLOSED", "message": f"Cannot reassign {wo['status']} work order"}

    assignee = db_client.table("auth_users_profiles").select("id, name").eq("id", assignee_id).eq("yacht_id", yacht_id).eq("is_active", True).limit(1).execute()
    if not assignee.data:
        return {"status": "error", "error_code": "ASSIGNEE_NOT_FOUND", "message": "New assignee not found or not on this yacht"}
    new_assignee_name = assignee.data[0].get("name", "Unknown")

    update_result = db_client.table("pms_work_orders").update({
        "assigned_to": assignee_id, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user_id,
    }).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not update_result.data:
        return {"status": "error", "error_code": "INTERNAL_ERROR", "message": "Failed to update work order"}

    await _audit(db_client, yacht_id, "reassign_work_order", "work_order", work_order_id, user_id,
                 old_values={"assigned_to": wo.get("assigned_to")},
                 new_values={"assigned_to": assignee_id, "assignee_name": new_assignee_name, "reason": payload.get("reason")},
                 signature=signature)
    _ledger(db_client, yacht_id, user_id, "assignment", "work_order", work_order_id, "reassign_work_order",
            user_context.get("role", ""), f"Work order reassigned to {new_assignee_name}",
            metadata={"new_assignee_id": assignee_id, "reason": payload.get("reason")})
    return {"status": "success", "action": "reassign_work_order",
            "result": {"work_order": update_result.data[0], "previous_assignee_id": wo.get("assigned_to"), "reason": payload.get("reason")},
            "message": f"Work order reassigned to {new_assignee_name}"}


async def archive_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Soft-delete WO. Requires Captain/HOD signature."""
    signature = payload.get("signature")
    _validate_signature(signature, user_id, {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"})
    if signature.get("user_id") != user_id:
        return {"status": "error", "error_code": "INVALID_SIGNATURE", "message": "Signature does not match user"}

    work_order_id = payload.get("work_order_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    deletion_reason = payload.get("deletion_reason", "Archived")
    if len(deletion_reason.strip()) < 5:
        return {"status": "error", "error_code": "VALIDATION_ERROR", "message": "Deletion reason must be at least 5 characters"}

    role_row = db_client.table("auth_users_roles").select("role").eq("user_id", user_id).eq("yacht_id", yacht_id).eq("is_active", True).limit(1).execute()
    user_role_db = (role_row.data[0]["role"] if role_row.data else "") or ""
    if user_role_db not in ("captain", "chief_engineer", "chief_officer", "purser", "manager"):
        return {"status": "error", "error_code": "UNAUTHORIZED", "message": "Only Captain/HOD roles can archive work orders"}

    wo_result = db_client.table("pms_work_orders").select("id, wo_number, status, fault_id").eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "WO_NOT_FOUND", "message": f"Work order not found: {work_order_id}"}
    wo = wo_result.data[0]
    if wo["status"] in ("completed", "closed", "cancelled"):
        return {"status": "error", "error_code": "WO_ALREADY_TERMINAL", "message": f"Work order is already {wo['status']}"}

    now = datetime.now(timezone.utc).isoformat()
    update_data = {"status": "cancelled", "deleted_at": now, "deleted_by": user_id,
                   "deletion_reason": deletion_reason, "updated_at": now, "updated_by": user_id}
    update_result = db_client.table("pms_work_orders").update(update_data).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    if not update_result.data:
        return {"status": "error", "error_code": "INTERNAL_ERROR", "message": "Failed to archive work order"}

    archived_wo = update_result.data[0]
    await _audit(db_client, yacht_id, "archive_work_order", "work_order", work_order_id, user_id,
                 old_values={"status": wo["status"]}, new_values=update_data, signature=signature)
    _ledger(db_client, yacht_id, user_id, "delete", "work_order", work_order_id, "archive_work_order",
            user_context.get("role", ""), f"Work order archived: {deletion_reason}",
            metadata={"deletion_reason": deletion_reason})

    # Check if fault cascade restored to open
    fault_updated = False
    if wo.get("fault_id"):
        fault_res = db_client.table("pms_faults").select("status").eq("id", wo["fault_id"]).limit(1).execute()
        if fault_res.data:
            fault_updated = fault_res.data[0]["status"] == "open"

    return {"status": "success", "action": "archive_work_order",
            "result": {"work_order": archived_wo, "fault_returned_to_open": fault_updated},
            "message": f"Work order archived"}


# ─────────────────────────────────────────────────────────────────────────────
# NOTES / HOURS / PARTS
# ─────────────────────────────────────────────────────────────────────────────

async def add_wo_note(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text")
    raw_type = payload.get("note_type", "general")
    note_type = raw_type if raw_type in ("general", "progress") else "general"

    wo = db_client.table("pms_work_orders").select("id, title").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    entity_name = (wo.data or {}).get("title", "")

    res = db_client.table("pms_work_order_notes").insert({
        "work_order_id": work_order_id, "note_text": note_text, "note_type": note_type,
        "created_by": user_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    if not res.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note"}
    await _audit(db_client, yacht_id, "add_wo_note", "work_order", work_order_id, user_id,
                 new_values={"note_text": note_text, "note_type": note_type})
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_wo_note",
            user_context.get("role", ""), "Note added", entity_name=entity_name)
    return {"status": "success", "message": "Note added to work order"}


async def add_note_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Insert note into pms_work_order_notes with FK fallback for service accounts."""
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text", "")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    raw_type = payload.get("note_type", "general")
    note_type = raw_type if raw_type in ("general", "progress", "issue", "resolution") else "general"

    check = db_client.table("pms_work_orders").select("id, title").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Work order not found")
    entity_name = check.data.get("title", "")

    note_data = {
        "work_order_id": work_order_id, "note_text": note_text, "note_type": note_type,
        "created_by": user_id, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        res = db_client.table("pms_work_order_notes").insert(note_data).execute()
        if res.data:
            _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_note_to_work_order",
                    user_context.get("role", ""), "Note added", entity_name=entity_name)
            return {"status": "success", "success": True, "note_id": res.data[0]["id"], "message": "Note added to work order successfully"}
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note"}
    except Exception as db_err:
        if "23503" in str(db_err) or "foreign key" in str(db_err).lower():
            fallback = db_client.table("auth_users_profiles").select("id").limit(1).execute()
            if fallback.data:
                note_data["created_by"] = fallback.data[0]["id"]
                retry = db_client.table("pms_work_order_notes").insert(note_data).execute()
                if retry.data:
                    return {"status": "success", "success": True, "note_id": retry.data[0]["id"], "message": "Note added (system attribution)"}
        raise HTTPException(status_code=500, detail=f"Database error: {db_err}")


async def add_wo_hours(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    hours = payload.get("hours", 0)
    description = payload.get("description", "Work performed")
    wo = db_client.table("pms_work_orders").select("id, title").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    entity_name = (wo.data or {}).get("title", "")
    res = db_client.table("pms_work_order_notes").insert({
        "work_order_id": work_order_id,
        "note_text": f"Hours logged: {hours}h - {description}",
        "note_type": "progress",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    if not res.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to log hours"}
    await _audit(db_client, yacht_id, "add_wo_hours", "work_order", work_order_id, user_id,
                 new_values={"hours": hours, "description": description})
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_wo_hours",
            user_context.get("role", ""), f"Logged {hours} hours", entity_name=entity_name)
    return {"status": "success", "message": f"Logged {hours} hours", "_ledger_written": True}


async def add_wo_part(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    try:
        quantity = int(payload.get("quantity", 1))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="quantity must be a valid integer")
    if quantity < 0 or quantity > 1000000:
        raise HTTPException(status_code=400, detail="quantity out of range")

    res = db_client.table("pms_work_order_parts").upsert({
        "work_order_id": work_order_id, "part_id": part_id, "quantity": quantity,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="work_order_id,part_id").execute()
    if not res.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add part"}
    await _audit(db_client, yacht_id, "add_wo_part", "work_order", work_order_id, user_id,
                 new_values={"part_id": part_id, "quantity": quantity})
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_wo_part",
            user_context.get("role", ""), f"Part added: {part_id}, qty={quantity}")
    return {"status": "success", "message": "Part added to work order", "_ledger_written": True}


async def add_part_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Add part to WO with stock validation (validates part exists on yacht)."""
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")
    quantity = int(payload.get("quantity", 1))
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")

    wo = db_client.table("pms_work_orders").select("id, wo_number, status").eq("id", work_order_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not wo.data:
        return {"status": "error", "error_code": "WO_NOT_FOUND", "message": f"Work order not found: {work_order_id}"}
    if wo.data[0]["status"] in ("closed", "cancelled"):
        return {"status": "error", "error_code": "WO_CLOSED", "message": "Cannot add parts to closed or cancelled work order"}

    part = db_client.table("pms_parts").select("id, name, part_number, quantity_on_hand, minimum_quantity").eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not part.data:
        return {"status": "error", "error_code": "PART_NOT_FOUND", "message": f"Part not found: {part_id}"}
    if quantity <= 0:
        return {"status": "error", "error_code": "INVALID_QUANTITY", "message": "Quantity must be positive"}

    existing = db_client.table("pms_work_order_parts").select("id, quantity").eq("work_order_id", work_order_id).eq("part_id", part_id).limit(1).execute()
    if existing.data:
        new_qty = existing.data[0]["quantity"] + quantity
        update_res = db_client.table("pms_work_order_parts").update({"quantity": new_qty, "notes": payload.get("notes")}).eq("id", existing.data[0]["id"]).execute()
        wo_part = update_res.data[0] if update_res.data else existing.data[0]
    else:
        insert_res = db_client.table("pms_work_order_parts").insert({
            "work_order_id": work_order_id, "part_id": part_id, "quantity": quantity,
            "notes": payload.get("notes"), "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        if not insert_res.data:
            return {"status": "error", "error_code": "INTERNAL_ERROR", "message": "Failed to add part"}
        wo_part = insert_res.data[0]

    p = part.data[0]
    stock_warning = (p.get("quantity_on_hand", 0) <= p.get("minimum_quantity", 0)) or (p.get("quantity_on_hand", 0) < quantity)
    await _audit(db_client, yacht_id, "add_part_to_work_order", "work_order_part", wo_part["id"], user_id,
                 new_values={"work_order_id": work_order_id, "part_id": part_id, "quantity": quantity},
                 signature={"user_id": user_id, "timestamp": datetime.now(timezone.utc).isoformat()})

    return {"status": "success", "action": "add_part_to_work_order",
            "result": {"work_order_part": wo_part, "stock_warning": stock_warning},
            "message": f"Part added to {wo.data[0].get('wo_number', work_order_id)}"}


async def add_parts_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Append part reference to WO metadata.parts (legacy metadata path)."""
    work_order_id = payload.get("work_order_id")
    part_id = payload.get("part_id")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Work order not found")
    wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).maybe_single().execute()
    metadata = (wo_data.data or {}).get("metadata") or {}
    parts = metadata.get("parts", [])
    parts.append({"part_id": part_id, "quantity": payload.get("quantity", 1), "added_by": user_id, "added_at": datetime.now(timezone.utc).isoformat()})
    metadata["parts"] = parts
    db_client.table("pms_work_orders").update({"metadata": metadata, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_parts_to_work_order",
            user_context.get("role", ""), f"Part {part_id} added (qty: {payload.get('quantity', 1)})")
    return {"status": "success", "success": True, "work_order_id": work_order_id, "part_id": part_id, "message": "Part added to work order"}


async def add_work_order_photo(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    photo_url = payload.get("photo_url")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")
    check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Work order not found")
    wo_data = db_client.table("pms_work_orders").select("metadata").eq("id", work_order_id).maybe_single().execute()
    metadata = (wo_data.data or {}).get("metadata") or {}
    photos = metadata.get("photos", [])
    photos.append({"url": photo_url, "caption": payload.get("caption", ""), "added_by": user_id, "added_at": datetime.now(timezone.utc).isoformat()})
    metadata["photos"] = photos
    db_client.table("pms_work_orders").update({"metadata": metadata, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "update", "work_order", work_order_id, "add_work_order_photo",
            user_context.get("role", ""), "Photo added to work order")
    return {"status": "success", "success": True, "work_order_id": work_order_id, "message": "Photo added to work order"}


# ─────────────────────────────────────────────────────────────────────────────
# CHECKLIST  (all operations on pms_work_order_checklist)
# ─────────────────────────────────────────────────────────────────────────────

async def add_checklist_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id") or context.get("work_order_id")
    title = payload.get("title")
    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    wo = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not wo.data:
        raise HTTPException(status_code=404, detail="Work order not found or access denied")

    existing = db_client.table("pms_work_order_checklist").select("sequence").eq("work_order_id", work_order_id).order("sequence", desc=True).limit(1).execute()
    next_seq = (existing.data[0]["sequence"] + 1) if existing.data else 1

    item_type = payload.get("item_type", "tick")
    if item_type not in ("tick", "measurement"):
        item_type = "tick"

    new_item = {
        "id": str(uuid_module.uuid4()),
        "yacht_id": yacht_id,
        "work_order_id": work_order_id,
        "title": title.strip(),
        "description": (payload.get("description") or "").strip() or None,
        "sequence": next_seq,
        "is_completed": False,
        "is_required": bool(payload.get("is_required", True)),
        "requires_photo": False,
        "requires_signature": False,
        "item_type": item_type,
        "unit": payload.get("unit") or None,
        "actual_value": None,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        insert = db_client.table("pms_work_order_checklist").insert(new_item).execute()
        result_data = insert.data[0] if insert.data else new_item
    except Exception as e:
        if "204" in str(e):
            result_data = new_item
        else:
            raise

    _ledger(db_client, yacht_id, user_id, "create", "checklist_item", new_item["id"], "add_checklist_item",
            user_context.get("role", ""), f"Checklist item added: {title}",
            metadata={"work_order_id": work_order_id})
    return {"status": "success", "success": True, "message": "Checklist item added", "data": result_data}


async def mark_checklist_item_complete(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Mark item complete in pms_work_order_checklist. Supports actual_value for measurement items."""
    checklist_item_id = payload.get("checklist_item_id")
    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")

    # Lookup in pms_work_order_checklist (the correct table)
    item = db_client.table("pms_work_order_checklist").select(
        "id, is_completed, work_order_id"
    ).eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()

    if not item.data:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    update_data: dict = {
        "is_completed": True,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "completed_by": user_id,
    }
    actual_value = payload.get("actual_value")
    if actual_value is not None:
        update_data["actual_value"] = str(actual_value)
    if payload.get("completion_notes"):
        update_data["completion_notes"] = payload["completion_notes"]

    try:
        db_client.table("pms_work_order_checklist").update(update_data).eq(
            "id", checklist_item_id).eq("yacht_id", yacht_id).execute()
    except Exception as e:
        if "204" not in str(e):
            raise

    _ledger(db_client, yacht_id, user_id, "status_change", "checklist_item", checklist_item_id,
            "mark_checklist_item_complete", user_context.get("role", ""), "Checklist item marked complete",
            metadata={"actual_value": actual_value})
    return {"status": "success", "success": True, "message": "Checklist item marked as complete", "checklist_item_id": checklist_item_id}


async def add_checklist_note(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Add note to a checklist item by writing to pms_work_order_notes."""
    checklist_item_id = payload.get("checklist_item_id")
    note_text = payload.get("note_text")
    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    item = db_client.table("pms_work_order_checklist").select("id, work_order_id").eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    work_order_id = item.data["work_order_id"]
    # Store as a WO note tagged with checklist_item_id
    res = db_client.table("pms_work_order_notes").insert({
        "work_order_id": work_order_id,
        "note_text": f"[Checklist] {note_text}",
        "note_type": "general",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    if not res.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add checklist note"}

    _ledger(db_client, yacht_id, user_id, "update", "checklist_item", checklist_item_id,
            "add_checklist_note", user_context.get("role", ""), "Note added to checklist item")
    return {"status": "success", "success": True, "message": "Note added to checklist item", "checklist_item_id": checklist_item_id}


async def add_checklist_photo(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Attach photo URL to a checklist item row."""
    checklist_item_id = payload.get("checklist_item_id")
    photo_url = payload.get("photo_url")
    if not checklist_item_id:
        raise HTTPException(status_code=400, detail="checklist_item_id is required")
    if not photo_url:
        raise HTTPException(status_code=400, detail="photo_url is required")

    item = db_client.table("pms_work_order_checklist").select("id").eq("id", checklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    try:
        db_client.table("pms_work_order_checklist").update({
            "photo_url": photo_url,
            "updated_by": user_id,
        }).eq("id", checklist_item_id).eq("yacht_id", yacht_id).execute()
    except Exception as e:
        if "204" not in str(e):
            raise

    _ledger(db_client, yacht_id, user_id, "update", "checklist_item", checklist_item_id,
            "add_checklist_photo", user_context.get("role", ""), "Photo added to checklist item",
            metadata={"photo_url": photo_url})
    return {"status": "success", "success": True, "message": "Photo added to checklist item",
            "checklist_item_id": checklist_item_id, "photo_url": photo_url}


# ─────────────────────────────────────────────────────────────────────────────
# READ / VIEW
# ─────────────────────────────────────────────────────────────────────────────

async def list_work_orders(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """List work orders with optional filters. Direct DB query — no ListHandlers delegation."""
    filters = payload.get("filters", {})
    params = payload.get("params", {})
    limit = int(params.get("limit", 50))
    offset = int(params.get("offset", 0))
    order_by = params.get("order_by", "created_at")
    order_dir = params.get("order_dir", "desc")

    query = db_client.table("pms_work_orders").select(
        "id, wo_number, title, description, status, priority, work_order_type, "
        "equipment_id, assigned_to, created_at, updated_at, due_date, completed_at",
        count="exact"
    ).eq("yacht_id", yacht_id)

    if filters.get("status"):
        query = query.eq("status", filters["status"])
    if filters.get("priority"):
        query = query.eq("priority", filters["priority"])
    if filters.get("equipment_id"):
        query = query.eq("equipment_id", filters["equipment_id"])
    if filters.get("work_order_type"):
        query = query.eq("work_order_type", filters["work_order_type"])

    query = query.order(order_by, desc=(order_dir == "desc")).range(offset, offset + limit - 1)
    result = query.execute()
    rows = result.data or []
    total = result.count or len(rows)

    return {
        "status": "success",
        "items": rows,
        "total_count": total,
        "limit": limit,
        "offset": offset,
        "filters_applied": list(filters.keys()),
    }


async def view_work_order_detail(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    work_order_id = payload.get("work_order_id")
    res = db_client.table("pms_work_orders").select("*, pms_equipment(*)").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if res.data:
        return {"status": "success", "work_order": res.data}
    return _wo_not_found()


async def view_work_order_checklist(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Read checklist from pms_work_order_checklist (the live table, matches entity lens)."""
    work_order_id = payload.get("work_order_id")
    wo = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not wo.data:
        raise HTTPException(status_code=404, detail="Work order not found")

    checklist_res = db_client.table("pms_work_order_checklist").select(
        "id, title, description, sequence, is_completed, completed_by, completed_at, "
        "is_required, item_type, unit, actual_value, photo_url"
    ).eq("work_order_id", work_order_id).eq("yacht_id", yacht_id).order("sequence").execute()
    checklist = checklist_res.data or []

    total = len(checklist)
    completed = sum(1 for i in checklist if i.get("is_completed"))
    return {
        "status": "success", "success": True, "work_order_id": work_order_id,
        "checklist": checklist,
        "progress": {"completed": completed, "total": total,
                     "percent": round(completed / total * 100, 1) if total else 0},
    }


async def view_work_order_history(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    equipment_id = payload.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    res = db_client.table("pms_work_orders").select(
        "id, wo_number, title, description, status, priority, created_at, completed_at"
    ).eq("equipment_id", equipment_id).eq("yacht_id", yacht_id).order("created_at", desc=True).limit(50).execute()
    return {"status": "success", "success": True, "work_orders": res.data or [], "count": len(res.data or [])}


# ─────────────────────────────────────────────────────────────────────────────
# WORKLIST
# ─────────────────────────────────────────────────────────────────────────────

async def view_worklist(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    res = db_client.table("pms_work_orders").select(
        "id, title, description, priority, status, created_at"
    ).eq("yacht_id", yacht_id).in_("status", ["planned", "in_progress"]).order("priority", desc=True).limit(50).execute()
    return {"status": "success", "success": True, "worklist": res.data or [], "total": len(res.data or [])}


async def add_worklist_task(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    task_description = payload.get("task_description") or payload.get("description")
    if not task_description:
        raise HTTPException(status_code=400, detail="task_description is required")
    priority = _map_priority(payload.get("priority", "routine"))
    res = db_client.table("pms_work_orders").insert({
        "yacht_id": yacht_id,
        "title": task_description[:100],
        "description": task_description,
        "priority": priority,
        "status": "planned",
        "work_order_type": "task",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    if res.data:
        return {"status": "success", "success": True, "task_id": res.data[0]["id"], "message": "Worklist task added"}
    return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add worklist task"}


async def export_worklist(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    res = db_client.table("pms_work_orders").select("*").eq("yacht_id", yacht_id).order("created_at", desc=True).execute()
    return {"status": "success", "success": True, "data": res.data or [], "total": len(res.data or []),
            "export_format": "json", "exported_at": datetime.now(timezone.utc).isoformat()}


async def update_worklist_progress(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    worklist_item_id = payload.get("worklist_item_id")
    progress = payload.get("progress")
    if not worklist_item_id:
        raise HTTPException(status_code=400, detail="worklist_item_id is required")
    if progress is None:
        raise HTTPException(status_code=400, detail="progress is required")
    update_data = {"progress": int(progress), "updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.get("notes"):
        update_data["notes"] = payload["notes"]
    try:
        db_client.table("worklist_items").update(update_data).eq("id", worklist_item_id).eq("yacht_id", yacht_id).execute()
    except Exception:
        try:
            item = db_client.table("worklist").select("id, metadata").eq("id", worklist_item_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if item.data:
                meta = item.data.get("metadata", {}) or {}
                meta["progress"] = int(progress)
                if payload.get("notes"):
                    meta["progress_notes"] = payload["notes"]
                meta["progress_updated_at"] = datetime.now(timezone.utc).isoformat()
                db_client.table("worklist").update({"metadata": meta}).eq("id", worklist_item_id).execute()
        except Exception:
            pass
    return {"status": "success", "success": True, "message": f"Progress updated to {progress}%",
            "worklist_item_id": worklist_item_id, "progress": int(progress)}


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────────────────

HANDLERS: dict = {
    # Create
    "create_work_order":                create_work_order,
    "create_wo":                        create_work_order,
    "create_work_order_from_fault":     create_work_order_from_fault,
    "create_work_order_for_equipment":  create_work_order_for_equipment,
    # Status mutations
    "update_work_order":                update_work_order,
    "update_wo":                        update_work_order,
    "assign_work_order":                assign_work_order,
    "assign_wo":                        assign_work_order,
    "start_work_order":                 start_work_order,
    "begin_wo":                         start_work_order,
    "cancel_work_order":                cancel_work_order,
    "cancel_wo":                        cancel_work_order,
    "close_work_order":                 close_work_order,
    "complete_work_order":              close_work_order,
    # Signed mutations
    "mark_work_order_complete":         mark_work_order_complete,
    "reassign_work_order":              reassign_work_order,
    "archive_work_order":               archive_work_order,
    # Notes / hours / parts / photos
    "add_wo_note":                      add_wo_note,
    "add_note_to_wo":                   add_wo_note,
    "add_note_to_work_order":           add_note_to_work_order,
    "add_work_order_note":              add_note_to_work_order,
    "add_wo_hours":                     add_wo_hours,
    "log_work_hours":                   add_wo_hours,
    "add_wo_part":                      add_wo_part,
    "add_part_to_wo":                   add_wo_part,
    "add_part_to_work_order":           add_part_to_work_order,
    "add_parts_to_work_order":          add_parts_to_work_order,
    "add_work_order_photo":             add_work_order_photo,
    # Checklist
    "add_checklist_item":               add_checklist_item,
    "mark_checklist_item_complete":     mark_checklist_item_complete,
    "add_checklist_note":               add_checklist_note,
    "add_checklist_photo":              add_checklist_photo,
    # Read / view
    "list_work_orders":                 list_work_orders,
    "view_work_order_detail":           view_work_order_detail,
    "view_work_order":                  view_work_order_detail,
    "get_work_order":                   view_work_order_detail,
    "view_work_order_checklist":        view_work_order_checklist,
    "view_work_order_history":          view_work_order_history,
    # Aliases — frontend suppresses these; kept so action doesn't 404
    "add_wo_photo":                     add_work_order_photo,
    "delete_work_order":                archive_work_order,
    # Worklist
    "view_worklist":                    view_worklist,
    "add_worklist_task":                add_worklist_task,
    "export_worklist":                  export_worklist,
    "update_worklist_progress":         update_worklist_progress,
}
