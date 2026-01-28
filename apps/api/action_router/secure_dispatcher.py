"""
CelesteOS Action Router - Secure Dispatcher
=============================================

Secure handler integration layer for the action router.

This module:
1. Registers secure handlers from handlers/secure_*.py modules
2. Validates all handlers have @secure_action decorator
3. Provides secure dispatch with proper auth context passing
4. Integrates with middleware/action_security.py for enforcement

Security invariants:
- Only handlers with _secure_action=True are accepted
- Auth context is passed to handlers (not just params)
- Idempotency keys are validated for MUTATE/SIGNED/ADMIN
- Yacht freeze status is checked before mutations

Usage:
    from action_router.secure_dispatcher import (
        secure_dispatch,
        get_secure_handlers,
        validate_secure_registry,
    )

    # Dispatch to secure handler
    result = await secure_dispatch(action_id, auth_context, params, idempotency_key)
"""

from typing import Dict, Any, Callable, Optional, Set
import logging
import os

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Import security middleware
from middleware.action_security import (
    is_secured_handler,
    get_handler_security_metadata,
    ActionSecurityError,
    YachtFrozenError,
    RoleNotAllowedError,
    IdempotencyRequiredError,
)

# ============================================================================
# SECURE HANDLER REGISTRY
# ============================================================================

# Secure handlers registry - maps action_id to secured handler function
SECURE_HANDLERS: Dict[str, Callable] = {}

# Track which handlers have been validated
_validated_handlers: Set[str] = set()

# Lazy-initialized DB client
_db_client = None


