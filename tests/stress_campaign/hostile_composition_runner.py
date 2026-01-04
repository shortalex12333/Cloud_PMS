#!/usr/bin/env python3
"""
Hostile Composition Test Runner
================================

Runs the hostile composition suite (160+ queries) to validate production safety.

Metrics captured:
- Error rate
- p50/p95 latency
- UNKNOWN rate
- Timeout rate
- Top failure signatures

Usage:
    python tests/stress_campaign/hostile_composition_runner.py
    python tests/stress_campaign/hostile_composition_runner.py --concurrency 10
"""

import json
import os
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter
import concurrent.futures

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.capability_composer import compose_search, MergeStrategy
from api.capability_observability import determine_outcome

# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def load_hostile_suite(suite_path: str) -> Dict[str, Any]:
    with open(suite_path) as f:
        return json.load(f)


def run_single_test(client, test_case: Dict[str, Any], timeout_ms: float = 5000.0) -> Dict[str, Any]:
    """Run a single hostile test case."""
    test_id = test_case.get("id", "unknown")
    entities = test_case.get("entities", [])
    category = test_case.get("category", "unknown")
    query = test_case.get("query", "")

    result = {
        "id": test_id,
        "category": category,
        "query": query[:100],  # Truncate for report
        "success": False,
        "latency_ms": 0.0,
        "outcome": "error",
        "error": None,
        "timed_out": False,
        "partial_results": False,
        "result_count": 0,
        "caps_executed": [],
        "caps_blocked": [],
        "caps_timed_out": [],
    }

    try:
        start = time.time()
        response = compose_search(
            supabase_client=client,
            yacht_id=TEST_YACHT_ID,
            entities=entities,
            limit_per_capability=10,
            merge_strategy=MergeStrategy.UNION,
            timeout_per_capability_ms=timeout_ms,
        )
        elapsed = (time.time() - start) * 1000

        result["success"] = response.success
        result["latency_ms"] = elapsed
        result["result_count"] = response.total_count
        result["caps_executed"] = response.capabilities_executed
        result["caps_blocked"] = [b["name"] for b in response.capabilities_blocked]
        result["caps_timed_out"] = [t["name"] for t in response.capabilities_timed_out]
        result["partial_results"] = response.partial_results
        result["timed_out"] = len(response.capabilities_timed_out) > 0

        # Determine outcome
        result["outcome"] = determine_outcome(
            response.capabilities_considered,
            response.capabilities_executed,
            response.capabilities_blocked,
            response.total_count,
        )

    except Exception as e:
        result["error"] = str(e)[:200]
        result["outcome"] = "error"

    return result


def run_hostile_suite(
    client,
    suite: Dict[str, Any],
    concurrency: int = 1,
    timeout_ms: float = 5000.0,
) -> Dict[str, Any]:
    """Run the full hostile suite and collect metrics."""
    test_cases = suite.get("test_cases", [])
    results = []

    print(f"\nRunning {len(test_cases)} hostile tests (concurrency={concurrency})...")
    print("-" * 60)

    start_time = time.time()

    if concurrency == 1:
        # Sequential execution
        for i, tc in enumerate(test_cases):
            result = run_single_test(client, tc, timeout_ms)
            results.append(result)

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"  Completed {i + 1}/{len(test_cases)}...")
    else:
        # Concurrent execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(run_single_test, client, tc, timeout_ms): tc
                for tc in test_cases
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    if completed % 20 == 0:
                        print(f"  Completed {completed}/{len(test_cases)}...")
                except Exception as e:
                    tc = futures[future]
                    results.append({
                        "id": tc.get("id", "unknown"),
                        "category": tc.get("category", "unknown"),
                        "success": False,
                        "outcome": "error",
                        "error": str(e),
                    })
                    completed += 1

    total_time = time.time() - start_time

    # Calculate metrics
    return calculate_metrics(results, total_time, suite)


