"""
Receiving Action Handlers (inline — no internal_dispatcher)

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 3).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
Import build_ledger_event from routes.handlers.ledger_utils, not from p0_actions_routes.

NOTE: The Receiving Lens v1 actions (create_receiving, attach_receiving_image_with_comment,
extract_receiving_candidates, update_receiving_fields, add_receiving_item, adjust_receiving_item,
link_invoice_document, accept_receiving, reject_receiving, view_receiving_history) use a
completely different dispatch path via action_router.dispatchers.internal_dispatcher and remain
in p0_actions_routes.py for now. Only the inline receiving actions are migrated here.
"""
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


# ============================================================================
# submit_receiving_for_review  (was L5376-5398)
# ============================================================================
async def submit_receiving_for_review(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    receiving_id = payload.get("receiving_id") or context.get("receiving_id")
    if not receiving_id:
        raise HTTPException(status_code=400, detail="receiving_id is required")
    upd = db_client.table("pms_receiving").update({
        "status": "in_review"
    }).eq("id", receiving_id).eq("yacht_id", yacht_id).execute()
    if upd.data:
        try:
            db_client.table("ledger_events").insert(build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="receiving", entity_id=receiving_id, action="submit_receiving_for_review",
                user_role=user_context.get("role"), change_summary="Receiving submitted for review",
            )).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record submit_receiving_for_review: {ledger_err}")
        return {"status": "success", "message": "Receiving submitted for review"}
    else:
        return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to submit receiving for review"}


# ============================================================================
# edit_receiving  (was L5400-5421)
# ============================================================================
async def edit_receiving(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    receiving_id = payload.get("receiving_id") or context.get("receiving_id")
    if not receiving_id:
        raise HTTPException(status_code=400, detail="receiving_id is required")
    # edit_receiving returns current record data so the UI can populate edit form
    rec = db_client.table("pms_receiving").select("*").eq("id", receiving_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if rec.data:
        try:
            db_client.table("ledger_events").insert(build_ledger_event(
                yacht_id=yacht_id, user_id=user_id, event_type="view",
                entity_type="receiving", entity_id=receiving_id, action="edit_receiving",
                user_role=user_context.get("role"), change_summary="Receiving record opened for editing",
            )).execute()
        except Exception as ledger_err:
            if "204" not in str(ledger_err):
                logger.warning(f"[Ledger] Failed to record edit_receiving: {ledger_err}")
        return {"status": "success", "message": "Receiving record ready for editing", "data": rec.data}
    else:
        return {"status": "error", "error_code": "NOT_FOUND", "message": "Receiving record not found"}


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    "submit_receiving_for_review": submit_receiving_for_review,
    "edit_receiving": edit_receiving,
}
