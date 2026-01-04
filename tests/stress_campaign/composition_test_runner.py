#!/usr/bin/env python3
"""
Composition Integration Test Runner
====================================

Tests capability composition (multi-entity queries).

Usage:
    python tests/stress_campaign/composition_test_runner.py
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.capability_composer import compose_search, MergeStrategy
from api.capability_observability import determine_outcome


# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def load_suite(suite_path: str) -> Dict[str, Any]:
    with open(suite_path) as f:
        return json.load(f)


def run_test(client, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single composition test."""
    test_id = test_case.get("id", "unknown")
    entities = test_case.get("entities", [])
    expect_caps = set(test_case.get("expect_capabilities", []))
    expect_blocked = set(test_case.get("expect_blocked", []))
    expect_min = test_case.get("expect_min_results", 0)
    expect_outcome = test_case.get("expect_outcome", "success")
    description = test_case.get("description", "")

    result = {
        "id": test_id,
        "description": description,
        "passed": False,
        "errors": [],
    }

    try:
        response = compose_search(
            client,
            TEST_YACHT_ID,
            entities,
            limit_per_capability=10,
        )

        # Check capabilities considered
        actual_caps = set(response.capabilities_considered)
        if actual_caps != expect_caps:
            result["errors"].append(
                f"Capabilities: expected {expect_caps}, got {actual_caps}"
            )

        # Check blocked capabilities
        actual_blocked = set(b["name"] for b in response.capabilities_blocked)
        if actual_blocked != expect_blocked:
            result["errors"].append(
                f"Blocked: expected {expect_blocked}, got {actual_blocked}"
            )

        # Check minimum results
        if response.total_count < expect_min:
            result["errors"].append(
                f"Results: expected >= {expect_min}, got {response.total_count}"
            )

        # Check outcome
        actual_outcome = determine_outcome(
            response.capabilities_considered,
            response.capabilities_executed,
            response.capabilities_blocked,
            response.total_count,
        )
        if actual_outcome != expect_outcome:
            result["errors"].append(
                f"Outcome: expected '{expect_outcome}', got '{actual_outcome}'"
            )

        # Pass if no errors
        result["passed"] = len(result["errors"]) == 0
        result["actual"] = {
            "capabilities": list(actual_caps),
            "blocked": list(actual_blocked),
            "results": response.total_count,
            "outcome": actual_outcome,
            "time_ms": response.total_execution_time_ms,
        }

    except Exception as e:
        result["errors"].append(f"Exception: {e}")

    return result


def main():
    print("=" * 60)
    print("COMPOSITION INTEGRATION TEST RUNNER")
    print("=" * 60)

    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Load suite
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suite_path = os.path.join(base_dir, "suites", "composition_integration.json")
    suite = load_suite(suite_path)

    test_cases = suite.get("test_cases", [])
    print(f"\nRunning {len(test_cases)} composition tests...")
    print("-" * 60)

    passed = 0
    failed = 0
    results = []

    for tc in test_cases:
        result = run_test(client, tc)
        results.append(result)

        if result["passed"]:
            passed += 1
            print(f"  ✓ {result['id']}: {result['description']}")
        else:
            failed += 1
            print(f"  ✗ {result['id']}: {result['description']}")
            for err in result["errors"]:
                print(f"    - {err}")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{len(test_cases)} ({passed/len(test_cases)*100:.1f}%)")
    print(f"Failed: {failed}")

    # Save results
    results_dir = os.path.join(base_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"composition_{timestamp}.json")

    with open(results_file, "w") as f:
        json.dump({
            "suite": suite.get("suite_name"),
            "run_time": datetime.now().isoformat(),
            "total": len(test_cases),
            "passed": passed,
            "failed": failed,
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
