#!/usr/bin/env python3
"""
Manual Audit Pass - Human-Grade Diagnostic Review
==================================================
Processes all 1,005 stress test cases with strict routing simulation.
Outputs: annotated JSONL + final report
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# =============================================================================
# CANONICAL ACTIONS (Source of Truth)
# =============================================================================

CANONICAL_ACTIONS = [
    # Fault Diagnosis (1-10)
    "diagnose_fault", "show_manual_section", "show_related_documents",
    "show_equipment_overview", "show_equipment_history", "show_recent_state",
    "show_predictive_insight", "suggest_likely_parts", "show_similar_past_events",
    "trace_related_faults",
    # Graph/Entity Navigation (11-15)
    "trace_related_equipment", "view_linked_entities", "show_document_graph",
    "expand_fault_tree", "show_entity_timeline",
    # Work Orders (16-25)
    "create_work_order", "list_work_orders", "update_work_order", "close_work_order",
    "add_note_to_work_order", "attach_photo_to_work_order", "assign_work_order",
    "set_priority_on_work_order", "schedule_work_order", "show_work_order_history",
    # Handover (26-30)
    "add_to_handover", "view_handover", "export_handover", "edit_handover_section",
    "attach_document_to_handover",
    # Inventory (31-38)
    "check_stock", "order_parts", "add_part_to_work_order", "show_storage_location",
    "scan_barcode", "update_stock_level", "show_part_compatibility", "create_purchase_request",
    # Compliance/HOR (39-45)
    "log_hours_of_rest", "view_hours_of_rest", "show_certificate", "show_certificate_expiry",
    "export_compliance_logs", "generate_audit_prep", "submit_compliance_report",
    # Documents (46-52)
    "upload_document", "search_documents", "open_document", "attach_document",
    "show_document_metadata", "download_document", "share_document",
    # Purchasing (53-58)
    "approve_purchase_order", "track_delivery", "link_supplier", "upload_invoice",
    "compare_supplier_prices", "create_purchase_order",
    # Tasks/Checklists (59-64)
    "create_task", "show_tasks_due", "mark_task_done", "show_checklist",
    "add_checklist_item", "assign_task",
    # Reporting (65-70)
    "export_summary", "generate_report", "show_analytics", "export_work_order_history",
    "show_equipment_utilization", "show_fault_trends",
    # Fleet/Shipyard (71-75)
    "compare_fleet_equipment", "show_fleet_alerts", "log_contractor_work",
    "schedule_shipyard_task", "share_with_shipyard",
    # Utility (76-77)
    "set_reminder", "add_note",
    # Special
    "none_search_only"
]

# Verbs that trigger actions (must be at START of query)
ACTION_VERBS = {
    # Diagnosis verbs
    "diagnose": "diagnose_fault",
    "troubleshoot": "diagnose_fault",
    "investigate": "diagnose_fault",
    # Show/view verbs
    "show": None,  # Context-dependent
    "view": None,  # Context-dependent
    "display": None,
    "get": None,
    "find": None,
    "search": "search_documents",
    "lookup": None,
    "look": None,
    # Create verbs
    "create": None,  # Context-dependent
    "open": None,
    "raise": None,
    "generate": None,
    "add": None,
    # Modify verbs
    "update": None,
    "edit": None,
    "modify": None,
    "change": None,
    # Complete verbs
    "close": None,
    "complete": None,
    "finish": None,
    "mark": None,
    # Inventory verbs
    "check": None,
    "order": "order_parts",
    "scan": "scan_barcode",
    # Log/record verbs
    "log": None,
    "record": None,
    "enter": None,
    # Export verbs
    "export": None,
    "download": "download_document",
    # Attach/upload
    "attach": None,
    "upload": "upload_document",
    # Trace verbs
    "trace": None,
    "expand": None,
    # Assignment
    "assign": None,
    "schedule": None,
    "set": None,
    # Suggest/predict
    "suggest": None,
    "predict": None,
    # Approve
    "approve": "approve_purchase_order",
    "submit": None,
    # Share
    "share": None,
    # Compare
    "compare": None,
    # Track
    "track": "track_delivery",
    "link": "link_supplier",
}

# Polite prefixes that should NOT trigger actions
POLITE_PREFIXES = [
    r"^can you\b",
    r"^could you\b",
    r"^would you\b",
    r"^please\b",
    r"^i need\b",
    r"^i want\b",
    r"^we need\b",
    r"^we should\b",
    r"^help me\b",
    r"^i'd like\b",
    r"^is it possible\b",
    r"^want to\b",
]

# Entity extraction patterns
ENTITY_PATTERNS = {
    "fault_code": [
        r"\b[EePp]\d{3,4}\b",  # E047, P0420
        r"\bSPN\s*\d+(?:\s*FMI\s*\d+)?\b",  # SPN 100 FMI 3
        r"\bMID\s*\d+\s*(?:SID|PSID)\s*\d+\b",  # MID 128 SID 001
        r"\bFault\s*\d+\b",  # Fault 001
        r"\bAlarm\s*\d+\b",  # Alarm 122
        r"\bWarning\s*\d+\b",  # Warning 15
        r"\bError\s*\d+\b",  # Error 99
    ],
    "measurement": [
        r"\b\d+(?:\.\d+)?\s*(?:psi|bar|rpm|kw|hp|volts?|amps?|hz|degrees?|°[cfCF]|liters?|gallons?|hours?|mins?|seconds?)\b",
    ],
    "brand": [
        "Caterpillar", "CAT", "MTU", "Cummins", "Volvo Penta", "MAN", "Yanmar",
        "John Deere", "Kohler", "Northern Lights", "Onan", "Fischer Panda",
        "Westerbeke", "Perkins", "Scania", "Detroit Diesel", "ZF", "Twin Disc",
        "Naiad", "Quantum", "ABT Trac", "Seakeeper", "Gyro Gale", "Wesmar",
        "Side-Power", "Max Power", "Lewmar", "Lofrans", "Maxwell", "Quick",
        "Muir", "Vetus", "Victron", "Mastervolt", "Magnum", "Xantrex",
        "Outback", "Blue Sea", "Newmar", "ProMariner", "Charles", "Glendinning",
        "Dometic", "Cruisair", "Marine Air", "Webasto", "Eberspacher",
        "Spectra", "Village Marine", "Sea Recovery", "HRO", "Tecnicomar",
        "Headhunter", "Vacuflush", "Jabsco", "Raritan", "Tecma", "Sealand",
        "Racor", "Parker", "Fleetguard", "Donaldson", "Baldwin", "Mann",
        "Groco", "Shurflo", "Flojet", "Rule", "Johnson", "Whale", "Grundfos",
        "Alfa Laval", "Westfalia", "GEA", "Mitsubishi", "Panasonic", "Daikin",
        "Carrier", "Trane", "Chigo", "Midea", "Haier", "Furuno", "Raymarine",
        "Garmin", "Simrad", "B&G", "Navico", "KVH", "Intellian", "Cobham",
        "Sailor", "Iridium", "Inmarsat", "FLIR", "ACR", "Ocean Signal", "EPIRB",
        "Icom", "Standard Horizon", "Uniden", "Shakespeare", "Glomex",
        "Fusion", "JL Audio", "Bose", "Sonos", "Lutron", "Crestron",
        "AMX", "Control4", "Extron", "Kramer", "Atlona", "Maretron",
    ],
    "equipment": [
        "main engine", "generator", "genset", "alternator", "thruster",
        "bow thruster", "stern thruster", "stabilizer", "fin stabilizer",
        "gyro", "watermaker", "desalinator", "chiller", "compressor",
        "HVAC", "AC unit", "air handler", "boiler", "heater", "furnace",
        "pump", "bilge pump", "fire pump", "transfer pump", "fuel pump",
        "water pump", "hydraulic pump", "circulation pump", "raw water pump",
        "valve", "manifold", "heat exchanger", "evaporator", "condenser",
        "inverter", "charger", "battery charger", "shore power", "transformer",
        "switchboard", "panel", "breaker", "relay", "contactor", "PLC",
        "separator", "purifier", "filter", "centrifuge", "coalescer",
        "tank", "fuel tank", "water tank", "holding tank", "grey water",
        "black water", "sewage", "MSD", "heads", "toilet",
        "anchor", "windlass", "winch", "capstan", "davit", "crane",
        "radar", "GPS", "chart plotter", "autopilot", "compass", "gyrocompass",
        "VHF", "SSB", "satcom", "VSAT", "antenna", "dome",
        "camera", "CCTV", "intercom", "PA system",
        "lighting", "LED", "navigation lights", "deck lights",
        "door", "hatch", "porthole", "window", "watertight door",
        "ventilation", "exhaust", "blower", "fan", "ducting",
        "shaft", "propeller", "prop", "rudder", "steering",
        "gearbox", "transmission", "clutch", "coupling",
        "oil", "fuel", "coolant", "refrigerant", "hydraulic fluid",
        "exhaust fan", "intake", "air filter", "oil filter", "fuel filter",
    ],
    "symptom": [
        "overheating", "overheat", "hot", "high temperature",
        "low pressure", "high pressure", "pressure drop",
        "no output", "low output", "not working", "failed", "failure",
        "alarm", "warning", "error", "fault",
        "noise", "vibration", "knocking", "grinding", "squealing",
        "leak", "leaking", "dripping", "seeping",
        "smoking", "smoke", "burning smell", "burnt",
        "stuck", "seized", "frozen", "jammed",
        "intermittent", "erratic", "fluctuating", "unstable",
        "surging", "hunting", "cycling", "oscillating",
        "tripping", "cutting out", "shutting down", "shutdown",
        "stalling", "won't start", "hard start", "no start",
        "slow", "sluggish", "weak", "reduced performance",
    ],
    "location": [
        "engine room", "lazarette", "forepeak", "bow", "stern",
        "port", "starboard", "midship", "deck", "bridge",
        "galley", "salon", "cabin", "master", "guest",
        "crew quarters", "wheelhouse", "flybridge", "sundeck",
        "tender garage", "beach club", "swim platform",
    ],
    "doc_type": [
        "manual", "schematic", "diagram", "drawing",
        "procedure", "checklist", "logbook", "certificate",
        "invoice", "quote", "PO", "purchase order",
        "report", "survey", "inspection",
        "specification", "datasheet", "parts list", "BOM",
    ],
}

# =============================================================================
# ROUTER SIMULATION
# =============================================================================

def is_polite_prefix(query: str) -> bool:
    """Check if query starts with a polite prefix."""
    query_lower = query.lower().strip()
    for pattern in POLITE_PREFIXES:
        if re.match(pattern, query_lower):
            return True
    return False

def get_first_word(query: str) -> str:
    """Get the first word of a query."""
    words = query.strip().split()
    return words[0].lower() if words else ""

def detect_action_verb(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect if query starts with an action verb.
    Returns: (verb, suggested_action) or (None, None)
    """
    first_word = get_first_word(query)

    if first_word in ACTION_VERBS:
        return first_word, ACTION_VERBS.get(first_word)

    return None, None

