"""
Action Registry - Static mapping of all available micro-actions

Based on api-spec.md search result actions:
- create_work_order
- add_to_handover
- add_note
- log_fault
- update_work_order_status
- create_handover
- export_handover

Each action defines:
- name: Unique action identifier
- requires: List of required fields (from context + payload combined)
- allowed_roles: Roles that can execute this action
- description: Human-readable description
- handler_type: "n8n" | "internal" (for future routing)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ActionDefinition:
    """Definition of a single micro-action"""
    name: str
    description: str
    requires: List[str]  # Required fields across context + payload
    allowed_roles: List[str]  # Roles that can execute: ["Captain", "Engineer", "Admin", "Crew"]
    handler_type: str = "n8n"  # "n8n" or "internal"
    n8n_workflow_id: Optional[str] = None  # TODO: Populate when n8n ready
    payload_schema: Dict = field(default_factory=dict)  # JSON schema for payload validation


# Master registry of all available actions
ACTION_REGISTRY: Dict[str, ActionDefinition] = {

    # ============================================================================
    # Notes & Comments Actions
    # ============================================================================
    "add_note": ActionDefinition(
        name="add_note",
        description="Add a note to equipment, work order, or general log",
        requires=["yacht_id", "user_id", "text"],
        allowed_roles=["Captain", "Engineer", "Admin", "Crew"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "equipment_id": {"type": "string", "format": "uuid"},
                "work_order_id": {"type": "string", "format": "uuid"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["text"]
        }
    ),

    # ============================================================================
    # Work Order Actions
    # ============================================================================
    "create_work_order": ActionDefinition(
        name="create_work_order",
        description="Create a new work order for equipment maintenance",
        requires=["yacht_id", "user_id", "equipment_id", "title"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "format": "uuid"},
                "title": {"type": "string", "minLength": 1},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "due_date": {"type": "string", "format": "date"}
            },
            "required": ["equipment_id", "title"]
        }
    ),

    "update_work_order_status": ActionDefinition(
        name="update_work_order_status",
        description="Update the status of an existing work order",
        requires=["yacht_id", "user_id", "work_order_id", "status"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "work_order_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": ["planned", "in_progress", "blocked", "completed", "cancelled"]},
                "notes": {"type": "string"}
            },
            "required": ["work_order_id", "status"]
        }
    ),

    "assign_work_order": ActionDefinition(
        name="assign_work_order",
        description="Assign a work order to a crew member",
        requires=["yacht_id", "user_id", "work_order_id", "assignee_id"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "work_order_id": {"type": "string", "format": "uuid"},
                "assignee_id": {"type": "string", "format": "uuid"},
                "notes": {"type": "string"}
            },
            "required": ["work_order_id", "assignee_id"]
        }
    ),

    # ============================================================================
    # Fault / Issue Actions
    # ============================================================================
    "log_fault": ActionDefinition(
        name="log_fault",
        description="Log a fault or issue on equipment",
        requires=["yacht_id", "user_id", "equipment_id", "fault_description"],
        allowed_roles=["Captain", "Engineer", "Admin", "Crew"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "equipment_id": {"type": "string", "format": "uuid"},
                "fault_code": {"type": "string"},
                "fault_description": {"type": "string", "minLength": 1},
                "severity": {"type": "string", "enum": ["minor", "moderate", "major", "critical"]},
                "photos": {"type": "array", "items": {"type": "string", "format": "uuid"}}
            },
            "required": ["equipment_id", "fault_description"]
        }
    ),

    "resolve_fault": ActionDefinition(
        name="resolve_fault",
        description="Mark a fault as resolved",
        requires=["yacht_id", "user_id", "fault_id", "resolution"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "fault_id": {"type": "string", "format": "uuid"},
                "resolution": {"type": "string", "minLength": 1},
                "work_order_id": {"type": "string", "format": "uuid"},
                "parts_used": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["fault_id", "resolution"]
        }
    ),

    # ============================================================================
    # Handover Actions
    # ============================================================================
    "create_handover": ActionDefinition(
        name="create_handover",
        description="Create a new handover draft document",
        requires=["yacht_id", "user_id", "title"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 1},
                "period_start": {"type": "string", "format": "date"},
                "period_end": {"type": "string", "format": "date"},
                "department": {"type": "string", "enum": ["engineering", "deck", "interior", "general"]}
            },
            "required": ["title"]
        }
    ),

    "add_to_handover": ActionDefinition(
        name="add_to_handover",
        description="Add an item (fault, note, document) to a handover draft",
        requires=["yacht_id", "user_id", "handover_id", "source_type", "source_id"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "handover_id": {"type": "string", "format": "uuid"},
                "source_type": {"type": "string", "enum": ["fault", "note", "document", "work_order"]},
                "source_id": {"type": "string", "format": "uuid"},
                "summary": {"type": "string"}
            },
            "required": ["handover_id", "source_type", "source_id"]
        }
    ),

    "export_handover": ActionDefinition(
        name="export_handover",
        description="Export handover document to PDF or HTML",
        requires=["yacht_id", "user_id", "handover_id", "format"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "handover_id": {"type": "string", "format": "uuid"},
                "format": {"type": "string", "enum": ["pdf", "html", "docx"]}
            },
            "required": ["handover_id", "format"]
        }
    ),

    # ============================================================================
    # Inventory / Parts Actions
    # ============================================================================
    "request_part": ActionDefinition(
        name="request_part",
        description="Request a spare part from inventory",
        requires=["yacht_id", "user_id", "part_id", "quantity"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "part_id": {"type": "string", "format": "uuid"},
                "quantity": {"type": "integer", "minimum": 1},
                "reason": {"type": "string"},
                "work_order_id": {"type": "string", "format": "uuid"}
            },
            "required": ["part_id", "quantity"]
        }
    ),

    "update_stock_level": ActionDefinition(
        name="update_stock_level",
        description="Update stock level for a part",
        requires=["yacht_id", "user_id", "part_id", "new_quantity"],
        allowed_roles=["Captain", "Engineer", "Admin"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "part_id": {"type": "string", "format": "uuid"},
                "new_quantity": {"type": "integer", "minimum": 0},
                "reason": {"type": "string", "enum": ["received", "used", "damaged", "audit"]}
            },
            "required": ["part_id", "new_quantity"]
        }
    ),

    # ============================================================================
    # Hours of Rest / Compliance Actions
    # ============================================================================
    "log_hours_of_rest": ActionDefinition(
        name="log_hours_of_rest",
        description="Log hours of rest for compliance tracking",
        requires=["yacht_id", "user_id", "date", "hours"],
        allowed_roles=["Captain", "Engineer", "Admin", "Crew"],
        handler_type="n8n",
        payload_schema={
            "type": "object",
            "properties": {
                "date": {"type": "string", "format": "date"},
                "hours": {"type": "number", "minimum": 0, "maximum": 24},
                "notes": {"type": "string"}
            },
            "required": ["date", "hours"]
        }
    ),
}


def get_action(action_name: str) -> Optional[ActionDefinition]:
    """Get an action definition by name"""
    return ACTION_REGISTRY.get(action_name)


def list_actions() -> List[str]:
    """List all available action names"""
    return list(ACTION_REGISTRY.keys())


def get_actions_for_role(role: str) -> List[ActionDefinition]:
    """Get all actions available for a specific role"""
    return [
        action for action in ACTION_REGISTRY.values()
        if role in action.allowed_roles
    ]
