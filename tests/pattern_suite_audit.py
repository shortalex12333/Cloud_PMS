#!/usr/bin/env python3
"""
Pattern Suite Audit
===================
Runs the routing audit on pattern suites and generates detailed metrics.
Tracks per-pattern performance to identify areas needing improvement.
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

from canonical_action_registry import (
    CANONICAL_ACTIONS,
    canonicalize_action,
    resolve_verb_action,
    has_polite_prefix,
    STRICT_TRIGGER_VERBS,
)

# Import the router simulation from manual_audit_v2
from manual_audit_v2 import (
    simulate_strict_router,
    extract_entities,
    classify_fp_severity,
    STATE_CHANGING_ACTIONS,
    READ_ONLY_ACTIONS,
)


@dataclass
class SuiteResult:
    """Results for a single suite."""
    suite_id: str
    pattern_target: str
    hypothesis: str

    # Trigger classification
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    # FP severity
    hard_fp: int = 0
    soft_misroute: int = 0

    # Action matching
    action_matches: int = 0
    action_collisions: int = 0

    # Entity extraction
    entity_hits: int = 0
    entity_misses: int = 0

    # Cases with issues
    failure_cases: List[Dict] = None

    def __post_init__(self):
        if self.failure_cases is None:
            self.failure_cases = []

    @property
    def precision(self) -> float:
        return self.tp / max(self.tp + self.fp, 1)

    @property
    def recall(self) -> float:
        return self.tp / max(self.tp + self.fn, 1)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / max(p + r, 0.001)

    @property
    def hypothesis_passed(self) -> bool:
        """Check if hypothesis is satisfied."""
        # Hypothesis passes if:
        # - Zero hard FPs
        # - F1 >= 0.8 or improved
        return self.hard_fp == 0 and self.f1 >= 0.8

    def to_dict(self) -> Dict:
        return {
            "suite_id": self.suite_id,
            "pattern_target": self.pattern_target,
            "hypothesis": self.hypothesis,
            "metrics": {
                "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
                "precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1": round(self.f1, 4),
            },
            "fp_severity": {
                "hard_fp": self.hard_fp,
                "soft_misroute": self.soft_misroute,
            },
            "action_detection": {
                "matches": self.action_matches,
                "collisions": self.action_collisions,
            },
            "entity_extraction": {
                "hits": self.entity_hits,
                "misses": self.entity_misses,
            },
            "hypothesis_passed": self.hypothesis_passed,
            "failure_cases": self.failure_cases[:10],  # Top 10 failures
        }


def audit_case(case: Dict) -> Dict:
    """Audit a single case from a pattern suite."""
    query = case["query"]
    labels = case["labels"]

    # Run router simulation
    router_result = simulate_strict_router(query)

    # Expected values
    exp_trigger = labels["should_trigger_action"]
    exp_action = labels["expected_primary_action"]
    exp_action_canonical = canonicalize_action(exp_action)

    # Predicted values
    pred_trigger = router_result["should_trigger_action"]
    pred_action = router_result["predicted_primary_action"]

    # Classification
    is_fp = (not exp_trigger) and pred_trigger
    is_fn = exp_trigger and (not pred_trigger)
    is_tp = exp_trigger and pred_trigger
    is_tn = (not exp_trigger) and (not pred_trigger)

    # Action match
    action_match = (exp_action_canonical == pred_action) if is_tp else False
    action_collision = is_tp and not action_match

    # FP severity
    severity = classify_fp_severity(exp_action_canonical, pred_action, exp_trigger, pred_trigger)

    # Entity extraction
    expected_entities = labels.get("expected_entities", [])
    extracted_entities = extract_entities(query)
    extracted_values = {e["raw_value"].lower() for e in extracted_entities}

    entity_hits = 0
    entity_misses = 0
    for exp_ent in expected_entities:
        value_hint = exp_ent.get("value_hint", "").lower()
        evidence = exp_ent.get("evidence", "").lower()
        if value_hint in extracted_values or evidence in extracted_values:
            entity_hits += 1
        else:
            entity_misses += 1

    return {
        "case_id": case["id"],
        "query": query,
        "expected": {
            "trigger": exp_trigger,
            "action": exp_action_canonical,
            "risk_class": labels.get("risk_class", "unknown"),
        },
        "predicted": {
            "trigger": pred_trigger,
            "action": pred_action,
        },
        "classification": {
            "is_tp": is_tp,
            "is_fp": is_fp,
            "is_fn": is_fn,
            "is_tn": is_tn,
        },
        "action_match": action_match,
        "action_collision": action_collision,
        "fp_severity": severity,
        "entity_hits": entity_hits,
        "entity_misses": entity_misses,
    }


def audit_suite(suite: Dict) -> SuiteResult:
    """Audit an entire suite."""
    result = SuiteResult(
        suite_id=suite["suite_id"],
        pattern_target=suite["pattern_target"],
        hypothesis=suite["hypothesis"],
    )

    for case in suite["cases"]:
        case_result = audit_case(case)

        # Update counters
        if case_result["classification"]["is_tp"]:
            result.tp += 1
        if case_result["classification"]["is_fp"]:
            result.fp += 1
        if case_result["classification"]["is_fn"]:
            result.fn += 1
        if case_result["classification"]["is_tn"]:
            result.tn += 1

        # FP severity
        if case_result["fp_severity"]["is_hard_fp"]:
            result.hard_fp += 1
        if case_result["fp_severity"]["is_soft_misroute"]:
            result.soft_misroute += 1

        # Action matching
        if case_result["action_match"]:
            result.action_matches += 1
        if case_result["action_collision"]:
            result.action_collisions += 1

        # Entity extraction
        result.entity_hits += case_result["entity_hits"]
        result.entity_misses += case_result["entity_misses"]

        # Track failures for analysis
        if case_result["classification"]["is_fp"] or case_result["classification"]["is_fn"] or case_result["action_collision"]:
            result.failure_cases.append({
                "case_id": case_result["case_id"],
                "query": case_result["query"][:60],
                "expected": case_result["expected"],
                "predicted": case_result["predicted"],
                "issue": "hard_fp" if case_result["fp_severity"]["is_hard_fp"] else
                         "soft_misroute" if case_result["fp_severity"]["is_soft_misroute"] else
                         "fn" if case_result["classification"]["is_fn"] else
                         "collision",
            })

    return result


def run_pattern_suite_audit(suites_path: str) -> Dict:
    """Run audit on all pattern suites."""
    with open(suites_path) as f:
        data = json.load(f)

    suites = data["suites"]

    print("=" * 70)
    print("PATTERN SUITE AUDIT")
    print("=" * 70)
    print(f"\nAuditing {len(suites)} suites...")

    results = []
    pattern_aggregates = defaultdict(lambda: {
        "suites": 0, "cases": 0,
        "tp": 0, "fp": 0, "fn": 0, "tn": 0,
        "hard_fp": 0, "soft_misroute": 0,
        "action_matches": 0, "action_collisions": 0,
    })

    for suite in suites:
        result = audit_suite(suite)
        results.append(result)

        # Aggregate by pattern
        pattern = suite["pattern_target"]
        agg = pattern_aggregates[pattern]
        agg["suites"] += 1
        agg["cases"] += result.tp + result.fp + result.fn + result.tn
        agg["tp"] += result.tp
        agg["fp"] += result.fp
        agg["fn"] += result.fn
        agg["tn"] += result.tn
        agg["hard_fp"] += result.hard_fp
        agg["soft_misroute"] += result.soft_misroute
        agg["action_matches"] += result.action_matches
        agg["action_collisions"] += result.action_collisions

    # Calculate overall metrics
    total_tp = sum(r.tp for r in results)
    total_fp = sum(r.fp for r in results)
    total_fn = sum(r.fn for r in results)
    total_tn = sum(r.tn for r in results)
    total_hard_fp = sum(r.hard_fp for r in results)
    total_soft_misroute = sum(r.soft_misroute for r in results)

    overall_precision = total_tp / max(total_tp + total_fp, 1)
    overall_recall = total_tp / max(total_tp + total_fn, 1)
    overall_f1 = 2 * overall_precision * overall_recall / max(overall_precision + overall_recall, 0.001)

    # Print summary
    print(f"\n{'=' * 70}")
    print("OVERALL METRICS")
    print(f"{'=' * 70}")
    print(f"""
