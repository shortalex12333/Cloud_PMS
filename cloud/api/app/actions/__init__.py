"""
CelesteOS Actions Module

Provides micro-action execution through a unified API endpoint.

Components:
- registry: Static registry of available actions with metadata
- validators: Validation pipeline for action requests
- dispatcher: Routes validated actions to handlers (n8n or internal)
"""

from app.actions.registry import (
    ActionDefinition,
    ACTION_REGISTRY,
    get_action,
    list_actions,
    get_actions_for_role
)

from app.actions.validators import (
    ValidationResult,
    ActionValidationError,
    UnknownActionError,
    MissingFieldsError,
    YachtMismatchError,
    UserMismatchError,
    RolePermissionError,
    validate_action_request
)

from app.actions.dispatcher import (
    DispatchResult,
    ActionDispatcher,
    action_dispatcher,
    dispatch_action
)

__all__ = [
    # Registry
    "ActionDefinition",
    "ACTION_REGISTRY",
    "get_action",
    "list_actions",
    "get_actions_for_role",
    # Validators
    "ValidationResult",
    "ActionValidationError",
    "UnknownActionError",
    "MissingFieldsError",
    "YachtMismatchError",
    "UserMismatchError",
    "RolePermissionError",
    "validate_action_request",
    # Dispatcher
    "DispatchResult",
    "ActionDispatcher",
    "action_dispatcher",
    "dispatch_action",
]
