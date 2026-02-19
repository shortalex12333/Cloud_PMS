"""
Actions Module
==============
Action execution class rules and response schemas.

Components:
- action_gating - AUTO/SUGGEST/CONFIRM execution class rules
- action_response_schema - Response structure
"""

from .action_gating import (
    ExecutionClass,
    GATED_ACTIONS,
    STATE_CHANGING_ACTIONS,
)
from .action_response_schema import (
    ActionResponseEnvelope,
    ResponseBuilder,
    AvailableAction,
    get_available_actions_for_entity,
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
