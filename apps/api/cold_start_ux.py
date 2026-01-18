"""
Cold Start UX - First-Week Experience
======================================

CRITICAL: Day 1-3 defines whether ship adopts or abandons.

This module defines:
1. Onboarding state detection
2. Progressive feature enablement
3. Empty state messaging
4. Success milestone triggers
5. "Learning" indicators

RULE: The system must never feel broken. If there's no data,
explain why and show what's coming. Silence = abandonment.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ONBOARDING STATES
# =============================================================================

class OnboardingState(Enum):
    """User's progression through first-week experience."""

    # Day 0
    JUST_CONNECTED = "just_connected"       # Email OAuth just completed
    FIRST_SYNC = "first_sync"               # Initial sync in progress
    SYNC_COMPLETE = "sync_complete"         # Initial sync done

    # Day 1-3
    EXPLORING = "exploring"                 # <5 interactions
    FIRST_LINK = "first_link"               # First email-to-object link
    FIRST_SEARCH = "first_search"           # First search used

    # Day 4-7
    PATTERN_FORMING = "pattern_forming"     # 5+ links created
    FEATURE_DISCOVERED = "feature_discovered"  # Used advanced feature

    # Established
    ESTABLISHED = "established"             # Regular user


@dataclass
class OnboardingProgress:
    """Tracks user's onboarding progress."""
    state: OnboardingState
    connected_at: Optional[datetime]
    messages_synced: int
    links_created: int
    searches_performed: int
    days_active: int

    @property
    def is_cold_start(self) -> bool:
        """True if user is in first-week experience."""
        return self.state in {
            OnboardingState.JUST_CONNECTED,
            OnboardingState.FIRST_SYNC,
            OnboardingState.SYNC_COMPLETE,
            OnboardingState.EXPLORING,
            OnboardingState.FIRST_LINK,
            OnboardingState.FIRST_SEARCH,
        }


# =============================================================================
# EMPTY STATE MESSAGES
# =============================================================================

# RULE: Every empty state has an explanation and expectation
EMPTY_STATE_MESSAGES: Dict[str, Dict[str, str]] = {
    "inbox": {
        "just_connected": {
            "title": "Syncing Your Inbox",
            "message": "We're importing your recent emails. This usually takes 2-5 minutes.",
            "action": None,
            "icon": "sync-spinner",
        },
        "sync_complete_empty": {
            "title": "No Recent Emails",
            "message": "Your inbox is empty or emails are older than 30 days. New emails will appear automatically.",
            "action": None,
            "icon": "inbox-empty",
        },
    },

    "related_suggestions": {
        "no_data": {
            "title": "Building Intelligence",
            "message": "Suggestions improve as you link emails to work orders. The more you link, the smarter it gets.",
            "action": "Link your first email to start",
            "icon": "brain-learning",
        },
        "low_confidence": {
            "title": "No Strong Matches",
            "message": "We didn't find confident matches for this email. You can link it manually.",
            "action": "Search to link manually",
            "icon": "search",
        },
    },

    "search_results": {
        "no_results": {
            "title": "No Matches Found",
            "message": "Try different keywords or check the spelling.",
            "action": None,
            "icon": "search-empty",
        },
        "first_time": {
            "title": "Search Your Emails",
            "message": "Type to search across all your synced emails by content, sender, or subject.",
            "action": None,
            "icon": "search-hint",
        },
    },

    "linked_emails": {
        "none_linked": {
            "title": "No Linked Emails Yet",
            "message": "Link emails to this work order to keep all related communication in one place.",
            "action": "Find and link emails",
            "icon": "link-add",
        },
    },
}


# =============================================================================
# LEARNING INDICATORS
# =============================================================================

@dataclass
class LearningIndicator:
    """Shows that system is actively learning."""
    message: str
    progress_percent: Optional[int]
    show_pulse: bool


LEARNING_INDICATORS: Dict[str, LearningIndicator] = {
    "embeddings_building": LearningIndicator(
        message="Indexing emails for smart search...",
        progress_percent=None,  # Indeterminate
        show_pulse=True,
    ),
    "suggestions_learning": LearningIndicator(
        message="Learning from your linking patterns",
        progress_percent=None,
        show_pulse=True,
    ),
    "first_sync": LearningIndicator(
        message="Syncing last 30 days of emails",
        progress_percent=None,
        show_pulse=True,
    ),
}


# =============================================================================
# SUCCESS MILESTONES
# =============================================================================

@dataclass
class Milestone:
    """A success milestone to celebrate."""
    id: str
    title: str
    message: str
    trigger_count: int
    icon: str
    show_once: bool


