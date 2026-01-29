"""
Security Metrics Stubs
======================

Placeholder metrics for security observability.
These counters can be wired to Prometheus, StatsD, or cloud metrics.

Usage:
    from utils.security_metrics import SecurityMetrics

    SecurityMetrics.ownership_check_passed("equipment", "yacht-001")
    SecurityMetrics.ownership_check_failed("equipment", "yacht-001")
    SecurityMetrics.cross_yacht_attempt("yacht-001", "yacht-002", "read_equipment")
    SecurityMetrics.incident_mode_block("streaming", "yacht-001")
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS BACKEND STUB
# =============================================================================

class MetricsBackend:
    """
    Abstract metrics backend.

    In production, replace with Prometheus, StatsD, or cloud provider SDK.
    Default implementation logs to structured logger for later aggregation.
    """

    @staticmethod
    def increment(metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        tags = tags or {}
        logger.info(
            f"[METRIC] {metric_name}",
            extra={
                "metric_type": "counter",
                "metric_name": metric_name,
                "metric_value": value,
                "metric_tags": tags,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )

    @staticmethod
    def timing(metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric."""
        tags = tags or {}
        logger.info(
            f"[METRIC] {metric_name}",
            extra={
                "metric_type": "timing",
                "metric_name": metric_name,
                "metric_value": duration_ms,
                "metric_tags": tags,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )

    @staticmethod
    def gauge(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        tags = tags or {}
        logger.info(
            f"[METRIC] {metric_name}",
            extra={
                "metric_type": "gauge",
                "metric_name": metric_name,
                "metric_value": value,
                "metric_tags": tags,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )


# Global backend instance (can be swapped for testing or different environments)
_backend = MetricsBackend()


def set_metrics_backend(backend: MetricsBackend):
    """Set the metrics backend (for testing or different environments)."""
    global _backend
    _backend = backend


# =============================================================================
# SECURITY COUNTERS
# =============================================================================

class SecurityMetrics:
    """
    Security-specific metrics counters.

    All security events should be instrumented via this class.
    """

    # -------------------------------------------------------------------------
    # Ownership Validation
    # -------------------------------------------------------------------------

    @staticmethod
    def ownership_check_passed(entity_type: str, yacht_id: str):
        """Record successful ownership check."""
        _backend.increment(
            "security.ownership.passed",
            tags={"entity_type": entity_type, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def ownership_check_failed(entity_type: str, yacht_id: str):
        """Record failed ownership check (entity not found / wrong yacht)."""
        _backend.increment(
            "security.ownership.failed",
            tags={"entity_type": entity_type, "yacht_id": yacht_id[:8]}
        )

    # -------------------------------------------------------------------------
    # Cross-Yacht Attempts
    # -------------------------------------------------------------------------

    @staticmethod
    def cross_yacht_attempt(
        source_yacht_id: str,
        target_yacht_id: str,
        action: str,
    ):
        """Record cross-yacht access attempt (potential attack)."""
        _backend.increment(
            "security.cross_yacht.attempt",
            tags={
                "source_yacht": source_yacht_id[:8],
                "target_yacht": target_yacht_id[:8],
                "action": action,
            }
        )
        # Also log as warning for immediate visibility
        logger.warning(
            f"[SECURITY] Cross-yacht attempt: {source_yacht_id[:8]} -> {target_yacht_id[:8]} ({action})"
        )

    # -------------------------------------------------------------------------
    # Role/Permission Checks
    # -------------------------------------------------------------------------

    @staticmethod
    def role_check_passed(role: str, action: str, yacht_id: str):
        """Record successful role check."""
        _backend.increment(
            "security.role.passed",
            tags={"role": role, "action": action, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def role_check_failed(role: str, required_roles: str, action: str, yacht_id: str):
        """Record failed role check."""
        _backend.increment(
            "security.role.failed",
            tags={
                "role": role,
                "required": required_roles,
                "action": action,
                "yacht_id": yacht_id[:8],
            }
        )

    # -------------------------------------------------------------------------
    # Incident Mode
    # -------------------------------------------------------------------------

    @staticmethod
    def incident_mode_block(operation: str, yacht_id: str):
        """Record operation blocked by incident mode."""
        _backend.increment(
            "security.incident_mode.block",
            tags={"operation": operation, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def incident_mode_activated(reason: str):
        """Record incident mode activation."""
        _backend.increment("security.incident_mode.activated", tags={"reason": reason})
        logger.warning(f"[SECURITY] Incident mode ACTIVATED: {reason}")

    @staticmethod
    def incident_mode_deactivated():
        """Record incident mode deactivation."""
        _backend.increment("security.incident_mode.deactivated")
        logger.info("[SECURITY] Incident mode DEACTIVATED")

    # -------------------------------------------------------------------------
    # Yacht Freeze
    # -------------------------------------------------------------------------

    @staticmethod
    def yacht_freeze_block(operation: str, yacht_id: str):
        """Record operation blocked by yacht freeze."""
        _backend.increment(
            "security.yacht_freeze.block",
            tags={"operation": operation, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def yacht_frozen(yacht_id: str, reason: str):
        """Record yacht freeze event."""
        _backend.increment(
            "security.yacht_freeze.activated",
            tags={"yacht_id": yacht_id[:8], "reason": reason}
        )

    @staticmethod
    def yacht_unfrozen(yacht_id: str):
        """Record yacht unfreeze event."""
        _backend.increment(
            "security.yacht_freeze.deactivated",
            tags={"yacht_id": yacht_id[:8]}
        )

    # -------------------------------------------------------------------------
    # Signed URL Security
    # -------------------------------------------------------------------------

    @staticmethod
    def signed_url_generated(url_type: str, yacht_id: str):
        """Record signed URL generation."""
        _backend.increment(
            "security.signed_url.generated",
            tags={"type": url_type, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def signed_url_blocked(reason: str, yacht_id: str):
        """Record blocked signed URL generation."""
        _backend.increment(
            "security.signed_url.blocked",
            tags={"reason": reason, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def path_traversal_attempt(path: str, yacht_id: str):
        """Record path traversal attempt."""
        _backend.increment(
            "security.path_traversal.attempt",
            tags={"yacht_id": yacht_id[:8]}
        )
        # Log warning but sanitize path
        safe_path = path[:50] if len(path) > 50 else path
        logger.warning(
            f"[SECURITY] Path traversal attempt: yacht={yacht_id[:8]}, path={safe_path}..."
        )

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    @staticmethod
    def auth_success(user_id: str, yacht_id: str):
        """Record successful authentication."""
        _backend.increment(
            "security.auth.success",
            tags={"user_id": user_id[:8], "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def auth_failure(reason: str):
        """Record authentication failure."""
        _backend.increment("security.auth.failure", tags={"reason": reason})

    @staticmethod
    def jwt_expired():
        """Record JWT expiration."""
        _backend.increment("security.jwt.expired")

    @staticmethod
    def jwt_invalid(reason: str):
        """Record invalid JWT."""
        _backend.increment("security.jwt.invalid", tags={"reason": reason})

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------

    @staticmethod
    def rate_limit_exceeded(endpoint: str, yacht_id: str, user_id: str):
        """Record rate limit exceeded."""
        _backend.increment(
            "security.rate_limit.exceeded",
            tags={
                "endpoint": endpoint,
                "yacht_id": yacht_id[:8],
                "user_id": user_id[:8],
            }
        )

    # -------------------------------------------------------------------------
    # Streaming Safety
    # -------------------------------------------------------------------------

    @staticmethod
    def streaming_rate_limit(yacht_id: str, user_id: str):
        """Record streaming rate limit hit."""
        _backend.increment(
            "security.streaming.rate_limit",
            tags={"yacht_id": yacht_id[:8], "user_id": user_id[:8]}
        )

    @staticmethod
    def streaming_cancelled(yacht_id: str, reason: str):
        """Record streaming cancellation."""
        _backend.increment(
            "security.streaming.cancelled",
            tags={"yacht_id": yacht_id[:8], "reason": reason}
        )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    @staticmethod
    def audit_write_success(action: str, yacht_id: str):
        """Record successful audit write."""
        _backend.increment(
            "security.audit.write_success",
            tags={"action": action, "yacht_id": yacht_id[:8]}
        )

    @staticmethod
    def audit_write_failure(action: str, yacht_id: str, error: str):
        """Record audit write failure."""
        _backend.increment(
            "security.audit.write_failure",
            tags={"action": action, "yacht_id": yacht_id[:8], "error": error}
        )
        # This is critical - audit failures should alert
        logger.error(f"[SECURITY] Audit write FAILED: yacht={yacht_id[:8]}, action={action}, error={error}")

    # -------------------------------------------------------------------------
    # SQL Injection Detection
    # -------------------------------------------------------------------------

    @staticmethod
    def sql_injection_attempt(input_type: str, yacht_id: str):
        """Record potential SQL injection attempt."""
        _backend.increment(
            "security.sql_injection.attempt",
            tags={"input_type": input_type, "yacht_id": yacht_id[:8]}
        )
        logger.warning(f"[SECURITY] SQL injection attempt detected: yacht={yacht_id[:8]}, input={input_type}")

    # -------------------------------------------------------------------------
    # Handler Security
    # -------------------------------------------------------------------------

    @staticmethod
    def unsecured_handler_detected(handler_name: str):
        """Record detection of unsecured handler (critical)."""
        _backend.increment(
            "security.handler.unsecured",
            tags={"handler": handler_name}
        )
        logger.critical(f"[SECURITY] Unsecured handler detected: {handler_name}")

    @staticmethod
    def handler_execution_denied(handler_name: str, reason: str, yacht_id: str):
        """Record denied handler execution."""
        _backend.increment(
            "security.handler.denied",
            tags={"handler": handler_name, "reason": reason, "yacht_id": yacht_id[:8]}
        )


# =============================================================================
# DECORATOR FOR AUTOMATIC TIMING
# =============================================================================

def timed_security_operation(operation_name: str):
    """Decorator to time security operations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                _backend.timing(
                    f"security.operation.{operation_name}",
                    duration_ms,
                    tags={"status": "success"}
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                _backend.timing(
                    f"security.operation.{operation_name}",
                    duration_ms,
                    tags={"status": "error", "error_type": type(e).__name__}
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                _backend.timing(
                    f"security.operation.{operation_name}",
                    duration_ms,
                    tags={"status": "success"}
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                _backend.timing(
                    f"security.operation.{operation_name}",
                    duration_ms,
                    tags={"status": "error", "error_type": type(e).__name__}
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
