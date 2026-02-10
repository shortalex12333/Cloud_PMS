"""
State Machine Validation Middleware

Validates that state transitions are valid for entities.
Security Fix: 2026-02-10 (Day 5)
"""

import logging
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current_status: str, action: str, allowed_actions: Set[str] = None):
        self.current_status = current_status
        self.action = action
        self.allowed_actions = allowed_actions or set()
        self.code = "INVALID_STATE_TRANSITION"
        self.message = f"Cannot perform '{action}' on item with status '{current_status}'"
        super().__init__(self.message)


# ============================================================================
# SHOPPING LIST STATE MACHINE
# ============================================================================
# States: candidate → approved/rejected → promoted (terminal)
#
# Valid transitions:
# - candidate → approve → approved
# - candidate → reject → rejected (terminal)
# - approved → promote → promoted (terminal)

SHOPPING_LIST_TRANSITIONS: Dict[str, Set[str]] = {
    "candidate": {"approve", "reject"},
    "approved": {"promote"},
    "rejected": set(),  # Terminal state - no actions allowed
    "promoted": set(),  # Terminal state - no actions allowed
}


# ============================================================================
# FAULT STATE MACHINE
# ============================================================================
# States: open → acknowledged → diagnosed → closed
#
# Valid transitions:
# - open → acknowledge, mark_false_alarm
# - acknowledged → diagnose, close, mark_false_alarm
# - diagnosed → close
# - closed → reopen
# - false_alarm: Terminal

FAULT_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"acknowledge", "mark_false_alarm", "update", "add_note", "add_photo"},
    "acknowledged": {"diagnose", "close", "mark_false_alarm", "update", "add_note", "add_photo"},
    "in_progress": {"diagnose", "close", "update", "add_note", "add_photo"},
    "diagnosed": {"close", "update", "add_note", "add_photo"},
    "resolved": {"close", "reopen", "add_note"},
    "closed": {"reopen", "view"},
    "false_alarm": set(),  # Terminal state
}


# ============================================================================
# EQUIPMENT STATE MACHINE
# ============================================================================
# States: operational → degraded/failed/maintenance → decommissioned
#
# Valid status changes are more flexible - most transitions allowed

EQUIPMENT_TRANSITIONS: Dict[str, Set[str]] = {
    "operational": {"update_status", "decommission", "archive", "add_note"},
    "degraded": {"update_status", "decommission", "add_note"},
    "failed": {"update_status", "decommission", "add_note"},
    "maintenance": {"update_status", "decommission", "add_note"},
    "decommissioned": set(),  # Terminal state
    "archived": {"restore"},
}


# ============================================================================
# WORK ORDER STATE MACHINE
# ============================================================================
# States: open → in_progress → completed/cancelled → archived

WORK_ORDER_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"start", "assign", "cancel", "update", "add_note", "add_part", "add_photo"},
    "in_progress": {"complete", "cancel", "update", "add_note", "add_part", "add_photo"},
    "on_hold": {"resume", "cancel", "update", "add_note"},
    "completed": {"archive", "reopen", "view"},
    "cancelled": {"reopen", "view"},
    "archived": {"view"},  # Terminal - view only
}


# ============================================================================
# ACTION TO VERB MAPPING
# ============================================================================
# Maps full action names to their verb for state machine lookup

ACTION_VERB_MAP = {
    # Shopping List
    "approve_shopping_list_item": "approve",
    "reject_shopping_list_item": "reject",
    "promote_candidate_to_part": "promote",

    # Faults
    "acknowledge_fault": "acknowledge",
    "diagnose_fault": "diagnose",
    "close_fault": "close",
    "update_fault": "update",
    "reopen_fault": "reopen",
    "mark_fault_false_alarm": "mark_false_alarm",
    "add_fault_note": "add_note",
    "add_fault_photo": "add_photo",

    # Equipment
    "update_equipment_status": "update_status",
    "decommission_equipment": "decommission",
    "archive_equipment": "archive",
    "add_equipment_note": "add_note",

    # Work Orders
    "start_work_order": "start",
    "assign_work_order": "assign",
    "cancel_work_order": "cancel",
    "update_work_order": "update",
    "close_work_order": "complete",
    "mark_work_order_complete": "complete",
    "add_note_to_work_order": "add_note",
    "add_part_to_work_order": "add_part",
    "add_work_order_photo": "add_photo",
    "archive_work_order": "archive",
}


def get_action_verb(action: str) -> str:
    """Get the verb for an action name."""
    if action in ACTION_VERB_MAP:
        return ACTION_VERB_MAP[action]

    # Fallback: extract first word before underscore
    parts = action.split("_")
    return parts[0] if parts else action


def validate_state_transition(
    domain: str,
    current_status: str,
    action: str
) -> None:
    """
    Validate that a state transition is allowed.

    Args:
        domain: The domain (shopping_list, fault, equipment, work_order)
        current_status: The current status of the entity
        action: The action being attempted

    Raises:
        InvalidStateTransitionError: If the transition is not allowed
    """
    transitions_map = {
        "shopping_list": SHOPPING_LIST_TRANSITIONS,
        "fault": FAULT_TRANSITIONS,
        "equipment": EQUIPMENT_TRANSITIONS,
        "work_order": WORK_ORDER_TRANSITIONS,
    }

    transitions = transitions_map.get(domain)
    if not transitions:
        # Unknown domain - skip validation
        return

    # Normalize status to lowercase
    status_key = current_status.lower() if current_status else "unknown"

    allowed_actions = transitions.get(status_key)
    if allowed_actions is None:
        # Unknown status - log but allow (graceful degradation)
        logger.warning(f"[STATE] Unknown status '{current_status}' for domain '{domain}'")
        return

    if not allowed_actions:
        # Terminal state - no actions allowed
        raise InvalidStateTransitionError(
            current_status=current_status,
            action=action,
            allowed_actions=set()
        )

    action_verb = get_action_verb(action)

    if action_verb not in allowed_actions:
        logger.warning(
            f"[STATE] Invalid transition: '{action}' (verb: {action_verb}) "
            f"not allowed on {domain} with status '{current_status}'. "
            f"Allowed: {allowed_actions}"
        )
        raise InvalidStateTransitionError(
            current_status=current_status,
            action=action,
            allowed_actions=allowed_actions
        )


def get_valid_next_statuses(domain: str, current_status: str) -> Set[str]:
    """
    Get the set of valid next statuses for an entity.

    Args:
        domain: The domain
        current_status: The current status

    Returns:
        Set of valid actions that can be performed
    """
    transitions_map = {
        "shopping_list": SHOPPING_LIST_TRANSITIONS,
        "fault": FAULT_TRANSITIONS,
        "equipment": EQUIPMENT_TRANSITIONS,
        "work_order": WORK_ORDER_TRANSITIONS,
    }

    transitions = transitions_map.get(domain, {})
    status_key = current_status.lower() if current_status else "unknown"

    return transitions.get(status_key, set())


__all__ = [
    "InvalidStateTransitionError",
    "validate_state_transition",
    "get_valid_next_statuses",
    "get_action_verb",
    "SHOPPING_LIST_TRANSITIONS",
    "FAULT_TRANSITIONS",
    "EQUIPMENT_TRANSITIONS",
    "WORK_ORDER_TRANSITIONS",
]
