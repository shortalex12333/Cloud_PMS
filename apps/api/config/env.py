"""
CelesteOS API - Environment Configuration
==========================================

Typed settings with secure defaults (deny-by-default).

Usage:
    from config.env import settings, validate_startup

    # Access settings
    if settings.email.search_enabled:
        # enable email search route
        pass

    # Validate on startup (fails fast if critical envs missing)
    validate_startup()

Security:
    - All sensitive features default to DISABLED
    - Critical auth envs required in non-dev environments
    - No secrets are logged or exposed
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def get_environment() -> Environment:
    """Detect current environment from ENVIRONMENT env var."""
    env_str = os.getenv("ENVIRONMENT", "development").lower()
    try:
        return Environment(env_str)
    except ValueError:
        logger.warning(f"Unknown ENVIRONMENT '{env_str}', defaulting to development")
        return Environment.DEVELOPMENT


# =============================================================================
# FEATURE FLAG HELPERS
# =============================================================================

def _bool_env(key: str, default: bool = False) -> bool:
    """Parse boolean environment variable. Defaults to False (deny-by-default)."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


def _int_env(key: str, default: int) -> int:
    """Parse integer environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer for {key}: '{value}', using default {default}")
        return default


def _str_env(key: str, default: str = "") -> str:
    """Get string environment variable."""
    return os.getenv(key, default)


# =============================================================================
# SETTINGS DATACLASSES
# =============================================================================

@dataclass
class IdentitySettings:
    """MASTER and TENANT database configuration."""
    # MASTER Supabase (auth/control plane)
    master_supabase_url: str = field(default_factory=lambda: _str_env("MASTER_SUPABASE_URL"))
    master_supabase_service_key: str = field(default_factory=lambda: _str_env("MASTER_SUPABASE_SERVICE_KEY"))
    master_supabase_jwt_secret: str = field(default_factory=lambda: _str_env("MASTER_SUPABASE_JWT_SECRET"))

    # TENANT Supabase (per-yacht data plane) - can also use generic fallback
    tenant_supabase_jwt_secret: str = field(default_factory=lambda: _str_env("TENANT_SUPABASE_JWT_SECRET"))

    # Default yacht for fallback routing
    default_yacht_code: str = field(default_factory=lambda: _str_env("DEFAULT_YACHT_CODE", "yTEST_YACHT_001"))

    @property
    def is_configured(self) -> bool:
        """Check if critical identity settings are configured."""
        return bool(self.master_supabase_url and self.master_supabase_service_key)

    @property
    def jwt_secret(self) -> str:
        """Get primary JWT secret (prefer MASTER, fallback to TENANT)."""
        return self.master_supabase_jwt_secret or self.tenant_supabase_jwt_secret


@dataclass
class EmailSettings:
    """Email feature flags. All default to DISABLED (deny-by-default)."""
    evidence_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_EVIDENCE_ENABLED", False))
    focus_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_FOCUS_ENABLED", False))
    link_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_LINK_ENABLED", False))
    related_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_RELATED_ENABLED", False))
    render_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_RENDER_ENABLED", False))
    search_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_SEARCH_ENABLED", False))
    sync_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_SYNC_ENABLED", False))
    thread_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_THREAD_ENABLED", False))
    transport_enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_TRANSPORT_ENABLED", False))

    @property
    def any_enabled(self) -> bool:
        """Check if any email feature is enabled."""
        return any([
            self.evidence_enabled, self.focus_enabled, self.link_enabled,
            self.related_enabled, self.render_enabled, self.search_enabled,
            self.sync_enabled, self.thread_enabled, self.transport_enabled
        ])


@dataclass
class FaultLensSettings:
    """Fault Lens and Certificate feature flags."""
    signed_actions_enabled: bool = field(default_factory=lambda: _bool_env("FAULT_LENS_SIGNED_ACTIONS_ENABLED", False))
    suggestions_enabled: bool = field(default_factory=lambda: _bool_env("FAULT_LENS_SUGGESTIONS_ENABLED", False))
    v1_enabled: bool = field(default_factory=lambda: _bool_env("FAULT_LENS_V1_ENABLED", False))

    # Certificate features
    feature_certificates: bool = field(default_factory=lambda: _bool_env("FEATURE_CERTIFICATES", False))
    ui_certificates: bool = field(default_factory=lambda: _bool_env("UI_CERTIFICATES", False))


@dataclass
class WorkerSettings:
    """Worker and streaming concurrency settings."""
    max_concurrent_global: int = field(default_factory=lambda: _int_env("MAX_CONCURRENT_GLOBAL", 50))
    max_concurrent_per_watcher: int = field(default_factory=lambda: _int_env("MAX_CONCURRENT_PER_WATCHER", 5))
    batch_size: int = field(default_factory=lambda: _int_env("WORKER_BATCH_SIZE", 10))
    poll_interval: int = field(default_factory=lambda: _int_env("WORKER_POLL_INTERVAL", 30))
    staging_mode: bool = field(default_factory=lambda: _bool_env("WORKER_STAGING_MODE", True))

    @property
    def is_production_mode(self) -> bool:
        """Check if workers are in production mode."""
        return not self.staging_mode


@dataclass
class AISettings:
    """AI/LLM and external service configuration."""
    openai_api_key: str = field(default_factory=lambda: _str_env("OPENAI_API_KEY"))

    # Azure Graph API (for email)
    azure_read_app_id: str = field(default_factory=lambda: _str_env("AZURE_READ_APP_ID"))
    azure_read_client_secret: str = field(default_factory=lambda: _str_env("AZURE_READ_CLIENT_SECRET"))
    azure_write_app_id: str = field(default_factory=lambda: _str_env("AZURE_WRITE_APP_ID"))
    azure_write_client_secret: str = field(default_factory=lambda: _str_env("AZURE_WRITE_CLIENT_SECRET"))

    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.openai_api_key)

    @property
    def azure_read_configured(self) -> bool:
        """Check if Azure read is configured."""
        return bool(self.azure_read_app_id and self.azure_read_client_secret)

    @property
    def azure_write_configured(self) -> bool:
        """Check if Azure write is configured."""
        return bool(self.azure_write_app_id and self.azure_write_client_secret)


@dataclass
class InfraSettings:
    """Infrastructure and logging settings."""
    pythonpath: str = field(default_factory=lambda: _str_env("PYTHONPATH", "."))
    log_level: str = field(default_factory=lambda: _str_env("LOG_LEVEL", "INFO"))
    port: int = field(default_factory=lambda: _int_env("PORT", 8000))

    # Incident mode cache TTL (seconds)
    system_flags_cache_ttl: int = field(default_factory=lambda: _int_env("SYSTEM_FLAGS_CACHE_TTL", 10))


@dataclass
class Settings:
    """Root settings object combining all configuration."""
    environment: Environment = field(default_factory=get_environment)
    identity: IdentitySettings = field(default_factory=IdentitySettings)
    email: EmailSettings = field(default_factory=EmailSettings)
    fault_lens: FaultLensSettings = field(default_factory=FaultLensSettings)
    worker: WorkerSettings = field(default_factory=WorkerSettings)
    ai: AISettings = field(default_factory=AISettings)
    infra: InfraSettings = field(default_factory=InfraSettings)

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.environment == Environment.TEST


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global settings instance (loaded once at import)
settings = Settings()


# =============================================================================
# STARTUP VALIDATION
# =============================================================================

class ConfigurationError(Exception):
    """Raised when critical configuration is missing."""
    pass


def validate_startup() -> Dict[str, Any]:
    """
    Validate configuration on startup. Fails fast if critical envs missing.

    Returns:
        Dict with validation results (for logging/debugging)

    Raises:
        ConfigurationError: If critical configuration is missing in non-dev
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check identity configuration
    if not settings.identity.master_supabase_url:
        if settings.is_production or settings.is_staging:
            errors.append("MASTER_SUPABASE_URL is required")
        else:
            warnings.append("MASTER_SUPABASE_URL not set (OK for development)")

    if not settings.identity.master_supabase_service_key:
        if settings.is_production or settings.is_staging:
            errors.append("MASTER_SUPABASE_SERVICE_KEY is required")
        else:
            warnings.append("MASTER_SUPABASE_SERVICE_KEY not set (OK for development)")

    if not settings.identity.jwt_secret:
        if settings.is_production or settings.is_staging:
            errors.append("JWT secret is required (MASTER_SUPABASE_JWT_SECRET or TENANT_SUPABASE_JWT_SECRET)")
        else:
            warnings.append("JWT secret not set (OK for development)")

    # Check AI configuration
    if not settings.ai.openai_configured:
        warnings.append("OPENAI_API_KEY not set - AI features disabled")

    # Check Azure configuration
    if settings.email.any_enabled and not settings.ai.azure_read_configured:
        warnings.append("Email features enabled but Azure read not configured")

    # Check worker mode
    if settings.is_production and settings.worker.staging_mode:
        warnings.append("WORKER_STAGING_MODE=true in production - workers may not run")

    # Build result
    result = {
        "environment": settings.environment.value,
        "errors": errors,
        "warnings": warnings,
        "features": get_feature_summary(),
    }

    # Log warnings
    for warning in warnings:
        logger.warning(f"[Config] {warning}")

    # Fail fast on errors in non-dev
    if errors:
        for error in errors:
            logger.error(f"[Config] CRITICAL: {error}")

        if not settings.is_development and not settings.is_test:
            raise ConfigurationError(f"Missing critical configuration: {', '.join(errors)}")

    return result


