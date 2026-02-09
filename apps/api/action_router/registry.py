"""
CelesteOS Action Router - Action Registry

Defines all available actions, their endpoints, schemas, and permissions.

This is the SINGLE SOURCE OF TRUTH for all micro-actions.

PHASE 8 CULL (2026-01-21): Removed 16 ghost actions not deployed to production.
Remaining: 30 actions that exist in production.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class HandlerType(str, Enum):
    """Type of handler for an action."""
    INTERNAL = "internal"
    # N8N = "n8n"  # DEPRECATED 2026-01-27: All handlers are INTERNAL


class ActionVariant(str, Enum):
    """Variant of action (mutation level)."""
    READ = "READ"      # Read-only (view, list)
    MUTATE = "MUTATE"  # Standard mutation (create, update)
    SIGNED = "SIGNED"  # Requires signature (PIN+TOTP payload)


class FieldClassification(str, Enum):
    """
    Field classification for auto-population.

    Used by prepare/prefill to compute values and by execute to validate.
    """
    REQUIRED = "REQUIRED"           # Must be provided by user
    OPTIONAL = "OPTIONAL"           # May be provided by user
    BACKEND_AUTO = "BACKEND_AUTO"   # Computed by backend (prefill)
    CONTEXT = "CONTEXT"             # From auth/session context (yacht_id, user_id)


@dataclass
class FieldMetadata:
    """
    Metadata for a single field in an action.

    Used for:
    - Auto-population in prepare/prefill phase
    - Validation in execute phase
    - UI hints for field rendering
    """
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None  # Source: "part", "equipment", "query_text", "stock_calculation"
    lookup_required: bool = False              # Requires yacht-scoped lookup
    description: Optional[str] = None          # Human-readable description
    options: Optional[List[str]] = None        # Valid options for enum fields


class ActionDefinition:
    """
    Definition of a single action.

    The registry is the SINGLE SOURCE OF TRUTH for:
    - Action contracts (required_fields, field_metadata)
    - Role gating (allowed_roles)
    - Mutation level (variant: READ/MUTATE/SIGNED)
    - Context gating (context_required)
    - Signature role requirement (signature_roles_required)
    - Discoverability (search_keywords)
    """

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
        domain: str = None,
        variant: ActionVariant = ActionVariant.MUTATE,
        search_keywords: List[str] = None,
        field_metadata: List[FieldMetadata] = None,  # Auto-population hints
        prefill_endpoint: str = None,                 # For two-phase actions
        storage_bucket: str = None,                   # For file-producing actions
        storage_path_template: str = None,            # Path pattern for storage
        context_required: Dict[str, Any] = None,      # Context gating: {"entity_type": "fault"}
        signature_roles_required: List[str] = None,   # For SIGNED: roles that can sign
    ):
        self.action_id = action_id
        self.label = label
        self.endpoint = endpoint
        self.handler_type = handler_type
        self.method = method.upper()
        self.allowed_roles = allowed_roles or ["Engineer", "HOD", "Manager"]
        self.required_fields = required_fields or []
        self.schema_file = schema_file
        self.domain = domain
        self.variant = variant
        self.search_keywords = search_keywords or []
        self.field_metadata = field_metadata or []
        self.prefill_endpoint = prefill_endpoint
        self.storage_bucket = storage_bucket
        self.storage_path_template = storage_path_template
        self.context_required = context_required  # e.g., {"entity_type": "fault", "entity_id": True}
        self.signature_roles_required = signature_roles_required  # e.g., ["captain", "manager"]


# ============================================================================
# ACTION REGISTRY - PRODUCTION VERIFIED (40 ACTIONS)
# ============================================================================
# CULLED 2026-01-21: Removed 16 actions returning 404 in production
# ADDED 2026-01-27: Part Lens v2 (10 actions)
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
    # WORK ORDER ACTIONS (curated, executable)
    # ========================================================================

    "close_work_order": ActionDefinition(
        action_id="close_work_order",
        label="Close Work Order",
        endpoint="/v1/work-orders/close",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "work_order_id"],
        schema_file="close_work_order.json",
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["close", "complete", "finish", "work", "order", "wo"],
    ),

    "add_work_order_photo": ActionDefinition(
        action_id="add_work_order_photo",
        label="Add Work Order Photo",
        endpoint="/v1/work-orders/add-photo",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "photo_url"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "upload", "photo", "image", "work", "order", "wo"],
    ),

    "add_parts_to_work_order": ActionDefinition(
        action_id="add_parts_to_work_order",
        label="Add Parts to Work Order",
        endpoint="/v1/work-orders/add-parts",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "part_id"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "parts", "part", "work", "order", "wo"],
    ),

    "view_work_order_checklist": ActionDefinition(
        action_id="view_work_order_checklist",
        label="View Work Order Checklist",
        endpoint="/v1/work-orders/checklist",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "work_order_id"],
        domain="work_orders",
        variant=ActionVariant.READ,
        search_keywords=["view", "checklist", "tasks", "work", "order", "wo"],
    ),

    "assign_work_order": ActionDefinition(
        action_id="assign_work_order",
        label="Assign Work Order",
        endpoint="/v1/work-orders/assign",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "assigned_to"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["assign", "reassign", "owner", "work", "order", "wo"],
    ),

    "update_work_order": ActionDefinition(
        action_id="update_work_order",
        label="Update Work Order",
        endpoint="/v1/work-orders/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["update", "edit", "modify", "work", "order", "wo"],
    ),

    "add_wo_hours": ActionDefinition(
        action_id="add_wo_hours",
        label="Add Work Order Hours",
        endpoint="/v1/work-orders/add-hours",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "hours"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "hours", "time", "work", "order", "wo"],
    ),

    "add_wo_part": ActionDefinition(
        action_id="add_wo_part",
        label="Add Part to Work Order",
        endpoint="/v1/work-orders/add-part",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "part_id"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "part", "work", "order", "wo"],
    ),

    "add_wo_note": ActionDefinition(
        action_id="add_wo_note",
        label="Add Work Order Note",
        endpoint="/v1/work-orders/add-note",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id", "note_text"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "note", "comment", "work", "order", "wo"],
    ),

    "start_work_order": ActionDefinition(
        action_id="start_work_order",
        label="Start Work Order",
        endpoint="/v1/work-orders/start",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["start", "begin", "in_progress", "work", "order", "wo"],
    ),

    "cancel_work_order": ActionDefinition(
        action_id="cancel_work_order",
        label="Cancel Work Order",
        endpoint="/v1/work-orders/cancel",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "work_order_id"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["cancel", "void", "abort", "work", "order", "wo"],
    ),

    "view_work_order_detail": ActionDefinition(
        action_id="view_work_order_detail",
        label="View Work Order Detail",
        endpoint="/v1/work-orders/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "work_order_id"],
        domain="work_orders",
        variant=ActionVariant.READ,
        search_keywords=["view", "detail", "show", "work", "order", "wo"],
    ),

    "create_work_order_from_fault": ActionDefinition(
        action_id="create_work_order_from_fault",
        label="Create Work Order from Fault",
        endpoint="/v1/work-orders/create-from-fault",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain + manager can initiate
        # Signature requirement: captain or manager role at signing
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "fault_id", "signature"],
        domain="faults",  # Listed in faults domain, not work_orders
        variant=ActionVariant.SIGNED,
        search_keywords=["create", "work", "order", "wo", "from", "fault"],
        # Context gating: only appears when focused on a Fault entity
        # Do NOT surface from free-text search - requires entity_id
        context_required={"entity_type": "fault", "entity_id": True},
        # Signature must be from captain or manager
        signature_roles_required=["captain", "manager"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.CONTEXT, auto_populate_from="entity_id",
                          description="From focused fault; action only appears in fault context"),
            FieldMetadata("title", FieldClassification.BACKEND_AUTO, auto_populate_from="fault",
                          description="Derived from fault title/equipment"),
            FieldMetadata("priority", FieldClassification.OPTIONAL, options=["low", "medium", "high", "critical"]),
            FieldMetadata("assigned_to", FieldClassification.OPTIONAL, lookup_required=True),
            FieldMetadata("signature", FieldClassification.REQUIRED,
                          description="PIN+TOTP payload; role_at_signing must be captain or manager"),
        ],
    ),

    # Signed work order actions
    "reassign_work_order": ActionDefinition(
        action_id="reassign_work_order",
        label="Reassign Work Order",
        endpoint="/v1/work-orders/reassign",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain + manager (not crew)
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "work_order_id", "assignee_id", "reason", "signature"],
        domain="work_orders",
        variant=ActionVariant.SIGNED,
        search_keywords=["reassign", "assign", "owner", "handover", "transfer", "work", "order", "wo"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("work_order_id", FieldClassification.REQUIRED),
            FieldMetadata("assignee_id", FieldClassification.REQUIRED, lookup_required=True,
                          description="New assignee user ID"),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for reassignment"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP signature payload"),
        ],
    ),

    "archive_work_order": ActionDefinition(
        action_id="archive_work_order",
        label="Archive Work Order",
        endpoint="/v1/work-orders/archive",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: captain + manager only (not HOD/crew)
        allowed_roles=["captain", "manager"],
        required_fields=["yacht_id", "work_order_id", "deletion_reason", "signature"],
        domain="work_orders",
        variant=ActionVariant.SIGNED,
        search_keywords=["archive", "delete", "remove", "soft", "delete", "work", "order", "wo"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("work_order_id", FieldClassification.REQUIRED),
            FieldMetadata("deletion_reason", FieldClassification.REQUIRED, description="Reason for archiving"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP signature payload"),
        ],
    ),

    # READ: View My Work Orders (aggregation view)
    "view_my_work_orders": ActionDefinition(
        action_id="view_my_work_orders",
        label="View My Work Orders",
        endpoint="/v1/work-orders/list-my",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        # Canonical: all roles can view their own work orders
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="work_orders",
        variant=ActionVariant.READ,
        search_keywords=["my", "work", "orders", "overdue", "critical", "time", "consuming", "assigned", "list"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("assigned_to", FieldClassification.OPTIONAL,
                          description="Filter by assignee (defaults to current user)"),
            FieldMetadata("group_key", FieldClassification.OPTIONAL,
                          options=["overdue", "critical", "time_consuming", "other"],
                          description="Filter by group"),
        ],
    ),

    # ========================================================================
    # WORK ORDER RELATED ENTITIES - P1: Show Related (2 actions)
    # ========================================================================

    # READ: View Related Entities
    "view_related_entities": ActionDefinition(
        action_id="view_related_entities",
        label="View Related Entities",
        endpoint="/v1/related",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "entity_type", "entity_id"],
        domain="work_orders",
        variant=ActionVariant.READ,
        search_keywords=["related", "context", "parts", "manuals", "previous", "attachments", "handovers"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("entity_type", FieldClassification.REQUIRED,
                          description="Entity type (e.g., 'work_order')"),
            FieldMetadata("entity_id", FieldClassification.REQUIRED,
                          description="Entity UUID"),
        ],
    ),

    # MUTATE: Add Entity Link (HOD/manager only)
    "add_entity_link": ActionDefinition(
        action_id="add_entity_link",
        label="Add Related Link",
        endpoint="/v1/related/add",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", "link_type"],
        domain="work_orders",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "link", "related", "reference", "evidence"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("source_entity_type", FieldClassification.REQUIRED,
                          description="Source entity type (e.g., 'work_order')"),
            FieldMetadata("source_entity_id", FieldClassification.REQUIRED,
                          description="Source entity UUID"),
            FieldMetadata("target_entity_type", FieldClassification.REQUIRED,
                          options=["part", "manual", "work_order", "handover", "attachment"],
                          description="Target entity type"),
            FieldMetadata("target_entity_id", FieldClassification.REQUIRED,
                          description="Target entity UUID"),
            FieldMetadata("link_type", FieldClassification.REQUIRED,
                          description="Link type (default: 'explicit')"),
            FieldMetadata("note", FieldClassification.OPTIONAL,
                          description="Optional context or reason for the link"),
        ],
    ),

    # ========================================================================
    # EQUIPMENT ACTIONS - Equipment Lens v2 (8 actions)
    # ========================================================================
    # Roles per Equipment Lens v2 binding brief:
    # - Crew (deckhand, steward, chef): add_note, attach_file (READ + limited MUTATE)
    # - Engineer+ (engineer, eto, chief_engineer, chief_officer): status, WO, parts, hours
    # - Manager/Captain: decommission (SIGNED)
    # ========================================================================

    "update_equipment_status": ActionDefinition(
        action_id="update_equipment_status",
        label="Update Equipment Status",
        endpoint="/v1/equipment/update-status",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "status"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["status", "update", "mark", "failed", "operational", "equipment", "broken", "working"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("status", FieldClassification.REQUIRED,
                          options=["operational", "degraded", "failed", "maintenance"],
                          description="Target status (decommissioned requires signed action)"),
            FieldMetadata("attention_reason", FieldClassification.OPTIONAL, auto_populate_from="query_text",
                          description="Reason for attention flag (auto-set for failed/degraded)"),
            FieldMetadata("clear_attention", FieldClassification.OPTIONAL, description="Set true to clear attention flag"),
        ],
    ),

    "add_equipment_note": ActionDefinition(
        action_id="add_equipment_note",
        label="Add Note to Equipment",
        endpoint="/v1/equipment/add-note",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "text"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["note", "log", "record", "observation", "comment", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("text", FieldClassification.REQUIRED, auto_populate_from="query_text",
                          description="Note content - residual text from query after entity extraction"),
            FieldMetadata("note_type", FieldClassification.OPTIONAL,
                          options=["observation", "inspection", "handover", "defect", "maintenance"],
                          description="Default: observation"),
            FieldMetadata("requires_ack", FieldClassification.OPTIONAL, description="Requires HOD acknowledgment"),
        ],
    ),

    "attach_file_to_equipment": ActionDefinition(
        action_id="attach_file_to_equipment",
        label="Attach Photo/Document",
        endpoint="/v1/equipment/attach-file",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "file"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["photo", "picture", "upload", "attach", "document", "file", "equipment", "image"],
        storage_bucket="documents",
        storage_path_template="{yacht_id}/equipment/{equipment_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("file", FieldClassification.REQUIRED, description="File upload (max 25MB)"),
            FieldMetadata("description", FieldClassification.OPTIONAL, auto_populate_from="query_text"),
            FieldMetadata("tags", FieldClassification.OPTIONAL, description="Array of tags for categorization"),
        ],
    ),

    "create_work_order_for_equipment": ActionDefinition(
        action_id="create_work_order_for_equipment",
        label="Create Work Order",
        endpoint="/v1/equipment/create-work-order",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "title", "type", "priority"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["work", "order", "create", "job", "task", "maintenance", "equipment", "wo"],
        prefill_endpoint="/v1/equipment/create-work-order/prefill",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("title", FieldClassification.REQUIRED, auto_populate_from="query_text",
                          description="WO title - auto-populated from query with equipment prefix"),
            FieldMetadata("type", FieldClassification.REQUIRED,
                          options=["corrective", "preventive", "predictive", "emergency", "project"],
                          description="Work order type"),
            FieldMetadata("priority", FieldClassification.REQUIRED,
                          options=["low", "medium", "high", "critical"],
                          description="Work order priority"),
            FieldMetadata("description", FieldClassification.OPTIONAL, auto_populate_from="query_text"),
            FieldMetadata("assigned_to", FieldClassification.OPTIONAL, description="Assignee user ID"),
            FieldMetadata("due_date", FieldClassification.OPTIONAL, description="Due date (ISO format)"),
            FieldMetadata("fault_severity", FieldClassification.OPTIONAL,
                          options=["cosmetic", "minor", "major", "critical", "safety"],
                          description="Required for corrective/emergency - creates linked fault"),
        ],
    ),

    "link_part_to_equipment": ActionDefinition(
        action_id="link_part_to_equipment",
        label="Link Part to Equipment",
        endpoint="/v1/equipment/link-part",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "part_id"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["link", "part", "associate", "bom", "equipment", "spare"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True,
                          description="Part to link (yacht-scoped lookup)"),
            FieldMetadata("quantity_required", FieldClassification.OPTIONAL, description="Quantity needed (default: 1)"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="BOM entry notes"),
        ],
    ),

    "flag_equipment_attention": ActionDefinition(
        action_id="flag_equipment_attention",
        label="Flag for Attention",
        endpoint="/v1/equipment/flag-attention",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "attention_flag"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["flag", "attention", "alert", "highlight", "equipment", "urgent"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("attention_flag", FieldClassification.REQUIRED, description="True to set, False to clear"),
            FieldMetadata("attention_reason", FieldClassification.OPTIONAL, auto_populate_from="query_text",
                          description="Reason for flagging (required when setting)"),
        ],
    ),

    "decommission_equipment": ActionDefinition(
        action_id="decommission_equipment",
        label="Decommission Equipment",
        endpoint="/v1/equipment/decommission",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "reason", "signature"],
        domain="equipment",
        variant=ActionVariant.SIGNED,  # Requires PIN+TOTP
        search_keywords=["decommission", "remove", "retire", "archive", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for decommissioning"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP signature payload"),
            FieldMetadata("replacement_equipment_id", FieldClassification.OPTIONAL,
                          auto_populate_from="equipment", lookup_required=True,
                          description="Replacement equipment (creates entity link)"),
        ],
    ),

    "record_equipment_hours": ActionDefinition(
        action_id="record_equipment_hours",
        label="Record Running Hours",
        endpoint="/v1/equipment/record-hours",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "hours_reading"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["hours", "running", "meter", "record", "log", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("hours_reading", FieldClassification.REQUIRED, description="Current meter reading"),
            FieldMetadata("reading_type", FieldClassification.OPTIONAL,
                          options=["manual", "automatic", "estimated", "rollover"],
                          description="Default: manual"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="Reading notes"),
        ],
    ),

    # Additional Equipment Lens v2 actions (Phase A)
    "create_equipment": ActionDefinition(
        action_id="create_equipment",
        label="Create Equipment",
        endpoint="/v1/equipment/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "name", "category"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["create", "new", "add", "equipment", "asset", "register"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("name", FieldClassification.REQUIRED, description="Equipment name"),
            FieldMetadata("category", FieldClassification.REQUIRED, description="Equipment category"),
            FieldMetadata("manufacturer", FieldClassification.OPTIONAL),
            FieldMetadata("model", FieldClassification.OPTIONAL),
            FieldMetadata("serial_number", FieldClassification.OPTIONAL),
            FieldMetadata("location", FieldClassification.OPTIONAL),
            FieldMetadata("parent_id", FieldClassification.OPTIONAL, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("running_hours", FieldClassification.OPTIONAL),
        ],
    ),

    "assign_parent_equipment": ActionDefinition(
        action_id="assign_parent_equipment",
        label="Assign Parent Equipment",
        endpoint="/v1/equipment/assign-parent",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["parent", "assign", "hierarchy", "equipment", "child", "group"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("parent_id", FieldClassification.OPTIONAL, auto_populate_from="equipment", lookup_required=True,
                          description="Parent equipment ID (null to clear)"),
        ],
    ),

    "archive_equipment": ActionDefinition(
        action_id="archive_equipment",
        label="Archive Equipment",
        endpoint="/v1/equipment/archive",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "reason"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["archive", "soft", "delete", "hide", "remove", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for archiving"),
        ],
    ),

    "restore_archived_equipment": ActionDefinition(
        action_id="restore_archived_equipment",
        label="Restore Archived Equipment",
        endpoint="/v1/equipment/restore",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "signature"],
        domain="equipment",
        variant=ActionVariant.SIGNED,  # Requires PIN+TOTP
        search_keywords=["restore", "unarchive", "recover", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP signature payload"),
            FieldMetadata("restore_reason", FieldClassification.OPTIONAL, description="Reason for restoration"),
        ],
    ),

    "get_open_faults_for_equipment": ActionDefinition(
        action_id="get_open_faults_for_equipment",
        label="Get Open Faults",
        endpoint="/v1/equipment/open-faults",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id"],
        domain="equipment",
        variant=ActionVariant.READ,
        search_keywords=["open", "faults", "active", "issues", "problems", "equipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("limit", FieldClassification.OPTIONAL, description="Max results (default: 20)"),
            FieldMetadata("offset", FieldClassification.OPTIONAL, description="Pagination offset"),
        ],
    ),

    "get_related_entities_for_equipment": ActionDefinition(
        action_id="get_related_entities_for_equipment",
        label="Show Related",
        endpoint="/v1/equipment/related",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id"],
        domain="equipment",
        variant=ActionVariant.READ,
        search_keywords=["related", "linked", "connected", "show", "equipment", "entities"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("entity_types", FieldClassification.OPTIONAL, description="Filter by entity types"),
        ],
    ),

    "add_entity_link": ActionDefinition(
        action_id="add_entity_link",
        label="Link Entities",
        endpoint="/v1/entity-links/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id"],
        domain="equipment",  # Primary domain
        variant=ActionVariant.MUTATE,
        search_keywords=["link", "connect", "relate", "entity", "relationship"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("source_entity_type", FieldClassification.REQUIRED,
                          options=["equipment", "work_order", "fault", "part"],
                          description="Source entity type"),
            FieldMetadata("source_entity_id", FieldClassification.REQUIRED, description="Source entity ID"),
            FieldMetadata("target_entity_type", FieldClassification.REQUIRED,
                          options=["equipment", "work_order", "fault", "part"],
                          description="Target entity type"),
            FieldMetadata("target_entity_id", FieldClassification.REQUIRED, description="Target entity ID"),
            FieldMetadata("relationship_type", FieldClassification.OPTIONAL,
                          options=["related", "parent", "child", "references", "replaced_by"],
                          description="Relationship type (default: related)"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="Link notes"),
        ],
    ),

    "link_document_to_equipment": ActionDefinition(
        action_id="link_document_to_equipment",
        label="Link Document to Equipment",
        endpoint="/v1/equipment/link-document",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD only - restrict to match document actions
        required_fields=["yacht_id", "equipment_id", "document_id"],
        domain="documents",  # Changed from "equipment" to "documents" per Document Lens v2 spec
        variant=ActionVariant.MUTATE,
        search_keywords=["link", "document", "attach", "manual", "equipment", "file"],
        storage_bucket="documents",
        storage_path_template="{yacht_id}/equipment/{equipment_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="Document metadata ID"),
            FieldMetadata("description", FieldClassification.OPTIONAL, description="Link description"),
        ],
    ),

    # ========================================================================
    # EQUIPMENT LENS V2 - ADDITIONAL ACTIONS (Spec Completion)
    # ========================================================================

    "set_equipment_status": ActionDefinition(
        action_id="set_equipment_status",
        label="Set Equipment Status",
        endpoint="/v1/equipment/set-status",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "to_status"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["mark", "out of service", "return to service", "equipment", "status", "operational"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("to_status", FieldClassification.REQUIRED,
                          options=["operational", "degraded", "failed", "maintenance", "out_of_service", "decommissioned"],
                          description="Target status. CRITICAL: 'out_of_service' requires linked_work_order_id."),
            FieldMetadata("linked_work_order_id", FieldClassification.OPTIONAL,
                          auto_populate_from="work_order", lookup_required=True,
                          description="Required for OOS: must reference OPEN/IN_PROGRESS WO for same equipment+yacht"),
            FieldMetadata("attention_reason", FieldClassification.OPTIONAL,
                          description="Reason for attention flag (failed/degraded)"),
            FieldMetadata("clear_attention", FieldClassification.OPTIONAL,
                          description="Clear attention flag"),
        ],
    ),

    "attach_image_with_comment": ActionDefinition(
        action_id="attach_image_with_comment",
        label="Attach Image with Comment",
        endpoint="/v1/equipment/attach-image",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "file", "comment"],
        domain="equipment",
        variant=ActionVariant.MUTATE,
        search_keywords=["attach", "image", "photo", "comment", "equipment", "document"],
        storage_bucket="documents",
        storage_path_template="{yacht_id}/equipment/{equipment_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("file", FieldClassification.REQUIRED, description="Image file upload"),
            FieldMetadata("comment", FieldClassification.REQUIRED, description="Comment/description for image"),
            FieldMetadata("tags", FieldClassification.OPTIONAL, description="Optional tags array"),
        ],
    ),

    "decommission_and_replace_equipment": ActionDefinition(
        action_id="decommission_and_replace_equipment",
        label="Decommission & Replace Equipment",
        endpoint="/v1/equipment/decommission-replace",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],
        required_fields=["yacht_id", "equipment_id", "reason", "replacement_name"],
        domain="equipment",
        variant=ActionVariant.SIGNED,  # Requires PIN+TOTP
        search_keywords=["decommission", "replace", "equipment", "retire", "swap"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.CONTEXT, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for decommission"),
            FieldMetadata("replacement_name", FieldClassification.REQUIRED, description="Name for replacement equipment"),
            FieldMetadata("replacement_manufacturer", FieldClassification.OPTIONAL, description="Replacement manufacturer"),
            FieldMetadata("replacement_model", FieldClassification.OPTIONAL, description="Replacement model"),
            FieldMetadata("replacement_serial_number", FieldClassification.OPTIONAL, description="Replacement serial number"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP signature payload (execute only)"),
            FieldMetadata("confirmation_token", FieldClassification.OPTIONAL, description="Token from prepare step (execute only)"),
            FieldMetadata("mode", FieldClassification.OPTIONAL,
                          options=["prepare", "execute"],
                          description="prepare=preview (no writes); execute=commit (requires signature)"),
        ],
        context_required={
            "prepare_mode": "Returns proposed_changes, confirmation_token, validation; no database writes",
            "execute_mode": "Requires signature; atomically marks old as decommissioned + creates replacement",
        },
    ),

    # ========================================================================
    # HANDOVER ACTIONS (8) - Dual-hash, dual-signature workflow
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

    "validate_handover_draft": ActionDefinition(
        action_id="validate_handover_draft",
        label="Validate Handover Draft",
        endpoint="/v1/handover/validate",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id"],
        variant=ActionVariant.READ,
    ),

    "finalize_handover_draft": ActionDefinition(
        action_id="finalize_handover_draft",
        label="Finalize Handover Draft",
        endpoint="/v1/handover/finalize",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id"],
        variant=ActionVariant.MUTATE,
    ),

    "export_handover": ActionDefinition(
        action_id="export_handover",
        label="Export Handover",
        endpoint="/v1/handover/export",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id"],
        variant=ActionVariant.MUTATE,
    ),

    "sign_handover_outgoing": ActionDefinition(
        action_id="sign_handover_outgoing",
        label="Sign Handover (Outgoing)",
        endpoint="/v1/handover/sign/outgoing",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["export_id", "yacht_id"],
        variant=ActionVariant.SIGNED,
        signature_roles_required=["chief_engineer", "chief_officer", "captain", "manager"],
    ),

    "sign_handover_incoming": ActionDefinition(
        action_id="sign_handover_incoming",
        label="Sign Handover (Incoming)",
        endpoint="/v1/handover/sign/incoming",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["export_id", "yacht_id", "acknowledge_critical"],
        variant=ActionVariant.SIGNED,
        signature_roles_required=["chief_engineer", "chief_officer", "captain", "manager"],
    ),

    "get_pending_handovers": ActionDefinition(
        action_id="get_pending_handovers",
        label="Get Pending Handovers",
        endpoint="/v1/handover/pending",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id"],
        variant=ActionVariant.READ,
    ),

    "verify_handover_export": ActionDefinition(
        action_id="verify_handover_export",
        label="Verify Handover Export",
        endpoint="/v1/handover/verify",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["export_id", "yacht_id"],
        variant=ActionVariant.READ,
    ),

    # ========================================================================
    # FAULT ACTIONS (Fault Lens v1 - Binding Brief 2026-01-27)
    # ========================================================================
    # Canonical roles per binding brief:
    # - report_fault, add_fault_photo, add_fault_note: crew, chief_engineer, chief_officer, captain
    # - acknowledge/update/reopen/close/diagnose: chief_engineer, chief_officer, captain
    # - view_fault_detail/history: crew, chief_engineer, chief_officer, captain, manager, purser
    # - create_work_order_from_fault (SIGNED): initiate: chief_engineer, chief_officer, captain, manager
    #   Signature requirement: captain or manager role at signing
    # ========================================================================
    "report_fault": ActionDefinition(
        action_id="report_fault",
        label="Report Fault",
        endpoint="/v1/faults/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: crew + HOD + captain (no manager)
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "title", "description"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["report", "add", "create", "fault", "defect", "issue", "problem", "broken", "not working"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.OPTIONAL, auto_populate_from="equipment", lookup_required=True,
                          description="Equipment link (optional - can report fault without equipment)"),
            FieldMetadata("title", FieldClassification.REQUIRED, auto_populate_from="query_text",
                          description="Short fault title (required)"),
            FieldMetadata("description", FieldClassification.REQUIRED, auto_populate_from="symptom",
                          description="Detailed description (required)"),
            FieldMetadata("severity", FieldClassification.OPTIONAL, auto_populate_from="symptom",
                          options=["cosmetic", "minor", "major", "critical", "safety"],
                          description="Default: minor. Auto-mapped from symptoms."),
        ],
    ),

    "acknowledge_fault": ActionDefinition(
        action_id="acknowledge_fault",
        label="Acknowledge Fault",
        endpoint="/v1/faults/acknowledge",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["acknowledge", "confirm", "fault", "ack"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
        ],
    ),

    "close_fault": ActionDefinition(
        action_id="close_fault",
        label="Close Fault",
        endpoint="/v1/faults/close",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["close", "resolve", "fault", "complete"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("resolution_notes", FieldClassification.OPTIONAL),
        ],
    ),

    "update_fault": ActionDefinition(
        action_id="update_fault",
        label="Update Fault",
        endpoint="/v1/faults/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["update", "edit", "modify", "fault"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("severity", FieldClassification.OPTIONAL, options=["cosmetic", "minor", "major", "critical", "safety"]),
            FieldMetadata("status", FieldClassification.OPTIONAL, options=["open", "investigating", "work_ordered", "resolved", "closed"]),
        ],
    ),

    "add_fault_photo": ActionDefinition(
        action_id="add_fault_photo",
        label="Add Fault Photo",
        endpoint="/v1/faults/add-photo",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: crew + HOD + captain
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id", "photo_url"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "upload", "photo", "image", "fault", "picture"],
        storage_bucket="pms-discrepancy-photos",
        storage_path_template="{yacht_id}/faults/{fault_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("photo_url", FieldClassification.REQUIRED, description="Storage path after upload"),
            FieldMetadata("caption", FieldClassification.OPTIONAL),
        ],
    ),

    "add_fault_note": ActionDefinition(
        action_id="add_fault_note",
        label="Add Fault Note",
        endpoint="/v1/faults/add-note",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: crew + HOD + captain
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id", "text"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "note", "comment", "fault", "observation"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("text", FieldClassification.REQUIRED),
        ],
    ),

    "view_fault_detail": ActionDefinition(
        action_id="view_fault_detail",
        label="View Fault Detail",
        endpoint="/v1/faults/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: all including manager and purser
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.READ,
        search_keywords=["view", "detail", "show", "fault", "see"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
        ],
    ),

    "view_fault_history": ActionDefinition(
        action_id="view_fault_history",
        label="View Fault History",
        endpoint="/v1/faults/history",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: all including manager and purser
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
        required_fields=["yacht_id", "equipment_id"],
        domain="faults",
        variant=ActionVariant.READ,
        search_keywords=["view", "history", "fault", "past", "previous", "recurrence"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("equipment_id", FieldClassification.REQUIRED, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("limit", FieldClassification.OPTIONAL, description="Max records to return (default: 50)"),
        ],
    ),

    "diagnose_fault": ActionDefinition(
        action_id="diagnose_fault",
        label="Diagnose Fault",
        endpoint="/v1/faults/diagnose",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["diagnose", "analysis", "fault", "troubleshoot"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("diagnosis", FieldClassification.REQUIRED, description="Root cause analysis text"),
            FieldMetadata("recommended_action", FieldClassification.OPTIONAL),
        ],
    ),

    "reopen_fault": ActionDefinition(
        action_id="reopen_fault",
        label="Reopen Fault",
        endpoint="/v1/faults/reopen",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["reopen", "re-open", "fault", "restore"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for reopening"),
        ],
    ),

    "mark_fault_false_alarm": ActionDefinition(
        action_id="mark_fault_false_alarm",
        label="Mark Fault as False Alarm",
        endpoint="/v1/faults/mark-false-alarm",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # Canonical: HOD + captain only
        allowed_roles=["chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "fault_id"],
        domain="faults",
        variant=ActionVariant.MUTATE,
        search_keywords=["false", "alarm", "dismiss", "fault", "cancel"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("fault_id", FieldClassification.REQUIRED, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("reason", FieldClassification.OPTIONAL, description="Reason for marking as false alarm"),
        ],
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
    # RECEIVING LENS V1 ACTIONS (10 actions)
    # ========================================================================
    # Workflow: Image upload → OCR extraction → User review/adjust → Accept (SIGNED)
    # Roles: HOD+ for mutations, Captain/Manager for signed acceptance
    # Storage: {yacht_id}/receiving/{receiving_id}/{filename}
    # ========================================================================

    "create_receiving": ActionDefinition(
        action_id="create_receiving",
        label="Create Receiving",
        endpoint="/v1/receiving/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["new", "create", "receive", "invoice", "package", "delivery", "shipment"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("vendor_name", FieldClassification.OPTIONAL, description="Vendor/supplier name"),
            FieldMetadata("vendor_reference", FieldClassification.OPTIONAL, description="Invoice number, AWB, packing slip"),
            FieldMetadata("received_date", FieldClassification.OPTIONAL, description="Receipt date (default today)"),
            FieldMetadata("currency", FieldClassification.OPTIONAL, description="Currency code"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="General notes"),
            FieldMetadata("linked_work_order_id", FieldClassification.OPTIONAL, description="Link to work order if applicable"),
        ],
    ),

    "attach_receiving_image_with_comment": ActionDefinition(
        action_id="attach_receiving_image_with_comment",
        label="Attach Image/Document",
        endpoint="/v1/receiving/attach-image",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "document_id"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["attach", "upload", "scan", "photo", "image", "document"],
        storage_bucket="pms-receiving-images",  # or "documents" for PDFs
        storage_path_template="{yacht_id}/receiving/{receiving_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="Document metadata ID"),
            FieldMetadata("doc_type", FieldClassification.OPTIONAL, options=["invoice", "packing_slip", "photo"], description="Document type"),
            FieldMetadata("comment", FieldClassification.OPTIONAL, description="Inline comment about this attachment"),
        ],
    ),

    "extract_receiving_candidates": ActionDefinition(
        action_id="extract_receiving_candidates",
        label="Extract from Image (OCR)",
        endpoint="/v1/receiving/extract",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "source_document_id"],
        domain="receiving",
        variant=ActionVariant.READ,  # PREPARE-only action (advisory)
        search_keywords=["extract", "scan", "ocr", "parse", "read"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("source_document_id", FieldClassification.REQUIRED, description="Document to extract from"),
        ],
    ),

    "update_receiving_fields": ActionDefinition(
        action_id="update_receiving_fields",
        label="Update Receiving Fields",
        endpoint="/v1/receiving/update-fields",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["update", "edit", "change", "modify"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("vendor_name", FieldClassification.OPTIONAL, description="Vendor/supplier name"),
            FieldMetadata("vendor_reference", FieldClassification.OPTIONAL, description="Invoice number"),
            FieldMetadata("currency", FieldClassification.OPTIONAL, description="Currency code"),
            FieldMetadata("received_date", FieldClassification.OPTIONAL, description="Receipt date"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="Notes"),
        ],
    ),

    "add_receiving_item": ActionDefinition(
        action_id="add_receiving_item",
        label="Add Line Item",
        endpoint="/v1/receiving/add-item",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "quantity_received"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "item", "line", "part", "product"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("part_id", FieldClassification.OPTIONAL, description="Link to parts catalog"),
            FieldMetadata("description", FieldClassification.OPTIONAL, description="Part description (required if no part_id)"),
            FieldMetadata("quantity_expected", FieldClassification.OPTIONAL, description="Expected quantity from PO"),
            FieldMetadata("quantity_received", FieldClassification.REQUIRED, description="Actual quantity received"),
            FieldMetadata("unit_price", FieldClassification.OPTIONAL, description="Unit price"),
            FieldMetadata("currency", FieldClassification.OPTIONAL, description="Currency code"),
        ],
    ),

    "adjust_receiving_item": ActionDefinition(
        action_id="adjust_receiving_item",
        label="Adjust Line Item",
        endpoint="/v1/receiving/adjust-item",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "receiving_item_id"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["adjust", "modify", "update", "change", "item"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("receiving_item_id", FieldClassification.REQUIRED, description="Line item ID"),
            FieldMetadata("quantity_received", FieldClassification.OPTIONAL, description="Updated quantity"),
            FieldMetadata("unit_price", FieldClassification.OPTIONAL, description="Updated price"),
            FieldMetadata("description", FieldClassification.OPTIONAL, description="Updated description"),
        ],
    ),

    "link_invoice_document": ActionDefinition(
        action_id="link_invoice_document",
        label="Link Invoice PDF",
        endpoint="/v1/receiving/link-invoice",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "document_id"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["link", "attach", "invoice", "pdf", "document"],
        storage_bucket="documents",
        storage_path_template="{yacht_id}/receiving/{receiving_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="Document metadata ID"),
            FieldMetadata("comment", FieldClassification.OPTIONAL, description="Comment about this document"),
        ],
    ),

    "accept_receiving": ActionDefinition(
        action_id="accept_receiving",
        label="Accept Receiving (Sign)",
        endpoint="/v1/receiving/accept",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id"],
        domain="receiving",
        variant=ActionVariant.SIGNED,
        signature_roles_required=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        search_keywords=["accept", "approve", "sign", "finalize", "confirm"],
        prefill_endpoint="/v1/receiving/accept?mode=prepare",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="Signature payload (PIN+TOTP) - execute only"),
        ],
    ),

    "reject_receiving": ActionDefinition(
        action_id="reject_receiving",
        label="Reject Receiving",
        endpoint="/v1/receiving/reject",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id", "reason"],
        domain="receiving",
        variant=ActionVariant.MUTATE,
        search_keywords=["reject", "decline", "refuse", "cancel"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Reason for rejection"),
        ],
    ),

    "view_receiving_history": ActionDefinition(
        action_id="view_receiving_history",
        label="View Receiving History",
        endpoint="/v1/receiving/history",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "receiving_id"],
        domain="receiving",
        variant=ActionVariant.READ,
        search_keywords=["view", "history", "audit", "trail", "log"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("receiving_id", FieldClassification.REQUIRED, description="Receiving record ID"),
        ],
    ),

    # ========================================================================
    # CERTIFICATE ACTIONS
    # ========================================================================
    "create_vessel_certificate": ActionDefinition(
        action_id="create_vessel_certificate",
        label="Add Vessel Certificate",
        endpoint="/v1/certificates/create-vessel",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],  # HOD roles
        required_fields=[
            "yacht_id",
            "certificate_type",
            "certificate_name",
            "issuing_authority",
        ],
        schema_file=None,
        domain="certificates",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "create", "new", "vessel", "certificate", "cert", "flag", "class", "safety"],
    ),

    "create_crew_certificate": ActionDefinition(
        action_id="create_crew_certificate",
        label="Add Crew Certificate",
        endpoint="/v1/certificates/create-crew",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],  # HOD roles
        required_fields=[
            "yacht_id",
            "person_name",
            "certificate_type",
            "issuing_authority",
        ],
        schema_file=None,
        domain="certificates",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "create", "new", "crew", "certificate", "cert", "stcw", "training"],
    ),

    "update_certificate": ActionDefinition(
        action_id="update_certificate",
        label="Update Certificate",
        endpoint="/v1/certificates/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],  # HOD roles
        required_fields=[
            "yacht_id",
            "certificate_id",
        ],
        schema_file=None,
        domain="certificates",
        variant=ActionVariant.MUTATE,
        search_keywords=["update", "edit", "modify", "change", "certificate", "cert", "expiry", "renewal"],
    ),

    "link_document_to_certificate": ActionDefinition(
        action_id="link_document_to_certificate",
        label="Link Document to Certificate",
        endpoint="/v1/certificates/link-document",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],  # HOD roles
        required_fields=[
            "yacht_id",
            "certificate_id",
            "document_id",
        ],
        schema_file=None,
        domain="certificates",
        variant=ActionVariant.MUTATE,
        search_keywords=["link", "attach", "upload", "document", "doc", "file", "pdf", "certificate", "cert"],
    ),

    "supersede_certificate": ActionDefinition(
        action_id="supersede_certificate",
        label="Supersede Certificate",
        endpoint="/v1/certificates/supersede",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # Manager roles for SIGNED action
        required_fields=[
            "yacht_id",
            "certificate_id",
            "reason",
            "signature",  # REQUIRED - signed action
        ],
        schema_file=None,
        domain="certificates",
        variant=ActionVariant.SIGNED,
        search_keywords=["supersede", "replace", "renew", "certificate", "cert", "expire", "sign"],
    ),

    # ========================================================================
    # DOCUMENT ACTIONS (Document Lens v2)
    # ========================================================================
    # Domain: documents
    # Table: doc_metadata (yacht-scoped, RLS enabled)
    # Storage: documents bucket, path: {yacht_id}/documents/{document_id}/{filename}
    # Handlers: apps/api/handlers/document_handlers.py
    #
    # Actions:
    #   upload_document     - MUTATE (All Crew) - Upload new document
    #   update_document     - MUTATE (HOD)      - Update metadata (title, tags, oem, doc_type)
    #   add_document_tags   - MUTATE (HOD)      - Batch add/modify tags
    #   delete_document     - SIGNED (Manager)  - Soft-delete with reason + signature
    #   get_document_url    - READ (All Crew)   - Get signed download URL
    #
    # NOTE: link_document_to_equipment is in Equipment section (domain=equipment)
    # NOTE: link_document_to_certificate is in Certificate section (domain=certificates)
    # ========================================================================

    "upload_document": ActionDefinition(
        action_id="upload_document",
        label="Upload Document",
        endpoint="/v1/documents/upload",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD roles - crew deny mutations
        required_fields=["yacht_id", "file_name", "mime_type"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["upload", "add", "create", "document", "doc", "file", "manual", "pdf", "attach"],
        storage_bucket="documents",
        storage_path_template="{yacht_id}/documents/{document_id}/{filename}",
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("file_name", FieldClassification.REQUIRED, description="Original filename (with extension)"),
            FieldMetadata("mime_type", FieldClassification.REQUIRED, description="MIME type (e.g., application/pdf, image/jpeg)"),
            FieldMetadata("title", FieldClassification.OPTIONAL, description="Human-readable document title"),
            FieldMetadata("doc_type", FieldClassification.OPTIONAL,
                          options=["manual", "drawing", "certificate", "report", "photo", "spec_sheet", "schematic", "other"],
                          description="Document classification"),
            FieldMetadata("oem", FieldClassification.OPTIONAL, description="Manufacturer/OEM name"),
            FieldMetadata("model_number", FieldClassification.OPTIONAL, description="Equipment model number"),
            FieldMetadata("serial_number", FieldClassification.OPTIONAL, description="Serial number if applicable"),
            FieldMetadata("system_path", FieldClassification.OPTIONAL, description="Hierarchical system path (e.g., 'propulsion/main_engine')"),
            FieldMetadata("tags", FieldClassification.OPTIONAL, description="Array of string tags"),
            FieldMetadata("equipment_ids", FieldClassification.OPTIONAL, description="Array of equipment UUIDs to link"),
            FieldMetadata("notes", FieldClassification.OPTIONAL, description="Upload notes/description"),
        ],
    ),

    "update_document": ActionDefinition(
        action_id="update_document",
        label="Update Document",
        endpoint="/v1/documents/update",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD roles
        required_fields=["yacht_id", "document_id"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["update", "edit", "modify", "document", "doc", "metadata", "title", "tags"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("title", FieldClassification.OPTIONAL, description="Update title"),
            FieldMetadata("doc_type", FieldClassification.OPTIONAL,
                          options=["manual", "drawing", "certificate", "report", "photo", "spec_sheet", "schematic", "other"]),
            FieldMetadata("oem", FieldClassification.OPTIONAL, description="Update OEM/manufacturer"),
            FieldMetadata("model_number", FieldClassification.OPTIONAL),
            FieldMetadata("serial_number", FieldClassification.OPTIONAL),
            FieldMetadata("system_path", FieldClassification.OPTIONAL),
            FieldMetadata("tags", FieldClassification.OPTIONAL, description="Replace tags array"),
            FieldMetadata("equipment_ids", FieldClassification.OPTIONAL, description="Replace linked equipment array"),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "add_document_tags": ActionDefinition(
        action_id="add_document_tags",
        label="Add Document Tags",
        endpoint="/v1/documents/add-tags",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD roles
        required_fields=["yacht_id", "document_id", "tags"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["tag", "label", "categorize", "document", "doc", "organize", "classify"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("tags", FieldClassification.REQUIRED, description="Array of tags to add (merges with existing)"),
            FieldMetadata("replace", FieldClassification.OPTIONAL, description="If true, replace all tags instead of merging"),
        ],
    ),

    "delete_document": ActionDefinition(
        action_id="delete_document",
        label="Delete Document",
        endpoint="/v1/documents/delete",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # Manager roles - SIGNED action
        required_fields=["yacht_id", "document_id", "reason", "signature"],
        domain="documents",
        variant=ActionVariant.SIGNED,
        search_keywords=["delete", "remove", "archive", "document", "doc", "destroy"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("reason", FieldClassification.REQUIRED, description="Deletion reason (audit trail)"),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="Digital signature JSON payload"),
        ],
    ),

    "get_document_url": ActionDefinition(
        action_id="get_document_url",
        label="Get Document Download Link",
        endpoint="/v1/documents/get-url",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "document_id"],
        domain="documents",
        variant=ActionVariant.READ,
        search_keywords=["download", "view", "open", "document", "doc", "link", "url", "get"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("expires_in", FieldClassification.OPTIONAL, description="URL expiry seconds (default: 3600)"),
        ],
    ),

    # ========================================================================
    # DOCUMENT COMMENT ACTIONS (Document Lens v2 - MVP)
    # ========================================================================
    # Domain: documents
    # Tables: doc_metadata_comments
    # MVP Scope: Document-level comments only (no page/section-specific)
    # ========================================================================

    "add_document_comment": ActionDefinition(
        action_id="add_document_comment",
        label="Add Comment",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD only - no crew mutations
        required_fields=["yacht_id", "document_id", "comment"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["comment", "note", "document", "add", "remark", "write", "leave", "post", "annotation"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("comment", FieldClassification.REQUIRED, description="Comment text"),
            FieldMetadata("parent_comment_id", FieldClassification.OPTIONAL, description="Parent comment UUID for threading"),
        ],
    ),

    "update_document_comment": ActionDefinition(
        action_id="update_document_comment",
        label="Edit Comment",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD only - no crew mutations
        required_fields=["yacht_id", "comment_id", "comment"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["edit", "update", "modify", "comment", "change", "fix", "correct", "revise", "alter", "note"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("comment_id", FieldClassification.REQUIRED, description="Comment UUID to edit"),
            FieldMetadata("comment", FieldClassification.REQUIRED, description="New comment text"),
        ],
    ),

    "delete_document_comment": ActionDefinition(
        action_id="delete_document_comment",
        label="Delete Comment",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],  # HOD only - no crew mutations
        required_fields=["yacht_id", "comment_id"],
        domain="documents",
        variant=ActionVariant.MUTATE,
        search_keywords=["delete", "remove", "comment", "erase", "trash", "discard", "clear", "note"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("comment_id", FieldClassification.REQUIRED, description="Comment UUID to delete"),
        ],
    ),

    "list_document_comments": ActionDefinition(
        action_id="list_document_comments",
        label="View Comments",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
                       "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "document_id"],
        domain="documents",
        variant=ActionVariant.READ,
        search_keywords=["list", "view", "comments", "document", "show", "see", "read", "notes", "what", "said", "wrote", "recent"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="doc_metadata.id UUID"),
            FieldMetadata("include_threads", FieldClassification.OPTIONAL, description="Include threaded replies (default: true)"),
        ],
    ),

    # ========================================================================
    # PARTS/INVENTORY ACTIONS (Part Lens v2)
    # ========================================================================
    # 10 actions: 2 READ, 6 MUTATE, 2 SIGNED
    # All mutations write to pms_audit_log (signature: {} or payload)
    # All stock mutations create pms_inventory_transactions
    # Suggested order qty = round_up(max(min_level - on_hand, 1), reorder_multiple)
    # ========================================================================

    # Legacy P0 Inventory actions (exposed for suggestions; execution handled via p0_actions_routes)
    "check_stock_level": ActionDefinition(
        action_id="check_stock_level",
        label="Check Stock Level",
        endpoint="/v1/actions/execute",  # Routed internally by p0_actions_routes
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # READ action: allow all crew to view stock
        allowed_roles=[
            "crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
            "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"
        ],
        required_fields=["yacht_id", "part_id"],
        domain="parts",
        variant=ActionVariant.READ,
        search_keywords=["check", "stock", "inventory", "view", "part", "level", "quantity"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
        ],
    ),

    "log_part_usage": ActionDefinition(
        action_id="log_part_usage",
        label="Log Part Usage",
        endpoint="/v1/actions/execute",  # Routed internally by p0_actions_routes
        handler_type=HandlerType.INTERNAL,
        method="POST",
        # MUTATE action: HOD and above
        allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity", "usage_reason"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["log", "use", "consume", "part", "deduct", "inventory", "stock"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED, description="Amount to deduct from stock"),
            FieldMetadata("usage_reason", FieldClassification.REQUIRED,
                          options=["work_order", "maintenance", "repair", "inspection", "other"]),
            FieldMetadata("work_order_id", FieldClassification.OPTIONAL, auto_populate_from="work_order", lookup_required=True),
            FieldMetadata("equipment_id", FieldClassification.OPTIONAL, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    # ========================================================================
    # SHOPPING LIST LENS ACTIONS (v1)
    # ========================================================================
    # Domain: shopping_list
    # Tables: pms_shopping_list_items, pms_shopping_list_state_history
    # Handlers: apps/api/handlers/shopping_list_handlers.py
    # ========================================================================

    "create_shopping_list_item": ActionDefinition(
        action_id="create_shopping_list_item",
        label="Add to Shopping List",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_name", "quantity_requested", "source_type"],
        domain="shopping_list",
        variant=ActionVariant.MUTATE,
        search_keywords=["add", "shopping", "list", "request", "order", "need", "buy", "purchase"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_name", FieldClassification.REQUIRED, description="Name of part/item needed"),
            FieldMetadata("quantity_requested", FieldClassification.REQUIRED, description="Amount requested (must be > 0)"),
            FieldMetadata("source_type", FieldClassification.REQUIRED,
                          options=["inventory_low", "inventory_oos", "work_order_usage", "receiving_missing", "receiving_damaged", "manual_add"],
                          description="Origin of request"),
            FieldMetadata("part_id", FieldClassification.OPTIONAL, description="Link to existing part in catalog"),
            FieldMetadata("part_number", FieldClassification.OPTIONAL),
            FieldMetadata("manufacturer", FieldClassification.OPTIONAL),
            FieldMetadata("unit", FieldClassification.OPTIONAL,
                          options=["ea", "kg", "L", "m", "box", "set", "roll"]),
            FieldMetadata("preferred_supplier", FieldClassification.OPTIONAL),
            FieldMetadata("estimated_unit_price", FieldClassification.OPTIONAL),
            FieldMetadata("urgency", FieldClassification.OPTIONAL,
                          options=["low", "normal", "high", "critical"]),
            FieldMetadata("required_by_date", FieldClassification.OPTIONAL, description="Deadline (ISO date)"),
            FieldMetadata("source_work_order_id", FieldClassification.OPTIONAL, description="Source WO if from work order"),
            FieldMetadata("source_receiving_id", FieldClassification.OPTIONAL, description="Source receiving if from receiving"),
            FieldMetadata("source_notes", FieldClassification.OPTIONAL),
        ],
    ),

    "approve_shopping_list_item": ActionDefinition(
        action_id="approve_shopping_list_item",
        label="Approve Shopping List Item",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HoD only
        required_fields=["yacht_id", "item_id", "quantity_approved"],
        domain="shopping_list",
        variant=ActionVariant.MUTATE,
        search_keywords=["approve", "shopping", "list", "accept", "authorize"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("item_id", FieldClassification.REQUIRED, description="Shopping list item ID"),
            FieldMetadata("quantity_approved", FieldClassification.REQUIRED, description="Approved amount (must be > 0)"),
            FieldMetadata("approval_notes", FieldClassification.OPTIONAL),
        ],
    ),

    "reject_shopping_list_item": ActionDefinition(
        action_id="reject_shopping_list_item",
        label="Reject Shopping List Item",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HoD only
        required_fields=["yacht_id", "item_id", "rejection_reason"],
        domain="shopping_list",
        variant=ActionVariant.MUTATE,
        search_keywords=["reject", "shopping", "list", "deny", "decline"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("item_id", FieldClassification.REQUIRED, description="Shopping list item ID"),
            FieldMetadata("rejection_reason", FieldClassification.REQUIRED, description="Why item was rejected"),
            FieldMetadata("rejection_notes", FieldClassification.OPTIONAL),
        ],
    ),

    "promote_candidate_to_part": ActionDefinition(
        action_id="promote_candidate_to_part",
        label="Add to Parts Catalog",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "manager"],  # Engineers only
        required_fields=["yacht_id", "item_id"],
        domain="shopping_list",
        variant=ActionVariant.MUTATE,
        search_keywords=["promote", "catalog", "part", "add", "create"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("item_id", FieldClassification.REQUIRED, description="Shopping list item ID (must be candidate)"),
        ],
    ),

    "view_shopping_list_history": ActionDefinition(
        action_id="view_shopping_list_history",
        label="View Item History",
        endpoint="/v1/actions/execute",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager"],  # All crew
        required_fields=["yacht_id", "item_id"],
        domain="shopping_list",
        variant=ActionVariant.READ,
        search_keywords=["history", "timeline", "changes", "audit"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("item_id", FieldClassification.REQUIRED, description="Shopping list item ID"),
        ],
    ),

    "consume_part": ActionDefinition(
        action_id="consume_part",
        label="Consume Part",
        endpoint="/v1/parts/consume",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["consume", "use", "part", "install", "fit", "work", "order", "deplete"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED, description="Must not exceed on_hand; 409 if insufficient"),
            FieldMetadata("work_order_id", FieldClassification.OPTIONAL, auto_populate_from="work_order", lookup_required=True),
            FieldMetadata("location_id", FieldClassification.BACKEND_AUTO, auto_populate_from="part"),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "adjust_stock_quantity": ActionDefinition(
        action_id="adjust_stock_quantity",
        label="Adjust Stock",
        endpoint="/v1/parts/adjust-stock",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # SIGNED actions: Captain/Manager only
        required_fields=["yacht_id", "part_id", "new_quantity", "reason", "signature"],
        domain="parts",
        variant=ActionVariant.SIGNED,  # Requires PIN+TOTP
        search_keywords=["adjust", "stock", "count", "inventory", "correct", "fix", "quantity", "update", "cycle"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("current_quantity", FieldClassification.BACKEND_AUTO, auto_populate_from="part"),
            FieldMetadata("new_quantity", FieldClassification.REQUIRED),
            FieldMetadata("reason", FieldClassification.REQUIRED, options=[
                "physical_count", "damaged", "expired", "found_additional", "correction", "other"
            ]),
            FieldMetadata("location_id", FieldClassification.OPTIONAL, lookup_required=True),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP payload"),
        ],
        prefill_endpoint="/v1/parts/adjust-stock/prefill",
    ),

    "receive_part": ActionDefinition(
        action_id="receive_part",
        label="Receive Part",
        endpoint="/v1/parts/receive",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity_received", "idempotency_key"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["receive", "delivery", "arrived", "part", "stock", "in", "add", "delivered"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity_received", FieldClassification.REQUIRED),
            FieldMetadata("idempotency_key", FieldClassification.REQUIRED, description="(yacht_id, idempotency_key) unique; 409 on duplicate"),
            FieldMetadata("supplier_id", FieldClassification.OPTIONAL, lookup_required=True),
            FieldMetadata("invoice_number", FieldClassification.OPTIONAL),
            FieldMetadata("location_id", FieldClassification.OPTIONAL, auto_populate_from="part"),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
            FieldMetadata("photo_storage_path", FieldClassification.OPTIONAL, description="Path in pms-receiving-images bucket"),
        ],
        storage_bucket="pms-receiving-images",
        storage_path_template="{yacht_id}/receiving/{part_id}/{filename}",
    ),

    "transfer_part": ActionDefinition(
        action_id="transfer_part",
        label="Transfer Part",
        endpoint="/v1/parts/transfer",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_id", "quantity", "from_location_id", "to_location_id"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["transfer", "move", "part", "location", "relocate", "shift"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED),
            FieldMetadata("from_location_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("to_location_id", FieldClassification.REQUIRED, lookup_required=True),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "write_off_part": ActionDefinition(
        action_id="write_off_part",
        label="Write Off Part",
        endpoint="/v1/parts/write-off",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # SIGNED actions: Captain/Manager only
        required_fields=["yacht_id", "part_id", "quantity", "reason", "signature"],
        domain="parts",
        variant=ActionVariant.SIGNED,  # Requires PIN+TOTP
        search_keywords=["write", "off", "scrap", "dispose", "discard", "damaged", "expired", "lost"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
            FieldMetadata("quantity", FieldClassification.REQUIRED),
            FieldMetadata("reason", FieldClassification.REQUIRED, options=[
                "damaged", "expired", "obsolete", "lost", "contaminated", "other"
            ]),
            FieldMetadata("location_id", FieldClassification.OPTIONAL, auto_populate_from="part", lookup_required=True),
            FieldMetadata("signature", FieldClassification.REQUIRED, description="PIN+TOTP payload"),
        ],
    ),

    "view_part_details": ActionDefinition(
        action_id="view_part_details",
        label="View Part Details",
        endpoint="/v1/parts/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "bosun", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
        required_fields=["yacht_id", "part_id"],
        domain="parts",
        variant=ActionVariant.READ,
        search_keywords=["view", "part", "details", "info", "stock", "see", "show"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_id", FieldClassification.REQUIRED, auto_populate_from="part", lookup_required=True),
        ],
    ),

    "view_low_stock": ActionDefinition(
        action_id="view_low_stock",
        label="View Low Stock",
        endpoint="/v1/parts/low-stock",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["*"],  # All authenticated users can view low stock report
        required_fields=["yacht_id"],
        domain="parts",
        variant=ActionVariant.READ,
        search_keywords=["low", "stock", "reorder", "minimum", "parts", "alert", "warning", "below"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("threshold_percent", FieldClassification.OPTIONAL, description="Filter by % of min_level"),
            FieldMetadata("department", FieldClassification.OPTIONAL, description="Filter by department"),
        ],
    ),

    "generate_part_labels": ActionDefinition(
        action_id="generate_part_labels",
        label="Generate Part Labels",
        endpoint="/v1/parts/labels/generate",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HOD+ only
        required_fields=["yacht_id", "part_ids"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["generate", "label", "print", "barcode", "qr", "sticker", "tag"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("part_ids", FieldClassification.REQUIRED, description="Array of part UUIDs"),
            FieldMetadata("label_format", FieldClassification.OPTIONAL, options=["small", "medium", "large"]),
            FieldMetadata("include_qr", FieldClassification.OPTIONAL),
            FieldMetadata("include_barcode", FieldClassification.OPTIONAL),
        ],
        storage_bucket="pms-label-pdfs",
        storage_path_template="{yacht_id}/parts/{part_id}/labels/{filename}",
    ),

    "request_label_output": ActionDefinition(
        action_id="request_label_output",
        label="Output Labels",
        endpoint="/v1/parts/labels/output",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HOD+ only
        required_fields=["yacht_id", "document_id", "output"],
        domain="parts",
        variant=ActionVariant.MUTATE,
        search_keywords=["print", "email", "download", "label", "output", "send"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("document_id", FieldClassification.REQUIRED, description="From generate_part_labels"),
            FieldMetadata("output", FieldClassification.REQUIRED, options=["print", "email", "download"]),
            FieldMetadata("email_address", FieldClassification.OPTIONAL, description="Required if output=email"),
            FieldMetadata("printer_id", FieldClassification.OPTIONAL, description="Required if output=print"),
        ],
    ),

    # ========================================================================
    # WARRANTY CLAIM ACTIONS (PR #5 - Fault Lens v1)
    # ========================================================================
    # Roles:
    # - draft_warranty_claim: crew, chief_engineer, chief_officer, captain
    # - submit_warranty_claim: chief_engineer, chief_officer, captain (HOD)
    # - approve/reject: captain, manager
    # Storage: pms-warranty-docs bucket with yacht-scoped prefixes
    # ========================================================================

    "draft_warranty_claim": ActionDefinition(
        action_id="draft_warranty_claim",
        label="Draft Warranty Claim",
        endpoint="/v1/warranty/draft",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain"],
        required_fields=["yacht_id", "title", "description"],
        domain="warranty",
        variant=ActionVariant.MUTATE,
        search_keywords=["draft", "create", "warranty", "claim", "new"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("title", FieldClassification.REQUIRED),
            FieldMetadata("description", FieldClassification.REQUIRED),
            FieldMetadata("claim_type", FieldClassification.OPTIONAL, options=["repair", "replacement", "refund"]),
            FieldMetadata("equipment_id", FieldClassification.OPTIONAL, auto_populate_from="equipment", lookup_required=True),
            FieldMetadata("fault_id", FieldClassification.OPTIONAL, auto_populate_from="fault", lookup_required=True),
            FieldMetadata("vendor_name", FieldClassification.OPTIONAL),
            FieldMetadata("manufacturer", FieldClassification.OPTIONAL),
            FieldMetadata("claimed_amount", FieldClassification.OPTIONAL),
        ],
    ),

    "submit_warranty_claim": ActionDefinition(
        action_id="submit_warranty_claim",
        label="Submit Warranty Claim",
        endpoint="/v1/warranty/submit",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain"],  # HOD only
        required_fields=["yacht_id", "claim_id"],
        domain="warranty",
        variant=ActionVariant.MUTATE,
        search_keywords=["submit", "warranty", "claim", "send", "approval"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("claim_id", FieldClassification.REQUIRED),
        ],
    ),

    "approve_warranty_claim": ActionDefinition(
        action_id="approve_warranty_claim",
        label="Approve Warranty Claim",
        endpoint="/v1/warranty/approve",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # Captain/Manager only
        required_fields=["yacht_id", "claim_id"],
        domain="warranty",
        variant=ActionVariant.MUTATE,
        search_keywords=["approve", "warranty", "claim", "accept"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("claim_id", FieldClassification.REQUIRED),
            FieldMetadata("approved_amount", FieldClassification.OPTIONAL),
            FieldMetadata("notes", FieldClassification.OPTIONAL),
        ],
    ),

    "reject_warranty_claim": ActionDefinition(
        action_id="reject_warranty_claim",
        label="Reject Warranty Claim",
        endpoint="/v1/warranty/reject",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["captain", "manager"],  # Captain/Manager only
        required_fields=["yacht_id", "claim_id", "rejection_reason"],
        domain="warranty",
        variant=ActionVariant.MUTATE,
        search_keywords=["reject", "deny", "warranty", "claim"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("claim_id", FieldClassification.REQUIRED),
            FieldMetadata("rejection_reason", FieldClassification.REQUIRED),
        ],
    ),

    "view_warranty_claim": ActionDefinition(
        action_id="view_warranty_claim",
        label="View Warranty Claim",
        endpoint="/v1/warranty/view",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
        required_fields=["yacht_id", "claim_id"],
        domain="warranty",
        variant=ActionVariant.READ,
        search_keywords=["view", "warranty", "claim", "detail", "show"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("claim_id", FieldClassification.REQUIRED),
        ],
    ),

    "compose_warranty_email": ActionDefinition(
        action_id="compose_warranty_email",
        label="Compose Warranty Email",
        endpoint="/v1/warranty/compose-email",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "captain", "manager"],  # HOD+ only
        required_fields=["yacht_id", "claim_id"],
        domain="warranty",
        variant=ActionVariant.READ,  # Prepare only, does not send
        search_keywords=["compose", "email", "warranty", "claim", "draft", "send"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("claim_id", FieldClassification.REQUIRED),
        ],
    ),

    # ========================================================================
    # HOURS OF REST ACTIONS (Crew Lens v3) - 12 actions
    # ========================================================================
    # Maritime Labour Convention (MLC 2006) & STCW Convention compliance
    #
    # Role Groups for Crew Lens:
    # - ALL_CREW: All maritime crew roles (can view own records, acknowledge warnings)
    # - HOD_PLUS: Head of Department and above (can manage department, dismiss warnings)

    # READ: Daily Hours of Rest
    "get_hours_of_rest": ActionDefinition(
        action_id="get_hours_of_rest",
        label="View Hours of Rest",
        endpoint="/v1/hours-of-rest",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="hours_of_rest",
        variant=ActionVariant.READ,
        search_keywords=["hours", "rest", "hor", "compliance", "mlc", "stcw", "crew", "view"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.OPTIONAL),
            FieldMetadata("start_date", FieldClassification.OPTIONAL),
            FieldMetadata("end_date", FieldClassification.OPTIONAL),
        ],
    ),

    # MUTATE: Daily Hours of Rest
    "upsert_hours_of_rest": ActionDefinition(
        action_id="upsert_hours_of_rest",
        label="Log Hours of Rest",
        endpoint="/v1/hours-of-rest/upsert",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "record_date", "rest_periods", "total_rest_hours"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["log", "hours", "rest", "create", "update", "daily", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("record_date", FieldClassification.REQUIRED),
            FieldMetadata("rest_periods", FieldClassification.REQUIRED),
            FieldMetadata("total_rest_hours", FieldClassification.REQUIRED),
        ],
    ),

    # READ: Monthly Sign-offs
    "list_monthly_signoffs": ActionDefinition(
        action_id="list_monthly_signoffs",
        label="List Monthly Sign-offs",
        endpoint="/v1/hours-of-rest/signoffs",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="hours_of_rest",
        variant=ActionVariant.READ,
        search_keywords=["signoff", "monthly", "approval", "list", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
        ],
    ),

    "get_monthly_signoff": ActionDefinition(
        action_id="get_monthly_signoff",
        label="View Monthly Sign-off",
        endpoint="/v1/hours-of-rest/signoffs/details",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "signoff_id"],
        domain="hours_of_rest",
        variant=ActionVariant.READ,
        search_keywords=["signoff", "monthly", "view", "details", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("signoff_id", FieldClassification.REQUIRED),
        ],
    ),

    # MUTATE: Monthly Sign-offs
    "create_monthly_signoff": ActionDefinition(
        action_id="create_monthly_signoff",
        label="Create Monthly Sign-off",
        endpoint="/v1/hours-of-rest/signoffs/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "month", "department"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["create", "signoff", "monthly", "initiate", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("month", FieldClassification.REQUIRED),
            FieldMetadata("department", FieldClassification.REQUIRED),
        ],
    ),

    "sign_monthly_signoff": ActionDefinition(
        action_id="sign_monthly_signoff",
        label="Sign Monthly Sign-off",
        endpoint="/v1/hours-of-rest/signoffs/sign",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "signoff_id", "signature_level", "signature_data"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["sign", "signoff", "monthly", "approve", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("signoff_id", FieldClassification.REQUIRED),
            FieldMetadata("signature_level", FieldClassification.REQUIRED),
            FieldMetadata("signature_data", FieldClassification.REQUIRED),
        ],
    ),

    # READ: Schedule Templates
    "list_crew_templates": ActionDefinition(
        action_id="list_crew_templates",
        label="List Schedule Templates",
        endpoint="/v1/hours-of-rest/templates",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="hours_of_rest",
        variant=ActionVariant.READ,
        search_keywords=["template", "schedule", "watch", "list", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
        ],
    ),

    # MUTATE: Schedule Templates
    "create_crew_template": ActionDefinition(
        action_id="create_crew_template",
        label="Create Schedule Template",
        endpoint="/v1/hours-of-rest/templates/create",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "schedule_name", "schedule_template"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["create", "template", "schedule", "watch", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("schedule_name", FieldClassification.REQUIRED),
            FieldMetadata("schedule_template", FieldClassification.REQUIRED),
        ],
    ),

    "apply_crew_template": ActionDefinition(
        action_id="apply_crew_template",
        label="Apply Schedule Template",
        endpoint="/v1/hours-of-rest/templates/apply",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "week_start_date"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["apply", "template", "schedule", "week", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("week_start_date", FieldClassification.REQUIRED),
            FieldMetadata("template_id", FieldClassification.OPTIONAL),
        ],
    ),

    # READ: Warnings
    "list_crew_warnings": ActionDefinition(
        action_id="list_crew_warnings",
        label="List Compliance Warnings",
        endpoint="/v1/hours-of-rest/warnings",
        handler_type=HandlerType.INTERNAL,
        method="GET",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id"],
        domain="hours_of_rest",
        variant=ActionVariant.READ,
        search_keywords=["warning", "compliance", "violation", "list", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
        ],
    ),

    # MUTATE: Warnings
    "acknowledge_warning": ActionDefinition(
        action_id="acknowledge_warning",
        label="Acknowledge Warning",
        endpoint="/v1/hours-of-rest/warnings/acknowledge",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["crew", "deckhand", "steward", "cook", "chef", "bosun", "engineer", "eto", "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
        required_fields=["yacht_id", "warning_id"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["acknowledge", "warning", "accept", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("warning_id", FieldClassification.REQUIRED),
        ],
    ),

    "dismiss_warning": ActionDefinition(
        action_id="dismiss_warning",
        label="Dismiss Warning",
        endpoint="/v1/hours-of-rest/warnings/dismiss",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "eto", "purser", "captain", "manager"],  # HOD+ only
        required_fields=["yacht_id", "warning_id", "hod_justification", "dismissed_by_role"],
        domain="hours_of_rest",
        variant=ActionVariant.MUTATE,
        search_keywords=["dismiss", "warning", "clear", "hor"],
        field_metadata=[
            FieldMetadata("yacht_id", FieldClassification.CONTEXT),
            FieldMetadata("user_id", FieldClassification.CONTEXT),
            FieldMetadata("warning_id", FieldClassification.REQUIRED),
            FieldMetadata("hod_justification", FieldClassification.REQUIRED),
            FieldMetadata("dismissed_by_role", FieldClassification.REQUIRED),
        ],
    ),
}


# ============================================================================
# CULLED ACTIONS (14) - DO NOT RE-ADD WITHOUT DEPLOYING TO PRODUCTION
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
# - suggest_parts                 (handler not deployed)
# - create_work_order_fault       (N8N handler not deployed)
# - update_worklist_progress      (handler not deployed)
#
# RESTORED (Fault Lens v1 2026-01-27):
# - view_fault_history            (handler deployed)
# - add_fault_note                (handler deployed)
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
# STORAGE SEMANTICS FOR FILE-RELATED ACTIONS
# ============================================================================

ACTION_STORAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "link_document_to_certificate": {
        "bucket": "documents",
        "path_template": "{yacht_id}/certificates/{certificate_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
        "confirmation_required": True,
    },
    # Faults - use pms-discrepancy-photos bucket
    "add_fault_photo": {
        "bucket": "pms-discrepancy-photos",
        "path_template": "{yacht_id}/faults/{fault_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/faults/"],
        "confirmation_required": True,
    },
    "create_vessel_certificate": {
        "bucket": "documents",
        "path_template": "{yacht_id}/certificates/{certificate_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
        "confirmation_required": True,
    },
    "create_crew_certificate": {
        "bucket": "documents",
        "path_template": "{yacht_id}/certificates/{certificate_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
        "confirmation_required": True,
    },
    # Work orders
    "add_work_order_photo": {
        "bucket": "pms-work-order-photos",
        "path_template": "{yacht_id}/work_orders/{work_order_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/work_orders/"],
        "confirmation_required": True,
    },
    # Parts - receiving images
    "receive_part": {
        "bucket": "pms-receiving-images",
        "path_template": "{yacht_id}/receiving/{part_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/receiving/"],
        "confirmation_required": False,
    },
    # Parts - label PDFs
    "generate_part_labels": {
        "bucket": "pms-label-pdfs",
        "path_template": "{yacht_id}/parts/{part_id}/labels/{filename}",
        "writable_prefixes": ["{yacht_id}/parts/"],
        "confirmation_required": False,
    },
    # Equipment - documents (Equipment Lens v2)
    "attach_file_to_equipment": {
        "bucket": "documents",
        "path_template": "{yacht_id}/equipment/{equipment_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/equipment/"],
        "max_file_size_mb": 25,
        "confirmation_required": True,
    },
    "link_document_to_equipment": {
        "bucket": "documents",
        "path_template": "{yacht_id}/equipment/{equipment_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/equipment/"],
        "confirmation_required": True,
    },
    # Document Lens v2 - Generic document uploads
    "upload_document": {
        "bucket": "documents",
        "path_template": "{yacht_id}/documents/{document_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/documents/"],
        "max_file_size_mb": 50,
        "confirmation_required": True,
    },
}


def get_storage_options(action_id: str, yacht_id: str = None, entity_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Get storage options for an action.

    Returns None if action has no storage semantics.
    Substitutes yacht_id and entity_id into path templates if provided.
    """
    config = ACTION_STORAGE_CONFIG.get(action_id)
    if not config:
        return None

    # Build preview path
    path_preview = config["path_template"]
    writable = list(config["writable_prefixes"])

    if yacht_id:
        path_preview = path_preview.replace("{yacht_id}", yacht_id)
        writable = [p.replace("{yacht_id}", yacht_id) for p in writable]

    # Replace known entity placeholders for preview
    if entity_id:
        path_preview = path_preview.replace("{certificate_id}", entity_id)
        path_preview = path_preview.replace("{work_order_id}", entity_id)
        path_preview = path_preview.replace("{fault_id}", entity_id)
        path_preview = path_preview.replace("{equipment_id}", entity_id)
        path_preview = path_preview.replace("{part_id}", entity_id)
        path_preview = path_preview.replace("{document_id}", entity_id)
    else:
        path_preview = path_preview.replace("{certificate_id}", "<new_id>")
        path_preview = path_preview.replace("{work_order_id}", "<id>")
        path_preview = path_preview.replace("{fault_id}", "<fault_id>")
        path_preview = path_preview.replace("{equipment_id}", "<equipment_id>")
        path_preview = path_preview.replace("{part_id}", "<part_id>")
        path_preview = path_preview.replace("{document_id}", "<document_id>")

    return {
        "bucket": config["bucket"],
        "path_preview": path_preview,
        "writable_prefixes": writable,
        "confirmation_required": config["confirmation_required"],
    }


