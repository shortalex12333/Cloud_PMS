"""
CelesteOS Action Router - Secure Dispatcher
============================================

Security-enforcing dispatcher that validates all handlers have @secure_action.

Registry startup gate: Importing this module validates all registered handlers.
Router MUST NOT start if any handler lacks @secure_action decorator.

Usage:
    from action_router.dispatchers.secure_dispatcher import (
        validate_registry_security,
        SecureDispatcher,
    )

    # At startup (before router accepts requests)
    validate_registry_security()  # Raises RegistrySecurityError if violated
"""

from typing import Dict, Any, List, Callable, Optional
import logging
import os

logger = logging.getLogger(__name__)


class RegistrySecurityError(Exception):
    """
    Raised when registry startup security validation fails.

    This is a FATAL error - the router must not start.
    """

    def __init__(self, unsecured_handlers: List[str], message: str = None):
        self.unsecured_handlers = unsecured_handlers
        self.message = message or f"Registry contains {len(unsecured_handlers)} unsecured handlers: {unsecured_handlers}"
        super().__init__(self.message)


class HandlerNotFoundError(Exception):
    """Raised when no handler is found for an action."""

    def __init__(self, action_id: str):
        self.action_id = action_id
        super().__init__(f"No handler registered for action: {action_id}")


def _get_handler_mapping() -> Dict[str, Callable]:
    """
    Get mapping of action_id -> handler function.

    Returns handlers from internal_dispatcher.HANDLERS.
    """
    try:
        from action_router.dispatchers.internal_dispatcher import HANDLERS
        return HANDLERS
    except ImportError:
        # Fallback for testing
        return {}


def _get_action_registry() -> Dict[str, Any]:
    """Get the action registry."""
    try:
        from action_router.registry import ACTION_REGISTRY
        return ACTION_REGISTRY
    except ImportError:
        return {}


def validate_handler_security(handler: Callable) -> bool:
    """
    Validate a single handler has @secure_action decorator.

    Returns:
        True if handler has _secure_action=True attribute
    """
    return getattr(handler, '_secure_action', False) is True


def get_unsecured_handlers(handlers: Dict[str, Callable]) -> List[str]:
    """
    Find all handlers lacking @secure_action decorator.

    Args:
        handlers: Dict mapping action_id to handler function

    Returns:
        List of action_ids with unsecured handlers
    """
    unsecured = []

    for action_id, handler in handlers.items():
        if not validate_handler_security(handler):
            unsecured.append(action_id)

    return unsecured


