#!/usr/bin/env python3
"""
CelesteOS Stress Test Dataset Generator V2
==========================================

Generates 1,000 methodical test cases for micro-action routing and entity extraction.

STRICT ROUTING MODE: Actions only trigger when query starts with explicit verb.
Polite prefixes ("can you", "please", "I need") are NEGATIVE CONTROLS.

Distribution targets:
- 350+ verb-first action triggers
- 250+ negative controls (false positive traps)
- 120+ mixed-intent cases
- 80+ messy/voice dictation
- 250+ documents/compliance/handover
- 200+ hard-mode (fault codes, measurements, locations, time qualifiers)
"""

import json
import random
from typing import List, Dict, Any
from datetime import datetime

# =============================================================================
# CANONICAL ACTIONS (Source: CELESTEOS CANONICAL MICRO-ACTION LIST V2)
# =============================================================================

CANONICAL_ACTIONS = [
    # 1. FIX SOMETHING (FAULT / DIAGNOSTIC)
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

    # 2. DO MAINTENANCE (TASKS / WORK ORDERS)
    "create_work_order",
    "create_work_order_from_fault",
    "add_note_to_work_order",
    "attach_photo_to_work_order",
    "attach_document_to_work_order",
    "add_part_to_work_order",
    "mark_work_order_complete",
    "show_tasks_due",
    "show_tasks_overdue",

    # 3. MANAGE EQUIPMENT
    "open_equipment_card",
    "show_all_linked_parts",
    "show_all_linked_faults",
    "show_all_linked_documents",
    "show_all_linked_work_orders",
    "link_document_to_equipment",

    # 4. INVENTORY & PARTS
    "check_stock_level",
    "show_storage_location",
    "order_part",
    "add_part_to_handover",
    "log_part_usage",
    "scan_barcode",

    # 5. HANDOVER & COMMUNICATION
    "add_to_handover",
    "add_note",
    "add_predictive_insight_to_handover",
    "add_document_to_handover",
    "edit_handover_section",
    "export_handover",
    "generate_summary",
    "add_document_section_to_handover",
    "summarise_document_for_handover",

    # 6. COMPLIANCE & HOURS OF REST
    "update_hours_of_rest",
    "show_hours_of_rest",
    "show_certificates",
    "show_expiring_certificates",
    "export_logs",
    "generate_audit_pack",
    "add_certificate",
    "upload_certificate_document",
    "update_certificate_metadata",

    # 7. DOCUMENTS
    "open_document",
    "open_document_page",
    "search_documents",
    "search_document_pages",
    "summarise_document_section",
    "upload_document",
    "delete_document",
    "archive_document",
    "replace_document_version",
    "tag_document",
    "link_document_to_fault",
    "compare_document_sections",
    "extract_procedures_from_document",
    "detect_document_anomalies",

    # 8. PURCHASING & SUPPLIERS
    "create_purchase_request",
    "add_part_to_purchase_request",
    "approve_purchase",
    "track_delivery",
    "attach_invoice",

    # 9. CHECKLISTS & OPERATIONS
    "open_checklist",
    "mark_checklist_item_complete",
    "add_note_to_checklist_item",
    "attach_photo_to_checklist_item",

    # 10. SHIPYARD / REFIT WORK
    "open_worklist",
    "add_worklist_item",
    "update_worklist_progress",
    "export_worklist",
    "tag_worklist_item",

    # 11. FLEET / MANAGEMENT
    "open_fleet_summary",
    "open_vessel_from_fleet",
    "export_fleet_report",

    # 12. GENERAL / SYSTEM UTILITY
    "undo_last_action",
    "open_location_on_map",
    "view_file",
    "open_media",
    "show_linked_context"
]

ENTITY_TYPES = [
    "equipment", "brand", "part", "fault_code", "person",
    "location", "time_range", "measurement", "system", "symptom", "doc_type"
]

# =============================================================================
# DOMAIN LEXICON
# =============================================================================

EQUIPMENT = [
    "main engine", "generator", "genset", "watermaker", "bow thruster", "stern thruster",
    "stabilizer", "gyro stabilizer", "fin stabilizer", "radar", "chartplotter", "autopilot",
    "windlass", "capstan", "tender", "jet ski", "compressor", "chiller", "air handler",
    "bilge pump", "fire pump", "fuel pump", "raw water pump", "circulation pump",
    "battery charger", "inverter", "shore power", "alternator", "transformer",
    "fuel filter", "oil filter", "air filter", "separator", "purifier", "centrifuge",
    "HVAC", "AC unit", "boiler", "heater", "exhaust fan", "ventilation"
]

EQUIPMENT_ABBREV = [
    "ME1", "ME2", "DG1", "DG2", "DG3", "gen1", "gen2", "BT", "ST", "BT1", "BT2",
    "AC1", "AC2", "AC3", "AHU1", "AHU2", "stbd main", "port main", "stbd gen", "port gen"
]

BRANDS = [
    "MTU", "Caterpillar", "CAT", "Cummins", "Volvo Penta", "Yanmar", "MAN", "Perkins",
    "Furuno", "Raymarine", "Garmin", "Simrad", "B&G", "JRC", "Navico",
    "Victron", "Mastervolt", "Fischer Panda", "Northern Lights", "Onan", "Kohler",
    "Spectra", "Sea Recovery", "Village Marine", "Dometic", "Webasto", "Climma",
    "Lewmar", "Maxwell", "Muir", "Lofrans", "Quick", "Vetus",
    "Seakeeper", "Naiad", "Quantum", "ABT TRAC",
    "Jabsco", "Johnson", "Rule", "Whale", "Shurflo", "Racor", "Parker"
]

PARTS = [
    "impeller", "membrane", "seal", "gasket", "o-ring", "bearing", "belt", "filter element",
    "injector", "thermostat", "sensor", "relay", "fuse", "breaker", "contactor",
    "solenoid", "actuator", "pump", "motor", "PCB", "control board", "display",
    "anode", "zinc", "heat exchanger", "cooler", "turbo", "alternator"
]

FAULT_CODES = [
    "E047", "E122", "E-15", "E001", "E999", "P0420", "P0171", "P0300",
    "SPN 100", "SPN 190", "SPN 110 FMI 3", "SPN 94 FMI 1",
    "Alarm 47", "Alarm 122", "Warning 15", "Fault 001",
    "MID 128 SID 001", "MID 144 PSID 25"
]

SYMPTOMS = [
    "overheating", "vibration", "noise", "leak", "low pressure", "high temperature",
    "not starting", "stalling", "surging", "hunting", "tripping", "cutting out",
    "smoking", "sparking", "grinding", "knocking", "rattling", "squealing",
    "low output", "no output", "intermittent", "erratic", "stuck", "seized"
]

LOCATIONS = [
    "engine room", "ER", "forward ER", "aft ER", "bridge", "wheelhouse",
    "lazarette", "forepeak", "bow locker", "stern locker", "bilge",
    "stbd side", "port side", "upper deck", "lower deck", "crew mess",
    "tank top", "compartment 3", "void space", "machinery space"
]