# ============================================================================
# ACTION SEARCH
# ============================================================================

# Synonym dictionary - maps natural language terms to canonical keywords
_SYNONYMS = {
    # Comment synonyms
    "note": "comment",
    "notes": "comments",
    "remark": "comment",
    "remarks": "comments",
    "annotation": "comment",
    "say": "comment",
    "said": "comment",
    "wrote": "comment",
    "write": "comment",
    "writing": "comment",
    # Action synonyms
    "remove": "delete",
    "erase": "delete",
    "trash": "delete",
    "edit": "update",
    "change": "update",
    "modify": "update",
    "show": "list",
    "view": "list",
    "see": "list",
    "get": "list",
    "fetch": "list",
    "leave": "add",
    "post": "add",
    "put": "add",
    # Document synonyms
    "doc": "document",
    "docs": "documents",
    "file": "document",
    "files": "documents",
    "manual": "document",
    "manuals": "documents",
}

# Stopwords to filter out
_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "at", "for", "with", "by",
    "is", "it", "this", "that", "or", "and", "but", "if", "my", "i",
    "me", "can", "you", "uhh", "uh", "um", "like", "just", "idk", "wait",
    "no", "what", "did", "do", "was", "were", "be", "been", "being",
    "have", "has", "had", "from", "about", "thing", "things", "whatever",
    "stuff", "something", "someone", "people", "all", "recent", "last",
}


