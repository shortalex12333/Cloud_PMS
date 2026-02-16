"""
Ledger API Routes

Provides endpoints for fetching ledger events from the tenant database.
Frontend (Vercel) calls these endpoints since it only has access to Master DB.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, date
import logging
import hashlib
import json

from middleware.auth import get_authenticated_user

logger = logging.getLogger(__name__)


def _get_tenant_client(tenant_key_alias: str):
    """Get tenant-specific Supabase client. Lazy import to avoid circular deps."""
    from pipeline_service import get_tenant_client
    return get_tenant_client(tenant_key_alias)

router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


@router.get("/events")
async def get_ledger_events(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: Optional[str] = Query(default=None, description="Filter by specific user_id (for 'Me' view)"),
    action: Optional[str] = Query(default=None, description="Filter by action: add_note, artefact_opened, etc."),
    date_from: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch ledger events for the current user's yacht.
    Returns events in reverse chronological order.
    - If user_id is provided, filters to only that user's events (Me view)
    - If user_id is not provided, returns all yacht events (Department view)
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = user_context.get("yacht_id")

        if not yacht_id:
            raise HTTPException(status_code=400, detail="No yacht_id in user context")

        db_client = _get_tenant_client(tenant_alias)

        # Build query
        query = db_client.table("ledger_events").select("*")

        # Filter by yacht (RLS should handle this, but be explicit)
        query = query.eq("yacht_id", yacht_id)

        # Filter by user_id if provided (Me view)
        if user_id:
            query = query.eq("user_id", user_id)

        # Filter by action if provided
        if action:
            query = query.eq("action", action)

        if date_from:
            query = query.gte("created_at", f"{date_from}T00:00:00Z")

        if date_to:
            query = query.lte("created_at", f"{date_to}T23:59:59Z")

        # Order and paginate (use created_at since that's the actual column)
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)

        result = query.execute()

        return {
            "success": True,
            "events": result.data or [],
            "count": len(result.data or []),
            "offset": offset,
            "limit": limit,
            "has_more": len(result.data or []) == limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch ledger events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch ledger events: {str(e)}")


@router.get("/events/by-entity/{entity_type}/{entity_id}")
async def get_entity_ledger_events(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=50, le=100),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch ledger events for a specific entity.
    Useful for showing history on entity detail pages.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = user_context.get("yacht_id")

        if not yacht_id:
            raise HTTPException(status_code=400, detail="No yacht_id in user context")

        db_client = _get_tenant_client(tenant_alias)

        result = db_client.table("ledger_events").select("*").eq(
            "yacht_id", yacht_id
        ).eq(
            "entity_type", entity_type
        ).eq(
            "entity_id", entity_id
        ).order(
            "event_timestamp", desc=True
        ).limit(limit).execute()

        return {
            "success": True,
            "events": result.data or [],
            "entity_type": entity_type,
            "entity_id": entity_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch entity ledger events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch entity ledger events: {str(e)}")


@router.get("/day-anchors")
async def get_day_anchors(
    days: int = Query(default=30, le=90, description="Number of days to fetch"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch day anchor summaries for the ledger UI.
    Shows mutation/read counts per day.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = user_context.get("yacht_id")

        if not yacht_id:
            raise HTTPException(status_code=400, detail="No yacht_id in user context")

        db_client = _get_tenant_client(tenant_alias)

        # Get day anchors
        result = db_client.table("ledger_day_anchors").select("*").eq(
            "yacht_id", yacht_id
        ).order(
            "anchor_date", desc=True
        ).limit(days).execute()

        return {
            "success": True,
            "anchors": result.data or [],
            "days_requested": days
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch day anchors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch day anchors: {str(e)}")


@router.post("/record")
async def record_ledger_event(
    event_data: dict,
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Record a ledger event from the frontend.
    Used for tracking read events like artefact_opened.

    Required fields:
    - action: The action being performed (e.g., artefact_opened)
    - entity_type: Type of entity (e.g., work_order, fault)
    - entity_id: UUID of the entity

    Optional:
    - metadata: Additional context data
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = user_context.get("yacht_id")
        user_id = user_context.get("user_id")

        if not yacht_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing yacht_id or user_id in context")

        # Support both old (event_name) and new (action) field names for backwards compatibility
        action_name = event_data.get("action") or event_data.get("event_name")
        entity_type = event_data.get("entity_type") or event_data.get("payload", {}).get("artefact_type", "unknown")
        entity_id = event_data.get("entity_id") or event_data.get("payload", {}).get("artefact_id")
        metadata = event_data.get("metadata") or event_data.get("payload", {})

        if not action_name:
            raise HTTPException(status_code=400, detail="action or event_name is required")

        if not entity_id:
            raise HTTPException(status_code=400, detail="entity_id is required")

        db_client = _get_tenant_client(tenant_alias)

        # Map action to event_type (read events map to specific types)
        event_type_map = {
            "artefact_opened": "update",  # Read events are tracked as updates
            "situation_ended": "status_change",
            "view": "update",
            "open": "update",
        }
        event_type = event_type_map.get(action_name, "update")

        # Generate proof_hash
        hash_input = json.dumps({
            "yacht_id": str(yacht_id),
            "user_id": str(user_id),
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action_name,
            "timestamp": datetime.utcnow().isoformat()
        }, sort_keys=True)
        proof_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        # Build ledger event using correct schema
        ledger_event = {
            "yacht_id": str(yacht_id),
            "user_id": str(user_id),
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action_name,
            "user_role": user_context.get("role", "member"),
            "source_context": "search",  # Frontend events come from search
            "metadata": {
                **metadata,
                "user_role": user_context.get("role", "member"),
            },
            "proof_hash": proof_hash
        }

        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
            logger.info(f"[Ledger] Recorded {action_name} for user {user_id}")
        except Exception as insert_err:
            if "204" in str(insert_err):
                logger.info(f"[Ledger] {action_name} recorded (204)")
            else:
                logger.warning(f"[Ledger] Failed to record {action_name}: {insert_err}")
                raise

        return {"success": True, "message": f"Event {action_name} recorded"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record ledger event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record ledger event: {str(e)}")
