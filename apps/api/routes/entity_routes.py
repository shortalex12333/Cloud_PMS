"""
Entity Lens Endpoints
=====================

GET /v1/entity/{type}/{id} — one endpoint per entity type.

Each returns the canonical shape consumed by RouteShell.tsx and the
LensContent components. These are READ-ONLY detail endpoints.

Missing endpoints added here: certificate, document, hours_of_rest,
shopping_list, warranty, handover_export, purchase_order.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
import logging
from typing import List, Dict, Optional

from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id
from integrations.supabase import get_tenant_client, get_supabase_client
from action_router.entity_actions import get_available_actions

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Shared helpers (signed URLs + navigation links) ──────────────────────────

# Fallback bucket map for pre-migration rows without storage_bucket column.
# New rows store storage_bucket directly on pms_attachments.
ATTACHMENT_BUCKET = {
    "fault": "pms-discrepancy-photos",
    "work_order": "pms-work-order-photos",
    "checklist_item": "pms-work-order-photos",
    "equipment": "pms-work-order-photos",
    "purchase_order": "pms-finance-documents",
    "warranty": "pms-finance-documents",
    "receiving": "pms-receiving-images",
}


def _sign_url(supabase, bucket: str, path: str, expires_in: int = 3600):
    """Sign a storage path. Returns URL string or None. Never raises."""
    if not path:
        return None
    try:
        result = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
        return result.get("signedURL") or result.get("signed_url")
    except Exception as e:
        logger.warning(f"Failed to sign {bucket}/{path}: {e}")
        return None


def _get_attachments(supabase, entity_type: str, entity_id: str, yacht_id: str) -> list:
    """Query pms_attachments, sign each, return list matching frontend Attachment shape."""
    try:
        result = supabase.table("pms_attachments").select(
            "id, filename, mime_type, storage_path, file_size, category, storage_bucket"
        ).eq("entity_type", entity_type).eq("entity_id", entity_id).eq(
            "yacht_id", yacht_id
        ).is_("deleted_at", "null").execute()

        attachments = []
        fallback_bucket = ATTACHMENT_BUCKET.get(entity_type, "attachments")
        for att in (result.data or []):
            path = att.get("storage_path")
            if not path:
                continue
            bucket = att.get("storage_bucket") or fallback_bucket
            url = _sign_url(supabase, bucket, path)
            if not url:
                continue
            attachments.append({
                "id": att["id"],
                "filename": att.get("filename", "file"),
                "url": url,
                "mime_type": att.get("mime_type", "application/octet-stream"),
                "size_bytes": att.get("file_size") or 0,
            })
        return attachments
    except Exception as e:
        logger.warning(f"Failed to get attachments for {entity_type}/{entity_id}: {e}")
        return []


def _nav(entity_type: str, entity_id, label: str):
    """Return {entity_type, entity_id, label} or None if entity_id is falsy."""
    if not entity_id:
        return None
    return {"entity_type": entity_type, "entity_id": str(entity_id), "label": label}


# ── Certificate ────────────────────────────────────────────────────────────────
# Two-table lookup: vessel certificates first, crew certificates as fallback.
# Returns domain="vessel" or domain="crew" so the frontend can adapt labels.

@router.get("/v1/entity/certificate/{certificate_id}")
async def get_certificate_entity(certificate_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_vessel_certificates").select("*") \
            .eq("id", certificate_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if not r or not r.data:
            raise HTTPException(status_code=404, detail="Certificate not found")

        data = r.data
        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            import json as _j
            metadata = _j.loads(metadata) if metadata else {}

        # Sign document URL if linked
        document_url = None
        doc_id = data.get("document_id")
        if doc_id:
            try:
                doc_r = supabase.table("doc_metadata").select(
                    "storage_path, storage_bucket"
                ).eq("id", doc_id).maybe_single().execute()
                if doc_r and doc_r.data:
                    bucket = doc_r.data.get("storage_bucket") or "documents"
                    document_url = _sign_url(supabase, bucket, doc_r.data.get("storage_path"))
            except Exception:
                pass

        attachments = _get_attachments(supabase, "certificate", certificate_id, yacht_id)

        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
            _nav("document", doc_id, "Document"),
        ] if n]

        _entity_response = {
            "id": data.get("id"),
            "name": data.get("certificate_name"),
            "certificate_type": data.get("certificate_type"),
            "certificate_number": data.get("certificate_number"),
            "issuing_authority": data.get("issuing_authority"),
            "issue_date": data.get("issue_date"),
            "expiry_date": data.get("expiry_date"),
            "status": data.get("status", "valid"),
            "equipment_id": data.get("equipment_id"),
            "document_id": data.get("document_id"),
            "document_url": document_url,
            "notes": data.get("notes"),
            "domain": "vessel",
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "certificate", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch certificate {certificate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Document ───────────────────────────────────────────────────────────────────
# Filter: deleted_at IS NULL (soft-delete). url = storage_path for v1.

@router.get("/v1/entity/document/{document_id}")
async def get_document_entity(document_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
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

        # Sign the document URL (fixes raw-path bug for private buckets)
        bucket = data.get("storage_bucket") or "documents"
        signed_url = _sign_url(supabase, bucket, data.get("storage_path"))

        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
        ] if n]

        _entity_response = {
            "id": data.get("id"),
            "filename": data.get("filename"),
            "title": data.get("title") or data.get("filename"),
            "description": data.get("description"),
            "mime_type": data.get("content_type"),
            "url": signed_url,
            "classification": data.get("classification"),
            "equipment_id": data.get("equipment_id"),
            "equipment_name": data.get("equipment_name"),
            "tags": data.get("tags") or [],
            "created_at": data.get("created_at"),
            "created_by": data.get("created_by"),
            "yacht_id": data.get("yacht_id"),
            "attachments": [],
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "document", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Hours of Rest ──────────────────────────────────────────────────────────────
# rest_periods is jsonb — may arrive as string from older rows; parse defensively.
# status derived from is_daily_compliant.

@router.get("/v1/entity/hours_of_rest/{record_id}")
async def get_hours_of_rest_entity(record_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
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

        _entity_response = {
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
            "attachments": [],
            "related_entities": [n for n in [
                _nav("crew", data.get("user_id"), "Crew Member"),
            ] if n],
        }
        _entity_response["available_actions"] = get_available_actions(
            "hours_of_rest", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hours_of_rest {record_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Hours of Rest Monthly Sign-Off ────────────────────────────────────────────
# Table: pms_hor_monthly_signoffs
# MLC 2006 Standard A2.3 requires crew → HOD → Captain signing chain.
# Lens: HoRSignoffContent.tsx

@router.get("/v1/entity/hours_of_rest_signoff/{signoff_id}")
async def get_hor_signoff_entity(signoff_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_hor_monthly_signoffs").select("*") \
            .eq("id", signoff_id).eq("yacht_id", yacht_id).limit(1).execute()

        if not r.data or len(r.data) == 0:
            raise HTTPException(status_code=404, detail="Sign-off record not found")

        data = r.data[0]

        # Look up user name from auth_users_profiles (no FK on signoffs table)
        user_name = None
        user_id_val = data.get("user_id")
        if user_id_val:
            try:
                user_result = supabase.table("auth_users_profiles").select(
                    "name, email"
                ).eq("id", user_id_val).eq("yacht_id", yacht_id).limit(1).execute()
                if user_result.data and len(user_result.data) > 0:
                    u = user_result.data[0]
                    user_name = u.get("name") or u.get("email")
            except Exception:
                pass  # Non-critical — fallback to user_id display

        status = data.get("status", "draft")
        title = f"HoR Sign-Off — {data.get('month', '')}"
        if user_name:
            title = f"{user_name} — {data.get('month', '')}"

        _entity_response = {
            "id": data.get("id"),
            "title": title,
            "crew_name": user_name,
            "user_id": data.get("user_id"),
            "department": data.get("department"),
            "month": data.get("month"),
            "status": status,
            "total_rest_hours": data.get("total_rest_hours"),
            "total_work_hours": data.get("total_work_hours"),
            "violation_count": data.get("violation_count"),
            "compliance_percentage": data.get("compliance_percentage"),
            # Signatures
            "crew_signature": data.get("crew_signature"),
            "crew_signed_at": data.get("crew_signed_at"),
            "crew_signed_by": data.get("crew_signed_by"),
            "hod_signature": data.get("hod_signature"),
            "hod_signed_at": data.get("hod_signed_at"),
            "hod_signed_by": data.get("hod_signed_by"),
            "master_signature": data.get("master_signature"),
            "master_signed_at": data.get("master_signed_at"),
            "master_signed_by": data.get("master_signed_by"),
            # Metadata
            "notes": data.get("notes"),
            "yacht_id": data.get("yacht_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "attachments": [],
            "related_entities": [n for n in [
                _nav("crew", data.get("user_id"), "Crew Member"),
            ] if n],
        }
        _entity_response["available_actions"] = get_available_actions(
            "hours_of_rest_signoff", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch hor_signoff {signoff_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Shopping List Item ─────────────────────────────────────────────────────────
# The search result object_id IS a pms_shopping_list_items.id.
# Returns single item wrapped in items:[...] array for the LensContent component.

@router.get("/v1/entity/shopping_list/{item_id}")
async def get_shopping_list_entity(item_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
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
        nav = [n for n in [
            _nav("part", data.get("part_id"), "Part"),
        ] if n]

        _entity_response = {
            "id": data.get("id"),
            "title": data.get("part_name"),
            "status": data.get("status"),
            "requester_id": data.get("created_by"),
            "requester_name": None,
            "created_at": data.get("created_at"),
            "items": [item],
            "yacht_id": data.get("yacht_id"),
            "attachments": [],
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "shopping_list", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
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
async def get_warranty_entity(warranty_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        r = supabase.table("pms_warranty_claims").select("*") \
            .eq("id", warranty_id).eq("yacht_id", yacht_id).maybe_single().execute()

        if r is None or not r.data:
            raise HTTPException(status_code=404, detail="Warranty not found")

        data = r.data
        title = data.get("title") or data.get("claim_number") or (data.get("id", "")[:8])

        attachments = _get_attachments(supabase, "warranty", warranty_id, yacht_id)
        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
            _nav("fault", data.get("fault_id"), "Fault"),
            _nav("work_order", data.get("work_order_id"), "Work Order"),
        ] if n]

        _entity_response = {
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
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "warranty", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch warranty {warranty_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Handover Export ────────────────────────────────────────────────────────────
# edited_content is JSON — parse to extract sections array.
# Frontend expects both user_signature (snake) and userSignature (camel).

@router.get("/v1/entity/handover_export/{export_id}")
async def get_handover_export_entity(export_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
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

        # Sign the export file URL — use original_storage_url path
        raw_storage_url = data.get("original_storage_url") or data.get("file_name") or ""
        # Strip bucket prefix if present (e.g., "handover-exports/85fe1119-.../original/abc.html" → "85fe1119-.../original/abc.html")
        export_path = raw_storage_url.replace("handover-exports/", "", 1) if raw_storage_url.startswith("handover-exports/") else raw_storage_url
        export_url = _sign_url(supabase, "handover-exports", export_path) if export_path else None

        nav = [n for n in [
            _nav("handover_export", data.get("draft_id"), "Source Draft"),
        ] if n]

        user_sig = data.get("user_signature")
        dept = data.get("department") or ""
        _entity_response = {
            "id": data.get("id"),
            "yacht_id": data.get("yacht_id"),
            "title": f"{dept} Handover Report".strip() if dept else "Handover Report",
            "status": data.get("review_status", "pending_review"),
            "review_status": data.get("review_status"),
            "export_type": data.get("export_type"),
            "export_status": data.get("export_status"),
            "department": dept or None,
            "original_storage_url": data.get("original_storage_url"),
            "document_hash": data.get("document_hash"),
            "file_name": data.get("file_name"),
            "export_url": export_url,
            "sections": sections,
            "user_signature": user_sig,
            "userSignature": user_sig,
            "hod_signature": data.get("hod_signature"),
            "submitted_at": data.get("exported_at"),
            "created_at": data.get("created_at"),
            "draft_id": data.get("draft_id"),
            "attachments": [],
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "handover_export", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch handover_export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Purchase Order ─────────────────────────────────────────────────────────────
# Joins pms_purchase_order_items by purchase_order_id.
# Column name variants handled with fallbacks.

@router.get("/v1/entity/purchase_order/{po_id}")
async def get_purchase_order_entity(po_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
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

        attachments = _get_attachments(supabase, "purchase_order", po_id, yacht_id)

        # Nav to parts from line items (limit 5)
        nav = []
        for it in raw_items[:5]:
            n = _nav("part", it.get("part_id"), it.get("name") or "Part")
            if n:
                nav.append(n)

        _entity_response = {
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
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "purchase_order", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch purchase_order {po_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Fault ──────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/fault/{fault_id}")
async def get_fault_entity(fault_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    """Fetch fault by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_faults').select('*').eq('id', fault_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Fault not found")

        data = response.data

        attachments = _get_attachments(supabase, "fault", fault_id, yacht_id)

        # Find linked work orders
        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
        ] if n]
        try:
            wo_r = supabase.table("pms_work_orders").select("id, title").eq(
                "fault_id", fault_id
            ).eq("yacht_id", yacht_id).limit(5).execute()
            for wo in (wo_r.data or []):
                n = _nav("work_order", wo.get("id"), wo.get("title") or "Work Order")
                if n:
                    nav.append(n)
        except Exception:
            pass

        fault_metadata = data.get('metadata', {}) or {}
        _entity_response = {
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
            "attachments": attachments,
            "related_entities": nav,
            "notes": fault_metadata.get("notes", []),
        }
        _entity_response["available_actions"] = get_available_actions(
            "fault", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
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


# ── Work Order ─────────────────────────────────────────────────────────────────

@router.get("/v1/entity/work_order/{work_order_id}")
async def get_work_order_entity(work_order_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    """Fetch work order by ID with all related data for entity viewer (ContextPanel)."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        user_id = auth['user_id']
        user_role = auth.get('role', 'crew')

        supabase = get_supabase_client()
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection unavailable")

        response = supabase.table('pms_work_orders').select('*').eq('id', work_order_id).eq('yacht_id', yacht_id).maybe_single().execute()
        if not response or not response.data:
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

        attachments = _get_attachments(supabase, "work_order", wo_id, yacht_id)
        nav = [n for n in [
            _nav("equipment", data.get("equipment_id"), "Equipment"),
            _nav("fault", data.get("fault_id"), "Fault"),
        ] if n]

        _entity_response = {
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
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "work_order", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch work order {work_order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Equipment ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/equipment/{equipment_id}")
async def get_equipment_entity(equipment_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    """Fetch equipment by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_equipment').select('*').eq('id', equipment_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Equipment not found")

        data = response.data
        metadata = data.get('metadata') or {}

        attachments = _get_attachments(supabase, "equipment", equipment_id, yacht_id)

        try:
            notes_r = supabase.table('pms_notes').select(
                'id, text, note_type, created_by, created_at'
            ).eq('equipment_id', equipment_id).eq('yacht_id', yacht_id).order('created_at', desc=True).execute()
            equipment_notes = notes_r.data or []
        except Exception:
            equipment_notes = []

        # Find linked work orders and faults
        nav = []
        try:
            wo_r = supabase.table("pms_work_orders").select("id, title").eq(
                "equipment_id", equipment_id
            ).eq("yacht_id", yacht_id).limit(3).execute()
            for wo in (wo_r.data or []):
                n = _nav("work_order", wo.get("id"), wo.get("title") or "Work Order")
                if n:
                    nav.append(n)
        except Exception:
            pass
        try:
            f_r = supabase.table("pms_faults").select("id, title").eq(
                "equipment_id", equipment_id
            ).eq("yacht_id", yacht_id).limit(3).execute()
            for f in (f_r.data or []):
                n = _nav("fault", f.get("id"), f.get("title") or "Fault")
                if n:
                    nav.append(n)
        except Exception:
            pass

        _entity_response = {
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
            "attachments": attachments,
            "related_entities": nav,
            "notes": equipment_notes,
        }
        _entity_response["available_actions"] = get_available_actions(
            "equipment", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch equipment {equipment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Part ───────────────────────────────────────────────────────────────────────

@router.get("/v1/entity/part/{part_id}")
async def get_part_entity(part_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    """Fetch part by ID for entity viewer (ContextPanel)."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_parts').select('*').eq('id', part_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not response or not response.data:
            raise HTTPException(status_code=404, detail="Part not found")

        data = response.data
        metadata = data.get('metadata') or {}

        # Hero photo (image_storage_path + image_bucket confirmed in pms_parts)
        image_bucket = data.get('image_bucket') or 'pms-work-order-photos'
        image_url = _sign_url(supabase, image_bucket, data.get('image_storage_path'))

        attachments = _get_attachments(supabase, "part", part_id, yacht_id)

        try:
            notes_r = supabase.table('pms_notes').select(
                'id, text, note_type, created_by, created_at'
            ).eq('part_id', part_id).eq('yacht_id', yacht_id).order('created_at', desc=True).execute()
            part_notes = notes_r.data or []
        except Exception:
            part_notes = []

        _entity_response = {
            "id": data.get('id'),
            "name": data.get('name') or 'Unknown Part',
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
            "image_url": image_url,
            "attachments": attachments,
            "related_entities": [],
            "notes": part_notes,
        }
        _entity_response["available_actions"] = get_available_actions(
            "part", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch part {part_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Receiving ──────────────────────────────────────────────────────────────────

@router.get("/v1/entity/receiving/{receiving_id}")
async def get_receiving_entity(receiving_id: str, auth: dict = Depends(get_authenticated_user), yacht_id: Optional[str] = Query(None, description="Vessel scope (fleet users)")):
    """Fetch receiving by ID for entity viewer (DeepLinkHandler)."""
    try:
        yacht_id = resolve_yacht_id(auth, yacht_id)
        tenant_key = auth['tenant_key_alias']
        supabase = get_tenant_client(tenant_key)

        response = supabase.table('pms_receiving') \
            .select('*') \
            .eq('id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .maybe_single() \
            .execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Receiving not found")

        data = response.data

        items_response = supabase.table('pms_receiving_items') \
            .select('id, description, quantity_expected, quantity_received, unit_price, currency, part_id') \
            .eq('receiving_id', receiving_id) \
            .eq('yacht_id', yacht_id) \
            .execute()
        raw_items = items_response.data or []

        attachments = _get_attachments(supabase, "receiving", receiving_id, yacht_id)

        # Invoice images = attachments with image MIME types
        invoice_images = [
            a for a in attachments
            if (a.get("mime_type") or "").startswith("image/")
        ]

        # Nav links: items' part_id → Part, po_number → Purchase Order
        nav = []
        for it in raw_items[:5]:
            n = _nav("part", it.get("part_id"), it.get("description") or "Part")
            if n:
                nav.append(n)
        po_num = data.get("po_number")
        if po_num:
            try:
                po_r = supabase.table("pms_purchase_orders").select("id").eq(
                    "po_number", po_num
                ).eq("yacht_id", yacht_id).maybe_single().execute()
                if po_r and po_r.data:
                    n = _nav("purchase_order", po_r.data["id"], f"PO {po_num}")
                    if n:
                        nav.append(n)
            except Exception:
                pass

        _entity_response = {
            "id": data.get('id'),
            "vendor_name": data.get('vendor_name'),
            "vendor_reference": data.get('vendor_reference'),
            "po_number": po_num,
            "received_date": data.get('received_date'),
            "status": data.get('status', 'draft'),
            "total": data.get('total'),
            "currency": data.get('currency'),
            "notes": data.get('notes'),
            "received_by": data.get('received_by'),
            "items": raw_items,
            "created_at": data.get('created_at'),
            "updated_at": data.get('updated_at'),
            "invoice_images": invoice_images,
            "attachments": attachments,
            "related_entities": nav,
        }
        _entity_response["available_actions"] = get_available_actions(
            "receiving", _entity_response, auth.get("role", "crew")
        )
        return _entity_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch receiving {receiving_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
