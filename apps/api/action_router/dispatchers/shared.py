"""Shared utilities used by multiple domain dispatchers."""

from typing import Dict, Any
import logging
from datetime import datetime
from supabase import Client
from integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def _emit_wo_notification(
    supabase: Client,
    yacht_id: str,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    entity_id: str,
    priority: str = "normal",
) -> None:
    """Insert a pms_notifications row for a work-order event. Fire-and-forget."""
    import uuid as _uuid
    try:
        supabase.table("pms_notifications").insert({
            "id": str(_uuid.uuid4()),
            "yacht_id": yacht_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "entity_type": "work_order",
            "entity_id": entity_id,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as _e:
        logger.warning("_emit_wo_notification failed (type=%s, wo=%s): %s", notification_type, entity_id, _e)


def _append_unique_uuid(lst: list, uid: str) -> list:
    """Return a new list with `uid` appended iff not already present."""
    current = list(lst or [])
    if uid not in current:
        current.append(uid)
    return current


def _remove_uuid(lst: list, uid: str) -> list:
    """Return a new list with every occurrence of `uid` removed."""
    return [x for x in (lst or []) if x != uid]


async def add_note(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a note to any entity via pms_notes."""
    import uuid as uuid_lib
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    user_id = params["user_id"]
    note_text = params.get("note_text") or params.get("text")
    if not note_text:
        raise ValueError("note_text is required")

    entity_id = (
        params.get("equipment_id") or params.get("fault_id") or
        params.get("work_order_id") or params.get("certificate_id") or
        params.get("document_id") or params.get("part_id") or
        params.get("entity_id")
    )

    note_id = str(uuid_lib.uuid4())
    now = datetime.utcnow().isoformat()

    note_data = {
        "id": note_id,
        "yacht_id": yacht_id,
        "text": note_text,
        "note_type": params.get("note_type", "observation"),
        "created_by": user_id,
        "created_by_role": params.get("role", ""),
        "created_at": now,
        "updated_at": now,
    }

    for col in ("equipment_id", "fault_id", "work_order_id", "document_id",
                "part_id", "purchase_order_id", "warranty_id", "certificate_id"):
        if params.get(col):
            note_data[col] = params[col]

    result = supabase.table("pms_notes").insert(note_data).execute()
    if not result.data:
        raise Exception("Failed to create note")

    return {
        "note_id": note_id,
        "entity_id": entity_id,
        "created_at": now,
        "message": "Note added successfully",
    }


async def open_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a signed URL for a document."""
    supabase = get_supabase_client()

    yacht_id = params["yacht_id"]
    storage_path = params["storage_path"]

    if not storage_path.startswith(f"{yacht_id}/"):
        raise ValueError("Access denied: Document does not belong to your yacht")

    try:
        result = supabase.storage.from_("documents").create_signed_url(
            storage_path, expires_in=3600,
        )
        if not result:
            raise Exception("Failed to generate signed URL")
        return {"signed_url": result["signedURL"], "expires_in": 3600}
    except Exception as e:
        raise Exception(f"Failed to generate document URL: {str(e)}")


HANDLERS: Dict[str, Any] = {
    "add_note": add_note,
    "add_certificate_note": add_note,
    "add_document_note": add_note,
    "add_part_note": add_note,
    "add_po_note": add_note,
    "open_document": open_document,
}
