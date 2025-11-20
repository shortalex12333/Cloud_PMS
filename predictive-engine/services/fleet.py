"""
Fleet Comparison Module

Provides anonymized fleet-level comparisons for benchmarking.

Compares individual yacht equipment performance against:
- Fleet-wide averages
- Equipment class norms
- Manufacturer-specific patterns

All comparisons maintain yacht privacy - no yacht identities are exposed.
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
from uuid import UUID

from db.supabase import db

logger = logging.getLogger(__name__)


class FleetComparator:
    """Compares yacht equipment to anonymized fleet statistics"""

    def __init__(self):
        self.db = db

    async def compare_to_fleet(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Compare equipment performance to fleet average.

        Args:
            yacht_id: Yacht UUID
            equipment_id: Equipment UUID

        Returns:
            Fleet comparison data or None if insufficient data
        """
        # Get equipment details
        equipment = await self.db.get_equipment_by_id(equipment_id)
        if not equipment:
            return None

        equipment_class = equipment.get("system_type", "")
        manufacturer = equipment.get("manufacturer", "")
        model = equipment.get("model", "")

        if not equipment_class:
            logger.warning(f"Equipment {equipment_id} missing system_type")
            return None

        # Get fleet statistics (anonymized)
        fleet_stats = await self.db.get_fleet_statistics(
            equipment_class=equipment_class,
            manufacturer=manufacturer
        )

        if not fleet_stats:
            logger.info(f"No fleet statistics available for {equipment_class}")
            return None

        # Calculate yacht's metrics
        faults = await self.db.get_faults_by_equipment(equipment_id, 365)
        yacht_fault_rate = len(faults) / 12.0  # faults per month

        # Get risk score
        risk_state = await self.db.get_risk_state_by_equipment(equipment_id)
        yacht_risk_score = risk_state.get("risk_score", 0.0) if risk_state else 0.0

        # Fleet averages
        fleet_avg_fault_rate = fleet_stats.get("avg_fault_rate", 0.5)
        fleet_avg_risk_score = fleet_stats.get("avg_risk_score", 0.3)
        fleet_sample_size = fleet_stats.get("sample_size", 10)

        # Calculate deviations
        if fleet_avg_fault_rate > 0:
            fault_rate_deviation = yacht_fault_rate / fleet_avg_fault_rate
        else:
            fault_rate_deviation = 1.0

        if fleet_avg_risk_score > 0:
            risk_deviation = yacht_risk_score / fleet_avg_risk_score
        else:
            risk_deviation = 1.0

        # Generate comparison summary
        if fault_rate_deviation > 1.5:
            comparison = (
                f"This {equipment_class} shows {fault_rate_deviation:.1f}x more faults "
                f"than fleet average for similar equipment."
            )
        elif fault_rate_deviation < 0.7:
            comparison = (
                f"This {equipment_class} performs better than fleet average "
                f"({fault_rate_deviation:.1f}x fewer faults)."
            )
        else:
            comparison = (
                f"This {equipment_class} performs within normal range "
                f"compared to fleet average."
            )

        return {
            "equipment_class": equipment_class,
            "manufacturer": manufacturer,
            "model": model,
            "yacht_fault_rate": round(yacht_fault_rate, 2),
            "yacht_risk_score": round(yacht_risk_score, 3),
            "fleet_avg_fault_rate": round(fleet_avg_fault_rate, 2),
            "fleet_avg_risk_score": round(fleet_avg_risk_score, 3),
            "fleet_sample_size": fleet_sample_size,
            "fault_rate_deviation": round(fault_rate_deviation, 2),
            "risk_deviation": round(risk_deviation, 2),
            "comparison_summary": comparison
        }

    async def get_fleet_statistics_summary(
        self,
        equipment_class: str,
        manufacturer: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get fleet-wide statistics for an equipment class.

        Args:
            equipment_class: Equipment type (e.g., "main_engine", "generator")
            manufacturer: Optional manufacturer filter

        Returns:
            Fleet statistics summary
        """
        stats = await self.db.get_fleet_statistics(
            equipment_class=equipment_class,
            manufacturer=manufacturer
        )

        if not stats:
            return None

        return {
            "equipment_class": equipment_class,
            "manufacturer": manufacturer,
            "avg_fault_rate": stats.get("avg_fault_rate", 0),
            "avg_risk_score": stats.get("avg_risk_score", 0),
            "avg_mtbf_days": stats.get("avg_mtbf_days", 0),
            "sample_size": stats.get("sample_size", 0),
            "data_quality": "high" if stats.get("sample_size", 0) >= 10 else "limited"
        }

    async def identify_fleet_trends(
        self,
        yacht_id: UUID
    ) -> Dict[str, Any]:
        """
        Identify fleet-wide trends affecting this yacht.

        Args:
            yacht_id: Yacht UUID

        Returns:
            Dict containing trend analysis
        """
        equipment_list = await self.db.get_equipment_by_yacht(yacht_id)

        trends = []
        for equipment in equipment_list:
            equipment_id = UUID(equipment["id"])
            comparison = await self.compare_to_fleet(yacht_id, equipment_id)

            if comparison and comparison["fault_rate_deviation"] > 1.5:
                trends.append({
                    "equipment_name": equipment.get("name"),
                    "equipment_id": str(equipment_id),
                    "equipment_class": comparison["equipment_class"],
                    "deviation": comparison["fault_rate_deviation"],
                    "status": "above_fleet_average"
                })

        return {
            "yacht_id": str(yacht_id),
            "total_equipment_analyzed": len(equipment_list),
            "equipment_above_fleet_avg": len(trends),
            "trends": sorted(trends, key=lambda x: x["deviation"], reverse=True)
        }
