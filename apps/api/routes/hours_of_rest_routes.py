"""
Hours of Rest Routes
====================

FastAPI routes for Hours of Rest (HOR) Lens - Crew Compliance Domain.
MLC 2006 & STCW Convention compliance tracking.

Endpoints (19 total):

Daily HOR Records:
- GET  /v1/hours-of-rest                    - View HOR records (READ) [get_hours_of_rest]
- POST /v1/hours-of-rest/upsert             - Upsert HOR record (MUTATE) [upsert_hours_of_rest]
- POST /v1/hours-of-rest/export             - Export HOR data (READ) — direct route, reuses get_hours_of_rest handler
- POST /v1/hours-of-rest/undo               - Undo submitted day (MUTATE) [undo_hours_of_rest]

MLC 2006 Corrections:
- POST /v1/hours-of-rest/corrections        - Create correction/note (MUTATE) [create_hor_correction]
- POST /v1/hours-of-rest/request-correction - HOD/Captain kick-back (MUTATE) [request_hor_correction]

Notifications:
- GET  /v1/hours-of-rest/notifications/unread    - Unread notifications [get_unread_notifications]
- POST /v1/hours-of-rest/notifications/mark-read - Mark as read [mark_notifications_read]

Sign Chain (Fleet Manager):
- GET  /v1/hours-of-rest/sign-chain         - Per-vessel sign chain status [get_hor_sign_chain]

Monthly Sign-offs:
- GET  /v1/hours-of-rest/signoffs           - List sign-offs (READ) [list_monthly_signoffs]
- GET  /v1/hours-of-rest/signoffs/details   - Get sign-off details (READ) [get_monthly_signoff]
- POST /v1/hours-of-rest/signoffs/create    - Create sign-off (MUTATE) [create_monthly_signoff]
- POST /v1/hours-of-rest/signoffs/sign      - Sign sign-off (MUTATE) [sign_monthly_signoff]

Schedule Templates:
- GET  /v1/hours-of-rest/templates          - List templates (READ) [list_crew_templates]
- POST /v1/hours-of-rest/templates/create   - Create template (MUTATE) [create_crew_template]
- POST /v1/hours-of-rest/templates/apply    - Apply template (MUTATE) [apply_crew_template]

Compliance Warnings:
- GET  /v1/hours-of-rest/warnings           - List warnings (READ) [list_crew_warnings]
- POST /v1/hours-of-rest/warnings/acknowledge - Acknowledge warning (MUTATE) [acknowledge_warning]
- POST /v1/hours-of-rest/warnings/dismiss   - Dismiss warning (MUTATE, HOD+) [dismiss_warning]

All routes require JWT authentication and yacht isolation validation.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime, timezone, timedelta, date
from supabase import Client

# Import handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from handlers.hours_of_rest_handlers import HoursOfRestHandlers
from middleware.auth import get_authenticated_user
from middleware.vessel_access import resolve_yacht_id

# Centralized Supabase client factory
from integrations.supabase import get_supabase_client, get_tenant_client

logger = logging.getLogger(__name__)

# ============================================================================
# SUPABASE CLIENT
# ============================================================================
# NOTE: get_supabase_client and get_tenant_client are imported from integrations.supabase


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/v1/hours-of-rest", tags=["hours-of-rest"])

# Per-request handler initialization with tenant-specific client
_hor_handlers_cache = {}

def get_hor_handlers(tenant_key_alias: str):
    """Get or initialize HOR handlers for specific tenant."""
    global _hor_handlers_cache
    if tenant_key_alias not in _hor_handlers_cache:
        supabase = get_tenant_client(tenant_key_alias)
        if supabase:
            try:
                _hor_handlers_cache[tenant_key_alias] = HoursOfRestHandlers(supabase)
                logger.info(f"✅ Hours of Rest handlers initialized for {tenant_key_alias}")
            except Exception as e:
                logger.error(f"Failed to initialize HOR handlers: {e}")
                raise HTTPException(status_code=503, detail="HOR handlers initialization failed")
        else:
            logger.warning(f"⚠️ HOR handlers not initialized - no database connection for {tenant_key_alias}")
            raise HTTPException(status_code=503, detail="Database connection not available")
    return _hor_handlers_cache[tenant_key_alias]


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ViewHoursRequest(BaseModel):
    """Request body for view endpoint."""
    # Note: yacht_id comes from JWT auth context for MUTATE actions
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation) - for GET queries only")
    user_id: Optional[str] = Field(None, description="User ID (defaults to auth user)")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD (defaults to 7 days ago)")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD (defaults to today)")


class UpdateHoursRequest(BaseModel):
    """Request body for upsert endpoint (MUTATE - signature optional).

    Work/rest inversion (2026-04-13):
      Crew now inputs work_periods; backend derives rest_periods as 24h complement.
      rest_periods is kept as an optional alias so any existing direct callers do not 500,
      but the handler ignores it — only work_periods is processed.
    """
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    record_date: str = Field(..., description="Record date YYYY-MM-DD")
    work_periods: Optional[list] = Field(None, description="Array of {start, end} work period objects. Empty = full rest day.")
    rest_periods: Optional[list] = Field(None, description="DEPRECATED: ignored. Backend derives rest from work_periods complement.")
    signature: Optional[Dict[str, Any]] = Field(None, description="Digital signature (optional, included in audit trail)")
    daily_compliance_notes: Optional[str] = Field(None, description="Optional notes")
    crew_comment: Optional[str] = Field(None, description="Required justification when logging non-compliant hours (MLC A2.3)")


class ExportHoursRequest(BaseModel):
    """Request body for export endpoint."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    user_id: Optional[str] = Field(None, description="User ID (defaults to auth user)")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    format: Optional[str] = Field("json", description="Export format: json, pdf, csv")