def determine_action_from_context(query: str, verb: str) -> str:
    """Determine specific action based on query context."""
    query_lower = query.lower()

    # Show/view actions
    if verb in ["show", "view", "display", "get"]:
        if "manual" in query_lower or "troubleshoot" in query_lower:
            return "show_manual_section"
        if "history" in query_lower:
            return "show_equipment_history"
        if "related" in query_lower and "document" in query_lower:
            return "show_related_documents"
        if "related" in query_lower and "fault" in query_lower:
            return "trace_related_faults"
        if "equipment" in query_lower and "overview" in query_lower:
            return "show_equipment_overview"
        if "predictive" in query_lower or "predict" in query_lower:
            return "show_predictive_insight"
        if "recent" in query_lower or "state" in query_lower:
            return "show_recent_state"
        if "similar" in query_lower or "past event" in query_lower:
            return "show_similar_past_events"
        if "linked" in query_lower or "entities" in query_lower:
            return "view_linked_entities"
        if "graph" in query_lower:
            return "show_document_graph"
        if "work order" in query_lower or "wo" in query_lower:
            return "list_work_orders"
        if "handover" in query_lower:
            return "view_handover"
        if "stock" in query_lower or "inventory" in query_lower:
            return "check_stock"
        if "hours" in query_lower and "rest" in query_lower:
            return "view_hours_of_rest"
        if "certificate" in query_lower:
            if "expir" in query_lower:
                return "show_certificate_expiry"
            return "show_certificate"
        if "task" in query_lower:
            return "show_tasks_due"
        if "checklist" in query_lower:
            return "show_checklist"
        if "storage" in query_lower or "location" in query_lower:
            return "show_storage_location"
        if "part" in query_lower and "compatib" in query_lower:
            return "show_part_compatibility"
        if "document" in query_lower:
            return "search_documents"
        # Default for show with equipment context
        return "show_equipment_overview"

    # Create actions
    if verb in ["create", "open", "raise", "generate"]:
        if "work order" in query_lower or "wo" in query_lower:
            return "create_work_order"
        if "task" in query_lower:
            return "create_task"
        if "purchase" in query_lower:
            if "order" in query_lower:
                return "create_purchase_order"
            return "create_purchase_request"
        if "report" in query_lower:
            return "generate_report"
        if "handover" in query_lower:
            return "export_handover"

    # Add actions
    if verb == "add":
        if "handover" in query_lower:
            return "add_to_handover"
        if "note" in query_lower:
            if "work order" in query_lower:
                return "add_note_to_work_order"
            return "add_note"
        if "part" in query_lower and "work order" in query_lower:
            return "add_part_to_work_order"
        if "checklist" in query_lower:
            return "add_checklist_item"

    # Update/edit actions
    if verb in ["update", "edit", "modify"]:
        if "work order" in query_lower:
            return "update_work_order"
        if "handover" in query_lower:
            return "edit_handover_section"
        if "stock" in query_lower:
            return "update_stock_level"

    # Close/complete actions
    if verb in ["close", "complete", "finish"]:
        if "work order" in query_lower:
            return "close_work_order"

    # Mark actions
    if verb == "mark":
        if "done" in query_lower or "complete" in query_lower:
            return "mark_task_done"

    # Check actions
    if verb == "check":
        if "stock" in query_lower or "inventory" in query_lower:
            return "check_stock"

    # Log actions
    if verb in ["log", "record", "enter"]:
        if "hours" in query_lower and "rest" in query_lower:
            return "log_hours_of_rest"
        if "contractor" in query_lower:
            return "log_contractor_work"

    # Export actions
    if verb == "export":
        if "handover" in query_lower:
            return "export_handover"
        if "summary" in query_lower:
            return "export_summary"
        if "compliance" in query_lower or "log" in query_lower:
            return "export_compliance_logs"
        if "work order" in query_lower:
            return "export_work_order_history"

    # Attach actions
    if verb == "attach":
        if "photo" in query_lower:
            return "attach_photo_to_work_order"
        if "document" in query_lower:
            if "handover" in query_lower:
                return "attach_document_to_handover"
            return "attach_document"

    # Trace actions
    if verb == "trace":
        if "equipment" in query_lower:
            return "trace_related_equipment"
        if "fault" in query_lower:
            return "trace_related_faults"

    # Expand actions
    if verb == "expand":
        if "fault" in query_lower or "tree" in query_lower:
            return "expand_fault_tree"

    # Suggest actions
    if verb == "suggest":
        if "part" in query_lower:
            return "suggest_likely_parts"

    # Assign/schedule actions
    if verb == "assign":
        if "work order" in query_lower:
            return "assign_work_order"
        if "task" in query_lower:
            return "assign_task"

    if verb == "schedule":
        if "work order" in query_lower:
            return "schedule_work_order"
        if "shipyard" in query_lower:
            return "schedule_shipyard_task"

    # Set actions
    if verb == "set":
        if "priority" in query_lower:
            return "set_priority_on_work_order"
        if "reminder" in query_lower:
            return "set_reminder"

    # Compare actions
    if verb == "compare":
        if "fleet" in query_lower:
            return "compare_fleet_equipment"
        if "supplier" in query_lower or "price" in query_lower:
            return "compare_supplier_prices"

    # Share actions
    if verb == "share":
        if "shipyard" in query_lower:
            return "share_with_shipyard"
        return "share_document"

    # Submit actions
    if verb == "submit":
        if "compliance" in query_lower or "report" in query_lower:
            return "submit_compliance_report"

    return "none_search_only"