def calculate_metrics(results: List[Dict], total_time: float, suite: Dict) -> Dict[str, Any]:
    """Calculate comprehensive metrics from test results."""

    total = len(results)

    # Success/failure counts
    successes = sum(1 for r in results if r.get("success", False))
    failures = sum(1 for r in results if not r.get("success", False))

    # Outcome distribution
    outcomes = Counter(r.get("outcome", "error") for r in results)

    # Error rate
    error_rate = failures / total if total > 0 else 0

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

    # UNKNOWN rate
    unknown_count = outcomes.get("unknown", 0)
    unknown_rate = unknown_count / total if total > 0 else 0

    # Timeout rate
    timeout_count = sum(1 for r in results if r.get("timed_out", False))
    timeout_rate = timeout_count / total if total > 0 else 0

    # Partial results rate
    partial_count = sum(1 for r in results if r.get("partial_results", False))
    partial_rate = partial_count / total if total > 0 else 0

    # Blocked capabilities summary
    blocked_caps = Counter()
    for r in results:
        for cap in r.get("caps_blocked", []):
            blocked_caps[cap] += 1

    # Timed out capabilities summary
    timed_out_caps = Counter()
    for r in results:
        for cap in r.get("caps_timed_out", []):
            timed_out_caps[cap] += 1

    # Top failure signatures
    error_signatures = Counter()
    for r in results:
        if r.get("error"):
            # Extract first 50 chars as signature
            sig = r["error"][:50]
            error_signatures[sig] += 1

    # Category breakdown
    category_results = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in category_results:
            category_results[cat] = {"total": 0, "success": 0, "latencies": []}
        category_results[cat]["total"] += 1
        if r.get("success", False):
            category_results[cat]["success"] += 1
        if r.get("latency_ms", 0) > 0:
            category_results[cat]["latencies"].append(r["latency_ms"])

    for cat, data in category_results.items():
        data["success_rate"] = data["success"] / data["total"] if data["total"] > 0 else 0
        data["avg_latency_ms"] = statistics.mean(data["latencies"]) if data["latencies"] else 0
        del data["latencies"]  # Remove raw data

    return {
        "suite_name": suite.get("suite_name", "hostile_composition"),
        "run_time": datetime.now().isoformat(),
        "total_execution_time_s": round(total_time, 2),

        # Core metrics
        "total_tests": total,
        "successes": successes,
        "failures": failures,
        "error_rate": round(error_rate, 4),

        # Latency
        "latency": {
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "avg_ms": round(avg_latency, 2),
            "max_ms": round(max_latency, 2),
        },

        # Outcomes
        "outcomes": dict(outcomes),
        "unknown_rate": round(unknown_rate, 4),

        # Timeouts
        "timeout_rate": round(timeout_rate, 4),
        "timeout_count": timeout_count,
        "timed_out_capabilities": dict(timed_out_caps.most_common(10)),

        # Partial results
        "partial_results_rate": round(partial_rate, 4),
        "partial_results_count": partial_count,

        # Blocked capabilities
        "blocked_capabilities": dict(blocked_caps.most_common(10)),

        # Failures
        "top_10_failure_signatures": dict(error_signatures.most_common(10)),

        # Category breakdown
        "category_breakdown": category_results,

        # Raw results for detailed analysis
        "detailed_results": results,
    }