# Monthly Sign-off Models
class CreateMonthlySignoffRequest(BaseModel):
    """Request body for creating monthly or weekly sign-off."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    month: Optional[str] = Field(None, description="Month in YYYY-MM format (required for monthly, auto-derived for weekly)")
    department: str = Field(..., description="Department: engineering/deck/interior/galley/general")
    period_type: Optional[str] = Field("monthly", description="weekly|monthly (default: monthly)")
    week_start: Optional[str] = Field(None, description="Monday date YYYY-MM-DD (required if period_type=weekly)")
    target_user_id: Optional[str] = Field(None, description="UUID of crew member to create signoff for (HOD use)")


class SignMonthlySignoffRequest(BaseModel):
    """Request body for signing monthly sign-off."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    signoff_id: str = Field(..., description="Sign-off UUID")
    signature_level: str = Field(..., description="crew|hod|master")
    signature_data: Dict[str, Any] = Field(..., description="Signature data {name, timestamp, ip_address}")
    notes: Optional[str] = Field(None, description="Optional notes/declaration")


# Schedule Template Models
class CreateCrewTemplateRequest(BaseModel):
    """Request body for creating schedule template."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    schedule_name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    schedule_template: Dict[str, Any] = Field(..., description="JSONB with 7 days schedule")
    applies_to: Optional[str] = Field("normal", description="normal|port|transit")
    is_active: Optional[bool] = Field(True, description="Activate template")


class ApplyCrewTemplateRequest(BaseModel):
    """Request body for applying schedule template."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    week_start_date: str = Field(..., description="Week start date YYYY-MM-DD (Monday)")
    template_id: Optional[str] = Field(None, description="Template UUID (uses active if not provided)")