MILESTONES: List[Milestone] = [
    Milestone(
        id="first_link",
        title="First Link Created!",
        message="You've connected an email to a work order. Related emails will now appear together.",
        trigger_count=1,
        icon="link-success",
        show_once=True,
    ),
    Milestone(
        id="five_links",
        title="Getting Smarter",
        message="With 5 links, suggestions are starting to learn your patterns.",
        trigger_count=5,
        icon="brain",
        show_once=True,
    ),
    Milestone(
        id="first_search",
        title="Search Ready",
        message="Your emails are indexed and searchable. Find anything instantly.",
        trigger_count=1,
        icon="search-ready",
        show_once=True,
    ),
    Milestone(
        id="twenty_five_links",
        title="Full Intelligence",
        message="With 25+ links, the system now confidently suggests matches.",
        trigger_count=25,
        icon="rocket",
        show_once=True,
    ),
]


# =============================================================================
# ONBOARDING DETECTION
# =============================================================================

def detect_onboarding_state(
    connected_at: Optional[datetime],
    messages_synced: int,
    links_created: int,
    searches_performed: int,
    sync_in_progress: bool
) -> OnboardingProgress:
    """
    Detect user's current onboarding state.

    Called on every relevant interaction to determine UX treatment.
    """
    now = datetime.utcnow()

    # No connection yet
    if not connected_at:
        return OnboardingProgress(
            state=OnboardingState.JUST_CONNECTED,
            connected_at=None,
            messages_synced=0,
            links_created=0,
            searches_performed=0,
            days_active=0,
        )

    days_active = (now - connected_at).days

    # Still syncing
    if sync_in_progress:
        return OnboardingProgress(
            state=OnboardingState.FIRST_SYNC,
            connected_at=connected_at,
            messages_synced=messages_synced,
            links_created=links_created,
            searches_performed=searches_performed,
            days_active=days_active,
        )

    # Sync complete, checking progression
    if messages_synced == 0:
        return OnboardingProgress(
            state=OnboardingState.SYNC_COMPLETE,
            connected_at=connected_at,
            messages_synced=0,
            links_created=0,
            searches_performed=0,
            days_active=days_active,
        )

    # Check milestones
    if links_created >= 5 and days_active >= 4:
        state = OnboardingState.ESTABLISHED
    elif links_created >= 5:
        state = OnboardingState.PATTERN_FORMING
    elif links_created >= 1:
        state = OnboardingState.FIRST_LINK
    elif searches_performed >= 1:
        state = OnboardingState.FIRST_SEARCH
    elif links_created == 0 and searches_performed == 0:
        state = OnboardingState.EXPLORING
    else:
        state = OnboardingState.SYNC_COMPLETE

    return OnboardingProgress(
        state=state,
        connected_at=connected_at,
        messages_synced=messages_synced,
        links_created=links_created,
        searches_performed=searches_performed,
        days_active=days_active,
    )


def get_empty_state_message(
    context: str,
    onboarding: OnboardingProgress
) -> Optional[Dict[str, Any]]:
    """
    Get appropriate empty state message for context.

    Args:
        context: Which UI context (inbox, related_suggestions, etc.)
        onboarding: User's onboarding progress

    Returns:
        Message dict or None if no special message needed
    """
    messages = EMPTY_STATE_MESSAGES.get(context, {})

    if context == "inbox":
        if onboarding.state == OnboardingState.FIRST_SYNC:
            return messages.get("just_connected")
        elif onboarding.messages_synced == 0:
            return messages.get("sync_complete_empty")

    elif context == "related_suggestions":
        if onboarding.links_created < 5:
            return messages.get("no_data")
        else:
            return messages.get("low_confidence")

    elif context == "search_results":
        if onboarding.searches_performed == 0:
            return messages.get("first_time")
        else:
            return messages.get("no_results")

    elif context == "linked_emails":
        return messages.get("none_linked")

    return None


def check_milestones(
    onboarding: OnboardingProgress,
    achieved_milestones: List[str]
) -> Optional[Milestone]:
    """
    Check if user has achieved a new milestone.

    Args:
        onboarding: User's onboarding progress
        achieved_milestones: List of milestone IDs already shown

    Returns:
        New milestone to show, or None
    """
    for milestone in MILESTONES:
        if milestone.id in achieved_milestones:
            continue

        if milestone.id == "first_link" and onboarding.links_created >= 1:
            return milestone
        elif milestone.id == "five_links" and onboarding.links_created >= 5:
            return milestone
        elif milestone.id == "first_search" and onboarding.searches_performed >= 1:
            return milestone
        elif milestone.id == "twenty_five_links" and onboarding.links_created >= 25:
            return milestone

    return None


# =============================================================================
# LOGGING
# =============================================================================

def log_onboarding_event(
    user_id: str,
    yacht_id: str,
    event: str,
    state: OnboardingState,
    details: Dict[str, Any] = None
):
    """Log onboarding events for analytics."""
    logger.info(
        f"[ONBOARDING] user={user_id} yacht={yacht_id} "
        f"event={event} state={state.value} "
        f"details={details or {}}"
    )