def _normalize_token(token: str) -> str:
    """Normalize a token using synonym dictionary."""
    return _SYNONYMS.get(token, token)


def _fuzzy_match(query: str, target: str, threshold: int = 2) -> bool:
    """
    Simple fuzzy match using Levenshtein distance.
    Returns True if edit distance <= threshold.
    """
    # Quick length check
    if abs(len(query) - len(target)) > threshold:
        return False

    # Simple Levenshtein distance
    m, n = len(query), len(target)
    if m == 0:
        return n <= threshold
    if n == 0:
        return m <= threshold

    # Create distance matrix
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if query[i - 1] == target[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,      # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost  # substitution
            )
        prev, curr = curr, prev

    return prev[n] <= threshold


def _tokenize(text: str) -> List[str]:
    """Tokenize text, apply synonyms, filter stopwords."""
    import re
    tokens = re.findall(r'\w+', text.lower())
    # Apply synonyms and filter stopwords
    result = []
    for t in tokens:
        if t in _STOPWORDS:
            continue
        normalized = _normalize_token(t)
        result.append(normalized)
    return result


def _token_matches(query_token: str, target_set: set, fuzzy: bool = True) -> bool:
    """Check if a query token matches any target (exact or fuzzy)."""
    # Exact match
    if query_token in target_set:
        return True

    # Fuzzy match for longer tokens (to avoid false positives on short words)
    if fuzzy and len(query_token) >= 4:
        for target in target_set:
            if len(target) >= 4 and _fuzzy_match(query_token, target, threshold=2):
                return True

    return False


