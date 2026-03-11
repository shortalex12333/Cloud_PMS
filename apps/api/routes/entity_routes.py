"""
Entity Lens Endpoints
=====================

GET /v1/entity/{type}/{id} — one endpoint per entity type.

Each returns the canonical shape consumed by RouteShell.tsx and the
LensContent components. These are READ-ONLY detail endpoints.

Missing endpoints added here: certificate, document, hours_of_rest,
shopping_list, warranty, handover_export, purchase_order.
"""

from fastapi import APIRouter, HTTPException, Depends
import logging
from typing import List, Dict

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client, get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Certificate ────────────────────────────────────────────────────────────────
# Two-table lookup: vessel certificates first, crew certificates as fallback.
# Returns domain="vessel" or domain="crew" so the frontend can adapt labels.

@router.get("/v1/entity/certificate/{certificate_id}")
async def get_certificate_entity(certificate_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        data, domain = None, "vessel"
        r = supabase.table("pms_vessel_certificates").select("*") \
            .eq("id", certificate_id).eq("yacht_id", yacht_id).maybe_single().execute()
        if r is not None and r.data:
            data = r.data
        else:
            r2 = supabase.table("pms_crew_certificates").select("*") \
                .eq("id", certificate_id).eq("yacht_id", yacht_id).maybe_single().execute()
            if r2.data:
                data, domain = r2.data, "crew"

        if not data:
            raise HTTPException(status_code=404, detail="Certificate not found")

        props = data.get("properties") or {}
        if isinstance(props, str):
            import json as _j
            props = _j.loads(props) if props else {}

        return {
            "id": data.get("id"),
            "name": data.get("certificate_name") if domain == "vessel" else data.get("certificate_type", "Certificate"),
            "certificate_type": data.get("certificate_type"),
            "issuing_authority": data.get("issuing_authority"),
            "issue_date": data.get("issue_date"),
            "expiry_date": data.get("expiry_date"),
            "status": data.get("status", "active"),
            "certificate_number": data.get("certificate_number"),
            "notes": props.get("notes") if isinstance(props, dict) else None,
            "crew_member_id": data.get("person_node_id") if domain == "crew" else None,
            "domain": domain,
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Document ───────────────────────────────────────────────────────────────────
# Filter: deleted_at IS NULL (soft-delete). url = storage_path for v1.

@router.get("/v1/entity/document/{document_id}")
async def get_document_entity(document_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("doc_metadata").select("*") \
            .eq("id", document_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Document not found")

        data = r.data
        return {
            "id": data.get("id"),
            "filename": data.get("filename"),
            "title": data.get("title") or data.get("filename"),
            "description": data.get("description"),
            "mime_type": data.get("content_type"),
            "url": data.get("storage_path"),
            "classification": data.get("classification"),
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "tags": data.get("tags") or [],
            "created_at": data.get("created_at"),
            "created_by": data.get("created_by"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Hours of Rest ──────────────────────────────────────────────────────────────
# rest_periods is jsonb — may arrive as string from older rows; parse defensively.
# status derived from is_daily_compliant.

@router.get("/v1/entity/hours_of_rest/{record_id}")
async def get_hours_of_rest_entity(record_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_hours_of_rest").select("*") \
            .eq("id", record_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Hours of rest record not found")

        data = r.data
        rest_periods = data.get("rest_periods") or []
        if isinstance(rest_periods, str):
            import json as _j
            rest_periods = _j.loads(rest_periods) if rest_periods else []

        is_daily = data.get("is_daily_compliant")
        if is_daily is True:
            status = "compliant"
        elif is_daily is False:
            status = "non_compliant"
        else:
            status = "unknown"

        return {
            "id": data.get("id"),
            "crew_member_id": data.get("user_id"),
            "crew_name": None,
            "date": data.get("record_date"),
            "total_rest_hours": data.get("total_rest_hours"),
            "total_work_hours": data.get("total_work_hours"),
            "is_compliant": data.get("is_daily_compliant"),
            "status": status,
            "weekly_rest_hours": data.get("weekly_rest_hours"),
            "daily_compliance_notes": data.get("daily_compliance_notes"),
            "weekly_compliance_notes": data.get("weekly_compliance_notes"),
            "rest_periods": [
                {
                    "id": p.get("id", f"period-{i}"),
                    "start_time": (
                        p.get("start_time") or
                        (f"{data.get('record_date')}T{p['start']}:00" if p.get("start") and data.get("record_date") else p.get("start"))
                    ),
                    "end_time": (
                        p.get("end_time") or
                        (f"{data.get('record_date')}T{p['end']}:00" if p.get("end") and data.get("record_date") else p.get("end"))
                    ),
                    "duration_hours": p.get("duration_hours") or p.get("hours"),
                }
                for i, p in enumerate(rest_periods)
                if isinstance(p, dict)
            ],
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hours_of_rest {record_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Shopping List Item ─────────────────────────────────────────────────────────
# The search result object_id IS a pms_shopping_list_items.id.
# Returns single item wrapped in items:[...] array for the LensContent component.

@router.get("/v1/entity/shopping_list/{item_id}")
async def get_shopping_list_entity(item_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_shopping_list_items").select("*") \
            .eq("id", item_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Shopping list item not found")

        data = r.data
        item = {
            "id": data.get("id"),
            "part_name": data.get("part_name"),
            "part_number": data.get("part_number"),
            "manufacturer": data.get("manufacturer"),
            "unit": data.get("unit"),
            "quantity_requested": data.get("quantity_requested"),
            "urgency": data.get("urgency"),
            "status": data.get("status"),
            "required_by_date": data.get("required_by_date"),
            "is_candidate_part": data.get("is_candidate_part", False),
        }
        return {
            "id": data.get("id"),
            "title": data.get("part_name"),
            "status": data.get("status"),
            "requester_id": data.get("created_by"),
            "requester_name": None,
            "created_at": data.get("created_at"),
            "items": [item],
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch shopping_list item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Warranty Claim ─────────────────────────────────────────────────────────────
# Table: pms_warranty_claims (NOT pms_warranties — that table doesn't exist)
# Schema confirmed from DB: claim_number, title, vendor_name, warranty_expiry,
# claimed_amount, status, equipment_id, fault_id, work_order_id, manufacturer

@router.get("/v1/entity/warranty/{warranty_id}")
async def get_warranty_entity(warranty_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_warranty_claims").select("*") \
            .eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Warranty not found")

        data = r.data
        title = data.get("title") or data.get("claim_number") or (data.get("id", "")[:8])

        return {
            "id": data.get("id"),
            "title": title,
            "claim_number": data.get("claim_number"),
            "equipment_id": data.get("equipment_id"),
            "fault_id": data.get("fault_id"),
            "work_order_id": data.get("work_order_id"),
            "vendor_name": data.get("vendor_name"),
            "manufacturer": data.get("manufacturer"),
            "part_number": data.get("part_number"),
            "serial_number": data.get("serial_number"),
            "purchase_date": data.get("purchase_date"),
            "expiry_date": data.get("warranty_expiry"),
            "status": data.get("status"),
            "claimed_amount": data.get("claimed_amount"),
            "approved_amount": data.get("approved_amount"),
            "currency": data.get("currency"),
            "description": data.get("description"),
            "claim_type": data.get("claim_type"),
            "created_at": data.get("created_at"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch warranty {warranty_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Handover Export ────────────────────────────────────────────────────────────
# edited_content is JSON — parse to extract sections array.
# Frontend expects both user_signature (snake) and userSignature (camel).

@router.get("/v1/entity/handover_export/{export_id}")
async def get_handover_export_entity(export_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("handover_exports").select("*") \
            .eq("id", export_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Handover export not found")

        data = r.data

        edited_content = data.get("edited_content") or {}
        if isinstance(edited_content, str):
            import json as _j
            edited_content = _j.loads(edited_content) if edited_content else {}
        if isinstance(edited_content, list):
            sections = edited_content
        elif isinstance(edited_content, dict):
            sections = edited_content.get("sections", [])
        else:
            sections = []

        user_sig = data.get("user_signature")
        return {
            "id": data.get("id"),
            "yacht_id": data.get("yacht_id"),
            "review_status": data.get("review_status"),
            "export_type": data.get("export_type"),
            "export_status": data.get("export_status"),
            "file_name": data.get("file_name"),
            "sections": sections,
            "user_signature": user_sig,
            "userSignature": user_sig,
            "hod_signature": data.get("hod_signature"),
            "submitted_at": data.get("exported_at"),
            "created_at": data.get("created_at"),
            "draft_id": data.get("draft_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch handover_export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Purchase Order ─────────────────────────────────────────────────────────────
# Joins pms_purchase_order_items by purchase_order_id.
# Column name variants handled with fallbacks.

@router.get("/v1/entity/purchase_order/{po_id}")
async def get_purchase_order_entity(po_id: str, auth: dict = Depends(get_authenticated_user)):
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_purchase_orders").select("*") \
            .eq("id", po_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        data = r.data

        items_r = supabase.table("pms_purchase_order_items").select("*") \
            .eq("purchase_order_id", po_id).execute()
        raw_items = items_r.data or []

        items = [
            {
                "id": item.get("id"),
                "part_id": item.get("part_id"),
                "name": item.get("name") or item.get("part_name") or item.get("description"),
                "quantity_ordered": item.get("quantity_ordered"),
                "quantity": item.get("quantity_ordered"),
                "quantity_received": item.get("quantity_received", 0),
                "unit_price": item.get("unit_price"),
                "currency": item.get("currency"),
            }
            for item in raw_items
        ]

        return {
            "id": data.get("id"),
            "po_number": data.get("po_number"),
            "status": data.get("status"),
            "supplier_name": data.get("supplier_name") or data.get("vendor_name"),
            "order_date": data.get("order_date") or data.get("created_at"),
            "expected_delivery": data.get("expected_delivery") or data.get("expected_delivery_date"),
            "total_amount": data.get("total_amount") or data.get("total"),
            "currency": data.get("currency", "USD"),
            "notes": data.get("notes"),
            "items": items,
            "created_at": data.get("created_at"),
            "yacht_id": data.get("yacht_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch purchase_order {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Fault ──────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/fault/{fault_id}")
async def get_fault_entity(fault_id: str, auth: dict = Depends(get_authenticated_user)):
    """Fetch fault by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_faults').select('*').eq('id', fault_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Fault not found")

        data = response.data
        return {
            "id": data.get('id'),
            "title": data.get('title') or data.get('fault_code', 'Unknown Fault'),
            "description": data.get('description', ''),
            "severity": data.get('severity', 'medium'),
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),
            "reported_at": data.get('reported_at') or data.get('detected_at'),
            "reporter": data.get('reporter') or data.get('reported_by', 'System'),
            "status": data.get('status'),
            "has_work_order": data.get('has_work_order', False),
            "ai_diagnosis": data.get('ai_diagnosis'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch fault {fault_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Work Order helpers ─────────────────────────────────────────────────────────

async def _is_user_hod(user_id: str, yacht_id: str, supabase) -> bool:
    """Check if user has Head of Department (HOD) role."""
    try:
        result = supabase.table('auth_users_roles').select('role').eq(
            'user_id', user_id
        ).eq(
            'yacht_id', yacht_id
        ).eq(
            'is_active', True
        ).in_(
            'role', ['chief_engineer', 'chief_officer', 'captain', 'purser']
        ).maybe_single().execute()
        return bool(result.data)
    except Exception as e:
        logger.warning(f"Failed to check HOD status for user {user_id}: {e}")
        return False


def _determine_available_actions(work_order: Dict, user_role: str, is_hod: bool) -> List[Dict]:
    """Determine which actions are available based on work order state."""
    actions = []
    status = work_order.get('status', '').lower()

    if status == 'planned':
        actions.append({"name": "Start Work Order", "endpoint": "/v1/actions/work_order/start", "requires_signature": False, "method": "POST"})
        actions.append({"name": "Cancel", "endpoint": "/v1/actions/work_order/cancel", "requires_signature": False, "method": "POST"})
    elif status == 'in_progress':
        actions.append({"name": "Add Part", "endpoint": "/v1/actions/work_order/add_part", "requires_signature": False, "method": "POST"})
        actions.append({"name": "Add Note", "endpoint": "/v1/actions/work_order/add_note", "requires_signature": False, "method": "POST"})
        if is_hod:
            actions.append({"name": "Complete", "endpoint": "/v1/actions/work_order/complete", "requires_signature": True, "method": "POST"})
    elif status == 'completed':
        actions.append({"name": "Reopen", "endpoint": "/v1/actions/work_order/reopen", "requires_signature": False, "method": "POST"})

    return actions[:6]


# ── Work Order ─────────────────────────────────────────────────────────────────

@router.get("/v1/entity/work_order/{work_order_id}")
async def get_work_order_entity(work_order_id: str, auth: dict = Depends(get_authenticated_user)):
    """Fetch work order by ID with all related data for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        user_id = auth['user_id']
        user_role = auth.get('role', 'crew')

        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection unavailable")

        response = supabase.table('pms_work_orders').select('*').eq('id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()
        if not response.data:
            response = supabase.table('pms_work_orders').select('*').eq('work_order_id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Work order not found")

        data = response.data
        wo_id = data.get('id') or data.get('work_order_id')

        notes_response = supabase.table('pms_work_order_notes').select(
            'id, note_text, note_type, created_by, created_at'
        ).eq('work_order_id', wo_id).order('created_at', desc=True).execute()
        notes = notes_response.data if notes_response.data else []

        parts_response = supabase.table('pms_work_order_parts').select(
            'id, part_id, quantity, notes, created_at, pms_parts(id, name, part_number, location)'
        ).eq('work_order_id', wo_id).execute()
        parts = parts_response.data if parts_response.data else []

        try:
            checklist_response = supabase.table('pms_work_order_checklist').select(
                'id, title, description, is_completed, completed_by, completed_at, sequence'
            ).eq('work_order_id', wo_id).order('sequence').execute()
            checklist = checklist_response.data if checklist_response.data else []
        except Exception:
            checklist = []

        audit_response = supabase.table('pms_audit_log').select(
            'id, action, old_values, new_values, user_id, created_at'
        ).eq('entity_type', 'work_order').eq('entity_id', wo_id).eq('yacht_id', yacht_id).order('created_at', desc=True).limit(50).execute()
        audit_history = audit_response.data if audit_response.data else []

        is_hod = await _is_user_hod(user_id, yacht_id, supabase)
        available_actions = _determine_available_actions(work_order=data, user_role=user_role, is_hod=is_hod)

        return {
            "id": wo_id,
            "wo_number": data.get('wo_number'),
            "title": data.get('title', 'Untitled Work Order'),
            "description": data.get('description', ''),
            "status": data.get('status', 'pending'),
            "priority": data.get('priority', 'medium'),
            "type": data.get('type') or data.get('work_order_type'),
            "equipment_id": data.get('equipment_id'),
            "equipment_name": data.get('equipment_name'),
            "assigned_to": data.get('assigned_to'),
            "assigned_to_name": data.get('assigned_to_name'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "due_date": data.get('due_date'),
            "completed_at": data.get('completed_at'),
            "completed_by": data.get('completed_by'),
            "fault_id": data.get('fault_id'),
            "notes": notes,
            "parts": parts,
            "checklist": checklist,
            "audit_history": audit_history,
            "notes_count": len(notes),
            "parts_count": len(parts),
            "checklist_count": len(checklist),
            "checklist_completed": len([c for c in checklist if c.get('is_completed')]),
            "available_actions": available_actions,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch work order {work_order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Equipment ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/equipment/{equipment_id}")
async def get_equipment_entity(equipment_id: str, auth: dict = Depends(get_authenticated_user)):
    """Fetch equipment by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_equipment').select('*').eq('id', equipment_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Equipment not found")

        data = response.data
        metadata = data.get('metadata') or {}
        return {
            "id": data.get('id'),
            "name": data.get('name', 'Unknown Equipment'),
            "equipment_type": data.get('system_type') or metadata.get('category', 'General'),
            "manufacturer": data.get('manufacturer'),
            "model": data.get('model'),
            "serial_number": data.get('serial_number'),
            "location": data.get('location', 'Unknown'),
            "status": metadata.get('status', 'operational'),
            "criticality": data.get('criticality'),
            "installation_date": data.get('installed_date'),
            "last_maintenance": metadata.get('last_maintenance'),
            "next_maintenance": metadata.get('next_maintenance'),
            "description": data.get('description'),
            "attention_flag": data.get('attention_flag'),
            "attention_reason": data.get('attention_reason'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch equipment {equipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Part ───────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/part/{part_id}")
async def get_part_entity(part_id: str, auth: dict = Depends(get_authenticated_user)):
    """Fetch part by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_parts').select('*').eq('id', part_id).eq('yacht_id', yacht_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Part not found")

        data = response.data
        metadata = data.get('metadata') or {}
        return {
            "id": data.get('id'),
            "name": data.get('name', 'Unknown Part'),
            "part_number": data.get('part_number', ''),
            "stock_quantity": data.get('quantity_on_hand', 0),
            "min_stock_level": data.get('minimum_quantity') or data.get('min_level', 0),
            "location": data.get('location', 'Unknown'),
            "unit_cost": metadata.get('unit_cost'),
            "supplier": metadata.get('supplier'),
            "category": data.get('category'),
            "unit": data.get('unit'),
            "manufacturer": data.get('manufacturer'),
            "description": data.get('description'),
            "last_counted_at": data.get('last_counted_at'),
            "last_counted_by": data.get('last_counted_by'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch part {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Receiving ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/receiving/{receiving_id}")
async def get_receiving_entity(receiving_id: str, auth: dict = Depends(get_authenticated_user)):
    """Fetch receiving by ID for entity viewer (DeepLinkHandler)."""
    try:
        yacht_id = auth['yacht_id']
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_receiving') \
            .select('*') \
            .eq('id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receiving not found")

        data = response.data
        return {
            "id": data.get('id'),
            "vendor_name": data.get('vendor_name'),
            "vendor_reference": data.get('vendor_reference'),
            "received_date": data.get('received_date'),
            "status": data.get('status', 'draft'),
            "total": data.get('total'),
            "currency": data.get('currency'),
            "notes": data.get('notes'),
            "received_by": data.get('received_by'),
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch receiving {receiving_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
