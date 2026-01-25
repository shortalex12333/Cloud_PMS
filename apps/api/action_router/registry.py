"""
CelesteOS Action Router - Action Registry

Defines all available actions, their endpoints, schemas, and permissions.

This is the SINGLE SOURCE OF TRUTH for all micro-actions.

PHASE 8 CULL (2026-01-21): Removed 16 ghost actions not deployed to production.
Remaining: 30 actions that exist in production.
"""

from typing import Dict, List, Any
from enum import Enum


class HandlerType(str, Enum):
    """Type of handler for an action."""
    INTERNAL = "internal"
    N8N = "n8n"


class ActionDefinition:
    """Definition of a single action."""

    def __init__(
        self,
        action_id: str,
        label: str,
        endpoint: str,
        handler_type: HandlerType,
        method: str = "POST",
        allowed_roles: List[str] = None,
        required_fields: List[str] = None,
        schema_file: str = None,
    ):
        self.action_id = action_id
        self.label = label
        self.endpoint = endpoint
        self.handler_type = handler_type
        self.method = method.upper()
        self.allowed_roles = allowed_roles or ["Engineer", "HOD", "Manager"]
        self.required_fields = required_fields or []
        self.schema_file = schema_file


# ============================================================================
# ACTION REGISTRY - PRODUCTION VERIFIED (30 ACTIONS)
# ============================================================================
# CULLED 2026-01-21: Removed 16 actions returning 404 in production
# See: verification_handoff/phase8/E008_ACTION_CULL.md
# ============================================================================

ACTION_REGISTRY: Dict[str, ActionDefinition] = {
    # ========================================================================
    # NOTES ACTIONS (1)
    # ========================================================================
    "add_note_to_work_order": ActionDefinition(
        action_id="add_note_to_work_order",
        label="Add Note to Work Order",
        endpoint="/v1/work-orders/add-note",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "note_text"],
        schema_file="add_note_to_work_order.json",
    ),

    # ========================================================================
    # WORK ORDER ACTIONS (14)
    # ========================================================================
    "create_work_order": ActionDefinition(
        action_id="create_work_order",
        label="Create Work Order",
        endpoint="/v1/work-orders/create",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "title", "priority"],
        schema_file="create_work_order.json",
    ),

    "close_work_order": ActionDefinition(
        action_id="close_work_order",
        label="Close Work Order",
        endpoint="/v1/work-orders/close",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
        schema_file="close_work_order.json",
    ),

    "add_work_order_photo": ActionDefinition(
        action_id="add_work_order_photo",
        label="Add Work Order Photo",
        endpoint="/v1/work-orders/add-photo",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "photo_url"],
    ),

    "add_parts_to_work_order": ActionDefinition(
        action_id="add_parts_to_work_order",
        label="Add Parts to Work Order",
        endpoint="/v1/work-orders/add-parts",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "part_id"],
    ),

    "view_work_order_checklist": ActionDefinition(
        action_id="view_work_order_checklist",
        label="View Work Order Checklist",
        endpoint="/v1/work-orders/checklist",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Crew", "ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
    ),

    "assign_work_order": ActionDefinition(
        action_id="assign_work_order",
        label="Assign Work Order",
        endpoint="/v1/work-orders/assign",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "assigned_to"],
    ),

    "update_work_order": ActionDefinition(
        action_id="update_work_order",
        label="Update Work Order",
        endpoint="/v1/work-orders/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
    ),

    "add_wo_hours": ActionDefinition(
        action_id="add_wo_hours",
        label="Add Work Order Hours",
        endpoint="/v1/work-orders/add-hours",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "hours"],
    ),

    "add_wo_part": ActionDefinition(
        action_id="add_wo_part",
        label="Add Part to Work Order",
        endpoint="/v1/work-orders/add-part",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "part_id"],
    ),

    "add_wo_note": ActionDefinition(
        action_id="add_wo_note",
        label="Add Work Order Note",
        endpoint="/v1/work-orders/add-note",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id", "note_text"],
    ),

    "start_work_order": ActionDefinition(
        action_id="start_work_order",
        label="Start Work Order",
        endpoint="/v1/work-orders/start",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
    ),

    "cancel_work_order": ActionDefinition(
        action_id="cancel_work_order",
        label="Cancel Work Order",
        endpoint="/v1/work-orders/cancel",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
    ),

    "view_work_order_detail": ActionDefinition(
        action_id="view_work_order_detail",
        label="View Work Order Detail",
        endpoint="/v1/work-orders/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Crew", "ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "work_order_id"],
    ),

    "create_work_order_from_fault": ActionDefinition(
        action_id="create_work_order_from_fault",
        label="Create Work Order from Fault",
        endpoint="/v1/work-orders/create-from-fault",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    # ========================================================================
    # EQUIPMENT ACTIONS (1)
    # ========================================================================
    "update_equipment_status": ActionDefinition(
        action_id="update_equipment_status",
        label="Update Equipment Status",
        endpoint="/v1/equipment/update-status",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "new_status"],
        schema_file=None,
    ),

    # ========================================================================
    # HANDOVER ACTIONS (1)
    # ========================================================================
    "add_to_handover": ActionDefinition(
        action_id="add_to_handover",
        label="Add to Handover",
        endpoint="/v1/handover/add-item",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "title"],
        schema_file=None,
    ),

    # ========================================================================
    # FAULT ACTIONS (10)
    # ========================================================================
    "report_fault": ActionDefinition(
        action_id="report_fault",
        label="Report Fault",
        endpoint="/v1/faults/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "description"],
    ),

    "acknowledge_fault": ActionDefinition(
        action_id="acknowledge_fault",
        label="Acknowledge Fault",
        endpoint="/v1/faults/acknowledge",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "close_fault": ActionDefinition(
        action_id="close_fault",
        label="Close Fault",
        endpoint="/v1/faults/close",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "update_fault": ActionDefinition(
        action_id="update_fault",
        label="Update Fault",
        endpoint="/v1/faults/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "add_fault_photo": ActionDefinition(
        action_id="add_fault_photo",
        label="Add Fault Photo",
        endpoint="/v1/faults/add-photo",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id", "photo_url"],
    ),

    "view_fault_detail": ActionDefinition(
        action_id="view_fault_detail",
        label="View Fault Detail",
        endpoint="/v1/faults/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Crew", "ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "diagnose_fault": ActionDefinition(
        action_id="diagnose_fault",
        label="Diagnose Fault",
        endpoint="/v1/faults/diagnose",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "reopen_fault": ActionDefinition(
        action_id="reopen_fault",
        label="Reopen Fault",
        endpoint="/v1/faults/reopen",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "mark_fault_false_alarm": ActionDefinition(
        action_id="mark_fault_false_alarm",
        label="Mark Fault as False Alarm",
        endpoint="/v1/faults/mark-false-alarm",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "fault_id"],
    ),

    "show_manual_section": ActionDefinition(
        action_id="show_manual_section",
        label="Show Manual Section",
        endpoint="/v1/documents/manual-section",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Crew", "ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id"],
    ),

    # ========================================================================
    # WORKLIST ACTIONS (3)
    # ========================================================================
    "view_worklist": ActionDefinition(
        action_id="view_worklist",
        label="View Worklist",
        endpoint="/v1/worklist/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id"],
    ),

    "add_worklist_task": ActionDefinition(
        action_id="add_worklist_task",
        label="Add Worklist Task",
        endpoint="/v1/worklist/add-task",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "task_description"],
    ),

    "export_worklist": ActionDefinition(
        action_id="export_worklist",
        label="Export Worklist",
        endpoint="/v1/worklist/export",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id"],
    ),

    # ========================================================================
    # CERTIFICATE ACTIONS
    # ========================================================================
    "create_vessel_certificate": ActionDefinition(
        action_id="create_vessel_certificate",
        label="Create Vessel Certificate",
        endpoint="/v1/certificates/create-vessel",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=[
            "yacht_id",
            "certificate_type",
            "certificate_name",
            "issuing_authority",
        ],
        schema_file=None,
    ),

    "create_crew_certificate": ActionDefinition(
        action_id="create_crew_certificate",
        label="Create Crew Certificate",
        endpoint="/v1/certificates/create-crew",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],  # is_hod() = chief_engineer, captain, manager
        required_fields=[
            "yacht_id",
            "person_name",
            "certificate_type",
            "issuing_authority",
        ],
        schema_file=None,
    ),

    "update_certificate": ActionDefinition(
        action_id="update_certificate",
        label="Update Certificate",
        endpoint="/v1/certificates/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=[
            "yacht_id",
            "certificate_id",
        ],
        schema_file=None,
    ),

    "link_document_to_certificate": ActionDefinition(
        action_id="link_document_to_certificate",
        label="Link Document to Certificate",
        endpoint="/v1/certificates/link-document",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=[
            "yacht_id",
            "certificate_id",
            "document_id",
        ],
        schema_file=None,
    ),

    "supersede_certificate": ActionDefinition(
        action_id="supersede_certificate",
        label="Supersede Certificate",
        endpoint="/v1/certificates/supersede",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Captain", "Manager"],  # Command roles for SIGNED action (lens: Captain/Manager)
        required_fields=[
            "yacht_id",
            "certificate_id",
            "reason",
            "signature",  # REQUIRED - signed action
        ],
        schema_file=None,
    ),
}


