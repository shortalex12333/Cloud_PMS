"""
Actions Module
==============
Microaction management from prepare-module + frontend-microactions branches.

Components:
- action_gating - AUTO/SUGGEST/CONFIRM execution class rules
- action_registry - READ/MUTATE action definitions
- action_executor - SQL execution handlers for actions
- action_response_schema - Response structure
"""

from .action_gating import (
    ExecutionClass,
    GATED_ACTIONS,
    STATE_CHANGING_ACTIONS,
)
from .action_registry import (
    get_registry,
    ActionVariant,
    Action,
    AuditLevel,
)
from .action_executor import (
    ActionExecutor,
    ExecutionResult,
    StagedMutation,
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
    'get_registry',
    'ActionVariant',
    'Action',
    'AuditLevel',
    'ActionExecutor',
    'ExecutionResult',
    'StagedMutation',
    'ActionResponseEnvelope',
    'ResponseBuilder',
    'AvailableAction',
    'get_available_actions_for_entity',
]
