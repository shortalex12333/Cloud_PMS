"""
Predictive Insights Models

Data models for predictive insights, anomalies, and recommendations.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, date
from uuid import UUID


class PredictiveInsight(BaseModel):
    """Predictive insight for equipment"""
    id: UUID
    yacht_id: UUID
    equipment_id: Optional[UUID] = None
    equipment_name: Optional[str] = None

    insight_type: Literal[
        "fault_prediction",
        "anomaly_detected",
        "part_shortage",
        "crew_pain_index",
        "maintenance_overdue",
        "cascade_risk",
        "fleet_deviation"
    ]

    severity: Literal["low", "medium", "high", "critical"]
    summary: str = Field(description="Human-readable summary")
    explanation: str = Field(description="Detailed explanation of the insight")
    recommended_action: Optional[str] = None

    # Contributing factors
    contributing_signals: Dict[str, float] = Field(default_factory=dict)
    related_entities: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime

    class Config:
        from_attributes = True


class InsightsResponse(BaseModel):
    """Response for insights query"""
    yacht_id: UUID
    total_insights: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    insights: List[PredictiveInsight]


class AnomalyDetection(BaseModel):
    """Anomaly detection result"""
    equipment_id: UUID
    anomaly_type: Literal[
        "fault_frequency_spike",
        "unusual_search_pattern",
        "abnormal_part_consumption",
        "note_creation_spike",
        "graph_propagation_anomaly"
    ]
    severity: float = Field(ge=0.0, le=1.0)
    description: str
    detected_at: datetime
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    deviation_percentage: Optional[float] = None


class FleetComparison(BaseModel):
    """Fleet-level anonymized comparison"""
    equipment_class: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None

    # Yacht's metrics
    yacht_fault_rate: float
    yacht_risk_score: float

    # Fleet metrics (anonymized)
    fleet_avg_fault_rate: float
    fleet_avg_risk_score: float
    fleet_sample_size: int

    # Deviation
    fault_rate_deviation: float  # multiplier (e.g., 2.1x means 2.1 times higher)
    risk_deviation: float

    comparison_summary: str


class RecommendedAction(BaseModel):
    """Recommended action based on insight"""
    action_type: Literal[
        "create_work_order",
        "order_parts",
        "inspect_equipment",
        "add_to_handover",
        "contact_vendor",
        "review_manual"
    ]
    priority: Literal["low", "medium", "high", "urgent"]
    description: str
    equipment_id: Optional[UUID] = None
    part_ids: List[UUID] = Field(default_factory=list)
    document_ids: List[UUID] = Field(default_factory=list)


class PredictiveCard(BaseModel):
    """Predictive insight card for UI (search engine integration)"""
    type: Literal["predictive"] = "predictive"
    equipment: str
    equipment_id: UUID
    risk_score: float = Field(ge=0.0, le=1.0)
    trend: Literal["↑", "↓", "→"]
    summary: str
    severity: Literal["low", "medium", "high", "critical"]

    # UI components
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Links
    related_faults: List[UUID] = Field(default_factory=list)
    related_docs: List[UUID] = Field(default_factory=list)
    related_parts: List[UUID] = Field(default_factory=list)


class InsightGenerationRequest(BaseModel):
    """Request to generate insights"""
    yacht_id: UUID
    equipment_id: Optional[UUID] = None
    min_severity: Literal["low", "medium", "high", "critical"] = "low"
    limit: int = Field(default=50, le=100)


class CrewPainIndex(BaseModel):
    """Crew pain index - repeated searches indicating problems"""
    equipment_id: UUID
    equipment_name: str
    search_count: int
    unique_users: int
    time_period_days: int
    common_queries: List[str]
    pain_score: float = Field(ge=0.0, le=1.0, description="Normalized pain score")
    interpretation: str
