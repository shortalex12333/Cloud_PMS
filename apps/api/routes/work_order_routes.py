"""
Work Order Routes
=================

API endpoints for work order management.

Includes:
- GET / - List work orders with pagination
- Yacht isolation via JWT authentication
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
import logging
import os

# Auth middleware
from middleware.auth import get_authenticated_user

# Centralized Supabase client factory
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class WorkOrderListParams(BaseModel):
    """Query parameters for listing work orders."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    status: Optional[str] = None
    priority: Optional[str] = None
    equipment_id: Optional[str] = None


class WorkOrderResponse(BaseModel):
    """Response schema for a single work order."""
    id: str
    wo_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    equipment_id: Optional[str] = None
    equipment_name: Optional[str] = None
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class WorkOrderListResponse(BaseModel):
    """Response schema for work order list endpoint."""
    data: List[Dict[str, Any]]
    total: int


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/", response_model=WorkOrderListResponse)
async def list_work_orders(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    equipment_id: Optional[UUID] = Query(default=None),
    auth: dict = Depends(get_authenticated_user)
):
    """
    List all work orders for the authenticated yacht.

    Returns paginated list with yacht_id isolation via JWT.

    Query Parameters:
    - offset: Pagination offset (default: 0)
    - limit: Number of results (default: 50, max: 100)
    - status: Filter by status (optional)
    - priority: Filter by priority (optional)
    - equipment_id: Filter by equipment (optional)

    Returns:
    - data: List of work orders
    - total: Total count for pagination
    """
    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])

        # Build query - select fields matching frontend WorkOrder type
        query = supabase.table("pms_work_orders").select(
            "id, wo_number, title, description, status, priority, equipment_id, equipment_name, assigned_to_id, assigned_to_name, due_date, created_at, updated_at",
            count="exact"
        ).eq("yacht_id", auth["yacht_id"])

        # Apply optional filters
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        if equipment_id:
            query = query.eq("equipment_id", str(equipment_id))

        # Execute with pagination and ordering
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        work_orders = result.data or []
        total_count = result.count or len(work_orders)

        return WorkOrderListResponse(
            data=work_orders,
            total=total_count,
        )

    except Exception as e:
        logger.error(f"Failed to list work orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{work_order_id}")
async def get_work_order(
    work_order_id: UUID,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get a single work order by ID.

    Returns work order details with yacht_id isolation.
    """
    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])

        result = supabase.table("pms_work_orders").select(
            "id, wo_number, title, description, status, priority, equipment_id, equipment_name, assigned_to_id, assigned_to_name, due_date, created_at, updated_at"
        ).eq("id", str(work_order_id)).eq("yacht_id", auth["yacht_id"]).maybe_single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Work order not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get work order {work_order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