# Warning Models
class AcknowledgeWarningRequest(BaseModel):
    """Request body for acknowledging warning."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    warning_id: str = Field(..., description="Warning UUID")
    crew_reason: Optional[str] = Field(None, description="Explanation text")


class DismissWarningRequest(BaseModel):
    """Request body for dismissing warning (HOD+ only)."""
    # Note: yacht_id comes from JWT auth context, this field is ignored for security
    yacht_id: Optional[str] = Field(None, description="DEPRECATED: yacht_id now from JWT context")
    warning_id: str = Field(..., description="Warning UUID")
    hod_justification: str = Field(..., description="Explanation required")
    dismissed_by_role: str = Field(..., description="hod|captain")


class UndoHoursRequest(BaseModel):
    """Request body for undoing a submitted HoR record."""
    record_id: str = Field(..., description="UUID of pms_hours_of_rest row to undo")


class CreateCorrectionRequest(BaseModel):
    """Request body for creating a HoR correction or note."""
    original_record_id: str = Field(..., description="UUID of pms_hours_of_rest row to correct")
    reason: str = Field(..., description="Mandatory legal field — why correction was made")
    note: Optional[str] = Field(None, description="Optional additional context")
    corrected_rest_periods: Optional[list] = Field(None, description="New rest periods (crew only). Omit for note-only.")
    requested_by_user_id: Optional[str] = Field(None, description="Who requested this correction (HOD/Captain UUID)")
    correction_chain: Optional[list] = Field(None, description="Ordered kick-back chain [{user_id, role, requested_at}]")


class RequestCorrectionRequest(BaseModel):
    """Request body for HOD/Captain requesting a correction kick-back."""
    signoff_id: str = Field(..., description="UUID of pms_hor_monthly_signoffs row")
    target_user_id: str = Field(..., description="UUID of user who should receive the correction request")
    correction_note: str = Field(..., description="What needs correcting (required)")
    role: str = Field(..., description="hod|captain — role of the requester")


class MarkReadRequest(BaseModel):
    """Request body for marking notifications as read."""
    notification_ids: Optional[list] = Field(None, description="List of notification UUIDs. Omit to mark ALL as read.")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
async def get_hours_of_rest_route(
    yacht_id: str,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    View Hours of Rest records for a user within date range.

    **Action**: get_hours_of_rest
    **Variant**: READ
    **Allowed Roles**: All authenticated users (with RLS restrictions)
    **Endpoint**: GET /v1/hours-of-rest

    Returns daily HOR records with compliance indicators.
    """
    user_id_from_jwt = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # Validate yacht isolation — fleet-aware (validates against vessel_ids, not just primary yacht_id)
    yacht_id = resolve_yacht_id(auth, yacht_id)

    hor_handlers = get_hor_handlers(tenant_key_alias)

    # Call handler
    try:
        # Entity ID for HOR view is the user being viewed
        entity_id = user_id or user_id_from_jwt

        result = await hor_handlers.get_hours_of_rest(
            entity_id=entity_id,
            yacht_id=yacht_id,
            params={
                "user_id": entity_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"get_hours_of_rest error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": str(e)
            }
        )


@router.post("/upsert")
async def upsert_hours_of_rest_route(
    request: UpdateHoursRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Upsert Hours of Rest record (MUTATE action).

    **Action**: upsert_hours_of_rest
    **Variant**: MUTATE (NOT SIGNED per registry)
    **Allowed Roles**: All authenticated users (own records only via RLS)
    **Endpoint**: POST /v1/hours-of-rest/upsert

    Creates or updates a daily HOR record.
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    hor_handlers = get_hor_handlers(tenant_key_alias)

    # NOTE: Registry shows this as MUTATE not SIGNED, so signature is optional
    # If signature provided, it will be included in audit trail

    # Call handler
    try:
        # work_periods is the canonical field. If caller sends only the deprecated
        # rest_periods, pass an empty work_periods so the handler returns a full rest day.
        work_periods = request.work_periods if request.work_periods is not None else []
        result = await hor_handlers.upsert_hours_of_rest(
            entity_id=user_id_from_jwt,  # HOR updates are for self
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "record_date": request.record_date,
                "work_periods": work_periods,
                "signature": request.signature,
                "daily_compliance_notes": request.daily_compliance_notes,
                "crew_comment": request.crew_comment
            }
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"upsert_hours_of_rest error: {e}", exc_info=True)

        # Map known errors to proper 4xx codes
        error_str = str(e).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        elif "duplicate" in error_str or "already exists" in error_str:
            raise HTTPException(status_code=409, detail={"error": "CONFLICT", "message": str(e)})
        elif "invalid" in error_str or "validation" in error_str:
            raise HTTPException(status_code=400, detail={"error": "BAD_REQUEST", "message": str(e)})
        else:
            # Genuine 500
            raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/export")
