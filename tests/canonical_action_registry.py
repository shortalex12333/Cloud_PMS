#!/usr/bin/env python3
"""
Canonical Action Registry
=========================
Single source of truth for all valid micro-actions.
Any output not in this registry is INVALID.

Rules:
1. All actions must be in CANONICAL_ACTIONS
2. Aliases resolve to canonical form
3. Unknown actions → none_search_only + log warning
"""

# =============================================================================
# CANONICAL ACTIONS (77 total + none_search_only)
# =============================================================================

CANONICAL_ACTIONS = frozenset([
    # Fault Diagnosis (1-10)
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

    # Graph/Entity Navigation (11-15)
    "trace_related_equipment",
    "view_linked_entities",
    "show_document_graph",
    "expand_fault_tree",
    "show_entity_timeline",

    # Work Orders (16-25)
    "create_work_order",
    "list_work_orders",
    "update_work_order",
    "close_work_order",
    "add_note_to_work_order",
    "attach_photo_to_work_order",
    "assign_work_order",
    "set_priority_on_work_order",
    "schedule_work_order",
    "show_work_order_history",

    # Handover (26-30)
    "add_to_handover",
    "view_handover",
    "export_handover",
    "edit_handover_section",
    "attach_document_to_handover",

    # Inventory (31-40)
    "check_stock_level",
    "order_part",
    "add_part_to_work_order",
    "show_storage_location",
    "scan_barcode",
    "update_stock_level",
    "show_part_compatibility",
    "create_purchase_request",
    "show_low_stock_alerts",
    "reserve_part",

    # Compliance/HOR (41-48)
    "log_hours_of_rest",
    "show_hours_of_rest",
    "show_certificates",
    "show_certificate_expiry",
    "export_compliance_logs",
    "generate_audit_pack",
    "submit_compliance_report",
    "upload_certificate_document",

    # Documents (49-56)
    "upload_document",
    "search_documents",
    "open_document",
    "attach_document_to_work_order",
    "show_document_metadata",
    "download_document",
    "share_document",
    "archive_document",

    # Purchasing (57-62)
    "approve_purchase_order",
    "track_delivery",
    "link_supplier",
    "upload_invoice",
    "compare_supplier_prices",
    "create_purchase_order",

    # Tasks/Checklists (63-68)
    "create_task",
    "show_tasks_due",
    "mark_work_order_complete",
    "show_checklist",
    "add_checklist_item",
    "assign_task",

    # Reporting (69-74)
    "export_summary",
    "generate_summary",
    "show_analytics",
    "export_work_order_history",
    "show_equipment_utilization",
    "show_fault_trends",

    # Fleet/Shipyard (75-79)
    "compare_fleet_equipment",
    "show_fleet_alerts",
    "log_contractor_work",
    "schedule_shipyard_task",
    "share_with_shipyard",

    # Utility (80-82)
    "set_reminder",
    "add_note",
    "open_equipment_card",

    # Equipment Cards (83-85)
    "link_document_to_equipment",
    "update_certificate_metadata",
    "detect_anomaly",

    # Special (always valid)
    "none_search_only",
])

# =============================================================================
# ALIAS MAP: Non-canonical → Canonical
# =============================================================================

