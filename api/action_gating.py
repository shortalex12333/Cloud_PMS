"""
Action Gating Configuration
===========================
Runtime enforcement of the Action Execution Contract.

This module defines which actions require confirmation and prevents
dangerous state changes from auto-executing.
"""

from enum import Enum
from typing import Set


class ExecutionClass(str, Enum):
    """Execution class determines runtime behavior."""
    AUTO = "auto"           # Execute immediately (read-only, high confidence)
    SUGGEST = "suggest"     # Show as chip, don't auto-execute
    CONFIRM = "confirm"     # Require explicit user confirmation


# Actions that ALWAYS require confirmation dialog
# These can NEVER be auto-executed regardless of confidence
GATED_ACTIONS: Set[str] = frozenset([
    # Destructive / Irreversible
    "archive_document",
    "close_work_order",

    # Compliance-affecting (legal/regulatory)
    "log_hours_of_rest",
    "submit_compliance_report",
    "upload_certificate_document",
    "update_certificate_metadata",

    # Multi-user impact
    "assign_work_order",
    "assign_task",
    "share_document",
    "share_with_shipyard",

    # Financial / Purchasing
    "approve_purchase_order",
    "create_purchase_order",
    "order_part",

    # Bulk operations
    "export_compliance_logs",
    "export_handover",
])

# Actions that are state-changing but lower risk
# These require confirmation if confidence < threshold
STATE_CHANGING_ACTIONS: Set[str] = frozenset([
    # Work Orders
    "create_work_order",
    "update_work_order",
    "add_note_to_work_order",
    "attach_photo_to_work_order",
    "attach_document_to_work_order",
    "set_priority_on_work_order",
    "schedule_work_order",
    "mark_work_order_complete",

    # Inventory
    "add_part_to_work_order",
    "update_stock_level",
    "create_purchase_request",
    "reserve_part",

    # Documents
    "upload_document",

    # Handover
    "add_to_handover",
    "edit_handover_section",
    "attach_document_to_handover",

    # Tasks
    "create_task",
    "add_checklist_item",

    # Misc
    "set_reminder",
    "add_note",
    "link_document_to_equipment",
    "log_contractor_work",
])

# Actions that are safe to auto-execute
READ_ONLY_ACTIONS: Set[str] = frozenset([
    # Diagnosis/Display
    "diagnose_fault",
    "show_manual_section",
    "show_related_documents",
    "show_equipment_overview",
    "show_equipment_history",
    "show_recent_state",
    "show_predictive_insight",
    "suggest_likely_parts",
    "show_similar_past_events",
    "trace_related_faults",
    "trace_related_equipment",
    "view_linked_entities",
    "show_document_graph",
    "expand_fault_tree",
    "show_entity_timeline",

    # Lists/Views
    "list_work_orders",
    "view_handover",
    "show_work_order_history",

    # Inventory reads
    "check_stock_level",
    "show_storage_location",
    "scan_barcode",
    "show_part_compatibility",
    "show_low_stock_alerts",

    # Compliance reads
    "show_hours_of_rest",
    "show_certificates",
    "show_certificate_expiry",
    "generate_audit_pack",

    # Documents reads
    "search_documents",
    "open_document",
    "show_document_metadata",
    "download_document",

    # Tasks reads
    "show_tasks_due",
    "show_checklist",

    # Reporting (read-only exports)
    "export_summary",
    "generate_summary",
    "show_analytics",
    "export_work_order_history",
    "show_equipment_utilization",
    "show_fault_trends",

    # Fleet
    "compare_fleet_equipment",
    "show_fleet_alerts",

    # Special
    "none_search_only",
    "open_equipment_card",
    "detect_anomaly",
])


# Confidence thresholds
AUTO_EXECUTE_THRESHOLD = 0.85  # Above this, can auto-execute non-gated
SUGGEST_THRESHOLD = 0.60       # Below this, always suggest


def get_execution_class(action: str, confidence: float = 1.0) -> ExecutionClass:
    """
    Determine execution class for an action.

    Args:
        action: The action name
        confidence: Router confidence score (0-1)

    Returns:
        ExecutionClass determining runtime behavior
    """
    # Gated actions ALWAYS require confirmation
    if action in GATED_ACTIONS:
        return ExecutionClass.CONFIRM

    # Read-only actions can auto-execute if confidence is high
    if action in READ_ONLY_ACTIONS:
        if confidence >= AUTO_EXECUTE_THRESHOLD:
            return ExecutionClass.AUTO
        else:
            return ExecutionClass.SUGGEST

    # State-changing actions require higher confidence or confirmation
    if action in STATE_CHANGING_ACTIONS:
        if confidence >= AUTO_EXECUTE_THRESHOLD:
            return ExecutionClass.SUGGEST  # Still suggest, don't auto-execute
        else:
            return ExecutionClass.CONFIRM

    # Unknown action - require confirmation to be safe
    return ExecutionClass.CONFIRM


def can_auto_execute(action: str, confidence: float = 1.0) -> bool:
    """Check if action can be auto-executed without user interaction."""
    return get_execution_class(action, confidence) == ExecutionClass.AUTO


def requires_confirmation(action: str) -> bool:
    """Check if action ALWAYS requires confirmation (regardless of confidence)."""
    return action in GATED_ACTIONS


def is_destructive(action: str) -> bool:
    """Check if action is destructive (gated or state-changing)."""
    return action in GATED_ACTIONS or action in STATE_CHANGING_ACTIONS


# Validation
def validate_action_sets():
    """Ensure no action appears in multiple sets."""
    all_actions = GATED_ACTIONS | STATE_CHANGING_ACTIONS | READ_ONLY_ACTIONS

    # Check for duplicates
    total = len(GATED_ACTIONS) + len(STATE_CHANGING_ACTIONS) + len(READ_ONLY_ACTIONS)
    if len(all_actions) != total:
        overlapping = []
        for action in all_actions:
            count = sum([
                action in GATED_ACTIONS,
                action in STATE_CHANGING_ACTIONS,
                action in READ_ONLY_ACTIONS
            ])
            if count > 1:
                overlapping.append(action)
        raise ValueError(f"Actions appear in multiple sets: {overlapping}")


# Run validation on import
validate_action_sets()
