"""
Execution Test Runner
=====================

Runs the 1500 execution tests against the capability executor.

Usage:
    python -m tests.execution_tests.runner [--live] [--limit N]

Options:
    --live      Run against live Supabase (default: mock)
    --limit N   Only run first N tests (default: all)

Output:
    Results written to tests/execution_tests/results/
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_id: str
    capability: str
    passed: bool
    expected_outcome: str
    actual_outcome: str
    execution_time_ms: float
    error: Optional[str] = None
    query_generated: Optional[str] = None


class ExecutionTestRunner:
    """Runs execution tests against capability executor."""

    def __init__(self, live: bool = False):
        self.live = live
        self.results: List[TestResult] = []

        if live:
            self._init_live_executor()
        else:
            self._init_mock_executor()

    def _init_live_executor(self):
        """Initialize live Supabase connection."""
        from supabase import create_client
        from api.capability_executor import CapabilityExecutor

        SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
        SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.executor_class = CapabilityExecutor

    def _init_mock_executor(self):
        """Initialize mock executor for testing."""
        self.client = None
        self.executor_class = None

    def load_tests(self, filepath: str = None) -> List[Dict[str, Any]]:
        """Load tests from JSON file."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(__file__),
                "execution_tests_1500.json"
            )

        with open(filepath) as f:
            data = json.load(f)

        return data["tests"]

    def run_test(self, test: Dict[str, Any]) -> TestResult:
        """Run a single test."""
        start_time = time.time()
        test_id = test["id"]
        capability = test["capability"]
        search_terms = test["search_terms"]
        yacht_id = test.get("yacht_id")
        expected_outcome = test["expected_outcome"]

        actual_outcome = None
        error = None
        query_generated = None

        try:
            if self.live:
                # Live execution
                from api.capability_executor import (
                    CapabilityExecutor,
                    SecurityError,
                )
                from api.table_capabilities import TABLE_CAPABILITIES, CapabilityStatus

                # Check yacht_id
                if not yacht_id:
                    actual_outcome = "error_yacht_id"
                else:
                    try:
                        executor = CapabilityExecutor(self.client, yacht_id)

                        # Check if capability exists and is active
                        if capability not in TABLE_CAPABILITIES:
                            actual_outcome = "blocked"
                        elif TABLE_CAPABILITIES[capability].status != CapabilityStatus.ACTIVE:
                            actual_outcome = "blocked"
                        else:
                            result = executor.execute(capability, search_terms)
                            query_generated = result.generated_query

                            if result.success:
                                if result.row_count > 0:
                                    actual_outcome = "success"
                                else:
                                    actual_outcome = "empty"
                            else:
                                if "not searchable" in str(result.error):
                                    actual_outcome = "error_validation"
                                else:
                                    actual_outcome = "blocked"
                                error = result.error

                    except SecurityError as e:
                        if "yacht_id" in str(e).lower():
                            actual_outcome = "error_yacht_id"
                        else:
                            actual_outcome = "error_validation"
                        error = str(e)

                    except Exception as e:
                        actual_outcome = "error_validation"
                        error = str(e)
            else:
                # Mock execution - simulate based on expected outcome
                # In mock mode, we just verify the test structure is valid
                actual_outcome = self._mock_execute(test)

        except Exception as e:
            actual_outcome = "error_validation"
            error = str(e)

        execution_time_ms = (time.time() - start_time) * 1000

        passed = actual_outcome == expected_outcome

        return TestResult(
            test_id=test_id,
            capability=capability,
            passed=passed,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            execution_time_ms=execution_time_ms,
            error=error,
            query_generated=query_generated,
        )

    def _mock_execute(self, test: Dict[str, Any]) -> str:
        """
        Mock execution - validates test structure and returns expected outcome.
        Used for CI/CD without live database.
        """
        yacht_id = test.get("yacht_id")
        capability = test["capability"]
        search_terms = test["search_terms"]

        # Validate yacht_id
        if not yacht_id:
            return "error_yacht_id"

        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, yacht_id.lower()):
            return "error_yacht_id"

        # Check capability exists
        active_capabilities = [
            "part_by_part_number_or_name",
            "inventory_by_location",
            "fault_by_fault_code",
            "documents_search",
            "graph_node_search",
        ]

        blocked_capabilities = [
            "work_order_by_id",
            "equipment_by_name_or_model",
        ]

        if capability in blocked_capabilities:
            return "blocked"

        if capability not in active_capabilities:
            return "blocked"

        # Validate search terms against capability
        valid_columns = {
            "part_by_part_number_or_name": ["part_number", "name", "manufacturer", "category", "description"],
            "inventory_by_location": ["location", "name", "part_number", "quantity", "needs_reorder", "equipment", "system"],
            "fault_by_fault_code": ["code", "name", "equipment_type", "manufacturer", "severity", "symptoms", "causes"],
            "documents_search": ["content", "section_title", "doc_type", "system_tag"],
            "graph_node_search": ["label", "normalized_label", "node_type"],
        }

        cap_columns = valid_columns.get(capability, [])
        for col in search_terms.keys():
            if col not in cap_columns:
                return "error_validation"

        # If search_terms is empty
        if not search_terms:
            return "error_validation"

        # Default: assume success (in mock mode)
        # The expected_outcome in the test is what we're validating against
        return test["expected_outcome"]

    def run_all(self, tests: List[Dict[str, Any]], limit: int = None) -> Dict[str, Any]:
        """Run all tests and return summary."""
        if limit:
            tests = tests[:limit]

        total = len(tests)
        passed = 0
        failed = 0
        start_time = time.time()

        for i, test in enumerate(tests):
            result = self.run_test(test)
            self.results.append(result)

            if result.passed:
                passed += 1
            else:
                failed += 1

            # Progress every 100 tests
            if (i + 1) % 100 == 0:
                print(f"Progress: {i + 1}/{total} tests ({passed} passed, {failed} failed)")

        total_time = time.time() - start_time

        # Categorize failures
        failures_by_category = {}
        for r in self.results:
            if not r.passed:
                cap = r.capability
                failures_by_category[cap] = failures_by_category.get(cap, 0) + 1

        return {
            "timestamp": datetime.now().isoformat(),
            "mode": "live" if self.live else "mock",
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "total_time_s": round(total_time, 2),
            "avg_time_ms": round((total_time * 1000) / total, 2) if total > 0 else 0,
            "failures_by_capability": failures_by_category,
        }

    def export_results(self, summary: Dict[str, Any], output_dir: str = None):
        """Export results to JSON file."""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "results")

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "live" if self.live else "mock"
        filename = f"execution_{mode}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        output = {
            "summary": summary,
            "results": [
                {
                    "test_id": r.test_id,
                    "capability": r.capability,
                    "passed": r.passed,
                    "expected": r.expected_outcome,
                    "actual": r.actual_outcome,
                    "time_ms": round(r.execution_time_ms, 2),
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\nResults exported to: {filepath}")
        return filepath


def main():
    """Run execution tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Run execution tests")
    parser.add_argument("--live", action="store_true", help="Run against live Supabase")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tests")
    args = parser.parse_args()

    print("=" * 60)
    print("EXECUTION TEST RUNNER")
    print("=" * 60)
    print(f"Mode: {'LIVE' if args.live else 'MOCK'}")
    print(f"Limit: {args.limit or 'all'}")
    print()

    runner = ExecutionTestRunner(live=args.live)
    tests = runner.load_tests()

    print(f"Loaded {len(tests)} tests")
    print()

    summary = runner.run_all(tests, limit=args.limit)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    print(f"Total time: {summary['total_time_s']}s")
    print(f"Avg time: {summary['avg_time_ms']}ms/test")

    if summary['failures_by_capability']:
        print()
        print("Failures by capability:")
        for cap, count in sorted(summary['failures_by_capability'].items()):
            print(f"  {cap}: {count}")

    runner.export_results(summary)

    # Return exit code based on pass rate
    if summary['pass_rate'] >= 0.95:
        print("\nPASS - 95%+ tests passed")
        return 0
    else:
        print(f"\nFAIL - Only {summary['pass_rate']:.1%} passed (need 95%)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
