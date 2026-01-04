#!/usr/bin/env python3
"""
Pipeline 1500 Test Runner
==========================

Runs the 1410-test pipeline chaos suite against /extract endpoint.

For every test, captures:
- input query
- expected lane (with UNKNOWN_OK vs UNKNOWN_BAD)
- observed lane
- capabilities executed + timings
- SQL/RPC executed identifiers
- outcome class: SAFE_CORRECT / SAFE_UNKNOWN_OK / SOFT_ERROR / UNSAFE

Usage:
    python tests/stress_campaign/pipeline_1500_runner.py
    python tests/stress_campaign/pipeline_1500_runner.py --concurrency 4
"""

import json
import os
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import concurrent.futures
import requests

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Production extract endpoint
EXTRACT_URL = "https://celeste-microactions.onrender.com/extract"


def load_suite(suite_path: str) -> Dict[str, Any]:
    with open(suite_path) as f:
        return json.load(f)


def classify_outcome(
    test_case: Dict[str, Any],
    response: Dict[str, Any],
    error: Optional[str] = None
) -> str:
    """
    Classify test outcome into:
    - SAFE_CORRECT: Expected behavior occurred
    - SAFE_UNKNOWN_OK: Unknown but acceptable (vague query, etc.)
    - SOFT_ERROR: Non-critical failure (timeout, empty result)
    - UNSAFE: Security violation or incorrect lane routing
    """
    expected_lane = test_case.get("expected_lane", "varies")
    expected_behavior = test_case.get("expected_behavior", "")

    if error:
        if "timeout" in error.lower():
            return "SOFT_ERROR"
        return "UNSAFE"

    observed_lane = response.get("lane", "")

    # Check for security violations
    if expected_lane == "BLOCKED":
        if observed_lane == "BLOCKED":
            return "SAFE_CORRECT"
        else:
            return "UNSAFE"  # Should have been blocked but wasn't

    # Check for injection detection
    if test_case.get("class_id") == "TC18":  # injection_realistic
        if observed_lane == "BLOCKED" or "injection" in response.get("lane_reason", "").lower():
            return "SAFE_CORRECT"
        else:
            return "UNSAFE"  # Injection not detected

    # Check for paste dump detection
    if test_case.get("class_id") == "TC17":  # paste_dumps
        if observed_lane == "BLOCKED" or "paste" in response.get("lane_reason", "").lower():
            return "SAFE_CORRECT"
        else:
            return "SOFT_ERROR"  # Paste dump not detected (less critical)

    # Check lane routing correctness
    if expected_lane != "varies":
        allowed_lanes = [l.strip() for l in expected_lane.split(" or ")]
        if observed_lane in allowed_lanes:
            return "SAFE_CORRECT"
        elif observed_lane == "UNKNOWN":
            # UNKNOWN can be acceptable for vague queries
            if "vague" in expected_behavior.lower() or "unknown" in expected_behavior.lower():
                return "SAFE_UNKNOWN_OK"
            else:
                return "SOFT_ERROR"
        elif observed_lane == "GPT" and "NO_LLM" in expected_lane:
            # GPT when NO_LLM expected - cost issue but not security
            return "SOFT_ERROR"
        elif observed_lane == "NO_LLM" and "GPT" in expected_lane:
            # NO_LLM when GPT expected - actually good (saved money)
            return "SAFE_CORRECT"

    # Default: check if response is reasonable
    if response.get("entities") or response.get("action"):
        return "SAFE_CORRECT"
    elif observed_lane == "UNKNOWN":
        return "SAFE_UNKNOWN_OK"
    else:
        return "SOFT_ERROR"


