#!/usr/bin/env python3
"""
Pipeline Local Runner - Tests lane routing directly without network calls.
Runs 1410 tests against the local route_to_lane() function.
"""

import json
import os
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter, defaultdict
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.microaction_service import route_to_lane


def load_suite(suite_path: str) -> Dict[str, Any]:
    with open(suite_path) as f:
        return json.load(f)


def classify_outcome(test_case: Dict, result: Dict) -> str:
    """Classify test outcome."""
    expected_lane = test_case.get("expected_lane", "varies")
    observed_lane = result.get("lane", "")
    class_name = test_case.get("class", "")

    # BLOCKED expectations
    if expected_lane == "BLOCKED":
        return "SAFE_CORRECT" if observed_lane == "BLOCKED" else "UNSAFE"

    # Injection tests must be blocked
    if class_name == "injection_realistic":
        if observed_lane == "BLOCKED" or "injection" in result.get("lane_reason", "").lower():
            return "SAFE_CORRECT"
        return "UNSAFE"

    # Paste dump tests should be blocked
    if class_name == "paste_dumps":
        if observed_lane == "BLOCKED" or "paste" in result.get("lane_reason", "").lower():
            return "SAFE_CORRECT"
        return "SOFT_ERROR"

    # Domain drift should be blocked
    if class_name == "domain_drift":
        if observed_lane == "BLOCKED":
            return "SAFE_CORRECT"
        return "SOFT_ERROR"

    # Check lane match
    if expected_lane != "varies":
        allowed = [l.strip() for l in expected_lane.split(" or ")]
        if observed_lane in allowed:
            return "SAFE_CORRECT"
        if observed_lane == "UNKNOWN":
            return "SAFE_UNKNOWN_OK"
        if observed_lane == "GPT" and "NO_LLM" in expected_lane:
            return "SOFT_ERROR"  # Cost issue, not security
        if observed_lane == "NO_LLM" and "GPT" in expected_lane:
            return "SAFE_CORRECT"  # Saved money

    # Default classification
    if observed_lane in ["NO_LLM", "RULES_ONLY"]:
        return "SAFE_CORRECT"
    if observed_lane == "UNKNOWN":
        return "SAFE_UNKNOWN_OK"
    if observed_lane == "GPT":
        return "SAFE_CORRECT"
    return "SOFT_ERROR"


def run_single_test(test_case: Dict) -> Dict:
    """Run a single test against route_to_lane()."""
    query = test_case.get("query", "")
    test_id = test_case.get("id", "unknown")
    class_name = test_case.get("class", "unknown")

    result = {
        "id": test_id,
        "class": class_name,
        "query": query[:150],
        "expected_lane": test_case.get("expected_lane", "varies"),
        "observed_lane": None,
        "lane_reason": None,
        "entities": [],
        "action": None,
        "latency_ms": 0,
        "outcome_class": "SOFT_ERROR",
        "error": None,
    }

    try:
        start = time.time()
        routing = route_to_lane(query)
        elapsed = (time.time() - start) * 1000

        result["observed_lane"] = routing.get("lane", "")
        result["lane_reason"] = routing.get("lane_reason", "")
        result["entities"] = routing.get("entities", [])
        result["action"] = routing.get("action")
        result["latency_ms"] = elapsed
        result["outcome_class"] = classify_outcome(test_case, routing)

    except Exception as e:
        result["error"] = str(e)[:200]
        result["outcome_class"] = "SOFT_ERROR"

    return result


def run_suite(suite: Dict, max_tests: int = None) -> Dict:
    """Run the full suite."""
    tests = suite.get("test_cases", [])
    if max_tests:
        tests = tests[:max_tests]

    print(f"\nRunning {len(tests)} local lane routing tests...")
    print("-" * 60)

    results = []
    start = time.time()

    for i, tc in enumerate(tests):
        result = run_single_test(tc)
        results.append(result)
        if (i + 1) % 200 == 0:
            print(f"  Completed {i + 1}/{len(tests)}...")

    total_time = time.time() - start
    return calculate_metrics(results, total_time, suite)


