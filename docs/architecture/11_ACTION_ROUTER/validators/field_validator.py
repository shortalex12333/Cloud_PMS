"""
Required Fields Validator

Validates that all required fields are present in the action payload.
"""

from typing import Dict, Any, List
from .validation_result import ValidationResult


def validate_required_fields(
    params: Dict[str, Any],
    required_fields: List[str],
    action_id: str,
) -> ValidationResult:
    """
    Validate all required fields are present in params.

    Args:
        params: Merged context + payload parameters
        required_fields: List of required field names
        action_id: ID of the action being validated

    Returns:
        ValidationResult indicating success or failure
    """
    # Check each required field
    missing_fields = []

    for field in required_fields:
        # Check if field exists and has a value
        value = params.get(field)
        if value is None or value == "":
            missing_fields.append(field)

    # If any fields missing, fail validation
    if missing_fields:
        return ValidationResult.failure(
            error_code="missing_fields",
            message=f"Missing required fields for action '{action_id}': {', '.join(missing_fields)}",
            details={
                "missing_fields": missing_fields,
                "required_fields": required_fields,
                "action_id": action_id,
            },
        )

    # Validation passed
    return ValidationResult.success()


__all__ = ["validate_required_fields"]
