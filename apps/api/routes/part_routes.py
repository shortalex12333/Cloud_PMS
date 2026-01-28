"""
Part Lens Routes
================

FastAPI routes for Part Lens v2 actions.

Endpoints:
- GET  /v1/parts/suggestions     - Get context-valid actions with prefill
- POST /v1/parts/shopping-list/prefill - Prefill for add_to_shopping_list
- POST /v1/parts/adjust-stock/prefill  - Prefill for adjust_stock_quantity
- GET  /v1/parts/low-stock       - View parts below min_level

Stock computation rule:
  suggested_qty = round_up(max(min_level - on_hand, 1), reorder_multiple)

All routes require JWT authentication and yacht isolation validation.
"""

from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging
import os
import math
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_router.registry import (
    get_actions_for_domain,
    get_action,
    get_field_metadata,
    FieldClassification,
)
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

router = APIRouter(prefix="/v1/parts", tags=["part-lens"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SuggestedAction(BaseModel):
    """A suggested action with prefill data."""
    action_id: str
    label: str
    variant: str
    prefill: Optional[Dict[str, Any]] = None
    field_metadata: Optional[List[Dict[str, Any]]] = None
    is_primary: bool = False


class PartSuggestionsResponse(BaseModel):
    """Response for part suggestions endpoint."""
    part_id: str
    part_name: Optional[str] = None
    part_number: Optional[str] = None
    stock: Dict[str, Any]
    suggested_actions: List[SuggestedAction]
    warnings: List[str] = []


class LowStockItem(BaseModel):
    """A part below minimum stock level."""
    id: str
    name: str
    part_number: Optional[str] = None
    is_critical: bool = False
    on_hand: int
    min_level: int
    shortage: int
    suggested_order_qty: int
    reorder_multiple: int = 1
    department: Optional[str] = None


class LowStockResponse(BaseModel):
    """Response for low stock endpoint."""
    parts: List[LowStockItem]
    total_low_stock: int
    critical_count: int
    total_suggested_order_value: Optional[float] = None


class PrefillResponse(BaseModel):
    """Response for prefill endpoints."""
    status: str
    prefill: Dict[str, Any]
    field_metadata: Dict[str, Any]


# ============================================================================
# STOCK COMPUTATION HELPERS
# ============================================================================

def round_up_to_multiple(value: int, multiple: int) -> int:
    """Round up to the nearest multiple.

    Example: round_up_to_multiple(7, 5) = 10
    """
    if multiple <= 0:
        return value
    return math.ceil(value / multiple) * multiple


def compute_suggested_order_qty(on_hand: int, min_level: int, reorder_multiple: int = 1) -> int:
    """
    Compute suggested order quantity.

    Formula: round_up(max(min_level - on_hand, 1), reorder_multiple)

    Args:
        on_hand: Current stock level
        min_level: Minimum required stock level
        reorder_multiple: Order in multiples of this value (default: 1)

    Returns:
        Suggested order quantity (always >= 1 if min_level > 0)
    """
    if min_level <= 0:
        return 0

    shortage = max(min_level - on_hand, 0)
    if shortage == 0:
        return 0

    # Ensure at least 1 if there's any shortage
    raw_qty = max(shortage, 1)

    # Round up to reorder multiple
    return round_up_to_multiple(raw_qty, reorder_multiple or 1)


def compute_urgency(on_hand: int, min_level: int) -> str:
    """Compute urgency level based on stock status."""
    if on_hand == 0:
        return "critical"
    elif min_level > 0 and on_hand <= min_level * 0.5:
        return "high"
    elif min_level > 0 and on_hand <= min_level:
        return "medium"
    return "low"


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/suggestions")
async def get_part_suggestions(
    part_id: str = Query(..., description="Part UUID"),
    yacht_id: str = Query(..., description="Yacht UUID"),
    user_id: str = Query(None, description="User UUID for suppression check"),
    role: str = Query(None, description="User role for action filtering"),
    authorization: str = Header(None),
) -> PartSuggestionsResponse:
    """
    Get context-valid actions for a part with prefill data.

    Returns suggested actions based on:
    - Part stock status (low stock → add_to_shopping_list primary)
    - User role (filters allowed actions)
    - Department suppression via is_part_alert_suppressed()
    - Current context (no "Related Evidence" yet per spec)

    Notification cadence for low stock:
    - 12h: Notify actor who consumed
    - 24h: Escalate to Chief
    - 7d: Secondary escalation
    - Options: "update minimum", "never notify again" (department-scope)

    Stock computation:
      suggested_qty = round_up(max(min_level - on_hand, 1), reorder_multiple)
    """
    # Validate JWT (optional for now, depends on deployment)
    # TODO: Enable JWT validation in production
    # jwt_payload = validate_jwt(authorization)

    db = get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    # Get part with stock levels
    try:
        result = db.table("pms_parts").select(
            "id, name, part_number, is_critical, category, "
            "min_level, reorder_multiple, primary_location_id"
        ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")

        part = result.data

        # Get stock level from canonical pms_part_stock view
        stock_result = db.table("pms_part_stock").select(
            "on_hand, location"
        ).eq("yacht_id", yacht_id).eq("part_id", part_id).maybe_single().execute()

        stock = stock_result.data or {}
        on_hand = stock.get("on_hand", 0) or 0
        min_level = part.get("min_level", 0) or 0
        reorder_multiple = part.get("reorder_multiple", 1) or 1

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get part data: {e}")
        # Return 404 for invalid part_id or data retrieval errors
        raise HTTPException(status_code=404, detail=f"Part not found or invalid: {part_id}")

    # Compute stock status
    is_low_stock = min_level > 0 and on_hand <= min_level
    is_out_of_stock = on_hand == 0
    suggested_order_qty = compute_suggested_order_qty(on_hand, min_level, reorder_multiple)
    urgency = compute_urgency(on_hand, min_level)

    # Check suppression for low stock alerts
    alert_suppressed = False
    if user_id and (is_low_stock or is_out_of_stock):
        alert_type = "out_of_stock" if is_out_of_stock else "low_stock"
        try:
            # Call is_part_alert_suppressed() function
            suppression_result = db.rpc("is_part_alert_suppressed", {
                "p_yacht_id": yacht_id,
                "p_user_id": user_id,
                "p_part_id": part_id,
                "p_department": part.get("category"),  # category maps to department for suppression
                "p_category": part.get("category"),
                "p_alert_type": alert_type,
            }).execute()
            alert_suppressed = suppression_result.data is True
        except Exception as e:
            logger.warning(f"Suppression check failed: {e}")
            # Continue without suppression if function fails

    # Build stock info
    stock_info = {
        "on_hand": on_hand,
        "min_level": min_level,
        "reorder_multiple": reorder_multiple,
        "is_low_stock": is_low_stock,
        "is_out_of_stock": is_out_of_stock,
        "suggested_order_qty": suggested_order_qty,
        "location": stock.get("location") or part.get("primary_location_id"),
        "alert_suppressed": alert_suppressed,
        "urgency": urgency,
    }

    # Get available actions for domain=parts, filtered by role
    available_actions = get_actions_for_domain("parts", role)

    # Build suggested actions with prefill
    suggested_actions = []
    warnings = []

    for action in available_actions:
        action_id = action["action_id"]
        is_primary = False
        prefill = {}

        # Determine if this action should be primary based on context
        if action_id == "add_to_shopping_list" and is_low_stock:
            # Only make primary if alert is NOT suppressed
            is_primary = not alert_suppressed
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "quantity_requested": suggested_order_qty,
                "urgency": urgency,
            }
        elif action_id == "consume_part":
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "available_qty": on_hand,
                "location": stock_info["location"],
            }
            if is_out_of_stock:
                # Don't suggest consume if out of stock
                continue
        elif action_id == "adjust_stock_quantity":
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "current_quantity": on_hand,
                "location": stock_info["location"],
            }
        elif action_id == "receive_part":
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "location": stock_info["location"],
            }
        elif action_id == "transfer_part":
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "from_location_id": stock_info["location_id"],
            }
            if is_out_of_stock:
                # Don't suggest transfer if out of stock
                continue
        elif action_id == "write_off_part":
            prefill = {
                "part_id": part_id,
                "part_name": part.get("name"),
                "available_qty": on_hand,
                "location": stock_info["location"],
            }
            if is_out_of_stock:
                continue
        elif action_id == "view_part_details":
            prefill = {"part_id": part_id}
        elif action_id == "view_low_stock":
            prefill = {}  # No part-specific prefill
        elif action_id in ("generate_part_labels", "request_label_output"):
            prefill = {"part_ids": [part_id]}

        # Get field metadata for the action
        try:
            field_meta = get_field_metadata(action_id)
        except Exception:
            field_meta = []

        suggested_actions.append(SuggestedAction(
            action_id=action_id,
            label=action["label"],
            variant=action["variant"],
            prefill=prefill,
            field_metadata=field_meta,
            is_primary=is_primary,
        ))

    # Add warnings
    if is_out_of_stock:
        warnings.append("Part is out of stock")
    elif is_low_stock:
        warnings.append(f"Part is below minimum level ({on_hand}/{min_level})")

    if part.get("is_critical"):
        warnings.append("This is a critical part")

    if alert_suppressed:
        warnings.append("Low stock alerts are suppressed for this part/category")

    # Sort: primary first, then by variant (MUTATE before READ)
    suggested_actions.sort(key=lambda a: (not a.is_primary, a.variant == "READ"))

    return PartSuggestionsResponse(
        part_id=part_id,
        part_name=part.get("name"),
        part_number=part.get("part_number"),
        stock=stock_info,
        suggested_actions=suggested_actions,
        warnings=warnings,
    )


