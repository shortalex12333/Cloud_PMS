"""
Hours of Rest Routes
====================

FastAPI routes for Hours of Rest (HOR) Lens - Crew Compliance Domain.
MLC 2006 & STCW Convention compliance tracking.

Endpoints (12 total):

Daily HOR Records:
- GET  /v1/hours-of-rest                    - View HOR records (READ) [get_hours_of_rest]
- POST /v1/hours-of-rest/upsert             - Upsert HOR record (MUTATE) [upsert_hours_of_rest]
- POST /v1/hours-of-rest/export             - Export HOR data (READ) [export_hours_of_rest]

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

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import os
from datetime import datetime, timezone
from supabase import create_client, Client

# Import handlers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from handlers.hours_of_rest_handlers import HoursOfRestHandlers
from action_router.validators import validate_jwt, validate_yacht_isolation
from pipeline_service import get_tenant_client

logger = logging.getLogger(__name__)

# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_supabase_client() -> Optional[Client]:
    """Get TENANT Supabase client for yacht operations data.

    Uses DEFAULT_YACHT_CODE env var to construct tenant-specific credentials.
    Falls back to generic SUPABASE_URL/SUPABASE_SERVICE_KEY if tenant vars missing.
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        logger.warning(f"Missing TENANT Supabase credentials for {default_yacht}")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


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
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    user_id: Optional[str] = Field(None, description="User ID (defaults to auth user)")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD (defaults to 7 days ago)")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD (defaults to today)")


class UpdateHoursRequest(BaseModel):
    """Request body for upsert endpoint (MUTATE - signature optional)."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    record_date: str = Field(..., description="Record date YYYY-MM-DD")
    rest_periods: list = Field(..., description="Array of rest period objects")
    signature: Optional[Dict[str, Any]] = Field(None, description="Digital signature (optional, included in audit trail)")
    daily_compliance_notes: Optional[str] = Field(None, description="Optional notes")


class ExportHoursRequest(BaseModel):
    """Request body for export endpoint."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    user_id: Optional[str] = Field(None, description="User ID (defaults to auth user)")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    format: Optional[str] = Field("json", description="Export format: json, pdf, csv")


# Monthly Sign-off Models
class CreateMonthlySignoffRequest(BaseModel):
    """Request body for creating monthly sign-off."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    month: str = Field(..., description="Month in YYYY-MM format")
    department: str = Field(..., description="Department: engineering/deck/interior/galley/general")


class SignMonthlySignoffRequest(BaseModel):
    """Request body for signing monthly sign-off."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    signoff_id: str = Field(..., description="Sign-off UUID")
    signature_level: str = Field(..., description="crew|hod|master")
    signature_data: Dict[str, Any] = Field(..., description="Signature data {name, timestamp, ip_address}")
    notes: Optional[str] = Field(None, description="Optional notes/declaration")


# Schedule Template Models
class CreateCrewTemplateRequest(BaseModel):
    """Request body for creating schedule template."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    schedule_name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    schedule_template: Dict[str, Any] = Field(..., description="JSONB with 7 days schedule")
    applies_to: Optional[str] = Field("normal", description="normal|port|transit")
    is_active: Optional[bool] = Field(True, description="Activate template")


class ApplyCrewTemplateRequest(BaseModel):
    """Request body for applying schedule template."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    week_start_date: str = Field(..., description="Week start date YYYY-MM-DD (Monday)")
    template_id: Optional[str] = Field(None, description="Template UUID (uses active if not provided)")