def _count_matches(query_tokens: List[str], target_set: set, fuzzy: bool = True) -> int:
    """Count how many query tokens match the target set."""
    return sum(1 for qt in query_tokens if _token_matches(qt, target_set, fuzzy))


def _match_score(query_tokens: List[str], action: ActionDefinition) -> float:
    """
    Compute match score for an action against query tokens.

    Scoring:
    - 1.0: Exact match on action_id
    - 0.9: All query tokens in label
    - 0.85: All query tokens in search_keywords
    - 0.75-0.84: High fuzzy match (most tokens match)
    - 0.5-0.74: Partial matches
    - 0.0: No match
    """
    if not query_tokens:
        return 1.0  # Empty query matches all

    action_id_lower = action.action_id.lower()
    label_tokens = _tokenize(action.label)
    keyword_set = set(kw.lower() for kw in action.search_keywords)
    label_set = set(label_tokens)

    # Also include normalized keywords
    normalized_keywords = set()
    for kw in action.search_keywords:
        normalized_keywords.add(kw.lower())
        normalized_keywords.add(_normalize_token(kw.lower()))

    # Check exact action_id match (handles underscores)
    query_str = "_".join(query_tokens)
    query_no_underscore = query_str.replace("_", "")
    action_no_underscore = action_id_lower.replace("_", "")
    if query_str == action_id_lower or query_no_underscore == action_no_underscore:
        return 1.0

    # Check if all query tokens appear in label (exact)
    if all(qt in label_set for qt in query_tokens):
        return 0.9

    # Check if all query tokens appear in keywords (exact)
    if all(qt in normalized_keywords for qt in query_tokens):
        return 0.85

    # Count exact + fuzzy matches
    label_hits = _count_matches(query_tokens, label_set, fuzzy=True)
    keyword_hits = _count_matches(query_tokens, normalized_keywords, fuzzy=True)

    # Use the better of the two
    best_hits = max(label_hits, keyword_hits)

    if best_hits == 0:
        return 0.0

    # Calculate hit ratio
    hit_ratio = best_hits / len(query_tokens)

    # Score based on match quality
    if hit_ratio >= 0.8:
        # High match - most tokens matched
        return 0.75 + (hit_ratio * 0.1)  # 0.75-0.85
    elif hit_ratio >= 0.5:
        # Medium match
        return 0.55 + (hit_ratio * 0.2)  # 0.55-0.75
    else:
        # Low match
        return 0.5 + (hit_ratio * 0.1)  # 0.5-0.55