@router.post("/shopping-list/prefill")
async def prefill_add_to_shopping_list(
    yacht_id: str = Query(...),
    part_id: str = Query(...),
    authorization: str = Header(None),
) -> PrefillResponse:
    """
    Prefill values for add_to_shopping_list action.

    Computes:
    - quantity_requested = round_up(max(min_level - on_hand, 1), reorder_multiple)
    - urgency based on stock level
    """
    db = get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Get part with min_level and reorder_multiple
        part_result = db.table("pms_parts").select(
            "id, name, part_number, min_level, reorder_multiple"
        ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

        if not part_result.data:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")

        part = part_result.data

        # Get current stock from canonical view
        stock_result = db.table("pms_part_stock").select(
            "on_hand"
        ).eq("yacht_id", yacht_id).eq("part_id", part_id).maybe_single().execute()

        stock = stock_result.data or {}
        on_hand = stock.get("on_hand", 0) or 0
        min_level = part.get("min_level", 0) or 0
        reorder_multiple = part.get("reorder_multiple", 1) or 1

        # Compute suggested quantity
        suggested_qty = compute_suggested_order_qty(on_hand, min_level, reorder_multiple)
        urgency = compute_urgency(on_hand, min_level)

        return PrefillResponse(
            status="success",
            prefill={
                "part_id": part_id,
                "part_name": part.get("name"),
                "part_number": part.get("part_number"),
                "current_stock": on_hand,
                "min_level": min_level,
                "reorder_multiple": reorder_multiple,
                "quantity_requested": suggested_qty,
                "urgency": urgency,
            },
            field_metadata={
                "quantity_requested": {
                    "classification": "BACKEND_AUTO",
                    "suggested_value": suggested_qty,
                    "editable": True,
                    "description": "round_up(max(min_level - on_hand, 1), reorder_multiple)",
                },
                "urgency": {
                    "classification": "BACKEND_AUTO",
                    "options": ["low", "medium", "high", "critical"],
                    "editable": True,
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"prefill_add_to_shopping_list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute prefill")


@router.post("/adjust-stock/prefill")
async def prefill_adjust_stock(
    yacht_id: str = Query(...),
    part_id: str = Query(...),
    authorization: str = Header(None),
) -> PrefillResponse:
    """
    Prefill values for adjust_stock_quantity action.

    Returns current quantity for user reference.
    This is a SIGNED action - requires PIN+TOTP signature.
    """
    db = get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Get part
        part_result = db.table("pms_parts").select(
            "id, name, part_number"
        ).eq("yacht_id", yacht_id).eq("id", part_id).maybe_single().execute()

        if not part_result.data:
            raise HTTPException(status_code=404, detail=f"Part not found: {part_id}")

        part = part_result.data

        # Get current stock from canonical view
        stock_result = db.table("pms_part_stock").select(
            "on_hand, location"
        ).eq("yacht_id", yacht_id).eq("part_id", part_id).maybe_single().execute()

        stock = stock_result.data or {}

        return PrefillResponse(
            status="success",
            prefill={
                "part_id": part_id,
                "part_name": part.get("name"),
                "part_number": part.get("part_number"),
                "current_quantity": stock.get("on_hand", 0) or 0,
                "location": stock.get("location"),
                "new_quantity": None,  # User must provide
                "reason": None,        # User must provide
            },
            field_metadata={
                "current_quantity": {
                    "classification": "BACKEND_AUTO",
                    "editable": False,
                },
                "new_quantity": {
                    "classification": "REQUIRED",
                    "editable": True,
                },
                "reason": {
                    "classification": "REQUIRED",
                    "options": [
                        "physical_count",
                        "damaged",
                        "expired",
                        "found_additional",
                        "correction",
                        "other",
                    ],
                    "editable": True,
                },
                "signature": {
                    "classification": "REQUIRED",
                    "description": "PIN+TOTP payload required for SIGNED action",
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"prefill_adjust_stock failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute prefill")


@router.get("/low-stock")
async def get_low_stock(
    yacht_id: str = Query(...),
    department: str = Query(None, description="Filter by department"),
    threshold_percent: float = Query(None, description="Filter by % of min_level"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None),
) -> LowStockResponse:
    """
    View parts below minimum stock level.

    Returns parts sorted by:
    1. Critical parts first
    2. Shortage amount (highest first)

    Includes suggested_order_qty for each part using the formula:
      round_up(max(min_level - on_hand, 1), reorder_multiple)
    """
    db = get_default_supabase_client()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        # Get parts with min_level > 0
        result = db.table("pms_parts").select(
            "id, name, part_number, is_critical, category, department, "
            "min_level, reorder_multiple, unit_cost"
        ).eq("yacht_id", yacht_id).gt("min_level", 0).execute()

        parts = result.data or []

        # Get all stock levels from canonical pms_part_stock view
        stock_result = db.table("pms_part_stock").select(
            "part_id, on_hand"
        ).eq("yacht_id", yacht_id).execute()

        stock_map = {s["part_id"]: s.get("on_hand", 0) or 0 for s in (stock_result.data or [])}

        # Filter to low stock
        low_stock_items = []
        total_value = 0.0

        for part in parts:
            on_hand = stock_map.get(part["id"], 0)
            min_level = part.get("min_level", 0) or 0
            reorder_multiple = part.get("reorder_multiple", 1) or 1

            # Check if below threshold
            if threshold_percent is not None:
                threshold = min_level * (threshold_percent / 100)
                if on_hand > threshold:
                    continue
            else:
                if on_hand > min_level:
                    continue

            # Department filter
            if department and part.get("department") != department:
                continue

            shortage = max(0, min_level - on_hand)
            suggested_qty = compute_suggested_order_qty(on_hand, min_level, reorder_multiple)

            # Calculate potential order value
            unit_cost = part.get("unit_cost") or 0
            if unit_cost and suggested_qty:
                total_value += unit_cost * suggested_qty

            low_stock_items.append(LowStockItem(
                id=part["id"],
                name=part["name"],
                part_number=part.get("part_number"),
                is_critical=part.get("is_critical", False),
                on_hand=on_hand,
                min_level=min_level,
                shortage=shortage,
                suggested_order_qty=suggested_qty,
                reorder_multiple=reorder_multiple,
                department=part.get("department"),
            ))

        # Sort: critical first, then by shortage descending
        low_stock_items.sort(key=lambda p: (not p.is_critical, -p.shortage))

        # Apply pagination
        paginated = low_stock_items[offset:offset + limit]
        critical_count = len([p for p in low_stock_items if p.is_critical])

        return LowStockResponse(
            parts=paginated,
            total_low_stock=len(low_stock_items),
            critical_count=critical_count,
            total_suggested_order_value=round(total_value, 2) if total_value else None,
        )

    except Exception as e:
        logger.error(f"get_low_stock failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve low stock data")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ["router"]
