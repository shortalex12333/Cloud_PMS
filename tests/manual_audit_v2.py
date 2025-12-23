#!/usr/bin/env python3
"""
Manual Audit V2 - With Canonical Action Resolution
===================================================
Uses canonical_action_registry for action normalization.
Implements strict routing with proper verb detection.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from canonical_action_registry import (
    CANONICAL_ACTIONS,
    canonicalize_action,
    resolve_verb_action,
    has_polite_prefix,
    STRICT_TRIGGER_VERBS,
)

# =============================================================================
# HARD FP vs SOFT MISROUTE SCORING FRAMEWORK
# =============================================================================

# State-changing actions (Hard FP if triggered incorrectly)
STATE_CHANGING_ACTIONS = frozenset([
    # Work Orders
    "create_work_order", "update_work_order", "close_work_order",
    "add_note_to_work_order", "attach_photo_to_work_order",
    "assign_work_order", "set_priority_on_work_order", "schedule_work_order",

    # Inventory mutations
    "order_part", "add_part_to_work_order", "update_stock_level",
    "create_purchase_request", "reserve_part",

    # Compliance mutations
    "log_hours_of_rest", "submit_compliance_report",
    "upload_certificate_document",

    # Document mutations
    "upload_document", "attach_document_to_work_order",
    "archive_document", "share_document",

    # Handover mutations
    "add_to_handover", "edit_handover_section",
    "attach_document_to_handover",

    # Tasks/Checklists
    "create_task", "mark_work_order_complete", "add_checklist_item", "assign_task",

    # Purchasing
    "approve_purchase_order", "create_purchase_order", "upload_invoice",

    # Misc mutations
    "set_reminder", "add_note", "link_document_to_equipment",
    "update_certificate_metadata", "log_contractor_work",
])

# Read-only actions (Soft misroute if wrong one triggered)
READ_ONLY_ACTIONS = frozenset([
    # Diagnosis/Display
    "diagnose_fault", "show_manual_section", "show_related_documents",
    "show_equipment_overview", "show_equipment_history", "show_recent_state",
    "show_predictive_insight", "suggest_likely_parts", "show_similar_past_events",
    "trace_related_faults", "trace_related_equipment", "view_linked_entities",
    "show_document_graph", "expand_fault_tree", "show_entity_timeline",

    # Lists/Views
    "list_work_orders", "view_handover", "show_work_order_history",

    # Inventory reads
    "check_stock_level", "show_storage_location", "scan_barcode",
    "show_part_compatibility", "show_low_stock_alerts",

    # Compliance reads
    "show_hours_of_rest", "show_certificates", "show_certificate_expiry",
    "generate_audit_pack",

    # Documents reads
    "search_documents", "open_document", "show_document_metadata",
    "download_document",

    # Tasks reads
    "show_tasks_due", "show_checklist",

    # Reporting (read-only exports)
    "export_summary", "generate_summary", "show_analytics",
    "export_work_order_history", "show_equipment_utilization", "show_fault_trends",
    "export_handover", "export_compliance_logs",

    # Fleet reads
    "compare_fleet_equipment", "show_fleet_alerts", "compare_supplier_prices",
    "track_delivery",

    # Special
    "open_equipment_card", "detect_anomaly", "none_search_only",
])


def classify_fp_severity(expected_action: str, predicted_action: str, exp_trigger: bool, pred_trigger: bool) -> dict:
    """
    Classify false positive severity.

    Returns:
        {
            "is_hard_fp": bool,      # State-changing action triggered incorrectly
            "is_soft_misroute": bool, # Wrong read-only action triggered
            "severity_score": int,    # 10 for hard FP, 3 for soft misroute
            "category": str          # "hard_fp", "soft_misroute", "correct", "fn"
        }
    """
    # Not a false positive
    if not ((not exp_trigger) and pred_trigger):
        if exp_trigger and not pred_trigger:
            return {"is_hard_fp": False, "is_soft_misroute": False, "severity_score": 3, "category": "fn"}
        return {"is_hard_fp": False, "is_soft_misroute": False, "severity_score": 0, "category": "correct"}

    # It IS a false positive - classify severity
    if predicted_action in STATE_CHANGING_ACTIONS:
        return {
            "is_hard_fp": True,
            "is_soft_misroute": False,
            "severity_score": 10,
            "category": "hard_fp"
        }
    elif predicted_action in READ_ONLY_ACTIONS:
        return {
            "is_hard_fp": False,
            "is_soft_misroute": True,
            "severity_score": 3,
            "category": "soft_misroute"
        }
    else:
        # Unknown action - treat as hard FP to be safe
        return {
            "is_hard_fp": True,
            "is_soft_misroute": False,
            "severity_score": 10,
            "category": "hard_fp"
        }

# =============================================================================
# ENTITY EXTRACTION PATTERNS
# =============================================================================

ENTITY_PATTERNS = {
    "fault_code": [
        r"\b[EePp]\d{3,4}\b",
        r"\bSPN\s*\d+(?:\s*FMI\s*\d+)?\b",
        r"\bMID\s*\d+\s*(?:SID|PSID)\s*\d+\b",
        r"\bFault\s*\d+\b",
        r"\bAlarm\s*\d+\b",
        r"\bWarning\s*\d+\b",
        r"\bError\s*\d+\b",
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
        "Alfa Laval", "Westfalia", "GEA", "Furuno", "Raymarine", "Garmin",
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
        "tank", "fuel tank", "water tank", "holding tank",
        "anchor", "windlass", "winch", "capstan", "davit", "crane",
        "radar", "GPS", "chart plotter", "autopilot", "compass",
        "VHF", "SSB", "satcom", "VSAT", "antenna",
        "exhaust fan", "ventilation", "blower", "fan",
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
    ],
}

# =============================================================================
# STRICT ROUTER SIMULATION
# =============================================================================

def get_first_token(query: str) -> str:
    """Extract first token, handling noise."""
    query = query.strip()

    # Skip common noise prefixes (expanded for voice dictation, email, forum)
    noise_patterns = [
        r"^[-•►→»*–—]\s*",        # Bullet points (various styles)
        r"^>{1,3}\s*",            # Quote markers (>, >>, >>>)
        r"^\d+[.)]\s*",           # Numbered lists
        r"^(fw:|re:|fwd:|from:)\s*.*?\n*",  # Email prefixes (may have newlines)
        r"^(um|uh|er|ah)\s+",     # Hesitation sounds
        r"^(ok|okay|so|right|well|yeah|yep|sure|alright)\s+",  # Filler/confirmation words
        r"^(basically|actually|literally|honestly|like)\s+",  # Hedge words
        r"^hey\s+",               # Casual opener
        r"^hi\s+",                # Greeting opener
        r"^yo\s+",                # Informal opener
        r"^the\s+",               # Accidental article prefix
        r"^noise_\w+\s+",         # Test noise markers (from suite generator)
    ]

    for pattern in noise_patterns:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE)

    words = query.strip().split()
    return words[0].lower() if words else ""


def simulate_strict_router(query: str) -> Dict:
    """
    Simulate strict routing with proper verb detection.

    Strict Mode Rules:
    1. Check for polite prefix first → none_search_only
    2. First token must be a recognized verb → trigger action
    3. Otherwise → none_search_only
    """
    query_stripped = query.strip()

    # Rule 1: Polite prefix = negative control
    if has_polite_prefix(query_stripped):
        return {
            "should_trigger_action": False,
            "predicted_primary_action": "none_search_only",
            "predicted_action_confidence": 0.98,
            "matched_verb": None,
            "match_rationale": "Polite prefix detected - strict mode rejects",
            "false_positive_risk": "low"
        }

    # Get first meaningful token
    first_token = get_first_token(query_stripped)

    # Rule 2: Check if first token is a trigger verb
    if first_token in STRICT_TRIGGER_VERBS:
        # Resolve action based on verb + context
        action = resolve_verb_action(first_token, query_stripped)
        canonical_action = canonicalize_action(action)

        # Context-dependent verbs may resolve to none_search_only
        # (e.g., "check generator compartment" without stock/inventory context)
        if canonical_action == "none_search_only":
            return {
                "should_trigger_action": False,
                "predicted_primary_action": "none_search_only",
                "predicted_action_confidence": 0.92,
                "matched_verb": first_token,
                "match_rationale": f"Verb '{first_token}' requires context (e.g., stock/inventory) - no match",
                "false_positive_risk": "low"
            }

        return {
            "should_trigger_action": True,
            "predicted_primary_action": canonical_action,
            "predicted_action_confidence": 0.90,
            "matched_verb": first_token,
            "match_rationale": f"Verb '{first_token}' at position 0 triggers '{canonical_action}'",
            "false_positive_risk": "low"
        }

    # Rule 3: No verb at start = search only
    return {
        "should_trigger_action": False,
        "predicted_primary_action": "none_search_only",
        "predicted_action_confidence": 0.95,
        "matched_verb": None,
        "match_rationale": f"First token '{first_token}' is not a trigger verb",
        "false_positive_risk": "low"
    }


# =============================================================================
# ENTITY EXTRACTION
# =============================================================================

def extract_entities(query: str) -> List[Dict]:
    """Extract entities from query."""
    entities = []

    for pattern in ENTITY_PATTERNS["fault_code"]:
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "fault_code",
                "raw_value": match.group(),
                "evidence": match.group(),
                "extraction_confidence": 0.95,
                "weight": 95,
            })

    for brand in ENTITY_PATTERNS["brand"]:
        pattern = r"\b" + re.escape(brand) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "brand",
                "raw_value": match.group(),
                "evidence": match.group(),
                "extraction_confidence": 0.90,
                "weight": 85,
            })

    for equip in ENTITY_PATTERNS["equipment"]:
        pattern = r"\b" + re.escape(equip) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "equipment",
                "raw_value": match.group(),
                "evidence": match.group(),
                "extraction_confidence": 0.85,
                "weight": 80,
            })

    for symptom in ENTITY_PATTERNS["symptom"]:
        pattern = r"\b" + re.escape(symptom) + r"\b"
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entities.append({
                "type": "symptom",
                "raw_value": match.group(),
                "evidence": match.group(),
                "extraction_confidence": 0.80,
                "weight": 70,
            })

    # Deduplicate
    seen = set()
    unique = []
    for e in entities:
        key = (e["type"], e["evidence"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


# =============================================================================
# MAIN AUDIT
# =============================================================================

def audit_case(case: Dict) -> Dict:
    """Audit a single case with canonical resolution."""
    query = case["query"]
    expected = case["expected"]
    bucket = case["bucket"]

    # Simulate strict router
    router_result = simulate_strict_router(query)

    # Canonicalize expected action for fair comparison
    expected_action_raw = expected["primary_action"]
    expected_action_canonical = canonicalize_action(expected_action_raw)

    # Extract entities
    entities = extract_entities(query)

    # Scoring
    exp_trigger = expected["should_trigger_action"]
    pred_trigger = router_result["should_trigger_action"]
    pred_action = router_result["predicted_primary_action"]

    is_false_positive = (not exp_trigger) and pred_trigger
    is_false_negative = exp_trigger and (not pred_trigger)

    # Check action match (using canonical forms)
    action_match = (expected_action_canonical == pred_action)

    # Entity metrics
    expected_entities = expected.get("expected_entities", [])
    expected_values = {e.get("value_hint", "").lower() for e in expected_entities}
    extracted_values = {e["raw_value"].lower() for e in entities}
    entity_misses = len(expected_values - extracted_values)

    # Classify FP severity using new framework
    severity = classify_fp_severity(expected_action_canonical, pred_action, exp_trigger, pred_trigger)

    # Failure tags
    failure_tags = []
    penalty = 0

    if is_false_positive:
        # Use severity-based penalty (Hard FP = 10, Soft Misroute = 3)
        penalty += severity["severity_score"]
        if severity["is_hard_fp"]:
            failure_tags.append("hard_fp_state_change")
        elif severity["is_soft_misroute"]:
            failure_tags.append("soft_misroute_read_only")

        # Also tag by query form for analysis
        if bucket["query_form"] == "polite_prefix":
            failure_tags.append("polite_prefix_trap")
        elif bucket["query_form"] == "noun_first":
            failure_tags.append("noun_only_should_not_trigger")
        else:
            failure_tags.append("verb_prefix_mismatch")

    if is_false_negative:
        penalty += 3
        failure_tags.append("verb_prefix_mismatch")

    if exp_trigger and pred_trigger and not action_match:
        failure_tags.append("action_collision")

    penalty += entity_misses * 2

    return {
        "id": case["id"],
        "query": query,
        "expected": {
            "should_trigger_action": exp_trigger,
            "primary_action": expected_action_raw,
            "primary_action_canonical": expected_action_canonical,
        },
        "manual_judgement": {
            "router": router_result,
            "entities": entities,
        },
        "scoring_outcome": {
            "is_false_positive": is_false_positive,
            "is_false_negative": is_false_negative,
            "fp_severity": severity,  # NEW: Hard FP vs Soft Misroute classification
            "action_match": action_match,
            "entity_misses": entity_misses,
            "penalty_points": penalty,
            "failure_mode_tags": failure_tags,
        }
    }


def run_audit(dataset_path: str, output_path: str):
    """Run full audit with canonical resolution and severity scoring."""
    with open(dataset_path) as f:
        dataset = json.load(f)

    cases = dataset["cases"]

    # Metrics
    tp = fp = fn = tn = 0
    action_matches = 0
    action_collisions = 0
    total_entity_misses = 0
    total_expected_entities = 0
    failure_mode_counts = defaultdict(int)

    # NEW: Hard FP vs Soft Misroute tracking
    hard_fp_count = 0
    soft_misroute_count = 0
    hard_fp_cases = []
    soft_misroute_cases = []

    print(f"Auditing {len(cases)} cases with canonical resolution + severity scoring...")

    with open(output_path, 'w') as out:
        for i, case in enumerate(cases):
            result = audit_case(case)
            out.write(json.dumps(result) + "\n")

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

            if result["scoring_outcome"]["action_match"]:
                action_matches += 1

            if "action_collision" in result["scoring_outcome"]["failure_mode_tags"]:
                action_collisions += 1

            total_entity_misses += result["scoring_outcome"]["entity_misses"]
            total_expected_entities += len(case["expected"].get("expected_entities", []))

            for tag in result["scoring_outcome"]["failure_mode_tags"]:
                failure_mode_counts[tag] += 1

            # Track Hard FP vs Soft Misroute
            fp_severity = result["scoring_outcome"]["fp_severity"]
            if fp_severity["is_hard_fp"]:
                hard_fp_count += 1
                hard_fp_cases.append({
                    "id": result["id"],
                    "query": result["query"][:60],
                    "predicted_action": result["manual_judgement"]["router"]["predicted_primary_action"]
                })
            elif fp_severity["is_soft_misroute"]:
                soft_misroute_count += 1
                soft_misroute_cases.append({
                    "id": result["id"],
                    "query": result["query"][:60],
                    "predicted_action": result["manual_judgement"]["router"]["predicted_primary_action"]
                })

            if (i + 1) % 200 == 0:
                print(f"  Processed {i + 1}/{len(cases)}")

    # Calculate metrics
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)
    entity_hit_rate = 1 - (total_entity_misses / max(total_expected_entities, 1))

    metrics = {
        "total_cases": len(cases),
        "trigger_classification": {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "fp_severity_breakdown": {
            "hard_fp_count": hard_fp_count,
            "soft_misroute_count": soft_misroute_count,
            "hard_fp_rate": round(hard_fp_count / max(fp, 1), 4),
            "hard_fp_cases": hard_fp_cases[:10],  # Top 10 for inspection
            "soft_misroute_cases": soft_misroute_cases[:10],
        },
        "action_detection": {
            "action_matches": action_matches,
            "action_collisions": action_collisions,
            "action_accuracy": round(action_matches / max(tp, 1), 4),
        },
        "entity_extraction": {
            "total_expected": total_expected_entities,
            "total_misses": total_entity_misses,
            "hit_rate": round(entity_hit_rate, 4),
        },
        "failure_modes": dict(failure_mode_counts),
    }

    with open("manual_audit_v3_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT V3 SUMMARY (with severity scoring)")
    print("=" * 70)
    print(f"""