def search_actions(
    query: str = None,
    role: str = None,
    domain: str = None,
) -> List[Dict[str, Any]]:
    """
    Search actions with role-gating and optional domain filter.

    Args:
        query: Search query (optional, returns all if empty)
        role: User role for filtering (required for gating)
        domain: Domain filter (optional, e.g., "certificates")

    Returns:
        List of action dicts with match_score, sorted by score desc
    """
    results = []
    query_tokens = _tokenize(query) if query else []

    for action_id, action in ACTION_REGISTRY.items():
        # Role gating: skip if user role not in allowed_roles
        if role and role not in action.allowed_roles:
            continue

        # Domain filter: skip if domain specified and action doesn't match
        # (actions with no domain are excluded when a domain filter is provided)
        if domain and action.domain != domain:
            continue

        # Compute match score
        score = _match_score(query_tokens, action)

        # Skip zero-score matches when query is provided
        if query_tokens and score == 0.0:
            continue

        results.append({
            "action_id": action.action_id,
            "label": action.label,
            "variant": action.variant.value if action.variant else "MUTATE",
            "allowed_roles": action.allowed_roles,
            "required_fields": action.required_fields,
            "domain": action.domain,
            "match_score": round(score, 2),
        })

    # Sort by score descending
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


# ============================================================================
# FIELD METADATA HELPERS
# ============================================================================