TIME_QUALIFIERS = [
    "today", "yesterday", "this week", "last week", "this month", "last month",
    "since port", "last trip", "after drydock", "before charter",
    "night watch", "morning watch", "last service", "since overhaul"
]

MEASUREMENTS = [
    "4.2 bar", "65 psi", "92C", "185F", "24V", "12V DC", "440V AC",
    "3500 RPM", "1800 hours", "250 hours", "15 knots", "8.5 gph",
    "0.3 ohms", "45 amps", "2.4 kW", "high temp alarm at 95C"
]

DOC_TYPES = [
    "manual", "service manual", "parts manual", "operator manual", "drawing",
    "schematic", "wiring diagram", "P&ID", "procedure", "SOP", "checklist",
    "certificate", "survey report", "class certificate", "ISM document"
]

POLITE_PREFIXES = [
    "can you", "could you", "please", "I need to", "I want to", "we need to",
    "we should", "would you", "I'd like to", "help me", "can I", "is it possible to"
]

CONVERSATIONAL_STARTERS = [
    "hey", "so", "um", "well", "look", "ok so", "right so", "basically"
]

# =============================================================================
# GOLD SEED TEMPLATES (300 unique seeds)
# =============================================================================

def generate_gold_seeds() -> List[Dict]:
    """Generate 300 handcrafted gold seed queries."""
    seeds = []
    seed_id = 1

    # =========================================================================
    # CATEGORY 1: FAULT/DIAGNOSTIC (50 seeds)
    # =========================================================================

    # Verb-first diagnostic commands (20)
    fault_verb_first = [
        ("diagnose fault {fault_code} on {equipment}", "diagnose_fault", True),
        ("diagnose {symptom} on {equipment}", "diagnose_fault", True),
        ("diagnose {equipment} {symptom}", "diagnose_fault", True),
        ("show manual section for {symptom}", "show_manual_section", True),
        ("show manual for {brand} {equipment}", "show_manual_section", True),
        ("show related documents for {fault_code}", "show_related_documents", True),
        ("show equipment overview {equipment}", "show_equipment_overview", True),
        ("show equipment history for {equipment}", "show_equipment_history", True),
        ("show recent state of {equipment}", "show_recent_state", True),
        ("show predictive insight for {equipment}", "show_predictive_insight", True),
        ("suggest likely parts for {fault_code}", "suggest_likely_parts", True),
        ("show similar past events to {fault_code}", "show_similar_past_events", True),
        ("trace related faults to {equipment}", "trace_related_faults", True),
        ("trace related equipment to {fault_code}", "trace_related_equipment", True),
        ("view linked entities for {equipment}", "view_linked_entities", True),
        ("show document graph for {equipment}", "show_document_graph", True),
        ("diagnose why {equipment} is {symptom}", "diagnose_fault", True),
        ("show troubleshooting for {symptom}", "show_manual_section", True),
        ("show fault history {equipment}", "show_equipment_history", True),
        ("diagnose {fault_code}", "diagnose_fault", True),
    ]

    # Negative controls - noun-first fault queries (15)
    fault_noun_first = [
        ("{equipment} {symptom}", "none_search_only", False, "Noun-first lookup, no verb"),
        ("{brand} {equipment} fault {fault_code}", "none_search_only", False, "Noun-first with fault code"),
        ("{fault_code} {equipment}", "none_search_only", False, "Fault code first, no verb"),
        ("{equipment} alarm {fault_code}", "none_search_only", False, "Equipment alarm lookup"),
        ("{symptom} issue {equipment}", "none_search_only", False, "Symptom-first lookup"),
        ("{brand} {equipment} error", "none_search_only", False, "Brand equipment error lookup"),
        ("fault {fault_code}", "none_search_only", False, "Bare fault code lookup"),
        ("{equipment} history", "none_search_only", False, "Noun-first history lookup"),
        ("{equipment} manual {symptom}", "none_search_only", False, "Equipment manual lookup"),
        ("{brand} troubleshooting {symptom}", "none_search_only", False, "Brand troubleshooting lookup"),
        ("error {fault_code} on {equipment}", "none_search_only", False, "Error-first, no action verb"),
        ("{equipment} not working", "none_search_only", False, "Status description, no verb"),
        ("{symptom} {location}", "none_search_only", False, "Symptom at location, no verb"),
        ("{brand} alarm codes", "none_search_only", False, "Brand alarm lookup"),
        ("{equipment} problems", "none_search_only", False, "Equipment problems lookup"),
    ]

    # Polite prefix negative controls (15)
    fault_polite = [
        ("can you diagnose {fault_code}", "none_search_only", False, "Polite prefix 'can you' - not verb-first"),
        ("please show the manual for {equipment}", "none_search_only", False, "Polite prefix 'please'"),
        ("I need to diagnose {equipment} {symptom}", "none_search_only", False, "Polite 'I need to'"),
        ("could you check {fault_code}", "none_search_only", False, "Polite 'could you'"),
        ("would you show {equipment} history", "none_search_only", False, "Polite 'would you'"),
        ("help me diagnose {symptom}", "none_search_only", False, "Polite 'help me'"),
        ("I want to see {equipment} faults", "none_search_only", False, "Polite 'I want to'"),
        ("we need to check {fault_code}", "none_search_only", False, "Polite 'we need to'"),
        ("is it possible to diagnose {equipment}", "none_search_only", False, "Polite 'is it possible'"),
        ("I'd like to see {equipment} overview", "none_search_only", False, "Polite 'I'd like'"),
        ("can I check {fault_code} meaning", "none_search_only", False, "Polite 'can I'"),
        ("please diagnose why {equipment} {symptom}", "none_search_only", False, "Polite prefix"),
        ("could you trace {fault_code} causes", "none_search_only", False, "Polite prefix"),
        ("I need {equipment} predictive insight", "none_search_only", False, "Polite 'I need'"),
        ("help me understand {fault_code}", "none_search_only", False, "Polite 'help me'"),
    ]

    # Add fault seeds
    for template, action, triggers in fault_verb_first:
        seeds.append(create_seed(seed_id, template, "fault", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in fault_noun_first:
        seeds.append(create_seed(seed_id, template, "fault", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in fault_polite:
        seeds.append(create_seed(seed_id, template, "fault", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    # =========================================================================
    # CATEGORY 2: WORK ORDERS (50 seeds)
    # =========================================================================

    wo_verb_first = [
        ("create work order for {equipment} {symptom}", "create_work_order", True),
        ("create work order {equipment} needs service", "create_work_order", True),
        ("create WO for {symptom} on {equipment}", "create_work_order", True),
        ("add note to work order {equipment} repair", "add_note_to_work_order", True),
        ("attach photo to work order", "attach_photo_to_work_order", True),
        ("attach document to work order {equipment}", "attach_document_to_work_order", True),
        ("add part to work order {part}", "add_part_to_work_order", True),
        ("mark work order complete", "mark_work_order_complete", True),
        ("show tasks due today", "show_tasks_due", True),
        ("show tasks overdue", "show_tasks_overdue", True),
        ("show overdue tasks for {equipment}", "show_tasks_overdue", True),
        ("create work order from fault {fault_code}", "create_work_order_from_fault", True),
        ("mark WO complete {equipment} service", "mark_work_order_complete", True),
        ("add {part} to work order", "add_part_to_work_order", True),
        ("show tasks due this week", "show_tasks_due", True),
        ("create maintenance task for {equipment}", "create_work_order", True),
        ("attach invoice to work order", "attach_document_to_work_order", True),
        ("add note {equipment} checked ok", "add_note_to_work_order", True),
        ("show scheduled tasks {equipment}", "show_tasks_due", True),
        ("create WO {brand} {equipment} service", "create_work_order", True),
    ]

    wo_noun_first = [
        ("work order for {equipment}", "none_search_only", False, "Noun-first, no create verb"),
        ("{equipment} work orders", "none_search_only", False, "Equipment WO lookup"),
        ("tasks due today", "none_search_only", False, "Missing 'show' verb"),
        ("overdue maintenance {equipment}", "none_search_only", False, "No action verb"),
        ("{equipment} needs service", "none_search_only", False, "Status statement, no action"),
        ("pending work orders", "none_search_only", False, "Lookup, no verb"),
        ("{equipment} maintenance history", "none_search_only", False, "History lookup"),
        ("work order WO-{number}", "none_search_only", False, "WO number lookup"),
        ("{equipment} service schedule", "none_search_only", False, "Schedule lookup"),
        ("scheduled maintenance {time_range}", "none_search_only", False, "Schedule lookup"),
    ]

    wo_polite = [
        ("can you create a work order for {equipment}", "none_search_only", False, "Polite 'can you'"),
        ("please mark work order complete", "none_search_only", False, "Polite 'please'"),
        ("I need to create WO for {symptom}", "none_search_only", False, "Polite 'I need'"),
        ("could you add note to work order", "none_search_only", False, "Polite 'could you'"),
        ("we should create task for {equipment}", "none_search_only", False, "Polite 'we should'"),
        ("help me create work order", "none_search_only", False, "Polite 'help me'"),
        ("I want to add part to WO", "none_search_only", False, "Polite 'I want'"),
        ("would you show overdue tasks", "none_search_only", False, "Polite 'would you'"),
        ("please show tasks due", "none_search_only", False, "Polite 'please'"),
        ("can I create WO for {fault_code}", "none_search_only", False, "Polite 'can I'"),
    ]

    # Mixed intent work orders
    wo_mixed = [
        ("create work order and add to handover {equipment} {symptom}", ["create_work_order", "add_to_handover"], True, "medium"),
        ("create WO for {fault_code} and check stock {part}", ["create_work_order_from_fault", "check_stock_level"], True, "hard"),
        ("mark complete and export handover", ["mark_work_order_complete", "export_handover"], True, "medium"),
        ("add note and attach photo to work order", ["add_note_to_work_order", "attach_photo_to_work_order"], True, "medium"),
        ("create work order then show related documents", ["create_work_order", "show_related_documents"], True, "medium"),
    ]

    for template, action, triggers in wo_verb_first:
        seeds.append(create_seed(seed_id, template, "maintenance", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in wo_noun_first:
        seeds.append(create_seed(seed_id, template, "maintenance", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in wo_polite:
        seeds.append(create_seed(seed_id, template, "maintenance", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    for template, actions, triggers, difficulty in wo_mixed:
        seeds.append(create_seed(seed_id, template, "maintenance", "mixed_intent", actions[0], triggers, difficulty, secondary=actions[1:]))
        seed_id += 1

    # =========================================================================
    # CATEGORY 3: EQUIPMENT (40 seeds)
    # =========================================================================

    equip_verb_first = [
        ("open equipment card {equipment}", "open_equipment_card", True),
        ("open equipment card for {brand} {equipment}", "open_equipment_card", True),
        ("show all linked parts {equipment}", "show_all_linked_parts", True),
        ("show all linked faults {equipment}", "show_all_linked_faults", True),
        ("show all linked documents {equipment}", "show_all_linked_documents", True),
        ("show all linked work orders {equipment}", "show_all_linked_work_orders", True),
        ("link document to equipment {equipment}", "link_document_to_equipment", True),
        ("show linked parts for {brand} {equipment}", "show_all_linked_parts", True),
        ("show faults linked to {equipment}", "show_all_linked_faults", True),
        ("show documents for {equipment}", "show_all_linked_documents", True),
        ("open card {equipment_abbrev}", "open_equipment_card", True),
        ("show parts list {equipment}", "show_all_linked_parts", True),
        ("show fault history {equipment}", "show_all_linked_faults", True),
        ("link manual to {equipment}", "link_document_to_equipment", True),
        ("show work orders {equipment}", "show_all_linked_work_orders", True),
    ]

    equip_noun_first = [
        ("{equipment} card", "none_search_only", False, "Noun-first equipment lookup"),
        ("{brand} {equipment} parts", "none_search_only", False, "Parts lookup, no verb"),
        ("{equipment} documents", "none_search_only", False, "Documents lookup"),
        ("{equipment_abbrev} faults", "none_search_only", False, "Faults lookup"),
        ("{equipment} work orders", "none_search_only", False, "WO lookup"),
        ("{brand} {equipment} specifications", "none_search_only", False, "Specs lookup"),
        ("{equipment_abbrev} details", "none_search_only", False, "Details lookup"),
        ("{equipment} running hours", "none_search_only", False, "Hours lookup"),
        ("{brand} {equipment} serial", "none_search_only", False, "Serial lookup"),
        ("{equipment} location", "none_search_only", False, "Location lookup"),
    ]

    equip_polite = [
        ("can you open {equipment} card", "none_search_only", False, "Polite prefix"),
        ("please show {equipment} parts", "none_search_only", False, "Polite prefix"),
        ("I need to see {equipment} documents", "none_search_only", False, "Polite prefix"),
        ("could you show {equipment} faults", "none_search_only", False, "Polite prefix"),
        ("help me find {equipment} manual", "none_search_only", False, "Polite prefix"),
    ]

    for template, action, triggers in equip_verb_first:
        seeds.append(create_seed(seed_id, template, "equipment", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in equip_noun_first:
        seeds.append(create_seed(seed_id, template, "equipment", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in equip_polite:
        seeds.append(create_seed(seed_id, template, "equipment", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    # =========================================================================
    # CATEGORY 4: INVENTORY (40 seeds)
    # =========================================================================

    inv_verb_first = [
        ("check stock level {part}", "check_stock_level", True),
        ("check stock {brand} {part}", "check_stock_level", True),
        ("show storage location {part}", "show_storage_location", True),
        ("order part {part}", "order_part", True),
        ("order {number} {part}", "order_part", True),
        ("add part to handover {part}", "add_part_to_handover", True),
        ("log part usage {part}", "log_part_usage", True),
        ("scan barcode", "scan_barcode", True),
        ("check inventory {part}", "check_stock_level", True),
        ("show where {part} is stored", "show_storage_location", True),
        ("order spare {part} for {equipment}", "order_part", True),
        ("log usage {number} {part}", "log_part_usage", True),
        ("check stock {part} for {equipment}", "check_stock_level", True),
        ("show location {brand} {part}", "show_storage_location", True),
        ("add {part} to handover notes", "add_part_to_handover", True),
    ]

    inv_noun_first = [
        ("{part} stock", "none_search_only", False, "Part stock lookup"),
        ("{brand} {part} quantity", "none_search_only", False, "Quantity lookup"),
        ("{part} location", "none_search_only", False, "Location lookup"),
        ("spare parts {equipment}", "none_search_only", False, "Spares lookup"),
        ("{part} in stock", "none_search_only", False, "Stock check lookup"),
        ("{brand} filters", "none_search_only", False, "Parts lookup"),
        ("inventory {part}", "none_search_only", False, "Inventory lookup"),
        ("{part} storage", "none_search_only", False, "Storage lookup"),
        ("{equipment} spares", "none_search_only", False, "Spares lookup"),
        ("low stock items", "none_search_only", False, "Low stock lookup"),
    ]

    inv_polite = [
        ("can you check stock {part}", "none_search_only", False, "Polite prefix"),
        ("please order {part}", "none_search_only", False, "Polite prefix"),
        ("I need to check {part} quantity", "none_search_only", False, "Polite prefix"),
        ("could you show {part} location", "none_search_only", False, "Polite prefix"),
        ("help me find {part}", "none_search_only", False, "Polite prefix"),
    ]

    for template, action, triggers in inv_verb_first:
        seeds.append(create_seed(seed_id, template, "inventory", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in inv_noun_first:
        seeds.append(create_seed(seed_id, template, "inventory", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in inv_polite:
        seeds.append(create_seed(seed_id, template, "inventory", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    # =========================================================================
    # CATEGORY 5: HANDOVER (40 seeds)
    # =========================================================================

    handover_verb_first = [
        ("add to handover {equipment} {symptom}", "add_to_handover", True),
        ("add note {equipment} checked", "add_note", True),
        ("add predictive insight to handover {equipment}", "add_predictive_insight_to_handover", True),
        ("add document to handover {doc_type}", "add_document_to_handover", True),
        ("edit handover section {equipment}", "edit_handover_section", True),
        ("export handover", "export_handover", True),
        ("generate summary", "generate_summary", True),
        ("add document section to handover", "add_document_section_to_handover", True),
        ("summarise document for handover {doc_type}", "summarise_document_for_handover", True),
        ("add to handover {fault_code} on {equipment}", "add_to_handover", True),
        ("export handover PDF", "export_handover", True),
        ("generate handover summary", "generate_summary", True),
        ("add {equipment} status to handover", "add_to_handover", True),
        ("edit engine room section", "edit_handover_section", True),
        ("add note engine room all normal", "add_note", True),
    ]

    handover_noun_first = [
        ("handover {equipment}", "none_search_only", False, "Handover lookup"),
        ("handover notes", "none_search_only", False, "Notes lookup"),
        ("current handover", "none_search_only", False, "Handover lookup"),
        ("handover for {time_range}", "none_search_only", False, "Handover lookup"),
        ("{equipment} handover status", "none_search_only", False, "Status lookup"),
        ("handover items", "none_search_only", False, "Items lookup"),
        ("engine room handover", "none_search_only", False, "Section lookup"),
        ("handover summary", "none_search_only", False, "Summary lookup"),
        ("previous handover", "none_search_only", False, "Previous lookup"),
        ("handover history", "none_search_only", False, "History lookup"),
    ]

    handover_polite = [
        ("can you add to handover {equipment}", "none_search_only", False, "Polite prefix"),
        ("please export handover", "none_search_only", False, "Polite prefix"),
        ("I need to add note", "none_search_only", False, "Polite prefix"),
        ("could you generate summary", "none_search_only", False, "Polite prefix"),
        ("help me edit handover", "none_search_only", False, "Polite prefix"),
    ]

    for template, action, triggers in handover_verb_first:
        seeds.append(create_seed(seed_id, template, "handover", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in handover_noun_first:
        seeds.append(create_seed(seed_id, template, "handover", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in handover_polite:
        seeds.append(create_seed(seed_id, template, "handover", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    # =========================================================================
    # CATEGORY 6: COMPLIANCE (40 seeds)
    # =========================================================================

    compliance_verb_first = [
        ("update hours of rest", "update_hours_of_rest", True),
        ("show hours of rest", "show_hours_of_rest", True),
        ("show certificates", "show_certificates", True),
        ("show expiring certificates", "show_expiring_certificates", True),
        ("export logs", "export_logs", True),
        ("generate audit pack", "generate_audit_pack", True),
        ("add certificate", "add_certificate", True),
        ("upload certificate document", "upload_certificate_document", True),
        ("update certificate metadata", "update_certificate_metadata", True),
        ("show hours of rest {time_range}", "show_hours_of_rest", True),
        ("show certificates expiring {time_range}", "show_expiring_certificates", True),
        ("export compliance logs", "export_logs", True),
        ("update HOR {person}", "update_hours_of_rest", True),
        ("show class certificates", "show_certificates", True),
        ("generate ISM audit pack", "generate_audit_pack", True),
    ]

    compliance_noun_first = [
        ("hours of rest {person}", "none_search_only", False, "HOR lookup"),
        ("certificates expiring", "none_search_only", False, "Certificate lookup"),
        ("compliance status", "none_search_only", False, "Status lookup"),
        ("HOR {time_range}", "none_search_only", False, "HOR lookup"),
        ("audit documents", "none_search_only", False, "Audit lookup"),
        ("class certificates", "none_search_only", False, "Certificate lookup"),
        ("ISM documents", "none_search_only", False, "ISM lookup"),
        ("survey dates", "none_search_only", False, "Survey lookup"),
        ("certificate status", "none_search_only", False, "Status lookup"),
        ("compliance items", "none_search_only", False, "Items lookup"),
    ]

    compliance_polite = [
        ("can you update hours of rest", "none_search_only", False, "Polite prefix"),
        ("please show certificates", "none_search_only", False, "Polite prefix"),
        ("I need to export logs", "none_search_only", False, "Polite prefix"),
        ("could you generate audit pack", "none_search_only", False, "Polite prefix"),
        ("help me add certificate", "none_search_only", False, "Polite prefix"),
    ]

    for template, action, triggers in compliance_verb_first:
        seeds.append(create_seed(seed_id, template, "compliance", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in compliance_noun_first:
        seeds.append(create_seed(seed_id, template, "compliance", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in compliance_polite:
        seeds.append(create_seed(seed_id, template, "compliance", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    # =========================================================================
    # CATEGORY 7: DOCUMENTS (40 seeds)
    # =========================================================================

    doc_verb_first = [
        ("open document {doc_type} {equipment}", "open_document", True),
        ("open document page {number}", "open_document_page", True),
        ("search documents {equipment}", "search_documents", True),
        ("search document pages {symptom}", "search_document_pages", True),
        ("summarise document section {doc_type}", "summarise_document_section", True),
        ("upload document", "upload_document", True),
        ("delete document", "delete_document", True),
        ("archive document", "archive_document", True),
        ("replace document version", "replace_document_version", True),
        ("tag document {equipment}", "tag_document", True),
        ("link document to fault {fault_code}", "link_document_to_fault", True),
        ("compare document sections", "compare_document_sections", True),
        ("extract procedures from document", "extract_procedures_from_document", True),
        ("detect document anomalies", "detect_document_anomalies", True),
        ("search {brand} {doc_type}", "search_documents", True),
    ]

    doc_noun_first = [
        ("{brand} {doc_type}", "none_search_only", False, "Document lookup"),
        ("{equipment} manual", "none_search_only", False, "Manual lookup"),
        ("{doc_type} {equipment}", "none_search_only", False, "Document lookup"),
        ("{brand} wiring diagram", "none_search_only", False, "Diagram lookup"),
        ("{equipment} drawings", "none_search_only", False, "Drawings lookup"),
        ("schematics {equipment}", "none_search_only", False, "Schematic lookup"),
        ("{equipment} procedures", "none_search_only", False, "Procedure lookup"),
        ("{brand} parts manual", "none_search_only", False, "Parts manual lookup"),
        ("{equipment} SOP", "none_search_only", False, "SOP lookup"),
        ("P&ID {equipment}", "none_search_only", False, "P&ID lookup"),
    ]

    doc_polite = [
        ("can you open {doc_type}", "none_search_only", False, "Polite prefix"),
        ("please search documents", "none_search_only", False, "Polite prefix"),
        ("I need to upload document", "none_search_only", False, "Polite prefix"),
        ("could you summarise section", "none_search_only", False, "Polite prefix"),
        ("help me find {brand} manual", "none_search_only", False, "Polite prefix"),
    ]

    for template, action, triggers in doc_verb_first:
        seeds.append(create_seed(seed_id, template, "documents", "verb_first", action, triggers, "easy"))
        seed_id += 1

    for template, action, triggers, reason in doc_noun_first:
        seeds.append(create_seed(seed_id, template, "documents", "noun_first", action, triggers, "medium", reason))
        seed_id += 1

    for template, action, triggers, reason in doc_polite:
        seeds.append(create_seed(seed_id, template, "documents", "polite_prefix", action, triggers, "medium", reason))
        seed_id += 1

    return seeds


def create_seed(
    seed_id: int,
    template: str,
    purpose: str,
    query_form: str,
    action: str,
    triggers: bool,
    difficulty: str,
    neg_reason: str = None,
    secondary: List[str] = None
) -> Dict:
    """Create a seed template with metadata."""
    return {
        "id": seed_id,
        "template": template,
        "purpose_cluster": purpose,
        "query_form": query_form,
        "primary_action": action,
        "should_trigger": triggers,
        "difficulty": difficulty,
        "negative_control_reason": neg_reason,
        "secondary_actions": secondary or []
    }


def fill_template(template: str) -> tuple:
    """Fill a template with random domain values."""
    filled = template
    entities = []

    if "{equipment}" in filled:
        eq = random.choice(EQUIPMENT)
        filled = filled.replace("{equipment}", eq, 1)
        entities.append({"type": "equipment", "value_hint": eq, "certainty": "high"})

    if "{equipment_abbrev}" in filled:
        eq = random.choice(EQUIPMENT_ABBREV)
        filled = filled.replace("{equipment_abbrev}", eq, 1)
        entities.append({"type": "equipment", "value_hint": eq, "certainty": "high"})

    if "{brand}" in filled:
        br = random.choice(BRANDS)
        filled = filled.replace("{brand}", br, 1)
        entities.append({"type": "brand", "value_hint": br, "certainty": "high"})

    if "{part}" in filled:
        pt = random.choice(PARTS)
        filled = filled.replace("{part}", pt, 1)
        entities.append({"type": "part", "value_hint": pt, "certainty": "high"})

    if "{fault_code}" in filled:
        fc = random.choice(FAULT_CODES)
        filled = filled.replace("{fault_code}", fc, 1)
        entities.append({"type": "fault_code", "value_hint": fc, "certainty": "high"})

    if "{symptom}" in filled:
        sy = random.choice(SYMPTOMS)
        filled = filled.replace("{symptom}", sy, 1)
        entities.append({"type": "symptom", "value_hint": sy, "certainty": "high"})

    if "{location}" in filled:
        loc = random.choice(LOCATIONS)
        filled = filled.replace("{location}", loc, 1)
        entities.append({"type": "location", "value_hint": loc, "certainty": "high"})

    if "{time_range}" in filled:
        tr = random.choice(TIME_QUALIFIERS)
        filled = filled.replace("{time_range}", tr, 1)
        entities.append({"type": "time_range", "value_hint": tr, "certainty": "medium"})

    if "{measurement}" in filled:
        ms = random.choice(MEASUREMENTS)
        filled = filled.replace("{measurement}", ms, 1)
        entities.append({"type": "measurement", "value_hint": ms, "certainty": "high"})

    if "{doc_type}" in filled:
        dt = random.choice(DOC_TYPES)
        filled = filled.replace("{doc_type}", dt, 1)
        entities.append({"type": "doc_type", "value_hint": dt, "certainty": "high"})

    if "{number}" in filled:
        num = str(random.randint(1, 10))
        filled = filled.replace("{number}", num, 1)

    if "{person}" in filled:
        persons = ["chief engineer", "2nd engineer", "3rd engineer", "ETO", "bosun", "captain"]
        person = random.choice(persons)
        filled = filled.replace("{person}", person, 1)
        entities.append({"type": "person", "value_hint": person, "certainty": "medium"})

    return filled, entities


def apply_noise(query: str, noise_type: str) -> str:
    """Apply noise transformation to a query."""
    if noise_type == "clean":
        return query

    if noise_type == "typo":
        # Introduce random typos
        chars = list(query)
        if len(chars) > 5:
            idx = random.randint(2, len(chars) - 2)
            if random.random() > 0.5:
                chars[idx] = chars[idx-1]  # duplicate
            else:
                chars[idx], chars[idx+1] = chars[idx+1], chars[idx]  # swap
        return "".join(chars)

    if noise_type == "shorthand":
        replacements = {
            "work order": "WO", "main engine": "ME", "generator": "gen",
            "starboard": "stbd", "port side": "port", "engine room": "ER",
            "air conditioning": "AC", "please": "pls", "temperature": "temp"
        }
        result = query
        for full, short in replacements.items():
            result = result.replace(full, short)
        return result

    if noise_type == "punctuation":
        # Remove or add punctuation
        if random.random() > 0.5:
            return query.replace(",", "").replace(".", "")
        else:
            return query + "..."

    if noise_type == "spacing":
        if random.random() > 0.5:
            return "  ".join(query.split())  # double spaces
        else:
            words = query.split()
            if len(words) > 2:
                idx = random.randint(0, len(words) - 2)
                words[idx] = words[idx] + words[idx + 1]
                del words[idx + 1]
            return " ".join(words)

    if noise_type == "autocorrect":
        autocorrects = {
            "bilge": "bulge", "stabilizer": "stabiliser", "impeller": "impellor",
            "gauge": "gage", "thermostat": "termostat", "alternator": "alternater"
        }
        result = query
        for correct, wrong in autocorrects.items():
            if correct in result.lower() and random.random() > 0.5:
                result = result.replace(correct, wrong)
        return result

    if noise_type == "copy_paste":
        # Add artifacts from copy-paste
        artifacts = ["\n", "\t", "  ", " - ", "• "]
        return random.choice(artifacts) + query

    if noise_type == "mixed":
        # Apply multiple noise types
        result = query
        for nt in random.sample(["typo", "shorthand", "spacing"], 2):
            result = apply_noise(result, nt)
        return result

    return query


def generate_variants(seeds: List[Dict], target_count: int) -> List[Dict]:
    """Generate variants from seeds to reach target count."""
    variants = []
    variant_id = len(seeds) + 1

    noise_types = ["typo", "shorthand", "punctuation", "spacing", "autocorrect", "copy_paste", "mixed"]

    while len(variants) < target_count:
        seed = random.choice(seeds)

        # Change at least 2 dimensions
        new_noise = random.choice(noise_types)
        new_difficulty = random.choice(["medium", "hard"]) if seed["difficulty"] == "easy" else seed["difficulty"]

        # Fill template with different values
        query, entities = fill_template(seed["template"])
        query = apply_noise(query, new_noise)

        variant = {
            "id": f"Q{variant_id:04d}",
            "query": query,
            "bucket": {
                "purpose_cluster": seed["purpose_cluster"],
                "query_form": seed["query_form"],
                "noise_type": new_noise,
                "difficulty": new_difficulty
            },
            "expected": {
                "should_trigger_action": seed["should_trigger"],
                "primary_action": seed["primary_action"],
                "secondary_actions": seed["secondary_actions"],
                "expected_entities": entities,
                "must_have_tokens": [e["value_hint"] for e in entities if e["certainty"] == "high"],
                "negative_control_reason": seed.get("negative_control_reason")
            },
            "scoring": {
                "false_positive_penalty": 10,
                "false_negative_penalty": 3,
                "entity_miss_penalty": 2,
                "entity_false_positive_penalty": 1
            },
            "notes_for_humans": f"Variant of seed {seed['id']}, noise: {new_noise}"
        }

        variants.append(variant)
        variant_id += 1

    return variants


def generate_hard_cases(count: int, start_id: int) -> List[Dict]:
    """Generate hard mode test cases."""
    cases = []
    case_id = start_id

    # Hard cases with fault codes
    fault_code_cases = [
        ("diagnose SPN 100 FMI 3 on {equipment}", "diagnose_fault", True),
        ("diagnose MID 128 SID 001 {equipment}", "diagnose_fault", True),
        ("{equipment} showing {fault_code} at {measurement}", "none_search_only", False),
        ("create work order fault {fault_code} {equipment} {symptom} at {measurement}", "create_work_order_from_fault", True),
        ("{fault_code} alarm {equipment} {time_range}", "none_search_only", False),
    ]

    # Hard cases with measurements
    measurement_cases = [
        ("diagnose {equipment} running at {measurement}", "diagnose_fault", True),
        ("{equipment} {measurement} alarm", "none_search_only", False),
        ("create work order {equipment} exceeded {measurement}", "create_work_order", True),
        ("{symptom} at {measurement} {equipment}", "none_search_only", False),
    ]

    # Hard cases with locations
    location_cases = [
        ("diagnose {symptom} {location}", "diagnose_fault", True),
        ("{location} {equipment} {symptom}", "none_search_only", False),
        ("create work order {equipment} {location} {symptom}", "create_work_order", True),
        ("check {equipment} {location}", "none_search_only", False),
    ]

    # Hard cases with time qualifiers
    time_cases = [
        ("show equipment history {equipment} {time_range}", "show_equipment_history", True),
        ("{equipment} issues {time_range}", "none_search_only", False),
        ("show tasks due {time_range}", "show_tasks_due", True),
        ("faults {time_range} {equipment}", "none_search_only", False),
    ]

    # Voice dictation (messy)
    voice_cases = [
        ("um diagnose the um {equipment} its {symptom}", "diagnose_fault", True, "voice_dictation"),
        ("so like create work order for {equipment} its got {symptom}", "create_work_order", True, "voice_dictation"),
        ("hey show me the um manual for {brand} {equipment}", "none_search_only", False, "voice_dictation"),
        ("ok so {equipment} is {symptom} again", "none_search_only", False, "voice_dictation"),
    ]

    # Messy paste
    paste_cases = [
        ("From: Engineer\\nSubject: {equipment}\\n\\n{symptom} issue", "none_search_only", False, "messy_paste"),
        ("- {equipment}\\n- {symptom}\\n- {fault_code}", "none_search_only", False, "messy_paste"),
        ("diagnose fault\\n{fault_code}\\n{equipment}", "diagnose_fault", True, "messy_paste"),
        ("WO Required:\\n{equipment} {symptom}", "none_search_only", False, "messy_paste"),
    ]

    all_hard = []

    for template, action, triggers in fault_code_cases:
        all_hard.append((template, action, triggers, "clean", "Fault code case"))
    for template, action, triggers in measurement_cases:
        all_hard.append((template, action, triggers, "clean", "Measurement case"))
    for template, action, triggers in location_cases:
        all_hard.append((template, action, triggers, "clean", "Location case"))
    for template, action, triggers in time_cases:
        all_hard.append((template, action, triggers, "clean", "Time qualifier case"))
    for template, action, triggers, noise in voice_cases:
        all_hard.append((template, action, triggers, noise, "Voice dictation"))
    for template, action, triggers, noise in paste_cases:
        all_hard.append((template, action, triggers, noise, "Messy paste"))

    while len(cases) < count:
        template, action, triggers, noise, note = random.choice(all_hard)
        query, entities = fill_template(template)
        if noise != "clean":
            query = apply_noise(query, noise if noise in ["voice_dictation", "messy_paste"] else "mixed")

        case = {
            "id": f"Q{case_id:04d}",
            "query": query,
            "bucket": {
                "purpose_cluster": random.choice(["fault", "maintenance", "equipment"]),
                "query_form": "verb_first" if triggers else "noun_first",
                "noise_type": noise,
                "difficulty": "hard"
            },
            "expected": {
                "should_trigger_action": triggers,
                "primary_action": action,
                "secondary_actions": [],
                "expected_entities": entities,
                "must_have_tokens": [e["value_hint"] for e in entities if e["certainty"] == "high"],
                "negative_control_reason": None if triggers else "Hard case - complex query structure"
            },
            "scoring": {
                "false_positive_penalty": 10,
                "false_negative_penalty": 3,
                "entity_miss_penalty": 2,
                "entity_false_positive_penalty": 1
            },
            "notes_for_humans": note
        }

        cases.append(case)
        case_id += 1

    return cases


def generate_mixed_intent_cases(count: int, start_id: int) -> List[Dict]:
    """Generate mixed-intent test cases (multiple actions in one query)."""
    cases = []
    case_id = start_id

    mixed_templates = [
        # Work order + handover combinations
        ("create work order for {equipment} {symptom} and add to handover", ["create_work_order", "add_to_handover"], True),
        ("create WO {equipment} then add note to handover", ["create_work_order", "add_to_handover"], True),
        ("mark work order complete and export handover", ["mark_work_order_complete", "export_handover"], True),
        ("add note to work order and add to handover", ["add_note_to_work_order", "add_to_handover"], True),

        # Diagnosis + work order combinations
        ("diagnose {fault_code} and create work order if needed", ["diagnose_fault", "create_work_order"], True),
        ("show manual for {symptom} then create work order", ["show_manual_section", "create_work_order"], True),
        ("diagnose {equipment} {symptom} and suggest parts", ["diagnose_fault", "suggest_likely_parts"], True),

        # Inventory + work order combinations
        ("check stock {part} and add to work order", ["check_stock_level", "add_part_to_work_order"], True),
        ("order {part} and create work order for {equipment}", ["order_part", "create_work_order"], True),
        ("check inventory and add to handover if low", ["check_stock_level", "add_to_handover"], True),

        # Document + handover combinations
        ("open document {doc_type} and add section to handover", ["open_document", "add_document_section_to_handover"], True),
        ("search documents {equipment} and add to handover", ["search_documents", "add_to_handover"], True),
        ("summarise document and add to handover", ["summarise_document_section", "add_to_handover"], True),

        # Equipment + history combinations
        ("show equipment history and create work order {equipment}", ["show_equipment_history", "create_work_order"], True),
        ("open equipment card and show linked faults", ["open_equipment_card", "show_all_linked_faults"], True),

        # Compliance combinations
        ("update hours of rest and export logs", ["update_hours_of_rest", "export_logs"], True),
        ("show certificates and generate audit pack", ["show_certificates", "generate_audit_pack"], True),

        # Triple actions
        ("diagnose {fault_code} then create work order and add to handover", ["diagnose_fault", "create_work_order", "add_to_handover"], True),
        ("check stock {part} order if needed and add to work order", ["check_stock_level", "order_part", "add_part_to_work_order"], True),

        # Negative controls - mixed intent but polite prefix
        ("can you create work order and add to handover", ["create_work_order", "add_to_handover"], False),
        ("please diagnose and create work order if needed", ["diagnose_fault", "create_work_order"], False),
        ("I need to check stock and order parts", ["check_stock_level", "order_part"], False),
    ]

    while len(cases) < count:
        template, actions, triggers = random.choice(mixed_templates)
        query, entities = fill_template(template)

        case = {
            "id": f"Q{case_id:04d}",
            "query": query,
            "bucket": {
                "purpose_cluster": random.choice(["maintenance", "fault", "inventory", "handover"]),
                "query_form": "mixed_intent",
                "noise_type": random.choice(["clean", "typo", "shorthand"]),
                "difficulty": "medium"
            },
            "expected": {
                "should_trigger_action": triggers,
                "primary_action": actions[0],
                "secondary_actions": actions[1:],
                "expected_entities": entities,
                "must_have_tokens": [e["value_hint"] for e in entities if e["certainty"] == "high"],
                "negative_control_reason": None if triggers else "Mixed intent with polite prefix"
            },
            "scoring": {
                "false_positive_penalty": 10,
                "false_negative_penalty": 3,
                "entity_miss_penalty": 2,
                "entity_false_positive_penalty": 1
            },
            "notes_for_humans": f"Mixed intent: {' + '.join(actions)}"
        }

        cases.append(case)
        case_id += 1

    return cases


def generate_messy_voice_cases(count: int, start_id: int) -> List[Dict]:
    """Generate messy paste and voice dictation cases."""
    cases = []
    case_id = start_id

    # Voice dictation templates (hesitations, filler words)
    voice_templates = [
        ("um diagnose the uh {equipment} its {symptom}", "diagnose_fault", True),
        ("so like create work order for the {equipment}", "create_work_order", True),
        ("hey show me um the manual for {brand} {equipment}", "show_manual_section", True),
        ("ok so check stock on the uh {part}", "check_stock_level", True),
        ("basically add this to handover the {equipment} issue", "add_to_handover", True),
        ("right so diagnose why {equipment} is {symptom}", "diagnose_fault", True),
        ("well show me the history for um {equipment}", "show_equipment_history", True),
        ("so yeah create wo for {equipment} {symptom}", "create_work_order", True),
        ("um can you uh diagnose {fault_code}", "none_search_only", False),  # polite with hesitation
        ("so like i need to check the um {part}", "none_search_only", False),  # polite with filler
        ("basically {equipment} is {symptom} what do i do", "none_search_only", False),  # question form
    ]

    # Messy paste templates (email artifacts, bullet points, newlines)
    paste_templates = [
        ("From: Engineer\nSubject: {equipment}\n\ndiagnose {symptom}", "diagnose_fault", True),
        ("- {equipment} fault\n- create work order", "create_work_order", True),
        ("RE: {equipment}\n\nshow manual section {symptom}", "show_manual_section", True),
        ("FW: Parts needed\n\ncheck stock {part}", "check_stock_level", True),
        ("URGENT:\n{equipment} {symptom}\nadd to handover", "add_to_handover", True),
        (">>> {equipment}\n>>> {symptom}\ndiagnose this", "diagnose_fault", True),
        ("• {equipment}\n• {symptom}\n• check manual", "none_search_only", False),  # no action verb
        ("Equipment: {equipment}\nSymptom: {symptom}\nAction: ?", "none_search_only", False),
        ("Copy from log:\n{equipment} - {symptom}\n{time_range}", "none_search_only", False),
    ]

    templates = []
    for t, a, tr in voice_templates:
        templates.append((t, a, tr, "voice_dictation"))
    for t, a, tr in paste_templates:
        templates.append((t, a, tr, "messy_paste"))

    while len(cases) < count:
        template, action, triggers, noise = random.choice(templates)
        query, entities = fill_template(template)

        case = {
            "id": f"Q{case_id:04d}",
            "query": query,
            "bucket": {
                "purpose_cluster": random.choice(["fault", "maintenance", "equipment", "inventory"]),
                "query_form": "verb_first" if triggers else "fragment",
                "noise_type": noise,
                "difficulty": "hard"
            },
            "expected": {
                "should_trigger_action": triggers,
                "primary_action": action,
                "secondary_actions": [],
                "expected_entities": entities,
                "must_have_tokens": [e["value_hint"] for e in entities if e["certainty"] == "high"],
                "negative_control_reason": None if triggers else f"Messy input - {noise}"
            },
            "scoring": {
                "false_positive_penalty": 10,
                "false_negative_penalty": 3,
                "entity_miss_penalty": 2,
                "entity_false_positive_penalty": 1
            },
            "notes_for_humans": f"Messy input type: {noise}"
        }

        cases.append(case)
        case_id += 1

    return cases


def generate_dataset() -> Dict:
    """Generate the complete 1000-case dataset."""

    # Step 1: Generate 300 gold seeds
    seeds = generate_gold_seeds()
    print(f"Generated {len(seeds)} gold seeds")

    # Step 2: Convert seeds to full cases
    cases = []
    for seed in seeds:
        query, entities = fill_template(seed["template"])

        case = {
            "id": f"Q{seed['id']:04d}",
            "query": query,
            "bucket": {
                "purpose_cluster": seed["purpose_cluster"],
                "query_form": seed["query_form"],
                "noise_type": "clean",
                "difficulty": seed["difficulty"]
            },
            "expected": {
                "should_trigger_action": seed["should_trigger"],
                "primary_action": seed["primary_action"],
                "secondary_actions": seed["secondary_actions"],
                "expected_entities": entities,
                "must_have_tokens": [e["value_hint"] for e in entities if e["certainty"] == "high"],
                "negative_control_reason": seed.get("negative_control_reason")
            },
            "scoring": {
                "false_positive_penalty": 10,
                "false_negative_penalty": 3,
                "entity_miss_penalty": 2,
                "entity_false_positive_penalty": 1
            },
            "notes_for_humans": f"Gold seed {seed['id']}"
        }
        cases.append(case)

    # Step 3: Generate variants to reach ~500
    variants = generate_variants(seeds, 400)
    cases.extend(variants)
    print(f"Generated {len(variants)} variants, total: {len(cases)}")

    # Step 4: Generate hard cases
    hard_cases = generate_hard_cases(200, len(cases) + 1)
    cases.extend(hard_cases)
    print(f"Generated {len(hard_cases)} hard cases, total: {len(cases)}")

    # Step 5: Generate additional mixed-intent cases to meet target (>=120)
    mixed_cases = generate_mixed_intent_cases(100, len(cases) + 1)
    cases.extend(mixed_cases)
    print(f"Generated {len(mixed_cases)} mixed intent cases, total: {len(cases)}")

    # Step 6: Generate additional messy/voice cases to meet target (>=80)
    messy_cases = generate_messy_voice_cases(60, len(cases) + 1)
    cases.extend(messy_cases)
    print(f"Generated {len(messy_cases)} messy/voice cases, total: {len(cases)}")

    # Calculate distribution
    counts = {
        "by_purpose_cluster": {},
        "by_query_form": {},
        "by_noise_type": {},
        "by_difficulty": {},
        "negative_controls": 0,
        "verb_first_triggers": 0,
        "mixed_intent": 0,
        "messy_or_voice": 0
    }

    for case in cases:
        bucket = case["bucket"]
        expected = case["expected"]

        # Count by purpose
        pc = bucket["purpose_cluster"]
        counts["by_purpose_cluster"][pc] = counts["by_purpose_cluster"].get(pc, 0) + 1

        # Count by query form
        qf = bucket["query_form"]
        counts["by_query_form"][qf] = counts["by_query_form"].get(qf, 0) + 1

        # Count by noise
        nt = bucket["noise_type"]
        counts["by_noise_type"][nt] = counts["by_noise_type"].get(nt, 0) + 1

        # Count by difficulty
        df = bucket["difficulty"]
        counts["by_difficulty"][df] = counts["by_difficulty"].get(df, 0) + 1

        # Count special categories
        if not expected["should_trigger_action"]:
            counts["negative_controls"] += 1

        if expected["should_trigger_action"] and qf == "verb_first":
            counts["verb_first_triggers"] += 1

        if expected["secondary_actions"]:
            counts["mixed_intent"] += 1

        if nt in ["voice_dictation", "messy_paste"]:
            counts["messy_or_voice"] += 1

    # Build final dataset
    dataset = {
        "meta": {
            "dataset_name": "celesteos_microaction_entity_stress_v2",
            "total_cases": len(cases),
            "generated_at": datetime.now().isoformat(),
            "generation_rules": {
                "strict_routing_mode": True,
                "strict_routing_rule": "Only trigger should_trigger_action=true when query begins with explicit verb. Polite prefixes are negative controls.",
                "false_positive_policy": "False positives are critical failures. false_positive_penalty >= 10."
            },
            "distribution_targets": {
                "total": 1000,
                "verb_first_triggers": ">=350",
                "negative_controls": ">=250",
                "mixed_intent": ">=120",
                "messy_or_voice": ">=80",
                "hard_mode": ">=200"
            }
        },
        "cases": cases,
        "summary": {
            "counts_by_purpose_cluster": counts["by_purpose_cluster"],
            "counts_by_query_form": counts["by_query_form"],
            "counts_by_noise_type": counts["by_noise_type"],
            "counts_by_difficulty": counts["by_difficulty"],
            "negative_controls": counts["negative_controls"],
            "strict_verb_first": counts["verb_first_triggers"],
            "mixed_intent": counts["mixed_intent"],
            "messy_or_voice": counts["messy_or_voice"]
        }
    }

    return dataset


if __name__ == "__main__":
    print("=" * 70)
    print("CelesteOS Stress Test Dataset Generator V2")
    print("=" * 70)

    dataset = generate_dataset()

    # Save to file
    output_path = "stress_test_dataset_v2.json"
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"Dataset saved to: {output_path}")
    print(f"Total cases: {dataset['meta']['total_cases']}")
    print(f"\nSummary:")
    print(f"  Negative controls: {dataset['summary']['negative_controls']}")
    print(f"  Verb-first triggers: {dataset['summary']['strict_verb_first']}")
    print(f"  Mixed intent: {dataset['summary']['mixed_intent']}")
    print(f"  Messy/voice: {dataset['summary']['messy_or_voice']}")
    print(f"\nBy purpose cluster:")
    for cluster, count in sorted(dataset['summary']['counts_by_purpose_cluster'].items()):
        print(f"  {cluster}: {count}")
    print(f"\nBy query form:")
    for form, count in sorted(dataset['summary']['counts_by_query_form'].items()):
        print(f"  {form}: {count}")
    print(f"\nBy difficulty:")
    for diff, count in sorted(dataset['summary']['counts_by_difficulty'].items()):
        print(f"  {diff}: {count}")
    print("=" * 70)
