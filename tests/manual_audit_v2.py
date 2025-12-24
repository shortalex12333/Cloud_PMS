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
    correct_verb_typo,
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
    # Normalize whitespace: tabs to spaces, multiple spaces to single
    query = re.sub(r'\t', ' ', query)
    query = re.sub(r' +', ' ', query)
    query = query.strip()

    # Skip common noise prefixes (expanded for voice dictation, email, forum)
    # Order matters: process multi-word patterns before single-word
    noise_patterns = [
        # Multi-line bullet lists: strip first bullet line (context) to get to command
        # e.g., "- tender fault\n- create work order" → "create work order"
        r"^-\s+[^\n]*\n-\s*",
        # URGENT/PRIORITY prefixes with context lines
        # e.g., "URGENT:\nAC unit seized\nadd to handover" → "add to handover"
        r"^(urgent|priority|critical|asap)[:\s]*\n[^\n]*\n",
        # Multi-line quote blocks (>>> line\n>>> line\n... then command)
        r"^(>{1,3}[^\n]*\n)+",
        # Email prefixes with content and newlines (greedy match)
        r"^(fw:|re:|fwd:|from:|subject:)[^\n]*\n+",
        # Multi-word voice fillers (must come before single-word patterns)
        r"^hey\s+(yeah\s+so|right\s+so|like\s+um|so\s+um|um|so)\s+",
        r"^(yeah|right|ok|okay)\s+so\s+",
        r"^(so|like)\s+(um|like|basically)\s+",
        r"^hey\s+so\s+um\s+",  # hey so um
        # Bullet points (various styles)
        r"^[-•►→»*–—]\s*",
        # Single-line quote markers (>, >>, >>>)
        r"^>{1,3}\s*",
        # Numbered lists
        r"^\d+[.)]\s*",
        # Hesitation sounds
        r"^(um|uh|er|ah)\s+",
        # Single-word filler/confirmation words
        r"^(ok|okay|so|right|well|yeah|yep|sure|alright)\s+",
        # Hedge words
        r"^(basically|actually|literally|honestly|like)\s+",
        # Casual openers
        r"^(hey|hi|yo)\s+",
        # Accidental article prefix
        r"^the\s+",
        # Test noise markers (from suite generator)
        r"^noise_\w+\s+",
    ]

    # Apply patterns iteratively until no more matches
    changed = True
    max_iterations = 5  # Prevent infinite loops
    iterations = 0
    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        for pattern in noise_patterns:
            new_query = re.sub(pattern, "", query, flags=re.IGNORECASE)
            if new_query != query:
                query = new_query.strip()
                changed = True
                break  # Restart from first pattern after a match

    words = query.strip().split()
    if not words:
        return ""

    first_token = words[0].lower()

    # Check for concatenated verb+word (e.g., "diagnoseradar" → "diagnose")
    # But NOT conjugations like "scheduled", "showing", "created"
    known_verbs = [
        "diagnose", "troubleshoot", "investigate",
        "show", "view", "display", "list",
        "create", "update", "close", "add", "attach",
        "check", "order", "scan", "reserve",
        "export", "generate", "open", "upload",
        "log", "submit", "archive", "share",
        "assign", "schedule", "mark", "set",
    ]
    # English verb conjugation suffixes to reject
    conjugation_suffixes = ["d", "ed", "s", "es", "ing", "er", "ment", "tion", "ness", "ly"]

    for verb in known_verbs:
        if first_token.startswith(verb) and len(first_token) > len(verb):
            remainder = first_token[len(verb):]
            # Skip if remainder is a conjugation suffix (e.g., scheduled → "d")
            if remainder in conjugation_suffixes:
                continue
            # Found concatenated verb+word (e.g., diagnoseradar)
            first_token = verb
            break

    # Apply typo correction
    return correct_verb_typo(first_token)


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
    action_matches_on_tp = 0  # FIXED: Only count matches on true positives
    action_collisions = 0
    total_entity_misses = 0
    total_expected_entities = 0
    failure_mode_counts = defaultdict(int)

    # NEW: Hard FP vs Soft Misroute tracking
    hard_fp_count = 0
    soft_misroute_count = 0
    hard_fp_cases = []
    soft_misroute_cases = []

    # NEW: Collision pair tracking (expected → predicted)
    collision_pairs = defaultdict(int)
    collision_examples = []

    # NEW: Entity extraction by type
    entity_hits_by_type = defaultdict(int)
    entity_misses_by_type = defaultdict(int)
    missed_entity_examples = []

    print(f"Auditing {len(cases)} cases with canonical resolution + severity scoring...")

    with open(output_path, 'w') as out:
        for i, case in enumerate(cases):
            result = audit_case(case)
            out.write(json.dumps(result) + "\n")

            exp_trigger = case["expected"]["should_trigger_action"]
            pred_trigger = result["manual_judgement"]["router"]["should_trigger_action"]

            exp_action = result["expected"]["primary_action_canonical"]
            pred_action = result["manual_judgement"]["router"]["predicted_primary_action"]

            if exp_trigger and pred_trigger:
                tp += 1
                # FIXED: Only count action matches on true positives
                if result["scoring_outcome"]["action_match"]:
                    action_matches_on_tp += 1
                else:
                    # Track collision pairs
                    collision_pairs[(exp_action, pred_action)] += 1
                    if len(collision_examples) < 50:
                        collision_examples.append({
                            "id": result["id"],
                            "query": result["query"][:50],
                            "expected": exp_action,
                            "predicted": pred_action,
                        })
            elif not exp_trigger and not pred_trigger:
                tn += 1
            elif not exp_trigger and pred_trigger:
                fp += 1
            else:
                fn += 1

            if "action_collision" in result["scoring_outcome"]["failure_mode_tags"]:
                action_collisions += 1

            # Track entity metrics by type
            expected_entities = case["expected"].get("expected_entities", [])
            extracted_entities = result["manual_judgement"]["entities"]
            extracted_values = {e["raw_value"].lower() for e in extracted_entities}

            for exp_ent in expected_entities:
                ent_type = exp_ent.get("type", "unknown")
                value_hint = exp_ent.get("value_hint", "").lower()
                if value_hint in extracted_values:
                    entity_hits_by_type[ent_type] += 1
                else:
                    entity_misses_by_type[ent_type] += 1
                    if len(missed_entity_examples) < 30:
                        missed_entity_examples.append({
                            "id": result["id"],
                            "type": ent_type,
                            "expected": value_hint,
                            "query": result["query"][:40],
                        })

            total_entity_misses += result["scoring_outcome"]["entity_misses"]
            total_expected_entities += len(expected_entities)

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

    # FIXED: Correct action accuracy (matches on TP only)
    action_accuracy = action_matches_on_tp / max(tp, 1)

    # Sort collision pairs by frequency
    top_collision_pairs = sorted(collision_pairs.items(), key=lambda x: -x[1])[:20]

    # Group collisions by verb family
    verb_collision_counts = defaultdict(int)
    for (exp, pred), count in collision_pairs.items():
        # Extract verb from action (first word before _)
        verb = exp.split("_")[0] if exp else "unknown"
        verb_collision_counts[verb] += count

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
            "hard_fp_cases": hard_fp_cases[:10],
            "soft_misroute_cases": soft_misroute_cases[:10],
        },
        "action_selection": {  # RENAMED & FIXED
            "correct_action_on_tp": action_matches_on_tp,
            "total_tp": tp,
            "action_accuracy": round(action_accuracy, 4),
            "collisions": action_collisions,
            "top_collision_pairs": [
                {"expected": exp, "predicted": pred, "count": cnt}
                for (exp, pred), cnt in top_collision_pairs
            ],
            "collisions_by_verb": dict(verb_collision_counts),
            "collision_examples": collision_examples[:20],
        },
        "entity_extraction": {
            "total_expected": total_expected_entities,
            "total_misses": total_entity_misses,
            "hit_rate": round(entity_hit_rate, 4),
            "by_type": {
                ent_type: {
                    "hits": entity_hits_by_type[ent_type],
                    "misses": entity_misses_by_type[ent_type],
                    "hit_rate": round(entity_hits_by_type[ent_type] / max(entity_hits_by_type[ent_type] + entity_misses_by_type[ent_type], 1), 4),
                }
                for ent_type in set(entity_hits_by_type.keys()) | set(entity_misses_by_type.keys())
            },
            "missed_examples": missed_entity_examples[:20],
        },
        "failure_modes": dict(failure_mode_counts),
    }

    with open("manual_audit_v3_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT REPORT")
    print("=" * 70)

    # SECTION 1: Trigger Metrics
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  SECTION 1: TRIGGER METRICS                                          ║
╚══════════════════════════════════════════════════════════════════════╝

  TP: {tp}  FP: {fp}  FN: {fn}  TN: {tn}
  Precision: {precision:.2%}
  Recall:    {recall:.2%}
  F1:        {f1:.2%}

  Hard FP (state-changing):  {hard_fp_count}
  Soft Misroute (read-only): {soft_misroute_count}