def get_prefillable_fields(action_id: str) -> List[Dict[str, Any]]:
    """
    Get fields that can be auto-populated for an action.

    Returns list of field metadata for BACKEND_AUTO and CONTEXT fields.
    Used by prefill/prepare endpoints to compute suggested values.
    """
    action = get_action(action_id)
    return [
        {
            "name": fm.name,
            "classification": fm.classification.value,
            "auto_populate_from": fm.auto_populate_from,
            "lookup_required": fm.lookup_required,
            "description": fm.description,
            "options": fm.options,
        }
        for fm in action.field_metadata
        if fm.classification in (FieldClassification.BACKEND_AUTO, FieldClassification.CONTEXT)
    ]


def get_required_user_fields(action_id: str) -> List[str]:
    """
    Get fields that must be provided by the user.

    Returns list of field names with classification=REQUIRED.
    Used by execute to validate payload before processing.
    """
    action = get_action(action_id)
    return [
        fm.name
        for fm in action.field_metadata
        if fm.classification == FieldClassification.REQUIRED
    ]


def get_field_metadata(action_id: str) -> List[Dict[str, Any]]:
    """
    Get all field metadata for an action.

    Returns full field metadata for UI/validation purposes.
    """
    action = get_action(action_id)
    return [
        {
            "name": fm.name,
            "classification": fm.classification.value,
            "auto_populate_from": fm.auto_populate_from,
            "lookup_required": fm.lookup_required,
            "description": fm.description,
            "options": fm.options,
        }
        for fm in action.field_metadata
    ]


