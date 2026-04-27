"""Fault domain action handlers."""

from typing import Dict, Any
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)


async def report_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    equipment_id = params.get("equipment_id")
    title = params.get("title")

    if not equipment_id:
        raise ValueError("equipment_id is required - faults must be attached to equipment")
    if not title:
        raise ValueError("title is required")

    severity = params.get("severity", "minor")
    description = params.get("description", "")

    valid_severities = ["cosmetic", "minor", "major", "critical", "safety"]
    if severity not in valid_severities:
        raise ValueError(f"Severity must be one of: {', '.join(valid_severities)}")

    eq_result = supabase.table("pms_equipment").select("id, name").eq(
        "id", equipment_id
    ).eq("yacht_id", yacht_id).execute()
    if not eq_result.data:
        raise ValueError(f"Equipment {equipment_id} not found or access denied")
    equipment_name = eq_result.data[0]["name"]

    year = datetime.utcnow().year
    count_result = supabase.table("pms_faults").select("id", count="exact").eq(
        "yacht_id", yacht_id
    ).gte("created_at", f"{year}-01-01").execute()
    count = (count_result.count or 0) + 1
    fault_code = f"FLT-{year}-{count:06d}"

    fault_id = str(uuid_lib.uuid4())
    now = datetime.utcnow().isoformat()
    fault_data = {
        "id": fault_id,
        "yacht_id": yacht_id,
        "equipment_id": equipment_id,
        "fault_code": fault_code,
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open",
        "detected_at": now,
        "metadata": {"reported_by": user_id, "source": "fault_lens"},
        "created_at": now,
        "updated_at": now,
    }

    result = supabase.table("pms_faults").insert(fault_data).execute()
    if not result.data:
        raise Exception("Failed to create fault")
    fault = result.data[0]

    audit_log_id = None
    try:
        audit_id = str(uuid_lib.uuid4())
        audit_result = supabase.table("pms_audit_log").insert({
            "id": audit_id,
            "yacht_id": yacht_id,
            "action": "report_fault",
            "entity_type": "fault",
            "entity_id": fault_id,
            "user_id": user_id,
            "old_values": None,
            "new_values": {"fault_code": fault_code, "title": title, "severity": severity, "equipment_id": equipment_id},
            "signature": {},
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }).execute()
        if audit_result.data:
            audit_log_id = audit_result.data[0]["id"]
    except Exception as e:
        logger.warning(f"Audit log failed for report_fault: {e}")

    handover_item_id = None
    if severity in ("critical", "safety"):
        try:
            item_result = supabase.table("dash_handover_items").insert({
                "id": str(uuid_lib.uuid4()),
                "yacht_id": yacht_id,
                "source_type": "fault",
                "source_id": fault_id,
                "title": f"{severity.upper()}: {title}",
                "description": description[:200] if description else None,
                "priority": "high" if severity == "critical" else "urgent",
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            }).execute()
            if item_result.data:
                handover_item_id = item_result.data[0]["id"]
        except Exception as e:
            logger.warning(f"Failed to add fault to handover: {e}")

    message = f"Fault {fault_code} reported"
    if handover_item_id:
        message += " (added to handover)"

    return {
        "status": "success",
        "fault_id": fault_id,
        "fault_code": fault_code,
        "title": title,
        "severity": severity,
        "equipment_id": equipment_id,
        "equipment_name": equipment_name,
        "created_at": fault["created_at"],
        "audit_log_id": audit_log_id,
        "handover_item_id": handover_item_id,
        "next_actions": ["add_fault_note", "add_fault_photo", "create_work_order_from_fault"],
        "message": message,
    }


async def close_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").update({
        "status": "closed",
        "resolved_at": datetime.utcnow().isoformat(),
        "resolved_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "status": "closed", "resolved_at": result.data[0].get("resolved_at")}


async def update_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    for field in ("description", "priority", "status"):
        if field in params:
            update_data[field] = params[field]
    result = supabase.table("pms_faults").update(update_data).eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "updated": True, "updated_at": update_data["updated_at"]}


async def add_fault_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    fault_result = supabase.table("pms_faults").select("id").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    attachment_id = str(uuid_lib.uuid4())
    supabase.table("attachments").insert({
        "id": attachment_id,
        "entity_type": "fault",
        "entity_id": params["fault_id"],
        "storage_path": params["photo_url"],
        "filename": params.get("filename", "photo.jpg"),
        "mime_type": "image/jpeg",
        "uploaded_by": params["user_id"],
        "uploaded_at": datetime.utcnow().isoformat(),
    }).execute()
    return {"attachment_id": attachment_id, "fault_id": params["fault_id"], "photo_url": params["photo_url"]}


