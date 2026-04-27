"""
handlers/purchase_order_phase4.py — Purchase Order domain, single source of truth.

Consolidates all PO handler logic previously split across:
  routes/handlers/purchase_order_handler.py  (Phase 4 — 13 actions)
  action_router/dispatchers/p1_p2.py         (adapter shim — order_part)
  handlers/p1_purchasing_handlers.py          (Gen 1 class — order_part impl)

No delegation chains. Every action hits the DB in ≤1 hop from this file.

DB tables used by this domain:
  pms_purchase_orders       — primary PO record
  pms_purchase_order_items  — line items (part/description/qty/price)
  pms_suppliers             — supplier lookup / creation
  pms_attachments           — invoice document records
  pms_notifications         — data-continuity alerts
  pms_notes                 — (not used directly; notes stored in metadata.notes)
  ledger_events             — all mutations
  pms_shopping_list_items   — back-link when sourced from shopping list

Status model (current DB truth):
  draft → submitted → approved → ordered → partially_received → received
  Any non-terminal state → cancelled

Role constant:
  _HOD_ROLES — purser + department heads + captain + manager
  submit_purchase_order is intentionally open to all authenticated users.
"""
import uuid as uuid_lib
from datetime import datetime, timezone, date
import logging

from fastapi import HTTPException
from supabase import Client

from handlers.ledger_utils import build_ledger_event
from handlers.receiving_handlers import spawn_receiving_from_po

logger = logging.getLogger(__name__)

_HOD_ROLES = ["purser", "chief_engineer", "chief_officer", "chief_steward", "captain", "manager"]

_ALLOWED_PO_STATUSES = {
    "draft", "submitted", "approved", "ordered",
    "partially_received", "received", "cancelled", "delayed",
}


def _push_po_notification(
    db_client: Client,
    yacht_id: str,
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    entity_id: str,
    priority: str = "normal",
) -> None:
    try:
        db_client.table("pms_notifications").insert({
            "yacht_id": yacht_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "entity_type": "purchase_order",
            "entity_id": entity_id,
            "idempotency_key": f"po_{notification_type}_{entity_id}_{str(uuid_lib.uuid4())[:8]}",
            "is_read": False,
            "triggered_by": user_id,
        }).execute()
    except Exception as notif_err:
        logger.warning(f"[Notification] po {notification_type} failed (non-fatal): {notif_err}")


def _ledger(
    db_client: Client,
    yacht_id: str,
    user_id: str,
    event_type: str,
    entity_id: str,
    action: str,
    user_role: str,
    change_summary: str,
) -> None:
    try:
        db_client.table("ledger_events").insert(build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type=event_type,
            entity_type="purchase_order", entity_id=entity_id, action=action,
            user_role=user_role, change_summary=change_summary,
        )).execute()
    except Exception as e:
        if "204" not in str(e):
            logger.warning(f"[Ledger] Failed to record {action}: {e}")


# ============================================================================
# submit_purchase_order
# ============================================================================
async def submit_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result = db_client.table("pms_purchase_orders").update({
        "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to submit purchase order"}
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "submit_purchase_order", user_context.get("role"), "Purchase order submitted")
    return {"status": "success", "message": "Purchase order submitted"}


