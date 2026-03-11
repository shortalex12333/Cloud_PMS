"""
Equipment Routes
================

API endpoints for equipment management (Equipment Lens v1).

Includes:
- GET / - List equipment with pagination
- GET /{equipment_id} - Get single equipment details

All endpoints enforce yacht_id isolation via JWT authentication.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from uuid import UUID
import logging
import os

# Auth middleware
from middleware.auth import get_authenticated_user

# Centralized Supabase client factory
from integrations.supabase import get_tenant_client

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# FEATURE FLAG
# =============================================================================

def check_feature_flag() -> bool:
    """Check if equipment feature is enabled."""
    return os.getenv("FEATURE_EQUIPMENT", "true").lower() == "true"


# =============================================================================
# READ ENDPOINTS
# =============================================================================

@router.get("/")
async def list_equipment(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search by name"),
    auth: dict = Depends(get_authenticated_user)
):
    """
    List all equipment for the authenticated yacht.

    Returns paginated list with equipment details.

    Response format:
    {
        "equipment": [...],
        "data": [...],  // alias for frontend compatibility
        "total": N,
        "pagination": { "offset": 0, "limit": 50, "total": N }
    }
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Equipment feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])

        # Build query with count
        query = supabase.table("pms_equipment").select(
            "id, name, description, system_type, location, manufacturer, model, serial_number, criticality, installed_date, attention_flag, attention_reason, metadata, created_at, updated_at",
            count="exact"
        ).eq("yacht_id", auth["yacht_id"])

        # Apply filters
        if status:
            # Status might be in metadata for some setups
            query = query.eq("metadata->>status", status)
        if category:
            query = query.eq("system_type", category)
        if location:
            query = query.ilike("location", f"%{location}%")
        if search:
            query = query.ilike("name", f"%{search}%")

        result = query.order("name").range(offset, offset + limit - 1).execute()

        equipment_list = result.data or []
        total_count = result.count or len(equipment_list)

        # Transform to match frontend Equipment interface
        transformed = []
        for eq in equipment_list:
            metadata = eq.get("metadata") or {}
            transformed.append({
                "id": eq.get("id"),
                "equipment_number": eq.get("id", "")[:8],  # Short ID as equipment number
                "name": eq.get("name", "Unknown Equipment"),
                "description": eq.get("description"),
                "category": eq.get("system_type") or metadata.get("category"),
                "location": eq.get("location"),
                "manufacturer": eq.get("manufacturer"),
                "model": eq.get("model"),
                "serial_number": eq.get("serial_number"),
                "status": metadata.get("status", "operational"),
                "criticality": eq.get("criticality"),
                "last_service_date": metadata.get("last_maintenance"),
                "next_service_date": metadata.get("next_maintenance"),
                "attention_flag": eq.get("attention_flag"),
                "attention_reason": eq.get("attention_reason"),
                "created_at": eq.get("created_at"),
                "updated_at": eq.get("updated_at"),
            })

        return {
            "status": "success",
            "equipment": transformed,
            "data": transformed,  # Alias for frontend compatibility
            "total": total_count,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
            },
        }

    except Exception as e:
        logger.error(f"Failed to list equipment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{equipment_id}")
async def get_equipment_details(
    equipment_id: UUID,
    auth: dict = Depends(get_authenticated_user)
):
    """
    Get equipment details by ID.

    Returns single equipment with full details.
    Enforces yacht_id isolation.
    """
    if not check_feature_flag():
        raise HTTPException(status_code=404, detail="Equipment feature not enabled")

    try:
        supabase = get_tenant_client(auth['tenant_key_alias'])

        result = supabase.table("pms_equipment").select(
            "*"
        ).eq("id", str(equipment_id)).eq("yacht_id", auth["yacht_id"]).maybe_single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Equipment not found")

        eq = result.data
        metadata = eq.get("metadata") or {}

        return {
            "id": eq.get("id"),
            "equipment_number": eq.get("id", "")[:8],
            "name": eq.get("name", "Unknown Equipment"),
            "description": eq.get("description"),
            "category": eq.get("system_type") or metadata.get("category"),
            "location": eq.get("location"),
            "manufacturer": eq.get("manufacturer"),
            "model": eq.get("model"),
            "serial_number": eq.get("serial_number"),
            "status": metadata.get("status", "operational"),
            "criticality": eq.get("criticality"),
            "installed_date": eq.get("installed_date"),
            "last_service_date": metadata.get("last_maintenance"),
            "next_service_date": metadata.get("next_maintenance"),
            "attention_flag": eq.get("attention_flag"),
            "attention_reason": eq.get("attention_reason"),
            "created_at": eq.get("created_at"),
            "updated_at": eq.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get equipment details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FEATURE STATUS ENDPOINT
# =============================================================================

@router.get("/debug/status")
async def get_equipment_feature_status():
    """
    Check equipment feature status.

    Returns feature flag values and configuration.
    Does not require authentication for easier debugging.
    """
    return {
        "feature_enabled": check_feature_flag(),
        "flags": {
            "FEATURE_EQUIPMENT": os.getenv("FEATURE_EQUIPMENT", "true"),
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "available_endpoints": [
            "GET /v1/equipment/",
            "GET /v1/equipment/{equipment_id}",
            "GET /v1/equipment/debug/status",
        ],
    }
