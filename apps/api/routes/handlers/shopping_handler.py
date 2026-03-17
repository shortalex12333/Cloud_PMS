"""
Shopping Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 5).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
Import build_ledger_event from routes.handlers.ledger_utils, not from p0_actions_routes.

Block 1 (L2646-2696): delete_shopping_item — inline with RBAC.
Block 2 (L4962-5034): create_shopping_list_item, approve_shopping_list_item,
    reject_shopping_list_item, promote_candidate_to_part, view_shopping_list_history
    — delegates to handlers.shopping_list_handlers.ShoppingListHandlers.
Block 3 (L5132-5163): mark_shopping_list_ordered — inline with ledger event.
"""
import re
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)

# RBAC for shopping list Lens v1 actions (from original L4969-4974)
_SHOPPING_LIST_ROLES = {
    "create_shopping_list_item": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
    "approve_shopping_list_item": ["chief_engineer", "chief_officer", "captain", "manager"],
    "reject_shopping_list_item": ["chief_engineer", "chief_officer", "captain", "manager"],
    "promote_candidate_to_part": ["chief_engineer", "manager"],
    "view_shopping_list_history": ["crew", "chief_engineer", "chief_officer", "captain", "manager"],
}

# RBAC for delete_shopping_item (from original L2648)
_DELETE_ITEM_ROLES = ["chief_engineer", "chief_officer", "captain", "manager"]

# RBAC for mark_shopping_list_ordered (from original L5134)
_MARK_ORDERED_ROLES = ["chief_engineer", "captain", "manager"]


# ============================================================================
# delete_shopping_item  (was L2646-2696)
# ============================================================================
async def delete_shopping_item(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    user_role = user_context.get("role", "")
    if user_role not in _DELETE_ITEM_ROLES:
        logger.warning(f"[RBAC] Role '{user_role}' denied for action 'delete_shopping_item'. Allowed: {_DELETE_ITEM_ROLES}")
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to perform action 'delete_shopping_item'",
            "required_roles": _DELETE_ITEM_ROLES,
        }

    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, str(item_id), re.IGNORECASE):
        raise HTTPException(status_code=400, detail="item_id must be a valid UUID")

    try:
        check = db_client.table("pms_shopping_list_items").select("id").eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if not check or not check.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        db_client.table("pms_shopping_list_items").delete().eq("id", item_id).eq("yacht_id", yacht_id).execute()

        return {
            "status": "success",
            "success": True,
            "item_id": item_id,
            "message": "Shopping list item deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str.lower() or "42P01" in error_str:
            raise HTTPException(status_code=404, detail="Shopping list feature not available")
        if "immutable" in error_str.lower() or "finance transactions" in error_str.lower():
            raise HTTPException(status_code=409, detail="Cannot delete: item is linked to a finance transaction. Use reversal instead.")
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")


# ============================================================================
# Shopping List Lens v1 actions (L4962-5034) — delegate to ShoppingListHandlers
# ============================================================================

async def _shopping_list_delegate(
    action: str,
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    """Shared dispatcher for Shopping List Lens v1 actions."""
    from handlers.shopping_list_handlers import ShoppingListHandlers
    shopping_list_handlers = ShoppingListHandlers(db_client)

    user_role = user_context.get("role", "")
    allowed_roles = _SHOPPING_LIST_ROLES.get(action, [])
    if user_role not in allowed_roles:
        logger.warning(f"[RBAC] Role '{user_role}' denied for action '{action}'. Allowed: {allowed_roles}")
        return {
            "success": False,
            "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to perform action '{action}'",
            "required_roles": allowed_roles,
        }

    handler_map = {
        "create_shopping_list_item": shopping_list_handlers.create_shopping_list_item,
        "approve_shopping_list_item": shopping_list_handlers.approve_shopping_list_item,
        "reject_shopping_list_item": shopping_list_handlers.reject_shopping_list_item,
        "promote_candidate_to_part": shopping_list_handlers.promote_candidate_to_part,
        "view_shopping_list_history": shopping_list_handlers.view_shopping_list_history,
    }

    handler_fn = handler_map[action]

    # State machine validation for mutating actions (from original L5000-5021)
    if action in ("approve_shopping_list_item", "reject_shopping_list_item", "promote_candidate_to_part"):
        item_id = payload.get("item_id") or payload.get("shopping_list_item_id") or context.get("shopping_list_item_id")
        if item_id:
            try:
                item = db_client.table("pms_shopping_list_items").select("status").eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if item and item.data:
                    current_status = item.data.get("status", "candidate")
                    try:
                        from action_router.middleware import validate_state_transition, InvalidStateTransitionError
                        validate_state_transition("shopping_list", current_status, action)
                    except InvalidStateTransitionError as e:
                        logger.warning(f"[STATE] {e.message}")
                        return {
                            "success": False,
                            "code": e.code,
                            "message": e.message,
                            "current_status": current_status,
                        }
            except Exception as db_err:
                logger.debug(f"[STATE] Could not check item status: {db_err}")

    # Add user context to payload (from original L5024-5026)
    payload["user_id"] = user_id
    payload["user_role"] = user_context.get("role")
    payload["user_name"] = user_context.get("name", "Unknown")

    entity_id = (payload.get("item_id") or payload.get("shopping_list_item_id")
                 or context.get("shopping_list_item_id"))

    return await handler_fn(
        entity_id=entity_id,
        yacht_id=yacht_id,
        params=payload,
    )


async def create_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    return await _shopping_list_delegate(
        "create_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def approve_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    return await _shopping_list_delegate(
        "approve_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def reject_shopping_list_item(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    return await _shopping_list_delegate(
        "reject_shopping_list_item", payload, context, yacht_id, user_id, user_context, db_client)


async def promote_candidate_to_part(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    return await _shopping_list_delegate(
        "promote_candidate_to_part", payload, context, yacht_id, user_id, user_context, db_client)


async def view_shopping_list_history(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    return await _shopping_list_delegate(
        "view_shopping_list_history", payload, context, yacht_id, user_id, user_context, db_client)


# ============================================================================
# mark_shopping_list_ordered  (was L5132-5163)
# ============================================================================
async def mark_shopping_list_ordered(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    user_role = user_context.get("role", "")
    if user_role not in _MARK_ORDERED_ROLES:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not permitted to perform 'mark_shopping_list_ordered'",
            "required_roles": _MARK_ORDERED_ROLES,
        })

    item_id = (payload.get("item_id") or payload.get("shopping_list_item_id")
               or context.get("shopping_list_item_id") or context.get("shopping_list_id"))
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    update_data = {"status": "ordered", "updated_at": datetime.now(timezone.utc).isoformat()}
    upd = db_client.table("pms_shopping_list_items").update(update_data).eq("id", item_id).eq("yacht_id", yacht_id).execute()
    if upd.data:
        try:
            ledger_event = build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="shopping_list_item", entity_id=item_id, action="mark_shopping_list_ordered",
                user_role=user_context.get("role"), change_summary="Shopping list item marked as ordered",
            )
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record mark_shopping_list_ordered: {ledger_err}")
        return {"status": "success", "message": "Shopping list item marked as ordered"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to mark shopping list item as ordered"}


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    "delete_shopping_item": delete_shopping_item,
    "create_shopping_list_item": create_shopping_list_item,
    "approve_shopping_list_item": approve_shopping_list_item,
    "reject_shopping_list_item": reject_shopping_list_item,
    "promote_candidate_to_part": promote_candidate_to_part,
    "view_shopping_list_history": view_shopping_list_history,
    "mark_shopping_list_ordered": mark_shopping_list_ordered,
}
