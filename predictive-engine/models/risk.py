"""
Risk Score Models

Data models for equipment risk scoring and predictive state.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


class SignalScores(BaseModel):
    """Individual signal scores that contribute to overall risk"""
    fault_signal: float = Field(ge=0.0, le=1.0, description="Fault pattern signal (0-1)")
    work_order_signal: float = Field(ge=0.0, le=1.0, description="Work order signal (0-1)")
    crew_activity_signal: float = Field(ge=0.0, le=1.0, description="Crew behavior signal (0-1)")
    part_consumption_signal: float = Field(ge=0.0, le=1.0, description="Part usage signal (0-1)")
    global_knowledge_signal: float = Field(ge=0.0, le=1.0, description="Global knowledge signal (0-1)")


class RiskScore(BaseModel):
    """Equipment risk score"""
    id: UUID
    yacht_id: UUID
    equipment_id: UUID
    equipment_name: Optional[str] = None

    # Overall risk
    risk_score: float = Field(ge=0.0, le=1.0, description="Overall risk score (0-1)")
    trend: Literal["↑", "↓", "→"] = Field(description="Trend direction")

    # Individual signals
    fault_signal: float = Field(ge=0.0, le=1.0)
    work_order_signal: float = Field(ge=0.0, le=1.0)
    crew_signal: float = Field(ge=0.0, le=1.0)
    part_signal: float = Field(ge=0.0, le=1.0)
    global_signal: float = Field(ge=0.0, le=1.0)

    # Metadata
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskStateResponse(BaseModel):
    """Response for risk state query"""
    yacht_id: UUID
    total_equipment: int
    high_risk_count: int  # risk_score >= 0.75
    emerging_risk_count: int  # risk_score >= 0.60
    monitor_count: int  # risk_score >= 0.40
    normal_count: int  # risk_score < 0.40
    equipment_risks: list[RiskScore]


class RiskCalculationRequest(BaseModel):
    """Request to calculate risk for specific equipment"""
    yacht_id: UUID
    equipment_id: Optional[UUID] = None
    force_recalculate: bool = False


class TrendData(BaseModel):
    """Historical trend data for risk scoring"""
    current_score: float
    previous_score: Optional[float] = None
    change_rate: Optional[float] = None
    trend: Literal["↑", "↓", "→"]
