"""
CelesteOS Backend - Feature Flags

Feature flags for gradual rollout and fail-closed behavior.
All email transport layer features default to OFF.

Updated: 2026-01-17 - Force rebuild for env var refresh
"""

import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# EMAIL TRANSPORT LAYER FLAGS (default: OFF)
# ============================================================================

# Master kill switch - if False, ALL email endpoints return 503
EMAIL_TRANSPORT_ENABLED = os.getenv('EMAIL_TRANSPORT_ENABLED', 'false').lower() == 'true'

# Individual feature flags
EMAIL_RELATED_ENABLED = os.getenv('EMAIL_RELATED_ENABLED', 'false').lower() == 'true'
EMAIL_THREAD_ENABLED = os.getenv('EMAIL_THREAD_ENABLED', 'false').lower() == 'true'
EMAIL_RENDER_ENABLED = os.getenv('EMAIL_RENDER_ENABLED', 'false').lower() == 'true'
EMAIL_LINK_ENABLED = os.getenv('EMAIL_LINK_ENABLED', 'false').lower() == 'true'
EMAIL_SYNC_ENABLED = os.getenv('EMAIL_SYNC_ENABLED', 'false').lower() == 'true'
EMAIL_EVIDENCE_ENABLED = os.getenv('EMAIL_EVIDENCE_ENABLED', 'false').lower() == 'true'

# Log flag status on startup
logger.info(f"[FeatureFlags] EMAIL_TRANSPORT_ENABLED={EMAIL_TRANSPORT_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_RELATED_ENABLED={EMAIL_RELATED_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_THREAD_ENABLED={EMAIL_THREAD_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_RENDER_ENABLED={EMAIL_RENDER_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_LINK_ENABLED={EMAIL_LINK_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_SYNC_ENABLED={EMAIL_SYNC_ENABLED}")
logger.info(f"[FeatureFlags] EMAIL_EVIDENCE_ENABLED={EMAIL_EVIDENCE_ENABLED}")


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
    }

    enabled = flags.get(feature_name, False)
    if not enabled:
        return False, f"Email feature '{feature_name}' is disabled"

    return True, ""


__all__ = [
    'EMAIL_TRANSPORT_ENABLED',
    'EMAIL_RELATED_ENABLED',
    'EMAIL_THREAD_ENABLED',
    'EMAIL_RENDER_ENABLED',
    'EMAIL_LINK_ENABLED',
    'EMAIL_SYNC_ENABLED',
    'EMAIL_EVIDENCE_ENABLED',
    'check_email_feature',
]