# ============================================================================
# CULLED ACTIONS (16) - DO NOT RE-ADD WITHOUT DEPLOYING TO PRODUCTION
# ============================================================================
# The following actions were removed 2026-01-21 because they return 404:
#
# - add_note                      (notes to equipment - handler not deployed)
# - add_document_to_handover      (N8N handler not deployed)
# - add_part_to_handover          (N8N handler not deployed)
# - add_predictive_to_handover    (N8N handler not deployed)
# - edit_handover_section         (handler not deployed)
# - export_handover               (N8N handler not deployed)
# - open_document                 (handler not deployed)
# - delete_document               (handler not deployed)
# - delete_shopping_item          (handler not deployed)
# - order_part                    (N8N handler not deployed)
# - classify_fault                (handler not deployed)
# - view_fault_history            (handler not deployed)
# - suggest_parts                 (handler not deployed)
# - add_fault_note                (handler not deployed)
# - create_work_order_fault       (N8N handler not deployed)
# - update_worklist_progress      (handler not deployed)
#
# See: verification_handoff/phase8/E008_ACTION_CULL.md
# ============================================================================


def get_action(action_id: str) -> ActionDefinition:
    """
    Get action definition by ID.

    Raises:
        KeyError: If action not found
    """
    if action_id not in ACTION_REGISTRY:
        raise KeyError(f"Action '{action_id}' not found in registry")

    return ACTION_REGISTRY[action_id]


def list_actions() -> Dict[str, ActionDefinition]:
    """Get all registered actions."""
    return ACTION_REGISTRY.copy()


def get_actions_for_role(role: str) -> Dict[str, ActionDefinition]:
    """Get all actions available for a specific role."""
    return {
        action_id: action
        for action_id, action in ACTION_REGISTRY.items()
        if role in action.allowed_roles
    }


def validate_action_exists(action_id: str) -> bool:
    """Check if action exists in registry."""
    return action_id in ACTION_REGISTRY


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ACTION_REGISTRY",
    "ActionDefinition",
    "HandlerType",
    "get_action",
    "list_actions",
    "get_actions_for_role",
    "validate_action_exists",
]