""")

    # SECTION 2: Action Selection Metrics
    print(f"""╔══════════════════════════════════════════════════════════════════════╗
║  SECTION 2: ACTION SELECTION METRICS                                  ║
╚══════════════════════════════════════════════════════════════════════╝

  Correct Action on TP: {action_matches_on_tp} / {tp}
  ACTION ACCURACY:      {action_accuracy:.2%}
  Collisions:           {action_collisions}
""")

    # Top collision pairs
    if top_collision_pairs:
        print("  TOP COLLISION PAIRS (expected → predicted):")
        for (exp, pred), cnt in top_collision_pairs[:10]:
            print(f"    {cnt:3d}x  {exp} → {pred}")

    # Collisions by verb family
    if verb_collision_counts:
        print("\n  COLLISIONS BY VERB FAMILY:")
        for verb, cnt in sorted(verb_collision_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {verb}: {cnt}")

    # SECTION 3: Entity Extraction Metrics
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  SECTION 3: ENTITY EXTRACTION METRICS                                 ║
╚══════════════════════════════════════════════════════════════════════╝

  Overall Hit Rate: {entity_hit_rate:.2%} ({total_expected_entities - total_entity_misses}/{total_expected_entities})

  BY ENTITY TYPE:""")

    for ent_type in sorted(set(entity_hits_by_type.keys()) | set(entity_misses_by_type.keys())):
        hits = entity_hits_by_type[ent_type]
        misses = entity_misses_by_type[ent_type]
        total = hits + misses
        rate = hits / max(total, 1)
        print(f"    {ent_type:20s}: {rate:.1%} ({hits}/{total})")

    if missed_entity_examples:
        print("\n  TOP MISSED ENTITIES:")
        for ex in missed_entity_examples[:10]:
            print(f"    [{ex['type']}] '{ex['expected']}' in: {ex['query']}...")

    # Summary
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║  SUMMARY                                                              ║
╚══════════════════════════════════════════════════════════════════════╝

  Trigger F1:        {f1:.2%}  {'✓ GOOD' if f1 > 0.95 else '✗ NEEDS WORK'}
  Hard FP:           {hard_fp_count}       {'✓ SAFE' if hard_fp_count == 0 else '✗ CRITICAL'}
  Action Accuracy:   {action_accuracy:.2%}  {'✓ GOOD' if action_accuracy > 0.90 else '✗ NEEDS WORK'}
  Entity Hit Rate:   {entity_hit_rate:.2%}  {'✓ GOOD' if entity_hit_rate > 0.80 else '✗ NEEDS WORK'}
""")

    if hard_fp_cases:
        print("HARD FP CASES (CRITICAL - state-changing actions triggered incorrectly):")
        for c in hard_fp_cases[:5]:
            print(f"  {c['id']}: {c['query']}... → {c['predicted_action']}")

    if soft_misroute_cases:
        print("\nSOFT MISROUTE CASES (read-only, wrong action):")
        for c in soft_misroute_cases[:5]:
            print(f"  {c['id']}: {c['query']}... → {c['predicted_action']}")

    return metrics


if __name__ == "__main__":
    run_audit("stress_test_dataset_v3.json", "manual_audit_v3_results.jsonl")
