"""
Input Validation Middleware

Provides validation utilities for action payloads.
Security Fix: 2026-02-10 (Day 3)
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# UUID regex pattern (v4 UUIDs)
UUID_REGEX = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# Maximum allowed values to prevent overflow
MAX_QUANTITY = 1_000_000
MAX_STRING_LENGTH = 10_000


class InputValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str, code: str = "VALIDATION_FAILED"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(message)


def validate_uuid(value: Any, field_name: str) -> str:
    """
    Validate that value is a valid UUID string.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Returns:
        The validated UUID string

    Raises:
        InputValidationError: If validation fails
    """
    if value is None:
        raise InputValidationError(
            field_name,
            f"{field_name} is required",
            "MISSING_REQUIRED_FIELD"
        )

    str_value = str(value).strip()

    if not str_value:
        raise InputValidationError(
            field_name,
            f"{field_name} is required",
            "MISSING_REQUIRED_FIELD"
        )

    if not UUID_REGEX.match(str_value):
        raise InputValidationError(
            field_name,
            f"Invalid UUID format for {field_name}",
            "VALIDATION_FAILED"
        )

    return str_value


def validate_positive_number(
    value: Any,
    field_name: str,
    allow_zero: bool = False,
    max_value: int = MAX_QUANTITY
) -> Union[int, float]:
    """
    Validate that value is a positive number.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        allow_zero: Whether to allow zero as a valid value
        max_value: Maximum allowed value

    Returns:
        The validated number

    Raises:
        InputValidationError: If validation fails
    """
    if value is None:
        raise InputValidationError(
            field_name,
            f"{field_name} is required",
            "MISSING_REQUIRED_FIELD"
        )

    try:
        num_value = float(value)
    except (ValueError, TypeError):
        raise InputValidationError(
            field_name,
            f"{field_name} must be a valid number",
            "VALIDATION_FAILED"
        )

    if allow_zero:
        if num_value < 0:
            raise InputValidationError(
                field_name,
                f"{field_name} must be zero or greater",
                "VALIDATION_FAILED"
            )
    else:
        if num_value <= 0:
            raise InputValidationError(
                field_name,
                f"{field_name} must be greater than 0",
                "VALIDATION_FAILED"
            )

    if num_value > max_value:
        raise InputValidationError(
            field_name,
            f"{field_name} exceeds maximum allowed value ({max_value})",
            "VALIDATION_FAILED"
        )

    # Return int if whole number, float otherwise
    if num_value == int(num_value):
        return int(num_value)
    return num_value


def validate_enum(
    value: Any,
    allowed_values: List[str],
    field_name: str,
    case_sensitive: bool = False
) -> str:
    """
    Validate that value is one of the allowed values.

    Args:
        value: The value to validate
        allowed_values: List of valid values
        field_name: Name of the field for error messages
        case_sensitive: Whether comparison should be case-sensitive

    Returns:
        The validated enum value

    Raises:
        InputValidationError: If validation fails
    """
    if value is None:
        raise InputValidationError(
            field_name,
            f"{field_name} is required",
            "MISSING_REQUIRED_FIELD"
        )

    str_value = str(value).strip()

    if case_sensitive:
        if str_value not in allowed_values:
            raise InputValidationError(
                field_name,
                f"Invalid {field_name}. Must be one of: {', '.join(allowed_values)}",
                "VALIDATION_FAILED"
            )
    else:
        lower_value = str_value.lower()
        lower_allowed = [v.lower() for v in allowed_values]
        if lower_value not in lower_allowed:
            raise InputValidationError(
                field_name,
                f"Invalid {field_name}. Must be one of: {', '.join(allowed_values)}",
                "VALIDATION_FAILED"
            )
        # Return the matched value in its original case
        idx = lower_allowed.index(lower_value)
        str_value = allowed_values[idx]

    return str_value


def validate_required_string(
    value: Any,
    field_name: str,
    min_length: int = 1,
    max_length: int = MAX_STRING_LENGTH
) -> str:
    """
    Validate that value is a non-empty string.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length
        max_length: Maximum allowed length

    Returns:
        The validated string

    Raises:
        InputValidationError: If validation fails
    """
    if value is None:
        raise InputValidationError(
            field_name,
            f"{field_name} is required",
            "MISSING_REQUIRED_FIELD"
        )

    str_value = str(value).strip()

    if len(str_value) < min_length:
        raise InputValidationError(
            field_name,
            f"{field_name} is required" if min_length == 1 else f"{field_name} must be at least {min_length} characters",
            "MISSING_REQUIRED_FIELD"
        )

    if len(str_value) > max_length:
        raise InputValidationError(
            field_name,
            f"{field_name} exceeds maximum length ({max_length} characters)",
            "VALIDATION_FAILED"
        )

    return str_value


def validate_optional_string(
    value: Any,
    field_name: str,
    max_length: int = MAX_STRING_LENGTH
) -> Optional[str]:
    """
    Validate an optional string field.

    Args:
        value: The value to validate (can be None)
        field_name: Name of the field for error messages
        max_length: Maximum allowed length

    Returns:
        The validated string or None

    Raises:
        InputValidationError: If validation fails
    """
    if value is None:
        return None

    str_value = str(value).strip()

    if not str_value:
        return None

    if len(str_value) > max_length:
        raise InputValidationError(
            field_name,
            f"{field_name} exceeds maximum length ({max_length} characters)",
            "VALIDATION_FAILED"
        )

    return str_value


# ============================================================================
# ACTION-SPECIFIC VALIDATION SCHEMAS
# ============================================================================

# Valid enum values for various fields
VALID_URGENCY = ["low", "normal", "high", "critical"]
VALID_SOURCE_TYPES = ["manual_add", "work_order", "pm_schedule", "conversation", "receiving"]
VALID_EQUIPMENT_STATUS = ["operational", "degraded", "failed", "maintenance", "decommissioned"]
VALID_FAULT_STATUS = ["open", "acknowledged", "in_progress", "resolved", "closed"]
VALID_WORK_ORDER_STATUS = ["open", "in_progress", "on_hold", "completed", "cancelled", "archived"]
VALID_PURCHASE_STATUS = ["draft", "submitted", "approved", "ordered", "shipped", "delivered", "cancelled"]


# Action validation schemas: {action_name: {field_name: validation_function}}
ACTION_VALIDATION_SCHEMAS = {
    # Shopping List Actions
    "create_shopping_list_item": {
        "part_name": lambda v: validate_required_string(v, "part_name"),
        "quantity_requested": lambda v: validate_positive_number(v, "quantity_requested"),
        "source_type": lambda v: validate_enum(v, VALID_SOURCE_TYPES, "source_type"),
    },
    "approve_shopping_list_item": {
        "item_id": lambda v: validate_uuid(v, "item_id"),
        "quantity_approved": lambda v: validate_positive_number(v, "quantity_approved"),
    },
    "reject_shopping_list_item": {
        "item_id": lambda v: validate_uuid(v, "item_id"),
        "rejection_reason": lambda v: validate_required_string(v, "rejection_reason"),
    },
    "promote_candidate_to_part": {
        "item_id": lambda v: validate_uuid(v, "item_id"),
    },
    "delete_shopping_item": {
        "item_id": lambda v: validate_uuid(v, "item_id"),
    },

    # Equipment Actions
    "update_equipment_status": {
        "equipment_id": lambda v: validate_uuid(v, "equipment_id"),
        "new_status": lambda v: validate_enum(v, VALID_EQUIPMENT_STATUS, "new_status"),
    },
    "add_equipment_note": {
        "equipment_id": lambda v: validate_uuid(v, "equipment_id"),
        "note_text": lambda v: validate_required_string(v, "note_text"),
    },

    # Fault Actions
    "report_fault": {
        "equipment_id": lambda v: validate_uuid(v, "equipment_id"),
        "description": lambda v: validate_required_string(v, "description"),
    },
    "diagnose_fault": {
        "fault_id": lambda v: validate_uuid(v, "fault_id"),
    },
    "close_fault": {
        "fault_id": lambda v: validate_uuid(v, "fault_id"),
    },
    "update_fault": {
        "fault_id": lambda v: validate_uuid(v, "fault_id"),
    },
    "add_fault_note": {
        "fault_id": lambda v: validate_uuid(v, "fault_id"),
        "note_text": lambda v: validate_required_string(v, "note_text"),
    },

    # Work Order Actions
    "add_note_to_work_order": {
        "work_order_id": lambda v: validate_uuid(v, "work_order_id"),
        "note_text": lambda v: validate_required_string(v, "note_text"),
    },
    "add_part_to_work_order": {
        "work_order_id": lambda v: validate_uuid(v, "work_order_id"),
        "part_id": lambda v: validate_uuid(v, "part_id"),
        "quantity": lambda v: validate_positive_number(v, "quantity"),
    },

    # Inventory Actions
    "log_part_usage": {
        "part_id": lambda v: validate_uuid(v, "part_id"),
        "quantity": lambda v: validate_positive_number(v, "quantity"),
        "usage_reason": lambda v: validate_required_string(v, "usage_reason"),
    },
    "check_stock_level": {
        "part_id": lambda v: validate_uuid(v, "part_id"),
    },

    # Purchase Actions
    "approve_purchase": {
        "purchase_request_id": lambda v: validate_uuid(v, "purchase_request_id"),
    },
    "update_purchase_status": {
        "purchase_request_id": lambda v: validate_uuid(v, "purchase_request_id"),
        "status": lambda v: validate_enum(v, VALID_PURCHASE_STATUS, "status"),
    },
}


def validate_action_payload(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate action payload against schema.

    Args:
        action: The action name
        payload: The payload to validate

    Returns:
        The validated payload with normalized values

    Raises:
        InputValidationError: If validation fails
    """
    schema = ACTION_VALIDATION_SCHEMAS.get(action)
    if not schema:
        # No schema defined for this action - skip validation
        return payload

    validated_payload = payload.copy()

    for field_name, validator_fn in schema.items():
        value = payload.get(field_name)
        try:
            validated_value = validator_fn(value)
            validated_payload[field_name] = validated_value
        except InputValidationError:
            raise
        except Exception as e:
            logger.warning(f"Validation error for {field_name}: {e}")
            raise InputValidationError(
                field_name,
                f"Invalid value for {field_name}",
                "VALIDATION_FAILED"
            )

    return validated_payload


__all__ = [
    "InputValidationError",
    "validate_uuid",
    "validate_positive_number",
    "validate_enum",
    "validate_required_string",
    "validate_optional_string",
    "validate_action_payload",
    "ACTION_VALIDATION_SCHEMAS",
    "VALID_URGENCY",
    "VALID_SOURCE_TYPES",
    "VALID_EQUIPMENT_STATUS",
    "VALID_FAULT_STATUS",
    "VALID_WORK_ORDER_STATUS",
    "VALID_PURCHASE_STATUS",
]
