"""
CelesteOS API - Configuration Package
======================================

Typed settings with secure defaults.

Usage:
    from config import settings, validate_startup, log_startup_config

    # On startup
    validate_startup()
    log_startup_config()

    # Access settings
    if settings.email.search_enabled:
        # enable route
        pass
"""

from config.env import (
    Settings,
    settings,
    Environment,
    validate_startup,
    log_startup_config,
    get_feature_summary,
    ConfigurationError,
    require_feature,
    check_feature_enabled,
)

__all__ = [
    "Settings",
    "settings",
    "Environment",
    "validate_startup",
    "log_startup_config",
    "get_feature_summary",
    "ConfigurationError",
    "require_feature",
    "check_feature_enabled",
]
