"""
Scoring Engine

Computes risk scores from signals using weighted formula:

risk_score =
  0.35 * fault_signal +
  0.25 * work_order_signal +
  0.15 * crew_activity_signal +
  0.15 * part_consumption_signal +
  0.10 * global_knowledge_signal

Output range: 0.00 - 1.00

Thresholds:
- 0.00 - 0.40: normal
- 0.40 - 0.60: monitor
- 0.60 - 0.75: emerging risk
- 0.75 - 1.00: high risk / likely upcoming failure
"""

import logging
from typing import Dict, Any, Literal, Optional
from datetime import datetime
from uuid import UUID

from services.signals import SignalCollector
from db.supabase import db

logger = logging.getLogger(__name__)


class RiskScorer:
    """Computes equipment risk scores from signals"""

    # Signal weights (must sum to 1.0)
    WEIGHTS = {
        "fault": 0.35,
        "work_order": 0.25,
        "crew_activity": 0.15,
        "part_consumption": 0.15,
        "global_knowledge": 0.10
    }

    # Risk thresholds
    THRESHOLDS = {
        "normal": (0.0, 0.40),
        "monitor": (0.40, 0.60),
        "emerging": (0.60, 0.75),
        "high": (0.75, 1.00)
    }

    def __init__(self):
        self.signal_collector = SignalCollector()
        self.db = db

    def calculate_risk_score(self, signals: Dict[str, Any]) -> float:
        """
        Calculate overall risk score from signal data.

        Args:
            signals: Dict containing signal categories with 'overall' scores

        Returns:
            float: Risk score between 0.0 and 1.0
        """
        signal_data = signals.get("signals", {})

        # Extract overall scores from each signal category
        fault_score = signal_data.get("fault", {}).get("overall", 0.0)
        wo_score = signal_data.get("work_order", {}).get("overall", 0.0)
        crew_score = signal_data.get("crew_behavior", {}).get("overall", 0.0)
        part_score = signal_data.get("part_consumption", {}).get("overall", 0.0)
        global_score = signal_data.get("global_knowledge", {}).get("overall", 0.0)

        # Weighted sum
        risk_score = (
            self.WEIGHTS["fault"] * fault_score +
            self.WEIGHTS["work_order"] * wo_score +
            self.WEIGHTS["crew_activity"] * crew_score +
            self.WEIGHTS["part_consumption"] * part_score +
            self.WEIGHTS["global_knowledge"] * global_score
        )

        # Ensure within bounds
        risk_score = max(0.0, min(1.0, risk_score))

        logger.debug(
            f"Risk calculation: fault={fault_score:.3f}, wo={wo_score:.3f}, "
            f"crew={crew_score:.3f}, part={part_score:.3f}, global={global_score:.3f} "
            f"=> risk={risk_score:.3f}"
        )

        return risk_score

    def get_risk_category(self, risk_score: float) -> str:
        """Get risk category from score"""
        for category, (low, high) in self.THRESHOLDS.items():
            if low <= risk_score < high:
                return category
        return "high"  # Catch-all for 1.0

    def calculate_trend(
        self,
        current_score: float,
        previous_score: Optional[float]
    ) -> Literal["↑", "↓", "→"]:
        """
        Calculate trend direction.

        Args:
            current_score: Current risk score
            previous_score: Previous risk score (None if first calculation)

        Returns:
            Trend indicator: ↑ (worsening), ↓ (improving), → (stable)
        """
        if previous_score is None:
            return "→"

        delta = current_score - previous_score
        threshold = 0.05  # 5% change threshold

        if delta > threshold:
            return "↑"
        elif delta < -threshold:
            return "↓"
        else:
            return "→"

    async def compute_and_save_risk(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        force_recalculate: bool = False
    ) -> Dict[str, Any]:
        """
        Compute risk score for equipment and save to database.

        Args:
            yacht_id: Yacht UUID
            equipment_id: Equipment UUID
            force_recalculate: Force recalculation even if recent data exists

        Returns:
            Dict containing risk score and metadata
        """
        logger.info(f"Computing risk for equipment {equipment_id}")

        # Get previous risk state for trend calculation
        previous_state = await self.db.get_risk_state_by_equipment(equipment_id)
        previous_score = previous_state.get("risk_score") if previous_state else None

        # Check if we need to recalculate
        if not force_recalculate and previous_state:
            updated_at = datetime.fromisoformat(
                previous_state["updated_at"].replace("Z", "+00:00")
            )
            hours_since_update = (datetime.now() - updated_at).total_seconds() / 3600

            if hours_since_update < 6:  # Don't recalculate if updated within 6 hours
                logger.info(f"Using cached risk state (updated {hours_since_update:.1f}h ago)")
                return previous_state

        # Collect all signals
        signals = await self.signal_collector.compute_all_signals(yacht_id, equipment_id)

        # Calculate risk score
        risk_score = self.calculate_risk_score(signals)

        # Calculate trend
        trend = self.calculate_trend(risk_score, previous_score)

        # Get equipment details for metadata
        equipment = await self.db.get_equipment_by_id(equipment_id)
        equipment_name = equipment.get("name") if equipment else "Unknown"

        # Prepare risk state data
        risk_state = {
            "yacht_id": str(yacht_id),
            "equipment_id": str(equipment_id),
            "equipment_name": equipment_name,
            "risk_score": round(risk_score, 4),
            "trend": trend,
            "fault_signal": round(signals["signals"]["fault"]["overall"], 4),
            "work_order_signal": round(signals["signals"]["work_order"]["overall"], 4),
            "crew_signal": round(signals["signals"]["crew_behavior"]["overall"], 4),
            "part_signal": round(signals["signals"]["part_consumption"]["overall"], 4),
            "global_signal": round(signals["signals"]["global_knowledge"]["overall"], 4),
            "updated_at": datetime.now().isoformat()
        }

        # Save to database
        success = await self.db.save_risk_state(risk_state)

        if success:
            logger.info(
                f"Risk score saved: {equipment_name} = {risk_score:.3f} ({trend})"
            )
        else:
            logger.error(f"Failed to save risk state for {equipment_id}")

        return risk_state

    async def compute_risk_for_yacht(
        self,
        yacht_id: UUID,
        force_recalculate: bool = False
    ) -> Dict[str, Any]:
        """
        Compute risk scores for all equipment on a yacht.

        Args:
            yacht_id: Yacht UUID
            force_recalculate: Force recalculation for all equipment

        Returns:
            Dict containing summary statistics and all risk scores
        """
        logger.info(f"Computing risk for all equipment on yacht {yacht_id}")

        # Get all equipment
        equipment_list = await self.db.get_equipment_by_yacht(yacht_id)

        if not equipment_list:
            logger.warning(f"No equipment found for yacht {yacht_id}")
            return {
                "yacht_id": str(yacht_id),
                "total_equipment": 0,
                "equipment_risks": []
            }

        # Compute risk for each equipment
        risk_scores = []
        for equipment in equipment_list:
            equipment_id = UUID(equipment["id"])
            try:
                risk_state = await self.compute_and_save_risk(
                    yacht_id,
                    equipment_id,
                    force_recalculate
                )
                risk_scores.append(risk_state)
            except Exception as e:
                logger.error(f"Error computing risk for equipment {equipment_id}: {e}")
                continue

        # Compute statistics
        high_risk = [r for r in risk_scores if r["risk_score"] >= 0.75]
        emerging_risk = [r for r in risk_scores if 0.60 <= r["risk_score"] < 0.75]
        monitor = [r for r in risk_scores if 0.40 <= r["risk_score"] < 0.60]
        normal = [r for r in risk_scores if r["risk_score"] < 0.40]

        result = {
            "yacht_id": str(yacht_id),
            "total_equipment": len(risk_scores),
            "high_risk_count": len(high_risk),
            "emerging_risk_count": len(emerging_risk),
            "monitor_count": len(monitor),
            "normal_count": len(normal),
            "equipment_risks": sorted(
                risk_scores,
                key=lambda x: x["risk_score"],
                reverse=True
            ),
            "computed_at": datetime.now().isoformat()
        }

        logger.info(
            f"Risk computation complete: {len(high_risk)} high, "
            f"{len(emerging_risk)} emerging, {len(monitor)} monitor, "
            f"{len(normal)} normal"
        )

        return result

    def get_contributing_factors(self, signals: Dict[str, Any]) -> list[str]:
        """
        Get human-readable list of contributing factors.

        Args:
            signals: Signal data

        Returns:
            List of contributing factor descriptions
        """
        factors = []
        signal_data = signals.get("signals", {})

        # Fault signals
        fault = signal_data.get("fault", {})
        if fault.get("frequency_score", 0) > 0.6:
            factors.append("High fault frequency")
        if fault.get("clustering_score", 0) > 0.6:
            factors.append("Repeated fault codes")
        if fault.get("severity_score", 0) > 0.7:
            factors.append("High severity faults")

        # Work order signals
        wo = signal_data.get("work_order", {})
        if wo.get("overdue_score", 0) > 0.5:
            factors.append("Overdue maintenance tasks")
        if wo.get("repeated_corrective_score", 0) > 0.5:
            factors.append("Repeated corrective maintenance")

        # Equipment behavior
        eq = signal_data.get("equipment_behavior", {})
        if eq.get("mtbf_score", 0) > 0.6:
            factors.append("Low mean time between failures")
        if eq.get("symptom_notes_score", 0) > 0.5:
            factors.append("Crew reporting symptoms (vibration, noise, leaks)")

        # Crew behavior
        crew = signal_data.get("crew_behavior", {})
        if crew.get("search_score", 0) > 0.5:
            factors.append("Frequent crew searches (pain index)")
        if crew.get("user_diversity_score", 0) > 0.5:
            factors.append("Multiple crew members investigating")

        # Part consumption
        part = signal_data.get("part_consumption", {})
        if part.get("replacement_frequency_score", 0) > 0.6:
            factors.append("High part replacement frequency")

        # Global knowledge
        global_sig = signal_data.get("global_knowledge", {})
        if global_sig.get("fleet_deviation_score", 0) > 0.6:
            factors.append("Above fleet average fault rate")

        return factors
