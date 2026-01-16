"""
Trigger Routes
==============

API endpoints for checking business rule triggers.

Endpoints:
- GET  /v1/triggers/check - Check all triggers for a yacht
- GET  /v1/triggers/low-stock - Check low stock triggers only
- GET  /v1/triggers/overdue-work-orders - Check overdue WO triggers only
- GET  /v1/triggers/hor-violations - Check HOR compliance violations
- GET  /v1/triggers/maintenance-due - Check upcoming maintenance triggers

All routes require yacht_id parameter and return triggered items with suggested actions.
"""

from fastapi import APIRouter, Query, HTTPException, Header
from typing import Optional
import os
import logging

from supabase import create_client, Client

# Import trigger service
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.trigger_service import TriggerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/triggers", tags=["triggers"])


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

def get_supabase_client() -> Client:
    """Get TENANT Supabase client for yacht operations.

    Uses DEFAULT_YACHT_CODE env var to route to correct tenant DB.
    """
    default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")

    url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise HTTPException(status_code=500, detail=f"TENANT Supabase config missing for {default_yacht}")

    return create_client(url, key)


def get_trigger_service() -> TriggerService:
    """Get trigger service instance."""
    return TriggerService(get_supabase_client())


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/check")
async def check_all_triggers(
    yacht_id: str = Query(..., description="Yacht ID to check triggers for"),
    authorization: Optional[str] = Header(None)
):
    """
    Check all business rule triggers for a yacht.

    Returns combined results from all trigger types:
    - LOW_STOCK: Parts below minimum stock threshold
    - OVERDUE_WO: Work orders past due date
    - HOR_VIOLATION: Hours of rest compliance violations
    - MAINTENANCE_DUE: Equipment maintenance due within 7 days

    Each triggered item includes:
    - severity (critical, warning, info)
    - entity details (id, name, type)
    - suggested_actions (list of action names)
    """
    try:
        service = get_trigger_service()
        result = await service.check_all_triggers(yacht_id)

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger.error(f"Trigger check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/low-stock")
async def check_low_stock(
    yacht_id: str = Query(..., description="Yacht ID"),
    authorization: Optional[str] = Header(None)
):
    """
    Check for parts with stock level at or below minimum threshold.

    Trigger: quantity_on_hand <= minimum_stock

    Severity:
    - critical: Out of stock (quantity = 0)
    - warning: Low stock (quantity > 0 but <= minimum)
    """
    try:
        service = get_trigger_service()
        items = await service.check_low_stock(yacht_id)

        return {
            "status": "success",
            "trigger_type": "LOW_STOCK",
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error(f"Low stock check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overdue-work-orders")
async def check_overdue_work_orders(
    yacht_id: str = Query(..., description="Yacht ID"),
    authorization: Optional[str] = Header(None)
):
    """
    Check for work orders that are past their due date.

    Trigger: due_date < NOW() AND status NOT IN ('completed', 'cancelled', 'closed')

    Severity:
    - critical: Overdue > 7 days OR urgent/critical priority
    - warning: Overdue <= 7 days
    """
    try:
        service = get_trigger_service()
        items = await service.check_overdue_work_orders(yacht_id)

        return {
            "status": "success",
            "trigger_type": "OVERDUE_WO",
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error(f"Overdue WO check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hor-violations")
async def check_hor_violations(
    yacht_id: str = Query(..., description="Yacht ID"),
    days_back: int = Query(7, description="Number of days to check back"),
    authorization: Optional[str] = Header(None)
):
    """
    Check for Hours of Rest compliance violations.

    Trigger:
    - is_daily_compliant = false (MLC 2006: < 10 hours rest per day)
    - is_weekly_compliant = false (STCW: < 77 hours rest per week)

    Severity:
    - critical: Both daily AND weekly violations
    - warning: Either daily OR weekly violation
    """
    try:
        service = get_trigger_service()
        items = await service.check_hor_violations(yacht_id, days_back)

        return {
            "status": "success",
            "trigger_type": "HOR_VIOLATION",
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error(f"HOR violation check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/maintenance-due")
async def check_maintenance_due(
    yacht_id: str = Query(..., description="Yacht ID"),
    days_ahead: int = Query(7, description="Number of days ahead to check"),
    authorization: Optional[str] = Header(None)
):
    """
    Check for equipment with maintenance due within specified window.

    Trigger: next_service_date <= NOW() + days_ahead

    Severity:
    - critical: Overdue (next_service_date < NOW())
    - warning: Due within 3 days
    - info: Due within 7 days
    """
    try:
        service = get_trigger_service()
        items = await service.check_maintenance_due(yacht_id, days_ahead)

        return {
            "status": "success",
            "trigger_type": "MAINTENANCE_DUE",
            "count": len(items),
            "items": items
        }

    except Exception as e:
        logger.error(f"Maintenance due check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for triggers service."""
    return {
        "status": "ok",
        "service": "triggers",
        "available_triggers": [
            "LOW_STOCK",
            "OVERDUE_WO",
            "HOR_VIOLATION",
            "MAINTENANCE_DUE"
        ]
    }