def get_db_client() -> Client:
    """Get TENANT Supabase client for secure handlers."""
    global _db_client
    if _db_client is None:
        default_yacht = os.getenv("DEFAULT_YACHT_CODE", "yTEST_YACHT_001")
        url = os.getenv(f"{default_yacht}_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = os.getenv(f"{default_yacht}_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise ValueError(f"Supabase credentials not configured")

        _db_client = create_client(url, key)
    return _db_client


# Lazy-initialized MASTER DB client
_master_client = None


def get_master_client() -> Client:
    """Get MASTER Supabase client for admin handlers (memberships, fleet_registry)."""
    global _master_client
    if _master_client is None:
        url = os.getenv("MASTER_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = os.getenv("MASTER_SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise ValueError("MASTER Supabase credentials not configured")

        _master_client = create_client(url, key)
    return _master_client


def register_secure_handlers() -> None:
    """
    Register all secure handlers from handlers/secure_*.py modules.

    Called at startup to populate SECURE_HANDLERS registry.
    Validates each handler has @secure_action decorator.
    """
    global SECURE_HANDLERS

    db_client = get_db_client()

    # ========================================================================
    # Register Secure Fault Handlers
    # ========================================================================
    try:
        from handlers.secure_fault_handlers import get_secure_fault_handlers
        fault_handlers = get_secure_fault_handlers(db_client)

        for action_id, handler in fault_handlers.items():
            if not is_secured_handler(handler):
                logger.error(
                    f"[SecureDispatcher] REJECTED: {action_id} - missing @secure_action"
                )
                raise ValueError(
                    f"Handler '{action_id}' from secure_fault_handlers is not secured"
                )
            SECURE_HANDLERS[action_id] = handler
            _validated_handlers.add(action_id)
            logger.info(f"[SecureDispatcher] Registered: {action_id} (fault)")

    except ImportError as e:
        logger.warning(f"[SecureDispatcher] Could not import secure_fault_handlers: {e}")

    # ========================================================================
    # Register Secure Document Handlers
    # ========================================================================
    try:
        from handlers.secure_document_handlers import get_secure_document_handlers
        doc_handlers = get_secure_document_handlers(db_client)

        for action_id, handler in doc_handlers.items():
            if not is_secured_handler(handler):
                logger.error(
                    f"[SecureDispatcher] REJECTED: {action_id} - missing @secure_action"
                )
                raise ValueError(
                    f"Handler '{action_id}' from secure_document_handlers is not secured"
                )
            SECURE_HANDLERS[action_id] = handler
            _validated_handlers.add(action_id)
            logger.info(f"[SecureDispatcher] Registered: {action_id} (document)")

    except ImportError as e:
        logger.warning(f"[SecureDispatcher] Could not import secure_document_handlers: {e}")

    # ========================================================================
    # Register Secure Admin Handlers (when available)
    # ========================================================================
    try:
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        # Admin handlers need MASTER client for memberships
        master_client = get_master_client()
        admin_handlers = get_secure_admin_handlers(db_client, master_client)

        for action_id, handler in admin_handlers.items():
            if not is_secured_handler(handler):
                logger.error(
                    f"[SecureDispatcher] REJECTED: {action_id} - missing @secure_action"
                )
                raise ValueError(
                    f"Handler '{action_id}' from secure_admin_handlers is not secured"
                )
            SECURE_HANDLERS[action_id] = handler
            _validated_handlers.add(action_id)
            logger.info(f"[SecureDispatcher] Registered: {action_id} (admin)")

    except ImportError as e:
        logger.debug(f"[SecureDispatcher] secure_admin_handlers not available: {e}")

    logger.info(
        f"[SecureDispatcher] Registered {len(SECURE_HANDLERS)} secure handlers"
    )


def validate_secure_registry() -> Dict[str, Any]:
    """
    Validate the secure handler registry.

    Returns validation report with:
    - total_handlers: Number of registered handlers
    - validated_handlers: List of validated handler action_ids
    - missing_security: List of handlers missing @secure_action (should be empty)
    - handler_metadata: Dict of action_id -> security metadata

    Raises:
        ValueError: If any handler is missing @secure_action
    """
    report = {
        'total_handlers': len(SECURE_HANDLERS),
        'validated_handlers': list(_validated_handlers),
        'missing_security': [],
        'handler_metadata': {},
    }

    for action_id, handler in SECURE_HANDLERS.items():
        if not is_secured_handler(handler):
            report['missing_security'].append(action_id)
        else:
            metadata = get_handler_security_metadata(handler)
            report['handler_metadata'][action_id] = metadata

    if report['missing_security']:
        raise ValueError(
            f"Secure registry contains unsecured handlers: {report['missing_security']}"
        )

    return report


def get_secure_handlers() -> Dict[str, Callable]:
    """
    Get all registered secure handlers.

    Returns:
        Dict mapping action_id to secured handler function
    """
    return SECURE_HANDLERS.copy()


def has_secure_handler(action_id: str) -> bool:
    """
    Check if a secure handler exists for action_id.

    Returns:
        True if secure handler is registered
    """
    return action_id in SECURE_HANDLERS


# ============================================================================
# SECURE DISPATCH
# ============================================================================


async def secure_dispatch(
    action_id: str,
    auth_context: Dict[str, Any],
    params: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatch action to secure handler with full security enforcement.

    This is the primary entry point for secure action execution.

    Args:
        action_id: Action ID to execute
        auth_context: Auth context from middleware (user_id, yacht_id, role, etc.)
        params: Action parameters (payload)
        idempotency_key: Idempotency-Key header value (required for mutations)
        request_id: Request ID for tracing

    Returns:
        Handler result dict

    Raises:
        KeyError: If action_id not found in secure handlers
        ActionSecurityError: For security validation failures
        Exception: For handler execution errors
    """
    if action_id not in SECURE_HANDLERS:
        raise KeyError(f"No secure handler found for action '{action_id}'")

    handler = SECURE_HANDLERS[action_id]

    # Get handler metadata for logging
    metadata = get_handler_security_metadata(handler)
    action_group = metadata.get('action_group', 'UNKNOWN') if metadata else 'UNKNOWN'

    logger.info(
        f"[SecureDispatcher] Dispatching: action={action_id}, "
        f"group={action_group}, user={auth_context.get('user_id', 'unknown')[:8]}..."
    )

    try:
        # Call secure handler with auth context
        # The @secure_action decorator handles:
        # - Yacht freeze check
        # - Role validation
        # - Idempotency key validation
        # - Ownership validation
        # - Context injection
        db_client = get_db_client()

        result = await handler(
            db_client,
            auth_context,
            idempotency_key=idempotency_key,
            request_id=request_id,
            **params,
        )

        logger.info(
            f"[SecureDispatcher] Success: action={action_id}, "
            f"yacht={auth_context.get('yacht_id', 'unknown')[:8]}..."
        )

        return result

    except (YachtFrozenError, RoleNotAllowedError, IdempotencyRequiredError) as e:
        # Security errors - re-raise with proper status codes
        logger.warning(
            f"[SecureDispatcher] Security error: action={action_id}, "
            f"error={e.code}, message={e.message}"
        )
        raise

    except ActionSecurityError as e:
        # Other security errors
        logger.warning(
            f"[SecureDispatcher] Action security error: action={action_id}, "
            f"error={e.code}"
        )
        raise

    except ValueError as e:
        # Validation/business logic errors (400)
        logger.warning(
            f"[SecureDispatcher] Validation error: action={action_id}, error={str(e)}"
        )
        raise

    except Exception as e:
        # Unexpected errors
        logger.error(
            f"[SecureDispatcher] Handler error: action={action_id}, error={str(e)}",
            exc_info=True,
        )
        raise


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_secure_dispatcher() -> None:
    """
    Initialize the secure dispatcher.

    Call at application startup to:
    1. Register all secure handlers
    2. Validate the registry
    """
    register_secure_handlers()

    try:
        report = validate_secure_registry()
        logger.info(
            f"[SecureDispatcher] Validated {report['total_handlers']} handlers"
        )
    except ValueError as e:
        logger.error(f"[SecureDispatcher] Validation failed: {e}")
        raise


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'SECURE_HANDLERS',
    'secure_dispatch',
    'register_secure_handlers',
    'validate_secure_registry',
    'get_secure_handlers',
    'has_secure_handler',
    'init_secure_dispatcher',
    'get_db_client',
    'get_master_client',
]
