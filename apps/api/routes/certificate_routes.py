"""
Certificate Routes
==================

API endpoints for certificate management (Certificate Lens v2).

Includes:
- CRUD operations for vessel and crew certificates
- Expiry monitoring endpoints
- Debug endpoint for pipeline testing

Feature flags:
- FEATURE_CERTIFICATES: Backend operations
- UI_CERTIFICATES: Frontend display
"""

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import os
from supabase import Client

# Auth middleware
from middleware.auth import get_authenticated_user

# Centralized Supabase client factory
from integrations.supabase import get_supabase_client, get_tenant_client

# Certificate handlers (optional - graceful degradation if schema_mapping incomplete)
try:
    from handlers.certificate_handlers import get_certificate_handlers
    CERTIFICATE_HANDLERS_AVAILABLE = True
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Certificate handlers not available: {e}")
    get_certificate_handlers = None
    CERTIFICATE_HANDLERS_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class CertificateListParams(BaseModel):
    """Query parameters for listing certificates."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    status: Optional[str] = None
    certificate_type: Optional[str] = None
    person_name: Optional[str] = None  # For crew certificates only


class ExpiringCertificatesParams(BaseModel):
    """Query parameters for finding expiring certificates."""
    days_ahead: int = Field(default=90, ge=1, le=365)
    domain: Literal["vessel", "crew", "all"] = "all"


class CertificatePipelineTestRequest(BaseModel):
    """Request body for debug pipeline test."""
    query: str = Field(..., description="User query to test through pipeline")
    # SECURITY: yacht_id removed from request schema per invariant #1
    # yacht_id MUST come from server-resolved auth context, never client payload


class CertificatePipelineTestResponse(BaseModel):
    """Response for debug pipeline test."""
    query: str
    entities_extracted: List[dict]
    intent_detected: dict
    actions_detected: List[dict]
    handler_result: Optional[dict] = None
    debug_info: dict


# =============================================================================
# SUPABASE CLIENT
# =============================================================================
# NOTE: get_supabase_client and get_tenant_client are imported from integrations.supabase


def check_feature_flag() -> bool:
    """Check if certificate feature is enabled."""
    return os.getenv("FEATURE_CERTIFICATES", "false").lower() == "true"


def check_handlers_available():
    """Verify certificate handlers are available. Raises 503 if not."""
    if not CERTIFICATE_HANDLERS_AVAILABLE or get_certificate_handlers is None:
        raise HTTPException(
            status_code=503,
            detail="Certificate handlers not available - service degraded"
        )


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/vessel")
async def list_vessel_certificates(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    certificate_type: Optional[str] = Query(default=None),
    auth: dict = Depends(get_authenticated_user)
):
    """
    List all vessel certificates for the authenticated yacht.

    Returns paginated list with expiry warnings.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_certificate_handlers(supabase)

        result = await handlers["list_vessel_certificates"](
            entity_id="",
            yacht_id=auth["yacht_id"],
            params={
                "offset": offset,
                "limit": limit,
                "status": status,
                "certificate_type": certificate_type,
            }
        )
        return result

    except Exception as e:
        logger.error(f"Failed to list vessel certificates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crew")
async def list_crew_certificates(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    person_name: Optional[str] = Query(default=None),
    certificate_type: Optional[str] = Query(default=None),
    auth: dict = Depends(get_authenticated_user)
):
    """
    List all crew certificates for the authenticated yacht.

    Returns paginated list grouped by person with expiry warnings.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_certificate_handlers(supabase)

        result = await handlers["list_crew_certificates"](
            entity_id="",
            yacht_id=auth["yacht_id"],
            params={
                "offset": offset,
                "limit": limit,
                "person_name": person_name,
                "certificate_type": certificate_type,
            }
        )
        return result

    except Exception as e:
        logger.error(f"Failed to list crew certificates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expiring")
async def find_expiring_certificates(
    days_ahead: int = Query(default=90, ge=1, le=365),
    domain: Literal["vessel", "crew", "all"] = Query(default="all"),
    auth: dict = Depends(get_authenticated_user)
):
    """
    Find certificates expiring within specified time range.

    Returns grouped by urgency: expired, expiring within 30 days, expiring within 90 days.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_certificate_handlers(supabase)

        result = await handlers["find_expiring_certificates"](
            entity_id="",
            yacht_id=auth["yacht_id"],
            params={
                "days_ahead": days_ahead,
                "domain": domain,
            }
        )
        return result

    except Exception as e:
        logger.error(f"Failed to find expiring certificates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{certificate_id}")
