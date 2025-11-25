"""
Documents and Equipment API endpoints
/v1/documents and /v1/equipment routes
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.auth import get_current_user, YachtContext
from app.core.supabase import supabase_client

router = APIRouter(tags=["Documents & Equipment"])


# ============================================================================
# DOCUMENTS
# ============================================================================

class DocumentResponse(BaseModel):
    """Document response"""
    id: UUID
    yacht_id: UUID
    sha256: str
    original_filename: str
    file_size: int
    mime_type: Optional[str]
    source_type: str
    document_type: Optional[str]
    processing_status: str
    indexed_at: Optional[datetime]
    created_at: datetime


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    document_type: Optional[str] = None,
    processing_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    context: YachtContext = Depends(get_current_user)
):
    """
    List documents with filters

    Filters:
    - document_type: manual, technical_drawing, sop, invoice, email, photo, report
    - processing_status: pending, processing, completed, failed
    """
    query = supabase_client.admin.table('documents') \
        .select('*') \
        .eq('yacht_id', context.yacht_id) \
        .order('created_at', desc=True) \
        .range(offset, offset + limit - 1)

    if document_type:
        query = query.eq('document_type', document_type)

    if processing_status:
        query = query.eq('processing_status', processing_status)

    response = query.execute()

    return [DocumentResponse(**doc) for doc in response.data]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    context: YachtContext = Depends(get_current_user)
):
    """Get document by ID"""
    response = supabase_client.admin.table('documents') \
        .select('*') \
        .eq('id', str(document_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Document", str(document_id))

    return DocumentResponse(**response.data)


# ============================================================================
# EQUIPMENT
# ============================================================================

class EquipmentResponse(BaseModel):
    """Equipment response"""
    id: UUID
    yacht_id: UUID
    parent_id: Optional[UUID]
    name: str
    system_type: Optional[str]
    criticality: str
    status: str
    location: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    created_at: datetime
    updated_at: datetime


@router.get("/equipment", response_model=List[EquipmentResponse])
async def list_equipment(
    system_type: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    criticality: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    context: YachtContext = Depends(get_current_user)
):
    """
    List equipment with filters

    Filters:
    - system_type: propulsion, electrical, hvac, hydraulics, etc.
    - parent_id: Get sub-equipment
    - criticality: low, medium, high
    """
    query = supabase_client.admin.table('equipment') \
        .select('*') \
        .eq('yacht_id', context.yacht_id) \
        .order('name') \
        .range(offset, offset + limit - 1)

    if system_type:
        query = query.eq('system_type', system_type)

    if parent_id:
        query = query.eq('parent_id', str(parent_id))

    if criticality:
        query = query.eq('criticality', criticality)

    response = query.execute()

    return [EquipmentResponse(**eq) for eq in response.data]


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: UUID,
    context: YachtContext = Depends(get_current_user)
):
    """Get equipment by ID"""
    response = supabase_client.admin.table('equipment') \
        .select('*') \
        .eq('id', str(equipment_id)) \
        .eq('yacht_id', context.yacht_id) \
        .single() \
        .execute()

    if not response.data:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Equipment", str(equipment_id))

    return EquipmentResponse(**response.data)
