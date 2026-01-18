"""
Email Resilience Layer - Failure & Degradation Handling
========================================================

CRITICAL: Ships don't live on happy paths.

This module defines:
1. Graceful degradation hierarchy
2. Explicit failure messages (never silent)
3. Fallback chains
4. User-facing error narratives

RULE: If the system spins or goes quiet, ship-side trust dies permanently.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# FAILURE TYPES
# =============================================================================

class EmailFailureType(Enum):
    """All known failure modes for email operations."""

    # Graph API failures
    GRAPH_DOWN = "graph_down"                    # Microsoft Graph unreachable
    GRAPH_RATE_LIMITED = "graph_rate_limited"   # 429 from Graph
    GRAPH_TIMEOUT = "graph_timeout"             # Request timed out

    # Token failures
    TOKEN_EXPIRED = "token_expired"             # Access token expired
    TOKEN_REVOKED = "token_revoked"             # User revoked OAuth
    TOKEN_MISSING = "token_missing"             # No token for this user
    TOKEN_REFRESH_FAILED = "token_refresh_failed"  # Couldn't refresh

    # Sync failures
    SYNC_PARTIAL = "sync_partial"               # Some messages failed
    SYNC_DELTA_INVALID = "sync_delta_invalid"   # Delta link expired
    SYNC_TIMEOUT = "sync_timeout"               # Sync took too long

    # Content failures
    BODY_UNAVAILABLE = "body_unavailable"       # Can't fetch email body
    ATTACHMENT_UNAVAILABLE = "attachment_unavailable"  # Can't fetch attachment

    # Processing failures
    EMBEDDING_FAILED = "embedding_failed"       # OpenAI embedding failed
    EMBEDDING_QUOTA = "embedding_quota"         # OpenAI quota exceeded
    EXTRACTION_FAILED = "extraction_failed"     # Entity extraction failed

    # Database failures
    VECTOR_INDEX_DOWN = "vector_index_down"     # pgvector unavailable
    DB_TIMEOUT = "db_timeout"                   # Database query timeout

    # Unknown
    UNKNOWN = "unknown"


# =============================================================================
# DEGRADATION LEVELS
# =============================================================================

class DegradationLevel(Enum):
    """Degradation hierarchy from full to minimal."""

    FULL = "full"           # Everything working
    REDUCED = "reduced"     # Some features degraded
    MINIMAL = "minimal"     # Metadata only, no smart features
    OFFLINE = "offline"     # Cannot connect to external services


@dataclass
class DegradedState:
    """Current degradation state for a user's email."""
    level: DegradationLevel
    failures: List[EmailFailureType]
    user_message: str
    available_features: List[str]
    unavailable_features: List[str]


# =============================================================================
# USER-FACING ERROR MESSAGES
# =============================================================================

# RULE: Every failure has an explicit, honest message
FAILURE_MESSAGES: Dict[EmailFailureType, str] = {
    # Graph failures
    EmailFailureType.GRAPH_DOWN:
        "Microsoft email services are temporarily unavailable. Showing cached data.",
    EmailFailureType.GRAPH_RATE_LIMITED:
        "Email sync paused momentarily due to high activity. Will resume shortly.",
    EmailFailureType.GRAPH_TIMEOUT:
        "Email request timed out. Showing available cached data.",

    # Token failures
    EmailFailureType.TOKEN_EXPIRED:
        "Email connection needs refresh. Please reconnect in Settings.",
    EmailFailureType.TOKEN_REVOKED:
        "Email access was disconnected. Please reconnect in Settings.",
    EmailFailureType.TOKEN_MISSING:
        "Email not connected. Connect your email in Settings to enable this feature.",
    EmailFailureType.TOKEN_REFRESH_FAILED:
        "Couldn't refresh email connection. Please reconnect in Settings.",

    # Sync failures
    EmailFailureType.SYNC_PARTIAL:
        "Some recent emails may not be shown. Sync will retry automatically.",
    EmailFailureType.SYNC_DELTA_INVALID:
        "Re-syncing inbox from scratch. This may take a moment.",
    EmailFailureType.SYNC_TIMEOUT:
        "Email sync is taking longer than expected. Showing available data.",

    # Content failures
    EmailFailureType.BODY_UNAVAILABLE:
        "Email body unavailable. Metadata shown.",
    EmailFailureType.ATTACHMENT_UNAVAILABLE:
        "Attachment temporarily unavailable. Please try again.",

    # Processing failures
    EmailFailureType.EMBEDDING_FAILED:
        "Search quality reduced. Basic text search still available.",
    EmailFailureType.EMBEDDING_QUOTA:
        "Smart search temporarily limited. Basic search available.",
    EmailFailureType.EXTRACTION_FAILED:
        "Automatic entity detection limited. Manual linking available.",

    # Database failures
    EmailFailureType.VECTOR_INDEX_DOWN:
        "Semantic search unavailable. Using text-based search.",
    EmailFailureType.DB_TIMEOUT:
        "Search is slow right now. Please try again.",

    # Unknown
    EmailFailureType.UNKNOWN:
        "Something went wrong. Please try again or contact support.",
}


# =============================================================================
# FALLBACK CHAINS
# =============================================================================

@dataclass
class FallbackChain:
    """Defines what to try when primary method fails."""
    primary: str
    fallbacks: List[str]
    final_fallback: str
    user_message_on_fallback: str