ACTION_ALIASES = {
    # Stock/Inventory aliases
    "check_stock": "check_stock_level",
    "check_inventory": "check_stock_level",
    "view_stock": "check_stock_level",
    "order_parts": "order_part",
    "purchase_part": "order_part",
    "request_part": "order_part",

    # Certificate aliases
    "show_certificate": "show_certificates",
    "view_certificate": "show_certificates",
    "view_certificates": "show_certificates",

    # Hours of rest aliases
    "view_hours_of_rest": "show_hours_of_rest",
    "display_hours_of_rest": "show_hours_of_rest",

    # Work order aliases
    "mark_task_done": "mark_work_order_complete",
    "complete_work_order": "mark_work_order_complete",
    "finish_work_order": "mark_work_order_complete",
    "create_wo": "create_work_order",
    "new_work_order": "create_work_order",
    "create_work_order_from_fault": "create_work_order",

    # Equipment aliases
    "view_equipment_details": "show_equipment_overview",
    "show_equipment_details": "show_equipment_overview",
    "view_equipment_overview": "show_equipment_overview",
    "view_equipment_history": "show_equipment_history",
    "display_equipment_history": "show_equipment_history",
    "view_equipment_status": "show_recent_state",
    "show_equipment_status": "show_recent_state",

    # Document aliases
    "search_related_documents": "show_related_documents",
    "find_documents": "search_documents",
    "find_manual": "show_manual_section",
    "view_manual": "show_manual_section",
    "open_manual": "show_manual_section",
    "show_troubleshooting_guide": "show_manual_section",
    "attach_document": "attach_document_to_work_order",

    # Predictive aliases
    "view_predictive_insight": "show_predictive_insight",
    "show_prediction": "show_predictive_insight",

    # Graph/navigation aliases
    "view_document_graph": "show_document_graph",
    "show_linked_entities": "view_linked_entities",
    "show_all_linked_faults": "view_linked_entities",
    "view_linked_faults": "view_linked_entities",

    # History aliases
    "view_history": "show_equipment_history",
    "show_history": "show_equipment_history",
    "view_past_events": "show_similar_past_events",
    "show_past_events": "show_similar_past_events",

    # Handover aliases
    "show_handover": "view_handover",
    "display_handover": "view_handover",

    # Export aliases
    "export_logs": "export_compliance_logs",
    "generate_report": "generate_summary",
    "create_summary": "generate_summary",

    # General search fallback
    "general_search": "none_search_only",
    "search": "none_search_only",
}

# =============================================================================
# CANONICALIZATION FUNCTIONS
# =============================================================================

def canonicalize_action(action: str) -> str:
    """
    Resolve an action to its canonical form.

    Returns:
        Canonical action name, or none_search_only if unknown.
    """
    if not action:
        return "none_search_only"

    action = action.lower().strip()

    # Already canonical
    if action in CANONICAL_ACTIONS:
        return action

    # Check alias map
    if action in ACTION_ALIASES:
        return ACTION_ALIASES[action]

    # Unknown action - log and return safe fallback
    # In production, this should log a warning
    return "none_search_only"


def validate_action(action: str) -> tuple[bool, str]:
    """
    Validate an action and return (is_valid, canonical_form).

    Returns:
        (True, canonical_action) if valid
        (False, none_search_only) if invalid
    """
    canonical = canonicalize_action(action)
    is_valid = canonical != "none_search_only" or action == "none_search_only"
    return (is_valid, canonical)


def is_canonical(action: str) -> bool:
    """Check if an action is already in canonical form."""
    return action in CANONICAL_ACTIONS


# =============================================================================
# VERB → ACTION MAPPING (for strict routing)
# =============================================================================

# Primary verbs that MUST appear at position 0 to trigger
STRICT_TRIGGER_VERBS = {
    # Diagnosis
    "diagnose": "diagnose_fault",
    "troubleshoot": "diagnose_fault",
    "investigate": "diagnose_fault",
    "detect": "detect_anomaly",

    # Show/View (context-dependent)
    "show": None,  # Requires context resolution
    "view": None,
    "display": None,
    "list": "list_work_orders",

    # Create
    "create": None,  # Requires context resolution
    "open": "open_equipment_card",
    "raise": "create_work_order",
    "generate": "generate_summary",
    "summarise": "generate_summary",
    "summarize": "generate_summary",

    # Modify
    "update": None,
    "edit": "edit_handover_section",
    "modify": "update_work_order",

    # Complete
    "close": "close_work_order",
    "complete": "mark_work_order_complete",
    "finish": "mark_work_order_complete",
    "mark": "mark_work_order_complete",

    # Inventory
    "check": None,  # Context-dependent: requires stock/inventory keywords
    "order": "order_part",
    "scan": "scan_barcode",
    "reserve": "reserve_part",

    # Log/Record
    "log": "log_hours_of_rest",
    "record": "log_hours_of_rest",
    "enter": "log_hours_of_rest",

    # Export
    "export": "export_summary",
    "download": "download_document",

    # Attach/Upload
    "attach": "attach_document_to_work_order",
    "upload": "upload_document",
    "archive": "archive_document",

    # Trace
    "trace": "trace_related_faults",
    "expand": "expand_fault_tree",

    # Suggest
    "suggest": "suggest_likely_parts",
    "predict": "show_predictive_insight",

    # Assign/Schedule
    "assign": "assign_work_order",
    "schedule": "schedule_work_order",
    "set": "set_priority_on_work_order",

    # Add
    "add": "add_to_handover",
    "include": "add_to_handover",

    # Compare
    "compare": "compare_fleet_equipment",

    # Share
    "share": "share_document",

    # Submit/Approve
    "submit": "submit_compliance_report",
    "approve": "approve_purchase_order",

    # Track/Link
    "track": "track_delivery",
    "link": "link_document_to_equipment",

    # Search/Find
    "search": "search_documents",
    "find": "search_documents",
    "lookup": "show_manual_section",
}

