"""
CelesteOS Backend - Feature Flags

Feature flags for gradual rollout and fail-closed behavior.
All email transport layer features default to OFF.

Updated: 2026-01-27 - Added Fault Lens v1 canary flag
"""

import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FAULT LENS V1 FLAGS (default: OFF - fail-closed)
# ============================================================================

# Master canary flag for Fault Lens v1
# Set to 'true' ONLY for canary yacht during initial rollout
FAULT_LENS_V1_ENABLED = os.getenv('FAULT_LENS_V1_ENABLED', 'false').lower() == 'true'

# Individual feature flags for granular control
FAULT_LENS_SUGGESTIONS_ENABLED = os.getenv('FAULT_LENS_SUGGESTIONS_ENABLED', 'false').lower() == 'true'
FAULT_LENS_RELATED_ENABLED = os.getenv('FAULT_LENS_RELATED_ENABLED', 'false').lower() == 'true'
FAULT_LENS_WARRANTY_ENABLED = os.getenv('FAULT_LENS_WARRANTY_ENABLED', 'false').lower() == 'true'
FAULT_LENS_SIGNED_ACTIONS_ENABLED = os.getenv('FAULT_LENS_SIGNED_ACTIONS_ENABLED', 'false').lower() == 'true'

logger.info(f"[FeatureFlags] FAULT_LENS_V1_ENABLED={FAULT_LENS_V1_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_SUGGESTIONS_ENABLED={FAULT_LENS_SUGGESTIONS_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_RELATED_ENABLED={FAULT_LENS_RELATED_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_WARRANTY_ENABLED={FAULT_LENS_WARRANTY_ENABLED}")
logger.info(f"[FeatureFlags] FAULT_LENS_SIGNED_ACTIONS_ENABLED={FAULT_LENS_SIGNED_ACTIONS_ENABLED}")

# ============================================================================
# EMAIL TRANSPORT LAYER FLAGS (default: OFF)
# ============================================================================

# Master kill switch - if False, ALL email endpoints return 503
# Changed default to TRUE to enable email transport layer
EMAIL_TRANSPORT_ENABLED = os.getenv('EMAIL_TRANSPORT_ENABLED', 'true').lower() == 'true'

# Individual feature flags - all enabled by default
EMAIL_RELATED_ENABLED = os.getenv('EMAIL_RELATED_ENABLED', 'true').lower() == 'true'
EMAIL_THREAD_ENABLED = os.getenv('EMAIL_THREAD_ENABLED', 'true').lower() == 'true'
EMAIL_RENDER_ENABLED = os.getenv('EMAIL_RENDER_ENABLED', 'true').lower() == 'true'
EMAIL_LINK_ENABLED = os.getenv('EMAIL_LINK_ENABLED', 'true').lower() == 'true'
EMAIL_SYNC_ENABLED = os.getenv('EMAIL_SYNC_ENABLED', 'true').lower() == 'true'
EMAIL_EVIDENCE_ENABLED = os.getenv('EMAIL_EVIDENCE_ENABLED', 'true').lower() == 'true'
EMAIL_SEARCH_ENABLED = os.getenv('EMAIL_SEARCH_ENABLED', 'true').lower() == 'true'
EMAIL_FOCUS_ENABLED = os.getenv('EMAIL_FOCUS_ENABLED', 'true').lower() == 'true'

# Log flag status on startup
logger.info(f"[FeatureFlags] EMAIL_TRANSPORT_ENABLED={EMAIL_TRANSPORT_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_RELATED_ENABLED={EMAIL_RELATED_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_THREAD_ENABLED={EMAIL_THREAD_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_RENDER_ENABLED={EMAIL_RENDER_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_LINK_ENABLED={EMAIL_LINK_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_SYNC_ENABLED={EMAIL_SYNC_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_EVIDENCE_ENABLED={EMAIL_EVIDENCE_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_SEARCH_ENABLED={EMAIL_SEARCH_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_FOCUS_ENABLED={EMAIL_FOCUS_ENABLED}")


def check_email_feature(feature_name: str) -> tuple[bool, str]:
    """
    Check if an email feature is enabled.
    Returns (enabled, error_message).

    Fail-closed: if master switch is off, all features are disabled.
    """
    if not EMAIL_TRANSPORT_ENABLED:
        return False, "Email transport layer is disabled"

    flags = {
        'related': EMAIL_RELATED_ENABLED,
        'thread': EMAIL_THREAD_ENABLED,
        'render': EMAIL_RENDER_ENABLED,
        'link': EMAIL_LINK_ENABLED,
        'sync': EMAIL_SYNC_ENABLED,
        'evidence': EMAIL_EVIDENCE_ENABLED,
        'search': EMAIL_SEARCH_ENABLED,
        'focus': EMAIL_FOCUS_ENABLED,
    }

    enabled = flags.get(feature_name, False)
    if not enabled:
        return False, f"Email feature '{feature_name}' is disabled"

    return True, ""


def check_fault_lens_feature(feature_name: str) -> tuple[bool, str]:
    """
    Check if a Fault Lens feature is enabled.
    Returns (enabled, error_message).

    Fail-closed: if master switch is off, all features are disabled.
    """
    if not FAULT_LENS_V1_ENABLED:
        return False, "Fault Lens v1 is disabled (canary flag off)"

    flags = {
        'suggestions': FAULT_LENS_SUGGESTIONS_ENABLED,
        'related': FAULT_LENS_RELATED_ENABLED,
        'warranty': FAULT_LENS_WARRANTY_ENABLED,
        'signed_actions': FAULT_LENS_SIGNED_ACTIONS_ENABLED,
    }

    enabled = flags.get(feature_name, False)
    if not enabled:
        return False, f"Fault Lens feature '{feature_name}' is disabled"

    return True, ""


__all__ = [
    # Email flags
    'EMAIL_TRANSPORT_ENABLED',
    'EMAIL_RELATED_ENABLED',
    'EMAIL_THREAD_ENABLED',
    'EMAIL_RENDER_ENABLED',
    'EMAIL_LINK_ENABLED',
    'EMAIL_SYNC_ENABLED',
    'EMAIL_EVIDENCE_ENABLED',
    'EMAIL_SEARCH_ENABLED',
    'EMAIL_FOCUS_ENABLED',
    'check_email_feature',
    # Fault Lens flags
    'FAULT_LENS_V1_ENABLED',
    'FAULT_LENS_SUGGESTIONS_ENABLED',
    'FAULT_LENS_RELATED_ENABLED',
    'FAULT_LENS_WARRANTY_ENABLED',
    'FAULT_LENS_SIGNED_ACTIONS_ENABLED',
    'check_fault_lens_feature',
]
