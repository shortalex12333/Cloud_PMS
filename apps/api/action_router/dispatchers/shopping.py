"""Shopping List and Purchase Order domain action handlers."""

from typing import Dict, Any
import logging
from datetime import datetime
from integrations.supabase import get_supabase_client
from handlers.shopping_list_handlers import get_shopping_list_handlers as _get_shopping_list_handlers_raw
from handlers.shopping_list_v2_handlers import get_shopping_list_v2_handlers as _get_shopping_list_v2_handlers_raw

logger = logging.getLogger(__name__)

_shopping_list_handlers = None
_shopping_list_v2_handlers = None


def _get_shopping_list_handlers():
    global _shopping_list_handlers
    if _shopping_list_handlers is None:
        _shopping_list_handlers = _get_shopping_list_handlers_raw(get_supabase_client())
    return _shopping_list_handlers


def _get_sl_v2_handlers():
    global _shopping_list_v2_handlers
    if _shopping_list_v2_handlers is None:
        _shopping_list_v2_handlers = _get_shopping_list_v2_handlers_raw(get_supabase_client())
    return _shopping_list_v2_handlers


# Shopping List v1

async def _sl_create_item(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_shopping_list_handlers()
    return await handlers.create_shopping_list_item(entity_id=None, yacht_id=params["yacht_id"], params=params)


async def _sl_approve_item(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_shopping_list_handlers()
    return await handlers.approve_shopping_list_item(entity_id=params["item_id"], yacht_id=params["yacht_id"], params=params)


async def _sl_reject_item(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_shopping_list_handlers()
    return await handlers.reject_shopping_list_item(entity_id=params["item_id"], yacht_id=params["yacht_id"], params=params)


async def _sl_promote_candidate(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_shopping_list_handlers()
    return await handlers.promote_candidate_to_part(entity_id=params["item_id"], yacht_id=params["yacht_id"], params=params)


async def _sl_view_history(params: Dict[str, Any]) -> Dict[str, Any]:
    handlers = _get_shopping_list_handlers()
    return await handlers.view_shopping_list_history(entity_id=params["item_id"], yacht_id=params["yacht_id"], params=params)


# Shopping List v2

async def _sl2_create_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().create_shopping_list(params)


async def _sl2_add_item_to_list(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().add_item_to_list(params)


async def _sl2_update_list_item(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().update_list_item(params)


async def _sl2_delete_list_item(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().delete_list_item(params)


async def _sl2_submit_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().submit_shopping_list(params)


async def _sl2_hod_review_list_item(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().hod_review_list_item(params)


async def _sl2_approve_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    return await _get_sl_v2_handlers().approve_shopping_list(params)


async def _sl2_add_photo(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as _uuid
    from datetime import datetime, timezone
    supabase = get_supabase_client()
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = supabase.table("pms_attachments").insert({
            "id": str(_uuid.uuid4()),
            "yacht_id": params["yacht_id"],
            "entity_type": "shopping_list",
            "entity_id": params["item_id"],
            "uploaded_by": params.get("user_id"),
            "storage_path": params["storage_path"],
            "storage_bucket": "pms-shopping-list-photos",
            "file_name": params.get("file_name", "photo"),
            "file_type": params.get("file_type", "image"),
            "created_at": now,
        }).execute()
        return {"status": "success", "action": "add_shopping_list_photo", "result": row.data[0] if row.data else {}}
    except Exception as exc:
        logger.error(f"[sl_v2] add_photo failed: {exc}", exc_info=True)
        return {"status": "error", "error_code": "INTERNAL_ERROR", "message": str(exc)}


async def delete_shopping_item(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    item_result = supabase.table("pms_shopping_list_items").select("id, part_name, status").eq(
        "id", params["item_id"]
    ).eq("yacht_id", params["yacht_id"]).execute()
    if not item_result.data:
        raise ValueError(f"Shopping item {params['item_id']} not found or access denied")
    item = item_result.data[0]
    if item.get("status") in ("ordered", "partially_fulfilled", "installed"):
        raise ValueError(f"Cannot delete item with status '{item.get('status')}'")
    supabase.table("pms_shopping_list_items").delete().eq("id", params["item_id"]).eq("yacht_id", params["yacht_id"]).execute()
    try:
        supabase.table("pms_audit_log").insert({
            "yacht_id": params["yacht_id"], "action": "delete_shopping_item",
            "entity_type": "shopping_item", "entity_id": params["item_id"],
            "user_id": params["user_id"],
            "old_values": {"part_name": item.get("part_name"), "status": item.get("status")},
            "new_values": None, "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Audit log failed for delete_shopping_item: {e}")
    return {"item_id": params["item_id"], "part_name": item.get("part_name"), "deleted": True, "deleted_by": params["user_id"]}


async def _submit_shopping_list(params: Dict[str, Any]) -> Dict[str, Any]:
    supabase = get_supabase_client()
    item_id = params.get("item_id") or params.get("entity_id")
    yacht_id = params["yacht_id"]
    if not item_id:
        raise ValueError("item_id or entity_id is required")
    item = supabase.table("pms_shopping_list_items").select("id, status").eq(
        "id", item_id
    ).eq("yacht_id", yacht_id).limit(1).execute()
    if not item.data:
        raise ValueError(f"Shopping list item {item_id} not found")
    if item.data[0]["status"] != "candidate":
        raise ValueError(f"Cannot submit: item is '{item.data[0]['status']}', expected 'candidate'")
    supabase.table("pms_shopping_list_items").update({
        "status": "under_review",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": params.get("user_id"),
    }).eq("id", item_id).eq("yacht_id", yacht_id).execute()
    return {"status": "success", "item_id": item_id, "new_status": "under_review"}


async def _convert_to_po(params: Dict[str, Any]) -> Dict[str, Any]:
    import uuid as uuid_lib
    supabase = get_supabase_client()
    yacht_id = params["yacht_id"]
    user_id = params.get("user_id")
    shopping_list_id = params.get("shopping_list_id")

    query = supabase.table("pms_shopping_list_items").select(
        "id, part_name, part_number, manufacturer, quantity_requested, quantity_approved, unit, part_id"
    ).eq("yacht_id", yacht_id).eq("status", "approved").is_("deleted_at", "null")
    if shopping_list_id:
        query = query.eq("shopping_list_id", shopping_list_id)
    else:
        item_ids = params.get("item_ids")
        if item_ids:
            query = query.in_("id", item_ids)
    items = (query.execute()).data or []
    if not items:
        raise ValueError("No approved shopping list items found")

    year = datetime.utcnow().year
    existing = supabase.table("pms_purchase_orders").select("po_number").eq(
        "yacht_id", yacht_id
    ).like("po_number", f"PO-{year}-%").execute()
    po_number = f"PO-{year}-{len(existing.data or []) + 1:03d}"

    po_id = str(uuid_lib.uuid4())
    po_data = {
        "id": po_id, "yacht_id": yacht_id, "po_number": po_number,
        "status": "draft", "ordered_by": user_id,
        "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat(),
    }
    if shopping_list_id:
        po_data["source_shopping_list_id"] = shopping_list_id
    if params.get("supplier_id"):
        po_data["supplier_id"] = params["supplier_id"]
    supabase.table("pms_purchase_orders").insert(po_data).execute()

    for line_number, item in enumerate(items, start=1):
        supabase.table("pms_purchase_order_items").insert({
            "id": str(uuid_lib.uuid4()), "yacht_id": yacht_id,
            "purchase_order_id": po_id, "part_id": item.get("part_id"),
            "description": item["part_name"],
            "quantity_ordered": int(item.get("quantity_approved") or item["quantity_requested"]),
            "shopping_list_item_id": item["id"],
        }).execute()
        supabase.table("pms_shopping_list_items").update({
            "status": "ordered", "order_id": po_id, "order_line_number": line_number,
            "updated_at": datetime.utcnow().isoformat(), "updated_by": user_id,
        }).eq("id", item["id"]).eq("yacht_id", yacht_id).execute()

    if shopping_list_id:
        try:
            supabase.table("pms_shopping_lists").update({
                "status": "converted_to_po", "converted_to_po_id": po_id,
                "converted_at": datetime.utcnow().isoformat(),
            }).eq("id", shopping_list_id).eq("yacht_id", yacht_id).execute()
        except Exception as sl_err:
            logger.warning(f"[convert_to_po] Shopping list status update failed: {sl_err}")

    return {
        "status": "success", "po_id": po_id, "po_number": po_number,
        "items_ordered": len(items), "source_shopping_list_id": shopping_list_id,
    }


HANDLERS: Dict[str, Any] = {
    "create_shopping_list_item": _sl_create_item,
    "approve_shopping_list_item": _sl_approve_item,
    "reject_shopping_list_item": _sl_reject_item,
    "promote_candidate_to_part": _sl_promote_candidate,
    "view_shopping_list_history": _sl_view_history,
    "approve_list": _sl_approve_item,
    "add_list_item": _sl_create_item,
    "create_shopping_list": _sl2_create_shopping_list,
    "add_item_to_list": _sl2_add_item_to_list,
    "update_list_item": _sl2_update_list_item,
    "delete_list_item": _sl2_delete_list_item,
    "submit_shopping_list": _sl2_submit_shopping_list,
    "hod_review_list_item": _sl2_hod_review_list_item,
    "approve_shopping_list": _sl2_approve_shopping_list,
    "add_shopping_list_photo": _sl2_add_photo,
    "delete_shopping_item": delete_shopping_item,
    "submit_list": _submit_shopping_list,
    "convert_to_po": _convert_to_po,
    "archive_list": None,  # soft_delete in index.py
    "delete_list": None,
}