def simulate_router(query: str) -> Dict:
    """
    Simulate strict routing logic.
    Returns router judgement dict.
    """
    query_stripped = query.strip()

    # Check for polite prefix first
    if is_polite_prefix(query_stripped):
        return {
            "should_trigger_action": False,
            "predicted_primary_action": "none_search_only",
            "predicted_action_confidence": 0.95,
            "matched_verb": None,
            "match_rationale": "Polite prefix detected - negative control",
            "false_positive_risk": "low"
        }

    # Check for action verb at start
    verb, default_action = detect_action_verb(query_stripped)

    if verb:
        # Determine specific action from context
        action = default_action if default_action else determine_action_from_context(query_stripped, verb)

        if action == "none_search_only":
            return {
                "should_trigger_action": False,
                "predicted_primary_action": "none_search_only",
                "predicted_action_confidence": 0.7,
                "matched_verb": verb,
                "match_rationale": f"Verb '{verb}' found but no clear action context",
                "false_positive_risk": "medium"
            }

        return {
            "should_trigger_action": True,
            "predicted_primary_action": action,
            "predicted_action_confidence": 0.9,
            "matched_verb": verb,
            "match_rationale": f"Verb '{verb}' at start triggers '{action}'",
            "false_positive_risk": "low"
        }

    # No verb at start - should be search only
    first_word = get_first_word(query_stripped)
    return {
        "should_trigger_action": False,
        "predicted_primary_action": "none_search_only",
        "predicted_action_confidence": 0.95,
        "matched_verb": None,
        "match_rationale": f"No action verb at start ('{first_word}' is not a trigger verb)",
        "false_positive_risk": "low"
    }

