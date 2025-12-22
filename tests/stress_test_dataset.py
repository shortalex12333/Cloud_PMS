"""
CelesteOS Micro-Action Stress Test Dataset
===========================================

600+ diverse queries covering:
- All canonical micro-actions
- Strict verb-first commands (should_trigger_action=true)
- Noun-first/conversational (should_trigger_action=false)
- Hard mode: mixed intent, abbreviations, fault codes, measurements
- Real crew language, messy input, edge cases
"""

import json
import random
from typing import List, Dict

# ============================================================================
# CANONICAL MICRO-ACTIONS (from CelesteOS spec)
# ============================================================================

CANONICAL_ACTIONS = {
    # Fault/Diagnostic
    'diagnose_fault', 'show_manual_section', 'show_related_documents', 'show_equipment_overview',
    'show_equipment_history', 'show_recent_state', 'show_predictive_insight', 'suggest_likely_parts',
    'show_similar_past_events', 'trace_related_faults', 'trace_related_equipment', 'view_linked_entities',
    'show_document_graph',

    # Work Orders / Maintenance
    'create_work_order', 'create_work_order_from_fault', 'add_note_to_work_order',
    'attach_photo_to_work_order', 'attach_document_to_work_order', 'add_part_to_work_order',
    'mark_work_order_complete', 'show_tasks_due', 'show_tasks_overdue',

    # Equipment
    'open_equipment_card', 'show_all_linked_parts', 'show_all_linked_faults',
    'show_all_linked_documents', 'show_all_linked_work_orders', 'link_document_to_equipment',

    # Inventory/Parts
    'check_stock_level', 'show_storage_location', 'order_part', 'add_part_to_handover',
    'log_part_usage', 'scan_barcode',

    # Handover/Comms
    'add_to_handover', 'add_note', 'add_predictive_insight_to_handover', 'add_document_to_handover',
    'edit_handover_section', 'export_handover', 'generate_summary', 'add_document_section_to_handover',
    'summarise_document_for_handover',

    # Compliance/HOR/Certificates
    'update_hours_of_rest', 'show_hours_of_rest', 'show_certificates', 'show_expiring_certificates',
    'export_logs', 'generate_audit_pack', 'add_certificate', 'upload_certificate_document',
    'update_certificate_metadata',

    # Documents/RAG
    'open_document', 'open_document_page', 'search_documents', 'search_document_pages',
    'summarise_document_section', 'upload_document', 'delete_document', 'archive_document',
    'replace_document_version', 'tag_document', 'link_document_to_fault', 'link_document_to_equipment',
    'compare_document_sections', 'extract_procedures_from_document', 'detect_document_anomalies',

    # Purchasing
    'create_purchase_request', 'add_part_to_purchase_request', 'approve_purchase',
    'track_delivery', 'attach_invoice',

    # Checklists
    'open_checklist', 'mark_checklist_item_complete', 'add_note_to_checklist_item',
    'attach_photo_to_checklist_item',

    # Shipyard/Refit
    'open_worklist', 'add_worklist_item', 'update_worklist_progress', 'export_worklist',
    'tag_worklist_item',

    # Fleet
    'open_fleet_summary', 'open_vessel_from_fleet', 'export_fleet_report',

    # Utility
    'undo_last_action', 'open_location_on_map', 'view_file', 'open_media', 'show_linked_context',
}

# ============================================================================
# TEST QUERY TEMPLATES AND VARIATIONS
# ============================================================================

