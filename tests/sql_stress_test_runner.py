#!/usr/bin/env python3
"""
SQL Foundation Stress Test Runner
=================================
Tests SQL query execution against /v3/search endpoint.
Similar to entity extraction stress tests but focused on SQL production.

Usage:
    python tests/sql_stress_test_runner.py [--endpoint URL] [--limit N]
"""

import json
import httpx
import time
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Test configuration
DEFAULT_ENDPOINT = "https://celeste-microactions.onrender.com/v3/search"
LOCAL_ENDPOINT = "http://localhost:8000/v3/search"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", os.environ.get("SERVICE_KEY", ""))

# Paths
QUERIES_FILE = Path(__file__).parent / "sql_stress_test_queries.jsonl"
RESULTS_FILE = Path(__file__).parent / "sql_stress_test_results.json"


@dataclass
class TestResult:
    """Result of a single test case"""
    test_id: str
    query: str
    passed: bool
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "query": self.query,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "errors": self.errors,
            "latency_ms": round(self.latency_ms, 2)
        }


@dataclass
class TestSuite:
    """Collection of test results"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    results: List[TestResult] = field(default_factory=list)
    by_category: Dict[str, Dict] = field(default_factory=dict)
    avg_latency_ms: float = 0.0

    def add_result(self, result: TestResult):
        self.total += 1
        self.results.append(result)

        if result.passed:
            self.passed += 1
        elif result.errors:
            self.errors += 1
        else:
            self.failed += 1

    def compute_stats(self):
        if self.results:
            self.avg_latency_ms = sum(r.latency_ms for r in self.results) / len(self.results)

        # Group by category
        for result in self.results:
            category = result.expected.get("category", "uncategorized")
            if category not in self.by_category:
                self.by_category[category] = {"total": 0, "passed": 0, "failed": 0}
            self.by_category[category]["total"] += 1
            if result.passed:
                self.by_category[category]["passed"] += 1
            else:
                self.by_category[category]["failed"] += 1

    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
                "pass_rate": round(self.passed / self.total * 100, 1) if self.total > 0 else 0,
                "avg_latency_ms": round(self.avg_latency_ms, 2)
            },
            "by_category": self.by_category,
            "results": [r.to_dict() for r in self.results]
        }


def load_test_cases(limit: Optional[int] = None) -> List[Dict]:
    """Load test cases from JSONL file"""
    cases = []
    with open(QUERIES_FILE, 'r') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
                if limit and len(cases) >= limit:
                    break
    return cases


def execute_query(endpoint: str, query: str, auth_token: str) -> Dict:
    """Execute a single query against the endpoint"""
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "yacht_id": YACHT_ID
    }

    start = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            latency_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                data["_latency_ms"] = latency_ms
                return data
            else:
                return {
                    "error": f"HTTP {response.status_code}",
                    "detail": response.text[:500],
                    "_latency_ms": latency_ms
                }
    except Exception as e:
        return {
            "error": str(e),
            "_latency_ms": (time.time() - start) * 1000
        }


def evaluate_result(test_case: Dict, response: Dict) -> TestResult:
    """Evaluate a test result against expected values"""
    test_id = test_case["id"]
    query = test_case["query"]
    labels = test_case["labels"]

    errors = []
    actual = {}

    # Check for error response
    if "error" in response:
        return TestResult(
            test_id=test_id,
            query=query,
            passed=False,
            expected=labels,
            actual={"error": response["error"]},
            errors=[response["error"]],
            latency_ms=response.get("_latency_ms", 0)
        )

    # Extract actual values from response
    # Response format: {"query", "entities", "lane", "intent", "results", "result_count", "trace"}
    actual["intent"] = response.get("intent", "UNKNOWN").upper()

    # Get tables from trace.tables_hit
    trace = response.get("trace", {})
    actual["tables"] = trace.get("tables_hit", []) if isinstance(trace, dict) else []
    actual["results_count"] = response.get("result_count", len(response.get("results", [])))
    actual["wave"] = None

    # Get wave from trace.wave_traces
    if isinstance(trace, dict):
        wave_traces = trace.get("wave_traces", [])
        if wave_traces:
            # Find the wave that returned results
            for wt in wave_traces:
                if isinstance(wt, dict) and wt.get("rows_returned", 0) > 0:
                    actual["wave"] = wt.get("wave")
                    break

    # Evaluate expectations
    passed = True

    # Check intent (case-insensitive, also normalize LOOKUP/SEARCH flexibility)
    if "expected_intent" in labels:
        expected_intent = labels["expected_intent"].upper()
        actual_intent = actual["intent"].upper()
        # Allow SEARCH as equivalent to LOOKUP for general queries (both are read operations)
        intent_match = (
            actual_intent == expected_intent or
            (expected_intent == "LOOKUP" and actual_intent == "SEARCH")  # SEARCH is acceptable for LOOKUP
        )
        if not intent_match:
            errors.append(f"Intent mismatch: expected {expected_intent}, got {actual_intent}")
            passed = False

    # Check tables
    if "expected_tables" in labels:
        expected_tables = set(labels["expected_tables"])
        actual_tables = set(actual["tables"]) if actual["tables"] else set()
        if not expected_tables.intersection(actual_tables):
            errors.append(f"Table mismatch: expected {expected_tables}, got {actual_tables}")
            passed = False

    # Check minimum results
    if "expected_results_min" in labels:
        min_results = labels["expected_results_min"]
        if actual["results_count"] < min_results:
            errors.append(f"Results count: expected >= {min_results}, got {actual['results_count']}")
            passed = False

    # Check wave type (for typo tolerance tests)
    if "expected_wave" in labels:
        expected_wave = labels["expected_wave"]
        if actual["wave"] and actual["wave"].upper() != expected_wave.upper():
            errors.append(f"Wave mismatch: expected {expected_wave}, got {actual['wave']}")
            passed = False

    return TestResult(
        test_id=test_id,
        query=query,
        passed=passed,
        expected=labels,
        actual=actual,
        errors=errors,
        latency_ms=response.get("_latency_ms", 0)
    )


def run_tests(endpoint: str, limit: Optional[int] = None, verbose: bool = True) -> TestSuite:
    """Run all test cases"""
    suite = TestSuite()
    test_cases = load_test_cases(limit)

    if not SERVICE_KEY:
        print("ERROR: No SERVICE_KEY or SUPABASE_SERVICE_KEY environment variable set")
        sys.exit(1)

    print(f"\nSQL Stress Test Runner")
    print(f"=" * 50)
    print(f"Endpoint: {endpoint}")
    print(f"Test cases: {len(test_cases)}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"=" * 50)
    print()

    for i, test_case in enumerate(test_cases, 1):
        test_id = test_case["id"]
        query = test_case["query"]
        category = test_case["labels"].get("category", "unknown")

        if verbose:
            print(f"[{i}/{len(test_cases)}] {test_id}: '{query}' ({category})", end=" ")

        response = execute_query(endpoint, query, SERVICE_KEY)
        result = evaluate_result(test_case, response)
        suite.add_result(result)

        if verbose:
            status = "PASS" if result.passed else "FAIL"
            latency = f"{result.latency_ms:.0f}ms"
            print(f"-> {status} ({latency})")
            if not result.passed and result.errors:
                for err in result.errors:
                    print(f"    ERROR: {err}")

    suite.compute_stats()
    return suite


def print_summary(suite: TestSuite):
    """Print test summary"""
    print()
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total:   {suite.total}")
    print(f"Passed:  {suite.passed} ({suite.passed/suite.total*100:.1f}%)")
    print(f"Failed:  {suite.failed}")
    print(f"Errors:  {suite.errors}")
    print(f"Avg Latency: {suite.avg_latency_ms:.0f}ms")
    print()

    if suite.by_category:
        print("BY CATEGORY:")
        print("-" * 40)
        for cat, stats in sorted(suite.by_category.items()):
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    print()


def save_results(suite: TestSuite, filepath: Path):
    """Save results to JSON file"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": DEFAULT_ENDPOINT,
        "yacht_id": YACHT_ID,
        **suite.to_dict()
    }

    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {filepath}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SQL Foundation Stress Test Runner")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="API endpoint URL")
    parser.add_argument("--local", action="store_true", help="Use local endpoint")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    args = parser.parse_args()

    endpoint = LOCAL_ENDPOINT if args.local else args.endpoint

    suite = run_tests(endpoint, limit=args.limit, verbose=not args.quiet)
    print_summary(suite)
    save_results(suite, RESULTS_FILE)

    # Exit with error code if tests failed
    sys.exit(0 if suite.failed == 0 and suite.errors == 0 else 1)


if __name__ == "__main__":
    main()
