"""
Work Order API endpoints
/v1/work-orders routes
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.auth import get_current_user, YachtContext
from app.core.supabase import supabase_client

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


class CreateWorkOrderRequest(BaseModel):
    """Create work order request"""
    equipment_id: UUID
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical
    type: str = "corrective"  # scheduled, corrective, unplanned


class WorkOrderResponse(BaseModel):
    """Work order response"""
    id: UUID
    yacht_id: UUID
    equipment_id: UUID
    title: str
    description: Optional[str]
    type: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    request: CreateWorkOrderRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Create new work order

    Can be triggered from:
    - Search result actions
    - Equipment view
    - Fault log
    - Predictive maintenance alerts
    """
    # Insert work order
    response = supabase_client.admin.table('work_orders').insert({
        'yacht_id': context.yacht_id,
        'equipment_id': str(request.equipment_id),
        'title': request.title,
        'description': request.description,
        'type': request.type,
        'status': 'planned',
        'priority': request.priority,
        'created_by': context.user_id
    }).execute()

    work_order = response.data[0]

    return WorkOrderResponse(**work_order)


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order(
    work_order_id: UUID,
    context: YachtContext = Depends(get_current_user)
):
    """Get work order by ID"""
    response = supabase_client.admin.table('work_orders') \
        .select('*') \
        .eq('id', str(work_order_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("WorkOrder", str(work_order_id))

    return WorkOrderResponse(**response.data)


@router.get("", response_model=List[WorkOrderResponse])
async def list_work_orders(
    status: Optional[str] = None,
    equipment_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    context: YachtContext = Depends(get_current_user)
):
    """
    List work orders with filters

    Filters:
    - status: planned, in_progress, completed, deferred, cancelled
    - equipment_id: Filter by equipment
    """
    query = supabase_client.admin.table('work_orders') \
        .select('*') \
        .eq('yacht_id', context.yacht_id) \
        .order('created_at', desc=True) \
        .range(offset, offset + limit - 1)

    if status:
        query = query.eq('status', status)

    if equipment_id:
        query = query.eq('equipment_id', str(equipment_id))

    response = query.execute()

    return [WorkOrderResponse(**wo) for wo in response.data]


@router.patch("/{work_order_id}/status")
async def update_work_order_status(
    work_order_id: UUID,
    status: str,
    context: YachtContext = Depends(get_current_user)
):
    """Update work order status"""
    # Update status
    response = supabase_client.admin.table('work_orders') \
        .update({'status': status, 'updated_at': datetime.utcnow().isoformat()}) \
        .eq('id', str(work_order_id)) \
        .eq('yacht_id', context.yacht_id) \
        .execute()

    if not response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("WorkOrder", str(work_order_id))

    # Log status change in work_order_history
    supabase_client.admin.table('work_order_history').insert({
        'work_order_id': str(work_order_id),
        'changed_by': context.user_id,
        'field_changed': 'status',
        'new_value': status
    }).execute()

    return {"status": "updated"}