def generate_stress_test_dataset() -> List[Dict]:
    """Generate 600+ diverse test queries"""

    queries = []
    query_id = 0

    # ==========================================================================
    # LAYER A: HAND-CRAFTED GOLD SEEDS (300-500 unique, meaningfully different)
    # ==========================================================================

    # --------------------------------------------------------------------------
    # 1. FAULT/DIAGNOSTIC QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    fault_diagnostic_seeds = [
        # Basic diagnose patterns
        {"query": "diagnose E047 coolant leak on ME1", "action": "diagnose_fault", "entities": [{"type": "fault_code", "value_hint": "E047"}, {"type": "equipment", "value_hint": "ME1"}], "difficulty": "easy"},
        {"query": "diagnose SPN 100 FMI 3 on port main", "action": "diagnose_fault", "entities": [{"type": "fault_code", "value_hint": "SPN 100 FMI 3"}, {"type": "equipment", "value_hint": "port main"}], "difficulty": "medium"},
        {"query": "diagnose overheating stbd generator", "action": "diagnose_fault", "entities": [{"type": "symptom", "value_hint": "overheating"}, {"type": "equipment", "value_hint": "stbd generator"}], "difficulty": "easy"},
        {"query": "diagnose why ME2 keeps tripping at 1800 rpm", "action": "diagnose_fault", "entities": [{"type": "equipment", "value_hint": "ME2"}, {"type": "symptom", "value_hint": "tripping"}, {"type": "measurement", "value_hint": "1800 rpm"}], "difficulty": "hard"},
        {"query": "diagnose P0420 catalyst efficiency below threshold", "action": "diagnose_fault", "entities": [{"type": "fault_code", "value_hint": "P0420"}], "difficulty": "medium"},
        {"query": "diagnose alarm 4521 on DG2", "action": "diagnose_fault", "entities": [{"type": "fault_code", "value_hint": "alarm 4521"}, {"type": "equipment", "value_hint": "DG2"}], "difficulty": "easy"},
        {"query": "diagnose vibration from port shaft at cruising speed", "action": "diagnose_fault", "entities": [{"type": "symptom", "value_hint": "vibration"}, {"type": "equipment", "value_hint": "port shaft"}], "difficulty": "medium"},
        {"query": "diagnose why watermaker output dropped to 50 l/h", "action": "diagnose_fault", "entities": [{"type": "equipment", "value_hint": "watermaker"}, {"type": "measurement", "value_hint": "50 l/h"}], "difficulty": "hard"},
        {"query": "diagnose low oil pressure reading on gen1", "action": "diagnose_fault", "entities": [{"type": "symptom", "value_hint": "low oil pressure"}, {"type": "equipment", "value_hint": "gen1"}], "difficulty": "easy"},
        {"query": "diagnose high exhaust temp 650C on turbo inlet", "action": "diagnose_fault", "entities": [{"type": "symptom", "value_hint": "high exhaust temp"}, {"type": "measurement", "value_hint": "650C"}, {"type": "part", "value_hint": "turbo inlet"}], "difficulty": "hard"},

        # Show manual section
        {"query": "show manual section for MTU 16V4000 cooling system", "action": "show_manual_section", "entities": [{"type": "equipment", "value_hint": "MTU 16V4000"}, {"type": "system", "value_hint": "cooling system"}], "difficulty": "easy"},
        {"query": "show lube oil section from CAT 3512 service manual", "action": "show_manual_section", "entities": [{"type": "equipment", "value_hint": "CAT 3512"}, {"type": "doc_type", "value_hint": "service manual"}], "difficulty": "medium"},
        {"query": "show troubleshooting guide for seakeeper gyro", "action": "show_manual_section", "entities": [{"type": "equipment", "value_hint": "seakeeper"}, {"type": "doc_type", "value_hint": "troubleshooting guide"}], "difficulty": "easy"},

        # Show equipment history
        {"query": "show history main engine port since last service", "action": "show_equipment_history", "entities": [{"type": "equipment", "value_hint": "main engine port"}], "difficulty": "medium"},
        {"query": "show equipment history for stabilizers last 90 days", "action": "show_equipment_history", "entities": [{"type": "equipment", "value_hint": "stabilizers"}], "difficulty": "easy"},
        {"query": "show past events watermaker membrane replacement", "action": "show_similar_past_events", "entities": [{"type": "equipment", "value_hint": "watermaker"}, {"type": "part", "value_hint": "membrane"}], "difficulty": "medium"},

        # Trace related
        {"query": "trace related faults to cooling pump failure", "action": "trace_related_faults", "entities": [{"type": "equipment", "value_hint": "cooling pump"}], "difficulty": "medium"},
        {"query": "trace what equipment connects to hydraulic manifold", "action": "trace_related_equipment", "entities": [{"type": "part", "value_hint": "hydraulic manifold"}], "difficulty": "medium"},

        # Show predictive
        {"query": "show predictive insight for generator bearings", "action": "show_predictive_insight", "entities": [{"type": "equipment", "value_hint": "generator"}, {"type": "part", "value_hint": "bearings"}], "difficulty": "medium"},
        {"query": "suggest likely parts for low output on watermaker", "action": "suggest_likely_parts", "entities": [{"type": "symptom", "value_hint": "low output"}, {"type": "equipment", "value_hint": "watermaker"}], "difficulty": "medium"},
    ]

    for seed in fault_diagnostic_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "fix_something",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 2. WORK ORDER QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    work_order_seeds = [
        {"query": "create work order for bilge pump replacement", "action": "create_work_order", "entities": [{"type": "equipment", "value_hint": "bilge pump"}], "difficulty": "easy"},
        {"query": "create wo ME1 oil change 500hr service", "action": "create_work_order", "entities": [{"type": "equipment", "value_hint": "ME1"}], "difficulty": "medium"},
        {"query": "create urgent work order gen2 cooling fan seized", "action": "create_work_order", "entities": [{"type": "equipment", "value_hint": "gen2"}, {"type": "part", "value_hint": "cooling fan"}, {"type": "symptom", "value_hint": "seized"}], "difficulty": "hard"},
        {"query": "create work order from fault E047", "action": "create_work_order_from_fault", "entities": [{"type": "fault_code", "value_hint": "E047"}], "difficulty": "easy"},
        {"query": "create wo from alarm 4521 high temp DG2", "action": "create_work_order_from_fault", "entities": [{"type": "fault_code", "value_hint": "alarm 4521"}, {"type": "equipment", "value_hint": "DG2"}], "difficulty": "medium"},

        {"query": "add note to work order WO-2847 parts ordered", "action": "add_note_to_work_order", "entities": [{"type": "equipment", "value_hint": "WO-2847"}], "difficulty": "easy"},
        {"query": "add note wo 3341 waiting for zinc delivery", "action": "add_note_to_work_order", "entities": [{"type": "part", "value_hint": "zinc"}], "difficulty": "medium"},
        {"query": "attach photo to work order 2847", "action": "attach_photo_to_work_order", "entities": [], "difficulty": "easy"},
        {"query": "attach document gasket specs to WO-3341", "action": "attach_document_to_work_order", "entities": [{"type": "part", "value_hint": "gasket"}], "difficulty": "medium"},
        {"query": "add impeller to work order 2847", "action": "add_part_to_work_order", "entities": [{"type": "part", "value_hint": "impeller"}], "difficulty": "easy"},

        {"query": "mark work order 2847 complete", "action": "mark_work_order_complete", "entities": [], "difficulty": "easy"},
        {"query": "close wo 3341 job done", "action": "mark_work_order_complete", "entities": [], "difficulty": "easy"},
        {"query": "show tasks due this week", "action": "show_tasks_due", "entities": [], "difficulty": "easy"},
        {"query": "show overdue work orders", "action": "show_tasks_overdue", "entities": [], "difficulty": "easy"},
        {"query": "show tasks due before charter Friday", "action": "show_tasks_due", "entities": [], "difficulty": "medium"},
    ]

    for seed in work_order_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "do_maintenance",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 3. EQUIPMENT QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    equipment_seeds = [
        {"query": "open equipment card for main engine 1", "action": "open_equipment_card", "entities": [{"type": "equipment", "value_hint": "main engine 1"}], "difficulty": "easy"},
        {"query": "open card DG2", "action": "open_equipment_card", "entities": [{"type": "equipment", "value_hint": "DG2"}], "difficulty": "easy"},
        {"query": "open equipment watermaker spectra", "action": "open_equipment_card", "entities": [{"type": "equipment", "value_hint": "watermaker"}, {"type": "brand", "value_hint": "spectra"}], "difficulty": "medium"},
        {"query": "show all parts linked to port main engine", "action": "show_all_linked_parts", "entities": [{"type": "equipment", "value_hint": "port main engine"}], "difficulty": "easy"},
        {"query": "show linked faults ME1", "action": "show_all_linked_faults", "entities": [{"type": "equipment", "value_hint": "ME1"}], "difficulty": "easy"},
        {"query": "show all documents linked to generator 1", "action": "show_all_linked_documents", "entities": [{"type": "equipment", "value_hint": "generator 1"}], "difficulty": "easy"},
        {"query": "show work orders linked to bilge pump", "action": "show_all_linked_work_orders", "entities": [{"type": "equipment", "value_hint": "bilge pump"}], "difficulty": "easy"},
        {"query": "link service bulletin to ME2", "action": "link_document_to_equipment", "entities": [{"type": "doc_type", "value_hint": "service bulletin"}, {"type": "equipment", "value_hint": "ME2"}], "difficulty": "medium"},
    ]

    for seed in equipment_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "manage_equipment",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 4. INVENTORY/PARTS QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    inventory_seeds = [
        {"query": "check stock level jabsco impeller", "action": "check_stock_level", "entities": [{"type": "brand", "value_hint": "jabsco"}, {"type": "part", "value_hint": "impeller"}], "difficulty": "easy"},
        {"query": "check stock oil filters CAT 3512", "action": "check_stock_level", "entities": [{"type": "part", "value_hint": "oil filters"}, {"type": "equipment", "value_hint": "CAT 3512"}], "difficulty": "medium"},
        {"query": "check how many zincs we have", "action": "check_stock_level", "entities": [{"type": "part", "value_hint": "zincs"}], "difficulty": "easy"},
        {"query": "show storage location for fuel filters", "action": "show_storage_location", "entities": [{"type": "part", "value_hint": "fuel filters"}], "difficulty": "easy"},
        {"query": "show where we keep the spare impellers", "action": "show_storage_location", "entities": [{"type": "part", "value_hint": "impellers"}], "difficulty": "easy"},
        {"query": "order part racor filter 2020SM", "action": "order_part", "entities": [{"type": "brand", "value_hint": "racor"}, {"type": "part", "value_hint": "filter 2020SM"}], "difficulty": "medium"},
        {"query": "order 6x zinc anodes for hull", "action": "order_part", "entities": [{"type": "part", "value_hint": "zinc anodes"}], "difficulty": "easy"},
        {"query": "add oil filter to handover list", "action": "add_part_to_handover", "entities": [{"type": "part", "value_hint": "oil filter"}], "difficulty": "easy"},
        {"query": "log part usage 2x fuel filters used on gen1", "action": "log_part_usage", "entities": [{"type": "part", "value_hint": "fuel filters"}, {"type": "equipment", "value_hint": "gen1"}], "difficulty": "medium"},
        {"query": "scan barcode for inventory", "action": "scan_barcode", "entities": [], "difficulty": "easy"},
    ]

    for seed in inventory_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "inventory",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 5. HANDOVER/COMMS QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    handover_seeds = [
        {"query": "add to handover ME1 running rough at idle", "action": "add_to_handover", "entities": [{"type": "equipment", "value_hint": "ME1"}, {"type": "symptom", "value_hint": "running rough"}], "difficulty": "easy"},
        {"query": "add note bilge pump making noise", "action": "add_note", "entities": [{"type": "equipment", "value_hint": "bilge pump"}, {"type": "symptom", "value_hint": "noise"}], "difficulty": "easy"},
        {"query": "add to handover: checked zincs, ordered replacements", "action": "add_to_handover", "entities": [{"type": "part", "value_hint": "zincs"}], "difficulty": "medium"},
        {"query": "add predictive insight generator bearing wear to handover", "action": "add_predictive_insight_to_handover", "entities": [{"type": "equipment", "value_hint": "generator"}, {"type": "part", "value_hint": "bearing"}], "difficulty": "medium"},
        {"query": "add service bulletin to handover", "action": "add_document_to_handover", "entities": [{"type": "doc_type", "value_hint": "service bulletin"}], "difficulty": "easy"},
        {"query": "edit handover section engineering notes", "action": "edit_handover_section", "entities": [], "difficulty": "easy"},
        {"query": "export handover to PDF", "action": "export_handover", "entities": [], "difficulty": "easy"},
        {"query": "generate summary for captain", "action": "generate_summary", "entities": [{"type": "person", "value_hint": "captain"}], "difficulty": "easy"},
        {"query": "summarise MTU manual lube section for handover", "action": "summarise_document_for_handover", "entities": [{"type": "brand", "value_hint": "MTU"}, {"type": "doc_type", "value_hint": "manual"}], "difficulty": "medium"},
    ]

    for seed in handover_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "handover",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 6. COMPLIANCE/HOR/CERTIFICATES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    compliance_seeds = [
        {"query": "update hours of rest for bosun today", "action": "update_hours_of_rest", "entities": [{"type": "person", "value_hint": "bosun"}], "difficulty": "easy"},
        {"query": "log HOR chief engineer 10h work 14h rest", "action": "update_hours_of_rest", "entities": [{"type": "person", "value_hint": "chief engineer"}], "difficulty": "medium"},
        {"query": "show hours of rest last 7 days", "action": "show_hours_of_rest", "entities": [], "difficulty": "easy"},
        {"query": "show HOR violations this month", "action": "show_hours_of_rest", "entities": [], "difficulty": "medium"},
        {"query": "show certificates expiring next 90 days", "action": "show_expiring_certificates", "entities": [], "difficulty": "easy"},
        {"query": "show all certificates for life rafts", "action": "show_certificates", "entities": [{"type": "equipment", "value_hint": "life rafts"}], "difficulty": "easy"},
        {"query": "export logs for flag state audit", "action": "export_logs", "entities": [], "difficulty": "medium"},
        {"query": "generate audit pack ISM compliance", "action": "generate_audit_pack", "entities": [], "difficulty": "medium"},
        {"query": "add certificate EPIRB annual service", "action": "add_certificate", "entities": [{"type": "equipment", "value_hint": "EPIRB"}], "difficulty": "easy"},
        {"query": "upload certificate document fire extinguisher inspection", "action": "upload_certificate_document", "entities": [{"type": "equipment", "value_hint": "fire extinguisher"}], "difficulty": "easy"},
    ]

    for seed in compliance_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "compliance",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 7. DOCUMENTS/RAG QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    document_seeds = [
        {"query": "open document CAT 3512 service manual", "action": "open_document", "entities": [{"type": "equipment", "value_hint": "CAT 3512"}, {"type": "doc_type", "value_hint": "service manual"}], "difficulty": "easy"},
        {"query": "open page 47 MTU 16V4000 manual", "action": "open_document_page", "entities": [{"type": "equipment", "value_hint": "MTU 16V4000"}, {"type": "doc_type", "value_hint": "manual"}], "difficulty": "medium"},
        {"query": "search documents for lube oil specifications", "action": "search_documents", "entities": [], "difficulty": "easy"},
        {"query": "search within seakeeper manual for calibration", "action": "search_document_pages", "entities": [{"type": "equipment", "value_hint": "seakeeper"}, {"type": "doc_type", "value_hint": "manual"}], "difficulty": "medium"},
        {"query": "summarise cooling system section from MTU manual", "action": "summarise_document_section", "entities": [{"type": "system", "value_hint": "cooling system"}, {"type": "brand", "value_hint": "MTU"}], "difficulty": "medium"},
        {"query": "upload document new service bulletin", "action": "upload_document", "entities": [{"type": "doc_type", "value_hint": "service bulletin"}], "difficulty": "easy"},
        {"query": "archive old generator manual", "action": "archive_document", "entities": [{"type": "equipment", "value_hint": "generator"}, {"type": "doc_type", "value_hint": "manual"}], "difficulty": "easy"},
        {"query": "tag document with ME1 equipment tag", "action": "tag_document", "entities": [{"type": "equipment", "value_hint": "ME1"}], "difficulty": "easy"},
        {"query": "link schematic to fault E047", "action": "link_document_to_fault", "entities": [{"type": "doc_type", "value_hint": "schematic"}, {"type": "fault_code", "value_hint": "E047"}], "difficulty": "medium"},
        {"query": "compare fuel system section old vs new manual", "action": "compare_document_sections", "entities": [{"type": "system", "value_hint": "fuel system"}], "difficulty": "hard"},
        {"query": "extract procedures from maintenance checklist", "action": "extract_procedures_from_document", "entities": [{"type": "doc_type", "value_hint": "maintenance checklist"}], "difficulty": "medium"},
    ]

    for seed in document_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "documents",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 8. PURCHASING QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    purchasing_seeds = [
        {"query": "create purchase request for zinc anodes", "action": "create_purchase_request", "entities": [{"type": "part", "value_hint": "zinc anodes"}], "difficulty": "easy"},
        {"query": "create PR oil filters x12 CAT 3512", "action": "create_purchase_request", "entities": [{"type": "part", "value_hint": "oil filters"}, {"type": "equipment", "value_hint": "CAT 3512"}], "difficulty": "medium"},
        {"query": "add impeller to purchase request PR-441", "action": "add_part_to_purchase_request", "entities": [{"type": "part", "value_hint": "impeller"}], "difficulty": "easy"},
        {"query": "approve purchase order PO-892", "action": "approve_purchase", "entities": [], "difficulty": "easy"},
        {"query": "track delivery order 892 zincs", "action": "track_delivery", "entities": [{"type": "part", "value_hint": "zincs"}], "difficulty": "easy"},
        {"query": "attach invoice to PO-892", "action": "attach_invoice", "entities": [], "difficulty": "easy"},
    ]

    for seed in purchasing_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "purchasing",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 9. CHECKLISTS QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    checklist_seeds = [
        {"query": "open checklist engine room rounds", "action": "open_checklist", "entities": [{"type": "location", "value_hint": "engine room"}], "difficulty": "easy"},
        {"query": "open pre-departure checklist", "action": "open_checklist", "entities": [], "difficulty": "easy"},
        {"query": "mark checklist item complete bilge inspection", "action": "mark_checklist_item_complete", "entities": [{"type": "equipment", "value_hint": "bilge"}], "difficulty": "easy"},
        {"query": "add note to checklist item found debris in strainer", "action": "add_note_to_checklist_item", "entities": [{"type": "part", "value_hint": "strainer"}], "difficulty": "medium"},
        {"query": "attach photo to checklist item zinc condition", "action": "attach_photo_to_checklist_item", "entities": [{"type": "part", "value_hint": "zinc"}], "difficulty": "easy"},
    ]

    for seed in checklist_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "checklists",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 10. SHIPYARD/REFIT QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    shipyard_seeds = [
        {"query": "open worklist hull paint refit 2025", "action": "open_worklist", "entities": [], "difficulty": "easy"},
        {"query": "add worklist item thruster overhaul", "action": "add_worklist_item", "entities": [{"type": "equipment", "value_hint": "thruster"}], "difficulty": "easy"},
        {"query": "update worklist progress item 47 complete", "action": "update_worklist_progress", "entities": [], "difficulty": "easy"},
        {"query": "export worklist for yard meeting", "action": "export_worklist", "entities": [], "difficulty": "easy"},
        {"query": "tag worklist item critical path", "action": "tag_worklist_item", "entities": [], "difficulty": "easy"},
    ]

    for seed in shipyard_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "shipyard",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 11. FLEET QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    fleet_seeds = [
        {"query": "open fleet summary all vessels", "action": "open_fleet_summary", "entities": [], "difficulty": "easy"},
        {"query": "open vessel MY Serenity from fleet", "action": "open_vessel_from_fleet", "entities": [], "difficulty": "easy"},
        {"query": "export fleet report maintenance status", "action": "export_fleet_report", "entities": [], "difficulty": "easy"},
    ]

    for seed in fleet_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "fleet",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # --------------------------------------------------------------------------
    # 12. UTILITY QUERIES (verb-first, should trigger)
    # --------------------------------------------------------------------------
    utility_seeds = [
        {"query": "undo last action", "action": "undo_last_action", "entities": [], "difficulty": "easy"},
        {"query": "open location on map engine room", "action": "open_location_on_map", "entities": [{"type": "location", "value_hint": "engine room"}], "difficulty": "easy"},
        {"query": "view file pump schematic.pdf", "action": "view_file", "entities": [{"type": "doc_type", "value_hint": "schematic"}], "difficulty": "easy"},
        {"query": "show linked context for fault E047", "action": "show_linked_context", "entities": [{"type": "fault_code", "value_hint": "E047"}], "difficulty": "medium"},
    ]

    for seed in utility_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "utility",
                "difficulty": seed["difficulty"],
                "noise_type": "clean"
            }
        })

    # ==========================================================================
    # LAYER B: NOUN-FIRST / CONVERSATIONAL (should NOT trigger strict action)
    # ==========================================================================

    noun_first_seeds = [
        # Equipment lookups (noun-first)
        {"query": "ME1 oil pressure history", "entities": [{"type": "equipment", "value_hint": "ME1"}]},
        {"query": "DG2 alarm codes", "entities": [{"type": "equipment", "value_hint": "DG2"}]},
        {"query": "watermaker output trending down", "entities": [{"type": "equipment", "value_hint": "watermaker"}, {"type": "symptom", "value_hint": "trending down"}]},
        {"query": "MTU 16V4000 coolant temp sensor location", "entities": [{"type": "equipment", "value_hint": "MTU 16V4000"}, {"type": "part", "value_hint": "coolant temp sensor"}]},
        {"query": "CAT 3512 oil filter part number", "entities": [{"type": "equipment", "value_hint": "CAT 3512"}, {"type": "part", "value_hint": "oil filter"}]},
        {"query": "seakeeper gyro calibration procedure", "entities": [{"type": "equipment", "value_hint": "seakeeper"}]},
        {"query": "jabsco pump rebuild kit", "entities": [{"type": "brand", "value_hint": "jabsco"}, {"type": "part", "value_hint": "rebuild kit"}]},
        {"query": "victron battery monitor settings", "entities": [{"type": "brand", "value_hint": "victron"}, {"type": "equipment", "value_hint": "battery monitor"}]},

        # Conversational / question form
        {"query": "what's the history on ME1 overheating", "entities": [{"type": "equipment", "value_hint": "ME1"}, {"type": "symptom", "value_hint": "overheating"}]},
        {"query": "what does error E047 mean", "entities": [{"type": "fault_code", "value_hint": "E047"}]},
        {"query": "where are the spare impellers stored", "entities": [{"type": "part", "value_hint": "impellers"}]},
        {"query": "who worked on the generator last", "entities": [{"type": "equipment", "value_hint": "generator"}]},
        {"query": "when was the watermaker membrane replaced", "entities": [{"type": "equipment", "value_hint": "watermaker"}, {"type": "part", "value_hint": "membrane"}]},
        {"query": "how many oil filters do we have", "entities": [{"type": "part", "value_hint": "oil filters"}]},
        {"query": "why is DG2 running hot", "entities": [{"type": "equipment", "value_hint": "DG2"}, {"type": "symptom", "value_hint": "running hot"}]},

        # "I want to..." / "Can you..." / "Please..." patterns
        {"query": "I want to create a work order for bilge pump", "entities": [{"type": "equipment", "value_hint": "bilge pump"}]},
        {"query": "can you show me the MTU manual", "entities": [{"type": "brand", "value_hint": "MTU"}, {"type": "doc_type", "value_hint": "manual"}]},
        {"query": "please add this to handover", "entities": []},
        {"query": "I need to check stock on zincs", "entities": [{"type": "part", "value_hint": "zincs"}]},
        {"query": "could you diagnose this fault code E047", "entities": [{"type": "fault_code", "value_hint": "E047"}]},
        {"query": "would like to order some oil filters", "entities": [{"type": "part", "value_hint": "oil filters"}]},

        # Pure lookups
        {"query": "generator 1 manual", "entities": [{"type": "equipment", "value_hint": "generator 1"}, {"type": "doc_type", "value_hint": "manual"}]},
        {"query": "stabilizer troubleshooting", "entities": [{"type": "equipment", "value_hint": "stabilizer"}]},
        {"query": "radar fault codes list", "entities": [{"type": "equipment", "value_hint": "radar"}]},
        {"query": "anchor windlass service interval", "entities": [{"type": "equipment", "value_hint": "anchor windlass"}]},
    ]

    for seed in noun_first_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": "none_search_only",
                "should_trigger_action": False,
                "expected_entities": seed["entities"],
                "purpose_cluster": "general",
                "difficulty": "medium",
                "noise_type": "clean"
            }
        })

    # ==========================================================================
    # LAYER C: HARD MODE - MESSY/NOISY/MIXED INTENT
    # ==========================================================================

    hard_mode_seeds = [
        # Typos
        {"query": "diagnose overheatng ME1", "action": "diagnose_fault", "noise": "typo", "entities": [{"type": "symptom", "value_hint": "overheating"}, {"type": "equipment", "value_hint": "ME1"}]},
        {"query": "create workorder genrator 2 oil change", "action": "create_work_order", "noise": "typo", "entities": [{"type": "equipment", "value_hint": "generator 2"}]},
        {"query": "chek stock jabsco impeler", "action": "check_stock_level", "noise": "typo", "entities": [{"type": "brand", "value_hint": "jabsco"}, {"type": "part", "value_hint": "impeller"}]},
        {"query": "opne document MTU manul", "action": "open_document", "noise": "typo", "entities": [{"type": "brand", "value_hint": "MTU"}, {"type": "doc_type", "value_hint": "manual"}]},

        # Voice dictation artifacts
        {"query": "diagnose main engine one overheating", "action": "diagnose_fault", "noise": "voice", "entities": [{"type": "equipment", "value_hint": "main engine 1"}, {"type": "symptom", "value_hint": "overheating"}]},
        {"query": "create work order for the bilge pump its making noise", "action": "create_work_order", "noise": "voice", "entities": [{"type": "equipment", "value_hint": "bilge pump"}, {"type": "symptom", "value_hint": "noise"}]},
        {"query": "show me the manual for the cat thirty five twelve", "action": "show_manual_section", "noise": "voice", "entities": [{"type": "equipment", "value_hint": "CAT 3512"}]},

        # Shorthand / abbreviations
        {"query": "diag E047 ME1", "action": "diagnose_fault", "noise": "shorthand", "entities": [{"type": "fault_code", "value_hint": "E047"}, {"type": "equipment", "value_hint": "ME1"}]},
        {"query": "creat wo DG2 overheat", "action": "create_work_order", "noise": "shorthand", "entities": [{"type": "equipment", "value_hint": "DG2"}, {"type": "symptom", "value_hint": "overheat"}]},
        {"query": "chk stk zincs", "action": "check_stock_level", "noise": "shorthand", "entities": [{"type": "part", "value_hint": "zincs"}]},
        {"query": "add hndovr gen1 oilchng done", "action": "add_to_handover", "noise": "shorthand", "entities": [{"type": "equipment", "value_hint": "gen1"}]},
        {"query": "shw docs ME1", "action": "show_all_linked_documents", "noise": "shorthand", "entities": [{"type": "equipment", "value_hint": "ME1"}]},

        # Messy paste / alarm strings
        {"query": "diagnose [ALARM] 2024-12-21T14:32:00 E047 HIGH COOLANT TEMP ME1 >105C", "action": "diagnose_fault", "noise": "messy_paste", "entities": [{"type": "fault_code", "value_hint": "E047"}, {"type": "equipment", "value_hint": "ME1"}, {"type": "measurement", "value_hint": ">105C"}]},
        {"query": "diagnose SPN:100 FMI:3 - LOW OIL PRESSURE WARNING - DG2", "action": "diagnose_fault", "noise": "messy_paste", "entities": [{"type": "fault_code", "value_hint": "SPN 100 FMI 3"}, {"type": "equipment", "value_hint": "DG2"}]},
        {"query": "create wo from: FAULT_4521_HIGH_TEMP_GEN2_2024-12-21", "action": "create_work_order_from_fault", "noise": "messy_paste", "entities": [{"type": "fault_code", "value_hint": "4521"}, {"type": "equipment", "value_hint": "GEN2"}]},

        # Mixed intent (multiple actions)
        {"query": "diagnose E047 and create work order and add to handover", "action": "diagnose_fault", "noise": "mixed_intent", "entities": [{"type": "fault_code", "value_hint": "E047"}]},
        {"query": "check stock zincs order more if low and add to handover", "action": "check_stock_level", "noise": "mixed_intent", "entities": [{"type": "part", "value_hint": "zincs"}]},
        {"query": "show ME1 history then create wo for oil change", "action": "show_equipment_history", "noise": "mixed_intent", "entities": [{"type": "equipment", "value_hint": "ME1"}]},

        # Weird casing
        {"query": "DIAGNOSE E047 ON ME1", "action": "diagnose_fault", "noise": "messy_paste", "entities": [{"type": "fault_code", "value_hint": "E047"}, {"type": "equipment", "value_hint": "ME1"}]},
        {"query": "CREATE Work Order FOR bilge PUMP", "action": "create_work_order", "noise": "messy_paste", "entities": [{"type": "equipment", "value_hint": "bilge pump"}]},
        {"query": "ShOw MaNuAl MtU 16v4000", "action": "show_manual_section", "noise": "messy_paste", "entities": [{"type": "equipment", "value_hint": "MTU 16V4000"}]},

        # Complex fault codes
        {"query": "diagnose MTU fault 0x4521 coolant system", "action": "diagnose_fault", "noise": "shorthand", "entities": [{"type": "fault_code", "value_hint": "0x4521"}, {"type": "system", "value_hint": "coolant system"}]},
        {"query": "diagnose CAT flash code 35-2", "action": "diagnose_fault", "noise": "shorthand", "entities": [{"type": "fault_code", "value_hint": "35-2"}]},
        {"query": "diagnose MID 128 PID 110 FMI 0 coolant temp", "action": "diagnose_fault", "noise": "messy_paste", "entities": [{"type": "fault_code", "value_hint": "MID 128 PID 110 FMI 0"}]},

        # Time references
        {"query": "diagnose ME1 overheating since yesterday", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "equipment", "value_hint": "ME1"}, {"type": "symptom", "value_hint": "overheating"}]},
        {"query": "show history watermaker last 2 weeks", "action": "show_equipment_history", "noise": "clean", "entities": [{"type": "equipment", "value_hint": "watermaker"}]},
        {"query": "create wo urgent before charter friday", "action": "create_work_order", "noise": "clean", "entities": []},
        {"query": "diagnose vibration started after leaving port", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "symptom", "value_hint": "vibration"}]},

        # Measurements
        {"query": "diagnose why coolant temp reading 95C when should be 80C", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "measurement", "value_hint": "95C"}, {"type": "measurement", "value_hint": "80C"}]},
        {"query": "diagnose low oil pressure 2.1 bar should be 3.5 bar", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "symptom", "value_hint": "low oil pressure"}, {"type": "measurement", "value_hint": "2.1 bar"}, {"type": "measurement", "value_hint": "3.5 bar"}]},
        {"query": "diagnose voltage drop 24V down to 22.5V", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "symptom", "value_hint": "voltage drop"}, {"type": "measurement", "value_hint": "24V"}, {"type": "measurement", "value_hint": "22.5V"}]},

        # Environment context
        {"query": "diagnose ME1 overheating at sea rough conditions", "action": "diagnose_fault", "noise": "clean", "entities": [{"type": "equipment", "value_hint": "ME1"}, {"type": "symptom", "value_hint": "overheating"}]},
        {"query": "add to handover night shift found leak bilge", "action": "add_to_handover", "noise": "clean", "entities": [{"type": "symptom", "value_hint": "leak"}, {"type": "location", "value_hint": "bilge"}]},
        {"query": "create urgent wo guest onboard stabilizer issue", "action": "create_work_order", "noise": "clean", "entities": [{"type": "equipment", "value_hint": "stabilizer"}]},
    ]

    for seed in hard_mode_seeds:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": seed["query"],
            "labels": {
                "expected_primary_action": seed["action"],
                "should_trigger_action": True,
                "expected_entities": seed["entities"],
                "purpose_cluster": "fix_something",
                "difficulty": "hard",
                "noise_type": seed["noise"]
            }
        })

    # ==========================================================================
    # ADVERSARIAL / NEGATIVE CONTROLS (should NOT trigger any action)
    # ==========================================================================

    negative_controls = [
        # Non-domain queries
        {"query": "what's the weather like today", "reason": "non_domain"},
        {"query": "tell me a joke", "reason": "non_domain"},
        {"query": "who won the football last night", "reason": "non_domain"},
        {"query": "what time is it in Monaco", "reason": "non_domain"},
        {"query": "how do I cook pasta", "reason": "non_domain"},

        # Too vague
        {"query": "help", "reason": "too_vague"},
        {"query": "problem", "reason": "too_vague"},
        {"query": "fix it", "reason": "too_vague"},
        {"query": "issue", "reason": "too_vague"},
        {"query": "thing", "reason": "too_vague"},

        # Paste dumps (should be blocked)
        {"query": "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua Ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat", "reason": "paste_dump"},

        # Gibberish
        {"query": "asdfghjkl qwerty zxcvbn", "reason": "gibberish"},
        {"query": "123456789 !!!! ????", "reason": "gibberish"},

        # Greetings (no action)
        {"query": "hello", "reason": "greeting"},
        {"query": "good morning", "reason": "greeting"},
        {"query": "thanks", "reason": "greeting"},
        {"query": "thank you", "reason": "greeting"},
    ]

    for ctrl in negative_controls:
        query_id += 1
        queries.append({
            "id": f"Q{query_id:04d}",
            "query": ctrl["query"],
            "labels": {
                "expected_primary_action": "none_search_only",
                "should_trigger_action": False,
                "expected_entities": [],
                "purpose_cluster": "general",
                "difficulty": "easy",
                "noise_type": "clean",
                "block_reason": ctrl["reason"]
            }
        })

    # ==========================================================================
    # MUTATIONS: Generate variants of seed queries
    # ==========================================================================

    def mutate_query(query: str, mutation_type: str) -> str:
        """Apply mutation to query"""
        if mutation_type == "lowercase":
            return query.lower()
        elif mutation_type == "uppercase":
            return query.upper()
        elif mutation_type == "please_prefix":
            return f"please {query.lower()}"
        elif mutation_type == "can_you_prefix":
            return f"can you {query.lower()}"
        elif mutation_type == "extra_spaces":
            words = query.split()
            return "  ".join(words)
        elif mutation_type == "no_spaces":
            # Only remove spaces around certain words
            return query.replace(" work order", " workorder").replace(" hand over", " handover")
        return query

    # Take a subset of verb-first seeds for mutations
    verb_first_queries = [q for q in queries if q["labels"]["should_trigger_action"]][:50]

    mutations = ["lowercase", "uppercase", "please_prefix", "extra_spaces"]
    for base_query in verb_first_queries[:30]:
        for mutation in random.sample(mutations, 2):  # 2 mutations per seed
            query_id += 1
            mutated = mutate_query(base_query["query"], mutation)

            # please/can_you prefix changes should_trigger_action to False
            should_trigger = base_query["labels"]["should_trigger_action"]
            if mutation in ["please_prefix", "can_you_prefix"]:
                should_trigger = False

            queries.append({
                "id": f"Q{query_id:04d}",
                "query": mutated,
                "labels": {
                    **base_query["labels"],
                    "should_trigger_action": should_trigger,
                    "noise_type": mutation,
                    "mutation_of": base_query["id"]
                }
            })

    return queries


