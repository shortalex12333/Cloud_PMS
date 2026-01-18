"""
Security Narrative - Visible Trust Cues
========================================

CRITICAL: Users need to SEE that their data is protected.

This module defines:
1. User-visible security indicators
2. Permission status displays
3. Data handling transparency
4. "Where is my data?" answers

RULE: Security theatre without substance is harmful.
These are REAL protections, made visible.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY STATUS
# =============================================================================

class SecurityStatus(Enum):
    """Overall security status for user's session."""

    SECURE = "secure"               # All good
    WARNING = "warning"             # Non-critical issue
    ACTION_REQUIRED = "action_required"  # User needs to do something


@dataclass
class SecurityIndicator:
    """User-visible security status."""
    status: SecurityStatus
    message: str
    details: Optional[str]
    action: Optional[str]
    icon: str


# =============================================================================
# VISIBLE TRUST CUES
# =============================================================================

# Messages shown to users about their data protection
TRUST_CUES: Dict[str, Dict[str, str]] = {
    "email_connection": {
        "secure": {
            "label": "Secure Connection",
            "message": "Your email is connected via Microsoft's secure OAuth.",
            "detail": "We never see or store your password.",
            "icon": "shield-check",
        },
        "expired": {
            "label": "Connection Expired",
            "message": "Your email connection needs renewal.",
            "detail": "Reconnect to resume syncing.",
            "icon": "shield-alert",
        },
    },

    "data_isolation": {
        "label": "Data Isolation",
        "message": "Your yacht's data is completely isolated.",
        "detail": "Row-level security ensures no cross-yacht access.",
        "icon": "lock",
    },

    "encryption": {
        "label": "Encrypted Storage",
        "message": "All data encrypted at rest and in transit.",
        "detail": "TLS 1.3 in transit, AES-256 at rest.",
        "icon": "key",
    },

    "no_training": {
        "label": "Your Data, Your Privacy",
        "message": "Your emails are never used to train AI.",
        "detail": "We use OpenAI for search only - no training on your content.",
        "icon": "brain-off",
    },

    "retention": {
        "label": "You Control Your Data",
        "message": "Disconnect anytime - your email data is deleted.",
        "detail": "We only store metadata and search indices.",
        "icon": "trash",
    },
}


# =============================================================================
# PERMISSION TRANSPARENCY
# =============================================================================

@dataclass
class PermissionDisplay:
    """What to show about OAuth permissions."""
    permission: str
    why_needed: str
    what_we_access: str
    what_we_dont: str


# Microsoft Graph permissions explained
PERMISSION_EXPLANATIONS: List[PermissionDisplay] = [
    PermissionDisplay(
        permission="Mail.Read",
        why_needed="To sync your inbox and show emails in the app",
        what_we_access="Email subjects, senders, recipients, body text, attachment names",
        what_we_dont="We cannot send emails, delete emails, or access other mailboxes",
    ),
    PermissionDisplay(
        permission="User.Read",
        why_needed="To identify your account and display your name",
        what_we_access="Your display name and email address",
        what_we_dont="We cannot access your contacts, calendar, or files",
    ),
]


# =============================================================================
# DATA HANDLING TRANSPARENCY
# =============================================================================

@dataclass
class DataHandlingInfo:
    """Transparent explanation of data handling."""
    data_type: str
    what_we_store: str
    where_stored: str
    retention: str
    who_can_see: str


DATA_HANDLING: List[DataHandlingInfo] = [
    DataHandlingInfo(
        data_type="Email Metadata",
        what_we_store="Subject, sender, date, thread relationships",
        where_stored="Supabase database (EU/US region)",
        retention="Until you disconnect email or delete account",
        who_can_see="Only users with access to your yacht",
    ),
    DataHandlingInfo(
        data_type="Email Body (cached)",
        what_we_store="Plain text content for search indexing",
        where_stored="Supabase database (EU/US region)",
        retention="Until you disconnect email or delete account",
        who_can_see="Only users with access to your yacht",
    ),
    DataHandlingInfo(
        data_type="Search Vectors",
        what_we_store="Mathematical representations for semantic search",
        where_stored="Supabase pgvector extension",
        retention="Until you disconnect email or delete account",
        who_can_see="System only - not human readable",
    ),
    DataHandlingInfo(
        data_type="Link History",
        what_we_store="Which emails you linked to which items",
        where_stored="Supabase database",
        retention="Permanent (part of audit trail)",
        who_can_see="Only users with access to your yacht",
    ),
]


# =============================================================================
# "WHERE IS MY DATA?" ANSWERS
# =============================================================================

