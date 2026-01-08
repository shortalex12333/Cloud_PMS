"""
Role Permission Validator

Validates user has required role for an action.
"""

from typing import Dict, Any, List
from .validation_result import ValidationResult


def validate_role_permission(
    user_context: Dict[str, Any],
    allowed_roles: List[str],
    action_id: str,
) -> ValidationResult:
    """
    Validate user's role is authorized for the action.

    Args:
        user_context: User context from JWT (contains role)
        allowed_roles: List of roles allowed to perform this action
        action_id: ID of the action being validated

    Returns:
        ValidationResult indicating success or failure
    """
    # Extract user role
    user_role = user_context.get("role")

    # Verify user has a role
    if not user_role:
        return ValidationResult.failure(
            error_code="missing_role",
            message="User role not found in token",
        )

    # Check if user's role is in allowed list
    if user_role not in allowed_roles:
        return ValidationResult.failure(
            error_code="permission_denied",
            message=f"Role '{user_role}' is not authorized to perform action '{action_id}'",
            details={
                "user_role": user_role,
                "allowed_roles": allowed_roles,
                "action_id": action_id,
            },
        )

    # Validation passed
    return ValidationResult.success()


__all__ = ["validate_role_permission"]
