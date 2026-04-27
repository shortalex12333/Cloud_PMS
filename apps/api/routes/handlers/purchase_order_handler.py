"""
Purchase Order Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 3).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
Import build_ledger_event from routes.handlers.ledger_utils, not from p0_actions_routes.
"""
from datetime import datetime, timezone
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event
from handlers.receiving_spawn import spawn_receiving_from_po

logger = logging.getLogger(__name__)


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
    import uuid as _uuid
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
            "idempotency_key": f"po_{notification_type}_{entity_id}_{str(_uuid.uuid4())[:8]}",
            "is_read": False,
            "triggered_by": user_id,
        }).execute()
    except Exception as notif_err:
        logger.warning(f"[Notification] po {notification_type} failed (non-fatal): {notif_err}")


# Used by approve_purchase_order, mark_po_received, cancel_purchase_order only.
# submit_purchase_order is intentionally open to all authenticated users.
# purser = financial officer on board; chief_officer / chief_steward = department heads
_HOD_ROLES = ["purser", "chief_engineer", "chief_officer", "chief_steward", "captain", "manager"]


# ============================================================================
# submit_purchase_order  (was L5463-5486)
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
    result_data = db_client.table("pms_purchase_orders").update({
        "status": "submitted", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if result_data.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="purchase_order", entity_id=po_id, action="submit_purchase_order",
                user_role=user_context.get("role"), change_summary="Purchase order submitted",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record submit_purchase_order: {ledger_err}")
        return {"status": "success", "message": "Purchase order submitted"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to submit purchase order"}


# ============================================================================
# approve_purchase_order  (was L5488-5519)
# ============================================================================
async def approve_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Role check — HOD only (canonical: LENS_TRUTH_SHEET.md)
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'approve_purchase_order'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result_data = db_client.table("pms_purchase_orders").update({
        "status": "ordered", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if result_data.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="approval",
                entity_type="purchase_order", entity_id=po_id, action="approve_purchase_order",
                user_role=user_context.get("role"), change_summary="Purchase order approved and ordered",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record approve_purchase_order: {ledger_err}")
        # Auto-create receiving record pre-populated from PO line items
        try:
            spawn_receiving_from_po(db_client, po_id, yacht_id, user_id)
        except Exception as spawn_err:
            logger.warning(f"[approve_purchase_order] Receiving spawn failed (non-fatal): {spawn_err}")
        return {"status": "success", "message": "Purchase order approved and ordered"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to approve purchase order"}


# ============================================================================
# mark_po_received  (was L5521-5552)
# ============================================================================
async def mark_po_received(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Role check — HOD only (canonical: LENS_TRUTH_SHEET.md)
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'mark_po_received'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result_data = db_client.table("pms_purchase_orders").update({
        "status": "received", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if result_data.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="purchase_order", entity_id=po_id, action="mark_po_received",
                user_role=user_context.get("role"), change_summary="Purchase order marked received",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record mark_po_received: {ledger_err}")
        # Data continuity: prompt invoice upload — goods received but record is open until invoice filed
        try:
            po_row = db_client.table("pms_purchase_orders").select("po_number").eq(
                "id", po_id
            ).limit(1).execute()
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
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update purchase order"}


# ============================================================================
# cancel_purchase_order  (was L5554-5585)
# ============================================================================
async def cancel_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    # Role check — HOD only (canonical: LENS_TRUTH_SHEET.md)
    if user_context.get("role", "") not in _HOD_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_context.get('role', '')}' is not permitted to perform 'cancel_purchase_order'",
            "required_roles": _HOD_ROLES,
        })
    po_id = payload.get("purchase_order_id") or context.get("purchase_order_id")
    if not po_id:
        raise HTTPException(status_code=400, detail="purchase_order_id is required")
    result_data = db_client.table("pms_purchase_orders").update({
        "status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if result_data.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="purchase_order", entity_id=po_id, action="cancel_purchase_order",
                user_role=user_context.get("role"), change_summary="Purchase order cancelled",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record cancel_purchase_order: {ledger_err}")
        return {"status": "success", "message": "Purchase order cancelled"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to cancel purchase order"}


# ============================================================================
# delete_purchase_order
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
    user_role = user_context.get("role", "")
    if user_role not in _HOD_ROLES:
        return {"status": "error", "error_code": "FORBIDDEN",
                "message": f"Role '{user_role}' is not permitted to delete a purchase order"}
    now = datetime.now(timezone.utc).isoformat()
    result_data = db_client.table("pms_purchase_orders").update({
        "deleted_at": now, "deleted_by": user_id, "updated_at": now,
    }).eq("id", po_id).eq("yacht_id", yacht_id).is_("deleted_at", "null").execute()
    if not result_data.data:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Purchase order not found or already deleted"}
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="status_change",
            entity_type="purchase_order", entity_id=po_id, action="delete_po",
            user_role=user_role, change_summary="Purchase order deleted",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        logger.warning(f"[Ledger] Failed to record delete_po: {ledger_err}")
    return {"status": "success", "purchase_order_id": po_id, "deleted_at": now}


# ============================================================================
# add_po_note — append a note to metadata.notes (Issue #14, 2026-04-23)
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

    result_data = db_client.table("pms_purchase_orders").update({
        "metadata": meta, "updated_at": stamp,
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result_data.data:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Failed to add PO note"}
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="annotation",
            entity_type="purchase_order", entity_id=po_id, action="add_po_note",
            user_role=user_context.get("role"), change_summary="Note added to purchase order",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record add_po_note: {ledger_err}")
    return {"status": "success", "message": "Note added"}


# ============================================================================
# update_purchase_status — explicit status transition (Issue #14, 2026-04-23)
# ============================================================================
_ALLOWED_PO_STATUSES = {
    "draft", "submitted", "approved", "ordered",
    "partially_received", "received", "cancelled", "delayed",
}


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
    result_data = db_client.table("pms_purchase_orders").update({
        "status": new_status, "updated_at": now,
    }).eq("id", po_id).eq("yacht_id", yacht_id).execute()
    if not result_data.data:
        return {"status": "error", "error_code": "UPDATE_FAILED",
                "message": "Failed to update purchase order status"}
    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="status_change",
            entity_type="purchase_order", entity_id=po_id, action="update_purchase_status",
            user_role=user_context.get("role"),
            change_summary=f"Purchase order status set to {new_status}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record update_purchase_status: {ledger_err}")
    return {"status": "success", "message": f"Status updated to {new_status}"}


# ============================================================================
# add_item_to_purchase — insert a line item (Issue #14, draft-only)
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

    # DB-side draft gate — matches the UI gate at entity_actions._apply_state_gate.
    current = db_client.table("pms_purchase_orders").select("status").eq(
        "id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not current or not current.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    po_status = (current.data.get("status") or "").lower()
    if po_status not in ("", "draft"):
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
        unit_price = (float(payload.get("unit_price")) if payload.get("unit_price")
                      is not None else None)
    except (TypeError, ValueError):
        unit_price = None

    insert_row = {
        "purchase_order_id": po_id,
        "description": description,
        "quantity_ordered": quantity,
    }
    if unit_price is not None:
        insert_row["unit_price"] = unit_price
    if payload.get("part_id"):
        insert_row["part_id"] = payload.get("part_id")
    if payload.get("currency"):
        insert_row["currency"] = payload.get("currency")

    insert_res = db_client.table("pms_purchase_order_items").insert(insert_row).execute()
    if not insert_res.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to add item to purchase order"}
    item_id = insert_res.data[0].get("id") if isinstance(insert_res.data, list) else None

    # If sourced from a shopping list item, write back the PO link.
    shopping_item_id = payload.get("shopping_list_item_id")
    if shopping_item_id:
        existing_lines = db_client.table("pms_purchase_order_items").select(
            "id"
        ).eq("purchase_order_id", po_id).execute()
        line_number = len(existing_lines.data) if existing_lines.data else 1
        db_client.table("pms_shopping_list_items").update({
            "order_id": po_id,
            "order_line_number": line_number,
            "status": "ordered",
        }).eq("id", shopping_item_id).eq("yacht_id", yacht_id).execute()

    # Bump the PO's updated_at so the lens reload picks it up.
    now = datetime.now(timezone.utc).isoformat()
    db_client.table("pms_purchase_orders").update(
        {"updated_at": now}
    ).eq("id", po_id).eq("yacht_id", yacht_id).execute()

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="annotation",
            entity_type="purchase_order", entity_id=po_id, action="add_item_to_purchase",
            user_role=user_context.get("role"),
            change_summary=f"Item added: {description} × {quantity}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record add_item_to_purchase: {ledger_err}")
    return {"status": "success", "purchase_order_id": po_id, "item_id": item_id}


# ============================================================================
# create_purchase_order — create a new draft PO from the list-view modal
# ============================================================================
async def create_purchase_order(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    import uuid as uuid_lib
    supplier_name = (payload.get("supplier_name") or "").strip()
    description = (payload.get("description") or "").strip()
    currency = (payload.get("currency") or "USD").strip().upper()
    notes = (payload.get("notes") or "").strip()

    # Generate PO number: PO-YYYY-NNN
    from datetime import date
    year = date.today().year
    existing = db_client.table("pms_purchase_orders").select(
        "po_number"
    ).eq("yacht_id", yacht_id).like("po_number", f"PO-{year}-%").execute()
    next_num = len(existing.data or []) + 1
    po_number = f"PO-{year}-{next_num:03d}"

    po_id = str(uuid_lib.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": po_id,
        "yacht_id": yacht_id,
        "po_number": po_number,
        "status": "draft",
        "currency": currency,
        "ordered_by": user_id,
        "created_at": now,
        "updated_at": now,
    }
    if description:
        row["description"] = description
    if notes:
        row["notes"] = notes

    ins = db_client.table("pms_purchase_orders").insert(row).execute()
    if not ins.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to create purchase order"}

    # If supplier_name given, resolve or create supplier row
    if supplier_name:
        try:
            sup = db_client.table("pms_suppliers").select("id").eq(
                "yacht_id", yacht_id
            ).ilike("name", supplier_name).limit(1).execute()
            if sup.data:
                supplier_id = sup.data[0]["id"]
            else:
                new_sup = db_client.table("pms_suppliers").insert({
                    "yacht_id": yacht_id,
                    "name": supplier_name,
                    "created_at": now,
                }).execute()
                supplier_id = new_sup.data[0]["id"] if new_sup.data else None
            if supplier_id:
                db_client.table("pms_purchase_orders").update(
                    {"supplier_id": supplier_id, "updated_at": now}
                ).eq("id", po_id).execute()
        except Exception as sup_err:
            logger.warning(f"[create_purchase_order] Supplier resolve failed: {sup_err}")

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="create",
            entity_type="purchase_order", entity_id=po_id, action="create_purchase_order",
            user_role=user_context.get("role"),
            change_summary=f"PO created: {po_number}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record create_purchase_order: {ledger_err}")

    # Data continuity: draft PO has no items yet — remind creator to complete it
    _push_po_notification(
        db_client=db_client, yacht_id=yacht_id, user_id=user_id,
        notification_type="purchase_order.draft_created",
        title=f"{po_number} created — add items to order",
        body="Draft PO is open. Add line items and confirm the supplier before submitting for approval.",
        entity_id=po_id,
    )

    return {"status": "success", "purchase_order_id": po_id, "po_number": po_number}


# ============================================================================
# deny_po_line_item — reject a single line from a PO, with mandatory reason
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

    # Confirm item belongs to this yacht
    check = db_client.table("pms_purchase_order_items").select(
        "id, purchase_order_id"
    ).eq("id", po_item_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not check or not check.data:
        raise HTTPException(status_code=404, detail="Line item not found")
    po_id = check.data["purchase_order_id"]

    now = datetime.now(timezone.utc).isoformat()
    db_client.table("pms_purchase_order_items").update({
        "line_status": "denied",
        "denied_at": now,
        "denial_reason": denial_reason,
    }).eq("id", po_item_id).eq("yacht_id", yacht_id).execute()

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="status_change",
            entity_type="purchase_order", entity_id=po_id, action="deny_po_line_item",
            user_role=user_context.get("role"),
            change_summary=f"Line item denied: {denial_reason}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record deny_po_line_item: {ledger_err}")

    return {"status": "success", "po_item_id": po_item_id, "line_status": "denied"}


# ============================================================================
# add_tracking_details — record carrier/tracking/delivery window, auto-advance
# approved → ordered when tracking_number OR delivery window is provided
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
        raise HTTPException(status_code=400, detail="Provide tracking_number or expected_delivery_start/end")

    # Fetch current PO
    po_row = db_client.table("pms_purchase_orders").select(
        "status, po_number"
    ).eq("id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not po_row or not po_row.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    current_status = po_row.data.get("status", "")
    po_number = po_row.data.get("po_number", "PO")

    # Auto-advance approved → ordered when logistics info is provided
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
        "id", po_id
    ).eq("yacht_id", yacht_id).execute()

    advanced = current_status == "approved"

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id,
            event_type="status_change" if advanced else "annotation",
            entity_type="purchase_order", entity_id=po_id, action="add_tracking_details",
            user_role=user_context.get("role"),
            change_summary=f"Tracking added{' — status → ordered' if advanced else ''}. "
                           f"{'Tracking: ' + tracking_number + '. ' if tracking_number else ''}"
                           f"{'Expected: ' + (delivery_start or '') + (' – ' + delivery_end if delivery_end else '') if delivery_start else ''}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record add_tracking_details: {ledger_err}")

    if advanced:
        # Notify that order is placed and goods are expected
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
        "status": "success",
        "purchase_order_id": po_id,
        "advanced_to_ordered": advanced,
        "tracking_number": tracking_number,
    }


# ============================================================================
# update_supplier_on_po — change the linked supplier on a draft/approved PO
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

    update: dict = {"updated_at": datetime.utcnow().isoformat()}
    if supplier_id:
        update["supplier_id"] = supplier_id
    if supplier_name:
        update["supplier_name"] = supplier_name

    db_client.table("pms_purchase_orders").update(update).eq("id", po_id).eq("yacht_id", yacht_id).execute()

    try:
        from routes.handlers.ledger_utils import build_ledger_event
        db_client.table("pms_ledger_events").insert(build_ledger_event(
            yacht_id=yacht_id, user_id=user_id,
            entity_type="purchase_order", entity_id=po_id, action="update_supplier_on_po",
            description=f"Supplier updated to '{supplier_name or supplier_id}'",
            metadata={"supplier_id": supplier_id, "supplier_name": supplier_name},
        )).execute()
    except Exception as ledger_err:
        logger.warning(f"[Ledger] Failed to record update_supplier_on_po: {ledger_err}")

    return {"status": "success", "purchase_order_id": po_id, "supplier_id": supplier_id, "supplier_name": supplier_name}


# ============================================================================
# upload_invoice — attach an invoice document to a PO (Issue #14, 2026-04-23)
#
# Frontend uploads the file to the "pms-finance-documents" bucket first
# (Supabase Storage). That call returns the storage_path, which is passed
# to this action. We just record the pms_attachments row — no byte movement.
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
    mime_type = payload.get("mime_type") or "application/octet-stream"
    file_size = payload.get("file_size") or 0

    po = db_client.table("pms_purchase_orders").select("id").eq(
        "id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not po or not po.data:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    now = datetime.now(timezone.utc).isoformat()
    att_row = {
        "yacht_id":          yacht_id,
        "entity_type":       "purchase_order",
        "entity_id":         po_id,
        "filename":          filename,
        "original_filename": filename,
        "mime_type":         mime_type,
        "file_size":         int(file_size or 0),
        "storage_path":      storage_path,
        "storage_bucket":    payload.get("storage_bucket") or "pms-finance-documents",
        "category":          "invoice",
        "description":       payload.get("description") or payload.get("notes"),
        "uploaded_by":       user_id,
        "uploaded_at":       now,
    }
    ins = db_client.table("pms_attachments").insert(att_row).execute()
    if not ins.data:
        return {"status": "error", "error_code": "INSERT_FAILED",
                "message": "Failed to record invoice attachment"}
    attachment_id = ins.data[0].get("id") if isinstance(ins.data, list) else None

    db_client.table("pms_purchase_orders").update(
        {"updated_at": now}
    ).eq("id", po_id).eq("yacht_id", yacht_id).execute()

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="annotation",
            entity_type="purchase_order", entity_id=po_id, action="upload_invoice",
            user_role=user_context.get("role"),
            change_summary=f"Invoice attached: {filename}",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed to record upload_invoice: {ledger_err}")
    return {"status": "success", "purchase_order_id": po_id, "attachment_id": attachment_id}


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    "submit_purchase_order": submit_purchase_order,
    "approve_purchase_order": approve_purchase_order,
    "mark_po_received": mark_po_received,
    "cancel_purchase_order": cancel_purchase_order,
    "delete_purchase_order": delete_purchase_order,
    "add_po_note": add_po_note,
    "update_purchase_status": update_purchase_status,
    "add_item_to_purchase": add_item_to_purchase,
    "upload_invoice": upload_invoice,
    "create_purchase_order": create_purchase_order,
    "deny_po_line_item": deny_po_line_item,
    "add_tracking_details": add_tracking_details,
    "update_supplier_on_po": update_supplier_on_po,
    # Frontend-facing aliases (match action IDs used by PurchaseOrderContent.tsx)
    "submit_po": submit_purchase_order,
    "approve_po": approve_purchase_order,
    "receive_po": mark_po_received,
    "cancel_po": cancel_purchase_order,
    "delete_po": delete_purchase_order,
    "approve_purchase": approve_purchase_order,
}
