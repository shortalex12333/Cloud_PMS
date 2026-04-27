"""Work Order domain action handlers."""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client
from .shared import _emit_wo_notification

logger = logging.getLogger(__name__)


async def add_note_to_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    wo_result = supabase.table("pms_work_orders").select("id, wo_number, status").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not wo_result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    wo = wo_result.data[0]
    if wo.get("status") in ("closed", "cancelled"):
        raise ValueError(f"Cannot add note to {wo.get('status')} work order")
    result = supabase.table("pms_work_order_notes").insert({
        "work_order_id": params["work_order_id"],
        "note_text": params["note_text"],
        "note_type": params.get("note_type", "general"),
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    if not result.data:
        raise Exception("Failed to create work order note")
    return {
        "note_id": result.data[0]["id"],
        "work_order_id": params["work_order_id"],
        "work_order_number": wo.get("wo_number"),
        "note_text": params["note_text"],
        "note_type": params.get("note_type", "general"),
        "created_at": result.data[0]["created_at"],
        "created_by": params["user_id"],
    }


async def close_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    wo_id = params["work_order_id"]
    yacht_id = params["yacht_id"]
    user_id = params["user_id"]

    wo_pre = supabase.table("pms_work_orders").select("id, title, fault_id, metadata").eq(
        "id", wo_id
    ).eq("yacht_id", yacht_id).limit(1).execute()
    wo_pre_row = wo_pre.data[0] if wo_pre.data else {}
    fault_id = wo_pre_row.get("fault_id")
    wo_title = wo_pre_row.get("title", "Work order")
    wo_metadata = wo_pre_row.get("metadata") or {}

    previous_fault_status: Optional[str] = None
    if fault_id:
        try:
            fr = supabase.table("pms_faults").select("id, status, work_order_id").eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).limit(1).execute()
            if fr.data:
                previous_fault_status = fr.data[0].get("status")
        except Exception as fr_err:
            logger.warning("close_work_order: pre-read fault status failed (fault=%s): %s", fault_id, fr_err)

    now_iso = datetime.utcnow().isoformat()
    result = supabase.table("pms_work_orders").update({
        "status": "completed",
        "completed_at": now_iso,
        "completed_by": user_id,
    }).eq("id", wo_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        raise ValueError(f"Work order {wo_id} not found or access denied")

    fault_auto_resolved = False
    if fault_id and previous_fault_status and previous_fault_status not in ("resolved", "closed"):
        fault_auto_resolved = True
        try:
            supabase.table("pms_faults").update({"work_order_id": wo_id}).eq(
                "id", fault_id
            ).eq("yacht_id", yacht_id).execute()
        except Exception as link_err:
            logger.warning("close_work_order: reverse-link write failed (fault=%s, wo=%s): %s", fault_id, wo_id, link_err)
        try:
            from routes.handlers.ledger_utils import build_ledger_event
            ev = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="fault", entity_id=fault_id, action="fault_auto_resolved",
                change_summary=f"Auto-resolved by WO {wo_id} completion",
                metadata={"work_order_id": wo_id, "previous_status": previous_fault_status, "new_status": "resolved"},
            )
            supabase.table("ledger_events").insert(ev).execute()
        except Exception as ledger_err:
            logger.warning("close_work_order: fault_auto_resolved ledger emission failed: %s", ledger_err)

    try:
        checklist = wo_metadata.get("checklist") or []
        incomplete_required = [c for c in checklist if c.get("is_required") and not c.get("is_completed")]
        if incomplete_required:
            n = len(incomplete_required)
            _emit_wo_notification(
                supabase, yacht_id=yacht_id, user_id=user_id,
                notification_type="wo_closed_incomplete_checklist",
                title=f"WO closed with {n} incomplete required item{'s' if n != 1 else ''}",
                body=f"'{wo_title}' was closed but {n} required checklist item{'s were' if n != 1 else ' was'} not completed.",
                entity_id=wo_id, priority="high",
            )
    except Exception as _chk_err:
        logger.warning("close_work_order: checklist notification failed (wo=%s): %s", wo_id, _chk_err)

    return {
        "work_order_id": result.data[0]["id"],
        "status": result.data[0]["status"],
        "completed_at": result.data[0]["completed_at"],
        "fault_auto_resolved": fault_auto_resolved,
        "linked_fault_id": fault_id,
    }


async def update_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    for field in ("title", "description", "priority", "status"):
        if field in params:
            update_data[field] = params[field]
    result = supabase.table("pms_work_orders").update(update_data).eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    return {"work_order_id": params["work_order_id"], "updated": True, "updated_at": update_data["updated_at"]}


async def assign_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    assignee = params.get("assignee_id") or params.get("assigned_to")
    result = supabase.table("pms_work_orders").update({
        "assigned_to": assignee,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    if assignee and assignee != params["user_id"]:
        wo_title = result.data[0].get("title", "Work order") if result.data else "Work order"
        _emit_wo_notification(
            supabase, yacht_id=params["yacht_id"], user_id=assignee,
            notification_type="wo_assigned", title="Work order assigned to you",
            body=f"'{wo_title}' has been assigned to you. Open it to begin.",
            entity_id=params["work_order_id"], priority="normal",
        )
    return {"work_order_id": params["work_order_id"], "assigned_to": assignee}


async def add_wo_hours(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    wo_result = supabase.table("pms_work_orders").select("id, hours_logged").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not wo_result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    current_hours = wo_result.data[0].get("hours_logged", 0) or 0
    new_hours = current_hours + params["hours"]
    supabase.table("pms_work_orders").update({
        "hours_logged": new_hours,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["work_order_id"]).execute()
    return {"work_order_id": params["work_order_id"], "hours_added": params["hours"], "total_hours": new_hours}


async def add_wo_part(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    link_id = str(uuid_lib.uuid4())
    supabase.table("work_order_parts").insert({
        "id": link_id,
        "work_order_id": params["work_order_id"],
        "part_id": params["part_id"],
        "quantity": params.get("quantity", 1),
        "added_by": params["user_id"],
        "added_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"link_id": link_id, "work_order_id": params["work_order_id"], "part_id": params["part_id"]}


async def add_wo_note(params: Dict[str, Any]) -> Dict[str, Any]:
    return await add_note_to_work_order(params)


async def start_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()
    result = supabase.table("pms_work_orders").update({
        "status": "in_progress",
        "started_at": now,
        "updated_at": now,
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    return {"work_order_id": params["work_order_id"], "status": "in_progress"}


async def cancel_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()
    result = supabase.table("pms_work_orders").update({
        "status": "cancelled",
        "cancelled_at": now,
        "cancel_reason": params.get("reason", "Cancelled by user"),
        "updated_at": now,
    }).eq("id", params["work_order_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    return {"work_order_id": params["work_order_id"], "status": "cancelled"}


async def create_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()

    wo_type = params.get("work_order_type") or params.get("type") or "corrective"
    raw_status = params.get("status", "open")
    status = raw_status if raw_status in ("draft", "open", "planned") else "open"

    wo_id = str(uuid_lib.uuid4())
    wo_data: Dict[str, Any] = {
        "id": wo_id,
        "yacht_id": params["yacht_id"],
        "title": params["title"],
        "description": params.get("description") or "",
        "work_order_type": wo_type,
        "priority": params.get("priority") or "routine",
        "status": status,
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }

    for fk in ("equipment_id", "fault_id", "assigned_to", "system_id"):
        val = params.get(fk)
        if val and str(val).strip():
            wo_data[fk] = val

    for scalar in ("due_date", "severity", "frequency", "system_name"):
        val = params.get(scalar)
        if val is not None:
            wo_data[scalar] = val

    if params.get("estimated_duration_minutes") is not None:
        try:
            wo_data["estimated_duration_minutes"] = int(params["estimated_duration_minutes"])
        except (ValueError, TypeError):
            pass
    if params.get("running_hours_required") is not None:
        wo_data["running_hours_required"] = bool(params["running_hours_required"])
    for rh_field in ("running_hours_current", "running_hours_checkpoint"):
        if params.get(rh_field) is not None:
            try:
                wo_data[rh_field] = float(params[rh_field])
            except (ValueError, TypeError):
                pass

    result = supabase.table("pms_work_orders").insert(wo_data).execute()
    if not result.data:
        raise Exception("Failed to create work order")

    note_text = params.get("note_text")
    if note_text and str(note_text).strip():
        try:
            supabase.table("pms_work_order_notes").insert({
                "id": str(uuid_lib.uuid4()),
                "work_order_id": wo_id,
                "yacht_id": params["yacht_id"],
                "note_text": str(note_text).strip(),
                "note_type": "general",
                "created_by": params["user_id"],
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception:
            pass

    if status != "draft" and not params.get("assigned_to"):
        _emit_wo_notification(
            supabase, yacht_id=params["yacht_id"], user_id=params["user_id"],
            notification_type="wo_unassigned", title="WO unassigned — assign an engineer",
            body=f"Work order '{params['title']}' has no assigned engineer.",
            entity_id=wo_id, priority="normal",
        )

    return {"work_order_id": wo_id, "status": status, "created_at": wo_data["created_at"]}


async def view_work_order_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_work_orders").select("*").eq(
        "id", params["work_order_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Work order {params['work_order_id']} not found or access denied")
    return result.data[0]


async def add_work_order_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    attachment_id = str(uuid_lib.uuid4())
    supabase.table("pms_attachments").insert({
        "id": attachment_id,
        "yacht_id": params["yacht_id"],
        "entity_type": "work_order",
        "entity_id": params["work_order_id"],
        "storage_path": params["photo_url"],
        "filename": params.get("filename", "photo.jpg"),
        "mime_type": "image/jpeg",
        "uploaded_by": params["user_id"],
        "uploaded_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"attachment_id": attachment_id, "work_order_id": params["work_order_id"], "photo_url": params["photo_url"]}


async def add_shopping_list_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    attachment_id = str(uuid_lib.uuid4())
    supabase.table("pms_attachments").insert({
        "id": attachment_id,
        "yacht_id": params["yacht_id"],
        "entity_type": "shopping_list",
        "entity_id": params["item_id"],
        "storage_path": params["photo_url"],
        "storage_bucket": "pms-shopping-list-photos",
        "filename": params.get("filename", "photo.jpg"),
        "mime_type": params.get("mime_type", "image/jpeg"),
        "description": params.get("caption"),
        "uploaded_by": params["user_id"],
        "uploaded_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"attachment_id": attachment_id, "item_id": params["item_id"], "photo_url": params["photo_url"]}


async def add_parts_to_work_order(params: Dict[str, Any]) -> Dict[str, Any]:
    return await add_wo_part(params)


async def view_work_order_checklist(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("checklist_items").select("*").eq(
        "work_order_id", params["work_order_id"]
    ).order("sequence").execute()
    items = result.data or []
    completed = len([i for i in items if i.get("is_completed")])
    return {
        "work_order_id": params["work_order_id"],
        "checklist": items,
        "progress": {"completed": completed, "total": len(items), "percent": round((completed / len(items) * 100) if items else 0, 1)},
    }


async def view_worklist(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("worklist_tasks").select("*").eq(
        "yacht_id", params["yacht_id"]
    ).order("created_at", desc=True).execute()
    return {"tasks": result.data or [], "total": len(result.data or [])}


async def add_worklist_task(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    task_id = str(uuid_lib.uuid4())
    supabase.table("worklist_tasks").insert({
        "id": task_id,
        "yacht_id": params["yacht_id"],
        "description": params["task_description"],
        "status": "pending",
        "created_by": params["user_id"],
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"task_id": task_id, "status": "pending"}


async def export_worklist(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("worklist_tasks").select("*").eq("yacht_id", params["yacht_id"]).execute()
    return {"tasks": result.data or [], "export_format": "json", "exported_at": datetime.utcnow().isoformat()}


HANDLERS: Dict[str, Any] = {
    "add_note_to_work_order": add_note_to_work_order,
    "close_work_order": close_work_order,
    "update_work_order": update_work_order,
    "assign_work_order": assign_work_order,
    "add_wo_hours": add_wo_hours,
    "add_wo_part": add_wo_part,
    "add_wo_note": add_wo_note,
    "add_work_order_note": add_wo_note,
    "start_work_order": start_work_order,
    "cancel_work_order": cancel_work_order,
    "create_work_order": create_work_order,
    "view_work_order_detail": view_work_order_detail,
    "add_work_order_photo": add_work_order_photo,
    "add_wo_photo": add_work_order_photo,
    "add_shopping_list_photo": add_shopping_list_photo,
    "add_parts_to_work_order": add_parts_to_work_order,
    "view_work_order_checklist": view_work_order_checklist,
    "view_worklist": view_worklist,
    "add_worklist_task": add_worklist_task,
    "export_worklist": export_worklist,
    "delete_work_order": None,  # resolved in index.py via soft_delete
}