FALLBACK_CHAINS: Dict[str, FallbackChain] = {
    "inbox_fetch": FallbackChain(
        primary="graph_api_live",
        fallbacks=["cached_metadata", "last_known_state"],
        final_fallback="empty_with_explanation",
        user_message_on_fallback="Showing cached inbox. Live data temporarily unavailable."
    ),

    "body_fetch": FallbackChain(
        primary="graph_api_body",
        fallbacks=["cached_body_if_exists"],
        final_fallback="metadata_only",
        user_message_on_fallback="Email body unavailable. Metadata shown."
    ),

    "email_search": FallbackChain(
        primary="hybrid_sql_vector",
        fallbacks=["sql_text_only", "cached_results"],
        final_fallback="no_results_with_explanation",
        user_message_on_fallback="Using text search. Semantic search temporarily unavailable."
    ),

    "related_suggestions": FallbackChain(
        primary="embedding_similarity",
        fallbacks=["token_extraction", "cached_suggestions"],
        final_fallback="manual_link_only",
        user_message_on_fallback="Automatic suggestions limited. Manual linking available."
    ),

    "attachment_fetch": FallbackChain(
        primary="graph_api_attachment",
        fallbacks=["stored_copy_if_exists"],
        final_fallback="unavailable_with_retry",
        user_message_on_fallback="Attachment temporarily unavailable. Please try again."
    ),
}


# =============================================================================
# DEGRADATION CALCULATOR
# =============================================================================

def calculate_degradation(failures: List[EmailFailureType]) -> DegradedState:
    """
    Calculate current degradation state from active failures.

    Returns user-friendly state with explicit messaging.
    """
    if not failures:
        return DegradedState(
            level=DegradationLevel.FULL,
            failures=[],
            user_message="",
            available_features=[
                "live_inbox", "body_fetch", "semantic_search",
                "auto_suggestions", "attachments"
            ],
            unavailable_features=[]
        )

    # Check for offline conditions
    offline_failures = {
        EmailFailureType.TOKEN_MISSING,
        EmailFailureType.TOKEN_REVOKED,
    }

    if any(f in offline_failures for f in failures):
        return DegradedState(
            level=DegradationLevel.OFFLINE,
            failures=failures,
            user_message="Email not connected. Connect in Settings to enable email features.",
            available_features=[],
            unavailable_features=[
                "live_inbox", "body_fetch", "semantic_search",
                "auto_suggestions", "attachments"
            ]
        )

    # Check for minimal conditions
    minimal_failures = {
        EmailFailureType.GRAPH_DOWN,
        EmailFailureType.TOKEN_EXPIRED,
        EmailFailureType.TOKEN_REFRESH_FAILED,
    }

    if any(f in minimal_failures for f in failures):
        return DegradedState(
            level=DegradationLevel.MINIMAL,
            failures=failures,
            user_message="Email services limited. Showing cached data only.",
            available_features=["cached_metadata", "manual_link"],
            unavailable_features=[
                "live_inbox", "body_fetch", "semantic_search",
                "auto_suggestions", "attachments"
            ]
        )

    # Reduced functionality
    unavailable = []
    if EmailFailureType.EMBEDDING_FAILED in failures or EmailFailureType.VECTOR_INDEX_DOWN in failures:
        unavailable.append("semantic_search")
    if EmailFailureType.EXTRACTION_FAILED in failures:
        unavailable.append("auto_suggestions")
    if EmailFailureType.BODY_UNAVAILABLE in failures:
        unavailable.append("body_fetch")

    all_features = [
        "live_inbox", "body_fetch", "semantic_search",
        "auto_suggestions", "attachments", "manual_link"
    ]
    available = [f for f in all_features if f not in unavailable]

    messages = [FAILURE_MESSAGES.get(f, FAILURE_MESSAGES[EmailFailureType.UNKNOWN]) for f in failures[:2]]

    return DegradedState(
        level=DegradationLevel.REDUCED,
        failures=failures,
        user_message=" ".join(messages),
        available_features=available,
        unavailable_features=unavailable
    )


# =============================================================================
# API RESPONSE WRAPPER
# =============================================================================

@dataclass
class ResilientEmailResponse:
    """
    Wrapper for all email API responses.

    Always includes:
    - success: bool
    - data: actual response data
    - degradation: current degradation state
    - user_message: human-readable status
    """
    success: bool
    data: Optional[Any]
    degradation: DegradedState
    user_message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "degradation": {
                "level": self.degradation.level.value,
                "available_features": self.degradation.available_features,
                "unavailable_features": self.degradation.unavailable_features,
            },
            "user_message": self.user_message,
        }


def wrap_email_response(
    data: Any,
    failures: List[EmailFailureType] = None,
    success: bool = True
) -> ResilientEmailResponse:
    """Wrap any email response with degradation context."""
    failures = failures or []
    degradation = calculate_degradation(failures)

    # Determine user message
    if success and not failures:
        user_message = ""
    elif success and failures:
        user_message = degradation.user_message
    else:
        primary_failure = failures[0] if failures else EmailFailureType.UNKNOWN
        user_message = FAILURE_MESSAGES.get(primary_failure, FAILURE_MESSAGES[EmailFailureType.UNKNOWN])

    return ResilientEmailResponse(
        success=success,
        data=data,
        degradation=degradation,
        user_message=user_message
    )


# =============================================================================
# LOGGING
# =============================================================================

def log_email_failure(
    failure_type: EmailFailureType,
    context: Dict[str, Any],
    user_id: str = None,
    yacht_id: str = None
):
    """Log email failure with full context for debugging."""
    logger.warning(
        f"[EMAIL_FAILURE] type={failure_type.value} "
        f"user={user_id} yacht={yacht_id} "
        f"context={context}"
    )
