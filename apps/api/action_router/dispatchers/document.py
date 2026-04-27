"""Document domain action handlers."""

from typing import Dict, Any
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client
from handlers.document_handlers import get_document_handlers as _get_document_handlers_raw
from handlers.document_comment_handlers import get_document_comment_handlers as _get_document_comment_handlers_raw
from handlers.attachment_comment_handlers import get_attachment_comment_handlers as _get_attachment_comment_handlers_raw
from .shared import _append_unique_uuid, _remove_uuid

logger = logging.getLogger(__name__)

_document_handlers = None
_document_comment_handlers = None
_attachment_comment_handlers = None


def _get_document_handlers():
    global _document_handlers
    if _document_handlers is None:
        _document_handlers = _get_document_handlers_raw(get_supabase_client())
    return _document_handlers


def _get_document_comment_handlers():
    global _document_comment_handlers
    if _document_comment_handlers is None:
        _document_comment_handlers = _get_document_comment_handlers_raw(get_supabase_client())
    return _document_comment_handlers


def _get_attachment_comment_handlers():
    global _attachment_comment_handlers
    if _attachment_comment_handlers is None:
        _attachment_comment_handlers = _get_attachment_comment_handlers_raw(get_supabase_client())
    return _attachment_comment_handlers


async def _doc_upload_document(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_handlers().get("upload_document")
    if not fn:
        raise ValueError("upload_document handler not registered")
    return await fn(**params)


async def _doc_update_document(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_handlers().get("update_document")
    if not fn:
        raise ValueError("update_document handler not registered")
    return await fn(**params)


async def _doc_add_document_tags(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_handlers().get("add_document_tags")
    if not fn:
        raise ValueError("add_document_tags handler not registered")
    return await fn(**params)


async def _doc_delete_document(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_handlers().get("delete_document")
    if not fn:
        raise ValueError("delete_document handler not registered")
    if not params.get("signature") or params.get("signature") == {}:
        raise ValueError("signature payload is required for delete_document (signed action)")
    return await fn(**params)


async def _doc_get_document_url(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_handlers().get("get_document_url")
    if not fn:
        raise ValueError("get_document_url handler not registered")
    return await fn(entity_id=params.get("document_id"), yacht_id=params.get("yacht_id"), params=params)


def _build_context_payload(params: Dict[str, Any]):
    context = {"yacht_id": params.get("yacht_id"), "user_id": params.get("user_id")}
    payload = {k: v for k, v in params.items() if k not in ("yacht_id", "user_id", "user_context")}
    return context, payload


async def _doc_add_document_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_comment_handlers().get("add_document_comment")
    if not fn:
        raise ValueError("add_document_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _doc_update_document_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_comment_handlers().get("update_document_comment")
    if not fn:
        raise ValueError("update_document_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _doc_delete_document_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_comment_handlers().get("delete_document_comment")
    if not fn:
        raise ValueError("delete_document_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _doc_list_document_comments(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_document_comment_handlers().get("list_document_comments")
    if not fn:
        raise ValueError("list_document_comments handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _att_add_attachment_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_attachment_comment_handlers().get("add_attachment_comment")
    if not fn:
        raise ValueError("add_attachment_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _att_update_attachment_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_attachment_comment_handlers().get("update_attachment_comment")
    if not fn:
        raise ValueError("update_attachment_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _att_delete_attachment_comment(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_attachment_comment_handlers().get("delete_attachment_comment")
    if not fn:
        raise ValueError("delete_attachment_comment handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _att_list_attachment_comments(params: Dict[str, Any]) -> Dict[str, Any]:
    fn = _get_attachment_comment_handlers().get("list_attachment_comments")
    if not fn:
        raise ValueError("list_attachment_comments handler not registered")
    context, payload = _build_context_payload(params)
    return await fn(payload, context)


async def _doc_link_equipment_to_document(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    yacht_id = params.get("yacht_id")
    document_id = params.get("document_id")
    equipment_id = params.get("equipment_id")
    if not (yacht_id and document_id and equipment_id):
        raise ValueError("yacht_id, document_id, and equipment_id are all required")
    doc_r = supabase.table("doc_metadata").select("id, equipment_ids").eq(
        "id", document_id
    ).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()
    if doc_r is None or not doc_r.data:
        raise ValueError("Document not found or access denied")
    eq_r = supabase.table("pms_equipment").select("id").eq(
        "id", equipment_id
    ).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()
    if eq_r is None or not eq_r.data:
        raise ValueError("Equipment not found or access denied")
    current = doc_r.data.get("equipment_ids") or []
    if equipment_id in current:
        return {"status": "success", "document_id": document_id, "equipment_id": equipment_id, "already_linked": True}
    new_ids = _append_unique_uuid(current, equipment_id)
    upd = supabase.table("doc_metadata").update({"equipment_ids": new_ids}).eq(
        "id", document_id
    ).eq("yacht_id", yacht_id).execute()
    if getattr(upd, "data", None) is None:
        raise ValueError("Update failed")
    return {"status": "success", "document_id": document_id, "equipment_id": equipment_id, "equipment_ids": new_ids}


async def _doc_unlink_equipment_from_document(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    yacht_id = params.get("yacht_id")
    document_id = params.get("document_id")
    equipment_id = params.get("equipment_id")
    if not (yacht_id and document_id and equipment_id):
        raise ValueError("yacht_id, document_id, and equipment_id are all required")
    doc_r = supabase.table("doc_metadata").select("id, equipment_ids").eq(
        "id", document_id
    ).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()
    if doc_r is None or not doc_r.data:
        raise ValueError("Document not found or access denied")
    current = doc_r.data.get("equipment_ids") or []
    if equipment_id not in current:
        return {"status": "success", "document_id": document_id, "equipment_id": equipment_id, "already_unlinked": True}
    new_ids = _remove_uuid(current, equipment_id)
    upd = supabase.table("doc_metadata").update({"equipment_ids": new_ids}).eq(
        "id", document_id
    ).eq("yacht_id", yacht_id).execute()
    if getattr(upd, "data", None) is None:
        raise ValueError("Update failed")
    return {"status": "success", "document_id": document_id, "equipment_id": equipment_id, "equipment_ids": new_ids}


async def delete_document(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    doc_result = supabase.table("documents").select("id, filename, deleted_at").eq(
        "id", params["document_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not doc_result.data:
        raise ValueError(f"Document {params['document_id']} not found or access denied")
    doc = doc_result.data[0]
    if doc.get("deleted_at"):
        raise ValueError("Document is already deleted")
    result = supabase.table("documents").update({
        "deleted_at": datetime.utcnow().isoformat(),
        "deleted_by": params["user_id"],
        "delete_reason": params.get("reason", "Deleted via API"),
    }).eq("id", params["document_id"]).eq("yacht_id", params["yacht_id"]).execute()
    if not result.data:
        raise Exception("Failed to delete document")
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"],
            "action": "delete_document",
            "entity_type": "document",
            "entity_id": params["document_id"],
            "user_id": params["user_id"],
            "old_values": {"deleted_at": None},
            "new_values": {"deleted_at": result.data[0].get("deleted_at")},
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for delete_document: {e}")
    return {"document_id": params["document_id"], "filename": doc.get("filename"), "deleted_at": result.data[0].get("deleted_at"), "deleted_by": params["user_id"]}


HANDLERS: Dict[str, Any] = {
    "upload_document": _doc_upload_document,
    "update_document": _doc_update_document,
    "add_document_tags": _doc_add_document_tags,
    "delete_document": _doc_delete_document,
    "get_document_url": _doc_get_document_url,
    "add_document_comment": _doc_add_document_comment,
    "update_document_comment": _doc_update_document_comment,
    "delete_document_comment": _doc_delete_document_comment,
    "list_document_comments": _doc_list_document_comments,
    "add_attachment_comment": _att_add_attachment_comment,
    "update_attachment_comment": _att_update_attachment_comment,
    "delete_attachment_comment": _att_delete_attachment_comment,
    "list_attachment_comments": _att_list_attachment_comments,
    "link_equipment_to_document": _doc_link_equipment_to_document,
    "unlink_equipment_from_document": _doc_unlink_equipment_from_document,
    "archive_document": None,  # soft_delete in index.py
}
