"""
CelesteOS Action Router - Action Registry

Defines all available actions, their endpoints, schemas, and permissions.

This is the SINGLE SOURCE OF TRUTH for all micro-actions.
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
# ACTION REGISTRY
# ============================================================================

ACTION_REGISTRY: Dict[str, ActionDefinition] = {
    # ========================================================================
    # NOTES ACTIONS
    # ========================================================================
    "add_note": ActionDefinition(
        action_id="add_note",
        label="Add Note",
        endpoint="/v1/notes/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "note_text"],
        schema_file="add_note.json",
    ),

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
    # WORK ORDER ACTIONS
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

    "create_work_order_fault": ActionDefinition(
        action_id="create_work_order_fault",
        label="Create Work Order for Fault",
        endpoint="/v1/work-orders/create",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "description"],
        schema_file="create_work_order_fault.json",
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

    # ========================================================================
    # EQUIPMENT ACTIONS
    # ========================================================================
    "update_equipment_status": ActionDefinition(
        action_id="update_equipment_status",
        label="Update Equipment Status",
        endpoint="/v1/equipment/update-status",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "attention_flag"],
        schema_file=None,
    ),

    # ========================================================================
    # HANDOVER ACTIONS
    # ========================================================================
    "add_to_handover": ActionDefinition(
        action_id="add_to_handover",
        label="Add to Handover",
        endpoint="/v1/handover/add-item",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["ETO", "Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "summary_text"],
        schema_file=None,
    ),

    "add_document_to_handover": ActionDefinition(
        action_id="add_document_to_handover",
        label="Add Document to Handover",
        endpoint="/v1/handover/add-document",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "document_id"],
        schema_file="add_document_to_handover.json",
    ),

    "add_part_to_handover": ActionDefinition(
        action_id="add_part_to_handover",
        label="Add Part to Handover",
        endpoint="/v1/handover/add-part",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "part_id", "reason"],
        schema_file="add_part_to_handover.json",
    ),

    "add_predictive_to_handover": ActionDefinition(
        action_id="add_predictive_to_handover",
        label="Add Predictive Insight to Handover",
        endpoint="/v1/handover/add-predictive",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "equipment_id", "insight_id", "summary"],
        schema_file="add_predictive_to_handover.json",
    ),

    "edit_handover_section": ActionDefinition(
        action_id="edit_handover_section",
        label="Edit Handover Section",
        endpoint="/v1/handover/edit-section",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id", "handover_id", "section_name", "new_text"],
        schema_file="edit_handover_section.json",
    ),

    "export_handover": ActionDefinition(
        action_id="export_handover",
        label="Export Handover",
        endpoint="/v1/handover/export",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["HOD", "Manager"],
        required_fields=["yacht_id"],
        schema_file="export_handover.json",
    ),

    # ========================================================================
    # DOCUMENT ACTIONS
    # ========================================================================
    "open_document": ActionDefinition(
        action_id="open_document",
        label="Open Document",
        endpoint="/v1/documents/open",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["Crew", "ETO", "Engineer", "HOD", "Manager"],
        required_fields=["storage_path"],
        schema_file="open_document.json",
    ),

    # ========================================================================
    # INVENTORY ACTIONS
    # ========================================================================
    "order_part": ActionDefinition(
        action_id="order_part",
        label="Order Part",
        endpoint="/v1/inventory/order-part",
        handler_type=HandlerType.N8N,
        method="POST",
        allowed_roles=["Engineer", "HOD", "Manager"],
        required_fields=["yacht_id", "part_id", "qty"],
        schema_file="order_part.json",
    ),
}


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
