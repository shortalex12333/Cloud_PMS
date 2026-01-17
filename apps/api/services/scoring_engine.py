"""
Email Watcher - Scoring Engine

Phase 7h: Point-based scoring and threshold logic for link suggestions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Score and rank candidate link suggestions.

    Uses point-based system with defined thresholds:
    - 130+: Auto-confirm (L1 hard match)
    - 100-129: Strong suggestion
    - 70-99: Weak suggestion
    - <70: Don't suggest
    """

    # ==========================================================================
    # Scoring Table
    # ==========================================================================

    SCORE_TABLE = {
        # Hard signals (safe to auto-confirm)
        'wo_id_match': 120,
        'po_id_match': 120,
        'eq_id_match': 120,
        'fault_id_match': 120,
        'uuid_match': 120,

        # Strong signals
        'part_number_match': 70,
        'serial_match': 70,
        'oem_number_match': 60,
        'attachment_wo_id': 90,
        'attachment_po_id': 90,

        # Context signals
        'vendor_email_match': 45,
        'vendor_hash_match': 45,
        'vendor_domain_match': 30,
        'equipment_wo_link': 35,
        'procurement_keywords': 25,
        'service_keywords': 25,
        'equipment_name_match': 20,

        # Recency/state signals
        'object_updated_7d': 15,
        'object_is_open': 20,
        'vendor_affinity': 15,  # Learned from history
    }

    # ==========================================================================
    # Decision Thresholds
    # ==========================================================================

    THRESHOLDS = {
        'auto_confirm': 130,    # L1 hard match - deterministic linking
        'strong_suggest': 100,  # High confidence suggestion
        'weak_suggest': 70,     # Low confidence - show but don't highlight
        'no_suggest': 69,       # Below this, don't suggest
        'ambiguous_gap': 15,    # If top1-top2 < this, ambiguous
    }

    def __init__(self):
        """Initialize scoring engine."""
        pass

    def score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Score and rank candidates.

        Args:
            candidates: List of candidate objects from CandidateFinder
            context: Optional context for bonus scoring (recency, state, etc.)

        Returns:
            Scored and sorted candidates (highest first)
        """
        if not candidates:
            return []

        # Apply bonus scoring based on context
        if context:
            candidates = self._apply_context_bonuses(candidates, context)

        # Sort by score descending
        scored = sorted(candidates, key=lambda x: x.get('score', 0), reverse=True)

        # Check for ambiguity between top candidates
        if len(scored) >= 2:
            gap = scored[0].get('score', 0) - scored[1].get('score', 0)
            if gap < self.THRESHOLDS['ambiguous_gap']:
                scored[0]['ambiguous'] = True
                scored[1]['ambiguous'] = True

        # Add score breakdown
        for candidate in scored:
            candidate['score_breakdown'] = self._build_score_breakdown(candidate)

        return scored

    def _apply_context_bonuses(
        self,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply context-based bonus scores.

        Args:
            candidates: List of candidates
            context: Context info (vendor_affinity, etc.)

        Returns:
            Candidates with updated scores
        """
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)

        for candidate in candidates:
            bonuses = []

            # Recency bonus: object updated in last 7 days
            updated_at = candidate.get('updated_at')
            if updated_at:
                try:
                    if isinstance(updated_at, str):
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        updated = updated.replace(tzinfo=None)
                    else:
                        updated = updated_at

                    if updated > seven_days_ago:
                        bonus = self.SCORE_TABLE['object_updated_7d']
                        candidate['score'] = candidate.get('score', 0) + bonus
                        bonuses.append(('object_updated_7d', bonus))
                except:
                    pass

            # Open status bonus
            status = candidate.get('status', '').lower()
            if status in ('open', 'in_progress', 'pending'):
                bonus = self.SCORE_TABLE['object_is_open']
                candidate['score'] = candidate.get('score', 0) + bonus
                bonuses.append(('object_is_open', bonus))

            # Vendor affinity bonus (learned)
            vendor_affinity = context.get('vendor_affinity', {})
            object_type = candidate.get('object_type')
            if object_type in vendor_affinity:
                affinity_score = vendor_affinity[object_type]
                if affinity_score > 0:
                    bonus = min(affinity_score, self.SCORE_TABLE['vendor_affinity'])
                    candidate['score'] = candidate.get('score', 0) + bonus
                    bonuses.append(('vendor_affinity', bonus))

            candidate['bonuses'] = bonuses

        return candidates

    def _build_score_breakdown(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build score breakdown for transparency.

        Args:
            candidate: Scored candidate

        Returns:
            Score breakdown dictionary
        """
        match_reason = candidate.get('match_reason', 'unknown')
        base_score = self.SCORE_TABLE.get(match_reason, 0)

        breakdown = {
            'base_reason': match_reason,
            'base_score': base_score,
            'bonuses': candidate.get('bonuses', []),
            'total': candidate.get('score', 0)
        }

        return breakdown

    def select_primary(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Select primary object based on scoring rules.

        Args:
            candidates: Scored and sorted candidates

        Returns:
            Selection result or None
        """
        if not candidates:
            return None

        top = candidates[0]
        score = top.get('score', 0)

        # Check thresholds
        if score >= self.THRESHOLDS['auto_confirm']:
            return {
                'candidate': top,
                'confidence': 'deterministic',
                'action': 'auto_link',
                'level': 'L1'
            }

        if score >= self.THRESHOLDS['strong_suggest']:
            if top.get('ambiguous'):
                return {
                    'candidate': top,
                    'candidates': candidates[:3],  # Include top 3 for user choice
                    'confidence': 'suggested',
                    'action': 'require_user',
                    'level': 'L2_ambiguous'
                }
            return {
                'candidate': top,
                'confidence': 'suggested',
                'action': 'suggest',
                'level': 'L2'
            }

        if score >= self.THRESHOLDS['weak_suggest']:
            return {
                'candidate': top,
                'candidates': candidates[:3],
                'confidence': 'suggested',
                'action': 'weak_suggest',
                'level': 'L3'
            }

        # Below threshold - don't suggest
        return None

    def get_confidence_level(self, score: int) -> str:
        """
        Get confidence level label for a score.

        Args:
            score: Candidate score

        Returns:
            Confidence level string
        """
        if score >= self.THRESHOLDS['auto_confirm']:
            return 'deterministic'
        elif score >= self.THRESHOLDS['strong_suggest']:
            return 'high'
        elif score >= self.THRESHOLDS['weak_suggest']:
            return 'low'
        else:
            return 'none'

    def should_create_suggestion(self, score: int) -> bool:
        """
        Check if score warrants creating a suggestion.

        Args:
            score: Candidate score

        Returns:
            True if suggestion should be created
        """
        return score >= self.THRESHOLDS['weak_suggest']

    def should_auto_confirm(self, score: int) -> bool:
        """
        Check if score warrants auto-confirmation.

        Args:
            score: Candidate score

        Returns:
            True if should auto-confirm
        """
        return score >= self.THRESHOLDS['auto_confirm']


# Export
__all__ = ['ScoringEngine']
