"""
CelesteOS API - Action Security Middleware
==========================================

Integrates security checks into action handlers.

Security invariants enforced:
1. Yacht context is server-resolved (never from payload)
2. Ownership validation for all foreign IDs
3. Idempotency for MUTATE/SIGNED/ADMIN actions
4. Yacht freeze blocks mutations
5. 404 for not-found (never 403 to prevent enumeration)

Usage:
    from middleware.action_security import secure_action, ActionContext

    @secure_action(
        action_group="MUTATE",
        required_roles=["hod", "captain", "manager"],
        validate_entities=["equipment_id", "fault_id"],
    )
    async def my_handler(ctx: ActionContext, **params):
        # ctx contains validated user, yacht, role
        # All entity IDs have been ownership-validated
        pass
"""

from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionGroup(Enum):
    """Action groups per security spec."""
    READ = "READ"           # No idempotency required
    MUTATE = "MUTATE"       # Requires idempotency
    SIGNED = "SIGNED"       # Requires idempotency + signature
    ADMIN = "ADMIN"         # Requires idempotency + elevated permissions


@dataclass
class ActionContext:
    """
    Validated action context.

    All fields are server-resolved and trusted.
    """
    user_id: str
    yacht_id: str
    role: str
    tenant_key_alias: str
    email: Optional[str] = None
    yacht_name: Optional[str] = None
    membership_id: Optional[str] = None
    membership_status: Optional[str] = None
    is_frozen: bool = False
    idempotency_key: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging/audit."""
        return {
            'user_id': self.user_id,
            'yacht_id': self.yacht_id,
            'role': self.role,
            'tenant_key_alias': self.tenant_key_alias,
            'is_frozen': self.is_frozen,
        }


class ActionSecurityError(Exception):
    """Base exception for action security errors."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class YachtFrozenError(ActionSecurityError):
    """Raised when yacht is frozen and mutation attempted."""
    def __init__(self, yacht_id: str):
        super().__init__(
            "YACHT_FROZEN",
            "Yacht is frozen. MUTATE/SIGNED/ADMIN actions are disabled.",
            status_code=403,
        )
        self.yacht_id = yacht_id


class RoleNotAllowedError(ActionSecurityError):
    """Raised when user role is not allowed for action."""
    def __init__(self, role: str, allowed_roles: List[str]):
        super().__init__(
            "ROLE_NOT_ALLOWED",
            f"Role '{role}' not allowed. Required: {', '.join(allowed_roles)}",
            status_code=403,
        )


class IdempotencyRequiredError(ActionSecurityError):
    """Raised when idempotency key is required but missing."""
    def __init__(self, action_id: str):
        super().__init__(
            "IDEMPOTENCY_REQUIRED",
            f"Idempotency-Key header required for action '{action_id}'",
            status_code=400,
        )


class OwnershipValidationError(ActionSecurityError):
    """Raised when entity ownership validation fails.

    Security invariant: Always return 404 (not 403) to prevent enumeration.
    """
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            "NOT_FOUND",
            f"{entity_type} not found",  # Generic message, no ID in response
            status_code=404,
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class MembershipInactiveError(ActionSecurityError):
    """Raised when user's membership is not ACTIVE."""
    def __init__(self, user_id: str, status: str):
        super().__init__(
            "MEMBERSHIP_INACTIVE",
            "Access denied. Membership is not active.",
            status_code=403,
        )
        self.user_id = user_id
        self.membership_status = status


class PayloadValidationError(ActionSecurityError):
    """Raised when payload validation fails."""
    def __init__(self, field: str, message: str):
        super().__init__(
            "VALIDATION_ERROR",
            f"Invalid {field}: {message}",
            status_code=400,
        )
        self.field = field


class StepUpRequiredError(ActionSecurityError):
    """Raised when action requires step-up authentication."""
    def __init__(self, action_id: str):
        super().__init__(
            "STEP_UP_REQUIRED",
            f"Action '{action_id}' requires step-up authentication",
            status_code=403,
        )


class SignatureRequiredError(ActionSecurityError):
    """Raised when SIGNED action is missing signature."""
    def __init__(self, action_id: str):
        super().__init__(
            "SIGNATURE_REQUIRED",
            f"Action '{action_id}' requires signature",
            status_code=400,
        )


