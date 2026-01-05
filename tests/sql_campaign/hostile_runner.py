#!/usr/bin/env python3
"""
HOSTILE SQL TEST RUNNER
=======================
Red-team testing for SQL execution layer.
Optimizes for finding failures, not confirming success.
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

# Configuration
ENDPOINT = "https://celeste-microactions.onrender.com/v3/search"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SERVICE_KEY = os.environ.get("SERVICE_KEY", "")

# Severity levels
CRITICAL = "CRITICAL"  # Security bypass, must fix before prod
HIGH = "HIGH"          # Trust/security risk
MEDIUM = "MEDIUM"      # Quality degradation
LOW = "LOW"            # Edge case acceptable for v1

# Security keywords that should NEVER appear in results
FORBIDDEN_PATTERNS = [
    "fleet_registry",
    "password",
    "secret",
    "credential",
    "other-yacht",
    "DROP TABLE",
    "DELETE FROM",
]

# Keywords that indicate injection reached SQL
SQL_LEAK_PATTERNS = [
    "syntax error",
    "unterminated",
    "invalid input syntax",
    "column does not exist",
    "relation does not exist",
    "permission denied",
]


@dataclass
class HostileResult:
    test_id: str
    query: str
    severity: str
    passed: bool
    assumption_tested: str
    expected_behavior: str
    actual_behavior: str
    security_concern: Optional[str] = None
    raw_response: Optional[Dict] = None
    latency_ms: float = 0.0

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "query": self.query[:100] + "..." if len(self.query) > 100 else self.query,
            "severity": self.severity,
            "passed": self.passed,
            "assumption_tested": self.assumption_tested,
            "expected": self.expected_behavior,
            "actual": self.actual_behavior,
            "security_concern": self.security_concern,
            "latency_ms": round(self.latency_ms, 2)
        }


def execute_query(query: str) -> Dict:
    """Execute query and capture full response."""
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query": query, "yacht_id": YACHT_ID}

    start = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(ENDPOINT, json=payload, headers=headers)
            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                data["_latency_ms"] = latency
                data["_status_code"] = 200
                return data
            elif resp.status_code in (403, 422):
                # 403 = WAF blocked, 422 = validation error (e.g. empty query)
                # Treat both as BLOCKED for testing purposes
                return {
                    "lane": "BLOCKED",
                    "lane_reason": f"http_{resp.status_code}",
                    "results": [],
                    "result_count": 0,
                    "_error": f"HTTP {resp.status_code}",
                    "_body": resp.text[:500],
                    "_latency_ms": latency,
                    "_status_code": resp.status_code
                }
            else:
                return {
                    "_error": f"HTTP {resp.status_code}",
                    "_body": resp.text[:1000],
                    "_latency_ms": latency,
                    "_status_code": resp.status_code
                }
    except Exception as e:
        return {
            "_error": str(e),
            "_latency_ms": (time.time() - start) * 1000,
            "_status_code": 0
        }


def check_security_leak(response: Dict) -> Optional[str]:
    """Check if response contains forbidden data in ACTUAL RESULTS."""
    # If query was blocked, no data leak possible - this is correct behavior
    if response.get("lane") == "BLOCKED":
        return None

    # Only check the results array for actual data leakage
    results = response.get("results", [])
    if not results:
        return None  # No results = no data leak

    results_str = json.dumps(results).lower()

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in results_str:
            return f"FORBIDDEN PATTERN IN RESULTS: {pattern}"

    for pattern in SQL_LEAK_PATTERNS:
        if pattern.lower() in results_str:
            return f"SQL ERROR IN RESULTS: {pattern}"

    return None


def check_yacht_id_enforced(response: Dict) -> bool:
    """Verify yacht_id was enforced at SQL level."""
    trace = response.get("trace", {})
    security = trace.get("security", {})
    return security.get("yacht_id_enforced", False)


def check_parameterized(response: Dict) -> bool:
    """Verify query was parameterized."""
    trace = response.get("trace", {})
    security = trace.get("security", {})
    return security.get("parameterized", False)


def evaluate_security_test(test: Dict, response: Dict) -> HostileResult:
    """Evaluate a security-focused test."""
    test_id = test["id"]
    query = test["query"]
    labels = test["labels"]
    assumption = labels.get("assumption_tested", "unknown")
    expected_lane = labels.get("expected_lane", "").upper()

    latency = response.get("_latency_ms", 0)

    # Check for security leak
    leak = check_security_leak(response)
    if leak:
        return HostileResult(
            test_id=test_id,
            query=query,
            severity=CRITICAL,
            passed=False,
            assumption_tested=assumption,
            expected_behavior="No forbidden data in response",
            actual_behavior=leak,
            security_concern=leak,
            raw_response=response,
            latency_ms=latency
        )

    # If expected BLOCKED, verify it was blocked
    if expected_lane == "BLOCKED":
        actual_lane = response.get("lane", "").upper()

        # Check if blocked
        if actual_lane == "BLOCKED":
            return HostileResult(
                test_id=test_id,
                query=query,
                severity=LOW,
                passed=True,
                assumption_tested=assumption,
                expected_behavior="Query blocked",
                actual_behavior=f"Correctly blocked (lane={actual_lane})",
                latency_ms=latency
            )

        # Not blocked - check if it returned dangerous results
        results = response.get("results", [])
        result_count = response.get("result_count", len(results))

        if result_count > 0:
            # Returned results for something that should be blocked
            return HostileResult(
                test_id=test_id,
                query=query,
                severity=HIGH,
                passed=False,
                assumption_tested=assumption,
                expected_behavior="Query blocked, no results",
                actual_behavior=f"NOT BLOCKED! Lane={actual_lane}, results={result_count}",
                security_concern="Injection/attack query returned results",
                raw_response=response,
                latency_ms=latency
            )
        else:
            # Not blocked but no results - medium concern
            return HostileResult(
                test_id=test_id,
                query=query,
                severity=MEDIUM,
                passed=False,
                assumption_tested=assumption,
                expected_behavior="Query blocked",
                actual_behavior=f"Not blocked but no results (lane={actual_lane})",
                security_concern="Attack query not explicitly blocked",
                latency_ms=latency
            )

    # For non-security tests, check basic expectations
    return evaluate_functional_test(test, response)


def evaluate_functional_test(test: Dict, response: Dict) -> HostileResult:
    """Evaluate a functional test."""
    test_id = test["id"]
    query = test["query"]
    labels = test["labels"]
    assumption = labels.get("assumption_tested", "unknown")
    expected_intent = labels.get("expected_intent", "").upper()
    expected_tables = labels.get("expected_tables", [])
    expected_filters = labels.get("expected_filters", labels.get("expected_filter"))

    latency = response.get("_latency_ms", 0)
    actual_intent = response.get("intent", "").upper()
    actual_lane = response.get("lane", "").upper()

    trace = response.get("trace", {})
    tables_hit = trace.get("tables_hit", [])
    result_count = response.get("result_count", 0)

    errors = []
    severity = LOW

    # Check yacht_id enforcement
    if not check_yacht_id_enforced(response):
        errors.append("yacht_id NOT enforced at SQL level")
        severity = CRITICAL

    # Check parameterization
    if not check_parameterized(response):
        errors.append("Query NOT parameterized")
        severity = max(severity, HIGH, key=lambda x: [LOW, MEDIUM, HIGH, CRITICAL].index(x))

    # Check intent
    if expected_intent and actual_intent != expected_intent:
        # Allow SEARCH for LOOKUP as acceptable
        if not (expected_intent == "LOOKUP" and actual_intent == "SEARCH"):
            errors.append(f"Intent mismatch: expected {expected_intent}, got {actual_intent}")
            severity = max(severity, MEDIUM, key=lambda x: [LOW, MEDIUM, HIGH, CRITICAL].index(x))

    # Check tables
    if expected_tables:
        if not any(t in tables_hit for t in expected_tables):
            errors.append(f"Table mismatch: expected one of {expected_tables}, got {tables_hit}")
            severity = max(severity, MEDIUM, key=lambda x: [LOW, MEDIUM, HIGH, CRITICAL].index(x))

    # Check filters - THIS IS CRITICAL
    if expected_filters:
        # Currently we have no way to verify filters were applied
        # This is a DESIGN GAP
        errors.append(f"UNVERIFIABLE: Cannot confirm filters {expected_filters} applied at SQL level")
        severity = max(severity, HIGH, key=lambda x: [LOW, MEDIUM, HIGH, CRITICAL].index(x))

    if errors:
        return HostileResult(
            test_id=test_id,
            query=query,
            severity=severity,
            passed=False,
            assumption_tested=assumption,
            expected_behavior=f"Intent={expected_intent}, Tables={expected_tables}",
            actual_behavior=f"Intent={actual_intent}, Tables={tables_hit}, Errors: {'; '.join(errors)}",
            security_concern=errors[0] if "yacht_id" in errors[0].lower() or "parameterized" in errors[0].lower() else None,
            latency_ms=latency
        )

    return HostileResult(
        test_id=test_id,
        query=query,
        severity=LOW,
        passed=True,
        assumption_tested=assumption,
        expected_behavior=f"Intent={expected_intent}, Tables={expected_tables}",
        actual_behavior=f"Intent={actual_intent}, Tables={tables_hit}, Results={result_count}",
        latency_ms=latency
    )


def run_hostile_tests(test_file: Path, limit: Optional[int] = None) -> List[HostileResult]:
    """Run hostile test suite."""
    results = []

    with open(test_file, 'r') as f:
        tests = [json.loads(line) for line in f if line.strip()]

    if limit:
        tests = tests[:limit]

    print(f"\n{'='*60}")
    print("HOSTILE SQL TEST RUNNER")
    print(f"{'='*60}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Tests: {len(tests)}")
    print(f"{'='*60}\n")

    critical_failures = []
    high_failures = []

    for i, test in enumerate(tests, 1):
        test_id = test["id"]
        query = test["query"][:50] + "..." if len(test["query"]) > 50 else test["query"]
        category = test["labels"].get("category", "unknown")

        print(f"[{i}/{len(tests)}] {test_id}: {query!r} ({category})", end=" ")

        response = execute_query(test["query"])

        # Determine if security or functional test
        if test["labels"].get("expected_lane") == "BLOCKED" or "injection" in category or "security" in category:
            result = evaluate_security_test(test, response)
        else:
            result = evaluate_functional_test(test, response)

        results.append(result)

        status = "PASS" if result.passed else f"FAIL[{result.severity}]"
        print(f"-> {status} ({result.latency_ms:.0f}ms)")

        if not result.passed:
            print(f"    ASSUMPTION: {result.assumption_tested}")
            print(f"    EXPECTED: {result.expected_behavior}")
            print(f"    ACTUAL: {result.actual_behavior}")
            if result.security_concern:
                print(f"    ⚠️  SECURITY: {result.security_concern}")

            if result.severity == CRITICAL:
                critical_failures.append(result)
            elif result.severity == HIGH:
                high_failures.append(result)

    return results


def print_report(results: List[HostileResult]):
    """Print hostile test report."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    by_severity = {}
    for r in results:
        if not r.passed:
            by_severity.setdefault(r.severity, []).append(r)

    print(f"\n{'='*60}")
    print("HOSTILE TEST REPORT")
    print(f"{'='*60}")
    print(f"Total:    {total}")
    print(f"Passed:   {passed} ({passed/total*100:.1f}%)")
    print(f"Failed:   {failed} ({failed/total*100:.1f}%)")
    print()

    print("FAILURES BY SEVERITY:")
    print("-" * 40)
    for sev in [CRITICAL, HIGH, MEDIUM, LOW]:
        failures = by_severity.get(sev, [])
        if failures:
            print(f"  {sev}: {len(failures)}")
            for f in failures[:5]:  # Show first 5
                print(f"    - {f.test_id}: {f.assumption_tested}")
            if len(failures) > 5:
                print(f"    ... and {len(failures)-5} more")

    print()

    # Critical findings
    critical = by_severity.get(CRITICAL, [])
    if critical:
        print("🚨 CRITICAL FINDINGS - MUST FIX BEFORE PRODUCTION:")
        print("=" * 60)
        for f in critical:
            print(f"  {f.test_id}: {f.query[:60]}")
            print(f"    Assumption violated: {f.assumption_tested}")
            print(f"    Security concern: {f.security_concern}")
            print()

    high = by_severity.get(HIGH, [])
    if high:
        print("⚠️  HIGH SEVERITY FINDINGS:")
        print("-" * 60)
        for f in high[:10]:
            print(f"  {f.test_id}: {f.assumption_tested}")
        if len(high) > 10:
            print(f"  ... and {len(high)-10} more")

    print()


def save_results(results: List[HostileResult], output_file: Path):
    """Save results to JSON."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": ENDPOINT,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "critical": sum(1 for r in results if not r.passed and r.severity == CRITICAL),
            "high": sum(1 for r in results if not r.passed and r.severity == HIGH),
        },
        "results": [r.to_dict() for r in results]
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {output_file}")


def main():
    if not SERVICE_KEY:
        print("ERROR: SERVICE_KEY environment variable not set")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit tests to run")
    parser.add_argument("--test-file", default="hostile_tests.jsonl")
    args = parser.parse_args()

    test_file = Path(__file__).parent / args.test_file
    output_file = Path(__file__).parent / "reports" / f"hostile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(exist_ok=True)

    results = run_hostile_tests(test_file, limit=args.limit)
    print_report(results)
    save_results(results, output_file)

    # Exit with error if critical failures
    critical = sum(1 for r in results if not r.passed and r.severity == CRITICAL)
    sys.exit(1 if critical > 0 else 0)


if __name__ == "__main__":
    main()
