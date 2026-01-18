"""
"This Is Not Email" Framing - Expectation Setting
==================================================

CRITICAL: Users will compare this to Outlook/Gmail and be confused.

This module defines:
1. Onboarding copy that sets expectations
2. Feature framing (what this IS vs what it ISN'T)
3. Consistent terminology
4. "Why can't I..." answers

RULE: If someone expects email and gets something else,
they think it's broken. Set expectations on first contact.
"""

from dataclasses import dataclass
from typing import Dict, List


# =============================================================================
# PRODUCT FRAMING
# =============================================================================

PRODUCT_NAME = "Email Sensor"  # Internal name for the email feature
PRODUCT_TAGLINE = "Email as context, not another inbox"


# The core positioning statement
POSITIONING = """
This is NOT your email inbox. It's a sensor that surfaces relevant
communication alongside your work - automatically linking emails to
work orders, faults, and vendors.

Your email stays in Outlook/Gmail. This tool brings the relevant
pieces into context when you need them.
"""


# =============================================================================
# FEATURE FRAMING
# =============================================================================

@dataclass
class FeatureFrame:
    """How to describe each feature."""
    feature: str
    what_it_is: str
    what_it_isnt: str
    why_different: str


FEATURE_FRAMES: List[FeatureFrame] = [
    FeatureFrame(
        feature="Email Panel",
        what_it_is="A view of recent emails, filtered by relevance to your yacht",
        what_it_isnt="A full email client - no folders, no archive, no drafts",
        why_different="We show you what matters. Full email management stays in Outlook.",
    ),

    FeatureFrame(
        feature="Related Emails",
        what_it_is="Emails automatically surfaced alongside work orders and faults",
        what_it_isnt="A search you have to run every time",
        why_different="Context comes to you. You don't go hunting for it.",
    ),

    FeatureFrame(
        feature="Smart Linking",
        what_it_is="System suggestions for connecting emails to the right work items",
        what_it_isnt="Manual filing into folders",
        why_different="The system learns what relates to what. You confirm or correct.",
    ),

    FeatureFrame(
        feature="Email Search",
        what_it_is="Semantic search across your synced emails, focused on finding context",
        what_it_isnt="A replacement for Outlook search",
        why_different="Optimized for 'find the email about the generator fault', not 'find emails from John'.",
    ),

    FeatureFrame(
        feature="Read-Only View",
        what_it_is="Viewing emails in context - linking them to work items",
        what_it_isnt="Replying, forwarding, composing, deleting",
        why_different="This is about connecting information, not email workflow.",
    ),
]


# =============================================================================
# ONBOARDING COPY
# =============================================================================

ONBOARDING_SCREENS = [
    {
        "id": "welcome",
        "title": "Email as a Sensor",
        "body": "We're about to connect your email - but this isn't another inbox. "
                "It's a tool that automatically surfaces relevant emails alongside "
                "your work orders, faults, and maintenance tasks.",
        "cta": "Connect Email",
    },
    {
        "id": "what_happens",
        "title": "What Happens Next",
        "body": "We'll sync your recent emails (last 30 days) and create a searchable "
                "index. Your emails stay in Outlook - we just bring the relevant ones "
                "into context here.",
        "cta": "Got It",
    },
    {
        "id": "what_to_expect",
        "title": "What You'll See",
        "body": "• Emails automatically linked to work orders\n"
                "• Supplier communication surfaced on relevant items\n"
                "• Smart suggestions that learn from your corrections\n\n"
                "This is NOT for reading all your email. That's what Outlook is for.",
        "cta": "Start Sync",
    },
]


# =============================================================================
# "WHY CAN'T I..." ANSWERS
# =============================================================================

WHY_CANT_I: Dict[str, Dict[str, str]] = {
    "reply": {
        "question": "Why can't I reply to emails here?",
        "answer": "This tool is for context, not email workflow. Reply in Outlook - "
                  "it's better at that.",
        "suggestion": "Click 'Open in Outlook' to reply.",
    },

    "delete": {
        "question": "Why can't I delete emails?",
        "answer": "Your emails live in Outlook. We just show them here for context.",
        "suggestion": "Delete in Outlook if needed.",
    },

    "folders": {
        "question": "Where are my folders?",
        "answer": "We don't replicate your folder structure. This shows recent emails "
                  "from Inbox and Sent - the ones most likely to need linking.",
        "suggestion": "Use Outlook for folder-based organization.",
    },

    "archive": {
        "question": "Why can't I archive?",
        "answer": "Archiving is an email workflow action. This tool is about linking "
                  "emails to work items, not managing your mailbox.",
        "suggestion": "Archive in Outlook if you're done with an email.",
    },

    "compose": {
        "question": "Why can't I compose a new email?",
        "answer": "This isn't an email client. It's a sensor that connects your "
                  "existing emails to your work.",
        "suggestion": "Open Outlook to compose emails.",
    },

    "all_emails": {
        "question": "Why don't I see all my emails?",
        "answer": "We sync the last 30 days from Inbox and Sent. Older emails "
                  "and other folders stay in Outlook.",
        "suggestion": "Check Outlook for older emails or other folders.",
    },

    "attachments": {
        "question": "Why can't I download attachments here?",
        "answer": "Attachments are fetched from Microsoft on demand. "
                  "For full attachment management, use Outlook.",
        "suggestion": "Click 'View in Outlook' for full attachment access.",
    },
}