def save_dataset(queries: List[Dict], filepath: str):
    """Save dataset as JSONL"""
    with open(filepath, 'w') as f:
        for q in queries:
            f.write(json.dumps(q) + '\n')
    print(f"Saved {len(queries)} queries to {filepath}")


def get_dataset_stats(queries: List[Dict]) -> Dict:
    """Get statistics about the dataset"""
    stats = {
        "total": len(queries),
        "should_trigger_true": sum(1 for q in queries if q["labels"]["should_trigger_action"]),
        "should_trigger_false": sum(1 for q in queries if not q["labels"]["should_trigger_action"]),
        "by_difficulty": {},
        "by_noise_type": {},
        "by_purpose_cluster": {},
        "by_action": {}
    }

    for q in queries:
        labels = q["labels"]

        # By difficulty
        diff = labels.get("difficulty", "unknown")
        stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1

        # By noise type
        noise = labels.get("noise_type", "unknown")
        stats["by_noise_type"][noise] = stats["by_noise_type"].get(noise, 0) + 1

        # By purpose cluster
        purpose = labels.get("purpose_cluster", "unknown")
        stats["by_purpose_cluster"][purpose] = stats["by_purpose_cluster"].get(purpose, 0) + 1

        # By action
        action = labels.get("expected_primary_action", "unknown")
        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1

    return stats


if __name__ == "__main__":
    # Generate dataset
    queries = generate_stress_test_dataset()

    # Save to file
    save_dataset(queries, "tests/stress_test_queries.jsonl")

    # Print stats
    stats = get_dataset_stats(queries)
    print("\n=== Dataset Statistics ===")
    print(f"Total queries: {stats['total']}")
    print(f"Should trigger action: {stats['should_trigger_true']}")
    print(f"Should NOT trigger action: {stats['should_trigger_false']}")
    print(f"\nBy difficulty: {stats['by_difficulty']}")
    print(f"\nBy noise type: {stats['by_noise_type']}")
    print(f"\nBy purpose cluster: {stats['by_purpose_cluster']}")