def validate_registry_security(
    handlers: Dict[str, Callable] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Validate all registered handlers have @secure_action decorator.

    This is the REGISTRY STARTUP GATE. Must be called before router accepts requests.

    Args:
        handlers: Handler mapping (defaults to internal_dispatcher.HANDLERS)
        strict: If True, raises RegistrySecurityError for violations

    Returns:
        Dict with validation results:
        {
            "valid": bool,
            "total_handlers": int,
            "secured_handlers": int,
            "unsecured_handlers": List[str],
        }

    Raises:
        RegistrySecurityError: If strict=True and unsecured handlers found
    """
    if handlers is None:
        handlers = _get_handler_mapping()

    unsecured = get_unsecured_handlers(handlers)

    result = {
        "valid": len(unsecured) == 0,
        "total_handlers": len(handlers),
        "secured_handlers": len(handlers) - len(unsecured),
        "unsecured_handlers": unsecured,
    }

    if unsecured:
        logger.error(
            f"[RegistrySecurityGate] FAILED: {len(unsecured)} unsecured handlers: {unsecured}"
        )

        if strict:
            raise RegistrySecurityError(unsecured)
    else:
        logger.info(
            f"[RegistrySecurityGate] PASSED: {len(handlers)} handlers secured"
        )

    return result


def get_handler_security_report(handlers: Dict[str, Callable] = None) -> Dict[str, Any]:
    """
    Generate security report for all handlers.

    Returns detailed metadata for each handler including:
    - action_id
    - secured: bool
    - action_group: str (READ/MUTATE/SIGNED/ADMIN)
    - required_roles: List[str]
    - validate_entities: List[str]

    Args:
        handlers: Handler mapping (defaults to internal_dispatcher.HANDLERS)

    Returns:
        Dict with handler details and summary
    """
    if handlers is None:
        handlers = _get_handler_mapping()

    report = {
        "handlers": [],
        "summary": {
            "total": len(handlers),
            "secured": 0,
            "unsecured": 0,
            "by_group": {"READ": 0, "MUTATE": 0, "SIGNED": 0, "ADMIN": 0},
        },
    }

    for action_id, handler in handlers.items():
        secured = validate_handler_security(handler)

        handler_info = {
            "action_id": action_id,
            "secured": secured,
            "action_group": getattr(handler, '_action_group', None),
            "required_roles": getattr(handler, '_required_roles', []),
            "validate_entities": getattr(handler, '_validate_entities', []),
        }
        report["handlers"].append(handler_info)

        if secured:
            report["summary"]["secured"] += 1
            group = handler_info["action_group"]
            if group in report["summary"]["by_group"]:
                report["summary"]["by_group"][group] += 1
        else:
            report["summary"]["unsecured"] += 1

    return report


class SecureDispatcher:
    """
    Security-enforcing action dispatcher.

    Wraps handlers with additional security validation at dispatch time.

    Usage:
        dispatcher = SecureDispatcher(handlers)
        result = await dispatcher.dispatch(action_id, ctx, **params)
    """

    def __init__(
        self,
        handlers: Dict[str, Callable] = None,
        validate_on_init: bool = True,
        strict: bool = True,
    ):
        """
        Initialize secure dispatcher.

        Args:
            handlers: Handler mapping (defaults to internal_dispatcher.HANDLERS)
            validate_on_init: Validate all handlers on init
            strict: Raise error for unsecured handlers
        """
        self.handlers = handlers or _get_handler_mapping()
        self._validated = False

        if validate_on_init:
            self.validate_security(strict=strict)

    def validate_security(self, strict: bool = True) -> Dict[str, Any]:
        """
        Validate all handlers have security decorator.

        Args:
            strict: Raise error for unsecured handlers

        Returns:
            Validation result dict

        Raises:
            RegistrySecurityError: If strict and unsecured handlers found
        """
        result = validate_registry_security(self.handlers, strict=strict)
        self._validated = result["valid"]
        return result

    def is_validated(self) -> bool:
        """Check if dispatcher has passed security validation."""
        return self._validated

    def get_handler(self, action_id: str) -> Callable:
        """
        Get handler for action_id.

        Args:
            action_id: Action identifier

        Returns:
            Handler function

        Raises:
            HandlerNotFoundError: If no handler for action_id
        """
        handler = self.handlers.get(action_id)
        if handler is None:
            raise HandlerNotFoundError(action_id)
        return handler

    async def dispatch(
        self,
        action_id: str,
        db_client,
        auth: Dict[str, Any],
        idempotency_key: str = None,
        request_id: str = None,
        **params
    ) -> Any:
        """
        Dispatch action to handler with security checks.

        The handler is expected to be decorated with @secure_action,
        which handles:
        - Yacht freeze check
        - Role validation
        - Idempotency key validation
        - Entity ownership validation
        - Context injection

        Args:
            action_id: Action identifier
            db_client: Supabase client
            auth: Auth dict from get_authenticated_user
            idempotency_key: Idempotency-Key header value
            request_id: Request ID for tracing
            **params: Handler parameters

        Returns:
            Handler result

        Raises:
            HandlerNotFoundError: If no handler for action_id
            ActionSecurityError: If security checks fail (from handler)
        """
        handler = self.get_handler(action_id)

        # Handler is expected to be @secure_action decorated
        # Security checks happen inside the decorator
        return await handler(
            db_client,
            auth,
            idempotency_key=idempotency_key,
            request_id=request_id,
            **params
        )


# ============================================================================
# MODULE-LEVEL STARTUP GATE
# ============================================================================

# Environment flag to skip validation (ONLY for testing)
_SKIP_REGISTRY_VALIDATION = os.getenv("SKIP_REGISTRY_VALIDATION", "").lower() == "true"

# Environment flag to use strict mode (default=True for production safety)
_STRICT_REGISTRY_VALIDATION = os.getenv("STRICT_REGISTRY_VALIDATION", "true").lower() != "false"

if not _SKIP_REGISTRY_VALIDATION:
    # Validate on module import (startup gate)
    # This runs when the router is imported, before it can accept requests
    # With strict=True (default), raises RegistrySecurityError if unsecured handlers found
    try:
        _startup_result = validate_registry_security(strict=_STRICT_REGISTRY_VALIDATION)
        if _startup_result["valid"]:
            logger.info(
                f"[SecureDispatcher] Registry validation PASSED: "
                f"{_startup_result['secured_handlers']} handlers secured"
            )
        elif not _STRICT_REGISTRY_VALIDATION:
            # Non-strict mode: log warning but continue
            logger.warning(
                f"[SecureDispatcher] Registry validation FAILED (non-strict): "
                f"{len(_startup_result['unsecured_handlers'])} handlers need @secure_action: "
                f"{_startup_result['unsecured_handlers']}"
            )
        # If strict=True and invalid, RegistrySecurityError is raised above
    except RegistrySecurityError:
        # Re-raise to fail fast at import time
        raise
    except Exception as e:
        # Only skip validation for unexpected errors (e.g., missing dependencies)
        logger.error(f"[SecureDispatcher] Registry validation error: {e}")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'RegistrySecurityError',
    'HandlerNotFoundError',
    'SecureDispatcher',
    'validate_registry_security',
    'validate_handler_security',
    'get_unsecured_handlers',
    'get_handler_security_report',
]
