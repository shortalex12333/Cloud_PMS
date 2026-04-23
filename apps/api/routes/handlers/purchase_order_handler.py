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

logger = logging.getLogger(__name__)

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
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    "submit_purchase_order": submit_purchase_order,
    "approve_purchase_order": approve_purchase_order,
    "mark_po_received": mark_po_received,
    "cancel_purchase_order": cancel_purchase_order,
    "delete_purchase_order": delete_purchase_order,
    # Frontend-facing aliases (match action IDs used by PurchaseOrderContent.tsx)
    "submit_po": submit_purchase_order,
    "approve_po": approve_purchase_order,
    "receive_po": mark_po_received,
    "cancel_po": cancel_purchase_order,
    "delete_po": delete_purchase_order,
}