async def export_hours_of_rest(
    request: ExportHoursRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Export Hours of Rest data in specified format.

    **Action**: export_hours_of_rest
    **Variant**: READ
    **Allowed Roles**: All authenticated users (with RLS restrictions)

    Returns HOR data as JSON, PDF, or CSV.
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # For now, return JSON format (PDF export can be added later)
    if request.format and request.format not in ["json", "pdf", "csv"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FORMAT",
                "message": f"Format '{request.format}' not supported. Use: json, pdf, csv"
            }
        )

    hor_handlers = get_hor_handlers(tenant_key_alias)

    # Call handler (reuse get_hours_of_rest for JSON export)
    try:
        entity_id = request.user_id or user_id_from_jwt

        result = await hor_handlers.get_hours_of_rest(
            entity_id=entity_id,
            yacht_id=yacht_id,
            params={
                "user_id": entity_id,
                "start_date": request.start_date,
                "end_date": request.end_date
            }
        )

        # Wrap in export envelope
        export_result = {
            "status": "success",
            "action": "export_hours_of_rest",
            "domain": "compliance",
            "format": request.format or "json",
            "data": result.get("data", {}),
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "exported_by": user_id_from_jwt,
                "yacht_id": yacht_id
            }
        }

        return JSONResponse(content=export_result)

    except Exception as e:
        logger.error(f"export_hours_of_rest error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": str(e)
            }
        )


# ============================================================================
# MONTHLY SIGN-OFF ENDPOINTS
# ============================================================================

