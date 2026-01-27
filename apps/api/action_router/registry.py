"""
CelesteOS Action Router - Action Registry

Defines all available actions, their endpoints, schemas, and permissions.

This is the SINGLE SOURCE OF TRUTH for all micro-actions.

PHASE 8 CULL (2026-01-21): Removed 16 ghost actions not deployed to production.
Remaining: 30 actions that exist in production.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class HandlerType(str, Enum):
    """Type of handler for an action."""
    INTERNAL = "internal"
    N8N = "n8n"


class ActionVariant(str, Enum):
    """Variant of action (mutation level)."""
    READ = "READ"      # Read-only (view, list)
    MUTATE = "MUTATE"  # Standard mutation (create, update)
    SIGNED = "SIGNED"  # Requires signature (supersede, delete)


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
        domain: str = None,
        variant: ActionVariant = ActionVariant.MUTATE,
        search_keywords: List[str] = None,
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
    # WORK ORDER ACTIONS (curated, executable)
    # ========================================================================

    "close_work_order": ActionDefinition(
        action_id="close_work_order",
        label="Close Work Order",
        endpoint="/v1/work-orders/close",
        handler_type=HandlerType.INTERNAL,
        method="POST",
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["crew", "chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
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
        allowed_roles=["captain", "manager"],
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
        allowed_roles=["crew", "chief_engineer", "captain", "manager"],
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
        allowed_roles=["chief_engineer", "captain", "manager"],
        required_fields=["yacht_id", "fault_id", "signature"],
        domain="work_orders",
        variant=ActionVariant.SIGNED,
        search_keywords=["create", "add", "new", "work", "order", "wo", "from", "fault"],
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
# STORAGE SEMANTICS FOR FILE-RELATED ACTIONS
# ============================================================================

ACTION_STORAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "link_document_to_certificate": {
        "bucket": "documents",
        "path_template": "{yacht_id}/certificates/{certificate_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/certificates/"],
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
        "bucket": "documents",
        "path_template": "{yacht_id}/work_orders/{work_order_id}/{filename}",
        "writable_prefixes": ["{yacht_id}/work_orders/"],
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
    else:
        path_preview = path_preview.replace("{certificate_id}", "<new_id>")
        path_preview = path_preview.replace("{work_order_id}", "<id>")

    return {
        "bucket": config["bucket"],
        "path_preview": path_preview,
        "writable_prefixes": writable,
        "confirmation_required": config["confirmation_required"],
    }


# ============================================================================
# ACTION SEARCH
# ============================================================================

def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    import re
    return re.findall(r'\w+', text.lower())


def _match_score(query_tokens: List[str], action: ActionDefinition) -> float:
    """
    Compute match score for an action against query tokens.

    Scoring:
    - 1.0: Exact match on action_id
    - 0.9: All query tokens in label
    - 0.8: All query tokens in search_keywords
    - 0.5-0.7: Partial matches
    - 0.0: No match
    """
    if not query_tokens:
        return 1.0  # Empty query matches all

    action_id_lower = action.action_id.lower()
    label_tokens = _tokenize(action.label)
    keyword_set = set(kw.lower() for kw in action.search_keywords)

    # Check exact action_id match
    query_str = "_".join(query_tokens)
    if query_str == action_id_lower or query_str.replace("_", "") == action_id_lower.replace("_", ""):
        return 1.0

    # Check if all query tokens appear in label
    label_set = set(label_tokens)
    if all(qt in label_set for qt in query_tokens):
        return 0.9

    # Check if all query tokens appear in keywords
    if all(qt in keyword_set for qt in query_tokens):
        return 0.85

    # Partial matches
    label_hits = sum(1 for qt in query_tokens if qt in label_set)
    keyword_hits = sum(1 for qt in query_tokens if qt in keyword_set)
    combined_hits = max(label_hits, keyword_hits)

    if combined_hits == 0:
        return 0.0

    # Scale from 0.5 to 0.7 based on hit ratio
    hit_ratio = combined_hits / len(query_tokens)
    return 0.5 + (hit_ratio * 0.2)


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
# EXPORTS
# ============================================================================

__all__ = [
    "ACTION_REGISTRY",
    "ActionDefinition",
    "ActionVariant",
    "HandlerType",
    "get_action",
    "list_actions",
    "get_actions_for_role",
    "validate_action_exists",
    "search_actions",
    "get_storage_options",
    "ACTION_STORAGE_CONFIG",
]
