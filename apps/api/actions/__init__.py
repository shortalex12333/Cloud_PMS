"""Compatibility shim — real implementations moved to schemas/ and middleware/."""

from schemas.action_response_schema import (
    ActionResponseEnvelope,
    ResponseBuilder,
    AvailableAction,
    get_available_actions_for_entity,
)
from middleware.action_gating import (
    ExecutionClass,
    GATED_ACTIONS,
    STATE_CHANGING_ACTIONS,
)

__all__ = [
    'ExecutionClass',
    'GATED_ACTIONS',
    'STATE_CHANGING_ACTIONS',
    'ActionResponseEnvelope',
    'ResponseBuilder',
    'AvailableAction',
    'get_available_actions_for_entity',
]