# =============================================================================
# ENTITY EXTRACTION
# =============================================================================

def extract_entities(query: str) -> List[Dict]:
    """Extract entities from query."""
    entities = []
    query_lower = query.lower()

    # Extract fault codes
    for pattern in ENTITY_PATTERNS["fault_code"]:
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "fault_code",
                "raw_value": match.group(),
                "canonical_suggestion": match.group().upper(),
                "canonical_confidence": 0.95,
                "term_type": "code",
                "evidence": match.group(),
                "extraction_confidence": 0.95,
                "weight": 95,
                "notes": None
            })

    # Extract measurements
    for pattern in ENTITY_PATTERNS["measurement"]:
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "measurement",
                "raw_value": match.group(),
                "canonical_suggestion": None,
                "canonical_confidence": 0.0,
                "term_type": "unit_value",
                "evidence": match.group(),
                "extraction_confidence": 0.85,
                "weight": 60,
                "notes": None
            })

    # Extract brands
    for brand in ENTITY_PATTERNS["brand"]:
        pattern = r"\b" + re.escape(brand) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "brand",
                "raw_value": match.group(),
                "canonical_suggestion": brand,
                "canonical_confidence": 0.9,
                "term_type": "model",
                "evidence": match.group(),
                "extraction_confidence": 0.9,
                "weight": 85,
                "notes": None
            })

    # Extract equipment
    for equip in ENTITY_PATTERNS["equipment"]:
        pattern = r"\b" + re.escape(equip) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "equipment",
                "raw_value": match.group(),
                "canonical_suggestion": equip.lower(),
                "canonical_confidence": 0.85,
                "term_type": "component",
                "evidence": match.group(),
                "extraction_confidence": 0.85,
                "weight": 80,
                "notes": None
            })

    # Extract symptoms
    for symptom in ENTITY_PATTERNS["symptom"]:
        pattern = r"\b" + re.escape(symptom) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "symptom",
                "raw_value": match.group(),
                "canonical_suggestion": symptom.lower(),
                "canonical_confidence": 0.8,
                "term_type": "other",
                "evidence": match.group(),
                "extraction_confidence": 0.8,
                "weight": 70,
                "notes": None
            })

    # Extract locations
    for loc in ENTITY_PATTERNS["location"]:
        pattern = r"\b" + re.escape(loc) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "location",
                "raw_value": match.group(),
                "canonical_suggestion": loc.lower(),
                "canonical_confidence": 0.85,
                "term_type": "location",
                "evidence": match.group(),
                "extraction_confidence": 0.85,
                "weight": 65,
                "notes": None
            })

    # Extract doc types
    for doc in ENTITY_PATTERNS["doc_type"]:
        pattern = r"\b" + re.escape(doc) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "doc_type",
                "raw_value": match.group(),
                "canonical_suggestion": doc.lower(),
                "canonical_confidence": 0.9,
                "term_type": "doc_phrase",
                "evidence": match.group(),
                "extraction_confidence": 0.9,
                "weight": 75,
                "notes": None
            })

    # Deduplicate by evidence
    seen = set()
    unique_entities = []
    for e in entities:
        key = (e["type"], e["evidence"].lower())
        if key not in seen:
            seen.add(key)
            unique_entities.append(e)

    return unique_entities

