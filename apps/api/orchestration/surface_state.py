"""
Surface State - UI State Machine
=================================

Single URL state machine. No navigation, no pages, no folders.
Surface state determines retrieval behavior.

LOCKED STATES:
    SEARCH - Global search bar active
    EMAIL_INBOX - Email overlay, no query (system-triggered)
    EMAIL_OPEN - Single email thread open
    EMAIL_SEARCH - Searching within email surface
    ENTITY_OPEN - Work order/equipment/part open
    DOCUMENT_OPEN - Document viewer active
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


class SurfaceState(Enum):
    """
    Locked surface states. No navigation metaphors.
    Each state implies different retrieval behavior.
    """
    SEARCH = "search"               # Global search bar
    EMAIL_INBOX = "email_inbox"     # Inbox view, no query text
    EMAIL_OPEN = "email_open"       # Single email/thread open
    EMAIL_SEARCH = "email_search"   # Searching within email
    ENTITY_OPEN = "entity_open"     # WO/Equipment/Part detail view
    DOCUMENT_OPEN = "doc_open"      # Document viewer


@dataclass
class SurfaceContext:
    """
    Complete context for a search request.
    Immutable after construction.
    """
    # Required
    surface_state: SurfaceState
    yacht_id: str
    user_id: str

    # Query (may be empty for system-triggered states)
    query_text: str = ""

    # Open entity context (when ENTITY_OPEN or EMAIL_OPEN)
    open_entity_type: Optional[str] = None  # 'work_order', 'equipment', 'email_thread', etc.
    open_entity_id: Optional[str] = None

    # Email-specific context
    open_thread_id: Optional[str] = None
    email_direction_bias: str = "inbound"  # 'inbound' (90%) or 'outbound' (10%) - frontend default

    # Timestamp for recency calculations
    request_time: datetime = field(default_factory=datetime.utcnow)

    # Debug/trace
    request_id: Optional[str] = None
    debug_mode: bool = False

    def is_email_surface(self) -> bool:
        """True if on any email-related surface."""
        return self.surface_state in (
            SurfaceState.EMAIL_INBOX,
            SurfaceState.EMAIL_OPEN,
            SurfaceState.EMAIL_SEARCH,
        )

    def is_system_triggered(self) -> bool:
        """True if this is a system-triggered query (no user text)."""
        return self.surface_state == SurfaceState.EMAIL_INBOX and not self.query_text.strip()

    def has_open_entity(self) -> bool:
        """True if an entity is currently open."""
        return self.open_entity_id is not None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/debugging."""
        return {
            'surface_state': self.surface_state.value,
            'yacht_id': self.yacht_id,
            'user_id': self.user_id,
            'query_text': self.query_text[:100] if self.query_text else None,
            'open_entity_type': self.open_entity_type,
            'open_entity_id': self.open_entity_id,
            'open_thread_id': self.open_thread_id,
            'is_email_surface': self.is_email_surface(),
            'is_system_triggered': self.is_system_triggered(),
            'request_id': self.request_id,
        }


# Default scopes per surface state
# These are the SAFE defaults when user doesn't specify domain
SAFE_DEFAULT_SCOPES = {
    SurfaceState.SEARCH: ["work_orders", "equipment", "faults", "documents", "parts", "certificates", "checklists"],
    SurfaceState.EMAIL_INBOX: ["emails"],
    SurfaceState.EMAIL_OPEN: ["emails", "email_attachments"],
    SurfaceState.EMAIL_SEARCH: ["emails", "email_attachments"],
    SurfaceState.ENTITY_OPEN: ["related_entities", "documents", "history", "emails"],
    SurfaceState.DOCUMENT_OPEN: ["documents", "document_chunks"],
}


def get_default_scopes(state: SurfaceState) -> list:
    """Get safe default scopes for a surface state."""
    return SAFE_DEFAULT_SCOPES.get(state, ["work_orders", "equipment", "documents"])
