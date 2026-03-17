# apps/api/action_router/entity_actions.py
"""
CelesteOS — Entity Action Discovery
=====================================
get_available_actions(entity_type, entity_data, user_role) -> list[dict]

Role filtering: actions where user_role not in allowed_roles are OMITTED entirely.
State gating: stateful entities (work_order, fault, receiving) get inline disabled/reason.
Flat entities (equipment, part, certificate, etc.): role filter only, no state gate.

No DB calls. Read-only with respect to entity_data input.
"""
from typing import Optional

from action_router.registry import ACTION_REGISTRY, get_actions_for_domain
from action_router.entity_prefill import (
    ENTITY_TYPE_TO_DOMAIN,
    resolve_prefill,
    get_field_schema,
)

# ── Work Order status sets ─────────────────────────────────────────────────────
_PRE_START_STATUSES = {"draft", "open", "planned"}
_ACTIVE_STATUSES = {"in_progress", "pending_parts"}
_TERMINAL_STATUSES = {"completed", "cancelled", "closed"}

_WO_PRE_START_DISABLED = {
    "close_work_order", "complete_work_order", "add_wo_hours",
    "reassign_work_order", "cancel_work_order",
}
_WO_ACTIVE_DISABLED = {"start_work_order"}
_WO_TERMINAL_DISABLED = {
    "start_work_order", "add_wo_part", "add_wo_hours",
    "log_part_usage", "add_work_order_photo", "assign_work_order",
}

# ── Fault status sets ──────────────────────────────────────────────────────────
_FAULT_TERMINAL_STATUSES = {"resolved", "closed"}
_FAULT_TERMINAL_DISABLED = {
    "acknowledge_fault", "diagnose_fault", "create_work_order_from_fault",
    "add_fault_photo", "close_fault",
    # reopen_fault intentionally EXCLUDED — escape hatch for terminal states
    # add_fault_note intentionally EXCLUDED — documentation, not a mutation
}

# ── Receiving status sets ──────────────────────────────────────────────────────
_RECEIVING_TERMINAL_STATUSES = {"accepted", "rejected"}
_RECEIVING_TERMINAL_DISABLED = {
    "add_receiving_item", "adjust_receiving_item", "accept_receiving",
    "reject_receiving", "attach_receiving_image_with_comment", "update_receiving_fields",
}


def get_available_actions(
    entity_type: str,
    entity_data: dict,
    user_role: str,
) -> list[dict]:
    """
    Return available actions for an entity, filtered by role and state.

    Read-only — never mutates entity_data.
    Returns [] for unknown entity types or types with no registry domain.
    """
    domain = ENTITY_TYPE_TO_DOMAIN.get(entity_type)
    if domain is None:
        return []

    domain_action_dicts = get_actions_for_domain(domain)  # List[Dict] — summaries only

    result = []
    for action_summary in domain_action_dicts:
        action_id = action_summary.get("action_id") or action_summary.get("id")
        if not action_id:
            continue

        # Full ActionDefinition — use .get() to safely skip missing IDs
        action_def = ACTION_REGISTRY.get(action_id)
        if not action_def:
            continue

        # Role gate: omit entirely if not permitted
        allowed = action_def.allowed_roles or []
        if user_role not in allowed:
            continue

        # State gate: inline for stateful entities only
        disabled, disabled_reason = _apply_state_gate(entity_type, entity_data, action_id)

        # Prefill + field schema (pure functions, no DB)
        prefill = resolve_prefill(entity_type, action_id, entity_data)
        required_fields, optional_fields = get_field_schema(action_id)

        # Variant → string; SIGNED sets requires_signature
        variant_str = (
            action_def.variant.value
            if hasattr(action_def.variant, "value")
            else str(action_def.variant)
        )
        requires_signature = (variant_str == "SIGNED")

        result.append({
            "action_id":            action_id,
            "label":                action_def.label,
            "variant":              variant_str,
            "icon":                 "",
            "is_primary":           False,
            "requires_signature":   requires_signature,
            "confirmation_message": None,
            "disabled":             disabled,
            "disabled_reason":      disabled_reason,
            "prefill":              prefill,
            "required_fields":      required_fields,
            "optional_fields":      optional_fields,
        })

    return result


def _apply_state_gate(
    entity_type: str,
    entity_data: dict,
    action_id: str,
) -> tuple[bool, Optional[str]]:
    """
    Returns (disabled: bool, disabled_reason: str | None).
    disabled=False, disabled_reason=None means the action is enabled.
    Only work_order, fault, and receiving entities have state gates.
    """
    status = (entity_data.get("status") or "").lower()

    if entity_type == "work_order":
        if status in _PRE_START_STATUSES and action_id in _WO_PRE_START_DISABLED:
            return True, "Work order must be started first"
        if status in _ACTIVE_STATUSES and action_id in _WO_ACTIVE_DISABLED:
            return True, "Work order is already in progress"
        if status in _TERMINAL_STATUSES and action_id in _WO_TERMINAL_DISABLED:
            reason_map = {
                "completed": "Work order is completed",
                "cancelled":  "Work order is cancelled",
                "closed":     "Work order is closed",
            }
            return True, reason_map.get(status, "Work order is finalised")

    elif entity_type == "fault":
        if status in _FAULT_TERMINAL_STATUSES and action_id in _FAULT_TERMINAL_DISABLED:
            return True, "Fault is already resolved"

    elif entity_type == "receiving":
        if status in _RECEIVING_TERMINAL_STATUSES and action_id in _RECEIVING_TERMINAL_DISABLED:
            return True, "Receiving record is finalised"

    return False, None