# =============================================================================
# INTENT CLASSIFICATION
# =============================================================================

def classify_intent(query: str, entities: List[Dict]) -> Dict:
    """Classify query intent."""
    query_lower = query.lower()

    # Check entity types for hints
    has_fault = any(e["type"] == "fault_code" for e in entities)
    has_symptom = any(e["type"] == "symptom" for e in entities)
    has_equipment = any(e["type"] == "equipment" for e in entities)
    has_part = any(e["type"] == "part" for e in entities)
    has_doc = any(e["type"] == "doc_type" for e in entities)

    # Keyword-based classification
    if has_fault or has_symptom or "diagnose" in query_lower or "troubleshoot" in query_lower:
        return {
            "primary_intent": "fault",
            "secondary_intents": ["maintenance"] if "maintenance" in query_lower else [],
            "intent_confidence": 0.9,
            "why": "Fault code or symptom present, or diagnosis verb"
        }

    if "work order" in query_lower or "wo" in query_lower or "task" in query_lower:
        return {
            "primary_intent": "maintenance",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Work order or task keywords"
        }

    if "handover" in query_lower:
        return {
            "primary_intent": "handover",
            "secondary_intents": [],
            "intent_confidence": 0.95,
            "why": "Handover keyword"
        }

    if "stock" in query_lower or "inventory" in query_lower or "order" in query_lower or has_part:
        return {
            "primary_intent": "inventory",
            "secondary_intents": [],
            "intent_confidence": 0.85,
            "why": "Inventory/stock keywords or part entity"
        }

    if "hours" in query_lower and "rest" in query_lower:
        return {
            "primary_intent": "compliance",
            "secondary_intents": [],
            "intent_confidence": 0.95,
            "why": "Hours of rest keywords"
        }

    if "certificate" in query_lower or "compliance" in query_lower or "audit" in query_lower:
        return {
            "primary_intent": "compliance",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Compliance/certificate keywords"
        }

    if has_doc or "manual" in query_lower or "document" in query_lower or "schematic" in query_lower:
        return {
            "primary_intent": "documents",
            "secondary_intents": [],
            "intent_confidence": 0.85,
            "why": "Document type entity or document keywords"
        }

    if "purchase" in query_lower or "supplier" in query_lower or "invoice" in query_lower:
        return {
            "primary_intent": "purchasing",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Purchasing keywords"
        }

    if "checklist" in query_lower:
        return {
            "primary_intent": "checklists",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Checklist keyword"
        }

    if "shipyard" in query_lower or "contractor" in query_lower:
        return {
            "primary_intent": "shipyard",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Shipyard/contractor keywords"
        }

    if "fleet" in query_lower:
        return {
            "primary_intent": "fleet",
            "secondary_intents": [],
            "intent_confidence": 0.9,
            "why": "Fleet keyword"
        }

    if has_equipment:
        return {
            "primary_intent": "equipment",
            "secondary_intents": [],
            "intent_confidence": 0.75,
            "why": "Equipment entity present"
        }

    return {
        "primary_intent": "general",
        "secondary_intents": [],
        "intent_confidence": 0.5,
        "why": "No clear intent indicators"
    }