def get_feature_summary() -> Dict[str, bool]:
    """
    Get summary of enabled features (for logging).

    Returns:
        Dict of feature_name -> enabled status
    """
    return {
        # Email features
        "email_evidence": settings.email.evidence_enabled,
        "email_focus": settings.email.focus_enabled,
        "email_link": settings.email.link_enabled,
        "email_related": settings.email.related_enabled,
        "email_render": settings.email.render_enabled,
        "email_search": settings.email.search_enabled,
        "email_sync": settings.email.sync_enabled,
        "email_thread": settings.email.thread_enabled,
        "email_transport": settings.email.transport_enabled,
        # Fault Lens features
        "fault_lens_signed_actions": settings.fault_lens.signed_actions_enabled,
        "fault_lens_suggestions": settings.fault_lens.suggestions_enabled,
        "fault_lens_v1": settings.fault_lens.v1_enabled,
        # Certificate features
        "certificates_backend": settings.fault_lens.feature_certificates,
        "certificates_ui": settings.fault_lens.ui_certificates,
        # Worker mode
        "worker_staging_mode": settings.worker.staging_mode,
        # AI
        "openai_configured": settings.ai.openai_configured,
        "azure_read_configured": settings.ai.azure_read_configured,
        "azure_write_configured": settings.ai.azure_write_configured,
    }