async def view_fault_detail(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return result.data[0]


async def diagnose_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {
        "status": "success",
        "fault_id": params["fault_id"],
        "fault": fault_result.data[0],
        "diagnosis": {"findings": [], "finding_count": 0},
        "remedies": {"suggested_actions": [], "remedy_count": 0},
    }


async def view_fault_history(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").select("*").eq(
        "yacht_id", params["yacht_id"]
    ).or_(f"id.eq.{params['entity_id']},equipment_id.eq.{params['entity_id']}").order(
        "created_at", desc=True
    ).limit(50).execute()
    return {"entity_id": params["entity_id"], "faults": result.data or [], "total": len(result.data or [])}


async def suggest_parts(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", params["fault_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not fault_result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "suggested_parts": [], "summary": {"total_suggested": 0, "available": 0, "unavailable": 0}}


async def show_manual_section(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"equipment_id": params.get("equipment_id"), "manual_sections": [], "message": "No manual sections found"}


async def add_fault_note(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    fault_id = params["fault_id"]
    user_id = params["user_id"]
    text = params.get("note_text") or params.get("text") or params.get("note")
    note_type = params.get("note_type", "observation")

    if not text:
        raise ValueError("Note text is required")

    fault_result = supabase.table("pms_faults").select("id, title").eq(
        "id", fault_id
    ).eq("yacht_id", yacht_id).execute()
    if not fault_result.data:
        raise ValueError(f"Fault {fault_id} not found or access denied")

    note_id = str(uuid_lib.uuid4())
    now = datetime.utcnow().isoformat()

    result = supabase.table("pms_notes").insert({
        "id": note_id,
        "yacht_id": yacht_id,
        "fault_id": fault_id,
        "text": text,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }).execute()
    if not result.data:
        raise Exception("Failed to insert note")

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "entity_type": "note",
            "entity_id": note_id,
            "action": "add_fault_note",
            "user_id": user_id,
            "old_values": None,
            "new_values": {"fault_id": fault_id, "text": text[:200], "note_type": note_type},
            "signature": {},
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for add_fault_note: {e}")

    return {"note_id": note_id, "fault_id": fault_id, "created_at": now, "message": "Note added successfully"}


async def create_work_order_from_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    import hashlib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    fault_id = params["fault_id"]
    user_id = params["user_id"]
    signature = params.get("signature")

    if not signature:
        raise ValueError("Signature is required for create_work_order_from_fault action")

    fault_result = supabase.table("pms_faults").select("*").eq(
        "id", fault_id
    ).eq("yacht_id", yacht_id).execute()
    if not fault_result.data:
        raise ValueError(f"Fault {fault_id} not found or access denied")
    fault = fault_result.data[0]

    if fault.get("status") in ("work_ordered", "resolved", "closed"):
        raise ValueError(f"Cannot create work order: fault is already {fault.get('status')}")

    severity_to_priority = {
        "cosmetic": "routine", "minor": "routine", "major": "important",
        "critical": "critical", "safety": "emergency",
    }
    priority = params.get("priority") or severity_to_priority.get(fault.get("severity"), "important")

    now = datetime.utcnow().isoformat()
    wo_id = str(uuid_lib.uuid4())

    result = supabase.table("pms_work_orders").insert({
        "id": wo_id,
        "yacht_id": yacht_id,
        "equipment_id": fault.get("equipment_id"),
        "fault_id": fault_id,
        "title": params.get("title") or fault.get("title") or f"Fix: {fault.get('description', 'Fault repair')[:100]}",
        "description": fault.get("description"),
        "type": "corrective",
        "priority": priority,
        "status": "planned",
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    }).execute()
    if not result.data:
        raise Exception("Failed to create work order")

    supabase.table("pms_faults").update({
        "status": "work_ordered",
        "work_order_id": wo_id,
        "updated_at": now,
        "updated_by": user_id,
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    signature_hash = hashlib.sha256(f"{user_id}:{fault_id}:{wo_id}:{now}".encode()).hexdigest()
    signature_payload = {
        "user_id": user_id,
        "role_at_signing": signature.get("role_at_signing", "unknown"),
        "signature_type": "create_work_order_from_fault",
        "fault_id": fault_id,
        "work_order_id": wo_id,
        "signature_hash": f"sha256:{signature_hash}",
        "signed_at": now,
    }

    try:
        supabase.table("pms_audit_log").insert({
            "id": str(uuid_lib.uuid4()),
            "yacht_id": yacht_id,
            "entity_type": "work_order",
            "entity_id": wo_id,
            "action": "create_work_order_from_fault",
            "user_id": user_id,
            "old_values": {"fault_status": fault.get("status")},
            "new_values": {"work_order_id": wo_id, "fault_id": fault_id, "fault_status": "work_ordered"},
            "signature": signature_payload,
            "metadata": {"source": "fault_lens"},
            "created_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for create_work_order_from_fault: {e}")

    return {
        "work_order_id": wo_id,
        "fault_id": fault_id,
        "status": "planned",
        "created_at": now,
        "message": "Work order created from fault",
        "next_actions": ["assign_work_order", "start_work_order"],
    }


async def reopen_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").update({
        "status": "open",
        "resolved_at": None,
        "resolved_by": None,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "status": "open"}


async def mark_fault_false_alarm(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").update({
        "status": "false_alarm",
        "resolved_at": datetime.utcnow().isoformat(),
        "resolved_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "status": "false_alarm"}


async def acknowledge_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    result = supabase.table("pms_faults").update({
        "acknowledged_at": datetime.utcnow().isoformat(),
        "acknowledged_by": params["user_id"],
    }).eq("id", params["fault_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise ValueError(f"Fault {params['fault_id']} not found or access denied")
    return {"fault_id": params["fault_id"], "acknowledged": True}


HANDLERS: Dict[str, Any] = {
    "report_fault": report_fault,
    "close_fault": close_fault,
    "update_fault": update_fault,
    "add_fault_photo": add_fault_photo,
    "view_fault_detail": view_fault_detail,
    "diagnose_fault": diagnose_fault,
    "view_fault_history": view_fault_history,
    "show_manual_section": show_manual_section,
    "add_fault_note": add_fault_note,
    "create_work_order_from_fault": create_work_order_from_fault,
    "reopen_fault": reopen_fault,
    "mark_fault_false_alarm": mark_fault_false_alarm,
    "acknowledge_fault": acknowledge_fault,
    "investigate_fault": diagnose_fault,
    "resolve_fault": close_fault,
    "suggest_parts": None,    # not_yet_implemented — resolved in index.py
    "classify_fault": None,   # not_yet_implemented — resolved in index.py
    "archive_fault": None,    # soft_delete — resolved in index.py
    "delete_fault": None,     # soft_delete — resolved in index.py
}
