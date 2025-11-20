"""
Risk API Router

Provides endpoints for risk state queries and predictive engine execution.

Endpoints:
- GET /v1/predictive/state - Get risk states for yacht
- POST /v1/predictive/run - Trigger manual predictive run
- POST /v1/predictive/run-for-yacht - Run for specific yacht
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

from services.scoring import RiskScorer
from models.risk import RiskStateResponse, RiskCalculationRequest
from db.supabase import db

logger = logging.getLogger(__name__)

router = APIRouter()


class RunPredictiveRequest(BaseModel):
    """Request to run predictive engine"""
    yacht_id: UUID
    equipment_id: Optional[UUID] = None
    force_recalculate: bool = False


@router.get("/state", response_model=dict)
async def get_risk_state(
    yacht_id: Optional[str] = Query(None, description="Yacht ID"),
    equipment_id: Optional[str] = Query(None, description="Equipment ID (optional)"),
    x_yacht_signature: Optional[str] = Header(None, description="Yacht signature for authentication"),
    authorization: Optional[str] = Header(None, description="Bearer token")
):
    """
    Get risk states for yacht or specific equipment.

    Returns:
        Risk state data including scores, trends, and statistics
    """
    # Authentication would be validated here in production
    # For now, we'll use the yacht_id parameter

    if not yacht_id:
        raise HTTPException(status_code=400, detail="yacht_id is required")

    try:
        yacht_uuid = UUID(yacht_id)

        if equipment_id:
            # Get risk state for specific equipment
            equipment_uuid = UUID(equipment_id)
            risk_state = await db.get_risk_state_by_equipment(equipment_uuid)

            if not risk_state:
                raise HTTPException(
                    status_code=404,
                    detail=f"No risk state found for equipment {equipment_id}"
                )

            return risk_state
        else:
            # Get all risk states for yacht
            risk_states = await db.get_risk_state_by_yacht(yacht_uuid)

            # Calculate statistics
            total_equipment = len(risk_states)
            high_risk = [r for r in risk_states if r["risk_score"] >= 0.75]
            emerging_risk = [r for r in risk_states if 0.60 <= r["risk_score"] < 0.75]
            monitor = [r for r in risk_states if 0.40 <= r["risk_score"] < 0.60]
            normal = [r for r in risk_states if r["risk_score"] < 0.40]

            return {
                "yacht_id": str(yacht_uuid),
                "total_equipment": total_equipment,
                "high_risk_count": len(high_risk),
                "emerging_risk_count": len(emerging_risk),
                "monitor_count": len(monitor),
                "normal_count": len(normal),
                "equipment_risks": risk_states
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error retrieving risk state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/run")
async def run_predictive_engine(
    request: RunPredictiveRequest,
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Manually trigger predictive engine run.

    This endpoint can be called:
    - Manually for testing
    - After significant data changes
    - On-demand from UI

    Args:
        request: Contains yacht_id, optional equipment_id, and force_recalculate flag

    Returns:
        Computed risk scores and summary
    """
    logger.info(f"Manual predictive run requested for yacht {request.yacht_id}")

    try:
        scorer = RiskScorer()

        if request.equipment_id:
            # Run for specific equipment
            risk_state = await scorer.compute_and_save_risk(
                request.yacht_id,
                request.equipment_id,
                request.force_recalculate
            )

            return {
                "status": "success",
                "message": f"Risk computed for equipment {request.equipment_id}",
                "risk_state": risk_state
            }
        else:
            # Run for all equipment on yacht
            result = await scorer.compute_risk_for_yacht(
                request.yacht_id,
                request.force_recalculate
            )

            return {
                "status": "success",
                "message": f"Risk computed for {result['total_equipment']} equipment items",
                "summary": {
                    "total_equipment": result["total_equipment"],
                    "high_risk_count": result["high_risk_count"],
                    "emerging_risk_count": result["emerging_risk_count"],
                    "monitor_count": result["monitor_count"],
                    "normal_count": result["normal_count"]
                },
                "equipment_risks": result["equipment_risks"]
            }

    except Exception as e:
        logger.error(f"Error running predictive engine: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run predictive engine: {str(e)}"
        )


@router.post("/run-for-yacht")
async def run_for_specific_yacht(
    yacht_id: str = Query(..., description="Yacht ID"),
    force_recalculate: bool = Query(False, description="Force recalculation"),
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Run predictive engine for a specific yacht.

    This is the primary endpoint used by:
    - Cron jobs (6-hour schedule)
    - Post-indexing triggers
    - Manual admin requests

    Args:
        yacht_id: Yacht UUID
        force_recalculate: Force recalculation even if recently updated

    Returns:
        Summary of risk computation results
    """
    logger.info(f"Running predictive engine for yacht {yacht_id}")

    try:
        yacht_uuid = UUID(yacht_id)
        scorer = RiskScorer()

        result = await scorer.compute_risk_for_yacht(
            yacht_uuid,
            force_recalculate
        )

        return {
            "status": "success",
            "yacht_id": str(yacht_uuid),
            "computed_at": result["computed_at"],
            "summary": {
                "total_equipment": result["total_equipment"],
                "high_risk": result["high_risk_count"],
                "emerging_risk": result["emerging_risk_count"],
                "monitor": result["monitor_count"],
                "normal": result["normal_count"]
            },
            "top_risks": result["equipment_risks"][:10]  # Return top 10 highest risks
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error running predictive for yacht: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run predictive engine: {str(e)}"
        )


@router.get("/state/{equipment_id}")
async def get_equipment_risk_state(
    equipment_id: str,
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get risk state for a specific equipment.

    Args:
        equipment_id: Equipment UUID

    Returns:
        Risk state data for the equipment
    """
    try:
        equipment_uuid = UUID(equipment_id)
        risk_state = await db.get_risk_state_by_equipment(equipment_uuid)

        if not risk_state:
            raise HTTPException(
                status_code=404,
                detail=f"No risk state found for equipment {equipment_id}"
            )

        return risk_state

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error retrieving equipment risk state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
