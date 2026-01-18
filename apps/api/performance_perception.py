"""
Performance Perception - Progressive Loading & Skeleton States
==============================================================

CRITICAL: Perceived speed > actual speed.

This module defines:
1. Skeleton state contracts
2. Progressive loading stages
3. Optimistic UI patterns
4. Timeout handling with user feedback

RULE: The UI must NEVER freeze or go blank without explanation.
Even 100ms of blank screen feels like "broken" on satellite.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# LOADING STAGES
# =============================================================================

class LoadingStage(Enum):
    """Progressive loading stages for any data fetch."""

    SKELETON = "skeleton"       # Show shape, no data
    CACHED = "cached"           # Show cached/stale data
    PARTIAL = "partial"         # Some fresh data arrived
    COMPLETE = "complete"       # All data loaded
    ERROR = "error"             # Failed with message


@dataclass
class LoadingState:
    """Current loading state for a component."""
    stage: LoadingStage
    message: Optional[str]
    progress_percent: Optional[int]  # 0-100 if known, None if indeterminate
    can_interact: bool               # Can user interact with partial data?
    show_refresh: bool               # Show manual refresh option?


# =============================================================================
# SKELETON CONTRACTS
# =============================================================================

# Each component defines what its skeleton looks like
SKELETON_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "inbox_list": {
        "type": "list",
        "item_count": 8,                    # Show 8 skeleton items
        "item_height_px": 72,               # Match real item height
        "show_avatar": True,
        "show_subject_line": True,
        "show_preview_line": True,
        "show_timestamp": True,
        "animate": True,                    # Pulse animation
    },

    "email_thread": {
        "type": "thread",
        "header_skeleton": True,            # From/To/Subject area
        "body_lines": 6,                    # Placeholder body lines
        "show_attachment_placeholder": True,
        "animate": True,
    },

    "context_panel": {
        "type": "panel",
        "sections": [
            {"name": "related", "items": 3},
            {"name": "suggested", "items": 2},
        ],
        "animate": True,
    },

    "search_results": {
        "type": "list",
        "item_count": 5,
        "item_height_px": 80,
        "show_highlight_placeholder": True,
        "animate": True,
    },

    "work_order_card": {
        "type": "card",
        "show_title": True,
        "show_status_badge": True,
        "show_description_lines": 2,
        "show_metadata_row": True,
        "animate": True,
    },
}


# =============================================================================
# TIMEOUT THRESHOLDS
# =============================================================================

@dataclass
class TimeoutThresholds:
    """Timeout handling for different operations."""

    # When to show "still loading" message
    SHOW_PATIENCE_MESSAGE_MS: int = 2000

    # When to show "taking longer than usual"
    SHOW_SLOW_WARNING_MS: int = 5000

    # When to show cached data instead
    FALLBACK_TO_CACHE_MS: int = 8000

    # When to show error state
    HARD_TIMEOUT_MS: int = 15000

    # Satellite-specific: longer thresholds
    SATELLITE_MULTIPLIER: float = 2.0


TIMEOUTS = TimeoutThresholds()


# Patience messages shown during long waits
PATIENCE_MESSAGES: Dict[str, List[str]] = {
    "default": [
        "Loading...",
        "Still working on it...",
        "Taking a bit longer than usual...",
        "Almost there...",
    ],
    "satellite": [
        "Loading (satellite connection)...",
        "Working through slower connection...",
        "Still fetching - satellite speeds vary...",
        "Hang tight, almost there...",
    ],
    "search": [
        "Searching...",
        "Checking more results...",
        "Deep search in progress...",
    ],
    "sync": [
        "Syncing emails...",
        "Still syncing...",
        "Large sync in progress...",
    ],
}


# =============================================================================
# OPTIMISTIC UI PATTERNS
# =============================================================================

@dataclass
class OptimisticUpdate:
    """Contract for optimistic UI updates."""
    action_id: str
    component: str
    optimistic_state: Dict[str, Any]    # What to show immediately
    rollback_state: Dict[str, Any]      # What to restore on failure
    timeout_ms: int                      # When to consider it failed


# Actions that should update UI before server confirms
OPTIMISTIC_ACTIONS: Dict[str, Dict[str, Any]] = {
    "link_email": {
        "immediate_feedback": "linked",         # Show as linked
        "rollback_on_fail": "unlinked",         # Restore if fails
        "timeout_ms": 5000,
        "success_toast": "Email linked",
        "failure_toast": "Couldn't link - please try again",
    },

    "unlink_email": {
        "immediate_feedback": "unlinked",
        "rollback_on_fail": "linked",
        "timeout_ms": 5000,
        "success_toast": "Link removed",
        "failure_toast": "Couldn't remove - please try again",
    },

    "dismiss_suggestion": {
        "immediate_feedback": "dismissed",
        "rollback_on_fail": "visible",
        "timeout_ms": 3000,
        "success_toast": None,                  # No toast needed
        "failure_toast": "Couldn't save preference",
    },

    "archive_thread": {
        "immediate_feedback": "archived",
        "rollback_on_fail": "visible",
        "timeout_ms": 5000,
        "success_toast": "Archived",
        "failure_toast": "Couldn't archive - please try again",
    },
}


# =============================================================================
# STALE DATA INDICATORS
# =============================================================================

@dataclass
class StaleDataIndicator:
    """Shows when data might be outdated."""
    is_stale: bool
    age_description: str            # "Updated 5 minutes ago"
    show_warning: bool              # Show visual stale indicator
    allow_interaction: bool         # Can user still interact?


def calculate_staleness(
    last_updated_seconds_ago: int,
    data_type: str
) -> StaleDataIndicator:
    """
    Calculate staleness indicator for data.

    Different data types have different staleness thresholds.
    """
    thresholds = {
        "inbox": 60,            # 1 minute
        "email_body": 300,      # 5 minutes (rarely changes)
        "search_results": 30,   # 30 seconds
        "work_order": 120,      # 2 minutes
        "suggestions": 60,      # 1 minute
    }

    threshold = thresholds.get(data_type, 60)
    is_stale = last_updated_seconds_ago > threshold

    # Generate human-readable age
    if last_updated_seconds_ago < 60:
        age_desc = "Just now"
    elif last_updated_seconds_ago < 300:
        mins = last_updated_seconds_ago // 60
        age_desc = f"Updated {mins} minute{'s' if mins > 1 else ''} ago"
    elif last_updated_seconds_ago < 3600:
        mins = last_updated_seconds_ago // 60
        age_desc = f"Updated {mins} minutes ago"
    else:
        hours = last_updated_seconds_ago // 3600
        age_desc = f"Updated {hours} hour{'s' if hours > 1 else ''} ago"

    return StaleDataIndicator(
        is_stale=is_stale,
        age_description=age_desc,
        show_warning=is_stale and last_updated_seconds_ago > threshold * 5,
        allow_interaction=True,  # Always allow interaction
    )


# =============================================================================
# PROGRESSIVE REVEAL
# =============================================================================

@dataclass
class ProgressiveReveal:
    """Defines what to show at each loading stage."""
    stage: LoadingStage
    components_visible: List[str]
    interactions_enabled: List[str]
    message: Optional[str]


# Email thread progressive reveal
EMAIL_THREAD_REVEAL = [
    ProgressiveReveal(
        stage=LoadingStage.SKELETON,
        components_visible=["header_skeleton", "body_skeleton"],
        interactions_enabled=[],
        message=None,
    ),
    ProgressiveReveal(
        stage=LoadingStage.CACHED,
        components_visible=["header", "cached_body_preview"],
        interactions_enabled=["scroll", "link_button"],
        message="Showing cached version",
    ),
    ProgressiveReveal(
        stage=LoadingStage.PARTIAL,
        components_visible=["header", "body"],
        interactions_enabled=["scroll", "link_button", "reply"],
        message=None,
    ),
    ProgressiveReveal(
        stage=LoadingStage.COMPLETE,
        components_visible=["header", "body", "attachments", "suggestions"],
        interactions_enabled=["all"],
        message=None,
    ),
]


# =============================================================================
# INTERACTION BLOCKING
# =============================================================================

# Which interactions to disable during loading
BLOCKED_DURING_LOAD: Dict[str, List[str]] = {
    "inbox": ["archive", "delete"],                     # Can still click to open
    "email_thread": [],                                 # Can interact with skeleton
    "search": ["export"],                               # Can still type
    "link_panel": ["confirm_link"],                     # Can browse suggestions
}

# Which interactions remain available
ALWAYS_AVAILABLE: List[str] = [
    "scroll",
    "navigation",
    "cancel",
    "search_input",
]


# =============================================================================
# LOGGING
# =============================================================================

def log_loading_event(
    component: str,
    stage: LoadingStage,
    duration_ms: int,
    is_satellite: bool = False,
    user_id: str = None,
):
    """Log loading performance for monitoring."""
    logger.info(
        f"[LOADING] component={component} stage={stage.value} "
        f"duration_ms={duration_ms} satellite={is_satellite} "
        f"user={user_id}"
    )