# Context patterns to resolve ambiguous verbs
VERB_CONTEXT_PATTERNS = {
    "show": [
        (r"manual|troubleshoot", "show_manual_section"),
        (r"history", "show_equipment_history"),
        (r"related.*doc", "show_related_documents"),
        (r"equipment.*overview|overview.*equipment", "show_equipment_overview"),
        (r"predictive|predict", "show_predictive_insight"),
        (r"recent|state|status", "show_recent_state"),
        (r"similar|past.*event", "show_similar_past_events"),
        (r"linked|entities", "view_linked_entities"),
        (r"graph", "show_document_graph"),
        (r"work.*order", "list_work_orders"),
        (r"handover", "view_handover"),
        (r"stock|inventory", "check_stock_level"),
        (r"hours.*rest|hor", "show_hours_of_rest"),
        (r"certificat", "show_certificates"),
        (r"expir", "show_certificate_expiry"),
        (r"task", "show_tasks_due"),
        (r"checklist", "show_checklist"),
        (r"storage|location", "show_storage_location"),
        (r"part.*compatib", "show_part_compatibility"),
        (r"document|doc", "search_documents"),
        (r"low.*stock|alert", "show_low_stock_alerts"),
        (r"timeline", "show_entity_timeline"),
        (r"fleet.*alert", "show_fleet_alerts"),
        (r"analytic", "show_analytics"),
        (r"utiliz", "show_equipment_utilization"),
        (r"fault.*trend", "show_fault_trends"),
    ],
    "view": [
        (r"handover", "view_handover"),
        (r"linked|entities", "view_linked_entities"),
        (r"history", "show_equipment_history"),
        (r"hours.*rest|hor", "show_hours_of_rest"),
        (r"equipment", "show_equipment_overview"),
    ],
    "create": [
        (r"work.*order|wo", "create_work_order"),
        (r"task", "create_task"),
        (r"purchase.*order|po", "create_purchase_order"),
        (r"purchase.*request|pr", "create_purchase_request"),
    ],
    "update": [
        (r"work.*order", "update_work_order"),
        (r"stock|inventory", "update_stock_level"),
        (r"certificat", "update_certificate_metadata"),
    ],
    "add": [
        (r"handover", "add_to_handover"),
        (r"note.*work.*order|work.*order.*note", "add_note_to_work_order"),
        (r"note", "add_note"),
        (r"part.*work.*order", "add_part_to_work_order"),
        (r"checklist", "add_checklist_item"),
    ],
    "attach": [
        (r"photo", "attach_photo_to_work_order"),
        (r"document.*handover|handover.*document", "attach_document_to_handover"),
        (r"document|doc", "attach_document_to_work_order"),
    ],
    "export": [
        (r"handover", "export_handover"),
        (r"summary", "export_summary"),
        (r"compliance|log", "export_compliance_logs"),
        (r"work.*order.*history", "export_work_order_history"),
    ],
    "log": [
        (r"hours.*rest|hor", "log_hours_of_rest"),
        (r"contractor", "log_contractor_work"),
    ],
    "schedule": [
        (r"work.*order", "schedule_work_order"),
        (r"shipyard", "schedule_shipyard_task"),
    ],
    "assign": [
        (r"work.*order", "assign_work_order"),
        (r"task", "assign_task"),
    ],
    "trace": [
        (r"equipment", "trace_related_equipment"),
        (r"fault", "trace_related_faults"),
    ],
    "compare": [
        (r"fleet", "compare_fleet_equipment"),
        (r"supplier|price", "compare_supplier_prices"),
    ],
    "share": [
        (r"shipyard", "share_with_shipyard"),
    ],
    "link": [
        (r"document.*equipment|equipment.*document", "link_document_to_equipment"),
        (r"supplier", "link_supplier"),
    ],
    "check": [
        # Only trigger check_stock_level with explicit inventory context
        (r"stock|inventory|spare|spares|parts?\s+level|on\s+hand|in\s+stock", "check_stock_level"),
        # Certificate checks
        (r"certificat|expir", "show_certificates"),
        # Hours checks
        (r"hours.*rest|hor\b", "show_hours_of_rest"),
        # If no inventory context, don't trigger an action (fallback to none_search_only)
    ],
    "upload": [
        (r"certificat", "upload_certificate_document"),
        (r"invoice", "upload_invoice"),
    ],
    "generate": [
        (r"summary|report", "generate_summary"),
        (r"audit", "generate_audit_pack"),
    ],
    "set": [
        (r"priority", "set_priority_on_work_order"),
        (r"reminder", "set_reminder"),
    ],
}