def print_report(metrics: Dict[str, Any]):
    """Print a formatted report of the metrics."""
    print("\n" + "=" * 60)
    print("HOSTILE COMPOSITION SUITE REPORT")
    print("=" * 60)

    print(f"\nSuite: {metrics['suite_name']}")
    print(f"Run time: {metrics['run_time']}")
    print(f"Execution time: {metrics['total_execution_time_s']}s")

    print("\n" + "-" * 40)
    print("CORE METRICS")
    print("-" * 40)
    print(f"Total tests: {metrics['total_tests']}")
    print(f"Successes: {metrics['successes']}")
    print(f"Failures: {metrics['failures']}")
    print(f"Error rate: {metrics['error_rate'] * 100:.2f}%")

    print("\n" + "-" * 40)
    print("LATENCY")
    print("-" * 40)
    lat = metrics["latency"]
    print(f"p50: {lat['p50_ms']:.1f}ms")
    print(f"p95: {lat['p95_ms']:.1f}ms")
    print(f"avg: {lat['avg_ms']:.1f}ms")
    print(f"max: {lat['max_ms']:.1f}ms")

    print("\n" + "-" * 40)
    print("OUTCOMES")
    print("-" * 40)
    for outcome, count in metrics["outcomes"].items():
        pct = count / metrics["total_tests"] * 100
        print(f"  {outcome}: {count} ({pct:.1f}%)")

    print(f"\nUNKNOWN rate: {metrics['unknown_rate'] * 100:.2f}%")

    print("\n" + "-" * 40)
    print("TIMEOUTS")
    print("-" * 40)
    print(f"Timeout rate: {metrics['timeout_rate'] * 100:.2f}%")
    print(f"Timeout count: {metrics['timeout_count']}")
    if metrics["timed_out_capabilities"]:
        print("Timed out capabilities:")
        for cap, count in metrics["timed_out_capabilities"].items():
            print(f"  - {cap}: {count}")

    print("\n" + "-" * 40)
    print("PARTIAL RESULTS")
    print("-" * 40)
    print(f"Partial results rate: {metrics['partial_results_rate'] * 100:.2f}%")
    print(f"Partial results count: {metrics['partial_results_count']}")

    print("\n" + "-" * 40)
    print("BLOCKED CAPABILITIES")
    print("-" * 40)
    if metrics["blocked_capabilities"]:
        for cap, count in metrics["blocked_capabilities"].items():
            print(f"  - {cap}: {count} queries")
    else:
        print("  (none)")

    print("\n" + "-" * 40)
    print("TOP 10 FAILURE SIGNATURES")
    print("-" * 40)
    if metrics["top_10_failure_signatures"]:
        for sig, count in metrics["top_10_failure_signatures"].items():
            print(f"  [{count}x] {sig}...")
    else:
        print("  (no failures)")

    print("\n" + "-" * 40)
    print("CATEGORY BREAKDOWN")
    print("-" * 40)
    for cat, data in sorted(metrics["category_breakdown"].items()):
        success_pct = data["success_rate"] * 100
        print(f"  {cat}: {data['total']} tests, {success_pct:.0f}% success, {data['avg_latency_ms']:.0f}ms avg")

    print("\n" + "=" * 60)

    # Pass/Fail summary
    if metrics["error_rate"] < 0.05 and metrics["latency"]["p95_ms"] < 2000:
        print("RELEASE GATE: PASS")
        print("  - Error rate < 5%")
        print("  - p95 latency < 2s")
    else:
        print("RELEASE GATE: FAIL")
        if metrics["error_rate"] >= 0.05:
            print(f"  - Error rate {metrics['error_rate']*100:.1f}% >= 5%")
        if metrics["latency"]["p95_ms"] >= 2000:
            print(f"  - p95 latency {metrics['latency']['p95_ms']:.0f}ms >= 2000ms")

    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run hostile composition suite")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Number of concurrent requests")
    parser.add_argument("--timeout", type=float, default=5000.0,
                        help="Timeout per capability in ms")
    args = parser.parse_args()

    print("=" * 60)
    print("HOSTILE COMPOSITION RUNNER")
    print("=" * 60)

    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Load suite
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suite_path = os.path.join(base_dir, "suites", "hostile_composition.json")
    suite = load_hostile_suite(suite_path)

    print(f"Loaded {len(suite.get('test_cases', []))} test cases")
    print(f"Concurrency: {args.concurrency}")
    print(f"Timeout per capability: {args.timeout}ms")

    # Run suite
    metrics = run_hostile_suite(
        client, suite,
        concurrency=args.concurrency,
        timeout_ms=args.timeout
    )

    # Print report
    print_report(metrics)

    # Save results
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"hostile_{timestamp}.json")

    # Remove detailed_results for smaller file
    metrics_summary = {k: v for k, v in metrics.items() if k != "detailed_results"}
    with open(results_file, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Exit with appropriate code
    if metrics["error_rate"] < 0.05 and metrics["latency"]["p95_ms"] < 2000:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
