"""
Inventory Routes
================

FastAPI routes for Inventory Lens.

Endpoints:
- GET  /v1/inventory - List parts/inventory with pagination

All routes require JWT authentication and yacht isolation validation.
"""

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_router.validators import validate_jwt, validate_yacht_isolation
from middleware.auth import lookup_tenant_for_user

logger = logging.getLogger(__name__)


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_tenant_supabase_client(tenant_key_alias: str) -> Client:
    """Get tenant-specific Supabase client instance."""
    if not tenant_key_alias:
        raise ValueError("tenant_key_alias is required for tenant DB access")

    url = os.getenv(f"{tenant_key_alias}_SUPABASE_URL")
    key = os.getenv(f"{tenant_key_alias}_SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(f"Missing tenant credentials for {tenant_key_alias}")

    return create_client(url, key)


def get_default_supabase_client() -> Optional[Client]:
    """Get default tenant Supabase client."""
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class InventoryItem(BaseModel):
    """Inventory item (part) in the list response."""
    id: str
    part_number: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    quantity_on_hand: int = 0
    minimum_quantity: Optional[int] = None
    unit_of_measure: Optional[str] = None
    location: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class InventoryListResponse(BaseModel):
    """Response for inventory list endpoint."""
    data: List[InventoryItem]
    total: int


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/", response_model=InventoryListResponse)
async def list_inventory(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    authorization: str = Header(..., description="Bearer token"),
) -> InventoryListResponse:
    """
    List inventory items (parts) with pagination.

    Returns parts from pms_parts table with stock information.
    Enforces yacht isolation via JWT.

    Query params:
    - offset: Pagination offset (default 0)
    - limit: Number of items to return (default 50, max 200)

    Returns:
    - data: List of inventory items
    - total: Total count of items for pagination
    """
    # SECURITY: Validate JWT and get auth context
    jwt_result = validate_jwt(authorization)
    if not jwt_result.valid:
        raise HTTPException(
            status_code=401,
            detail=jwt_result.error.message if jwt_result.error else "Invalid token"
        )

    # SECURITY: yacht_id ONLY from auth context - invariant #1
    yacht_id = jwt_result.context.get("yacht_id")
    user_id = jwt_result.context.get("user_id")

    if not yacht_id:
        raise HTTPException(status_code=403, detail="No yacht context in token")

    # Get tenant-specific client if available
    db = None
    if user_id:
        tenant_info = lookup_tenant_for_user(user_id)
        if tenant_info and tenant_info.get("tenant_key_alias"):
            try:
                db = get_tenant_supabase_client(tenant_info["tenant_key_alias"])
            except Exception as e:
                logger.warning(f"Failed to get tenant client, falling back to default: {e}")

    if not db:
        db = get_default_supabase_client()

    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Get total count for pagination
        count_result = db.table("pms_parts").select(
            "id", count="exact"
        ).eq("yacht_id", yacht_id).execute()

        total = count_result.count if count_result.count is not None else 0

        # Get paginated parts
        result = db.table("pms_parts").select(
            "id, part_number, name, description, category, manufacturer, "
            "quantity_on_hand, minimum_quantity, min_level, unit, location, "
            "unit_cost, created_at, updated_at"
        ).eq("yacht_id", yacht_id).order(
            "name", desc=False
        ).range(offset, offset + limit - 1).execute()

        parts = result.data or []

        # Transform to response format
        items = []
        for part in parts:
            # Map database fields to API response fields
            items.append(InventoryItem(
                id=part["id"],
                part_number=part.get("part_number"),
                name=part.get("name", "Unknown Part"),
                description=part.get("description"),
                category=part.get("category"),
                manufacturer=part.get("manufacturer"),
                quantity_on_hand=part.get("quantity_on_hand", 0) or 0,
                minimum_quantity=part.get("minimum_quantity") or part.get("min_level"),
                unit_of_measure=part.get("unit"),
                location=part.get("location"),
                price=part.get("unit_cost"),
                currency=None,  # Not stored in pms_parts
                created_at=part.get("created_at", ""),
                updated_at=part.get("updated_at"),
            ))

        return InventoryListResponse(
            data=items,
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_inventory failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve inventory data")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router"]
