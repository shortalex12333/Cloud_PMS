"""
Handover API endpoints
/v1/handovers routes
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

from app.core.auth import get_current_user, YachtContext
from app.core.supabase import supabase_client

router = APIRouter(prefix="/handovers", tags=["Handovers"])


class CreateHandoverRequest(BaseModel):
    """Create handover draft"""
    title: str
    period_start: date
    period_end: date
    department: Optional[str] = "engineering"


class AddHandoverItemRequest(BaseModel):
    """Add item to handover"""
    source_type: str  # fault, work_order, note, document
    source_id: UUID
    summary: str
    priority: Optional[str] = "normal"


class HandoverItemResponse(BaseModel):
    """Handover item response"""
    id: UUID
    handover_id: UUID
    source_type: str
    source_id: UUID
    summary: str
    priority: str
    created_at: datetime


class HandoverResponse(BaseModel):
    """Handover response"""
    id: UUID
    yacht_id: UUID
    title: str
    period_start: date
    period_end: date
    department: str
    status: str
    created_by: UUID
    created_at: datetime


class ExportHandoverRequest(BaseModel):
    """Export handover request"""
    format: str = "pdf"  # pdf, html, docx


class ExportHandoverResponse(BaseModel):
    """Export handover response"""
    url: str
    format: str
    expires_at: datetime


@router.post("", response_model=HandoverResponse, status_code=status.HTTP_201_CREATED)
async def create_handover(
    request: CreateHandoverRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Create new handover draft

    Handovers compile:
    - Critical faults and resolutions
    - Work orders completed
    - Notes and observations
    - Equipment status changes
    """
    response = supabase_client.admin.table('handover_drafts').insert({
        'yacht_id': context.yacht_id,
        'title': request.title,
        'period_start': request.period_start.isoformat(),
        'period_end': request.period_end.isoformat(),
        'department': request.department,
        'status': 'draft',
        'created_by': context.user_id
    }).execute()

    handover = response.data[0]

    return HandoverResponse(**handover)


@router.post("/{handover_id}/items", response_model=HandoverItemResponse)
async def add_handover_item(
    handover_id: UUID,
    request: AddHandoverItemRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Add item to handover

    Items can be added from:
    - Search results ("Add to Handover" action)
    - Work order view
    - Equipment view
    - Notes view
    """
    # Verify handover exists and belongs to yacht
    handover_response = supabase_client.admin.table('handover_drafts') \
        .select('id') \
        .eq('id', str(handover_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not handover_response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Handover", str(handover_id))

    # Insert handover item
    response = supabase_client.admin.table('handover_items').insert({
        'handover_id': str(handover_id),
        'source_type': request.source_type,
        'source_id': str(request.source_id),
        'summary': request.summary,
        'priority': request.priority or 'normal'
    }).execute()

    item = response.data[0]

    return HandoverItemResponse(**item)


@router.get("/{handover_id}", response_model=HandoverResponse)
async def get_handover(
    handover_id: UUID,
    context: YachtContext = Depends(get_current_user)
):
    """Get handover by ID"""
    response = supabase_client.admin.table('handover_drafts') \
        .select('*') \
        .eq('id', str(handover_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Handover", str(handover_id))

    return HandoverResponse(**response.data)


@router.get("/{handover_id}/items", response_model=List[HandoverItemResponse])
async def list_handover_items(
    handover_id: UUID,
    context: YachtContext = Depends(get_current_user)
):
    """List all items in a handover"""
    # Verify handover exists
    handover_response = supabase_client.admin.table('handover_drafts') \
        .select('id') \
        .eq('id', str(handover_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not handover_response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Handover", str(handover_id))

    # Get items
    response = supabase_client.admin.table('handover_items') \
        .select('*') \
        .eq('handover_id', str(handover_id)) \
        .order('created_at', desc=True) \
        .execute()

    return [HandoverItemResponse(**item) for item in response.data]


@router.post("/{handover_id}/export", response_model=ExportHandoverResponse)
async def export_handover(
    handover_id: UUID,
    request: ExportHandoverRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Export handover to PDF/HTML/DOCX

    Generates formatted document with:
    - Cover page with yacht info, period
    - Sections by priority/category
    - Embedded images and diagrams
    - Sign-off section

    NOTE: Export logic delegated to document generation service
    """
    # TODO: Integrate with document generation service

    # For now, return stub
    return ExportHandoverResponse(
        url=f"https://celesteos.com/handovers/{handover_id}.pdf",
        format=request.format,
        expires_at=datetime.utcnow()
    )