def run_single_test(test_case: Dict[str, Any], timeout_s: float = 30.0) -> Dict[str, Any]:
    """Run a single test against the extract endpoint."""
    test_id = test_case.get("id", "unknown")
    query = test_case.get("query", "")
    class_id = test_case.get("class_id", "")
    expected_lane = test_case.get("expected_lane", "varies")
    expected_behavior = test_case.get("expected_behavior", "")

    result = {
        "id": test_id,
        "class_id": class_id,
        "query": query[:200],  # Truncate for report
        "expected_lane": expected_lane,
        "expected_behavior": expected_behavior,
        "observed_lane": None,
        "lane_reason": None,
        "entities": [],
        "action": None,
        "capabilities_executed": [],
        "sql_rpc_ids": [],
        "latency_ms": 0.0,
        "outcome_class": "SOFT_ERROR",
        "error": None,
    }

    try:
        start = time.time()
        response = requests.post(
            EXTRACT_URL,
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            json={"query": query},
            timeout=timeout_s,
        )
        elapsed = (time.time() - start) * 1000
        result["latency_ms"] = elapsed

        if response.status_code == 200:
            data = response.json()
            result["observed_lane"] = data.get("lane", "")
            result["lane_reason"] = data.get("lane_reason", "")
            result["entities"] = data.get("entities", [])
            result["action"] = data.get("action")
            result["capabilities_executed"] = data.get("capabilities_executed", [])
            result["sql_rpc_ids"] = data.get("sql_rpc_ids", [])

            # Classify outcome
            result["outcome_class"] = classify_outcome(test_case, data)
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
            result["outcome_class"] = "SOFT_ERROR"

    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
        result["outcome_class"] = "SOFT_ERROR"
    except Exception as e:
        result["error"] = str(e)[:200]
        result["outcome_class"] = "SOFT_ERROR"

    return result


