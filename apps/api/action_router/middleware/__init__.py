"""Compatibility shim — real implementations moved to middleware/."""

from middleware.validation_middleware import (
    InputValidationError,
    validate_uuid,
    validate_positive_number,
    validate_enum,
    validate_required_string,
    validate_action_payload,
)

from middleware.state_machine import (
    InvalidStateTransitionError,
    validate_state_transition,
    get_valid_next_statuses,
)

__all__ = [
    "InputValidationError",
    "validate_uuid",
    "validate_positive_number",
    "validate_enum",
    "validate_required_string",
    "validate_action_payload",
    "InvalidStateTransitionError",
    "validate_state_transition",
    "get_valid_next_statuses",
]