def resolve_verb_action(verb: str, query: str) -> str:
    """
    Resolve a verb to an action based on query context.

    Args:
        verb: The trigger verb (lowercase)
        query: Full query string

    Returns:
        Canonical action name
    """
    import re

    query_lower = query.lower()

    # Check if verb has a direct mapping
    if verb in STRICT_TRIGGER_VERBS:
        direct_action = STRICT_TRIGGER_VERBS[verb]
        if direct_action is not None:
            return direct_action

    # Check context patterns for ambiguous verbs
    if verb in VERB_CONTEXT_PATTERNS:
        for pattern, action in VERB_CONTEXT_PATTERNS[verb]:
            if re.search(pattern, query_lower):
                return action

    # Default fallbacks by verb
    # NOTE: "check" without context → none_search_only (prevents FP on "check generator compartment")
    defaults = {
        "show": "show_equipment_overview",
        "view": "show_equipment_overview",
        "display": "show_equipment_overview",
        "create": "create_work_order",
        "update": "update_work_order",
        "add": "add_note",
        "attach": "attach_document_to_work_order",
        "export": "export_summary",
        "check": "none_search_only",  # Requires explicit inventory/stock context
    }

    return defaults.get(verb, "none_search_only")


# =============================================================================
# POLITE PREFIX DETECTION
# =============================================================================

POLITE_PREFIXES = [
    r"^can\s+you\b",
    r"^could\s+you\b",
    r"^would\s+you\b",
    r"^will\s+you\b",
    r"^please\b",
    r"^i\s+need\s+to\b",
    r"^i\s+need\b",
    r"^i\s+want\s+to\b",
    r"^i\s+want\b",
    r"^i'd\s+like\s+to\b",
    r"^i'd\s+like\b",
    r"^we\s+need\s+to\b",
    r"^we\s+need\b",
    r"^we\s+should\b",
    r"^help\s+me\b",
    r"^is\s+it\s+possible\b",
    r"^want\s+to\b",
    r"^need\s+to\b",
    r"^trying\s+to\b",
    r"^looking\s+to\b",
]

def has_polite_prefix(query: str) -> bool:
    """Check if query starts with a polite prefix (negative control)."""
    import re
    query_lower = query.lower().strip()
    for pattern in POLITE_PREFIXES:
        if re.match(pattern, query_lower):
            return True
    return False


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test canonicalization
    test_cases = [
        ("check_stock", "check_stock_level"),
        ("view_hours_of_rest", "show_hours_of_rest"),
        ("mark_task_done", "mark_work_order_complete"),
        ("diagnose_fault", "diagnose_fault"),  # Already canonical
        ("unknown_action", "none_search_only"),  # Invalid
        ("general_search", "none_search_only"),  # Alias to none
    ]

    print("=== CANONICALIZATION TESTS ===")
    for input_action, expected in test_cases:
        result = canonicalize_action(input_action)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_action} -> {result} (expected: {expected})")

    print(f"\n=== REGISTRY STATS ===")
    print(f"  Canonical actions: {len(CANONICAL_ACTIONS)}")
    print(f"  Aliases defined:   {len(ACTION_ALIASES)}")
    print(f"  Trigger verbs:     {len(STRICT_TRIGGER_VERBS)}")
