"""
Confidence Threshold Governance - Email Link Suggestions
=========================================================

LOCKED FOR MVP - DO NOT CHANGE WITHOUT EXPLICIT APPROVAL

This module defines:
1. Confidence thresholds for link suggestions
2. Behaviour at each confidence level
3. Logging requirements
4. Future tunability hooks

RULES:
- Too aggressive → wrong links → loss of trust
- Too conservative → feels dumb
- MVP: Conservative bias (manual confirmation preferred)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIDENCE LEVELS (LOCKED)
# =============================================================================

class ConfidenceLevel(Enum):
    """
    Confidence levels for link suggestions.

    LOCKED VALUES - do not modify without explicit approval.
    """
    DETERMINISTIC = "deterministic"   # 100% certain (exact ID match)
    HIGH = "high"                     # 85%+ certain
    MEDIUM = "medium"                 # 60-84% certain
    LOW = "low"                       # 30-59% certain
    NONE = "none"                     # <30% or no signal


# =============================================================================
# THRESHOLDS (LOCKED)
# =============================================================================

@dataclass(frozen=True)
class ConfidenceThresholds:
    """
    MVP confidence thresholds.

    LOCKED - these values define ship-side behaviour.
    """

    # Score thresholds (0-100 scale)
    DETERMINISTIC_MIN: int = 100  # Exact pattern match only
    HIGH_MIN: int = 85            # Multiple strong signals
    MEDIUM_MIN: int = 60          # Single strong signal
    LOW_MIN: int = 30             # Weak signal
    NONE_MAX: int = 29            # Below this = no suggestion

    # Behavioural thresholds
    AUTO_SUGGEST_MIN: int = 60    # Show in suggestions panel
    ONE_CLICK_CONFIRM_MIN: int = 85  # Allow one-click accept
    REQUIRE_MANUAL_MAX: int = 59  # Require manual selection
    SUPPRESS_BELOW: int = 30      # Don't show at all


# Global locked thresholds
THRESHOLDS = ConfidenceThresholds()


# =============================================================================
# CONFIDENCE BEHAVIOURS
# =============================================================================

@dataclass
class LinkSuggestionBehaviour:
    """Defines UI/UX behaviour for a confidence level."""
    show_in_panel: bool           # Show in Related panel
    allow_one_click: bool         # Allow single-click confirm
    require_selection: bool       # Require dropdown selection
    show_confidence: bool         # Show confidence indicator
    highlight_uncertainty: bool   # Add visual uncertainty cue


CONFIDENCE_BEHAVIOURS = {
    ConfidenceLevel.DETERMINISTIC: LinkSuggestionBehaviour(
        show_in_panel=True,
        allow_one_click=True,
        require_selection=False,
        show_confidence=False,     # Don't show - it's obvious
        highlight_uncertainty=False,
    ),

    ConfidenceLevel.HIGH: LinkSuggestionBehaviour(
        show_in_panel=True,
        allow_one_click=True,
        require_selection=False,
        show_confidence=True,      # Show confidence
        highlight_uncertainty=False,
    ),

    ConfidenceLevel.MEDIUM: LinkSuggestionBehaviour(
        show_in_panel=True,
        allow_one_click=False,     # Require explicit confirm
        require_selection=False,
        show_confidence=True,
        highlight_uncertainty=True,  # Visual cue
    ),

    ConfidenceLevel.LOW: LinkSuggestionBehaviour(
        show_in_panel=True,
        allow_one_click=False,
        require_selection=True,    # Require selection
        show_confidence=True,
        highlight_uncertainty=True,
    ),

    ConfidenceLevel.NONE: LinkSuggestionBehaviour(
        show_in_panel=False,       # Don't show
        allow_one_click=False,
        require_selection=True,
        show_confidence=False,
        highlight_uncertainty=False,
    ),
}


# =============================================================================
# CONFIDENCE CALCULATOR
# =============================================================================

def calculate_confidence_level(score: int) -> ConfidenceLevel:
    """
    Convert numeric score to confidence level.

    Args:
        score: 0-100 confidence score

    Returns:
        ConfidenceLevel enum
    """
    if score >= THRESHOLDS.DETERMINISTIC_MIN:
        return ConfidenceLevel.DETERMINISTIC
    elif score >= THRESHOLDS.HIGH_MIN:
        return ConfidenceLevel.HIGH
    elif score >= THRESHOLDS.MEDIUM_MIN:
        return ConfidenceLevel.MEDIUM
    elif score >= THRESHOLDS.LOW_MIN:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.NONE


def get_suggestion_behaviour(score: int) -> LinkSuggestionBehaviour:
    """Get UI behaviour for a confidence score."""
    level = calculate_confidence_level(score)
    return CONFIDENCE_BEHAVIOURS[level]


def should_show_suggestion(score: int) -> bool:
    """Determine if suggestion should be shown."""
    return score >= THRESHOLDS.AUTO_SUGGEST_MIN


def allows_one_click_confirm(score: int) -> bool:
    """Determine if one-click confirm is allowed."""
    return score >= THRESHOLDS.ONE_CLICK_CONFIRM_MIN


# =============================================================================
# SCORE CALCULATION
# =============================================================================

@dataclass
class ScoringSignal:
    """A single scoring signal."""
    signal_type: str
    value: int
    reason: str


class LinkScorer:
    """
    Calculate confidence scores for link suggestions.

    Scoring rules (LOCKED):
    - Exact ID match in subject: +100 (deterministic)
    - ID pattern in body: +50
    - Vendor domain match: +30
    - Recent time proximity: +15
    - Keyword overlap: +10
    - Attachment signal: +10
    """

    SIGNAL_WEIGHTS = {
        "exact_id_subject": 100,   # [WO-1234] in subject
        "exact_id_body": 50,       # WO-1234 in body
        "vendor_domain": 30,       # Sender matches supplier
        "time_proximity": 15,      # Created within 48h
        "keyword_overlap": 10,     # Shared keywords
        "attachment_signal": 10,   # Document type match
        "user_history": 20,        # Similar past links
    }

    def __init__(self):
        self.signals: List[ScoringSignal] = []

    def add_signal(self, signal_type: str, reason: str) -> None:
        """Add a scoring signal."""
        value = self.SIGNAL_WEIGHTS.get(signal_type, 0)
        self.signals.append(ScoringSignal(
            signal_type=signal_type,
            value=value,
            reason=reason
        ))

    def calculate_score(self) -> int:
        """Calculate final confidence score (capped at 100)."""
        total = sum(s.value for s in self.signals)
        return min(100, total)

    def get_breakdown(self) -> dict:
        """Get score breakdown for logging/explain."""
        return {
            "total": self.calculate_score(),
            "signals": [
                {"type": s.signal_type, "value": s.value, "reason": s.reason}
                for s in self.signals
            ]
        }


# =============================================================================
# LOGGING (REQUIRED)
# =============================================================================

def log_suggestion_decision(
    thread_id: str,
    object_type: str,
    object_id: str,
    score: int,
    level: ConfidenceLevel,
    signals: List[ScoringSignal],
    shown: bool,
    yacht_id: str
):
    """
    Log every suggestion decision.

    REQUIRED: All suggestion decisions must be logged for:
    - Debugging
    - Tuning future thresholds
    - Audit trail
    """
    logger.info(
        f"[LINK_SUGGESTION] "
        f"thread={thread_id} "
        f"object={object_type}:{object_id} "
        f"score={score} "
        f"level={level.value} "
        f"shown={shown} "
        f"signals={len(signals)} "
        f"yacht={yacht_id}"
    )


# =============================================================================
# FUTURE TUNABILITY (NOT MVP)
# =============================================================================

# These hooks exist for per-yacht tuning in future versions.
# DO NOT IMPLEMENT IN MVP - just placeholder.

def get_yacht_thresholds(yacht_id: str) -> ConfidenceThresholds:
    """
    Future: Get custom thresholds for a yacht.

    MVP: Returns global defaults.
    """
    # TODO: In future, look up yacht-specific overrides
    return THRESHOLDS


def should_enable_aggressive_suggestions(yacht_id: str) -> bool:
    """
    Future: Some yachts may opt into more aggressive suggestions.

    MVP: Always False.
    """
    return False
