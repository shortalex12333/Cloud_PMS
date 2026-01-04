#!/usr/bin/env python3
"""
Stress Test Configuration: Constants and Registry
==================================================

Contains the 67-action registry, entity types, and test matrix configurations.
"""

# =============================================================================
# 67 MICRO-ACTION REGISTRY (Source of Truth)
# =============================================================================

ACTION_REGISTRY = {
    # FAULT & DIAGNOSIS (9)
    "diagnose_fault": {"category": "fix_something", "side_effect": "read_only"},
    "report_fault": {"category": "fix_something", "side_effect": "mutation_heavy"},
    "show_manual_section": {"category": "fix_something", "side_effect": "read_only"},
    "view_fault_history": {"category": "fix_something", "side_effect": "read_only"},
    "suggest_parts": {"category": "fix_something", "side_effect": "read_only"},
    "create_work_order_from_fault": {"category": "fix_something", "side_effect": "mutation_heavy"},
    "add_fault_note": {"category": "fix_something", "side_effect": "mutation_light"},
    "add_fault_photo": {"category": "fix_something", "side_effect": "mutation_light"},
    "link_equipment_to_fault": {"category": "fix_something", "side_effect": "mutation_light"},

    # WORK ORDER (11)
    "create_work_order": {"category": "do_maintenance", "side_effect": "mutation_heavy"},
    "view_work_order_history": {"category": "do_maintenance", "side_effect": "read_only"},
    "mark_work_order_complete": {"category": "do_maintenance", "side_effect": "mutation_heavy"},
    "complete_work_order": {"category": "do_maintenance", "side_effect": "mutation_heavy"},
    "add_work_order_note": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "add_work_order_photo": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "add_parts_to_work_order": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "link_parts_to_work_order": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "view_work_order_checklist": {"category": "do_maintenance", "side_effect": "read_only"},
    "assign_work_order": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "edit_work_order_details": {"category": "do_maintenance", "side_effect": "mutation_heavy"},

    # EQUIPMENT (6)
    "view_equipment_details": {"category": "manage_equipment", "side_effect": "read_only"},
    "view_equipment_history": {"category": "manage_equipment", "side_effect": "read_only"},
    "view_equipment_parts": {"category": "manage_equipment", "side_effect": "read_only"},
    "view_linked_faults": {"category": "manage_equipment", "side_effect": "read_only"},
    "view_equipment_manual": {"category": "manage_equipment", "side_effect": "read_only"},
    "add_equipment_note": {"category": "manage_equipment", "side_effect": "mutation_light"},

    # INVENTORY/PARTS (9)
    "view_part_stock": {"category": "control_inventory", "side_effect": "read_only"},
    "add_part": {"category": "control_inventory", "side_effect": "mutation_heavy"},
    "order_part": {"category": "control_inventory", "side_effect": "mutation_heavy"},
    "view_part_location": {"category": "control_inventory", "side_effect": "read_only"},
    "view_part_usage": {"category": "control_inventory", "side_effect": "read_only"},
    "log_part_usage": {"category": "control_inventory", "side_effect": "mutation_light"},
    "edit_part_quantity": {"category": "control_inventory", "side_effect": "mutation_heavy"},
    "scan_part_barcode": {"category": "control_inventory", "side_effect": "read_only"},
    "view_linked_equipment": {"category": "control_inventory", "side_effect": "read_only"},

    # HANDOVER (6)
    "add_to_handover": {"category": "communicate_status", "side_effect": "mutation_light"},
    "add_document_to_handover": {"category": "communicate_status", "side_effect": "mutation_light"},
    "add_predictive_insight_to_handover": {"category": "communicate_status", "side_effect": "mutation_light"},
    "edit_handover_section": {"category": "communicate_status", "side_effect": "mutation_light"},
    "export_handover": {"category": "communicate_status", "side_effect": "read_only"},
    "regenerate_handover_summary": {"category": "communicate_status", "side_effect": "mutation_light"},

    # DOCUMENT (3)
    "view_document": {"category": "fix_something", "side_effect": "read_only"},
    "view_related_documents": {"category": "fix_something", "side_effect": "read_only"},
    "view_document_section": {"category": "fix_something", "side_effect": "read_only"},

    # HOURS OF REST (4)
    "view_hours_of_rest": {"category": "comply_audit", "side_effect": "read_only"},
    "update_hours_of_rest": {"category": "comply_audit", "side_effect": "mutation_heavy"},
    "export_hours_of_rest": {"category": "comply_audit", "side_effect": "read_only"},
    "view_compliance_status": {"category": "comply_audit", "side_effect": "read_only"},

    # PURCHASING (7)
    "create_purchase_request": {"category": "procure_suppliers", "side_effect": "mutation_heavy"},
    "add_item_to_purchase": {"category": "procure_suppliers", "side_effect": "mutation_light"},
    "approve_purchase": {"category": "procure_suppliers", "side_effect": "mutation_heavy"},
    "upload_invoice": {"category": "procure_suppliers", "side_effect": "mutation_light"},
    "track_delivery": {"category": "procure_suppliers", "side_effect": "read_only"},
    "log_delivery_received": {"category": "procure_suppliers", "side_effect": "mutation_heavy"},
    "update_purchase_status": {"category": "procure_suppliers", "side_effect": "mutation_light"},

    # CHECKLISTS (4)
    "view_checklist": {"category": "do_maintenance", "side_effect": "read_only"},
    "mark_checklist_item_complete": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "add_checklist_note": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "add_checklist_photo": {"category": "do_maintenance", "side_effect": "mutation_light"},

    # SHIPYARD/REFIT (5)
    "view_worklist": {"category": "do_maintenance", "side_effect": "read_only"},
    "add_worklist_task": {"category": "do_maintenance", "side_effect": "mutation_heavy"},
    "update_worklist_progress": {"category": "do_maintenance", "side_effect": "mutation_light"},
    "export_worklist": {"category": "do_maintenance", "side_effect": "read_only"},
    "tag_for_survey": {"category": "comply_audit", "side_effect": "mutation_light"},

    # FLEET (3)
    "view_fleet_summary": {"category": "manage_equipment", "side_effect": "read_only"},
    "open_vessel": {"category": "manage_equipment", "side_effect": "read_only"},
    "export_fleet_summary": {"category": "communicate_status", "side_effect": "read_only"},

    # PREDICTIVE (2)
    "request_predictive_insight": {"category": "manage_equipment", "side_effect": "read_only"},
    "view_smart_summary": {"category": "communicate_status", "side_effect": "read_only"},

    # MOBILE (2)
    "upload_photo": {"category": "communicate_status", "side_effect": "mutation_light"},
    "record_voice_note": {"category": "communicate_status", "side_effect": "mutation_light"},

    # EDIT ACTIONS (6+)
    "edit_equipment_details": {"category": "manage_equipment", "side_effect": "mutation_heavy"},
    "edit_part_details": {"category": "control_inventory", "side_effect": "mutation_light"},
    "edit_purchase_details": {"category": "procure_suppliers", "side_effect": "mutation_heavy"},
    "edit_invoice_amount": {"category": "procure_suppliers", "side_effect": "mutation_heavy"},
    "edit_fault_details": {"category": "fix_something", "side_effect": "mutation_light"},
    "edit_note": {"category": "communicate_status", "side_effect": "mutation_light"},
    "delete_item": {"category": "communicate_status", "side_effect": "mutation_heavy"},
    "approve_work_order": {"category": "do_maintenance", "side_effect": "mutation_heavy"},
    "scan_equipment_barcode": {"category": "manage_equipment", "side_effect": "read_only"},
}

