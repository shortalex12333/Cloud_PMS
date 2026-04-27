"""
Entity Lens Endpoints — HTTP delegation layer.

GET /v1/entity/{type}/{id} — one endpoint per entity type.
All DB queries and business logic live in handlers/entity_lens_handlers.py
(12 non-handover routes) and handlers/handover_handlers.HandoverWorkflowHandlers
(handover_export route). Phase C thinning complete.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from typing import Optional

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id
from integrations.supabase import get_tenant_client
from handlers.entity_lens_handlers import EntityLensHandlers
from handlers.handover_handlers import HandoverWorkflowHandlers

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Certificate ────────────────────────────────────────────────────────────────

@router.get("/v1/entity/certificate/{certificate_id}")
async def get_certificate_entity(certificate_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_certificate_entity(certificate_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch certificate {certificate_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Document ───────────────────────────────────────────────────────────────────

@router.get("/v1/entity/document/{document_id}")
async def get_document_entity(document_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_document_entity(document_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Hours of Rest ──────────────────────────────────────────────────────────────

@router.get("/v1/entity/hours_of_rest/{record_id}")
async def get_hours_of_rest_entity(record_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_hours_of_rest_entity(record_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hours_of_rest {record_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Hours of Rest Monthly Sign-Off ────────────────────────────────────────────

@router.get("/v1/entity/hours_of_rest_signoff/{signoff_id}")
async def get_hor_signoff_entity(signoff_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_hor_signoff_entity(signoff_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hor_signoff {signoff_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Shopping List Item ─────────────────────────────────────────────────────────

@router.get("/v1/entity/shopping_list/{item_id}")
async def get_shopping_list_entity(item_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_shopping_list_entity(item_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch shopping_list item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Warranty Claim ─────────────────────────────────────────────────────────────

@router.get("/v1/entity/warranty/{warranty_id}")
async def get_warranty_entity(warranty_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_warranty_entity(warranty_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch warranty {warranty_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Handover Export ────────────────────────────────────────────────────────────

@router.get("/v1/entity/handover_export/{export_id}")
async def get_handover_export_entity(export_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        h = HandoverWorkflowHandlers(supabase)
        return await h.get_export_entity(export_id, yacht_id, auth.get('role', 'crew'))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch handover_export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Purchase Order ─────────────────────────────────────────────────────────────

@router.get("/v1/entity/purchase_order/{po_id}")
async def get_purchase_order_entity(po_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_purchase_order_entity(po_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch purchase_order {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Fault ──────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/fault/{fault_id}")
async def get_fault_entity(fault_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_fault_entity(fault_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch fault {fault_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Work Order ─────────────────────────────────────────────────────────────────

@router.get("/v1/entity/work_order/{work_order_id}")
async def get_work_order_entity(work_order_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_work_order_entity(work_order_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch work order {work_order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Equipment ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/equipment/{equipment_id}")
async def get_equipment_entity(equipment_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_equipment_entity(equipment_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch equipment {equipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Part ───────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/part/{part_id}")
async def get_part_entity(part_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_part_entity(part_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch part {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Receiving ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/receiving/{receiving_id}")
async def get_receiving_entity(receiving_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        supabase = get_tenant_client(auth['tenant_key_alias'])
        return await EntityLensHandlers(supabase).get_receiving_entity(receiving_id, yacht_id, auth)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch receiving {receiving_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