def get_actions_for_domain(domain: str, role: str = None) -> List[Dict[str, Any]]:
    """
    Get all actions for a domain, optionally filtered by role.

    Used by suggestions endpoint to return context-valid actions.
    """
    results = []
    for action_id, action in ACTION_REGISTRY.items():
        if action.domain != domain:
            continue
        if role and role not in action.allowed_roles:
            continue

        results.append({
            "action_id": action.action_id,
            "label": action.label,
            "variant": action.variant.value if action.variant else "MUTATE",
            "allowed_roles": action.allowed_roles,
            "required_fields": action.required_fields,
            "has_prefill": action.prefill_endpoint is not None,
            "prefill_endpoint": action.prefill_endpoint,
            "context_required": action.context_required,
        })

    return results


# ============================================================================
# CONTEXT GATING
# ============================================================================

def check_context_gating(
    action_id: str,
    entity_type: str = None,
    entity_id: str = None,
) -> Dict[str, Any]:
    """
    Check if an action is allowed given the current context.

    Args:
        action_id: Action to check
        entity_type: Current focused entity type (e.g., "fault", "work_order")
        entity_id: Current focused entity ID

    Returns:
        {
            "allowed": bool,
            "reason": str or None,  # Explanation if not allowed
        }

    Example:
        create_work_order_from_fault requires entity_type="fault" and entity_id
        - Allowed: check_context_gating("create_work_order_from_fault", "fault", "abc123")
        - Denied: check_context_gating("create_work_order_from_fault", None, None)
    """
    action = get_action(action_id)

    if not action.context_required:
        return {"allowed": True, "reason": None}

    required = action.context_required

    # Check entity_type requirement
    if "entity_type" in required:
        required_type = required["entity_type"]
        if entity_type != required_type:
            return {
                "allowed": False,
                "reason": f"Action requires focus on {required_type} entity",
            }

    # Check entity_id requirement
    if required.get("entity_id") is True:
        if not entity_id:
            return {
                "allowed": False,
                "reason": "Action requires a specific entity ID (focused context)",
            }

    return {"allowed": True, "reason": None}


