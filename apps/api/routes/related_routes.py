"""
Related Entity Routes
=====================

Generic API endpoints for Show Related feature (Work Order Lens P1).

Endpoints:
- GET  /v1/related - View related entities for any entity type
- POST /v1/related/add - Add explicit entity link (HOD/manager only)

Supports multiple entity types:
- work_order (P1)
- fault (from Fault Lens v1)
- equipment
- part
- manual
- handover
- attachment

All routes require JWT authentication and yacht isolation.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import os
from supabase import create_client, Client

# Auth middleware
from middleware.auth import get_authenticated_user

# Related handlers
try:
    from handlers.related_handlers import RelatedHandlers
    RELATED_HANDLERS_AVAILABLE = True
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Related handlers not available: {e}")
    RelatedHandlers = None
    RELATED_HANDLERS_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/related", tags=["related-entities"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AddEntityLinkRequest(BaseModel):
    """Request to add an explicit entity link."""
    yacht_id: Optional[UUID] = Field(default=None, description="Yacht UUID (optional, uses auth yacht_id if not provided)")
    source_entity_type: str = Field(..., description="Source entity type (e.g., 'work_order')")
    source_entity_id: UUID = Field(..., description="Source entity UUID")
    target_entity_type: str = Field(..., description="Target entity type")
    target_entity_id: UUID = Field(..., description="Target entity UUID")
    link_type: str = Field(default="explicit", description="Link type")
    note: Optional[str] = Field(default=None, description="Optional note")


class AddEntityLinkResponse(BaseModel):
    """Response for add entity link."""
    status: str
    link_id: str
    created_at: str


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def get_supabase_client() -> Client:
    """Get TENANT Supabase client.

    Uses DEFAULT_YACHT_CODE env var to route to correct tenant DB.
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise HTTPException(status_code=500, detail=f"TENANT Supabase config missing for {default_yacht}")

    return create_client(url, key)


def check_handlers_available():
    """Verify related handlers are available. Raises 503 if not."""
    if not RELATED_HANDLERS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Related handlers not available - service degraded"
        )


# =============================================================================
# READ ENDPOINT: View Related Entities
# =============================================================================

@router.get("/")
async def view_related_entities(
    entity_type: str = Query(..., description="Entity type (e.g., 'work_order', 'fault', 'equipment')"),
    entity_id: UUID = Query(..., description="Entity UUID"),
    limit: int = Query(default=10, ge=1, description="Max results per group (1-50)"),
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get related entities for any entity (Work Order Lens P1).

    Returns groups of related entities with match reasons:
    - parts: FK-linked parts
    - manuals: Equipment manuals
    - previous_work: Previous work orders on same equipment
    - handovers: Equipment handovers
    - attachments: Directly attached documents
    - explicit_links: User-added links from pms_entity_links

    Role: All crew can view (yacht-scoped).

    Match Reasons:
    - FK:wo_part: Foreign key via pms_work_order_parts
    - FK:equipment: Via equipment_id
    - same_equipment: Other work orders on same equipment
    - explicit_link: Manually added by HOD/manager

    Response:
    {
      "status": "success",
      "groups": [
        {
          "group_key": "parts",
          "label": "Parts",
          "count": 2,
          "items": [
            {
              "entity_id": "...",
              "entity_type": "part",
              "title": "Part name",
              "subtitle": "Part #: ABC123",
              "match_reasons": ["FK:wo_part"],
              "weight": 100,
              "open_action": "focus"
            }
          ]
        }
      ],
      "add_related_enabled": true
    }
    """
    check_handlers_available()

    # Manual limit validation for 400 response (not 422)
    if limit > 50:
        raise HTTPException(status_code=400, detail="limit cannot exceed 50")

    try:
        supabase = get_supabase_client()
        handlers = RelatedHandlers(supabase)

        yacht_id = auth["yacht_id"]
        user_id = auth["user_id"]

        result = await handlers.get_related(
            yacht_id=yacht_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            limit=limit
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get related entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MUTATE ENDPOINT: Add Entity Link (HOD/Manager Only)
# =============================================================================

@router.post("/add", response_model=AddEntityLinkResponse)
async def add_entity_link(
    request: AddEntityLinkRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Add an explicit entity link (HOD/manager only).

    Creates a curated link in pms_entity_links table.
    RLS enforces role gating (HOD + captain + manager).

    Valid entity types:
    - work_order
    - fault
    - equipment
    - part
    - manual
    - handover
    - attachment

    Link types:
    - explicit: Generic user-created link (default)
    - related: General relationship
    - caused_by: Source caused by target
    - resolved_by: Source resolved by target
    - supersedes: Source supersedes target
    - warranty_for: Warranty claim for target

    Returns:
    {
      "status": "success",
      "link_id": "...",
      "created_at": "2026-01-28T12:00:00Z"
    }

    Error Responses:
    - 400: Invalid entity type or missing entity
    - 403: Not authorized (crew cannot create links)
    - 404: Source or target entity not found
    - 409: Link already exists
    """
    check_handlers_available()

    try:
        supabase = get_supabase_client()
        handlers = RelatedHandlers(supabase)

        # Validate yacht_id matches auth (if provided)
        if request.yacht_id and str(request.yacht_id) != auth["yacht_id"]:
            raise HTTPException(status_code=403, detail="Yacht ID mismatch")

        result = await handlers.add_related(
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            source_entity_type=request.source_entity_type,
            source_entity_id=str(request.source_entity_id),
            target_entity_type=request.target_entity_type,
            target_entity_id=str(request.target_entity_id),
            link_type=request.link_type,
            note=request.note
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add entity link: {e}", exc_info=True)
        # Check if it's an RLS denial
        if "policy" in str(e).lower() or "permission" in str(e).lower() or "rls" in str(e).lower():
            raise HTTPException(status_code=403, detail="Not authorized to create links (HOD/manager required)")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FEATURE STATUS ENDPOINT
# =============================================================================

@router.get("/debug/status")
async def get_related_feature_status():
    """
    Check Show Related feature status.

    Returns handlers availability and configuration.
    Does not require authentication for easier debugging.
    """
    return {
        "handlers_available": RELATED_HANDLERS_AVAILABLE,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "available_endpoints": [
            "GET /v1/related?entity_type=&entity_id=",
            "POST /v1/related/add",
        ],
        "supported_entity_types": [
            "work_order",
            "fault",
            "equipment",
            "part",
            "manual",
            "handover",
            "attachment",
        ],
    }
