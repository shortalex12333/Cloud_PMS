"""
CelesteOS Action Router

Central gateway for all user-initiated mutations in CelesteOS.

Single endpoint: POST /v1/actions/execute
"""

from .router import router, execute_action
from .registry import (
    ACTION_REGISTRY,
    ActionDefinition,
    HandlerType,
    get_action,
    list_actions,
    get_actions_for_role,
)
from .telemetry import (
    log_action_event,
    log_suggestion_viewed,
    log_prefill_requested,
    log_prefill_completed,
    log_execute_requested,
    log_execute_completed,
)

__all__ = [
    "router",
    "execute_action",
    "ACTION_REGISTRY",
    "ActionDefinition",
    "HandlerType",
    "get_action",
    "list_actions",
    "get_actions_for_role",
    # Telemetry exports
    "log_action_event",
    "log_suggestion_viewed",
    "log_prefill_requested",
    "log_prefill_completed",
    "log_execute_requested",
    "log_execute_completed",
]
