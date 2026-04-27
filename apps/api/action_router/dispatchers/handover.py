"""Handover domain action handlers."""

from typing import Dict, Any
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)


async def edit_handover_section(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    yacht_id = params["yacht_id"]
    export_id = params.get("export_id") or params.get("handover_id") or params.get("entity_id")
    section_name = params.get("section_name")
    content = params.get("new_text") or params.get("content")

    if not export_id:
        raise ValueError("export_id or handover_id is required")
    if not section_name:
        raise ValueError("section_name is required")

    result = supabase.table("handover_exports").select(
        "id, yacht_id, edited_content, review_status"
    ).eq("id", export_id).eq("yacht_id", yacht_id).limit(1).execute()

    if not result.data:
        raise ValueError(f"Handover export {export_id} not found")

    export_row = result.data[0]
    if export_row.get("review_status") not in (None, "pending_review"):
        raise ValueError("Cannot edit after submission")

    edited_content = export_row.get("edited_content") or {}
    if "sections" not in edited_content:
        edited_content["sections"] = []

    found = False
    for section in edited_content["sections"]:
        if section.get("title") == section_name or section.get("id") == section_name:
            section["content"] = content
            section["updated_by"] = params.get("user_id")
            section["updated_at"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        edited_content["sections"].append({
            "title": section_name,
            "content": content,
            "updated_by": params.get("user_id"),
            "updated_at": datetime.utcnow().isoformat(),
        })

    edited_content["last_saved_at"] = datetime.utcnow().isoformat()
    edited_content["saved_by"] = params.get("user_id")

    supabase.table("handover_exports").update({"edited_content": edited_content}).eq(
        "id", export_id
    ).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "export_id": export_id, "section_name": section_name}


async def add_to_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    from handlers.handover_handlers import HandoverHandlers
    supabase = get_supabase_client()
    handler = HandoverHandlers(supabase)
    summary = params.get("summary") or params.get("summary_text", "")
    return await handler.add_to_handover_execute(
        entity_type=params.get("entity_type", "note"),
        entity_id=params.get("entity_id") or params.get("equipment_id"),
        summary=summary,
        category=params.get("category", "fyi"),
        yacht_id=params["yacht_id"],
        user_id=params["user_id"],
        priority=params.get("priority", "normal"),
        section=params.get("section"),
        is_critical=params.get("is_critical", False),
        requires_action=params.get("requires_action", False),
        action_summary=params.get("action_summary"),
        entity_url=params.get("entity_url"),
    )


async def _sign_handover(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    yacht_id = params["yacht_id"]
    export_id = params.get("export_id") or params.get("handover_id") or params.get("entity_id")
    user_id = params.get("user_id")

    if not export_id:
        raise ValueError("export_id or handover_id is required")

    result = supabase.table("handover_exports").select(
        "id, yacht_id, review_status, exported_by_user_id"
    ).eq("id", export_id).eq("yacht_id", yacht_id).limit(1).execute()

    if not result.data:
        raise ValueError(f"Handover export {export_id} not found")

    review_status = result.data[0].get("review_status")
    if review_status not in (None, "pending_review"):
        raise ValueError(f"Cannot sign: export is '{review_status}', expected 'pending_review'")

    now = datetime.utcnow().isoformat()
    signature = params.get("signature") or {"signer_name": user_id, "signed_at": now}

    supabase.table("handover_exports").update({
        "user_signature": signature,
        "user_signed_at": now,
        "review_status": "pending_hod_signature",
    }).eq("id", export_id).eq("yacht_id", yacht_id).execute()

    return {"status": "success", "export_id": export_id, "review_status": "pending_hod_signature"}


HANDLERS: Dict[str, Any] = {
    "edit_handover_section": edit_handover_section,
    "add_to_handover": add_to_handover,
    "sign_handover": _sign_handover,
    "archive_handover": None,  # soft_delete in index.py
    "delete_handover": None,
}