# =============================================================================
# CONSISTENT TERMINOLOGY
# =============================================================================

# Use these terms consistently across the product
TERMINOLOGY = {
    # Use
    "email_panel": "Email Panel",           # Not "Inbox"
    "link": "Link",                          # Not "File" or "Attach"
    "related": "Related Emails",             # Not "Associated" or "Connected"
    "suggestion": "Suggested Link",          # Not "Recommendation"
    "sync": "Sync",                          # Not "Import" or "Download"
    "context": "Context",                    # Core concept

    # Don't use
    "AVOID_inbox": "❌ Inbox (implies full email client)",
    "AVOID_mailbox": "❌ Mailbox (implies ownership)",
    "AVOID_folder": "❌ Folder (we don't have folders)",
    "AVOID_archive": "❌ Archive (not our action)",
    "AVOID_delete": "❌ Delete (not our action)",
}


# =============================================================================
# EMPTY STATE FRAMING
# =============================================================================

EMPTY_STATE_FRAMING = {
    "no_emails": {
        "title": "No Recent Emails",
        "message": "Your inbox might be empty, or emails are older than 30 days. "
                   "New emails will appear automatically.",
        "NOT": "❌ 'No emails found' (implies something's wrong)",
    },

    "no_related": {
        "title": "No Related Emails Yet",
        "message": "As you link emails, this gets smarter. Link your first email to start.",
        "NOT": "❌ 'Nothing here' (too vague)",
    },

    "no_suggestions": {
        "title": "No Confident Matches",
        "message": "We didn't find strong matches. You can search and link manually.",
        "NOT": "❌ 'No suggestions' (implies system failure)",
    },
}


# =============================================================================
# TOOLTIP COPY
# =============================================================================

TOOLTIPS = {
    "email_panel_toggle": "Show/hide the Email Panel - your recent emails filtered for relevance",
    "link_button": "Link this email to the current work item",
    "unlink_button": "Remove this email from the current work item",
    "suggestion_confirm": "Confirm this suggested link",
    "suggestion_dismiss": "Hide this suggestion (you can still link manually)",
    "open_in_outlook": "Open this email in Outlook for full features",
    "sync_status": "Last synced with your email account",
    "confidence_indicator": "How confident we are this email relates to this item",
}


# =============================================================================
# ERROR MESSAGE FRAMING
# =============================================================================

ERROR_FRAMING = {
    "sync_failed": {
        "title": "Sync Paused",
        "message": "We couldn't reach your email. Showing cached data.",
        "NOT": "❌ 'Failed to sync emails' (too alarming)",
    },

    "search_failed": {
        "title": "Search Limited",
        "message": "Smart search is temporarily unavailable. Basic text search still works.",
        "NOT": "❌ 'Search error' (too technical)",
    },

    "link_failed": {
        "title": "Couldn't Save Link",
        "message": "Please try again in a moment.",
        "NOT": "❌ 'Database error' (too technical)",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_feature_frame(feature_name: str) -> FeatureFrame:
    """Get framing for a specific feature."""
    for frame in FEATURE_FRAMES:
        if frame.feature.lower() == feature_name.lower():
            return frame
    return None


def get_why_cant_i(action: str) -> Dict[str, str]:
    """Get explanation for why an action isn't available."""
    return WHY_CANT_I.get(action, {
        "question": f"Why can't I {action}?",
        "answer": "This tool focuses on linking emails to work items. "
                  "For full email features, use Outlook.",
        "suggestion": "Open Outlook for full email management.",
    })


def get_onboarding_screen(screen_id: str) -> Dict[str, str]:
    """Get specific onboarding screen copy."""
    for screen in ONBOARDING_SCREENS:
        if screen["id"] == screen_id:
            return screen
    return None
