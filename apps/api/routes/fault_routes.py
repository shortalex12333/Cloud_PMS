"""
Fault Routes
============

API endpoints for fault management (Fault Lens v1).

Includes:
- CRUD operations for faults
- Show Related endpoint using pms_entity_links
- Add Related endpoint for HOD+ to link entities
- Fault history and diagnostics

Feature flags:
- FEATURE_FAULTS: Backend operations
- UI_FAULTS: Frontend display
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Literal, Dict, Any
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

# Fault handlers
try:
    from handlers.fault_handlers import get_fault_handlers
    from handlers.fault_mutation_handlers import get_fault_mutation_handlers
    FAULT_HANDLERS_AVAILABLE = True
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).warning(f"Fault handlers not available: {e}")
    get_fault_handlers = None
    get_fault_mutation_handlers = None
    FAULT_HANDLERS_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class FaultListParams(BaseModel):
    """Query parameters for listing faults."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)
    status: Optional[str] = None
    severity: Optional[str] = None
    equipment_id: Optional[str] = None


class ShowRelatedRequest(BaseModel):
    """Request for Show Related endpoint."""
    entity_type: str = Field(..., description="Source entity type (e.g., 'fault')")
    entity_id: UUID = Field(..., description="Source entity ID")
    link_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by link types (e.g., ['related', 'caused_by'])"
    )
    limit: int = Field(default=20, ge=1, le=50)


class ShowRelatedResponse(BaseModel):
    """Response for Show Related endpoint."""
    source_entity_type: str
    source_entity_id: str
    related: List[Dict[str, Any]]
    total: int


class AddRelatedRequest(BaseModel):
    """Request to add a related entity link."""
    source_entity_type: str = Field(..., description="Source entity type")
    source_entity_id: UUID = Field(..., description="Source entity ID")
    target_entity_type: str = Field(..., description="Target entity type")
    target_entity_id: UUID = Field(..., description="Target entity ID")
    link_type: str = Field(default="related", description="Type of relationship")
    note: Optional[str] = Field(default=None, description="Optional note about the relationship")


class AddRelatedResponse(BaseModel):
    """Response for Add Related endpoint."""
    link_id: str
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    link_type: str
    created_at: str


class ReportFaultRequest(BaseModel):
    """Request to report a fault."""
    equipment_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    severity: str = Field(default="minor", description="Severity: cosmetic|minor|major|critical|safety")


class UpdateFaultRequest(BaseModel):
    """Request to update a fault."""
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


# =============================================================================
# SUPABASE CLIENT
# =============================================================================
# NOTE: get_supabase_client and get_tenant_client are imported from integrations.supabase


def check_feature_flag() -> bool:
    """Check if fault feature is enabled."""
    return os.getenv("FEATURE_FAULTS", "true").lower() == "true"