# Warning Models
class AcknowledgeWarningRequest(BaseModel):
    """Request body for acknowledging warning."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    warning_id: str = Field(..., description="Warning UUID")
    crew_reason: Optional[str] = Field(None, description="Explanation text")


class DismissWarningRequest(BaseModel):
    """Request body for dismissing warning (HOD+ only)."""
    yacht_id: str = Field(..., description="Yacht ID (tenant isolation)")
    warning_id: str = Field(..., description="Warning UUID")
    hod_justification: str = Field(..., description="Explanation required")
    dismissed_by_role: str = Field(..., description="hod|captain")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("")
async def get_hours_of_rest_route(
    yacht_id: str,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    View Hours of Rest records for a user within date range.

    **Action**: get_hours_of_rest
    **Variant**: READ
    **Allowed Roles**: All authenticated users (with RLS restrictions)
    **Endpoint**: GET /v1/hours-of-rest

    Returns daily HOR records with compliance indicators.
    """
    # Validate JWT first to get tenant_key_alias
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "UNAUTHORIZED",
                "error_code": "UNAUTHORIZED",
                "message": jwt_result.error.message if jwt_result.error else "Invalid or missing JWT"
            }
        )

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}

    # Validate yacht isolation
    yacht_validation = validate_yacht_isolation({"yacht_id": yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FORBIDDEN",
                "error_code": "YACHT_ISOLATION_VIOLATION",
                "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation validation failed"
            }
        )

    # Get handlers with tenant-specific client
    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
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
        logger.error(f"view_hours_of_rest error: {e}", exc_info=True)
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
    authorization: str = Header(None)
):
    """
    Upsert Hours of Rest record (MUTATE action).

    **Action**: upsert_hours_of_rest
    **Variant**: MUTATE (NOT SIGNED per registry)
    **Allowed Roles**: All authenticated users (own records only via RLS)
    **Endpoint**: POST /v1/hours-of-rest/upsert

    Creates or updates a daily HOR record.
    """
    # Validate JWT first to get tenant_key_alias
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "UNAUTHORIZED",
                "error_code": "UNAUTHORIZED",
                "message": jwt_result.error.message if jwt_result.error else "Invalid or missing JWT"
            }
        )

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}

    # Validate yacht isolation
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FORBIDDEN",
                "error_code": "YACHT_ISOLATION_VIOLATION",
                "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation validation failed"
            }
        )

    # Get handlers with tenant-specific client
    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    # NOTE: Registry shows this as MUTATE not SIGNED, so signature is optional
    # If signature provided, it will be included in audit trail

    # Call handler
    try:
        result = await hor_handlers.upsert_hours_of_rest(
            entity_id=user_id_from_jwt,  # HOR updates are for self
            yacht_id=request.yacht_id,
            user_id=user_id_from_jwt,
            payload={
                "record_date": request.record_date,
                "rest_periods": request.rest_periods,
                "signature": request.signature,
                "daily_compliance_notes": request.daily_compliance_notes
            }
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"update_hours_of_rest error: {e}", exc_info=True)

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
    authorization: str = Header(None)
):
    """
    Export Hours of Rest data in specified format.

    **Action**: export_hours_of_rest
    **Variant**: READ
    **Allowed Roles**: All authenticated users (with RLS restrictions)

    Returns HOR data as JSON, PDF, or CSV.
    """
    # Validate JWT first to get tenant_key_alias
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "UNAUTHORIZED",
                "error_code": "UNAUTHORIZED",
                "message": jwt_result.error.message if jwt_result.error else "Invalid or missing JWT"
            }
        )

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}

    # Validate yacht isolation
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FORBIDDEN",
                "error_code": "YACHT_ISOLATION_VIOLATION",
                "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation validation failed"
            }
        )

    # For now, return JSON format (PDF export can be added later)
    if request.format and request.format not in ["json", "pdf", "csv"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FORMAT",
                "message": f"Format '{request.format}' not supported. Use: json, pdf, csv"
            }
        )

    # Get handlers with tenant-specific client
    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    # Call handler (reuse get_hours_of_rest for JSON export)
    try:
        entity_id = request.user_id or user_id_from_jwt

        result = await hor_handlers.get_hours_of_rest(
            entity_id=entity_id,
            yacht_id=request.yacht_id,
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
                "yacht_id": request.yacht_id
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
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(None)
):
    """
    List monthly sign-offs for user or department.

    **Action**: list_monthly_signoffs
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/signoffs
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.list_monthly_signoffs(
            entity_id=user_id or user_id_from_jwt,
            yacht_id=yacht_id,
            params={"user_id": user_id, "department": department, "status": status, "limit": limit, "offset": offset}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"list_monthly_signoffs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.get("/signoffs/details")
async def get_monthly_signoff_route(
    yacht_id: str,
    signoff_id: str,
    authorization: str = Header(None)
):
    """
    Get monthly sign-off details.

    **Action**: get_monthly_signoff
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/signoffs/details
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
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
    authorization: str = Header(None)
):
    """
    Create monthly sign-off (starts as draft).

    **Action**: create_monthly_signoff
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/signoffs/create
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.create_monthly_signoff(
            entity_id=user_id_from_jwt,
            yacht_id=request.yacht_id,
            user_id=user_id_from_jwt,
            payload={"month": request.month, "department": request.department}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"create_monthly_signoff error: {e}", exc_info=True)
        error_str = str(e).lower()
        if "duplicate" in error_str or "already exists" in error_str:
            raise HTTPException(status_code=409, detail={"error": "CONFLICT", "message": str(e)})
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": str(e)})


@router.post("/signoffs/sign")
async def sign_monthly_signoff_route(
    request: SignMonthlySignoffRequest,
    authorization: str = Header(None)
):
    """
    Add signature to monthly sign-off (crew/HOD/captain).

    **Action**: sign_monthly_signoff
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/signoffs/sign
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.sign_monthly_signoff(
            entity_id=request.signoff_id,
            yacht_id=request.yacht_id,
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
    authorization: str = Header(None)
):
    """
    List schedule templates for user.

    **Action**: list_crew_templates
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/templates
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
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


@router.post("/templates/create")
async def create_crew_template_route(
    request: CreateCrewTemplateRequest,
    authorization: str = Header(None)
):
    """
    Create schedule template.

    **Action**: create_crew_template
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/templates/create
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.create_crew_template(
            entity_id=user_id_from_jwt,
            yacht_id=request.yacht_id,
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
    authorization: str = Header(None)
):
    """
    Apply template to week of dates.

    **Action**: apply_crew_template
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/templates/apply
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.apply_crew_template(
            entity_id=user_id_from_jwt,
            yacht_id=request.yacht_id,
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
    yacht_id: str,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    warning_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    authorization: str = Header(None)
):
    """
    List compliance warnings for user.

    **Action**: list_crew_warnings
    **Variant**: READ
    **Endpoint**: GET /v1/hours-of-rest/warnings
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
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
    authorization: str = Header(None)
):
    """
    Crew acknowledges warning (cannot dismiss).

    **Action**: acknowledge_warning
    **Variant**: MUTATE
    **Endpoint**: POST /v1/hours-of-rest/warnings/acknowledge
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.acknowledge_warning(
            entity_id=request.warning_id,
            yacht_id=request.yacht_id,
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
    authorization: str = Header(None)
):
    """
    HOD/Captain dismisses warning (requires justification).

    **Action**: dismiss_warning
    **Variant**: MUTATE
    **Allowed Roles**: HOD+ only (chief_engineer, chief_officer, captain, manager)
    **Endpoint**: POST /v1/hours-of-rest/warnings/dismiss
    """
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORIZED", "message": jwt_result.error.message if jwt_result.error else "Invalid JWT"})

    user_id_from_jwt = jwt_result.context.get("user_id") if jwt_result.context else None
    user_context = jwt_result.context or {}
    user_role = jwt_result.context.get("role", "crew") if jwt_result.context else "crew"

    # Role check - HOD+ only
    hod_plus_roles = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"]
    if user_role.lower() not in hod_plus_roles:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": f"Role '{user_role}' cannot dismiss warnings. HOD+ required."})

    yacht_validation = validate_yacht_isolation({"yacht_id": request.yacht_id}, user_context)
    if not yacht_validation.valid:
        raise HTTPException(status_code=403, detail={"error": "YACHT_ISOLATION_VIOLATION", "message": yacht_validation.error.message if yacht_validation.error else "Yacht isolation failed"})

    tenant_key_alias = user_context.get("tenant_key_alias")
    if not tenant_key_alias:
        raise HTTPException(status_code=500, detail={"error": "INTERNAL_SERVER_ERROR", "message": "No tenant key found"})
    hor_handlers = get_hor_handlers(tenant_key_alias)

    try:
        result = await hor_handlers.dismiss_warning(
            entity_id=request.warning_id,
            yacht_id=request.yacht_id,
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
