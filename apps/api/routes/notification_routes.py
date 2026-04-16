"""
Notification API Routes
=======================

GET  /v1/notifications                         — list notifications for current user+yacht
PATCH /v1/notifications/{notification_id}/read  — mark one notification as read
PATCH /v1/notifications/mark-all-read           — mark all unread notifications as read

All queries scope by yacht_id AND user_id. No exceptions.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime, timezone
import logging

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id

logger = logging.getLogger(__name__)


def _get_tenant_client(tenant_key_alias: str):
    """Get tenant-specific Supabase client."""
    from integrations.supabase import get_tenant_client
    return get_tenant_client(tenant_key_alias)


router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    unread_only: bool = Query(default=True, description="Only return unread notifications"),
    limit: int = Query(default=20, le=50, ge=1, description="Max notifications to return"),
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Fetch notifications for the current user scoped to their yacht.
    Returns newest first. Default: unread only, 20 items.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)
        user_id = user_context.get("user_id", "")

        db_client = _get_tenant_client(tenant_alias)

        query = (
            db_client.table("pms_notifications")
            .select("id, notification_type, title, body, priority, entity_type, entity_id, is_read, created_at")
            .eq("yacht_id", yacht_id)
            .eq("user_id", user_id)
        )

        if unread_only:
            query = query.eq("is_read", False)

        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()

        notifications = result.data if result.data else []

        # Unread count (always full count, regardless of limit)
        count_query = (
            db_client.table("pms_notifications")
            .select("id", count="exact")
            .eq("yacht_id", yacht_id)
            .eq("user_id", user_id)
            .eq("is_read", False)
        )
        count_result = count_query.execute()
        unread_count = count_result.count if count_result.count is not None else 0

        return {
            "status": "success",
            "unread_count": unread_count,
            "notifications": notifications,
        }

    except Exception as e:
        logger.error(f"Failed to fetch notifications: {e}")
        # Fire-and-forget: return empty list, not 500
        return {
            "status": "success",
            "unread_count": 0,
            "notifications": [],
        }


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Mark a single notification as read.
    Scoped by yacht_id AND user_id — users can only mark their own.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)
        user_id = user_context.get("user_id", "")

        db_client = _get_tenant_client(tenant_alias)

        # Verify the notification belongs to this user+yacht
        check = (
            db_client.table("pms_notifications")
            .select("id")
            .eq("id", notification_id)
            .eq("yacht_id", yacht_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not check.data:
            raise HTTPException(status_code=404, detail="Notification not found")

        now = datetime.now(timezone.utc).isoformat()

        db_client.table("pms_notifications").update(
            {"is_read": True, "read_at": now}
        ).eq("id", notification_id).eq("yacht_id", yacht_id).eq("user_id", user_id).execute()

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification {notification_id} as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")


@router.patch("/mark-all-read")
async def mark_all_notifications_read(
    yacht_id: Optional[str] = Query(default=None, description="Vessel scope (fleet users)"),
    user_context: dict = Depends(get_authenticated_user),
):
    """
    Mark all unread notifications as read for this user+yacht.
    Returns the count of notifications that were marked.
    """
    try:
        tenant_alias = user_context.get("tenant_key_alias", "")
        yacht_id = resolve_yacht_id(user_context, yacht_id)
        user_id = user_context.get("user_id", "")

        db_client = _get_tenant_client(tenant_alias)

        # Count unread first so we can report how many were marked
        count_query = (
            db_client.table("pms_notifications")
            .select("id", count="exact")
            .eq("yacht_id", yacht_id)
            .eq("user_id", user_id)
            .eq("is_read", False)
        )
        count_result = count_query.execute()
        unread_count = count_result.count if count_result.count is not None else 0

        if unread_count > 0:
            now = datetime.now(timezone.utc).isoformat()

            db_client.table("pms_notifications").update(
                {"is_read": True, "read_at": now}
            ).eq("yacht_id", yacht_id).eq("user_id", user_id).eq("is_read", False).execute()

        return {"status": "success", "marked": unread_count}

    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark notifications as read")