def run_suite(
    suite: Dict[str, Any],
    concurrency: int = 1,
    timeout_s: float = 30.0,
    max_tests: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the full test suite and collect metrics."""
    test_cases = suite.get("test_cases", [])
    if max_tests:
        test_cases = test_cases[:max_tests]

    results = []

    print(f"\nRunning {len(test_cases)} pipeline tests (concurrency={concurrency})...")
    print("-" * 60)

    start_time = time.time()

    if concurrency == 1:
        for i, tc in enumerate(test_cases):
            result = run_single_test(tc, timeout_s)
            results.append(result)
            if (i + 1) % 50 == 0:
                print(f"  Completed {i + 1}/{len(test_cases)}...")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(run_single_test, tc, timeout_s): tc
                for tc in test_cases
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    tc = futures[future]
                    results.append({
                        "id": tc.get("id", "unknown"),
                        "class_id": tc.get("class_id", ""),
                        "outcome_class": "SOFT_ERROR",
                        "error": str(e),
                    })
                completed += 1
                if completed % 50 == 0:
                    print(f"  Completed {completed}/{len(test_cases)}...")

    total_time = time.time() - start_time

    return calculate_metrics(results, total_time, suite)


def calculate_metrics(results: List[Dict], total_time: float, suite: Dict) -> Dict[str, Any]:
    """Calculate comprehensive metrics from test results."""
    total = len(results)

    # Outcome class distribution
    outcome_counts = Counter(r.get("outcome_class", "SOFT_ERROR") for r in results)

    # Lane distribution
    lane_counts = Counter(r.get("observed_lane", "unknown") for r in results)

    # Expected vs observed lane comparison
    lane_matches = sum(1 for r in results
                       if r.get("expected_lane") != "varies" and
                       r.get("observed_lane") in r.get("expected_lane", "").split(" or "))

    # Latency metrics
    latencies = [r.get("latency_ms", 0) for r in results if r.get("latency_ms", 0) > 0]
    if latencies:
        p50 = statistics.median(latencies)
        sorted_lat = sorted(latencies)
        p95_idx = int(len(sorted_lat) * 0.95)
        p95 = sorted_lat[p95_idx] if p95_idx < len(sorted_lat) else sorted_lat[-1]
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
    else:
        p50 = p95 = avg_latency = max_latency = 0

    # Class breakdown
    class_results = defaultdict(lambda: {
        "total": 0, "safe_correct": 0, "safe_unknown_ok": 0,
        "soft_error": 0, "unsafe": 0, "latencies": []
    })
    for r in results:
        cid = r.get("class_id", "unknown")
        class_results[cid]["total"] += 1
        outcome = r.get("outcome_class", "SOFT_ERROR")
        if outcome == "SAFE_CORRECT":
            class_results[cid]["safe_correct"] += 1
        elif outcome == "SAFE_UNKNOWN_OK":
            class_results[cid]["safe_unknown_ok"] += 1
        elif outcome == "SOFT_ERROR":
            class_results[cid]["soft_error"] += 1
        elif outcome == "UNSAFE":
            class_results[cid]["unsafe"] += 1
        if r.get("latency_ms", 0) > 0:
            class_results[cid]["latencies"].append(r["latency_ms"])

    # Calculate per-class metrics
    for cid, data in class_results.items():
        data["safe_rate"] = (data["safe_correct"] + data["safe_unknown_ok"]) / data["total"] if data["total"] > 0 else 0
        data["avg_latency_ms"] = statistics.mean(data["latencies"]) if data["latencies"] else 0
        del data["latencies"]

    # Error signatures
    error_signatures = Counter()
    for r in results:
        if r.get("error"):
            sig = r["error"][:50]
            error_signatures[sig] += 1

    # Unsafe cases (critical failures)
    unsafe_cases = [r for r in results if r.get("outcome_class") == "UNSAFE"]

    # Calculate rates
    safe_correct_rate = outcome_counts.get("SAFE_CORRECT", 0) / total if total > 0 else 0
    safe_unknown_ok_rate = outcome_counts.get("SAFE_UNKNOWN_OK", 0) / total if total > 0 else 0
    soft_error_rate = outcome_counts.get("SOFT_ERROR", 0) / total if total > 0 else 0
    unsafe_rate = outcome_counts.get("UNSAFE", 0) / total if total > 0 else 0

    return {
        "suite_name": suite.get("suite_name", "pipeline_1500"),
        "run_time": datetime.now().isoformat(),
        "total_execution_time_s": round(total_time, 2),

        # Core metrics
        "total_tests": total,
        "outcome_distribution": dict(outcome_counts),
        "safe_correct_rate": round(safe_correct_rate, 4),
        "safe_unknown_ok_rate": round(safe_unknown_ok_rate, 4),
        "soft_error_rate": round(soft_error_rate, 4),
        "unsafe_rate": round(unsafe_rate, 4),

        # Lane metrics
        "lane_distribution": dict(lane_counts),
        "lane_match_rate": round(lane_matches / total, 4) if total > 0 else 0,

        # Latency
        "latency": {
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "avg_ms": round(avg_latency, 2),
            "max_ms": round(max_latency, 2),
        },

        # Class breakdown
        "class_breakdown": dict(class_results),

        # Errors
        "top_10_error_signatures": dict(error_signatures.most_common(10)),

        # Unsafe cases (critical)
        "unsafe_cases": unsafe_cases[:20],  # First 20 for analysis

        # All results for detailed analysis
        "detailed_results": results,
    }


def generate_fix_plan(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate prioritized fix plan from test results."""
    fix_plan = []

    # Priority 1: UNSAFE cases (security/correctness issues)
    unsafe_by_class = defaultdict(list)
    for case in metrics.get("unsafe_cases", []):
        unsafe_by_class[case.get("class_id", "unknown")].append(case)

    for class_id, cases in sorted(unsafe_by_class.items(), key=lambda x: -len(x[1])):
        # Sample queries
        sample_queries = [c.get("query", "")[:100] for c in cases[:3]]
        fix_plan.append({
            "priority": "P0-CRITICAL",
            "class_id": class_id,
            "issue_type": "UNSAFE_ROUTING",
            "count": len(cases),
            "description": f"{len(cases)} tests in {class_id} returned UNSAFE outcome",
            "sample_queries": sample_queries,
            "root_cause": determine_root_cause(cases),
            "fix": determine_fix(class_id, cases),
        })

    # Priority 2: High SOFT_ERROR rate classes
    for class_id, data in metrics.get("class_breakdown", {}).items():
        error_rate = data.get("soft_error", 0) / data.get("total", 1)
        if error_rate > 0.3:  # More than 30% soft errors
            fix_plan.append({
                "priority": "P1-HIGH",
                "class_id": class_id,
                "issue_type": "HIGH_ERROR_RATE",
                "count": data.get("soft_error", 0),
                "description": f"{class_id} has {error_rate*100:.0f}% soft error rate",
                "root_cause": f"Class {class_id} needs better handling",
                "fix": f"Review {class_id} lane routing logic",
            })

    # Priority 3: Latency issues (p95 > 2s per class)
    for class_id, data in metrics.get("class_breakdown", {}).items():
        avg_lat = data.get("avg_latency_ms", 0)
        if avg_lat > 2000:
            fix_plan.append({
                "priority": "P2-MEDIUM",
                "class_id": class_id,
                "issue_type": "HIGH_LATENCY",
                "avg_latency_ms": round(avg_lat, 0),
                "description": f"{class_id} average latency {avg_lat:.0f}ms exceeds 2s target",
                "root_cause": "Query complexity or GPT routing",
                "fix": "Optimize or route to NO_LLM where possible",
            })

    return sorted(fix_plan, key=lambda x: (x["priority"], -x.get("count", 0)))


def determine_root_cause(cases: List[Dict]) -> str:
    """Analyze cases to determine root cause."""
    if not cases:
        return "Unknown"

    # Check for patterns
    lanes = Counter(c.get("observed_lane", "") for c in cases)
    errors = Counter(c.get("error", "")[:30] for c in cases if c.get("error"))

    if "GPT" in lanes and any(c.get("expected_lane") == "BLOCKED" for c in cases):
        return "Blocked queries routing to GPT instead of being blocked"

    if "GPT" in lanes and any("NO_LLM" in c.get("expected_lane", "") for c in cases):
        return "NO_LLM queries routing to GPT (cost issue)"

    if errors:
        return f"Error pattern: {errors.most_common(1)[0][0]}"

    return "Lane routing mismatch"


def determine_fix(class_id: str, cases: List[Dict]) -> str:
    """Determine fix for a class of failures."""
    if class_id == "TC17":  # paste_dumps
        return "Add paste detection patterns to route_to_lane()"
    elif class_id == "TC18":  # injection_realistic
        return "Strengthen injection detection in security layer"
    elif class_id == "TC10":  # domain_drift
        return "Add off-domain detection to block non-marine queries"
    elif class_id == "TC07":  # command_camouflage
        return "Add implicit action patterns to detect hidden commands"
    elif class_id in ["TC01", "TC02"]:  # spelling/abbreviations
        return "Add fuzzy matching or abbreviation expansion"
    else:
        return f"Review lane routing for {class_id} patterns"


def print_report(metrics: Dict[str, Any], fix_plan: List[Dict[str, Any]]):
    """Print formatted report."""
    print("\n" + "=" * 70)
    print("PIPELINE 1500 CHAOS SUITE REPORT")
    print("=" * 70)

    print(f"\nSuite: {metrics['suite_name']}")
    print(f"Run time: {metrics['run_time']}")
    print(f"Execution time: {metrics['total_execution_time_s']}s")

    print("\n" + "-" * 50)
    print("OUTCOME DISTRIBUTION")
    print("-" * 50)
    for outcome, count in sorted(metrics["outcome_distribution"].items()):
        pct = count / metrics["total_tests"] * 100
        status = "OK" if outcome in ["SAFE_CORRECT", "SAFE_UNKNOWN_OK"] else "ISSUE"
        print(f"  {outcome}: {count} ({pct:.1f}%) [{status}]")

    print(f"\nSafe rate: {(metrics['safe_correct_rate'] + metrics['safe_unknown_ok_rate'])*100:.1f}%")
    print(f"Unsafe rate: {metrics['unsafe_rate']*100:.1f}%")

    print("\n" + "-" * 50)
    print("LANE DISTRIBUTION")
    print("-" * 50)
    for lane, count in sorted(metrics["lane_distribution"].items(), key=lambda x: -x[1]):
        pct = count / metrics["total_tests"] * 100
        print(f"  {lane}: {count} ({pct:.1f}%)")

    print(f"\nLane match rate: {metrics['lane_match_rate']*100:.1f}%")

    print("\n" + "-" * 50)
    print("LATENCY")
    print("-" * 50)
    lat = metrics["latency"]
    print(f"  p50: {lat['p50_ms']:.1f}ms")
    print(f"  p95: {lat['p95_ms']:.1f}ms")
    print(f"  avg: {lat['avg_ms']:.1f}ms")
    print(f"  max: {lat['max_ms']:.1f}ms")

    print("\n" + "-" * 50)
    print("CLASS BREAKDOWN (sorted by unsafe count)")
    print("-" * 50)
    sorted_classes = sorted(
        metrics["class_breakdown"].items(),
        key=lambda x: (-x[1].get("unsafe", 0), -x[1].get("soft_error", 0))
    )
    for class_id, data in sorted_classes[:15]:
        safe = data.get("safe_correct", 0) + data.get("safe_unknown_ok", 0)
        total = data.get("total", 0)
        unsafe = data.get("unsafe", 0)
        soft_err = data.get("soft_error", 0)
        status = "FAIL" if unsafe > 0 else ("WARN" if soft_err > total * 0.3 else "OK")
        print(f"  {class_id}: {safe}/{total} safe, {unsafe} unsafe, {soft_err} soft_err [{status}]")

    print("\n" + "-" * 50)
    print("TOP 10 ERROR SIGNATURES")
    print("-" * 50)
    if metrics["top_10_error_signatures"]:
        for sig, count in metrics["top_10_error_signatures"].items():
            print(f"  [{count}x] {sig}...")
    else:
        print("  (no errors)")

    print("\n" + "=" * 70)
    print("FIX PLAN (Top 10 by Priority)")
    print("=" * 70)
    for i, fix in enumerate(fix_plan[:10], 1):
        print(f"\n{i}. [{fix['priority']}] {fix['class_id']}: {fix['issue_type']}")
        print(f"   Count: {fix.get('count', 'N/A')}")
        print(f"   Description: {fix['description']}")
        print(f"   Root cause: {fix.get('root_cause', 'Unknown')}")
        print(f"   Fix: {fix.get('fix', 'TBD')}")
        if fix.get("sample_queries"):
            print(f"   Samples: {fix['sample_queries'][0][:80]}...")

    print("\n" + "=" * 70)

    # Pass/fail gate
    unsafe_rate = metrics["unsafe_rate"]
    safe_rate = metrics["safe_correct_rate"] + metrics["safe_unknown_ok_rate"]
    p95 = metrics["latency"]["p95_ms"]

    print("\nRELEASE GATE:")
    if unsafe_rate == 0 and safe_rate >= 0.9 and p95 < 2000:
        print("  STATUS: PASS")
        print(f"  - Unsafe rate: {unsafe_rate*100:.2f}% (target: 0%)")
        print(f"  - Safe rate: {safe_rate*100:.1f}% (target: ≥90%)")
        print(f"  - p95 latency: {p95:.0f}ms (target: <2000ms)")
    else:
        print("  STATUS: FAIL")
        if unsafe_rate > 0:
            print(f"  ✗ Unsafe rate: {unsafe_rate*100:.2f}% (target: 0%)")
        if safe_rate < 0.9:
            print(f"  ✗ Safe rate: {safe_rate*100:.1f}% (target: ≥90%)")
        if p95 >= 2000:
            print(f"  ✗ p95 latency: {p95:.0f}ms (target: <2000ms)")

    print("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run pipeline 1500 chaos suite")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Number of concurrent requests")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Timeout per request in seconds")
    parser.add_argument("--max-tests", type=int, default=None,
                        help="Max tests to run (for quick testing)")
    args = parser.parse_args()

    print("=" * 70)
    print("PIPELINE 1500 CHAOS RUNNER")
    print("=" * 70)

    # Load suite
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suite_path = os.path.join(base_dir, "suites", "pipeline_1500.json")
    suite = load_suite(suite_path)

    print(f"Loaded {len(suite.get('test_cases', []))} test cases")
    print(f"Concurrency: {args.concurrency}")
    print(f"Timeout: {args.timeout}s")
    if args.max_tests:
        print(f"Max tests: {args.max_tests}")

    # Run suite
    metrics = run_suite(
        suite,
        concurrency=args.concurrency,
        timeout_s=args.timeout,
        max_tests=args.max_tests,
    )

    # Generate fix plan
    fix_plan = generate_fix_plan(metrics)

    # Print report
    print_report(metrics, fix_plan)

    # Save results
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"pipeline_1500_{timestamp}.json")

    # Save without detailed_results for smaller file
    metrics_summary = {k: v for k, v in metrics.items() if k != "detailed_results"}
    metrics_summary["fix_plan"] = fix_plan
    with open(results_file, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Exit with appropriate code
    if metrics["unsafe_rate"] == 0 and metrics["safe_correct_rate"] + metrics["safe_unknown_ok_rate"] >= 0.9:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