# =============================================================================
# MAIN AUDIT FUNCTION
# =============================================================================

def audit_case(case: Dict) -> Dict:
    """Audit a single case and return annotated judgement."""
    query = case["query"]
    expected = case["expected"]
    bucket = case["bucket"]

    # Simulate router
    router_result = simulate_router(query)

    # Extract entities
    entities = extract_entities(query)

    # Classify intent
    intent = classify_intent(query, entities)

    # Determine scoring outcome
    exp_trigger = expected["should_trigger_action"]
    pred_trigger = router_result["should_trigger_action"]

    is_false_positive = (not exp_trigger) and pred_trigger
    is_false_negative = exp_trigger and (not pred_trigger)

    # Calculate entity metrics
    expected_entities = expected.get("expected_entities", [])
    expected_values = {e.get("value_hint", "").lower() for e in expected_entities}
    extracted_values = {e["raw_value"].lower() for e in entities}

    entity_hits = len(expected_values & extracted_values)
    entity_misses = len(expected_values - extracted_values)
    entity_fps = 0  # We don't penalize extra entities heavily

    # Calculate penalty
    penalty = 0
    failure_tags = []

    if is_false_positive:
        penalty += 10
        if bucket["query_form"] == "polite_prefix":
            failure_tags.append("polite_prefix_trap")
        elif bucket["query_form"] == "noun_first":
            failure_tags.append("noun_only_should_not_trigger")
        else:
            failure_tags.append("verb_prefix_mismatch")

    if is_false_negative:
        penalty += 3
        failure_tags.append("verb_prefix_mismatch")

    if expected["primary_action"] != router_result["predicted_primary_action"]:
        if exp_trigger and pred_trigger:
            failure_tags.append("action_collision")

    penalty += entity_misses * 2

    # Build search profile
    search_profile = {
        "original_query_form": bucket["query_form"],
        "noise_type": bucket["noise_type"],
        "difficulty": bucket["difficulty"],
        "must_have_tokens": expected.get("must_have_tokens", []),
        "should_add_to_new_terms": []
    }

    # Build full result
    result = {
        "id": case["id"],
        "query": query,
        "expected": expected,
        "manual_judgement": {
            "router": router_result,
            "intent": intent,
            "entities": entities,
            "search_profile": search_profile
        },
        "scoring_outcome": {
            "is_false_positive": is_false_positive,
            "is_false_negative": is_false_negative,
            "entity_misses": entity_misses,
            "entity_false_positives": entity_fps,
            "penalty_points": penalty,
            "failure_mode_tags": failure_tags
        }
    }

    return result

