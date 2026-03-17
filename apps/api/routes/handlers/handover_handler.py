"""
Handover Action Handlers

Migrated from p0_actions_routes.py elif blocks (Phase 4, Task 5).
Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.

Block 1 (L2548-2553): create_handover, acknowledge_handover, update_handover, delete_handover,
    filter_handover — BLOCKED: dash_handover_items.handover_id NOT NULL but no parent table.
Block 2 (L1982-2064): add_to_handover — delegates to handlers.handover_handlers.HandoverHandlers.
Block 3 (L3702-3754): add_document_to_handover — inline.
Block 4 (L3756-3808): add_predictive_insight_to_handover — inline.
Block 5 (L3810-3860): edit_handover_section — inline.
Block 6 (L3862-3904): export_handover — inline.
Block 7 (L3906-3947): regenerate_handover_summary — inline.
"""
import logging
import uuid as uuid_module
from datetime import datetime, timezone

from fastapi import HTTPException
from supabase import Client

logger = logging.getLogger(__name__)


# ============================================================================
# BLOCKED ACTIONS (L2548-2553) — parent handovers table does not exist yet
# ============================================================================

async def create_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'create_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
    )


async def acknowledge_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'acknowledge_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
    )


async def update_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'update_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
    )


async def delete_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'delete_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
    )


async def filter_handover(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Action 'filter_handover' BLOCKED: dash_handover_items.handover_id is NOT NULL but no parent handovers table exists."
    )


# ============================================================================
# add_to_handover  (was L1982-2064 — delegates to HandoverHandlers)
# ============================================================================
async def add_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    from handlers.handover_handlers import HandoverHandlers
    handover_handlers = HandoverHandlers(db_client)

    # Support multiple payload formats for backwards compatibility (from original L1987-1996)
    summary = payload.get("summary") or payload.get("summary_text")
    if not summary:
        title = payload.get("title")
        description = payload.get("description", "")
        summary = f"{title}\n\n{description}" if title and description else (title or description or "")

    if not summary or len(summary) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Summary must be at least 10 characters"
            }
        )

    entity_type = payload.get("entity_type", "note")
    entity_id = payload.get("entity_id")
    category = payload.get("category", "fyi")
    priority = payload.get("priority", "normal")
    is_critical = payload.get("is_critical", False)
    requires_action = payload.get("requires_action", False)
    action_summary = payload.get("action_summary")
    section = payload.get("section") or payload.get("presentation_bucket")

    try:
        result = await handover_handlers.add_to_handover_execute(
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            category=category,
            yacht_id=yacht_id,
            user_id=user_id,
            priority=priority,
            section=section,
            is_critical=is_critical,
            requires_action=requires_action,
            action_summary=action_summary,
        )

        # Map handler errors to HTTP exceptions (from original L2033-2051)
        if result.get("status") == "error":
            error_code = result.get("error_code")
            status_code = 400
            if error_code == "INTERNAL_ERROR":
                status_code = 500
            raise HTTPException(
                status_code=status_code,
                detail={
                    "status": "error",
                    "error_code": error_code,
                    "message": result.get("message")
                }
            )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in add_to_handover: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to add to handover: {str(e)}"
            }
        )


# ============================================================================
# _find_handover — shared helper for handover lookup across both table names
# ============================================================================
def _find_handover(db_client: Client, handover_id: str, yacht_id: str, columns: str = "id"):
    """Try 'handovers' then 'handover' table. Returns (data, table_name) or raises 404."""
    handover = db_client.table("handovers").select(columns).eq(
        "id", handover_id
    ).eq("yacht_id", yacht_id).maybe_single().execute()
    table_name = "handovers"

    if not handover.data:
        handover = db_client.table("handover").select(columns).eq(
            "id", handover_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()
        table_name = "handover"

    if not handover.data:
        raise HTTPException(status_code=404, detail="Handover not found")

    return handover, table_name


# ============================================================================
# add_document_to_handover  (was L3702-3754)
# ============================================================================
async def add_document_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    document_id = payload.get("document_id")
    summary = payload.get("summary", "")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    _find_handover(db_client, handover_id, yacht_id)

    try:
        item_data = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "handover_id": handover_id,
            "entity_id": document_id,
            "entity_type": "document",
            "summary": summary or "Document attached",
            "added_by": user_id,
            "status": "pending",
        }
        db_client.table("handover_items").insert(item_data).execute()
    except Exception:
        pass  # Table may not exist

    return {
        "status": "success",
        "success": True,
        "message": "Document added to handover",
        "handover_id": handover_id,
        "document_id": document_id,
    }


