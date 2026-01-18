"""
Undo, Correction & Audit Flows
===============================

CRITICAL: Wrong links happen. Recovery must be effortless.

This module defines:
1. Undo capabilities for all commit actions
2. Correction flows for wrong links
3. Audit trail for all link actions
4. "Why this suggestion?" explanations

RULE: If a user can't undo a wrong link in <3 seconds,
they'll stop trusting the system entirely.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# ACTION TYPES
# =============================================================================

class LinkActionType(Enum):
    """All link-related actions that can be undone."""

    # Creation
    LINK_CREATED = "link_created"           # Manual link created
    LINK_SUGGESTED = "link_suggested"       # System suggested, user confirmed
    LINK_AUTO = "link_auto"                 # Auto-linked (deterministic)

    # Modification
    LINK_CORRECTED = "link_corrected"       # User corrected wrong link
    LINK_REMOVED = "link_removed"           # Link deleted

    # Feedback
    SUGGESTION_DISMISSED = "suggestion_dismissed"   # User dismissed suggestion
    SUGGESTION_WRONG = "suggestion_wrong"           # User marked as wrong


# =============================================================================
# UNDO WINDOW
# =============================================================================

# LOCKED: Undo window is 30 seconds for all actions
UNDO_WINDOW_SECONDS = 30


@dataclass
class UndoableAction:
    """An action that can be undone within the window."""
    action_id: str
    action_type: LinkActionType
    created_at: datetime
    expires_at: datetime

    # What was done
    thread_id: str
    object_type: str
    object_id: str

    # For reversal
    previous_state: Optional[Dict[str, Any]]
    user_id: str
    yacht_id: str

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def seconds_remaining(self) -> int:
        if self.is_expired:
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())


def create_undoable_action(
    action_type: LinkActionType,
    thread_id: str,
    object_type: str,
    object_id: str,
    user_id: str,
    yacht_id: str,
    previous_state: Optional[Dict[str, Any]] = None
) -> UndoableAction:
    """Create an undoable action with standard window."""
    now = datetime.utcnow()
    return UndoableAction(
        action_id=str(uuid.uuid4()),
        action_type=action_type,
        created_at=now,
        expires_at=now + timedelta(seconds=UNDO_WINDOW_SECONDS),
        thread_id=thread_id,
        object_type=object_type,
        object_id=object_id,
        previous_state=previous_state,
        user_id=user_id,
        yacht_id=yacht_id,
    )


from datetime import timedelta


# =============================================================================
# UNDO RESPONSE
# =============================================================================

@dataclass
class UndoResponse:
    """Response from an undo operation."""
    success: bool
    message: str
    restored_state: Optional[Dict[str, Any]]


# =============================================================================
# CORRECTION FLOW
# =============================================================================

@dataclass
class CorrectionRequest:
    """Request to correct a wrong link."""
    original_link_id: str
    thread_id: str
    wrong_object_type: str
    wrong_object_id: str
    correct_object_type: Optional[str]
    correct_object_id: Optional[str]
    reason: Optional[str]  # Why was it wrong?


@dataclass
class CorrectionResult:
    """Result of a correction operation."""
    success: bool
    message: str
    new_link_id: Optional[str]
    undo_action: Optional[UndoableAction]


def process_correction(request: CorrectionRequest, user_id: str, yacht_id: str) -> CorrectionResult:
    """
    Process a link correction.

    Steps:
    1. Mark original link as corrected (not deleted - for audit)
    2. Create new link if correct target provided
    3. Log correction for ML feedback
    4. Return undoable action
    """
    # This would integrate with the database layer
    # For now, define the contract

    return CorrectionResult(
        success=True,
        message="Link corrected. You can undo this for 30 seconds.",
        new_link_id=str(uuid.uuid4()) if request.correct_object_id else None,
        undo_action=create_undoable_action(
            action_type=LinkActionType.LINK_CORRECTED,
            thread_id=request.thread_id,
            object_type=request.correct_object_type or request.wrong_object_type,
            object_id=request.correct_object_id or request.wrong_object_id,
            user_id=user_id,
            yacht_id=yacht_id,
            previous_state={
                "original_link_id": request.original_link_id,
                "wrong_object_type": request.wrong_object_type,
                "wrong_object_id": request.wrong_object_id,
            }
        )
    )


# =============================================================================
# AUDIT TRAIL
# =============================================================================

@dataclass
class AuditEntry:
    """Audit trail entry for link actions."""
    entry_id: str
    timestamp: datetime
    action_type: LinkActionType
    user_id: str
    yacht_id: str

    # What was affected
    thread_id: str
    object_type: str
    object_id: str

    # Context
    confidence_score: Optional[int]
    was_suggestion: bool
    was_auto_linked: bool

    # Outcome
    was_undone: bool
    was_corrected: bool
    correction_details: Optional[Dict[str, Any]]


def create_audit_entry(
    action_type: LinkActionType,
    user_id: str,
    yacht_id: str,
    thread_id: str,
    object_type: str,
    object_id: str,
    confidence_score: Optional[int] = None,
    was_suggestion: bool = False,
    was_auto_linked: bool = False,
) -> AuditEntry:
    """Create audit entry for link action."""
    return AuditEntry(
        entry_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        action_type=action_type,
        user_id=user_id,
        yacht_id=yacht_id,
        thread_id=thread_id,
        object_type=object_type,
        object_id=object_id,
        confidence_score=confidence_score,
        was_suggestion=was_suggestion,
        was_auto_linked=was_auto_linked,
        was_undone=False,
        was_corrected=False,
        correction_details=None,
    )


# =============================================================================
# "WHY THIS SUGGESTION?" EXPLAINABILITY
# =============================================================================

@dataclass
class SuggestionExplanation:
    """Human-readable explanation of why a suggestion was made."""
    summary: str
    signals: List[Dict[str, str]]
    confidence_level: str
    confidence_percent: int


def explain_suggestion(
    thread_id: str,
    object_type: str,
    object_id: str,
    score_breakdown: Dict[str, Any]
) -> SuggestionExplanation:
    """
    Generate human-readable explanation for a suggestion.

    Users should be able to understand WHY the system thinks
    this email relates to this work order.
    """
    signals = score_breakdown.get("signals", [])
    total_score = score_breakdown.get("total", 0)

    # Build human-readable signal descriptions
    readable_signals = []

    signal_descriptions = {
        "exact_id_subject": "Work order ID found in email subject",
        "exact_id_body": "Work order ID mentioned in email body",
        "vendor_domain": "Sender's company matches supplier on record",
        "time_proximity": "Email arrived within 48 hours of work order",
        "keyword_overlap": "Similar keywords found in both",
        "attachment_signal": "Attachment type matches expected documents",
        "user_history": "You've linked similar emails before",
    }

    for signal in signals:
        signal_type = signal.get("type", "")
        readable = signal_descriptions.get(signal_type, signal.get("reason", ""))
        if readable:
            readable_signals.append({
                "signal": readable,
                "strength": _strength_label(signal.get("value", 0))
            })

    # Determine confidence level description
    if total_score >= 100:
        level = "Certain"
        summary = "This is a definite match."
    elif total_score >= 85:
        level = "High"
        summary = "Very likely this email relates to this item."
    elif total_score >= 60:
        level = "Medium"
        summary = "This email probably relates to this item."
    elif total_score >= 30:
        level = "Low"
        summary = "This might be related, but please verify."
    else:
        level = "Uncertain"
        summary = "Weak signals. Manual verification recommended."

    return SuggestionExplanation(
        summary=summary,
        signals=readable_signals,
        confidence_level=level,
        confidence_percent=total_score,
    )


def _strength_label(value: int) -> str:
    """Convert signal value to strength label."""
    if value >= 50:
        return "Strong"
    elif value >= 20:
        return "Moderate"
    else:
        return "Weak"


# =============================================================================
# UI COPY
# =============================================================================

# Undo toast messages
UNDO_MESSAGES = {
    LinkActionType.LINK_CREATED: "Email linked. Undo?",
    LinkActionType.LINK_SUGGESTED: "Suggestion confirmed. Undo?",
    LinkActionType.LINK_REMOVED: "Link removed. Undo?",
    LinkActionType.LINK_CORRECTED: "Link corrected. Undo?",
    LinkActionType.SUGGESTION_DISMISSED: "Suggestion dismissed.",
    LinkActionType.SUGGESTION_WRONG: "Marked as wrong suggestion. This helps us learn.",
}

# Correction prompts
CORRECTION_PROMPTS = {
    "wrong_link": "This link is wrong",
    "choose_correct": "Link to the correct item instead",
    "just_remove": "Just remove this link",
    "mark_wrong": "Mark suggestion as wrong (helps us improve)",
}


# =============================================================================
# LOGGING
# =============================================================================

def log_link_action(
    action_type: LinkActionType,
    user_id: str,
    yacht_id: str,
    thread_id: str,
    object_type: str,
    object_id: str,
    confidence_score: Optional[int] = None,
    was_suggestion: bool = False,
    details: Dict[str, Any] = None
):
    """Log all link actions for audit and ML feedback."""
    logger.info(
        f"[LINK_ACTION] type={action_type.value} "
        f"user={user_id} yacht={yacht_id} "
        f"thread={thread_id} object={object_type}:{object_id} "
        f"confidence={confidence_score} suggestion={was_suggestion} "
        f"details={details or {}}"
    )


def log_correction(
    user_id: str,
    yacht_id: str,
    thread_id: str,
    wrong_object: str,
    correct_object: Optional[str],
    reason: Optional[str]
):
    """Log corrections for ML feedback loop."""
    logger.info(
        f"[CORRECTION] user={user_id} yacht={yacht_id} "
        f"thread={thread_id} wrong={wrong_object} "
        f"correct={correct_object} reason={reason}"
    )