@router.get("/signoffs")
async def list_monthly_signoffs_route(
    yacht_id: str,
    user_id: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    period_type: Optional[str] = None,
    week_start: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(get_authenticated_user)
):
    """
    List monthly sign-offs for user or department.

    **Action**: list_monthly_signoffs
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/signoffs
    """
    user_id_from_jwt = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # Validate yacht isolation — fleet-aware (validates against vessel_ids, not just primary yacht_id)
    yacht_id = resolve_yacht_id(auth, yacht_id)

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.list_monthly_signoffs(
            entity_id=user_id or user_id_from_jwt,
            yacht_id=yacht_id,
            params={
                "user_id": user_id,
                "department": department,
                "status": status,
                "period_type": period_type,
                "week_start": week_start,
                "limit": limit,
                "offset": offset,
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"list_monthly_signoffs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.get("/signoffs/details")
async def get_monthly_signoff_route(
    yacht_id: str,
    signoff_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get monthly sign-off details.

    **Action**: get_monthly_signoff
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/signoffs/details
    """
    user_id_from_jwt = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # Validate yacht isolation — fleet-aware (validates against vessel_ids, not just primary yacht_id)
    yacht_id = resolve_yacht_id(auth, yacht_id)

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.get_monthly_signoff(
            entity_id=signoff_id,
            yacht_id=yacht_id,
            params={"signoff_id": signoff_id}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"get_monthly_signoff error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/signoffs/create")
async def create_monthly_signoff_route(
    request: CreateMonthlySignoffRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Create monthly sign-off (starts as draft).

    **Action**: create_monthly_signoff
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/signoffs/create
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.create_monthly_signoff(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "month": request.month,
                "department": request.department,
                "period_type": request.period_type or "monthly",
                "week_start": request.week_start,
                "target_user_id": request.target_user_id,
            }
        )
        # Propagate the semantic HTTP status from the handler's error envelope
        http_status = (result.get("error") or {}).get("status_code") or 200
        return JSONResponse(content=result, status_code=http_status)
    except Exception as e:
        logger.error(f"create_monthly_signoff error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "duplicate" in error_str or "already exists" in error_str:
            raise HTTPException(status_code=409, detail={"error": "CONFLICT", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/signoffs/sign")
async def sign_monthly_signoff_route(
    request: SignMonthlySignoffRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Add signature to monthly sign-off (crew/HOD/captain).

    **Action**: sign_monthly_signoff
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/signoffs/sign
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    caller_role = auth.get("role", "")

    # Role enforcement: signature_level must match caller's role.
    # captain/manager are authorised at both HOD and master levels.
    HOD_ROLES    = {"chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"}
    MASTER_ROLES = {"captain", "master", "manager"}
    sig_level = request.signature_level
    if sig_level == "hod" and caller_role not in HOD_ROLES:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN",
            "message": f"HOD signature requires HOD role. Your role: {caller_role}"})
    if sig_level == "master" and caller_role not in MASTER_ROLES:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN",
            "message": f"Master signature requires captain/master role. Your role: {caller_role}"})

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.sign_monthly_signoff(
            entity_id=request.signoff_id,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "signoff_id": request.signoff_id,
                "signature_level": request.signature_level,
                "signature_data": request.signature_data,
                "notes": request.notes
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"sign_monthly_signoff error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


# ============================================================================
# SCHEDULE TEMPLATE ENDPOINTS
# ============================================================================

@router.get("/templates")
async def list_crew_templates_route(
    yacht_id: str,
    user_id: Optional[str] = None,
    is_active: bool = True,
    auth: dict = Depends(get_authenticated_user)
):
    """
    List schedule templates for user.

    **Action**: list_crew_templates
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/templates
    """
    user_id_from_jwt = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # Validate yacht isolation — fleet-aware (validates against vessel_ids, not just primary yacht_id)
    yacht_id = resolve_yacht_id(auth, yacht_id)

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.list_crew_templates(
            entity_id=user_id or user_id_from_jwt,
            yacht_id=yacht_id,
            params={"user_id": user_id or user_id_from_jwt, "is_active": is_active}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"list_crew_templates error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.get("/templates/{template_id}")
async def get_crew_template_route(
    template_id: str,
    yacht_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get single schedule template by ID.

    **Action**: get_crew_template
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/templates/{template_id}
    """
    user_id = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    yacht_id = resolve_yacht_id(auth, yacht_id)
    hor_handlers = get_hor_handlers(tenant_key_alias)
    try:
        result = await hor_handlers.get_crew_template(
            template_id=template_id,
            entity_id=user_id,
            yacht_id=yacht_id,
            user_id=user_id,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"get_crew_template error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/templates/create")
async def create_crew_template_route(
    request: CreateCrewTemplateRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Create schedule template.

    **Action**: create_crew_template
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/templates/create
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.create_crew_template(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "schedule_name": request.schedule_name,
                "description": request.description,
                "schedule_template": request.schedule_template,
                "applies_to": request.applies_to,
                "is_active": request.is_active
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"create_crew_template error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/templates/apply")
async def apply_crew_template_route(
    request: ApplyCrewTemplateRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Apply template to week of dates.

    **Action**: apply_crew_template
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/templates/apply
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.apply_crew_template(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={"week_start_date": request.week_start_date, "template_id": request.template_id}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"apply_crew_template error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


# ============================================================================
# WARNING ENDPOINTS
# ============================================================================

@router.get("/warnings")
async def list_crew_warnings_route(
    yacht_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    warning_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(get_authenticated_user)
):
    """
    List compliance warnings for user.

    **Action**: list_crew_warnings
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/warnings
    """
    user_id_from_jwt = auth["user_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    # Validate yacht isolation — fleet-aware (validates against vessel_ids, not just primary yacht_id)
    yacht_id = resolve_yacht_id(auth, yacht_id)

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.list_crew_warnings(
            entity_id=user_id or user_id_from_jwt,
            yacht_id=yacht_id,
            params={"user_id": user_id or user_id_from_jwt, "status": status, "warning_type": warning_type, "limit": limit, "offset": offset}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"list_crew_warnings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/warnings/acknowledge")
async def acknowledge_warning_route(
    request: AcknowledgeWarningRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Crew acknowledges warning (cannot dismiss).

    **Action**: acknowledge_warning
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/warnings/acknowledge
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.acknowledge_warning(
            entity_id=request.warning_id,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={"warning_id": request.warning_id, "crew_reason": request.crew_reason}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"acknowledge_warning error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/warnings/dismiss")
async def dismiss_warning_route(
    request: DismissWarningRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    HOD/Captain dismisses warning (requires justification).

    **Action**: dismiss_warning
    **Variant**: MUTATE
    **Allowed Roles**: HOD+ only (chief_engineer, chief_officer, captain, manager)
    **Endpoint**: POST /v1/hours-of-rest/warnings/dismiss
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    user_role = auth.get("role", "crew")

    # Role check - HOD+ only
    hod_plus_roles = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"]
    if user_role.lower() not in hod_plus_roles:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": f"Role '{user_role}' cannot dismiss warnings. HOD+ required."})

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.dismiss_warning(
            entity_id=request.warning_id,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "warning_id": request.warning_id,
                "hod_justification": request.hod_justification,
                "dismissed_by_role": request.dismissed_by_role
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"dismiss_warning error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


# ============================================================================
# MLC 2006 PHASE 1 — UNDO / CORRECTIONS / NOTIFICATIONS / SIGN CHAIN
# ============================================================================

@router.post("/undo")
async def undo_hours_of_rest_route(
    request: UndoHoursRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Crew undoes their own submitted HoR record.

    MLC: original preserved in pms_hor_corrections. Blocked if HOD already signed.

    **Action**: undo_hours_of_rest
    **Endpoint**: POST /v1/hours-of-rest/undo
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.undo_hours_of_rest(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={"record_id": request.record_id}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"undo_hours_of_rest error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "locked" in error_str:
            raise HTTPException(status_code=409, detail={"error": "LOCKED", "message": str(e)})
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/corrections")
async def create_hor_correction_route(
    request: CreateCorrectionRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Create a correction for an existing HoR record.

    Crew: full time correction (corrected_rest_periods required).
    HOD/Captain: note only (corrected_rest_periods omitted).
    Original is NEVER modified.

    **Action**: create_hor_correction
    **Endpoint**: POST /v1/hours-of-rest/corrections
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.create_hor_correction(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "original_record_id": request.original_record_id,
                "reason": request.reason,
                "note": request.note,
                "corrected_rest_periods": request.corrected_rest_periods,
                "requested_by_user_id": request.requested_by_user_id,
                "correction_chain": request.correction_chain or [],
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"create_hor_correction error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        if "forbidden" in error_str:
            raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/request-correction")
async def request_hor_correction_route(
    request: RequestCorrectionRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    HOD or Captain requests a correction from the party below them.

    HOD → Crew: sets correction_requested on weekly signoff, notifies crew.
    Captain → HOD: same but notifies HOD.

    **Action**: request_hor_correction
    **Endpoint**: POST /v1/hours-of-rest/request-correction
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    user_role = auth.get("role", "crew")

    hod_plus_roles = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"]
    if user_role.lower() not in hod_plus_roles:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": "HOD+ required to request corrections"})

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.request_hor_correction(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "signoff_id": request.signoff_id,
                "target_user_id": request.target_user_id,
                "correction_note": request.correction_note,
                "role": request.role,
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"request_hor_correction error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "not found" in error_str:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": str(e)})
        if "invalid_state" in error_str or "invalid state" in error_str:
            raise HTTPException(status_code=409, detail={"error": "INVALID_STATE", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.get("/notifications/unread")
async def get_unread_notifications_route(
    limit: int = 50,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get unread HoR notifications for the current user.

    **Action**: get_unread_notifications
    **Endpoint**: GET /v1/hours-of-rest/notifications/unread
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.get_unread_notifications(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            params={"limit": limit}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"get_unread_notifications error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/notifications/mark-read")
async def mark_notifications_read_route(
    request: MarkReadRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Mark one or all notifications as read.

    **Action**: mark_notifications_read
    **Endpoint**: POST /v1/hours-of-rest/notifications/mark-read
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.mark_notifications_read(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            user_id=user_id_from_jwt,
            payload={"notification_ids": request.notification_ids}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"mark_notifications_read error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.get("/sign-chain")
async def get_hor_sign_chain_route(
    week_start: str,
    target_yacht_id: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get per-vessel sign chain status for fleet manager (S6).

    Returns crew submission count, per-dept HOD sign status,
    captain sign status, FM review status, and outstanding corrections.

    **Action**: get_hor_sign_chain
    **Endpoint**: GET /v1/hours-of-rest/sign-chain
    """
    user_id_from_jwt = auth["user_id"]
    yacht_id = auth["yacht_id"]
    tenant_key_alias = auth["tenant_key_alias"]
    caller_role = auth.get("role", "")

    # Role enforcement: sign-chain is for managers, captains, and HODs only
    SIGN_CHAIN_ROLES = {"manager", "owner", "captain", "master",
                        "chief_engineer", "chief_officer", "chief_steward", "eto", "purser"}
    if caller_role not in SIGN_CHAIN_ROLES:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN",
            "message": "sign-chain access requires manager/captain/HOD role"})

    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.get_hor_sign_chain(
            entity_id=user_id_from_jwt,
            yacht_id=yacht_id,
            params={
                "week_start": week_start,
                "target_yacht_id": target_yacht_id,
            }
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"get_hor_sign_chain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})