TRIGGER CLASSIFICATION:
  TP: {tp}  FP: {fp}  FN: {fn}  TN: {tn}
  Precision: {precision:.2%}
  Recall:    {recall:.2%}
  F1:        {f1:.2%}

FALSE POSITIVE SEVERITY (NEW):
  Hard FP (state-changing):  {hard_fp_count}
  Soft Misroute (read-only): {soft_misroute_count}
  Hard FP Rate: {hard_fp_count / max(fp, 1):.2%} of all FPs

ACTION DETECTION (after canonicalization):
  Matches:    {action_matches} / {tp} = {action_matches / max(tp, 1):.2%}
  Collisions: {action_collisions}

ENTITY EXTRACTION:
  Hit Rate: {entity_hit_rate:.2%} ({total_expected_entities - total_entity_misses}/{total_expected_entities})

FAILURE MODES:
""")
    for mode, count in sorted(failure_mode_counts.items(), key=lambda x: -x[1]):
        print(f"  {mode}: {count}")

    if hard_fp_cases:
        print("\nHARD FP CASES (state-changing actions triggered incorrectly):")
        for c in hard_fp_cases[:5]:
            print(f"  {c['id']}: {c['query']}... → {c['predicted_action']}")

    if soft_misroute_cases:
        print("\nSOFT MISROUTE CASES (read-only, wrong action):")
        for c in soft_misroute_cases[:5]:
            print(f"  {c['id']}: {c['query']}... → {c['predicted_action']}")

    return metrics


if __name__ == "__main__":
    run_audit("stress_test_dataset_v3.json", "manual_audit_v3_results.jsonl")
