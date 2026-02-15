"""
Ledger API Routes

Provides endpoints for fetching ledger events from the tenant database.
Frontend (Vercel) calls these endpoints since it only has access to Master DB.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, date
import logging

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
    event_type: Optional[str] = Query(default=None, description="Filter by event_type: mutation, read"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity_type: work_order, fault, etc."),
    date_from: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    user_context: dict = Depends(get_authenticated_user)
):
    """
    Fetch ledger events for the current user's yacht.
    Returns events in reverse chronological order.
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

        # Apply filters
        if event_type:
            query = query.eq("event_type", event_type)

        if entity_type:
            query = query.eq("entity_type", entity_type)

        if date_from:
            query = query.gte("event_timestamp", f"{date_from}T00:00:00Z")

        if date_to:
            query = query.lte("event_timestamp", f"{date_to}T23:59:59Z")

        # Order and paginate
        query = query.order("event_timestamp", desc=True)
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