def check_yacht_not_frozen(ctx: ActionContext, action_group: ActionGroup) -> None:
    """
    Check yacht is not frozen for mutation actions.

    READ actions are always allowed.
    MUTATE/SIGNED/ADMIN actions blocked when frozen.

    Raises:
        YachtFrozenError: If yacht is frozen and action is not READ
    """
    if action_group == ActionGroup.READ:
        return

    if ctx.is_frozen:
        logger.warning(
            f"[ActionSecurity] Blocked {action_group.value} action: "
            f"yacht {ctx.yacht_id[:8]}... is FROZEN"
        )
        raise YachtFrozenError(ctx.yacht_id)


def check_role_allowed(ctx: ActionContext, allowed_roles: Set[str]) -> None:
    """
    Check user role is in allowed roles.

    Raises:
        RoleNotAllowedError: If role not allowed
    """
    if not allowed_roles:
        return  # No role restriction

    if ctx.role not in allowed_roles:
        logger.warning(
            f"[ActionSecurity] Role denied: user={ctx.user_id[:8]}..., "
            f"role={ctx.role}, required={allowed_roles}"
        )
        raise RoleNotAllowedError(ctx.role, list(allowed_roles))


def check_idempotency_key(
    idempotency_key: Optional[str],
    action_id: str,
    action_group: ActionGroup,
) -> Optional[str]:
    """
    Validate idempotency key for mutating actions.

    READ actions don't require idempotency.
    MUTATE/SIGNED/ADMIN require valid idempotency key.

    Returns:
        The validated idempotency key (or None for READ)

    Raises:
        IdempotencyRequiredError: If key required but missing/invalid
    """
    if action_group == ActionGroup.READ:
        return None

    if not idempotency_key:
        raise IdempotencyRequiredError(action_id)

    # Validate key format
    if len(idempotency_key) < 8 or len(idempotency_key) > 128:
        raise IdempotencyRequiredError(action_id)

    return idempotency_key