# Total should be 67+ (registry may grow)
# assert len(ACTION_REGISTRY) >= 67, f"Registry has {len(ACTION_REGISTRY)} actions, expected at least 67"

# =============================================================================
# ENTITY TYPES
# =============================================================================

ENTITY_TYPES = [
    "equipment", "part", "location", "fault_code", "symptom",
    "measurement", "temporal", "document", "brand", "model",
    "person", "work_order", "certificate", "supplier"
]

# =============================================================================
# LANE DEFINITIONS
# =============================================================================

LANES = ["BLOCKED", "NO_LLM", "RULES_ONLY", "GPT"]

LANE_CAPABILITIES = {
    "BLOCKED": {
        "allow_vector_search": False,
        "allow_embedding": False,
        "deterministic_required": True,
    },
    "NO_LLM": {
        "allow_vector_search": False,
        "allow_embedding": False,
        "deterministic_required": True,
    },
    "RULES_ONLY": {
        "allow_vector_search": False,
        "allow_embedding": False,
        "deterministic_required": True,
    },
    "GPT": {
        "allow_vector_search": True,
        "allow_embedding": True,
        "deterministic_required": False,
    },
}

# =============================================================================
# TEST PARAMETERS
# =============================================================================

# Quantitative minimums
MIN_TOTAL_CALLS = 1000
MIN_PER_LANE = {
    "BLOCKED": 50,
    "NO_LLM": 300,
    "RULES_ONLY": 300,
    "GPT": 300,
}
MIN_CONCURRENCY_CALLS = 100
MAX_UNEXPLAINED_FAILURE_RATE = 0.01  # 1%

# Test yacht IDs (synthetic)
TEST_YACHT_IDS = [
    "85fe1119-b04c-41ac-80f1-829d23322598",
    "12345678-1234-1234-1234-123456789abc",
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
]

# Endpoint URLs
ENDPOINTS = {
    "extract": "/extract",
    "search_v1": "/v1/search",
    "search_v2": "/v2/search",
    "health": "/health",
}

# Base URL (will be overridden by environment)
DEFAULT_BASE_URL = "https://extract.core.celeste7.ai"
LOCAL_BASE_URL = "http://localhost:8000"