def run_full_audit(dataset_path: str, output_path: str):
    """Run full audit on dataset."""
    with open(dataset_path) as f:
        dataset = json.load(f)

    cases = dataset["cases"]
    results = []

    # Metrics tracking
    tp = fp = fn = tn = 0
    action_confusion = defaultdict(lambda: defaultdict(int))
    failure_mode_counts = defaultdict(int)
    total_entity_misses = 0
    total_expected_entities = 0

    print(f"Auditing {len(cases)} cases...")

    with open(output_path, 'w') as out:
        for i, case in enumerate(cases):
            result = audit_case(case)
            results.append(result)

            # Write JSONL
            out.write(json.dumps(result) + "\n")

            # Update metrics
            exp_trigger = case["expected"]["should_trigger_action"]
            pred_trigger = result["manual_judgement"]["router"]["should_trigger_action"]

            if exp_trigger and pred_trigger:
                tp += 1
            elif not exp_trigger and not pred_trigger:
                tn += 1
            elif not exp_trigger and pred_trigger:
                fp += 1
            else:
                fn += 1

            # Action confusion
            exp_action = case["expected"]["primary_action"]
            pred_action = result["manual_judgement"]["router"]["predicted_primary_action"]
            action_confusion[exp_action][pred_action] += 1

            # Failure modes
            for tag in result["scoring_outcome"]["failure_mode_tags"]:
                failure_mode_counts[tag] += 1

            # Entity metrics
            total_entity_misses += result["scoring_outcome"]["entity_misses"]
            total_expected_entities += len(case["expected"].get("expected_entities", []))

            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(cases)}")

    print(f"\nAudit complete. Results written to {output_path}")

    # Return metrics for report
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "action_confusion": dict(action_confusion),
        "failure_mode_counts": dict(failure_mode_counts),
        "total_entity_misses": total_entity_misses,
        "total_expected_entities": total_expected_entities,
        "total_cases": len(cases)
    }

