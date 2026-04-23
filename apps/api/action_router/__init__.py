"""
CelesteOS Action Router

Central gateway for all user-initiated mutations in CelesteOS.

Live endpoint: POST /v1/actions/execute — served by routes/p0_actions_routes.py
"""

from .registry import (
    ACTION_REGISTRY,
    ActionDefinition,
    HandlerType,
    get_action,
    list_actions,
    get_actions_for_role,
)

__all__ = [
    "ACTION_REGISTRY",
    "ActionDefinition",
    "HandlerType",
    "get_action",
    "list_actions",
    "get_actions_for_role",
]