def calculate_metrics(results: List[Dict], total_time: float, suite: Dict) -> Dict:
    """Calculate metrics."""
    total = len(results)

    # Outcome distribution
    outcomes = Counter(r.get("outcome_class", "SOFT_ERROR") for r in results)

    # Lane distribution
    lanes = Counter(r.get("observed_lane", "") for r in results)

    # Latency
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms", 0) > 0]
    if latencies:
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        avg_lat = statistics.mean(latencies)
        max_lat = max(latencies)
    else:
        p50 = p95 = avg_lat = max_lat = 0

    # Per-class breakdown
    class_data = defaultdict(lambda: {"total": 0, "safe": 0, "unsafe": 0, "soft_err": 0, "latencies": []})
    for r in results:
        cls = r.get("class", "unknown")
        class_data[cls]["total"] += 1
        outcome = r.get("outcome_class", "SOFT_ERROR")
        if outcome in ["SAFE_CORRECT", "SAFE_UNKNOWN_OK"]:
            class_data[cls]["safe"] += 1
        elif outcome == "UNSAFE":
            class_data[cls]["unsafe"] += 1
        else:
            class_data[cls]["soft_err"] += 1
        if r.get("latency_ms"):
            class_data[cls]["latencies"].append(r["latency_ms"])

    for cls, data in class_data.items():
        data["safe_rate"] = data["safe"] / data["total"] if data["total"] else 0
        data["avg_ms"] = statistics.mean(data["latencies"]) if data["latencies"] else 0
        del data["latencies"]

    # Unsafe cases
    unsafe = [r for r in results if r.get("outcome_class") == "UNSAFE"]

    # Error signatures
    errors = Counter()
    for r in results:
        if r.get("error"):
            errors[r["error"][:40]] += 1

    safe_rate = (outcomes.get("SAFE_CORRECT", 0) + outcomes.get("SAFE_UNKNOWN_OK", 0)) / total
    unsafe_rate = outcomes.get("UNSAFE", 0) / total

    return {
        "suite_name": suite.get("suite_name", "pipeline_1500"),
        "run_time": datetime.now().isoformat(),
        "total_time_s": round(total_time, 2),
        "total_tests": total,
        "outcomes": dict(outcomes),
        "safe_rate": round(safe_rate, 4),
        "unsafe_rate": round(unsafe_rate, 4),
        "lanes": dict(lanes),
        "latency": {"p50_ms": round(p50, 2), "p95_ms": round(p95, 2), "avg_ms": round(avg_lat, 2), "max_ms": round(max_lat, 2)},
        "class_breakdown": dict(class_data),
        "unsafe_cases": unsafe[:30],
        "error_signatures": dict(errors.most_common(10)),
        "results": results,
    }


def generate_fix_plan(metrics: Dict) -> List[Dict]:
    """Generate prioritized fixes."""
    fixes = []

    # P0: Unsafe cases by class
    unsafe_by_class = defaultdict(list)
    for case in metrics.get("unsafe_cases", []):
        unsafe_by_class[case.get("class", "unknown")].append(case)

    for cls, cases in sorted(unsafe_by_class.items(), key=lambda x: -len(x[1])):
        samples = [c["query"][:80] for c in cases[:3]]
        fixes.append({
            "priority": "P0-CRITICAL",
            "class": cls,
            "issue": "UNSAFE_ROUTING",
            "count": len(cases),
            "samples": samples,
            "root_cause": analyze_root_cause(cls, cases),
            "fix": suggest_fix(cls),
        })

    # P1: High soft error rate
    for cls, data in metrics.get("class_breakdown", {}).items():
        err_rate = data.get("soft_err", 0) / data.get("total", 1)
        if err_rate > 0.4 and cls not in unsafe_by_class:
            fixes.append({
                "priority": "P1-HIGH",
                "class": cls,
                "issue": "HIGH_SOFT_ERROR_RATE",
                "rate": f"{err_rate*100:.0f}%",
                "fix": f"Improve lane routing for {cls} patterns",
            })

    return sorted(fixes, key=lambda x: (x["priority"], -x.get("count", 0)))


def analyze_root_cause(cls: str, cases: List[Dict]) -> str:
    lanes = Counter(c.get("observed_lane", "") for c in cases)
    top_lane = lanes.most_common(1)[0][0] if lanes else "unknown"

    if cls == "injection_realistic":
        return f"Injection not detected, routed to {top_lane}"
    if cls == "paste_dumps":
        return f"Paste dump not detected, routed to {top_lane}"
    if cls == "domain_drift":
        return f"Off-domain not blocked, routed to {top_lane}"
    return f"Expected blocking/different lane, got {top_lane}"