def check_handlers_available():
    """Verify fault handlers are available. Raises 503 if not."""
    if not FAULT_HANDLERS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Fault handlers not available - service degraded"
        )


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/")
async def list_faults(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    equipment_id: Optional[UUID] = Query(default=None),
    auth: dict = Depends(get_authenticated_user)
):
    """
    List all faults for the authenticated yacht.

    Returns paginated list with severity indicators.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])

        # Build query
        query = supabase.table("pms_faults").select(
            "id, fault_code, title, description, severity, status, equipment_id, detected_at, resolved_at, created_at",
            count="exact"
        ).eq("yacht_id", auth["yacht_id"])

        if status:
            query = query.eq("status", status)
        if severity:
            query = query.eq("severity", severity)
        if equipment_id:
            query = query.eq("equipment_id", str(equipment_id))

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        faults = result.data or []
        total_count = result.count or len(faults)

        # Add computed fields
        for fault in faults:
            fault["is_active"] = fault.get("resolved_at") is None

        return {
            "status": "success",
            "data": {
                "faults": faults,
                "total": total_count,
            },
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
            },
        }

    except Exception as e:
        logger.error(f"Failed to list faults: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fault_id}")
async def get_fault_details(
    fault_id: UUID,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get fault details.

    Returns fault with equipment info and available actions.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_handlers(supabase)

        result = await handlers["view_fault"](
            entity_id=str(fault_id),
            yacht_id=auth["yacht_id"],
        )
        return result

    except Exception as e:
        logger.error(f"Failed to get fault details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fault_id}/history")
async def get_fault_history(
    fault_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get fault history (for recurrence analysis).

    Returns past faults for the same equipment.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_handlers(supabase)

        result = await handlers["view_fault_history"](
            entity_id=str(fault_id),
            yacht_id=auth["yacht_id"],
            params={
                "offset": offset,
                "limit": limit,
            }
        )
        return result

    except Exception as e:
        logger.error(f"Failed to get fault history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SHOW RELATED ENDPOINT (Fault Lens v1)
# =============================================================================

@router.post("/related", response_model=ShowRelatedResponse)
async def show_related(
    request: ShowRelatedRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get related entities for a fault (or other entity).

    Uses pms_entity_links table for curated links.
    Returns both outgoing (source→target) and incoming (target←source) links.

    Role: All crew can view (yacht-scoped).

    Returns:
    - List of related entities with their types and link metadata
    - Total count
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        yacht_id = auth["yacht_id"]
        entity_type = request.entity_type
        entity_id = str(request.entity_id)

        related = []

        # Query outgoing links (source → target)
        outgoing_query = supabase.table("pms_entity_links").select(
            "id, target_entity_type, target_entity_id, link_type, note, created_at, created_by"
        ).eq("yacht_id", yacht_id).eq(
            "source_entity_type", entity_type
        ).eq("source_entity_id", entity_id)

        if request.link_types:
            outgoing_query = outgoing_query.in_("link_type", request.link_types)

        outgoing_result = outgoing_query.order("created_at", desc=True).limit(request.limit).execute()

        for link in (outgoing_result.data or []):
            related.append({
                "link_id": link["id"],
                "direction": "outgoing",
                "entity_type": link["target_entity_type"],
                "entity_id": link["target_entity_id"],
                "link_type": link["link_type"],
                "note": link.get("note"),
                "created_at": link["created_at"],
            })

        # Query incoming links (source → this entity as target)
        incoming_query = supabase.table("pms_entity_links").select(
            "id, source_entity_type, source_entity_id, link_type, note, created_at, created_by"
        ).eq("yacht_id", yacht_id).eq(
            "target_entity_type", entity_type
        ).eq("target_entity_id", entity_id)

        if request.link_types:
            incoming_query = incoming_query.in_("link_type", request.link_types)

        incoming_result = incoming_query.order("created_at", desc=True).limit(request.limit).execute()

        for link in (incoming_result.data or []):
            related.append({
                "link_id": link["id"],
                "direction": "incoming",
                "entity_type": link["source_entity_type"],
                "entity_id": link["source_entity_id"],
                "link_type": link["link_type"],
                "note": link.get("note"),
                "created_at": link["created_at"],
            })

        # Enrich with entity details (equipment, work_order, etc.)
        related = await _enrich_related_entities(supabase, yacht_id, related)

        return ShowRelatedResponse(
            source_entity_type=entity_type,
            source_entity_id=entity_id,
            related=related,
            total=len(related),
        )

    except Exception as e:
        logger.error(f"Failed to get related entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _enrich_related_entities(
    supabase: Client,
    yacht_id: str,
    related: List[Dict],
) -> List[Dict]:
    """
    Enrich related entities with basic details (name, title, etc.).

    Fetches minimal info from respective tables for display.
    """
    enriched = []

    for item in related:
        entity_type = item["entity_type"]
        entity_id = item["entity_id"]

        item["entity_details"] = {}

        try:
            if entity_type == "equipment":
                result = supabase.table("pms_equipment").select(
                    "name, equipment_type, location"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if result.data:
                    item["entity_details"] = result.data

            elif entity_type == "fault":
                result = supabase.table("pms_faults").select(
                    "fault_code, title, severity, status"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if result.data:
                    item["entity_details"] = result.data

            elif entity_type == "work_order":
                result = supabase.table("pms_work_orders").select(
                    "work_order_number, title, status, priority"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if result.data:
                    item["entity_details"] = result.data

            elif entity_type == "part":
                result = supabase.table("pms_parts").select(
                    "name, part_number, category"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if result.data:
                    item["entity_details"] = result.data

            elif entity_type == "warranty_claim":
                result = supabase.table("pms_warranty_claims").select(
                    "claim_number, title, status"
                ).eq("id", entity_id).eq("yacht_id", yacht_id).maybe_single().execute()
                if result.data:
                    item["entity_details"] = result.data

        except Exception as e:
            logger.warning(f"Failed to enrich {entity_type}/{entity_id}: {e}")

        enriched.append(item)

    return enriched


# =============================================================================
# ADD RELATED ENDPOINT (HOD+ only)
# =============================================================================

@router.post("/related/add", response_model=AddRelatedResponse)
async def add_related(
    request: AddRelatedRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Add a related entity link (HOD + captain only).

    Creates a curated link between two entities.
    RLS enforces role gating.

    Link types:
    - 'related': Generic relationship
    - 'caused_by': Fault caused by another issue
    - 'resolved_by': Fault resolved by work order
    - 'supersedes': Entity supersedes another
    - 'warranty_for': Warranty claim linked to fault/equipment
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        yacht_id = auth["yacht_id"]
        user_id = auth["user_id"]

        # Create link
        link_data = {
            "yacht_id": yacht_id,
            "source_entity_type": request.source_entity_type,
            "source_entity_id": str(request.source_entity_id),
            "target_entity_type": request.target_entity_type,
            "target_entity_id": str(request.target_entity_id),
            "link_type": request.link_type,
            "note": request.note,
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = supabase.table("pms_entity_links").insert(link_data).execute()

        if not result.data:
            raise HTTPException(status_code=403, detail="Not authorized to create links (HOD+ required)")

        link = result.data[0]

        return AddRelatedResponse(
            link_id=link["id"],
            source_entity_type=link["source_entity_type"],
            source_entity_id=link["source_entity_id"],
            target_entity_type=link["target_entity_type"],
            target_entity_id=link["target_entity_id"],
            link_type=link["link_type"],
            created_at=link["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add related link: {e}", exc_info=True)
        # Check if it's an RLS denial
        if "policy" in str(e).lower() or "permission" in str(e).lower():
            raise HTTPException(status_code=403, detail="Not authorized to create links (HOD+ required)")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MUTATION ENDPOINTS
# =============================================================================

@router.post("/")
async def report_fault(
    request: ReportFaultRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Report a new fault (all crew can report).

    Severity mapping:
    - low → cosmetic
    - medium → minor
    - high → major
    - cosmetic, minor, major, critical, safety → unchanged

    Auto-adds to handover if severity is critical/safety.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["report_fault"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            title=request.title,
            severity=request.severity,
            description=request.description,
            equipment_id=str(request.equipment_id) if request.equipment_id else None,
        )

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to report fault: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fault_id}/acknowledge")
async def acknowledge_fault(
    fault_id: UUID,
    notes: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Acknowledge a fault (HOD/captain only).

    Transitions fault from 'open' to 'investigating'.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["acknowledge_fault"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            fault_id=str(fault_id),
            notes=notes,
        )

        if result.get("status") == "error":
            status_code = 400
            if result.get("error_code") == "NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge fault: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fault_id}/close")
async def close_fault(
    fault_id: UUID,
    resolution_notes: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Close a fault (HOD/captain only).
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["close_fault"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            fault_id=str(fault_id),
            resolution_notes=resolution_notes,
        )

        if result.get("status") == "error":
            status_code = 400
            if result.get("error_code") == "NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close fault: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{fault_id}")
async def update_fault(
    fault_id: UUID,
    request: UpdateFaultRequest,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Update fault details (HOD/captain only).
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["update_fault"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            fault_id=str(fault_id),
            severity=request.severity,
            status=request.status,
            title=request.title,
            description=request.description,
        )

        if result.get("status") == "error":
            status_code = 400
            if result.get("error_code") == "NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update fault: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fault_id}/reopen")
async def reopen_fault(
    fault_id: UUID,
    reason: str,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Reopen a closed/resolved fault (HOD/captain only).
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["reopen_fault"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            fault_id=str(fault_id),
            reason=reason,
        )

        if result.get("status") == "error":
            status_code = 400
            if result.get("error_code") == "NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reopen fault: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{fault_id}/false-alarm")
async def mark_false_alarm(
    fault_id: UUID,
    reason: Optional[str] = None,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Mark fault as false alarm (HOD/captain only).

    Terminal state - cannot be reopened.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Fault feature not enabled")

    check_handlers_available()

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])
        handlers = get_fault_mutation_handlers(supabase)

        result = await handlers["mark_fault_false_alarm"](
            yacht_id=auth["yacht_id"],
            user_id=auth["user_id"],
            fault_id=str(fault_id),
            reason=reason,
        )

        if result.get("status") == "error":
            status_code = 400
            if result.get("error_code") == "NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark fault as false alarm: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FEATURE STATUS ENDPOINT
# =============================================================================

@router.get("/debug/status")
async def get_fault_feature_status():
    """
    Check fault feature status.

    Returns feature flag values and configuration.
    Does not require authentication for easier debugging.
    """
    return {
        "feature_enabled": check_feature_flag(),
        "handlers_available": FAULT_HANDLERS_AVAILABLE,
        "flags": {
            "FEATURE_FAULTS": os.getenv("FEATURE_FAULTS", "true"),
            "UI_FAULTS": os.getenv("UI_FAULTS", "false"),
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "available_endpoints": [
            "GET /api/v1/faults/",
            "GET /api/v1/faults/{fault_id}",
            "GET /api/v1/faults/{fault_id}/history",
            "POST /api/v1/faults/",
            "PUT /api/v1/faults/{fault_id}",
            "POST /api/v1/faults/{fault_id}/acknowledge",
            "POST /api/v1/faults/{fault_id}/close",
            "POST /api/v1/faults/{fault_id}/reopen",
            "POST /api/v1/faults/{fault_id}/false-alarm",
            "POST /api/v1/faults/related",
            "POST /api/v1/faults/related/add",
        ],
    }
