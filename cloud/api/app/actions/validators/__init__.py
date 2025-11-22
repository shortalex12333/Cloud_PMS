"""
Action Validators - Validation pipeline for action execution

Validates:
1. JWT/Token authentication
2. Yacht context matching
3. User context matching
4. Role permissions
5. Required fields presence
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

from app.actions.registry import get_action, ActionDefinition
from app.core.auth import YachtContext

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation pipeline"""
    valid: bool
    error_code: Optional[int] = None  # HTTP status code
    error_message: Optional[str] = None
    action_def: Optional[ActionDefinition] = None


class ActionValidationError(Exception):
    """Base exception for action validation errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UnknownActionError(ActionValidationError):
    """Raised when action is not found in registry"""
    def __init__(self, action_name: str):
        super().__init__(
            f"Unknown action: '{action_name}'. Check action-catalogue for valid actions.",
            status_code=400
        )


class MissingFieldsError(ActionValidationError):
    """Raised when required fields are missing"""
    def __init__(self, missing_fields: List[str]):
        super().__init__(
            f"Missing required fields: {', '.join(missing_fields)}",
            status_code=400
        )


class YachtMismatchError(ActionValidationError):
    """Raised when context yacht_id doesn't match token yacht"""
    def __init__(self):
        super().__init__(
            "Context yacht_id does not match authenticated yacht",
            status_code=403
        )


class UserMismatchError(ActionValidationError):
    """Raised when context user_id doesn't match token user"""
    def __init__(self):
        super().__init__(
            "Context user_id does not match authenticated user",
            status_code=403
        )


class RolePermissionError(ActionValidationError):
    """Raised when user role is not allowed for this action"""
    def __init__(self, role: str, action: str, allowed_roles: List[str]):
        super().__init__(
            f"Role '{role}' is not permitted to execute '{action}'. "
            f"Allowed roles: {', '.join(allowed_roles)}",
            status_code=403
        )


def validate_action_exists(action_name: str) -> ActionDefinition:
    """
    Validate that the action exists in the registry.

    Args:
        action_name: Name of the action to look up

    Returns:
        ActionDefinition if found

    Raises:
        UnknownActionError if action not found
    """
    action_def = get_action(action_name)
    if action_def is None:
        logger.warning(f"Unknown action requested: {action_name}")
        raise UnknownActionError(action_name)
    return action_def


def validate_context_matches_token(
    context: Dict[str, Any],
    auth_context: YachtContext
) -> None:
    """
    Validate that request context matches the authenticated token.

    Args:
        context: Request context from body
        auth_context: Authenticated yacht context from JWT

    Raises:
        YachtMismatchError: If yacht_id doesn't match
        UserMismatchError: If user_id doesn't match
    """
    # Validate yacht_id matches
    context_yacht_id = context.get("yacht_id")
    if context_yacht_id and str(context_yacht_id) != str(auth_context.yacht_id):
        logger.warning(
            f"Yacht mismatch: context={context_yacht_id}, token={auth_context.yacht_id}"
        )
        raise YachtMismatchError()

    # Validate user_id matches
    context_user_id = context.get("user_id")
    if context_user_id and str(context_user_id) != str(auth_context.user_id):
        logger.warning(
            f"User mismatch: context={context_user_id}, token={auth_context.user_id}"
        )
        raise UserMismatchError()


def validate_role_permission(
    role: str,
    action_def: ActionDefinition
) -> None:
    """
    Validate that the user's role is allowed to execute this action.

    Args:
        role: User's role from JWT
        action_def: The action being executed

    Raises:
        RolePermissionError: If role is not allowed
    """
    # Normalize role for comparison
    role_normalized = role.strip().title() if role else ""

    if role_normalized not in action_def.allowed_roles:
        logger.warning(
            f"Role '{role}' not permitted for action '{action_def.name}'. "
            f"Allowed: {action_def.allowed_roles}"
        )
        raise RolePermissionError(role, action_def.name, action_def.allowed_roles)


def validate_required_fields(
    context: Dict[str, Any],
    payload: Dict[str, Any],
    action_def: ActionDefinition
) -> None:
    """
    Validate that all required fields are present in context + payload.

    Args:
        context: Request context
        payload: Request payload
        action_def: The action definition with required fields

    Raises:
        MissingFieldsError: If any required fields are missing
    """
    # Combine context and payload for field lookup
    combined = {**context, **payload}

    missing_fields = []
    for field in action_def.requires:
        if field not in combined or combined[field] is None:
            missing_fields.append(field)

    if missing_fields:
        logger.warning(
            f"Missing fields for action '{action_def.name}': {missing_fields}"
        )
        raise MissingFieldsError(missing_fields)


def validate_action_request(
    action_name: str,
    context: Dict[str, Any],
    payload: Dict[str, Any],
    auth_context: YachtContext
) -> Tuple[ActionDefinition, Dict[str, Any]]:
    """
    Full validation pipeline for an action request.

    Steps:
    1. Validate action exists in registry
    2. Validate context matches JWT token (yacht_id, user_id)
    3. Validate role has permission for this action
    4. Validate all required fields are present

    Args:
        action_name: Name of the action to execute
        context: Request context (yacht_id, user_id, role)
        payload: Action-specific payload
        auth_context: Authenticated yacht context from JWT

    Returns:
        Tuple of (ActionDefinition, merged_fields dict)

    Raises:
        ActionValidationError subclass on any validation failure
    """
    logger.info(f"Validating action request: {action_name}")

    # Step 1: Validate action exists
    action_def = validate_action_exists(action_name)

    # Step 2: Validate context matches token
    validate_context_matches_token(context, auth_context)

    # Step 3: Validate role permission
    # Use role from context if provided, otherwise from auth_context
    role = context.get("role") or auth_context.user_role
    validate_role_permission(role, action_def)

    # Step 4: Validate required fields
    # Enrich context with auth values if not provided
    enriched_context = {
        "yacht_id": str(auth_context.yacht_id),
        "user_id": str(auth_context.user_id),
        "role": role,
        **context  # User-provided context takes precedence
    }
    validate_required_fields(enriched_context, payload, action_def)

    # Merge all fields for dispatch
    merged_fields = {**enriched_context, **payload}

    logger.info(f"Action '{action_name}' validated successfully")
    return action_def, merged_fields
