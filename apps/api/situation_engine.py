"""
CelesteOS Situation Engine v1.0
================================

Thin situation detection + policy recommendation engine.
Facts come from DB (Supabase). Logic lives here.

Patterns supported (v1):
- RECURRENT_SYMPTOM: Same symptom on same equipment >= 3 times in 60 days
- RECURRENT_SYMPTOM_PRE_EVENT: Same as above, but critical event within 72h
- HIGH_RISK_EQUIPMENT: Equipment with risk_score > 0.7 mentioned

Usage:
    from situation_engine import SituationEngine, Severity

    engine = SituationEngine(supabase_client)

    situation = engine.detect_situation(
        yacht_id=yacht_id,
        resolved_entities=[
            {'type': 'equipment', 'entity_id': 'uuid', 'canonical': 'Main Engine', 'confidence': 0.9},
            {'type': 'symptom', 'canonical': 'OVERHEAT', 'confidence': 0.85}
        ],
        vessel_context={'hours_until_event': 48, 'next_event_type': 'charter'}
    )

    if situation:
        recommendations = engine.get_recommendations(situation, yacht_id, resolved_entities)
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Situation:
    """Detected situation with context and evidence."""
    type: str
    label: str
    severity: Severity
    context: Optional[str]
    evidence: List[str]

    def to_dict(self) -> Dict:
        return {
            'type': self.type,
            'label': self.label,
            'severity': self.severity.value,
            'context': self.context,
            'evidence': self.evidence
        }


@dataclass
class Recommendation:
    """Single recommended action."""
    action: str
    template: Optional[str]
    reason: str
    parts_available: bool = True
    urgency: str = "normal"

    def to_dict(self) -> Dict:
        return asdict(self)


class SituationEngine:
    """
    Thin situation detection + policy engine.
    Facts come from DB. Logic lives here.
    """

    # Palliative fix indicators (temporary fixes that don't address root cause)
    PALLIATIVE_KEYWORDS = [
        'top-up', 'top up', 'topped up', 'temporary', 'temp fix',
        'reset', 'cleared', 'silenced', 'bypassed', 'workaround',
        'pending', 'deferred', 'monitor', 'watching'
    ]

    def __init__(self, supabase_client):
        """
        Initialize with Supabase client.

        Args:
            supabase_client: Initialized Supabase client (from supabase-py)
        """
        self.db = supabase_client

    def detect_situation(
        self,
        yacht_id: str,
        resolved_entities: List[Dict],
        vessel_context: Dict
    ) -> Optional[Situation]:
        """
        Check for known patterns. Returns first match or None.

        Args:
            yacht_id: UUID of the yacht
            resolved_entities: List of resolved entities from DB resolvers
                Each entity: {type, entity_id, canonical, confidence}
            vessel_context: Dict with {hours_until_event, next_event_type, ...}

        Returns:
            Situation if pattern detected, None otherwise
        """
        if not resolved_entities:
            return None

        # Extract equipment and symptoms from resolved entities
        equipment_entities = [e for e in resolved_entities if e.get('type') == 'equipment']
        symptom_entities = [e for e in resolved_entities if e.get('type') == 'symptom']

        # Pattern 1: Recurrent symptom on equipment
        if equipment_entities and symptom_entities:
            situation = self._check_recurrent_symptom(
                yacht_id=yacht_id,
                equipment=equipment_entities[0],  # Use highest confidence
                symptom=symptom_entities[0],
                vessel_context=vessel_context
            )
            if situation:
                return situation

        # Pattern 2: High risk equipment mentioned (no symptom required)
        if equipment_entities:
            situation = self._check_high_risk_equipment(
                yacht_id=yacht_id,
                equipment=equipment_entities[0]
            )
            if situation:
                return situation

        return None

    def _check_recurrent_symptom(
        self,
        yacht_id: str,
        equipment: Dict,
        symptom: Dict,
        vessel_context: Dict
    ) -> Optional[Situation]:
        """Check for recurrent symptom pattern."""
        equipment_label = equipment.get('canonical', equipment.get('value', ''))
        symptom_code = symptom.get('canonical', symptom.get('value', ''))

        if not equipment_label or not symptom_code:
            return None

        # Call DB function to check recurrence
        try:
            result = self.db.rpc('check_symptom_recurrence', {
                'p_yacht_id': yacht_id,
                'p_equipment_label': equipment_label,
                'p_symptom_code': symptom_code,
                'p_threshold_count': 3,
                'p_threshold_days': 60
            }).execute()

            if not result.data:
                return None

            recurrence = result.data[0] if isinstance(result.data, list) else result.data

            if not recurrence.get('is_recurrent'):
                return None

            # Build evidence
            evidence = [
                f"{recurrence['occurrence_count']} {symptom_code} events in {recurrence['span_days']} days"
            ]

            # Check last fix type
            last_wo = self._get_last_wo(yacht_id, equipment_label)
            if last_wo and self._is_palliative(last_wo):
                evidence.append(f"Last fix was palliative ({last_wo.get('title', 'unknown')})")

            # Check if there are still open reports
            if recurrence.get('open_count', 0) > 0:
                evidence.append(f"{recurrence['open_count']} unresolved occurrence(s)")

            # Determine if pre-critical-event
            hours_until_event = vessel_context.get('hours_until_event')
            next_event_type = vessel_context.get('next_event_type')
            is_critical_window = (
                hours_until_event is not None and
                hours_until_event < 72 and
                next_event_type in ('charter', 'survey', 'crossing')
            )

            return Situation(
                type="RECURRENT_SYMPTOM_PRE_EVENT" if is_critical_window else "RECURRENT_SYMPTOM",
                label=f"{equipment_label} {symptom_code} (recurring)",
                severity=Severity.HIGH if is_critical_window else Severity.MEDIUM,
                context=f"{next_event_type.title()} in {int(hours_until_event)}h" if is_critical_window else None,
                evidence=evidence
            )

        except Exception as e:
            logger.error(f"Error checking symptom recurrence: {e}")
            return None

    def _check_high_risk_equipment(
        self,
        yacht_id: str,
        equipment: Dict
    ) -> Optional[Situation]:
        """Check if equipment has elevated risk score."""
        equipment_id = equipment.get('entity_id')
        equipment_label = equipment.get('canonical', equipment.get('value', ''))

        if not equipment_id:
            return None

        try:
            # Query predictive_state for risk score
            result = self.db.table('predictive_state').select('risk_score, confidence').eq(
                'equipment_id', equipment_id
            ).single().execute()

            if not result.data:
                return None

            risk_score = result.data.get('risk_score', 0)
            confidence = result.data.get('confidence', 0)

            if risk_score < 0.7:
                return None

            return Situation(
                type="HIGH_RISK_EQUIPMENT",
                label=f"{equipment_label} at elevated risk",
                severity=Severity.HIGH if risk_score > 0.85 else Severity.MEDIUM,
                context=None,
                evidence=[
                    f"Risk score: {risk_score:.0%}",
                    f"Confidence: {confidence:.0%}"
                ]
            )

        except Exception as e:
            logger.warning(f"Error checking equipment risk (may not have predictive_state): {e}")
            return None

    def get_recommendations(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict],
        user_role: str = "crew"
    ) -> List[Recommendation]:
        """
        Get recommended actions for a detected situation.
        Role-aware policies for v1.

        Args:
            situation: Detected situation
            yacht_id: UUID of the yacht
            resolved_entities: List of resolved entities
            user_role: User role (captain, chief_engineer, engineer, crew, management)

        Returns:
            Ordered list of recommended actions tailored to user role
        """
        if situation is None:
            return []

        # Branch by role: captain/management get high-level recs, engineers get actionable recs
        if user_role in ("captain", "management"):
            return self._get_recommendations_for_captain(situation, yacht_id, resolved_entities)
        else:
            return self._get_recommendations_for_engineering(situation, yacht_id, resolved_entities)

    def _get_recommendations_for_engineering(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Engineering-focused recommendations: actionable WOs and diagnostics."""
        if situation.type in ("RECURRENT_SYMPTOM", "RECURRENT_SYMPTOM_PRE_EVENT"):
            return self._policy_recurrent_symptom_engineering(situation, yacht_id, resolved_entities)

        if situation.type == "HIGH_RISK_EQUIPMENT":
            return self._policy_high_risk_engineering(situation, yacht_id, resolved_entities)

        return []

    def _get_recommendations_for_captain(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Captain/management-focused recommendations: risk framing and coordination."""
        if situation.type in ("RECURRENT_SYMPTOM", "RECURRENT_SYMPTOM_PRE_EVENT"):
            return self._policy_recurrent_symptom_captain(situation, yacht_id, resolved_entities)

        if situation.type == "HIGH_RISK_EQUIPMENT":
            return self._policy_high_risk_captain(situation, yacht_id, resolved_entities)

        return []

    def _policy_recurrent_symptom_engineering(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Engineering policy for recurrent symptom situations."""
        recommendations = []

        # Primary action: Create root cause investigation WO
        recommendations.append(Recommendation(
            action="create_work_order",
            template="inspection_root_cause",
            reason="Recurring issue suggests underlying cause not addressed",
            parts_available=True,  # TODO: Check inventory
            urgency="urgent" if situation.severity == Severity.HIGH else "normal"
        ))

        # If pre-event critical window, add diagnostic
        if situation.type == "RECURRENT_SYMPTOM_PRE_EVENT":
            recommendations.append(Recommendation(
                action="run_diagnostic",
                template=None,
                reason="Verify system health before critical period",
                urgency="high"
            ))

            # Also suggest monitoring
            recommendations.append(Recommendation(
                action="configure_alert",
                template=None,
                reason="Lower alert thresholds during critical period",
                urgency="normal"
            ))

        return recommendations

    def _policy_recurrent_symptom_captain(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Captain policy for recurrent symptom situations."""
        recommendations = []

        # Risk assessment and coordination
        if situation.type == "RECURRENT_SYMPTOM_PRE_EVENT":
            recommendations.append(Recommendation(
                action="review_charter_risk",
                template=None,
                reason="Recurring issue before charter - assess operational risk",
                urgency="high"
            ))
            recommendations.append(Recommendation(
                action="coordinate_with_engineering",
                template=None,
                reason="Confirm engineering team has root cause investigation underway",
                urgency="high"
            ))
        else:
            recommendations.append(Recommendation(
                action="review_maintenance_status",
                template=None,
                reason="Recurring issue - review with chief engineer",
                urgency="normal"
            ))

        # For high severity, suggest contingency planning
        if situation.severity == Severity.HIGH:
            recommendations.append(Recommendation(
                action="prepare_contingency",
                template=None,
                reason="High-severity recurring issue - consider backup plans",
                urgency="elevated"
            ))

        return recommendations

    def _policy_high_risk_engineering(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Engineering policy for high risk equipment situations."""
        return [
            Recommendation(
                action="view_predictive_analysis",
                template=None,
                reason="Review failure modes and recommended preventive actions",
                urgency="normal"
            ),
            Recommendation(
                action="schedule_inspection",
                template="predictive_inspection",
                reason="Proactive inspection before potential failure",
                urgency="elevated" if situation.severity == Severity.HIGH else "normal"
            )
        ]

    def _policy_high_risk_captain(
        self,
        situation: Situation,
        yacht_id: str,
        resolved_entities: List[Dict]
    ) -> List[Recommendation]:
        """Captain policy for high risk equipment situations."""
        recommendations = [
            Recommendation(
                action="review_risk_summary",
                template=None,
                reason="Equipment flagged as elevated risk - review status",
                urgency="normal"
            )
        ]

        if situation.severity == Severity.HIGH:
            recommendations.append(Recommendation(
                action="coordinate_with_engineering",
                template=None,
                reason="High-risk equipment - ensure proactive inspection scheduled",
                urgency="elevated"
            ))

        return recommendations

    def _get_last_wo(self, yacht_id: str, equipment_label: str) -> Optional[Dict]:
        """Get the most recent work order for this equipment."""
        try:
            # Query work_orders via graph_nodes relationship
            # For v1, simplified query
            result = self.db.table('graph_nodes').select(
                'id, label, properties, created_at'
            ).eq(
                'yacht_id', yacht_id
            ).eq(
                'node_type', 'work_order'
            ).ilike(
                'label', f'%{equipment_label}%'
            ).order(
                'created_at', desc=True
            ).limit(1).execute()

            if result.data:
                wo = result.data[0]
                return {
                    'id': wo.get('id'),
                    'title': wo.get('label', ''),
                    'properties': wo.get('properties', {}),
                    'created_at': wo.get('created_at')
                }
            return None

        except Exception as e:
            logger.warning(f"Error getting last WO: {e}")
            return None

    def _is_palliative(self, wo: Dict) -> bool:
        """Check if a work order was a palliative (temporary) fix."""
        title = wo.get('title', '').lower()
        properties = wo.get('properties', {})
        notes = properties.get('notes', '').lower() if properties else ''

        combined_text = f"{title} {notes}"

        return any(kw in combined_text for kw in self.PALLIATIVE_KEYWORDS)

    def log_suggestion(
        self,
        yacht_id: str,
        user_id: Optional[str],
        query_text: str,
        intent: Optional[str],
        situation: Optional[Situation],
        recommendations: List[Recommendation],
        search_query_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Log what we suggested for future learning.

        Returns:
            UUID of the suggestion log entry, or None on error
        """
        try:
            result = self.db.table('suggestion_log').insert({
                'yacht_id': yacht_id,
                'user_id': user_id,
                'query_text': query_text,
                'intent': intent,
                'search_query_id': search_query_id,
                'situation_detected': situation is not None,
                'situation_type': situation.type if situation else None,
                'situation_severity': situation.severity.value if situation else None,
                'situation_context': situation.context if situation else None,
                'suggested_actions': [r.to_dict() for r in recommendations],
                'evidence_provided': situation.evidence if situation else []
            }).execute()

            if result.data:
                return result.data[0].get('id')
            return None

        except Exception as e:
            logger.error(f"Error logging suggestion: {e}")
            return None

    def log_symptom_report(
        self,
        yacht_id: str,
        equipment_label: str,
        symptom_code: str,
        symptom_label: str,
        user_id: Optional[str] = None,
        search_query_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Log a symptom occurrence from search query.

        Returns:
            UUID of the symptom report, or None on error
        """
        try:
            result = self.db.rpc('log_symptom_from_search', {
                'p_yacht_id': yacht_id,
                'p_equipment_label': equipment_label,
                'p_symptom_code': symptom_code,
                'p_symptom_label': symptom_label,
                'p_search_query_id': search_query_id,
                'p_user_id': user_id
            }).execute()

            return result.data if result.data else None

        except Exception as e:
            logger.error(f"Error logging symptom report: {e}")
            return None


# Singleton instance (initialized on first import with valid client)
_engine_instance: Optional[SituationEngine] = None


def get_situation_engine(supabase_client=None) -> Optional[SituationEngine]:
    """
    Get or create singleton SituationEngine instance.

    Args:
        supabase_client: Supabase client (required on first call)

    Returns:
        SituationEngine instance
    """
    global _engine_instance

    if _engine_instance is None and supabase_client is not None:
        _engine_instance = SituationEngine(supabase_client)

    return _engine_instance
