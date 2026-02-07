"""
Email Watcher - Scoring Engine

Phase 7h: Point-based scoring and threshold logic for link suggestions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import math

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
        'wo_id_match': 135,
        'po_id_match': 135,
        'eq_id_match': 135,
        'fault_id_match': 135,
        'uuid_match': 135,

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
        'weak_suggest': 60,     # Low confidence - show but don't highlight
        'no_suggest': 59,       # Below this, don't suggest
        'ambiguous_gap': 15,    # If top1-top2 < this, ambiguous
    }

    # ==========================================================================
    # L2.5 Hybrid Fusion Weights
    # ==========================================================================

    HYBRID_WEIGHTS = {
        'text': 0.45,      # Text match weight
        'vector': 0.35,    # Semantic vector weight
        'recency': 0.15,   # Recency decay weight
        'bias': 0.05,      # Role bias weight
    }

    RRF_K = 60             # RRF constant (typical range: 60-100)
    RRF_ALPHA = 0.7        # Fusion blending: α*weighted + (1-α)*RRF

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

        # Set base score from SCORE_TABLE based on match_reason
        for candidate in candidates:
            match_reason = candidate.get('match_reason', 'unknown')
            base_score = self.SCORE_TABLE.get(match_reason, 0)
            candidate['score'] = base_score

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

            # Open status bonus (using StatusMapper for canonical comparison)
            from services.status_mapper import StatusMapper
            status = candidate.get('status', '')
            if StatusMapper.is_wo_active(status):
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

    # ==========================================================================
    # L2.5 Hybrid Fusion Scoring
    # ==========================================================================

    def normalize_vector_score(self, raw_cosine: float, mu: float = 0.72, sigma: float = 0.05) -> float:
        """
        Logistic normalization for vector similarity scores.

        Transforms cosine similarity to [0,1] with configurable μ (center) and σ (spread).

        Args:
            raw_cosine: Raw cosine similarity from search_index (typically 0.6-0.9)
            mu: Center point for logistic (default: 0.72)
            sigma: Spread parameter (default: 0.05)

        Returns:
            Normalized score in [0, 1] range
        """
        try:
            return 1.0 / (1.0 + math.exp(-(raw_cosine - mu) / sigma))
        except (OverflowError, ZeroDivisionError):
            # Handle edge cases
            return 0.0 if raw_cosine < mu else 1.0

    def compute_hybrid_fusion_score(
        self,
        score_inputs: Dict[str, float],
        use_rrf: bool = True,
        mu: float = 0.50,
        sigma: float = 0.10
    ) -> float:
        """
        Compute hybrid fusion score from search_index signals.

        Applies normalization:
        - s_text: Clamped to [0, 1]
        - s_vector: Logistic normalization 1/(1+exp(-(s-μ)/σ))
        - s_recency: Used as-is (exponential decay from RPC)
        - s_bias: Used as-is (from search_role_bias table)

        Then blends with RRF: α·Score + (1-α)·RRF_scaled

        Args:
            score_inputs: Dict with s_text, s_vector, s_recency, s_bias, rank_text, rank_vector
            use_rrf: If True, blend weighted + RRF scores (default: True)
            mu: Center point for vector logistic (default: 0.72)
            sigma: Spread for vector logistic (default: 0.05)

        Returns:
            Fused score in [0, 1] range
        """
        # Get weights
        w_text = self.HYBRID_WEIGHTS['text']
        w_vector = self.HYBRID_WEIGHTS['vector']
        w_recency = self.HYBRID_WEIGHTS['recency']
        w_bias = self.HYBRID_WEIGHTS['bias']

        # Get raw scores
        s_text_raw = score_inputs.get('s_text', 0.0)
        s_vector_raw = score_inputs.get('s_vector', 0.0)
        s_recency = score_inputs.get('s_recency', 0.0)
        s_bias = score_inputs.get('s_bias', 0.5)

        # Normalize s_text: clamp to [0, 1]
        s_text = max(0.0, min(1.0, s_text_raw))

        # Normalize s_vector: logistic transformation
        s_vector = self.normalize_vector_score(s_vector_raw, mu=mu, sigma=sigma)

        # Compute weighted fusion
        weighted_score = (
            w_text * s_text +
            w_vector * s_vector +
            w_recency * s_recency +
            w_bias * s_bias
        )

        if not use_rrf:
            return weighted_score

        # RRF blending
        rank_text = score_inputs.get('rank_text', 999999)
        rank_vector = score_inputs.get('rank_vector', 999999)

        rrf_score = (
            1.0 / (self.RRF_K + rank_text) +
            1.0 / (self.RRF_K + rank_vector)
        )

        # Normalize RRF to [0, 1]
        # Max possible RRF score is 2/(K+1) when rank=1 for both
        rrf_max = 2.0 / (self.RRF_K + 1)
        rrf_scaled = min(rrf_score / rrf_max, 1.0)

        # Blend: α * weighted + (1-α) * RRF
        final_score = self.RRF_ALPHA * weighted_score + (1 - self.RRF_ALPHA) * rrf_scaled

        return final_score

    def scale_hybrid_score_to_points(self, fusion_score: float) -> int:
        """
        Scale hybrid fusion score [0, 1] to point system [0, 150].

        Maps to our threshold system:
        - 0.87+ → 130+ (auto-confirm)
        - 0.67-0.86 → 100-129 (strong suggest)
        - 0.47-0.66 → 70-99 (weak suggest)
        - <0.47 → <70 (no suggest)

        Args:
            fusion_score: Score in [0, 1] from compute_hybrid_fusion_score()

        Returns:
            Point score in [0, 150] range
        """
        # Linear scaling with cap
        point_score = int(fusion_score * 150)
        return min(point_score, 150)

    def score_hybrid_candidates(
        self,
        candidates: List[Dict[str, Any]],
        use_rrf: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Score candidates from L2.5 hybrid search using fusion.

        Args:
            candidates: Candidates from find_search_index_candidates()
            use_rrf: Whether to use RRF blending (default: True)

        Returns:
            Scored candidates with 'score' field set
        """
        for candidate in candidates:
            score_inputs = candidate.get('score_inputs', {})

            if score_inputs:
                # Compute fusion score with normalization + RRF
                fusion_score = self.compute_hybrid_fusion_score(score_inputs, use_rrf=use_rrf)

                # Scale to point system
                candidate['score'] = self.scale_hybrid_score_to_points(fusion_score)

                # Store fusion score for transparency
                candidate['fusion_score'] = fusion_score

                # Update match reason to indicate hybrid
                candidate['match_reason'] = 'hybrid_search_index'

                # Build breakdown
                candidate['score_breakdown'] = {
                    'base_reason': 'hybrid_fusion',
                    'fusion_score': fusion_score,
                    'score_inputs': score_inputs,
                    'weights': self.HYBRID_WEIGHTS,
                    'total': candidate['score']
                }
            else:
                # Fallback if score_inputs missing
                candidate['score'] = 0

        # Sort by score descending
        candidates = sorted(candidates, key=lambda x: x.get('score', 0), reverse=True)

        return candidates


# Export
__all__ = ['ScoringEngine']
