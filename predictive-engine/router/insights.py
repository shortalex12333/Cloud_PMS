"""
Insights API Router

Provides endpoints for predictive insights, anomaly detection, and recommendations.

Endpoints:
- GET /v1/predictive/insights - Get insights for yacht
- GET /v1/predictive/insights/{equipment_id} - Get insights for equipment
- POST /v1/predictive/generate-insights - Generate new insights
- GET /v1/predictive/anomalies - Get detected anomalies
- GET /v1/predictive/fleet-comparison - Get fleet comparison data
"""

import logging
from typing import Optional, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

from services.insights import InsightGenerator
from services.anomalies import AnomalyDetector
from services.fleet import FleetComparator
from db.supabase import db

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateInsightsRequest(BaseModel):
    """Request to generate insights"""
    yacht_id: UUID
    equipment_id: Optional[UUID] = None
    min_severity: Literal["low", "medium", "high", "critical"] = "low"


@router.get("/insights")
async def get_insights(
    yacht_id: str = Query(..., description="Yacht ID"),
    min_severity: str = Query("low", description="Minimum severity (low/medium/high/critical)"),
    limit: int = Query(50, le=100, description="Maximum number of insights to return"),
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get predictive insights for a yacht.

    Args:
        yacht_id: Yacht UUID
        min_severity: Minimum severity level to include
        limit: Maximum number of insights

    Returns:
        List of insights with summary statistics
    """
    try:
        yacht_uuid = UUID(yacht_id)

        # Validate severity
        if min_severity not in ["low", "medium", "high", "critical"]:
            raise HTTPException(
                status_code=400,
                detail="min_severity must be one of: low, medium, high, critical"
            )

        # Get insights from database
        insights = await db.get_insights_by_yacht(
            yacht_uuid,
            min_severity=min_severity,
            limit=limit
        )

        # Filter by severity on client side
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order[min_severity]

        filtered_insights = [
            i for i in insights
            if severity_order.get(i.get("severity", "low"), 0) >= min_level
        ]

        # Calculate statistics
        critical_count = len([i for i in filtered_insights if i.get("severity") == "critical"])
        high_count = len([i for i in filtered_insights if i.get("severity") == "high"])
        medium_count = len([i for i in filtered_insights if i.get("severity") == "medium"])
        low_count = len([i for i in filtered_insights if i.get("severity") == "low"])

        return {
            "yacht_id": str(yacht_uuid),
            "total_insights": len(filtered_insights),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "insights": filtered_insights
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error retrieving insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/insights/{equipment_id}")
async def get_equipment_insights(
    equipment_id: str,
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get predictive insights for specific equipment.

    Args:
        equipment_id: Equipment UUID

    Returns:
        List of insights for the equipment
    """
    try:
        equipment_uuid = UUID(equipment_id)

        # Get equipment to find yacht_id
        equipment = await db.get_equipment_by_id(equipment_uuid)
        if not equipment:
            raise HTTPException(
                status_code=404,
                detail=f"Equipment {equipment_id} not found"
            )

        yacht_id = UUID(equipment["yacht_id"])

        # Get all insights and filter for this equipment
        all_insights = await db.get_insights_by_yacht(yacht_id, limit=100)

        equipment_insights = [
            i for i in all_insights
            if i.get("equipment_id") == str(equipment_uuid)
        ]

        return {
            "equipment_id": str(equipment_uuid),
            "equipment_name": equipment.get("name", "Unknown"),
            "total_insights": len(equipment_insights),
            "insights": equipment_insights
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error retrieving equipment insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/generate-insights")
async def generate_insights(
    request: GenerateInsightsRequest,
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Generate new predictive insights.

    This endpoint:
    - Computes risk scores
    - Detects anomalies
    - Generates explanations
    - Saves insights to database

    Args:
        request: Contains yacht_id, optional equipment_id, and min_severity

    Returns:
        Generated insights
    """
    logger.info(f"Generating insights for yacht {request.yacht_id}")

    try:
        generator = InsightGenerator()

        if request.equipment_id:
            # Generate for specific equipment
            insights = await generator.generate_insights_for_equipment(
                request.yacht_id,
                request.equipment_id
            )

            return {
                "status": "success",
                "message": f"Generated {len(insights)} insights for equipment {request.equipment_id}",
                "insights": insights
            }
        else:
            # Generate for all equipment on yacht
            result = await generator.generate_insights_for_yacht(
                request.yacht_id,
                request.min_severity
            )

            return {
                "status": "success",
                "message": f"Generated {result['total_insights']} insights for yacht",
                "summary": {
                    "total_insights": result["total_insights"],
                    "critical_count": result["critical_count"],
                    "high_count": result["high_count"],
                    "medium_count": result["medium_count"],
                    "low_count": result["low_count"]
                },
                "insights": result["insights"]
            }

    except Exception as e:
        logger.error(f"Error generating insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get("/anomalies")
async def get_anomalies(
    yacht_id: str = Query(..., description="Yacht ID"),
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get detected anomalies for a yacht.

    Anomalies are unusual patterns that may indicate emerging problems:
    - Fault frequency spikes
    - Search pattern anomalies (crew pain)
    - Note creation spikes
    - Abnormal part consumption
    - Graph propagation anomalies

    Args:
        yacht_id: Yacht UUID

    Returns:
        Detected anomalies with severity ratings
    """
    try:
        yacht_uuid = UUID(yacht_id)

        detector = AnomalyDetector()
        result = await detector.detect_yacht_anomalies(yacht_uuid)

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/fleet-comparison")
async def get_fleet_comparison(
    yacht_id: str = Query(..., description="Yacht ID"),
    equipment_id: Optional[str] = Query(None, description="Equipment ID (optional)"),
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get fleet comparison data for yacht equipment.

    Compares equipment performance to anonymized fleet averages.

    Args:
        yacht_id: Yacht UUID
        equipment_id: Optional equipment ID for specific comparison

    Returns:
        Fleet comparison data showing deviations from fleet average
    """
    try:
        yacht_uuid = UUID(yacht_id)
        comparator = FleetComparator()

        if equipment_id:
            # Compare specific equipment
            equipment_uuid = UUID(equipment_id)
            comparison = await comparator.compare_to_fleet(yacht_uuid, equipment_uuid)

            if not comparison:
                return {
                    "message": "Insufficient fleet data for comparison",
                    "comparison": None
                }

            return {
                "yacht_id": str(yacht_uuid),
                "equipment_id": str(equipment_uuid),
                "comparison": comparison
            }
        else:
            # Get fleet trends for all equipment
            trends = await comparator.identify_fleet_trends(yacht_uuid)

            return trends

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error retrieving fleet comparison: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/predictive-cards/{equipment_id}")
async def get_predictive_card(
    equipment_id: str,
    x_yacht_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """
    Get predictive card for equipment (for search engine integration).

    Returns a structured card with:
    - Risk score
    - Trend
    - Summary
    - Contributing factors
    - Recommended actions

    Args:
        equipment_id: Equipment UUID

    Returns:
        Predictive card structure for UI
    """
    try:
        equipment_uuid = UUID(equipment_id)

        # Get equipment
        equipment = await db.get_equipment_by_id(equipment_uuid)
        if not equipment:
            raise HTTPException(status_code=404, detail="Equipment not found")

        yacht_id = UUID(equipment["yacht_id"])

        # Get risk state
        risk_state = await db.get_risk_state_by_equipment(equipment_uuid)

        # Get insights
        all_insights = await db.get_insights_by_yacht(yacht_id, limit=50)
        equipment_insights = [
            i for i in all_insights
            if i.get("equipment_id") == str(equipment_uuid)
        ]

        # Generate card
        if equipment_insights:
            generator = InsightGenerator()
            card = generator.generate_predictive_card(
                equipment_insights[0],
                risk_state
            )
            return card
        elif risk_state:
            # Return basic card from risk state
            return {
                "type": "predictive",
                "equipment": equipment.get("name", "Unknown"),
                "equipment_id": str(equipment_uuid),
                "risk_score": risk_state.get("risk_score", 0),
                "trend": risk_state.get("trend", "→"),
                "summary": f"Risk score: {risk_state.get('risk_score', 0):.2f}",
                "severity": "high" if risk_state.get("risk_score", 0) >= 0.75 else "medium",
                "actions": [],
                "contributing_factors": [],
                "recommendations": []
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="No predictive data available for this equipment"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {e}")
    except Exception as e:
        logger.error(f"Error generating predictive card: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