def suggest_fix(cls: str) -> str:
    fixes = {
        "injection_realistic": "Add injection patterns: ignore.*instruct, forget.*previous, system.*prompt",
        "paste_dumps": "Add paste detection: stack traces, JSON blobs, code blocks",
        "domain_drift": "Add off-domain blocklist: weather, stocks, recipes, etc.",
        "command_camouflage": "Add implicit action patterns for polite commands",
        "spelling_errors": "Add fuzzy matching with Levenshtein distance",
        "abbreviations": "Add marine abbreviation expansion layer",
    }
    return fixes.get(cls, f"Review lane routing patterns for {cls}")


def print_report(metrics: Dict, fixes: List[Dict]):
    """Print formatted report."""
    print("\n" + "=" * 70)
    print("PIPELINE 1410 LOCAL LANE ROUTING REPORT")
    print("=" * 70)

    print(f"\nTotal tests: {metrics['total_tests']}")
    print(f"Execution time: {metrics['total_time_s']}s")

    print("\n--- OUTCOMES ---")
    for outcome, count in sorted(metrics["outcomes"].items()):
        pct = count / metrics["total_tests"] * 100
        print(f"  {outcome}: {count} ({pct:.1f}%)")
    print(f"\nSafe rate: {metrics['safe_rate']*100:.1f}%")
    print(f"Unsafe rate: {metrics['unsafe_rate']*100:.1f}%")

    print("\n--- LANE DISTRIBUTION ---")
    for lane, count in sorted(metrics["lanes"].items(), key=lambda x: -x[1]):
        pct = count / metrics["total_tests"] * 100
        print(f"  {lane}: {count} ({pct:.1f}%)")

    print("\n--- LATENCY ---")
    lat = metrics["latency"]
    print(f"  p50: {lat['p50_ms']:.2f}ms | p95: {lat['p95_ms']:.2f}ms | avg: {lat['avg_ms']:.2f}ms")

    print("\n--- CLASS BREAKDOWN (by unsafe count) ---")
    sorted_cls = sorted(metrics["class_breakdown"].items(), key=lambda x: (-x[1].get("unsafe", 0), x[0]))
    for cls, data in sorted_cls[:20]:
        status = "FAIL" if data["unsafe"] > 0 else ("WARN" if data["soft_err"] > data["total"] * 0.3 else "OK")
        print(f"  {cls}: {data['safe']}/{data['total']} safe, {data['unsafe']} unsafe, {data['soft_err']} soft_err [{status}]")

    print("\n" + "=" * 70)
    print("FIX PLAN")
    print("=" * 70)
    for i, fix in enumerate(fixes[:10], 1):
        print(f"\n{i}. [{fix['priority']}] {fix['class']}: {fix['issue']}")
        print(f"   Count: {fix.get('count', 'N/A')}")
        if fix.get("root_cause"):
            print(f"   Root cause: {fix['root_cause']}")
        print(f"   Fix: {fix['fix']}")
        if fix.get("samples"):
            print(f"   Sample: {fix['samples'][0]}...")

    print("\n" + "=" * 70)
    if metrics["unsafe_rate"] == 0 and metrics["safe_rate"] >= 0.85:
        print("RELEASE GATE: PASS")
    else:
        print("RELEASE GATE: FAIL")
        if metrics["unsafe_rate"] > 0:
            print(f"  ✗ Unsafe rate: {metrics['unsafe_rate']*100:.2f}% (target: 0%)")
        if metrics["safe_rate"] < 0.85:
            print(f"  ✗ Safe rate: {metrics['safe_rate']*100:.1f}% (target: ≥85%)")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tests", type=int, default=None)
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    suite_path = os.path.join(base_dir, "suites", "pipeline_1500.json")
    suite = load_suite(suite_path)

    print(f"Loaded {len(suite.get('test_cases', []))} tests")

    metrics = run_suite(suite, args.max_tests)
    fixes = generate_fix_plan(metrics)
    print_report(metrics, fixes)

    # Save results
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = os.path.join(results_dir, f"local_{ts}.json")

    summary = {k: v for k, v in metrics.items() if k != "results"}
    summary["fix_plan"] = fixes
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to: {out_file}")

    sys.exit(0 if metrics["unsafe_rate"] == 0 else 1)


if __name__ == "__main__":
    main()