def validate_entity_ownership(
    db_client,
    entity_param: str,
    entity_id: str,
    yacht_id: str,
    entity_type_mapping: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Validate entity ownership before action execution.

    Uses the central ownership validator.

    Args:
        db_client: Supabase client for TENANT DB
        entity_param: Parameter name (e.g., "equipment_id")
        entity_id: Entity UUID to validate
        yacht_id: Context yacht_id
        entity_type_mapping: Custom mapping of param name to table

    Returns:
        Entity data on success

    Raises:
        NotFoundError: If entity not found or not owned (returns 404)
    """
    from validators.ownership import ensure_owned, NotFoundError

    # Default mapping from param name to table
    default_mapping = {
        "equipment_id": "pms_equipment",
        "fault_id": "pms_faults",
        "work_order_id": "pms_work_orders",
        "document_id": "doc_metadata",
        "part_id": "pms_parts",
        "note_id": "pms_notes",
        "attachment_id": "pms_attachments",
        "checklist_id": "pms_checklists",
    }

    mapping = {**default_mapping, **(entity_type_mapping or {})}

    # Get table name from param
    table_name = mapping.get(entity_param)
    if not table_name:
        # Try stripping _id suffix
        entity_type = entity_param.replace("_id", "")
        table_name = f"pms_{entity_type}s"

    return ensure_owned(db_client, table_name, entity_id, yacht_id)


def create_action_context(auth: Dict[str, Any], idempotency_key: str = None) -> ActionContext:
    """
    Create ActionContext from auth dict (from get_authenticated_user).

    Args:
        auth: Auth dict from get_authenticated_user dependency
        idempotency_key: Optional idempotency key from header

    Returns:
        ActionContext with validated fields
    """
    return ActionContext(
        user_id=auth['user_id'],
        yacht_id=auth['yacht_id'],
        role=auth['role'],
        tenant_key_alias=auth['tenant_key_alias'],
        email=auth.get('email'),
        yacht_name=auth.get('yacht_name'),
        membership_id=auth.get('membership_id'),
        membership_status=auth.get('membership_status'),
        is_frozen=auth.get('is_frozen', False),
        idempotency_key=idempotency_key,
    )


def secure_action(
    action_id: str,
    action_group: str = "READ",
    required_roles: List[str] = None,
    validate_entities: List[str] = None,
    entity_type_mapping: Dict[str, str] = None,
):
    """
    Decorator to add security checks to action handlers.

    Usage:
        @secure_action(
            action_id="update_fault",
            action_group="MUTATE",
            required_roles=["hod", "captain", "manager"],
            validate_entities=["fault_id"],
        )
        async def update_fault_handler(ctx: ActionContext, **params):
            # ctx is validated
            # params["fault_id"] has been ownership-validated
            pass

    Args:
        action_id: Unique action identifier
        action_group: READ, MUTATE, SIGNED, or ADMIN
        required_roles: List of roles allowed (empty = all roles)
        validate_entities: List of entity_id params to validate ownership
        entity_type_mapping: Custom param -> table mapping

    The decorated function receives:
        - ctx: ActionContext (first positional arg)
        - **params: Original params (with yacht_id injected from ctx)

    CI Contract:
        Decorated functions have _secure_action=True attribute for
        contract testing (tests/ci/test_handler_security_contract.py).
    """
    group = ActionGroup[action_group]
    roles_set = set(required_roles) if required_roles else set()
    entities_to_validate = validate_entities or []

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            db_client,
            auth: Dict[str, Any],
            idempotency_key: str = None,
            request_id: str = None,
            **params
        ):
            # Create context from auth
            ctx = create_action_context(auth, idempotency_key)
            ctx.request_id = request_id

            # 1. Check yacht not frozen (for mutations)
            check_yacht_not_frozen(ctx, group)

            # 2. Check role allowed
            check_role_allowed(ctx, roles_set)

            # 3. Check idempotency key (for mutations)
            ctx.idempotency_key = check_idempotency_key(
                idempotency_key, action_id, group
            )

            # 4. Validate entity ownership
            for entity_param in entities_to_validate:
                entity_id = params.get(entity_param)
                if entity_id:
                    validate_entity_ownership(
                        db_client,
                        entity_param,
                        entity_id,
                        ctx.yacht_id,
                        entity_type_mapping,
                    )

            # 5. Inject yacht_id from context (never trust payload)
            params['yacht_id'] = ctx.yacht_id
            params['user_id'] = ctx.user_id

            # 6. Execute handler
            return await func(ctx, **params)

        # CI Contract: Mark function as secured for contract testing
        wrapper._secure_action = True
        wrapper._action_id = action_id
        wrapper._action_group = action_group
        wrapper._required_roles = required_roles or []
        wrapper._validate_entities = validate_entities or []

        return wrapper
    return decorator


def is_secured_handler(func: Callable) -> bool:
    """
    Check if a handler has @secure_action decorator.

    Used by CI contract tests to verify all handlers are secured.

    Returns:
        True if handler has _secure_action=True attribute
    """
    return getattr(func, '_secure_action', False) is True


def get_handler_security_metadata(func: Callable) -> Optional[Dict[str, Any]]:
    """
    Get security metadata from a secured handler.

    Returns:
        Dict with action_id, action_group, required_roles, validate_entities
        or None if not a secured handler
    """
    if not is_secured_handler(func):
        return None

    return {
        'action_id': getattr(func, '_action_id', None),
        'action_group': getattr(func, '_action_group', None),
        'required_roles': getattr(func, '_required_roles', []),
        'validate_entities': getattr(func, '_validate_entities', []),
    }


# ============================================================================
# CONVENIENCE FUNCTIONS FOR HANDLER INTEGRATION
# ============================================================================


def inject_yacht_context(params: Dict[str, Any], ctx: ActionContext) -> Dict[str, Any]:
    """
    Inject yacht context into params, overwriting any payload yacht_id.

    Security invariant: yacht_id MUST come from ctx, never payload.
    """
    return {
        **params,
        'yacht_id': ctx.yacht_id,
        'user_id': ctx.user_id,
    }


def compute_payload_hash(payload: Dict[str, Any], exclude_keys: List[str] = None) -> str:
    """
    Compute SHA256 hash of payload for audit logging.

    Excludes sensitive keys from hash computation.
    """
    import hashlib
    import json

    exclude = set(exclude_keys or [])
    exclude.update({'signature', 'password', 'token', 'secret', 'api_key'})

    # Filter and sort for deterministic hash
    filtered = {
        k: v for k, v in sorted(payload.items())
        if k not in exclude and not any(s in k.lower() for s in ['password', 'secret', 'token'])
    }

    payload_str = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()[:32]


def build_audit_entry(
    ctx: ActionContext,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: Dict = None,
    new_values: Dict = None,
    signature: Dict = None,
    outcome: str = "allowed",
    payload: Dict = None,
    affected_record_ids: List[str] = None,
) -> Dict[str, Any]:
    """
    Build audit log entry with context.

    Signature invariant: signature is NEVER None in audit.

    Args:
        ctx: ActionContext with user/yacht/role
        action: Action name (e.g., "report_fault")
        entity_type: Entity type (e.g., "fault")
        entity_id: Entity UUID
        old_values: Previous state (for updates)
        new_values: New state
        signature: Signature payload (SIGNED actions)
        outcome: "allowed", "denied", or "error"
        payload: Original payload for hash (sensitive keys excluded)
        affected_record_ids: List of affected record IDs

    Returns:
        Complete audit entry dict ready for insertion
    """
    from datetime import datetime, timezone

    # Compute payload hash (excludes sensitive keys)
    payload_hash = None
    if payload:
        payload_hash = compute_payload_hash(payload)

    return {
        "yacht_id": ctx.yacht_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": ctx.user_id,
        "old_values": old_values,
        "new_values": new_values,
        "signature": signature or {},  # INVARIANT: never None
        "metadata": {
            "source": "action_router",
            "action": action,
            "role": ctx.role,
            "request_id": ctx.request_id,
            "idempotency_key": ctx.idempotency_key,
            "payload_hash": payload_hash,
            "outcome": outcome,
            "affected_record_ids": affected_record_ids,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# ERROR RESPONSE MAPPING
# ============================================================================


def map_security_error_to_response(error: Exception) -> Dict[str, Any]:
    """
    Map security exception to standardized HTTP response body.

    Security invariant: Error messages must not reveal implementation details
    or enable enumeration attacks.

    Returns:
        Dict with 'error', 'code', 'message', 'status_code'
    """
    if isinstance(error, ActionSecurityError):
        return {
            "error": True,
            "code": error.code,
            "message": error.message,
            "status_code": error.status_code,
        }

    # Unknown exception - return generic 500
    logger.error(f"[ActionSecurity] Unmapped error: {type(error).__name__}: {error}")
    return {
        "error": True,
        "code": "INTERNAL_ERROR",
        "message": "An internal error occurred",
        "status_code": 500,
    }


def get_standard_error_codes() -> Dict[str, Dict[str, Any]]:
    """
    Get mapping of standard error codes to HTTP status and messages.

    Use this for consistent error handling across handlers.

    Returns:
        Dict of error_code -> {status_code, message_template}
    """
    return {
        # 400 Bad Request - Client errors
        "VALIDATION_ERROR": {"status_code": 400, "message": "Invalid request data"},
        "IDEMPOTENCY_REQUIRED": {"status_code": 400, "message": "Idempotency-Key header required"},
        "INVALID_PAYLOAD": {"status_code": 400, "message": "Invalid request payload"},
        "SIGNATURE_REQUIRED": {"status_code": 400, "message": "Signature required"},

        # 403 Forbidden - Authorization errors
        "YACHT_FROZEN": {"status_code": 403, "message": "Yacht is frozen"},
        "ROLE_NOT_ALLOWED": {"status_code": 403, "message": "Insufficient permissions"},
        "MEMBERSHIP_INACTIVE": {"status_code": 403, "message": "Membership not active"},
        "PERMISSION_DENIED": {"status_code": 403, "message": "Permission denied"},
        "STEP_UP_REQUIRED": {"status_code": 403, "message": "Step-up authentication required"},

        # 404 Not Found - Used for ownership failures (prevents enumeration)
        "NOT_FOUND": {"status_code": 404, "message": "Resource not found"},

        # 409 Conflict - Idempotency collisions
        "IDEMPOTENCY_CONFLICT": {"status_code": 409, "message": "Request already processed"},

        # 500 Internal Server Error
        "INTERNAL_ERROR": {"status_code": 500, "message": "An internal error occurred"},
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'ActionContext',
    'ActionGroup',
    'ActionSecurityError',
    'YachtFrozenError',
    'RoleNotAllowedError',
    'IdempotencyRequiredError',
    'OwnershipValidationError',
    'MembershipInactiveError',
    'PayloadValidationError',
    'StepUpRequiredError',
    'SignatureRequiredError',
    'secure_action',
    'create_action_context',
    'check_yacht_not_frozen',
    'check_role_allowed',
    'check_idempotency_key',
    'validate_entity_ownership',
    'inject_yacht_context',
    'build_audit_entry',
    'compute_payload_hash',
    'is_secured_handler',
    'get_handler_security_metadata',
    'map_security_error_to_response',
    'get_standard_error_codes',
]