if __name__ == "__main__":
    metrics = run_full_audit("stress_test_dataset_v2.json", "manual_audit_results.jsonl")

    # Print summary metrics
    print("\n" + "="*70)
    print("AUDIT METRICS SUMMARY")
    print("="*70)

    total = metrics["tp"] + metrics["fp"] + metrics["fn"] + metrics["tn"]
    print(f"\nTRIGGER CLASSIFICATION:")
    print(f"  True Positives:  {metrics['tp']}")
    print(f"  True Negatives:  {metrics['tn']}")
    print(f"  False Positives: {metrics['fp']} (CRITICAL)")
    print(f"  False Negatives: {metrics['fn']}")
    print(f"  Precision: {metrics['tp'] / max(metrics['tp'] + metrics['fp'], 1):.2%}")
    print(f"  Recall:    {metrics['tp'] / max(metrics['tp'] + metrics['fn'], 1):.2%}")

    print(f"\nENTITY EXTRACTION:")
    print(f"  Expected Entities: {metrics['total_expected_entities']}")
    print(f"  Misses: {metrics['total_entity_misses']}")
    hit_rate = 1 - (metrics['total_entity_misses'] / max(metrics['total_expected_entities'], 1))
    print(f"  Hit Rate: {hit_rate:.2%}")

    print(f"\nFAILURE MODES:")
    for mode, count in sorted(metrics["failure_mode_counts"].items(), key=lambda x: -x[1]):
        print(f"  {mode}: {count}")

    # Save metrics
    with open("manual_audit_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nMetrics saved to manual_audit_metrics.json")
