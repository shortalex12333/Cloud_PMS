#!/usr/bin/env python3
"""
Capability Integration Test Runner
===================================

Runs integration tests against the capability execution layer.

Usage:
    python tests/stress_campaign/capability_test_runner.py [--suite SUITE] [--cap CAPABILITY]

Options:
    --suite SUITE      Suite file to run (default: capability_integration.json)
    --cap CAPABILITY   Only run tests for this capability
    --verbose          Show all test results, not just failures
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.table_capabilities import TABLE_CAPABILITIES, CapabilityStatus
from api.capability_executor import CapabilityExecutor, QueryResult
from api.result_normalizer import normalize_results, NormalizedResponse


# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def load_suite(suite_path: str) -> Dict[str, Any]:
    """Load a test suite from JSON file."""
    with open(suite_path) as f:
        return json.load(f)


def run_test(
    executor: CapabilityExecutor,
    test_case: Dict[str, Any],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run a single test case.

    Returns:
        Dict with pass/fail status and details
    """
    test_id = test_case.get("id", "unknown")
    capability = test_case.get("capability", "")
    search = test_case.get("search", {})
    expect_min = test_case.get("expect_min_results", 0)
    expect_table = test_case.get("expect_table", "")
    description = test_case.get("description", "")

    result = {
        "id": test_id,
        "capability": capability,
        "description": description,
        "passed": False,
        "error": None,
        "actual_count": 0,
        "expected_min": expect_min,
        "execution_time_ms": 0,
    }

    try:
        start = time.time()
        query_result = executor.execute(capability, search, limit=20)
        elapsed = (time.time() - start) * 1000

        result["execution_time_ms"] = elapsed
        result["actual_count"] = query_result.row_count

        if not query_result.success:
            result["error"] = query_result.error
            return result

        # Check table match
        if expect_table and query_result.table_name != expect_table:
            result["error"] = f"Expected table {expect_table}, got {query_result.table_name}"
            return result

        # Check minimum results
        if query_result.row_count >= expect_min:
            result["passed"] = True
        else:
            result["error"] = f"Expected >= {expect_min} results, got {query_result.row_count}"

        # Normalize results to verify contract
        normalized = normalize_results(query_result)
        if not normalized.success and query_result.success:
            result["error"] = f"Normalization failed: {normalized.error}"
            result["passed"] = False

        # Verify contract shape
        for nr in normalized.results:
            required_fields = ["source_table", "primary_id", "title", "snippet", "actions"]
            for field in required_fields:
                if not hasattr(nr, field):
                    result["error"] = f"Missing required field: {field}"
                    result["passed"] = False
                    break

    except Exception as e:
        result["error"] = str(e)

    return result


def run_suite(
    suite: Dict[str, Any],
    capability_filter: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run all tests in a suite."""
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    executor = CapabilityExecutor(client, TEST_YACHT_ID)

    test_cases = suite.get("test_cases", [])
    if capability_filter:
        test_cases = [t for t in test_cases if t.get("capability") == capability_filter]

    results = {
        "suite_name": suite.get("suite_name", "unknown"),
        "run_time": datetime.now().isoformat(),
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "by_capability": {},
        "failures": [],
        "execution_times": [],
    }

    print(f"\nRunning {len(test_cases)} tests...")
    print("-" * 60)

    for i, test_case in enumerate(test_cases):
        test_result = run_test(executor, test_case, verbose)

        # Track by capability
        cap = test_result["capability"]
        if cap not in results["by_capability"]:
            results["by_capability"][cap] = {"total": 0, "passed": 0, "failed": 0}
        results["by_capability"][cap]["total"] += 1

        if test_result["passed"]:
            results["passed"] += 1
            results["by_capability"][cap]["passed"] += 1
            if verbose:
                print(f"  ✓ {test_result['id']}: {test_result['description']}")
        else:
            results["failed"] += 1
            results["by_capability"][cap]["failed"] += 1
            results["failures"].append(test_result)
            print(f"  ✗ {test_result['id']}: {test_result['description']}")
            print(f"    Error: {test_result['error']}")

        results["execution_times"].append(test_result["execution_time_ms"])

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(test_cases)} tests complete")

    # Calculate stats
    if results["execution_times"]:
        results["avg_execution_ms"] = sum(results["execution_times"]) / len(results["execution_times"])
        results["max_execution_ms"] = max(results["execution_times"])
        results["min_execution_ms"] = min(results["execution_times"])
    else:
        results["avg_execution_ms"] = 0
        results["max_execution_ms"] = 0
        results["min_execution_ms"] = 0

    results["pass_rate"] = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0

    return results


def main():
    parser = argparse.ArgumentParser(description="Run capability integration tests")
    parser.add_argument("--suite", default="suites/capability_integration.json",
                        help="Suite file to run")
    parser.add_argument("--cap", default=None, help="Only run tests for this capability")
    parser.add_argument("--verbose", action="store_true", help="Show all test results")
    args = parser.parse_args()

    # Find suite file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suite_path = os.path.join(base_dir, args.suite)

    if not os.path.exists(suite_path):
        print(f"ERROR: Suite file not found: {suite_path}")
        sys.exit(1)

    print("=" * 60)
    print("CAPABILITY INTEGRATION TEST RUNNER")
    print("=" * 60)
    print(f"Suite: {args.suite}")
    print(f"Yacht: {TEST_YACHT_ID}")

    suite = load_suite(suite_path)
    results = run_suite(suite, args.cap, args.verbose)

    # Print summary
    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']} ({results['pass_rate']:.1f}%)")
    print(f"Failed: {results['failed']}")
    print()
    print("By capability:")
    for cap, stats in sorted(results["by_capability"].items()):
        pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✓" if stats["failed"] == 0 else "✗"
        print(f"  {status} {cap}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    print()
    print(f"Execution time: avg={results['avg_execution_ms']:.1f}ms, max={results['max_execution_ms']:.1f}ms")

    # Save results
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"capability_integration_{timestamp}.json")

    # Remove execution_times from saved results (too verbose)
    save_results = {k: v for k, v in results.items() if k != "execution_times"}
    with open(results_file, "w") as f:
        json.dump(save_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Exit code based on failures
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
