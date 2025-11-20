"""
Anomaly Detection Module

Detects anomalies and unusual patterns that indicate emerging problems:
- Outlier detection on fault frequency
- Unexpected spikes in note creation
- Sudden search query clusters
- Abnormal part usage
- Graph-based propagation anomalies

Uses statistical methods (Z-score, IQR, moving averages) for detection.
"""

import logging
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime, timedelta
from uuid import UUID
from collections import Counter, defaultdict
import statistics

from db.supabase import db

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in equipment behavior"""

    # Thresholds
    Z_SCORE_THRESHOLD = 2.0  # Standard deviations for outlier detection
    SPIKE_MULTIPLIER = 2.5  # Activity must be 2.5x baseline to be considered spike

    def __init__(self):
        self.db = db

    async def detect_fault_frequency_anomaly(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        window_days: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Detect anomalous fault frequency using moving window analysis.

        Compares recent fault rate to historical baseline.
        """
        faults = await self.db.get_faults_by_equipment(equipment_id, window_days * 2)

        if len(faults) < 5:  # Need enough data for meaningful analysis
            return None

        # Split into recent and baseline periods
        now = datetime.now()
        cutoff = now - timedelta(days=window_days)

        recent_faults = [
            f for f in faults
            if datetime.fromisoformat(f["detected_at"].replace("Z", "+00:00")) >= cutoff
        ]
        baseline_faults = [
            f for f in faults
            if datetime.fromisoformat(f["detected_at"].replace("Z", "+00:00")) < cutoff
        ]

        if not baseline_faults:
            return None

        # Calculate rates (faults per month)
        recent_rate = len(recent_faults) / (window_days / 30.0)
        baseline_rate = len(baseline_faults) / (window_days / 30.0)

        if baseline_rate == 0:
            baseline_rate = 0.1  # Avoid division by zero

        spike_ratio = recent_rate / baseline_rate

        # Detect anomaly if recent rate significantly higher
        if spike_ratio >= self.SPIKE_MULTIPLIER:
            severity = min(spike_ratio / 5.0, 1.0)  # Normalize to 0-1
            return {
                "equipment_id": str(equipment_id),
                "anomaly_type": "fault_frequency_spike",
                "severity": round(severity, 3),
                "description": (
                    f"Fault frequency spike detected: {recent_rate:.1f} faults/month "
                    f"vs baseline {baseline_rate:.1f} faults/month ({spike_ratio:.1f}x increase)"
                ),
                "detected_at": datetime.now().isoformat(),
                "baseline_value": round(baseline_rate, 2),
                "current_value": round(recent_rate, 2),
                "deviation_percentage": round((spike_ratio - 1.0) * 100, 1)
            }

        return None

    async def detect_search_pattern_anomaly(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        window_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Detect unusual search patterns (crew pain index spike).

        Indicates crew repeatedly searching for same equipment/issue.
        """
        queries = await self.db.get_search_queries_by_equipment(
            yacht_id,
            equipment_id,
            window_days * 2
        )

        # Get equipment name for filtering
        equipment = await self.db.get_equipment_by_id(equipment_id)
        equipment_name = equipment.get("name", "").lower() if equipment else ""

        if not equipment_name:
            return None

        # Filter queries mentioning this equipment
        relevant_queries = [
            q for q in queries
            if equipment_name in q.get("query_text", "").lower()
        ]

        if len(relevant_queries) < 5:
            return None

        # Split into recent and baseline
        now = datetime.now()
        cutoff = now - timedelta(days=window_days)

        recent_queries = [
            q for q in relevant_queries
            if datetime.fromisoformat(q["created_at"].replace("Z", "+00:00")) >= cutoff
        ]
        baseline_queries = [
            q for q in relevant_queries
            if datetime.fromisoformat(q["created_at"].replace("Z", "+00:00")) < cutoff
        ]

        if not baseline_queries:
            baseline_count = 0.5  # Baseline assumption
        else:
            baseline_count = len(baseline_queries)

        recent_count = len(recent_queries)
        spike_ratio = recent_count / baseline_count if baseline_count > 0 else recent_count

        if spike_ratio >= self.SPIKE_MULTIPLIER:
            # Get unique users
            unique_users = len(set(q.get("user_id") for q in recent_queries if q.get("user_id")))

            severity = min(spike_ratio / 5.0, 1.0)
            return {
                "equipment_id": str(equipment_id),
                "anomaly_type": "unusual_search_pattern",
                "severity": round(severity, 3),
                "description": (
                    f"Crew pain index spike: {recent_count} searches in last {window_days} days "
                    f"by {unique_users} users vs baseline {baseline_count:.0f} searches "
                    f"({spike_ratio:.1f}x increase)"
                ),
                "detected_at": datetime.now().isoformat(),
                "baseline_value": baseline_count,
                "current_value": recent_count,
                "deviation_percentage": round((spike_ratio - 1.0) * 100, 1),
                "metadata": {
                    "unique_users": unique_users,
                    "search_terms": [q.get("query_text", "")[:50] for q in recent_queries[:5]]
                }
            }

        return None

    async def detect_note_creation_spike(
        self,
        equipment_id: UUID,
        window_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Detect unusual spike in note creation.

        Many notes in short time indicates crew concern.
        """
        notes = await self.db.get_notes_by_equipment(equipment_id, window_days * 2)

        if len(notes) < 3:
            return None

        # Split into recent and baseline
        now = datetime.now()
        cutoff = now - timedelta(days=window_days)

        recent_notes = [
            n for n in notes
            if datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")) >= cutoff
        ]
        baseline_notes = [
            n for n in notes
            if datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")) < cutoff
        ]

        if not baseline_notes:
            baseline_count = 0.5
        else:
            baseline_count = len(baseline_notes)

        recent_count = len(recent_notes)
        spike_ratio = recent_count / baseline_count if baseline_count > 0 else recent_count

        if spike_ratio >= self.SPIKE_MULTIPLIER:
            severity = min(spike_ratio / 5.0, 1.0)
            return {
                "equipment_id": str(equipment_id),
                "anomaly_type": "note_creation_spike",
                "severity": round(severity, 3),
                "description": (
                    f"Note creation spike: {recent_count} notes in last {window_days} days "
                    f"vs baseline {baseline_count:.0f} notes ({spike_ratio:.1f}x increase)"
                ),
                "detected_at": datetime.now().isoformat(),
                "baseline_value": baseline_count,
                "current_value": recent_count,
                "deviation_percentage": round((spike_ratio - 1.0) * 100, 1)
            }

        return None

    async def detect_part_consumption_anomaly(
        self,
        equipment_id: UUID,
        window_days: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Detect abnormal part consumption patterns.

        Sudden increase in part replacements indicates degradation.
        """
        part_usage = await self.db.get_part_usage_by_equipment(equipment_id, window_days * 2)

        if len(part_usage) < 3:
            return None

        # Count parts per time window
        now = datetime.now()
        cutoff = now - timedelta(days=window_days)

        recent_parts = []
        baseline_parts = []

        for usage in part_usage:
            completed_at = datetime.fromisoformat(usage["completed_at"].replace("Z", "+00:00"))
            parts = usage.get("parts", [])

            if completed_at >= cutoff:
                recent_parts.extend(parts)
            else:
                baseline_parts.extend(parts)

        if not baseline_parts:
            baseline_count = 0.5
        else:
            baseline_count = len(baseline_parts)

        recent_count = len(recent_parts)
        spike_ratio = recent_count / baseline_count if baseline_count > 0 else recent_count

        if spike_ratio >= self.SPIKE_MULTIPLIER:
            severity = min(spike_ratio / 5.0, 1.0)

            # Identify most frequently replaced parts
            if recent_parts:
                part_ids = [p.get("part_id") for p in recent_parts if p.get("part_id")]
                top_parts = Counter(part_ids).most_common(3)
            else:
                top_parts = []

            return {
                "equipment_id": str(equipment_id),
                "anomaly_type": "abnormal_part_consumption",
                "severity": round(severity, 3),
                "description": (
                    f"Part consumption spike: {recent_count} parts replaced in last {window_days} days "
                    f"vs baseline {baseline_count:.0f} parts ({spike_ratio:.1f}x increase)"
                ),
                "detected_at": datetime.now().isoformat(),
                "baseline_value": baseline_count,
                "current_value": recent_count,
                "deviation_percentage": round((spike_ratio - 1.0) * 100, 1),
                "metadata": {
                    "top_parts": [{"part_id": str(p[0]), "count": p[1]} for p in top_parts]
                }
            }

        return None

    async def detect_graph_propagation_anomaly(
        self,
        equipment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Detect anomalies in graph structure.

        Unusual increase in relationships may indicate cascading issues.
        """
        edges = await self.db.get_graph_edges_for_equipment(equipment_id)

        if not edges:
            return None

        # Count recent edge creation vs historical
        now = datetime.now()
        recent_cutoff = now - timedelta(days=90)

        recent_edges = [
            e for e in edges
            if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) >= recent_cutoff
        ]

        # If graph is growing rapidly, it indicates cascading relationships
        total_edges = len(edges)
        recent_edges_count = len(recent_edges)

        if total_edges >= 15 and recent_edges_count / total_edges > 0.5:
            # More than 50% of edges created recently = rapid growth
            severity = min(recent_edges_count / 20.0, 1.0)

            return {
                "equipment_id": str(equipment_id),
                "anomaly_type": "graph_propagation_anomaly",
                "severity": round(severity, 3),
                "description": (
                    f"Rapid relationship growth: {recent_edges_count} new connections in 90 days "
                    f"(total: {total_edges}). Indicates cascading issues."
                ),
                "detected_at": datetime.now().isoformat(),
                "baseline_value": total_edges - recent_edges_count,
                "current_value": total_edges,
                "deviation_percentage": round((recent_edges_count / (total_edges - recent_edges_count) - 1) * 100, 1) if total_edges > recent_edges_count else 100
            }

        return None

    async def detect_all_anomalies(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Run all anomaly detection methods and return detected anomalies.

        Args:
            yacht_id: Yacht UUID
            equipment_id: Equipment UUID

        Returns:
            List of detected anomalies
        """
        logger.info(f"Running anomaly detection for equipment {equipment_id}")

        anomalies = []

        # Run all detection methods
        fault_anomaly = await self.detect_fault_frequency_anomaly(yacht_id, equipment_id)
        if fault_anomaly:
            anomalies.append(fault_anomaly)

        search_anomaly = await self.detect_search_pattern_anomaly(yacht_id, equipment_id)
        if search_anomaly:
            anomalies.append(search_anomaly)

        note_anomaly = await self.detect_note_creation_spike(equipment_id)
        if note_anomaly:
            anomalies.append(note_anomaly)

        part_anomaly = await self.detect_part_consumption_anomaly(equipment_id)
        if part_anomaly:
            anomalies.append(part_anomaly)

        graph_anomaly = await self.detect_graph_propagation_anomaly(equipment_id)
        if graph_anomaly:
            anomalies.append(graph_anomaly)

        logger.info(f"Detected {len(anomalies)} anomalies for equipment {equipment_id}")
        return anomalies

    async def detect_yacht_anomalies(
        self,
        yacht_id: UUID
    ) -> Dict[str, Any]:
        """
        Run anomaly detection for all equipment on a yacht.

        Args:
            yacht_id: Yacht UUID

        Returns:
            Dict containing all detected anomalies grouped by equipment
        """
        logger.info(f"Running anomaly detection for yacht {yacht_id}")

        equipment_list = await self.db.get_equipment_by_yacht(yacht_id)
        all_anomalies = []

        for equipment in equipment_list:
            equipment_id = UUID(equipment["id"])
            try:
                anomalies = await self.detect_all_anomalies(yacht_id, equipment_id)
                for anomaly in anomalies:
                    anomaly["equipment_name"] = equipment.get("name", "Unknown")
                    all_anomalies.append(anomaly)
            except Exception as e:
                logger.error(f"Error detecting anomalies for equipment {equipment_id}: {e}")
                continue

        # Sort by severity
        all_anomalies.sort(key=lambda x: x["severity"], reverse=True)

        result = {
            "yacht_id": str(yacht_id),
            "total_anomalies": len(all_anomalies),
            "critical_anomalies": len([a for a in all_anomalies if a["severity"] >= 0.75]),
            "high_anomalies": len([a for a in all_anomalies if 0.5 <= a["severity"] < 0.75]),
            "moderate_anomalies": len([a for a in all_anomalies if a["severity"] < 0.5]),
            "anomalies": all_anomalies,
            "detected_at": datetime.now().isoformat()
        }

        logger.info(f"Anomaly detection complete: {len(all_anomalies)} total anomalies found")
        return result
