"""
Yacht Isolation Validator

Ensures user can only access data from their assigned yacht.
"""

from typing import Dict, Any
from .validation_result import ValidationResult


def validate_yacht_isolation(
    context: Dict[str, Any],
    user_context: Dict[str, Any],
) -> ValidationResult:
    """
    Validate that context yacht_id matches user's yacht_id.

    This is a critical security check that prevents cross-yacht data access.

    Args:
        context: Action context containing yacht_id
        user_context: User context from JWT (contains user's yacht_id)

    Returns:
        ValidationResult indicating success or failure
    """
    # Extract yacht IDs
    context_yacht_id = context.get("yacht_id")
    user_yacht_id = user_context.get("yacht_id")

    # yacht_id is required in context for all actions
    if not context_yacht_id:
        return ValidationResult.failure(
            error_code="missing_yacht_id",
            message="yacht_id is required in action context",
            field="yacht_id",
        )

    # Verify user has assigned yacht
    if not user_yacht_id:
        return ValidationResult.failure(
            error_code="user_no_yacht",
            message="User is not assigned to any yacht",
        )

    # Verify yacht_id match
    if context_yacht_id != user_yacht_id:
        return ValidationResult.failure(
            error_code="yacht_mismatch",
            message=f"Access denied: User yacht ({user_yacht_id}) does not match requested yacht ({context_yacht_id})",
            details={
                "user_yacht_id": user_yacht_id,
                "requested_yacht_id": context_yacht_id,
            },
        )

    # Validation passed
    return ValidationResult.success()


__all__ = ["validate_yacht_isolation"]