async def get_certificate_details(
    certificate_id: UUID,
    domain: Literal["vessel", "crew"] = Query(default="vessel"),
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get certificate details.

    Args:
        certificate_id: UUID of the certificate
        domain: "vessel" or "crew" to specify which table to query
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_certificate_handlers(supabase)

        result = await handlers["get_certificate_details"](
            entity_id=str(certificate_id),
            yacht_id=auth["yacht_id"],
            params={"domain": domain}
        )
        return result

    except Exception as e:
        logger.error(f"Failed to get certificate details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{certificate_id}/history")
async def view_certificate_history(
    certificate_id: UUID,
    domain: Literal["vessel", "crew"] = Query(default="vessel"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    auth: dict = Depends(get_authenticated_user)
):
    """
    View certificate audit history.

    Returns list of changes with who made them and when.
    Includes signature information for signed actions (supersede).
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_certificate_handlers(supabase)

        result = await handlers["view_certificate_history"](
            entity_id=str(certificate_id),
            yacht_id=auth["yacht_id"],
            params={
                "domain": domain,
                "offset": offset,
                "limit": limit,
            }
        )
        return result

    except Exception as e:
        logger.error(f"Failed to view certificate history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DEBUG ENDPOINT - Certificate Pipeline Testing
# =============================================================================

@router.post("/debug/pipeline-test", response_model=CertificatePipelineTestResponse)
async def debug_certificate_pipeline(
    request: CertificatePipelineTestRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    DEBUG ENDPOINT: Test certificate pipeline end-to-end.

    Takes a user query and returns:
    - Entities extracted (Module B)
    - Intent detected (Intent Parser)
    - Actions detected (Module A)
    - Handler result (if applicable)

    Only available when FEATURE_CERTIFICATES=true.

    Example queries to test:
    - "show ISM certificate expiry"
    - "list all crew certificates"
    - "what certificates expire next month"
    - "create STCW certificate for John Smith"
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Certificate feature not enabled")

    # Check for debug mode - only allow in development
    # SECURITY: This endpoint is explicitly disabled in production
    env = os.getenv("ENVIRONMENT", "production")
    if env == "production":
        logger.warning(f"[CertDebug] Blocked production access attempt: user={auth['user_id'][:8]}...")
        raise HTTPException(status_code=403, detail="Debug endpoint disabled in production")

    # Log debug endpoint access for audit trail
    logger.info(f"[CertDebug] Debug access: user={auth['user_id'][:8]}..., env={env}")

    query = request.query
    # SECURITY: yacht_id ONLY from auth context - invariant #1
    yacht_id = auth["yacht_id"]

    debug_info = {
        "feature_flag": "FEATURE_CERTIFICATES=true",
        "yacht_id": yacht_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # =============================================================================
    # Step 1: Entity Extraction (Module B)
    # =============================================================================
    entities_extracted = []
    try:
        from extraction import get_extractor
        extractor = get_extractor()
        entities = extractor.extract_entities(query)
        entities_extracted = [e.to_dict() for e in entities]
        debug_info["entity_extraction_success"] = True
        debug_info["entity_count"] = len(entities_extracted)
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        debug_info["entity_extraction_error"] = str(e)

    # =============================================================================
    # Step 2: Intent Detection (Intent Parser)
    # =============================================================================
    intent_detected = {}
    try:
        from services.intent_parser import IntentParser
        parser = IntentParser()
        parsed = parser.parse(query)
        intent_detected = parsed.to_dict()
        debug_info["intent_parsing_success"] = True
    except Exception as e:
        logger.error(f"Intent parsing failed: {e}")
        debug_info["intent_parsing_error"] = str(e)

    # =============================================================================
    # Step 3: Action Detection (Module A)
    # =============================================================================
    actions_detected = []
    try:
        from extraction import ActionDetector
        detector = ActionDetector()
        detected = detector.detect_actions(query)
        actions_detected = [
            {
                "action": a.action,
                "confidence": a.confidence,
                "verb_match": a.verb_match,
                "execution_class": a.execution_class,
            }
            for a in detected
        ]
        debug_info["action_detection_success"] = True
        debug_info["action_count"] = len(actions_detected)
    except Exception as e:
        logger.error(f"Action detection failed: {e}")
        debug_info["action_detection_error"] = str(e)

    # =============================================================================
    # Step 4: Handler Execution (if READ action detected)
    # =============================================================================
    handler_result = None
    if actions_detected:
        primary_action = actions_detected[0]["action"]

        # Only execute READ handlers automatically
        read_handlers = {
            "list_vessel_certificates",
            "list_crew_certificates",
            "get_certificate_details",
            "view_certificate_history",
            "find_expiring_certificates",
        }

        if primary_action in read_handlers:
            try:
                supabase = get_tenant_client(auth['tenant_key_alias'])
                handlers = get_certificate_handlers(supabase)

                if primary_action in handlers:
                    # Build params from entities
                    params = {}
                    for entity in entities_extracted:
                        if entity["type"] == "certificate":
                            params["certificate_type"] = entity["canonical"]

                    handler_result = await handlers[primary_action](
                        entity_id="",
                        yacht_id=yacht_id,
                        params=params
                    )
                    debug_info["handler_executed"] = primary_action
                    debug_info["handler_success"] = True
            except Exception as e:
                logger.error(f"Handler execution failed: {e}")
                debug_info["handler_error"] = str(e)
        else:
            debug_info["handler_skipped"] = f"Action {primary_action} is not a READ handler - skipped auto-execution"

    return CertificatePipelineTestResponse(
        query=query,
        entities_extracted=entities_extracted,
        intent_detected=intent_detected,
        actions_detected=actions_detected,
        handler_result=handler_result,
        debug_info=debug_info,
    )


# =============================================================================
# FEATURE STATUS ENDPOINT
# =============================================================================

@router.get("/debug/status")
async def get_certificate_feature_status():
    """
    Check certificate feature status.

    Returns feature flag values and configuration.
    Does not require authentication for easier debugging.
    """
    return {
        "feature_enabled": check_feature_flag(),
        "flags": {
            "FEATURE_CERTIFICATES": os.getenv("FEATURE_CERTIFICATES", "false"),
            "UI_CERTIFICATES": os.getenv("UI_CERTIFICATES", "false"),
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "available_endpoints": [
            "GET /api/v1/certificates/vessel",
            "GET /api/v1/certificates/crew",
            "GET /api/v1/certificates/expiring",
            "GET /api/v1/certificates/{certificate_id}",
            "GET /api/v1/certificates/{certificate_id}/history",
            "POST /api/v1/certificates/debug/pipeline-test",
        ],
    }
