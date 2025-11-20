"""
Insight Generator

Generates human-readable predictive insights with explanations and recommendations.

Combines:
- Risk scores
- Anomaly detection
- Signal analysis
- Fleet comparisons

Outputs structured insights for:
- UI cards
- Handover generation
- Work order recommendations
- Alert generation
"""

import logging
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
from uuid import UUID, uuid4

from services.signals import SignalCollector
from services.scoring import RiskScorer
from services.anomalies import AnomalyDetector
from services.fleet import FleetComparator
from db.supabase import db

logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generates predictive insights from risk scores and anomalies"""

    def __init__(self):
        self.signal_collector = SignalCollector()
        self.scorer = RiskScorer()
        self.anomaly_detector = AnomalyDetector()
        self.fleet_comparator = FleetComparator()
        self.db = db

    def determine_severity(self, risk_score: float, anomaly_severity: Optional[float] = None) -> Literal["low", "medium", "high", "critical"]:
        """
        Determine insight severity from risk score and anomaly severity.

        Args:
            risk_score: Equipment risk score (0-1)
            anomaly_severity: Anomaly severity if applicable (0-1)

        Returns:
            Severity level
        """
        max_severity = max(risk_score, anomaly_severity or 0.0)

        if max_severity >= 0.75:
            return "critical"
        elif max_severity >= 0.60:
            return "high"
        elif max_severity >= 0.40:
            return "medium"
        else:
            return "low"

    def generate_fault_prediction_insight(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        equipment_name: str,
        risk_score: float,
        signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate fault prediction insight"""
        fault_data = signals.get("signals", {}).get("fault", {})

        # Build explanation
        factors = []
        if fault_data.get("frequency_score", 0) > 0.5:
            factors.append(f"fault frequency above normal")
        if fault_data.get("clustering_score", 0) > 0.5:
            factors.append(f"repeated fault codes detected")
        if fault_data.get("recency_score", 0) > 0.7:
            factors.append(f"recent fault activity")

        contributing_signals = {
            "fault_frequency": fault_data.get("frequency_score", 0),
            "fault_clustering": fault_data.get("clustering_score", 0),
            "fault_recency": fault_data.get("recency_score", 0)
        }

        summary = f"{equipment_name} shows elevated fault risk ({risk_score:.2f})"
        explanation = (
            f"{equipment_name} is showing signs of potential upcoming failure. "
            f"Contributing factors: {', '.join(factors) if factors else 'general degradation pattern'}. "
            f"Recommend inspection and review of recent fault history."
        )

        recommended_action = "Inspect equipment, review fault logs, and consider preventive maintenance"

        return {
            "id": str(uuid4()),
            "yacht_id": str(yacht_id),
            "equipment_id": str(equipment_id),
            "equipment_name": equipment_name,
            "insight_type": "fault_prediction",
            "severity": self.determine_severity(risk_score),
            "summary": summary,
            "explanation": explanation,
            "recommended_action": recommended_action,
            "contributing_signals": contributing_signals,
            "related_entities": {"equipment_id": str(equipment_id)},
            "created_at": datetime.now().isoformat()
        }

    def generate_anomaly_insight(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        equipment_name: str,
        anomaly: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate insight from detected anomaly"""
        anomaly_type = anomaly.get("anomaly_type")
        severity_score = anomaly.get("severity", 0.5)

        # Map anomaly types to recommendations
        action_map = {
            "fault_frequency_spike": "Investigate root cause of increased fault rate. Review recent operational changes.",
            "unusual_search_pattern": "Crew indicating concern. Interview crew and inspect equipment.",
            "note_creation_spike": "Crew documenting issues. Review notes and address concerns proactively.",
            "abnormal_part_consumption": "Excessive part replacement indicates underlying issue. Perform comprehensive inspection.",
            "graph_propagation_anomaly": "Cascading issues detected. Review system-wide relationships and dependencies."
        }

        summary = anomaly.get("description", "Anomaly detected")
        explanation = (
            f"{equipment_name}: {anomaly.get('description', '')} "
            f"This pattern suggests emerging problems that require attention."
        )

        recommended_action = action_map.get(anomaly_type, "Investigate and monitor closely")

        contributing_signals = {
            "baseline_value": anomaly.get("baseline_value", 0),
            "current_value": anomaly.get("current_value", 0),
            "deviation_percentage": anomaly.get("deviation_percentage", 0)
        }

        return {
            "id": str(uuid4()),
            "yacht_id": str(yacht_id),
            "equipment_id": str(equipment_id),
            "equipment_name": equipment_name,
            "insight_type": "anomaly_detected",
            "severity": self.determine_severity(severity_score),
            "summary": summary,
            "explanation": explanation,
            "recommended_action": recommended_action,
            "contributing_signals": contributing_signals,
            "related_entities": {
                "equipment_id": str(equipment_id),
                "anomaly_type": anomaly_type
            },
            "created_at": datetime.now().isoformat()
        }

    def generate_crew_pain_insight(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        equipment_name: str,
        crew_signals: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate crew pain index insight"""
        search_score = crew_signals.get("search_score", 0)
        user_diversity = crew_signals.get("user_diversity_score", 0)
        note_frequency = crew_signals.get("note_frequency_score", 0)

        if search_score < 0.4 and user_diversity < 0.4:
            return None  # Not significant enough

        pain_score = (search_score + user_diversity + note_frequency) / 3.0

        summary = f"Crew pain index elevated for {equipment_name}"
        explanation = (
            f"Multiple crew members are repeatedly searching for and documenting issues with {equipment_name}. "
            f"This indicates an ongoing problem that is consuming crew attention and needs resolution. "
            f"Pain index: {pain_score:.2f}"
        )

        recommended_action = (
            "Interview crew to understand the specific issues. "
            "Address underlying problem to reduce crew workload and prevent escalation."
        )

        return {
            "id": str(uuid4()),
            "yacht_id": str(yacht_id),
            "equipment_id": str(equipment_id),
            "equipment_name": equipment_name,
            "insight_type": "crew_pain_index",
            "severity": self.determine_severity(pain_score),
            "summary": summary,
            "explanation": explanation,
            "recommended_action": recommended_action,
            "contributing_signals": {
                "search_score": search_score,
                "user_diversity_score": user_diversity,
                "note_frequency_score": note_frequency,
                "pain_index": pain_score
            },
            "related_entities": {"equipment_id": str(equipment_id)},
            "created_at": datetime.now().isoformat()
        }

    def generate_fleet_deviation_insight(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        equipment_name: str,
        fleet_comparison: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Generate fleet deviation insight"""
        if not fleet_comparison:
            return None

        deviation = fleet_comparison.get("fault_rate_deviation", 1.0)

        if deviation < 1.5:  # Not significantly different from fleet average
            return None

        summary = f"{equipment_name} shows {deviation:.1f}x higher fault rate than fleet average"
        explanation = (
            f"{equipment_name} is experiencing {deviation:.1f}x more faults than the fleet average "
            f"for similar equipment. Fleet average: {fleet_comparison.get('fleet_avg_fault_rate', 0):.1f} faults/year, "
            f"this yacht: {fleet_comparison.get('yacht_fault_rate', 0):.1f} faults/year. "
            f"This suggests a local issue specific to this installation."
        )

        recommended_action = (
            "Compare operational patterns with fleet best practices. "
            "Review installation, environmental factors, and maintenance procedures."
        )

        severity_score = min(deviation / 3.0, 1.0)  # 3x deviation = critical

        return {
            "id": str(uuid4()),
            "yacht_id": str(yacht_id),
            "equipment_id": str(equipment_id),
            "equipment_name": equipment_name,
            "insight_type": "fleet_deviation",
            "severity": self.determine_severity(severity_score),
            "summary": summary,
            "explanation": explanation,
            "recommended_action": recommended_action,
            "contributing_signals": {
                "yacht_fault_rate": fleet_comparison.get("yacht_fault_rate", 0),
                "fleet_avg_fault_rate": fleet_comparison.get("fleet_avg_fault_rate", 0),
                "deviation_multiplier": deviation
            },
            "related_entities": {
                "equipment_id": str(equipment_id),
                "equipment_class": fleet_comparison.get("equipment_class", "")
            },
            "created_at": datetime.now().isoformat()
        }

    async def generate_insights_for_equipment(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Generate all applicable insights for a piece of equipment.

        Args:
            yacht_id: Yacht UUID
            equipment_id: Equipment UUID

        Returns:
            List of insight dictionaries
        """
        logger.info(f"Generating insights for equipment {equipment_id}")

        insights = []

        # Get equipment details
        equipment = await self.db.get_equipment_by_id(equipment_id)
        if not equipment:
            logger.warning(f"Equipment {equipment_id} not found")
            return insights

        equipment_name = equipment.get("name", "Unknown")

        # Get risk score and signals
        risk_state = await self.db.get_risk_state_by_equipment(equipment_id)
        if risk_state:
            risk_score = risk_state.get("risk_score", 0)

            # Generate fault prediction insight if risk is significant
            if risk_score >= 0.40:
                # Get full signals for detailed analysis
                signals = await self.signal_collector.compute_all_signals(yacht_id, equipment_id)

                fault_insight = self.generate_fault_prediction_insight(
                    yacht_id,
                    equipment_id,
                    equipment_name,
                    risk_score,
                    signals
                )
                insights.append(fault_insight)

                # Crew pain index
                crew_signals = signals.get("signals", {}).get("crew_behavior", {})
                crew_insight = self.generate_crew_pain_insight(
                    yacht_id,
                    equipment_id,
                    equipment_name,
                    crew_signals
                )
                if crew_insight:
                    insights.append(crew_insight)

                # Fleet comparison
                fleet_comparison = await self.fleet_comparator.compare_to_fleet(
                    yacht_id,
                    equipment_id
                )
                fleet_insight = self.generate_fleet_deviation_insight(
                    yacht_id,
                    equipment_id,
                    equipment_name,
                    fleet_comparison
                )
                if fleet_insight:
                    insights.append(fleet_insight)

        # Anomaly-based insights
        anomalies = await self.anomaly_detector.detect_all_anomalies(yacht_id, equipment_id)
        for anomaly in anomalies:
            anomaly_insight = self.generate_anomaly_insight(
                yacht_id,
                equipment_id,
                equipment_name,
                anomaly
            )
            insights.append(anomaly_insight)

        # Save insights to database
        for insight in insights:
            await self.db.save_insight(insight)

        logger.info(f"Generated {len(insights)} insights for equipment {equipment_id}")
        return insights

    async def generate_insights_for_yacht(
        self,
        yacht_id: UUID,
        min_severity: Literal["low", "medium", "high", "critical"] = "low"
    ) -> Dict[str, Any]:
        """
        Generate insights for all equipment on a yacht.

        Args:
            yacht_id: Yacht UUID
            min_severity: Minimum severity to include

        Returns:
            Dict containing all insights and summary statistics
        """
        logger.info(f"Generating insights for yacht {yacht_id}")

        equipment_list = await self.db.get_equipment_by_yacht(yacht_id)
        all_insights = []

        for equipment in equipment_list:
            equipment_id = UUID(equipment["id"])
            try:
                insights = await self.generate_insights_for_equipment(yacht_id, equipment_id)
                all_insights.extend(insights)
            except Exception as e:
                logger.error(f"Error generating insights for equipment {equipment_id}: {e}")
                continue

        # Filter by severity if needed
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_severity_level = severity_order.get(min_severity, 0)

        filtered_insights = [
            i for i in all_insights
            if severity_order.get(i["severity"], 0) >= min_severity_level
        ]

        # Sort by severity (critical first)
        filtered_insights.sort(
            key=lambda x: severity_order.get(x["severity"], 0),
            reverse=True
        )

        # Calculate statistics
        critical_count = len([i for i in filtered_insights if i["severity"] == "critical"])
        high_count = len([i for i in filtered_insights if i["severity"] == "high"])
        medium_count = len([i for i in filtered_insights if i["severity"] == "medium"])
        low_count = len([i for i in filtered_insights if i["severity"] == "low"])

        result = {
            "yacht_id": str(yacht_id),
            "total_insights": len(filtered_insights),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "insights": filtered_insights,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(
            f"Generated insights for yacht: {critical_count} critical, "
            f"{high_count} high, {medium_count} medium, {low_count} low"
        )

        return result

    def generate_predictive_card(
        self,
        insight: Dict[str, Any],
        risk_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a predictive card for UI (search engine integration).

        Args:
            insight: Insight data
            risk_state: Optional risk state data

        Returns:
            Predictive card structure for UI
        """
        contributing_factors = []
        if risk_state:
            scoring = RiskScorer()
            # Extract factors from risk state
            if risk_state.get("fault_signal", 0) > 0.5:
                contributing_factors.append("Elevated fault activity")
            if risk_state.get("work_order_signal", 0) > 0.5:
                contributing_factors.append("Maintenance issues")
            if risk_state.get("crew_signal", 0) > 0.5:
                contributing_factors.append("Crew concern")

        # Build actions based on insight type and severity
        actions = []
        if insight["severity"] in ["high", "critical"]:
            actions.append({
                "action": "create_work_order",
                "label": "Create Work Order",
                "equipment_id": insight["equipment_id"]
            })

        actions.append({
            "action": "add_to_handover",
            "label": "Add to Handover",
            "context": {
                "insight_id": insight["id"],
                "equipment_id": insight["equipment_id"]
            }
        })

        actions.append({
            "action": "view_history",
            "label": "View History",
            "equipment_id": insight["equipment_id"]
        })

        return {
            "type": "predictive",
            "equipment": insight["equipment_name"],
            "equipment_id": insight["equipment_id"],
            "risk_score": risk_state.get("risk_score", 0.5) if risk_state else 0.5,
            "trend": risk_state.get("trend", "→") if risk_state else "→",
            "summary": insight["summary"],
            "severity": insight["severity"],
            "actions": actions,
            "contributing_factors": contributing_factors or [insight["explanation"][:100]],
            "recommendations": [insight["recommended_action"]],
            "related_faults": [],  # Could be populated from insight metadata
            "related_docs": [],
            "related_parts": []
        }