TRIGGER CLASSIFICATION:
  TP: {total_tp}  FP: {total_fp}  FN: {total_fn}  TN: {total_tn}
  Precision: {overall_precision:.2%}
  Recall:    {overall_recall:.2%}
  F1:        {overall_f1:.2%}

FALSE POSITIVE SEVERITY:
  Hard FP (CRITICAL):    {total_hard_fp}
  Soft Misroute:         {total_soft_misroute}
  Hard FP Rate: {total_hard_fp / max(total_fp, 1):.2%} of all FPs
""")

    print(f"\n{'=' * 70}")
    print("PER-PATTERN BREAKDOWN")
    print(f"{'=' * 70}")

    # Sort by failure count
    for pattern, agg in sorted(pattern_aggregates.items(),
                                key=lambda x: (x[1]["hard_fp"], x[1]["fp"], -x[1]["tp"]),
                                reverse=True):
        prec = agg["tp"] / max(agg["tp"] + agg["fp"], 1)
        rec = agg["tp"] / max(agg["tp"] + agg["fn"], 1)
        f1 = 2 * prec * rec / max(prec + rec, 0.001)

        status = "PASS" if agg["hard_fp"] == 0 and f1 >= 0.8 else "FAIL"
        print(f"\n  {pattern}:")
        print(f"    Suites: {agg['suites']}  Cases: {agg['cases']}")
        print(f"    TP: {agg['tp']}  FP: {agg['fp']}  FN: {agg['fn']}  TN: {agg['tn']}")
        print(f"    Precision: {prec:.2%}  Recall: {rec:.2%}  F1: {f1:.2%}")
        print(f"    Hard FP: {agg['hard_fp']}  Soft Misroute: {agg['soft_misroute']}")
        print(f"    Collisions: {agg['action_collisions']}")
        print(f"    Status: [{status}]")

    # Print failing suites
    failing_suites = [r for r in results if not r.hypothesis_passed]
    if failing_suites:
        print(f"\n{'=' * 70}")
        print(f"FAILING SUITES ({len(failing_suites)})")
        print(f"{'=' * 70}")

        for r in failing_suites[:10]:
            print(f"\n  {r.suite_id} ({r.pattern_target}):")
            print(f"    F1: {r.f1:.2%}  Hard FP: {r.hard_fp}  Soft Misroute: {r.soft_misroute}")
            print(f"    Failures:")
            for fc in r.failure_cases[:3]:
                print(f"      - [{fc['issue']}] {fc['query']}")
                print(f"        Expected: {fc['expected']['action']} | Got: {fc['predicted']['action']}")

    # Save results
    output = {
        "overall": {
            "total_suites": len(suites),
            "total_cases": total_tp + total_fp + total_fn + total_tn,
            "trigger_classification": {
                "tp": total_tp, "fp": total_fp, "fn": total_fn, "tn": total_tn,
                "precision": round(overall_precision, 4),
                "recall": round(overall_recall, 4),
                "f1": round(overall_f1, 4),
            },
            "fp_severity": {
                "hard_fp": total_hard_fp,
                "soft_misroute": total_soft_misroute,
            },
        },
        "pattern_breakdown": {
            pattern: {
                **agg,
                "precision": round(agg["tp"] / max(agg["tp"] + agg["fp"], 1), 4),
                "recall": round(agg["tp"] / max(agg["tp"] + agg["fn"], 1), 4),
            }
            for pattern, agg in pattern_aggregates.items()
        },
        "suite_results": [r.to_dict() for r in results],
    }

    with open("pattern_suite_audit_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n\nResults saved to pattern_suite_audit_results.json")

    return output


if __name__ == "__main__":
    run_pattern_suite_audit("pattern_suites_v1.json")