def log_startup_config():
    """
    Log startup configuration (redacted - no secrets).

    Call this after validate_startup() in main.py.
    """
    summary = get_feature_summary()

    logger.info("=" * 60)
    logger.info("[Config] CelesteOS API Configuration")
    logger.info("=" * 60)
    logger.info(f"[Config] Environment: {settings.environment.value}")
    logger.info(f"[Config] Log Level: {settings.infra.log_level}")
    logger.info(f"[Config] Port: {settings.infra.port}")
    logger.info("")
    logger.info("[Config] Identity:")
    logger.info(f"  MASTER_SUPABASE_URL: {'configured' if settings.identity.master_supabase_url else 'NOT SET'}")
    logger.info(f"  MASTER_SUPABASE_SERVICE_KEY: {'configured' if settings.identity.master_supabase_service_key else 'NOT SET'}")
    logger.info(f"  JWT_SECRET: {'configured' if settings.identity.jwt_secret else 'NOT SET'}")
    logger.info(f"  DEFAULT_YACHT_CODE: {settings.identity.default_yacht_code}")
    logger.info("")
    logger.info("[Config] Features Enabled:")
    for feature, enabled in summary.items():
        status = "ENABLED" if enabled else "disabled"
        logger.info(f"  {feature}: {status}")
    logger.info("")
    logger.info("[Config] Worker Settings:")
    logger.info(f"  MAX_CONCURRENT_GLOBAL: {settings.worker.max_concurrent_global}")
    logger.info(f"  MAX_CONCURRENT_PER_WATCHER: {settings.worker.max_concurrent_per_watcher}")
    logger.info(f"  WORKER_BATCH_SIZE: {settings.worker.batch_size}")
    logger.info(f"  WORKER_POLL_INTERVAL: {settings.worker.poll_interval}s")
    logger.info(f"  WORKER_STAGING_MODE: {settings.worker.staging_mode}")
    logger.info("=" * 60)


# =============================================================================
# FEATURE FLAG HELPERS (for route guards)
# =============================================================================

def require_feature(feature_name: str, enabled: bool):
    """
    Decorator factory to guard routes by feature flag.

    Usage:
        @app.get("/email/search")
        @require_feature("email_search", settings.email.search_enabled)
        async def email_search():
            ...

    Raises:
        HTTPException(404) if feature is disabled
    """
    from functools import wraps
    from fastapi import HTTPException

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not enabled:
                raise HTTPException(
                    status_code=404,
                    detail="Not found"  # Generic to prevent enumeration
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_feature_enabled(feature_name: str, enabled: bool) -> None:
    """
    Check if feature is enabled. Raises HTTPException(404) if not.

    Usage:
        check_feature_enabled("email_search", settings.email.search_enabled)
    """
    from fastapi import HTTPException

    if not enabled:
        logger.debug(f"[Config] Feature '{feature_name}' is disabled - returning 404")
        raise HTTPException(status_code=404, detail="Not found")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Settings
    "Settings",
    "settings",
    "Environment",
    # Validation
    "validate_startup",
    "log_startup_config",
    "get_feature_summary",
    "ConfigurationError",
    # Feature guards
    "require_feature",
    "check_feature_enabled",
]