# ============================================================================
# approve_purchase_order
# ============================================================================
async def approve_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'approve_purchase_order'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result = db_client.table("pms_purchase_orders").update({
        "status": "ordered", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to approve purchase order"}
    _ledger(db_client, yacht_id, user_id, "approval", po_id,
            "approve_purchase_order", user_context.get("role"), "Purchase order approved and ordered")
    try:
        spawn_receiving_from_po(db_client, po_id, yacht_id, user_id)
    except Exception as spawn_err:
        logger.warning(f"[approve_purchase_order] Receiving spawn failed (non-fatal): {spawn_err}")
    return {"status": "success", "message": "Purchase order approved and ordered"}


# ============================================================================
# mark_po_received
# ============================================================================
async def mark_po_received(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'mark_po_received'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result = db_client.table("pms_purchase_orders").update({
        "status": "received", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update purchase order"}
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "mark_po_received", user_context.get("role"), "Purchase order marked received")
    try:
        po_row = db_client.table("pms_purchase_orders").select("po_number").eq(
            "id", po_id).limit(1).execute()
        po_number = po_row.data[0]["po_number"] if po_row.data else "PO"
    except Exception:
        po_number = "PO"
    _push_po_notification(
        db_client=db_client, yacht_id=yacht_id, user_id=user_id,
        notification_type="purchase_order.received_no_invoice",
        title=f"{po_number} received — upload invoice",
        body="Goods received. Upload the supplier invoice to close this purchase order.",
        entity_id=po_id, priority="high",
    )
    return {"status": "success", "message": "Purchase order marked as received"}


# ============================================================================
# cancel_purchase_order
# ============================================================================
async def cancel_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'cancel_purchase_order'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result = db_client.table("pms_purchase_orders").update({
        "status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to cancel purchase order"}
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "cancel_purchase_order", user_context.get("role"), "Purchase order cancelled")
    return {"status": "success", "message": "Purchase order cancelled"}


# ============================================================================
# delete_purchase_order (soft-delete)
# ============================================================================
async def delete_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    if user_context.get("role", "") not in _HOD_ROLES:
        return {"status": "error", "error_code": "FORBIDDEN",
                "message": f"Role '{user_context.get('role', '')}' is not permitted to delete a purchase order"}
    now = datetime.now(timezone.utc).isoformat()
    result = db_client.table("pms_purchase_orders").update({
        "deleted_at": now, "deleted_by": user_id, "updated_at": now,
    }).eq("id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Purchase order not found or already deleted"}
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "delete_po", user_context.get("role"), "Purchase order deleted")
    return {"status": "success", "purchase_order_id": po_id, "deleted_at": now}


# ============================================================================
# add_po_note
# ============================================================================
async def add_po_note(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to add PO notes",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    note_text = (payload.get("note_text") or payload.get("note") or "").strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")
    current = db_client.table("pms_purchase_orders").select("metadata").eq(
        "id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not current or not current.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    meta = current.data.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    existing = meta.get("notes", "")
    stamp = datetime.now(timezone.utc).isoformat()
    prefix = f"{existing}\n\n" if existing else ""
    meta["notes"] = f"{prefix}[{stamp}] {note_text}"
    result = db_client.table("pms_purchase_orders").update({
        "metadata": meta, "updated_at": stamp,
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to add PO note"}
    _ledger(db_client, yacht_id, user_id, "annotation", po_id,
            "add_po_note", user_context.get("role"), "Note added to purchase order")
    return {"status": "success", "message": "Note added"}


# ============================================================================
# update_purchase_status
# ============================================================================
async def update_purchase_status(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to update PO status",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    new_status = (payload.get("status") or payload.get("new_status") or "").strip().lower()
    if new_status not in _ALLOWED_PO_STATUSES:
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "INVALID_STATUS",
            "message": f"status must be one of: {sorted(_ALLOWED_PO_STATUSES)}",
        })
    now = datetime.now(timezone.utc).isoformat()
    result = db_client.table("pms_purchase_orders").update({
        "status": new_status, "updated_at": now,
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result.data:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Failed to update purchase order status"}
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "update_purchase_status", user_context.get("role"),
            f"Purchase order status set to {new_status}")
    return {"status": "success", "message": f"Status updated to {new_status}"}


# ============================================================================
# add_item_to_purchase — draft-only line item insertion
# ============================================================================
async def add_item_to_purchase(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to add PO items",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    current = db_client.table("pms_purchase_orders").select("status").eq(
        "id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not current or not current.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    po_status = (current.data.get("status") or "").lower()
    if po_status != "draft":
        raise HTTPException(status_code=422, detail={
            "status": "error", "error_code": "INVALID_STATE",
            "message": f"Cannot add items to a PO in '{po_status}' status — only draft POs can be edited.",
        })
    description = (payload.get("description") or payload.get("name")
                   or payload.get("part_name") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    try:
        quantity = float(payload.get("quantity_ordered") or payload.get("quantity") or 1)
    except (TypeError, ValueError):
        quantity = 1.0
    try:
        unit_price = float(payload["unit_price"]) if payload.get("unit_price") is not None else None
    except (TypeError, ValueError):
        unit_price = None
    insert_row: dict = {"purchase_order_id": po_id, "description": description,
                        "quantity_ordered": quantity}
    if unit_price is not None:
        insert_row["unit_price"] = unit_price
    if payload.get("part_id"):
        insert_row["part_id"] = payload["part_id"]
    if payload.get("currency"):
        insert_row["currency"] = payload["currency"]
    ins = db_client.table("pms_purchase_order_items").insert(insert_row).execute()
    if not ins.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to add item to purchase order"}
    item_id = ins.data[0].get("id") if isinstance(ins.data, list) else None
    shopping_item_id = payload.get("shopping_list_item_id")
    if shopping_item_id:
        existing_lines = db_client.table("pms_purchase_order_items").select(
            "id").eq("purchase_order_id", po_id).execute()
        line_number = len(existing_lines.data) if existing_lines.data else 1
        db_client.table("pms_shopping_list_items").update({
            "order_id": po_id, "order_line_number": line_number, "status": "ordered",
        }).eq("id", shopping_item_id).eq("yacht_id", yacht_id).execute()
    now = datetime.now(timezone.utc).isoformat()
    db_client.table("pms_purchase_orders").update(
        {"updated_at": now}).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "annotation", po_id,
            "add_item_to_purchase", user_context.get("role"),
            f"Item added: {description} × {quantity}")
    return {"status": "success", "purchase_order_id": po_id, "item_id": item_id}


# ============================================================================
# create_purchase_order
# ============================================================================
async def create_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    supplier_name = (payload.get("supplier_name") or "").strip()
    description = (payload.get("description") or "").strip()
    currency = (payload.get("currency") or "USD").strip().upper()
    notes = (payload.get("notes") or "").strip()
    year = date.today().year
    existing = db_client.table("pms_purchase_orders").select(
        "po_number").eq("yacht_id", yacht_id).like("po_number", f"PO-{year}-%").execute()
    _nums = [int(r["po_number"].rsplit("-", 1)[-1]) for r in (existing.data or [])
             if r.get("po_number", "").count("-") >= 2]
    po_number = f"PO-{year}-{max(_nums, default=0) + 1:03d}"
    po_id = str(uuid_lib.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row: dict = {
        "id": po_id, "yacht_id": yacht_id, "po_number": po_number,
        "status": "draft", "currency": currency, "ordered_by": user_id,
        "created_at": now, "updated_at": now,
    }
    if description:
        row["description"] = description
    if notes:
        row["notes"] = notes
    ins = db_client.table("pms_purchase_orders").insert(row).execute()
    if not ins.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to create purchase order"}
    if supplier_name:
        try:
            sup = db_client.table("pms_suppliers").select("id").eq(
                "yacht_id", yacht_id).ilike("name", supplier_name).limit(1).execute()
            if sup.data:
                supplier_id = sup.data[0]["id"]
            else:
                new_sup = db_client.table("pms_suppliers").insert({
                    "yacht_id": yacht_id, "name": supplier_name, "created_at": now,
                }).execute()
                supplier_id = new_sup.data[0]["id"] if new_sup.data else None
            if supplier_id:
                db_client.table("pms_purchase_orders").update(
                    {"supplier_id": supplier_id, "updated_at": now}
                ).eq("id", po_id).execute()
        except Exception as sup_err:
            logger.warning(f"[create_purchase_order] Supplier resolve failed: {sup_err}")
    _ledger(db_client, yacht_id, user_id, "create", po_id,
            "create_purchase_order", user_context.get("role"), f"PO created: {po_number}")
    _push_po_notification(
        db_client=db_client, yacht_id=yacht_id, user_id=user_id,
        notification_type="purchase_order.draft_created",
        title=f"{po_number} created — add items to order",
        body="Draft PO is open. Add line items and confirm the supplier before submitting for approval.",
        entity_id=po_id,
    )
    return {"status": "success", "purchase_order_id": po_id, "po_number": po_number}


# ============================================================================
# deny_po_line_item
# ============================================================================
async def deny_po_line_item(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' cannot deny PO line items",
            "required_roles": _HOD_ROLES,
        })
    po_item_id = payload.get("po_item_id") or payload.get("line_item_id")
    if not po_item_id:
        raise HTTPException(status_code=400, detail="po_item_id is required")
    denial_reason = (payload.get("denial_reason") or payload.get("reason") or "").strip()
    if not denial_reason:
        raise HTTPException(status_code=400, detail="denial_reason is required")
    check = db_client.table("pms_purchase_order_items").select(
        "id, purchase_order_id").eq("id", po_item_id).eq(
        "yacht_id", yacht_id).maybe_single().execute()
    if not check or not check.data:
        raise HTTPException(status_code=404, detail="Line item not found")
    po_id = check.data["purchase_order_id"]
    now = datetime.now(timezone.utc).isoformat()
    db_client.table("pms_purchase_order_items").update({
        "line_status": "denied", "denied_at": now, "denial_reason": denial_reason,
    }).eq("id", po_item_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "status_change", po_id,
            "deny_po_line_item", user_context.get("role"),
            f"Line item denied: {denial_reason}")
    return {"status": "success", "po_item_id": po_item_id, "line_status": "denied"}


# ============================================================================
# add_tracking_details — record carrier/tracking/window; auto-advance approved→ordered
# ============================================================================
async def add_tracking_details(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' cannot add tracking details",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    tracking_number = (payload.get("tracking_number") or "").strip() or None
    carrier = (payload.get("carrier") or "").strip() or None
    delivery_start = (payload.get("expected_delivery_start") or "").strip() or None
    delivery_end = (payload.get("expected_delivery_end") or "").strip() or None
    if not any([tracking_number, delivery_start, delivery_end]):
        raise HTTPException(status_code=400,
                            detail="Provide tracking_number or expected_delivery_start/end")
    po_row = db_client.table("pms_purchase_orders").select(
        "status, po_number").eq("id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not po_row or not po_row.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    current_status = po_row.data.get("status", "")
    po_number = po_row.data.get("po_number", "PO")
    now = datetime.now(timezone.utc).isoformat()
    update_payload: dict = {"updated_at": now}
    if tracking_number:
        update_payload["tracking_number"] = tracking_number
    if carrier:
        update_payload["carrier"] = carrier
    if delivery_start:
        update_payload["expected_delivery_start"] = delivery_start
    if delivery_end:
        update_payload["expected_delivery_end"] = delivery_end
    if current_status == "approved":
        update_payload["status"] = "ordered"
        update_payload["ordered_at"] = now
    db_client.table("pms_purchase_orders").update(update_payload).eq(
        "id", po_id).eq("yacht_id", yacht_id).execute()
    advanced = current_status == "approved"
    _ledger(db_client, yacht_id, user_id,
            "status_change" if advanced else "annotation", po_id,
            "add_tracking_details", user_context.get("role"),
            f"Tracking added{' — status → ordered' if advanced else ''}. "
            f"{'Tracking: ' + tracking_number + '. ' if tracking_number else ''}"
            f"{'Expected: ' + (delivery_start or '') + (' – ' + delivery_end if delivery_end else '') if delivery_start else ''}")
    if advanced:
        window = ""
        if delivery_start and delivery_end:
            window = f" Expected between {delivery_start} and {delivery_end}."
        elif delivery_start:
            window = f" Expected from {delivery_start}."
        _push_po_notification(
            db_client=db_client, yacht_id=yacht_id, user_id=user_id,
            notification_type="purchase_order.ordered",
            title=f"{po_number} ordered",
            body=f"Order placed.{window} Open Receiving when goods arrive.",
            entity_id=po_id,
        )
    return {
        "status": "success", "purchase_order_id": po_id,
        "advanced_to_ordered": advanced, "tracking_number": tracking_number,
    }


# ============================================================================
# update_supplier_on_po
# ============================================================================
async def update_supplier_on_po(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' cannot update supplier",
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    supplier_id = (payload.get("supplier_id") or "").strip() or None
    supplier_name = (payload.get("supplier_name") or "").strip() or None
    if not supplier_id and not supplier_name:
        raise HTTPException(status_code=400, detail="supplier_id or supplier_name is required")
    po = db_client.table("pms_purchase_orders").select("id, status").eq(
        "id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()
    if not po or not po.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    po_status = (po.data.get("status") or "").lower()
    if po_status in ("received", "cancelled"):
        raise HTTPException(status_code=422, detail={
            "status": "error", "error_code": "INVALID_STATE",
            "message": f"Cannot change supplier on a PO in '{po_status}' status.",
        })
    update: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if supplier_id:
        update["supplier_id"] = supplier_id
    if supplier_name:
        update["supplier_name"] = supplier_name
    db_client.table("pms_purchase_orders").update(update).eq(
        "id", po_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "annotation", po_id,
            "update_supplier_on_po", user_context.get("role"),
            f"Supplier updated to '{supplier_name or supplier_id}'")
    return {"status": "success", "purchase_order_id": po_id,
            "supplier_id": supplier_id, "supplier_name": supplier_name}


# ============================================================================
# upload_invoice — record attachment row after frontend uploads to Storage
# ============================================================================
async def upload_invoice(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to upload invoices",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    storage_path = (payload.get("storage_path") or "").strip()
    if not storage_path:
        raise HTTPException(status_code=400, detail="storage_path is required (upload file first)")
    filename = (payload.get("filename") or payload.get("original_filename") or "invoice").strip()
    po = db_client.table("pms_purchase_orders").select("id").eq(
        "id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not po or not po.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    now = datetime.now(timezone.utc).isoformat()
    att_row = {
        "yacht_id": yacht_id, "entity_type": "purchase_order", "entity_id": po_id,
        "filename": filename, "original_filename": filename,
        "mime_type": payload.get("mime_type") or "application/octet-stream",
        "file_size": int(payload.get("file_size") or 0),
        "storage_path": storage_path,
        "storage_bucket": payload.get("storage_bucket") or "pms-finance-documents",
        "category": "invoice",
        "description": payload.get("description") or payload.get("notes"),
        "uploaded_by": user_id, "uploaded_at": now,
    }
    ins = db_client.table("pms_attachments").insert(att_row).execute()
    if not ins.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to record invoice attachment"}
    attachment_id = ins.data[0].get("id") if isinstance(ins.data, list) else None
    db_client.table("pms_purchase_orders").update(
        {"updated_at": now}).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    _ledger(db_client, yacht_id, user_id, "annotation", po_id,
            "upload_invoice", user_context.get("role"), f"Invoice attached: {filename}")
    return {"status": "success", "purchase_order_id": po_id, "attachment_id": attachment_id}


# ============================================================================
# order_part — add a part as a line item to an existing PO
#
# Migrated from p1_purchasing_handlers.order_part_execute (Gen 1).
# Status bug fixed: Gen 1 checked ["draft", "requested"] — DB uses "submitted".
# Signature validation removed: not required at Phase 4 (no signed action schema).
# ============================================================================
async def order_part(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to add parts to POs",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    part_id = payload.get("part_id") or context.get("part_id")
    if not part_id:
        raise HTTPException(status_code=400, detail="part_id is required")
    try:
        quantity = int(payload.get("quantity") or 1)
        if quantity < 1:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="quantity must be a positive integer")

    po_result = db_client.table("pms_purchase_orders").select(
        "id, po_number, status").eq("id", po_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not po_result.data:
        raise HTTPException(status_code=404, detail=f"Purchase order not found: {po_id}")
    po = po_result.data[0]
    # DB status model: draft → submitted → ordered (approve_purchase_order writes "ordered" directly)
    if po["status"] not in ("draft", "submitted"):
        raise HTTPException(status_code=422, detail={
            "status": "error", "error_code": "INVALID_PO_STATUS",
            "message": f"Cannot add parts to PO in status '{po['status']}'. Must be draft or submitted.",
        })

    part_result = db_client.table("pms_parts").select(
        "id, name, part_number").eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()
    if not part_result.data:
        raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")
    part = part_result.data[0]

    existing = db_client.table("pms_purchase_order_items").select("id").eq(
        "purchase_order_id", po_id).eq("part_id", part_id).limit(1).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail={
            "status": "error", "error_code": "DUPLICATE_LINE_ITEM",
            "message": "Part already in this PO. Use add_item_to_purchase to add a different quantity.",
        })

    try:
        unit_price = float(payload["unit_price"]) if payload.get("unit_price") is not None else None
    except (TypeError, ValueError):
        unit_price = None

    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid_lib.uuid4())
    ins = db_client.table("pms_purchase_order_items").insert({
        "id": item_id,
        "yacht_id": yacht_id,
        "purchase_order_id": po_id,
        "part_id": part_id,
        "quantity_ordered": quantity,
        "unit_price": unit_price,
        "description": payload.get("notes"),
        "created_at": now,
    }).execute()
    if not ins.data:
        raise HTTPException(status_code=500, detail="Failed to add part to purchase order")

    db_client.table("pms_purchase_orders").update(
        {"updated_at": now}).eq("id", po_id).eq("yacht_id", yacht_id).execute()

    _ledger(db_client, yacht_id, user_id, "annotation", po_id,
            "order_part", user_context.get("role"),
            f"Part added: {part.get('name', part_id)} × {quantity}")

    return {
        "status": "success",
        "purchase_order_id": po_id,
        "po_number": po["po_number"],
        "item_id": item_id,
        "part_id": part_id,
        "part_name": part.get("name"),
        "quantity_ordered": quantity,
    }


# ============================================================================
# PDF DATA FETCH (called directly by purchase_order_pdf_route, not a p0 action)
# ============================================================================
def fetch_po_for_pdf(db_client: Client, po_id: str, yacht_id: str) -> dict:
    """Return all data needed to render the PO PDF. Raises HTTPException on not-found."""
    po_r = db_client.table("pms_purchase_orders").select("*").eq(
        "id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").maybe_single().execute()
    if not po_r or not po_r.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    po = dict(po_r.data)

    items_r = db_client.table("pms_purchase_order_items").select("*").eq(
        "purchase_order_id", po_id).execute()
    items = items_r.data or []

    vessel_name = "Vessel"
    try:
        vessel_r = db_client.table("vessels").select("name").eq(
            "id", yacht_id).maybe_single().execute()
        if vessel_r and vessel_r.data:
            vessel_name = vessel_r.data.get("name") or "Vessel"
    except Exception:
        pass

    ordered_by_id = po.get("ordered_by")
    if ordered_by_id:
        try:
            profile_r = db_client.table("user_yacht_profiles").select("full_name").eq(
                "user_id", ordered_by_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if profile_r and profile_r.data:
                po["ordered_by_name"] = profile_r.data.get("full_name") or ordered_by_id[:8]
        except Exception:
            pass

    return {"po": po, "items": items, "vessel_name": vessel_name}


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Core lifecycle
    "submit_purchase_order":  submit_purchase_order,
    "approve_purchase_order": approve_purchase_order,
    "mark_po_received":       mark_po_received,
    "cancel_purchase_order":  cancel_purchase_order,
    "delete_purchase_order":  delete_purchase_order,
    "create_purchase_order":  create_purchase_order,
    # Mutations
    "add_po_note":            add_po_note,
    "update_purchase_status": update_purchase_status,
    "add_item_to_purchase":   add_item_to_purchase,
    "order_part":             order_part,
    "deny_po_line_item":      deny_po_line_item,
    "add_tracking_details":   add_tracking_details,
    "update_supplier_on_po":  update_supplier_on_po,
    "upload_invoice":         upload_invoice,
    # Frontend-facing aliases
    "submit_po":              submit_purchase_order,
    "approve_po":             approve_purchase_order,
    "receive_po":             mark_po_received,
    "cancel_po":              cancel_purchase_order,
    "delete_po":              delete_purchase_order,
    "approve_purchase":       approve_purchase_order,
}