def get_context_gated_actions() -> List[Dict[str, Any]]:
    """
    Get all actions that have context gating requirements.

    Returns list of actions with their context_required specs.
    Used for documentation and suggestions filtering.
    """
    results = []
    for action_id, action in ACTION_REGISTRY.items():
        if action.context_required:
            results.append({
                "action_id": action.action_id,
                "label": action.label,
                "domain": action.domain,
                "context_required": action.context_required,
            })
    return results


def validate_signature_role(action_id: str, role_at_signing: str) -> Dict[str, Any]:
    """
    Validate that the signing user's role is allowed for a SIGNED action.

    Args:
        action_id: The action being signed
        role_at_signing: The role of the user at time of signing

    Returns:
        {
            "valid": bool,
            "reason": str or None,  # Explanation if not valid
            "required_roles": List[str] or None,  # Roles that can sign
        }

    Example:
        create_work_order_from_fault requires captain or manager signature.
        - Valid: validate_signature_role("create_work_order_from_fault", "captain")
        - Invalid: validate_signature_role("create_work_order_from_fault", "chief_engineer")
    """
    action = get_action(action_id)

    # Non-signed actions don't require signature validation
    if action.variant != ActionVariant.SIGNED:
        return {"valid": True, "reason": None, "required_roles": None}

    # If no signature_roles_required, any allowed_role can sign
    if not action.signature_roles_required:
        if role_at_signing in action.allowed_roles:
            return {"valid": True, "reason": None, "required_roles": action.allowed_roles}
        return {
            "valid": False,
            "reason": f"Role '{role_at_signing}' not allowed for action",
            "required_roles": action.allowed_roles,
        }

    # Check against specific signature roles
    if role_at_signing in action.signature_roles_required:
        return {"valid": True, "reason": None, "required_roles": action.signature_roles_required}

    return {
        "valid": False,
        "reason": f"Signature requires role: {', '.join(action.signature_roles_required)}",
        "required_roles": action.signature_roles_required,
    }


def get_signature_requirements(action_id: str) -> Optional[Dict[str, Any]]:
    """
    Get signature requirements for an action.

    Returns None if action is not SIGNED.
    Returns signature requirements dict for SIGNED actions.
    """
    action = get_action(action_id)

    if action.variant != ActionVariant.SIGNED:
        return None

    return {
        "action_id": action.action_id,
        "variant": "SIGNED",
        "signature_roles_required": action.signature_roles_required or action.allowed_roles,
        "required_signature_fields": ["signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"],
    }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ACTION_REGISTRY",
    "ActionDefinition",
    "ActionVariant",
    "HandlerType",
    "FieldClassification",
    "FieldMetadata",
    "get_action",
    "list_actions",
    "get_actions_for_role",
    "get_actions_for_domain",
    "validate_action_exists",
    "search_actions",
    "get_storage_options",
    "get_prefillable_fields",
    "get_required_user_fields",
    "get_field_metadata",
    "check_context_gating",
    "get_context_gated_actions",
    "validate_signature_role",
    "get_signature_requirements",
    "ACTION_STORAGE_CONFIG",
]