# ============================================================================
# add_predictive_insight_to_handover  (was L3756-3808)
# ============================================================================
async def add_predictive_insight_to_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    insight_text = payload.get("insight_text")
    insight_type = payload.get("insight_type", "general")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")
    if not insight_text:
        raise HTTPException(status_code=400, detail="insight_text is required")

    handover, table_name = _find_handover(db_client, handover_id, yacht_id, "id, metadata")

    metadata = handover.data.get("metadata", {}) or {}
    insights = metadata.get("predictive_insights", []) or []
    insights.append({
        "text": insight_text,
        "type": insight_type,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["predictive_insights"] = insights

    db_client.table(table_name).update({
        "metadata": metadata,
        "updated_by": user_id,
    }).eq("id", handover_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Predictive insight added to handover",
        "handover_id": handover_id,
        "insights_count": len(insights),
    }


# ============================================================================
# edit_handover_section  (was L3810-3860)
# ============================================================================
async def edit_handover_section(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    section_name = payload.get("section_name")
    section_content = payload.get("content", "")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")
    if not section_name:
        raise HTTPException(status_code=400, detail="section_name is required")

    handover, table_name = _find_handover(db_client, handover_id, yacht_id, "id, metadata")

    metadata = handover.data.get("metadata", {}) or {}
    sections = metadata.get("sections", {}) or {}
    sections[section_name] = {
        "content": section_content,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata["sections"] = sections

    db_client.table(table_name).update({
        "metadata": metadata,
        "updated_by": user_id,
    }).eq("id", handover_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": f"Handover section '{section_name}' updated",
        "handover_id": handover_id,
        "section_name": section_name,
    }


# ============================================================================
# export_handover  (was L3862-3904)
# ============================================================================
async def export_handover(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")
    export_format = payload.get("format", "pdf")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")

    # Get handover with all fields
    handover = db_client.table("handovers").select("*").eq(
        "id", handover_id
    ).eq("yacht_id", yacht_id).maybe_single().execute()

    if not handover.data:
        handover = db_client.table("handover").select("*").eq(
            "id", handover_id
        ).eq("yacht_id", yacht_id).maybe_single().execute()

    if not handover.data:
        raise HTTPException(status_code=404, detail="Handover not found")

    # Get items if using handover_items table
    items = []
    try:
        items_result = db_client.table("handover_items").select("*").eq(
            "handover_id", handover_id
        ).execute()
        items = items_result.data or []
    except Exception:
        pass

    return {
        "status": "success",
        "success": True,
        "handover": handover.data,
        "items": items,
        "export_format": export_format,
        "message": f"Handover ready for {export_format} export",
    }


# ============================================================================
# regenerate_handover_summary  (was L3906-3947)
# ============================================================================
async def regenerate_handover_summary(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,
) -> dict:
    handover_id = payload.get("handover_id")

    if not handover_id:
        raise HTTPException(status_code=400, detail="handover_id is required")

    handover, table_name = _find_handover(db_client, handover_id, yacht_id, "id, metadata")

    metadata = handover.data.get("metadata", {}) or {}
    metadata["summary_regeneration_requested"] = True
    metadata["summary_regeneration_requested_at"] = datetime.now(timezone.utc).isoformat()
    metadata["summary_regeneration_requested_by"] = user_id

    db_client.table(table_name).update({
        "metadata": metadata,
        "updated_by": user_id,
    }).eq("id", handover_id).execute()

    return {
        "status": "success",
        "success": True,
        "message": "Summary regeneration requested",
        "handover_id": handover_id,
    }


# ============================================================================
# HANDLER REGISTRY
# ============================================================================
HANDLERS: dict = {
    # Blocked actions (501)
    "create_handover": create_handover,
    "acknowledge_handover": acknowledge_handover,
    "update_handover": update_handover,
    "delete_handover": delete_handover,
    "filter_handover": filter_handover,
    # Live actions
    "add_to_handover": add_to_handover,
    "add_document_to_handover": add_document_to_handover,
    "add_predictive_insight_to_handover": add_predictive_insight_to_handover,
    "edit_handover_section": edit_handover_section,
    "export_handover": export_handover,
    "regenerate_handover_summary": regenerate_handover_summary,
}
