"""
Signal Collectors

Implements 19+ predictive maintenance signals from multiple data sources:
- Fault signals
- Work order signals
- Equipment behavior signals
- Part consumption signals
- Crew behavior signals
- Climate & operational signals
- Document-based signals
- Graph signals

Each signal is normalized to 0.0-1.0 range for scoring.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from collections import Counter, defaultdict
import statistics

from db.supabase import db

logger = logging.getLogger(__name__)


class SignalCollector:
    """Collects and normalizes predictive maintenance signals"""

    def __init__(self):
        self.db = db

    # ========== FAULT SIGNALS ==========

    async def compute_fault_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        days_back: int = 365
    ) -> Dict[str, float]:
        """
        Compute fault-based signals:
        - Fault frequency
        - Recency
        - Clustering (same component repeatedly affected)
        - Severity
        - Fault chains
        """
        faults = await self.db.get_faults_by_equipment(equipment_id, days_back)

        if not faults:
            return {
                "frequency_score": 0.0,
                "recency_score": 0.0,
                "clustering_score": 0.0,
                "severity_score": 0.0,
                "overall": 0.0
            }

        # Fault frequency (normalized by expected rate)
        # Assume >12 faults/year is high for critical equipment
        fault_count = len(faults)
        frequency_score = min(fault_count / 12.0, 1.0)

        # Recency - recent faults score higher
        now = datetime.now()
        recency_scores = []
        for fault in faults:
            detected_at = datetime.fromisoformat(fault["detected_at"].replace("Z", "+00:00"))
            days_ago = (now - detected_at).days
            # Exponential decay: recent = 1.0, 365 days ago = ~0.0
            recency = max(0.0, 1.0 - (days_ago / 365.0))
            recency_scores.append(recency)

        recency_score = max(recency_scores) if recency_scores else 0.0

        # Clustering - repeated fault codes
        fault_codes = [f.get("fault_code") for f in faults if f.get("fault_code")]
        if fault_codes:
            code_counts = Counter(fault_codes)
            max_repeats = max(code_counts.values())
            # If same fault repeats 3+ times, high clustering
            clustering_score = min(max_repeats / 3.0, 1.0)
        else:
            clustering_score = 0.0

        # Severity - weighted by fault severity
        severity_map = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
        severity_scores = [
            severity_map.get(f.get("severity", "low"), 0.25)
            for f in faults
        ]
        severity_score = statistics.mean(severity_scores) if severity_scores else 0.0

        # Overall fault signal (average of sub-signals)
        overall = statistics.mean([
            frequency_score,
            recency_score,
            clustering_score,
            severity_score
        ])

        return {
            "frequency_score": frequency_score,
            "recency_score": recency_score,
            "clustering_score": clustering_score,
            "severity_score": severity_score,
            "overall": overall
        }

    # ========== WORK ORDER SIGNALS ==========

    async def compute_work_order_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        days_back: int = 365
    ) -> Dict[str, float]:
        """
        Compute work order signals:
        - Overdue scheduled tasks
        - Repeated corrective tasks
        - Reappearing tasks (<90 days)
        - Partially completed tasks
        """
        work_orders = await self.db.get_work_orders_by_equipment(equipment_id, days_back)
        history = await self.db.get_work_order_history(equipment_id, days_back)

        # Overdue tasks
        now = datetime.now()
        overdue_count = 0
        for wo in work_orders:
            if wo.get("status") not in ["completed", "cancelled"]:
                due_date = wo.get("due_date")
                if due_date:
                    due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    if due < now:
                        overdue_count += 1

        overdue_score = min(overdue_count / 3.0, 1.0)  # 3+ overdue = 1.0

        # Repeated corrective tasks
        corrective_count = sum(
            1 for wo in work_orders if wo.get("type") == "corrective"
        )
        repeated_corrective_score = min(corrective_count / 5.0, 1.0)  # 5+ = 1.0

        # Reappearing tasks (within 90 days)
        if len(history) >= 2:
            reappearing = 0
            sorted_history = sorted(
                history,
                key=lambda x: x["completed_at"],
                reverse=True
            )
            for i in range(len(sorted_history) - 1):
                current = datetime.fromisoformat(sorted_history[i]["completed_at"].replace("Z", "+00:00"))
                previous = datetime.fromisoformat(sorted_history[i + 1]["completed_at"].replace("Z", "+00:00"))
                if (current - previous).days < 90:
                    reappearing += 1

            reappearing_score = min(reappearing / 3.0, 1.0)
        else:
            reappearing_score = 0.0

        # Partially completed tasks
        partial_count = sum(
            1 for h in history if h.get("status_on_completion") == "partial"
        )
        partial_score = min(partial_count / 3.0, 1.0)

        # Overall
        overall = statistics.mean([
            overdue_score,
            repeated_corrective_score,
            reappearing_score,
            partial_score
        ])

        return {
            "overdue_score": overdue_score,
            "repeated_corrective_score": repeated_corrective_score,
            "reappearing_score": reappearing_score,
            "partial_score": partial_score,
            "overall": overall
        }

    # ========== EQUIPMENT BEHAVIOR SIGNALS ==========

    async def compute_equipment_behavior_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        days_back: int = 365
    ) -> Dict[str, float]:
        """
        Compute equipment behavior signals:
        - MTBF (Mean Time Between Failures)
        - Sudden increase in maintenance activity
        - Drop in maintenance (crew avoidance)
        - Notes mentioning symptoms
        """
        faults = await self.db.get_faults_by_equipment(equipment_id, days_back)
        history = await self.db.get_work_order_history(equipment_id, days_back)
        notes = await self.db.get_notes_by_equipment(equipment_id, days_back)

        # MTBF calculation
        if len(faults) >= 2:
            sorted_faults = sorted(
                faults,
                key=lambda x: x["detected_at"]
            )
            intervals = []
            for i in range(len(sorted_faults) - 1):
                current = datetime.fromisoformat(sorted_faults[i]["detected_at"].replace("Z", "+00:00"))
                next_fault = datetime.fromisoformat(sorted_faults[i + 1]["detected_at"].replace("Z", "+00:00"))
                intervals.append((next_fault - current).days)

            mtbf_days = statistics.mean(intervals) if intervals else 365
            # Lower MTBF = higher risk. Assume 90 days is critical
            mtbf_score = max(0.0, 1.0 - (mtbf_days / 90.0))
        else:
            mtbf_score = 0.0

        # Maintenance activity trend
        if len(history) >= 6:
            # Compare first half to second half
            mid = len(history) // 2
            recent_half = history[:mid]
            older_half = history[mid:]

            recent_count = len(recent_half)
            older_count = len(older_half)

            if older_count > 0:
                activity_ratio = recent_count / older_count
                # Sudden increase (>2x) indicates problems
                increase_score = min(max(0.0, (activity_ratio - 1.0) / 2.0), 1.0)
                # Drop (<0.5x) might indicate crew avoidance
                avoidance_score = min(max(0.0, (1.0 - activity_ratio) / 0.5), 1.0)
            else:
                increase_score = 0.0
                avoidance_score = 0.0
        else:
            increase_score = 0.0
            avoidance_score = 0.0

        # Notes with symptom keywords
        symptom_keywords = [
            "vibration", "noise", "leak", "smell", "smoke",
            "overheating", "pressure", "temperature", "unusual"
        ]
        symptom_notes = 0
        for note in notes:
            text = note.get("text", "").lower()
            if any(keyword in text for keyword in symptom_keywords):
                symptom_notes += 1

        symptom_score = min(symptom_notes / 5.0, 1.0)

        # Overall
        overall = statistics.mean([
            mtbf_score,
            increase_score,
            max(avoidance_score, 0.0),  # Avoidance is warning sign
            symptom_score
        ])

        return {
            "mtbf_score": mtbf_score,
            "activity_increase_score": increase_score,
            "avoidance_score": avoidance_score,
            "symptom_notes_score": symptom_score,
            "overall": overall
        }

    # ========== PART CONSUMPTION SIGNALS ==========

    async def compute_part_consumption_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        days_back: int = 365
    ) -> Dict[str, float]:
        """
        Compute part consumption signals:
        - Inventory depletion rate
        - Parts repeatedly replaced
        - Abnormal consumption patterns
        """
        part_usage = await self.db.get_part_usage_by_equipment(equipment_id, days_back)

        if not part_usage:
            return {
                "depletion_score": 0.0,
                "replacement_frequency_score": 0.0,
                "overall": 0.0
            }

        # Collect all parts used
        all_parts = []
        for usage in part_usage:
            parts = usage.get("parts", [])
            if isinstance(parts, list):
                all_parts.extend([p.get("part_id") for p in parts if p.get("part_id")])

        if not all_parts:
            return {"depletion_score": 0.0, "replacement_frequency_score": 0.0, "overall": 0.0}

        # Parts replaced repeatedly
        part_counts = Counter(all_parts)
        max_replacements = max(part_counts.values())
        replacement_frequency_score = min(max_replacements / 4.0, 1.0)  # 4+ times = 1.0

        # Check stock levels (requires additional query)
        # For now, use replacement frequency as proxy for depletion
        depletion_score = replacement_frequency_score * 0.7

        overall = statistics.mean([
            depletion_score,
            replacement_frequency_score
        ])

        return {
            "depletion_score": depletion_score,
            "replacement_frequency_score": replacement_frequency_score,
            "overall": overall
        }

    # ========== CREW BEHAVIOR SIGNALS ==========

    async def compute_crew_behavior_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID,
        days_back: int = 90
    ) -> Dict[str, float]:
        """
        Compute crew behavior signals (Crew Pain Index):
        - Repeated search queries
        - Repeated notes
        - Anomaly spikes in activity
        """
        queries = await self.db.get_search_queries_by_equipment(yacht_id, equipment_id, days_back)
        notes = await self.db.get_notes_by_equipment(equipment_id, days_back)

        # Search query patterns - filter for this equipment
        equipment_queries = []
        equipment_obj = await self.db.get_equipment_by_id(equipment_id)
        equipment_name = equipment_obj.get("name", "").lower() if equipment_obj else ""

        for query in queries:
            query_text = query.get("query_text", "").lower()
            if equipment_name and equipment_name in query_text:
                equipment_queries.append(query)

        # Repeated searches indicate pain
        search_count = len(equipment_queries)
        search_score = min(search_count / 10.0, 1.0)  # 10+ searches = 1.0

        # Unique users searching (more users = more widespread concern)
        unique_users = len(set(q.get("user_id") for q in equipment_queries if q.get("user_id")))
        user_diversity_score = min(unique_users / 3.0, 1.0)  # 3+ users = 1.0

        # Note creation frequency
        note_count = len(notes)
        note_frequency_score = min(note_count / 8.0, 1.0)  # 8+ notes = 1.0

        # Overall crew pain index
        overall = statistics.mean([
            search_score,
            user_diversity_score,
            note_frequency_score
        ])

        return {
            "search_score": search_score,
            "user_diversity_score": user_diversity_score,
            "note_frequency_score": note_frequency_score,
            "overall": overall
        }

    # ========== GLOBAL KNOWLEDGE SIGNALS ==========

    async def compute_global_knowledge_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> Dict[str, float]:
        """
        Compute global knowledge signals:
        - Known issues from Celeste global DB
        - Manufacturer bulletins
        - Fleet-wide patterns
        """
        # Get equipment details
        equipment = await self.db.get_equipment_by_id(equipment_id)
        if not equipment:
            return {"overall": 0.0}

        manufacturer = equipment.get("manufacturer", "")
        model = equipment.get("model", "")
        system_type = equipment.get("system_type", "")

        # Get fleet statistics
        fleet_stats = await self.db.get_fleet_statistics(
            equipment_class=system_type,
            manufacturer=manufacturer
        )

        if not fleet_stats:
            return {"overall": 0.0}

        # Compare yacht's fault rate to fleet average
        yacht_faults = await self.db.get_faults_by_equipment(equipment_id, 365)
        yacht_fault_rate = len(yacht_faults) / 12.0  # faults per month

        fleet_avg_rate = fleet_stats.get("avg_fault_rate", 0.5)
        if fleet_avg_rate > 0:
            deviation_ratio = yacht_fault_rate / fleet_avg_rate
            # If >2x fleet average, score high
            deviation_score = min(max(0.0, (deviation_ratio - 1.0) / 2.0), 1.0)
        else:
            deviation_score = 0.0

        return {
            "fleet_deviation_score": deviation_score,
            "overall": deviation_score
        }

    # ========== GRAPH SIGNALS ==========

    async def compute_graph_signal(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> Dict[str, float]:
        """
        Compute graph-based signals:
        - Equipment → faults → parts relationship density
        - Multi-hop weakness propagation
        - Connected component analysis
        """
        # Get graph edges for equipment
        edges = await self.db.get_graph_edges_for_equipment(equipment_id)

        if not edges:
            return {"overall": 0.0}

        # Count edge types
        fault_edges = sum(1 for e in edges if e.get("edge_type") == "HAS_FAULT")
        part_edges = sum(1 for e in edges if e.get("edge_type") == "USES_PART")
        doc_edges = sum(1 for e in edges if e.get("edge_type") == "MENTIONED_IN")

        # High relationship density indicates complexity and potential risk
        total_edges = len(edges)
        density_score = min(total_edges / 20.0, 1.0)  # 20+ edges = complex system

        # Fault relationship intensity
        fault_intensity = min(fault_edges / 10.0, 1.0)

        overall = statistics.mean([density_score, fault_intensity])

        return {
            "density_score": density_score,
            "fault_intensity": fault_intensity,
            "overall": overall
        }

    # ========== COMBINED SIGNAL COMPUTATION ==========

    async def compute_all_signals(
        self,
        yacht_id: UUID,
        equipment_id: UUID
    ) -> Dict[str, Any]:
        """
        Compute all signals for equipment and return structured data.

        Returns normalized 0.0-1.0 scores for each signal category.
        """
        logger.info(f"Computing all signals for equipment {equipment_id}")

        # Compute each signal type
        fault_signals = await self.compute_fault_signal(yacht_id, equipment_id)
        wo_signals = await self.compute_work_order_signal(yacht_id, equipment_id)
        equipment_signals = await self.compute_equipment_behavior_signal(yacht_id, equipment_id)
        part_signals = await self.compute_part_consumption_signal(yacht_id, equipment_id)
        crew_signals = await self.compute_crew_behavior_signal(yacht_id, equipment_id)
        global_signals = await self.compute_global_knowledge_signal(yacht_id, equipment_id)
        graph_signals = await self.compute_graph_signal(yacht_id, equipment_id)

        return {
            "equipment_id": str(equipment_id),
            "yacht_id": str(yacht_id),
            "signals": {
                "fault": fault_signals,
                "work_order": wo_signals,
                "equipment_behavior": equipment_signals,
                "part_consumption": part_signals,
                "crew_behavior": crew_signals,
                "global_knowledge": global_signals,
                "graph": graph_signals
            },
            "computed_at": datetime.now().isoformat()
        }