WHERE_IS_MY_DATA = {
    "email_provider": {
        "question": "Where are my actual emails?",
        "answer": "Your emails stay in Microsoft 365. We only cache metadata and text for search.",
        "detail": "If you disconnect, our cached copy is deleted. Your emails remain in Outlook.",
    },

    "database": {
        "question": "Where is the database?",
        "answer": "Supabase (hosted on AWS in the US region).",
        "detail": "Data is encrypted at rest with AES-256.",
    },

    "ai_processing": {
        "question": "Does AI see my emails?",
        "answer": "Only for search indexing. We use OpenAI's embedding API.",
        "detail": "Email text is converted to vectors for search. OpenAI's API does not retain or train on this data.",
    },

    "backups": {
        "question": "Are there backups?",
        "answer": "Supabase maintains point-in-time recovery.",
        "detail": "Backups are encrypted and only used for disaster recovery.",
    },

    "deletion": {
        "question": "How do I delete my data?",
        "answer": "Disconnect your email in Settings, or delete your account.",
        "detail": "Email data is deleted within 24 hours. Audit logs may be retained for compliance.",
    },
}


# =============================================================================
# SECURITY SETTINGS UI
# =============================================================================

@dataclass
class SecuritySetting:
    """A security setting the user can view/modify."""
    id: str
    label: str
    description: str
    current_value: str
    can_modify: bool
    action_label: Optional[str]


def get_security_settings(user_id: str, yacht_id: str) -> List[SecuritySetting]:
    """Get security settings for display in Settings page."""
    return [
        SecuritySetting(
            id="email_connection",
            label="Email Connection",
            description="Microsoft 365 connected via OAuth 2.0",
            current_value="Connected",  # Or "Not connected"
            can_modify=True,
            action_label="Disconnect",
        ),
        SecuritySetting(
            id="data_region",
            label="Data Region",
            description="Where your data is stored",
            current_value="US (Supabase)",
            can_modify=False,
            action_label=None,
        ),
        SecuritySetting(
            id="encryption",
            label="Encryption",
            description="Data protection status",
            current_value="Enabled (TLS 1.3 + AES-256)",
            can_modify=False,
            action_label=None,
        ),
        SecuritySetting(
            id="last_sync",
            label="Last Email Sync",
            description="When emails were last fetched",
            current_value="2 minutes ago",  # Dynamic
            can_modify=False,
            action_label="Sync Now",
        ),
    ]


# =============================================================================
# AUDIT VISIBILITY
# =============================================================================

@dataclass
class AuditLogEntry:
    """User-visible audit log entry."""
    timestamp: str
    action: str
    description: str
    user_email: str


def get_recent_audit_log(yacht_id: str, limit: int = 20) -> List[AuditLogEntry]:
    """
    Get recent audit log for yacht.

    Shows users what actions have been taken on their data.
    """
    # This would query the audit table
    # Example return for contract
    return [
        AuditLogEntry(
            timestamp="2026-01-18 14:30",
            action="email_linked",
            description="Email linked to WO-1234",
            user_email="captain@yacht.com",
        ),
        AuditLogEntry(
            timestamp="2026-01-18 14:25",
            action="email_synced",
            description="15 new emails synced",
            user_email="system",
        ),
    ]


# =============================================================================
# INDICATOR GENERATION
# =============================================================================

def get_security_indicator(
    email_connected: bool,
    token_valid: bool,
    last_sync_minutes: int
) -> SecurityIndicator:
    """Generate current security indicator for header display."""

    if not email_connected:
        return SecurityIndicator(
            status=SecurityStatus.WARNING,
            message="Email not connected",
            details="Connect your email to enable sync features",
            action="Connect Email",
            icon="mail-off",
        )

    if not token_valid:
        return SecurityIndicator(
            status=SecurityStatus.ACTION_REQUIRED,
            message="Email connection expired",
            details="Please reconnect to resume syncing",
            action="Reconnect",
            icon="shield-alert",
        )

    if last_sync_minutes > 30:
        return SecurityIndicator(
            status=SecurityStatus.WARNING,
            message=f"Email sync delayed ({last_sync_minutes}m)",
            details="Sync may be slow due to connectivity",
            action="Sync Now",
            icon="clock",
        )

    return SecurityIndicator(
        status=SecurityStatus.SECURE,
        message="Secure",
        details=TRUST_CUES["data_isolation"]["message"],
        action=None,
        icon="shield-check",
    )


# =============================================================================
# LOGGING
# =============================================================================

def log_security_event(
    event_type: str,
    user_id: str,
    yacht_id: str,
    details: Dict[str, Any] = None
):
    """Log security-relevant events."""
    logger.info(
        f"[SECURITY] event={event_type} user={user_id} "
        f"yacht={yacht_id} details={details or {}}"
    )
