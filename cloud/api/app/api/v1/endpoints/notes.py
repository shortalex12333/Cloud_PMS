"""
Notes API endpoints
/v1/notes routes
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.auth import get_current_user, YachtContext
from app.core.supabase import supabase_client

router = APIRouter(prefix="/notes", tags=["Notes"])


class CreateNoteRequest(BaseModel):
    """Create note request"""
    text: str
    equipment_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    category: Optional[str] = None  # observation, maintenance, fault, general


class NoteResponse(BaseModel):
    """Note response"""
    id: UUID
    yacht_id: UUID
    text: str
    equipment_id: Optional[UUID]
    work_order_id: Optional[UUID]
    category: Optional[str]
    created_by: UUID
    created_at: datetime


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: CreateNoteRequest,
    context: YachtContext = Depends(get_current_user)
):
    """
    Create new note

    Notes can be attached to:
    - Equipment (observations, oil levels, temps, etc.)
    - Work orders (progress updates, findings)
    - General yacht log
    """
    # Note: Actual table for notes might be named differently (e.g., observations, comments)
    # Using generic 'notes' table for now
    response = supabase_client.admin.table('notes').insert({
        'yacht_id': context.yacht_id,
        'text': request.text,
        'equipment_id': str(request.equipment_id) if request.equipment_id else None,
        'work_order_id': str(request.work_order_id) if request.work_order_id else None,
        'category': request.category,
        'created_by': context.user_id
    }).execute()

    note = response.data[0]

    return NoteResponse(**note)


@router.get("", response_model=List[NoteResponse])
async def list_notes(
    equipment_id: Optional[UUID] = None,
    work_order_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    context: YachtContext = Depends(get_current_user)
):
    """
    List notes with filters

    Filters:
    - equipment_id: Notes for specific equipment
    - work_order_id: Notes for specific work order
    """
    query = supabase_client.admin.table('notes') \
        .select('*') \
        .eq('yacht_id', context.yacht_id) \
        .order('created_at', desc=True) \
        .range(offset, offset + limit - 1)

    if equipment_id:
        query = query.eq('equipment_id', str(equipment_id))

    if work_order_id:
        query = query.eq('work_order_id', str(work_order_id))

    response = query.execute()

    return [NoteResponse(**note) for note in response.data]
