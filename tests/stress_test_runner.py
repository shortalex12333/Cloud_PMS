#!/usr/bin/env python3
"""
CelesteOS Micro-Action Stress Test Runner
==========================================

Executes stress tests against the /extract endpoint with:
- JWT authentication
- Request throttling to avoid rate limits
- Detailed result collection
- Extraction quality analysis
- Failure detection and reporting
"""

import os
import sys
import json
import time
import jwt
import hashlib
import requests
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics

# ============================================================================
# CONFIGURATION
# ============================================================================

# Endpoint configuration
DEFAULT_ENDPOINT = "https://celeste-microactions.onrender.com"
LOCAL_ENDPOINT = "http://localhost:8000"

# Rate limiting: 100 requests/minute = 1.67 req/sec
# We'll use 1 req/sec to be safe (60 req/min)
REQUEST_DELAY_SECONDS = 1.0

# JWT configuration
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")
YACHT_SALT = os.getenv("YACHT_SALT", "test-yacht-salt")

# Default test identities
DEFAULT_USER_ID = "stress-test-user-001"
DEFAULT_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


# ============================================================================
# JWT TOKEN GENERATION
# ============================================================================

def generate_jwt(
    user_id: str = DEFAULT_USER_ID,
    yacht_id: str = DEFAULT_YACHT_ID,
    expires_in_hours: int = 1
) -> str:
    """Generate a valid JWT token for testing"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "yacht_id": yacht_id,
        "user_metadata": {"yacht_id": yacht_id},
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=expires_in_hours)).timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token


def generate_yacht_signature(yacht_id: str = DEFAULT_YACHT_ID) -> str:
    """Generate yacht signature for authentication"""
    return hashlib.sha256(f"{yacht_id}{YACHT_SALT}".encode()).hexdigest()


# ============================================================================
# TEST RESULT DATA STRUCTURES
# ============================================================================

@dataclass
class TestResult:
    """Result of a single test query"""
    query_id: str
    query: str
    expected_action: str
    expected_should_trigger: bool
    expected_entities: List[Dict]

    # Response data
    response_status: int = 0
    response_time_ms: int = 0
    response_lane: str = ""
    response_lane_reason: str = ""
    response_intent: str = ""
    response_entities: List[Dict] = field(default_factory=list)
    response_action: str = ""
    response_error: str = ""

    # Evaluation
    action_match: bool = False
    entity_coverage: float = 0.0
    lane_appropriate: bool = False
    is_pass: bool = False
    failure_reason: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TestSummary:
    """Summary of all test results"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    blocked: int = 0

    avg_response_time_ms: float = 0.0
    min_response_time_ms: int = 0
    max_response_time_ms: int = 0

    action_accuracy: float = 0.0
    entity_coverage_avg: float = 0.0
    lane_accuracy: float = 0.0

    failures_by_reason: Dict[str, int] = field(default_factory=dict)
    failures_by_action: Dict[str, int] = field(default_factory=dict)

    test_duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# TEST EXECUTION
# ============================================================================

class StressTestRunner:
    """Execute stress tests against the extraction endpoint"""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        user_id: str = DEFAULT_USER_ID,
        yacht_id: str = DEFAULT_YACHT_ID,
        delay_seconds: float = REQUEST_DELAY_SECONDS,
        verbose: bool = False
    ):
        self.endpoint = endpoint.rstrip('/')
        self.user_id = user_id
        self.yacht_id = yacht_id
        self.delay_seconds = delay_seconds
        self.verbose = verbose

        # Generate auth tokens
        self.jwt_token = generate_jwt(user_id, yacht_id)
        self.yacht_signature = generate_yacht_signature(yacht_id)

        # Results storage
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    def _make_request(self, query: str) -> Tuple[Dict, int, int]:
        """
        Make a request to the /extract endpoint

        Returns: (response_data, status_code, response_time_ms)
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
            "X-Yacht-Signature": self.yacht_signature,
        }

        payload = {
            "query": query,
            "include_embedding": False,  # Skip embedding for speed
            "include_metadata": True,
            "validate_combination": True,
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.endpoint}/extract",
                headers=headers,
                json=payload,
                timeout=30
            )
            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return response.json(), response.status_code, response_time_ms
            else:
                return {"error": response.text}, response.status_code, response_time_ms

        except requests.exceptions.Timeout:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {"error": "Request timeout"}, 0, response_time_ms
        except requests.exceptions.ConnectionError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {"error": f"Connection error: {str(e)}"}, 0, response_time_ms
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return {"error": str(e)}, 0, response_time_ms

    def _evaluate_result(
        self,
        test_data: Dict,
        response: Dict,
        status_code: int
    ) -> TestResult:
        """Evaluate a single test result"""
        labels = test_data["labels"]

        result = TestResult(
            query_id=test_data["id"],
            query=test_data["query"],
            expected_action=labels["expected_primary_action"],
            expected_should_trigger=labels["should_trigger_action"],
            expected_entities=labels.get("expected_entities", []),
            response_status=status_code,
        )

        # Handle errors
        if status_code != 200 or "error" in response:
            result.response_error = response.get("error", f"HTTP {status_code}")
            result.is_pass = False
            result.failure_reason = "request_error"
            return result

        # Extract response data
        result.response_lane = response.get("lane", "")
        result.response_lane_reason = response.get("lane_reason", "")
        result.response_intent = response.get("intent", "")
        result.response_entities = response.get("entities", [])
        result.response_action = response.get("command_action") or response.get("action", "")

        # Get latency from response metadata
        metadata = response.get("metadata", {})
        result.response_time_ms = metadata.get("latency_ms", 0)

        # Evaluate: Action match
        # For BLOCKED lane, check if blocking was appropriate
        if result.response_lane == "BLOCKED":
            block_reason = response.get("lane_reason", "")
            # If query shouldn't trigger action and is vague/non-domain, BLOCKED is correct
            if not result.expected_should_trigger and block_reason in ["too_vague", "non_domain", "paste_dump"]:
                result.action_match = True
                result.lane_appropriate = True
            else:
                result.action_match = False
                result.lane_appropriate = False
        else:
            # For NO_LLM/RULES_ONLY/GPT lanes
            if result.expected_action == "none_search_only":
                # Should NOT have triggered a command action
                result.action_match = not result.response_action or result.response_action == ""
            else:
                # Should have detected the expected action
                # Be lenient: check if expected action is substring or close match
                expected_lower = result.expected_action.lower()
                response_action_lower = result.response_action.lower() if result.response_action else ""
                response_intent_lower = result.response_intent.lower() if result.response_intent else ""

                result.action_match = (
                    expected_lower in response_action_lower or
                    expected_lower in response_intent_lower or
                    expected_lower.replace("_", "") in response_action_lower.replace("_", "") or
                    # Check for common mappings
                    (expected_lower == "create_work_order" and "create" in response_intent_lower and "work" in response_intent_lower) or
                    (expected_lower == "diagnose_fault" and "diagnose" in response_intent_lower) or
                    (expected_lower == "show_manual_section" and "document" in response_intent_lower) or
                    (expected_lower == "check_stock_level" and "stock" in response_intent_lower)
                )

            # Evaluate lane appropriateness
            if result.expected_should_trigger:
                # Should be in an action-triggering lane
                result.lane_appropriate = result.response_lane in ["NO_LLM", "RULES_ONLY", "GPT"]
            else:
                # Can be in any lane (search is valid)
                result.lane_appropriate = True

        # Evaluate: Entity coverage
        if result.expected_entities and result.response_entities:
            matches = 0
            for expected in result.expected_entities:
                expected_type = expected.get("type", "").lower()
                expected_hint = expected.get("value_hint", "").lower()

                for actual in result.response_entities:
                    actual_type = actual.get("type", "").lower()
                    actual_value = actual.get("value", "").lower()
                    actual_canonical = actual.get("canonical", "").lower()

                    # Check type match
                    type_match = (
                        expected_type == actual_type or
                        expected_type in actual_type or
                        actual_type in expected_type
                    )

                    # Check value match (lenient)
                    value_match = (
                        expected_hint in actual_value or
                        expected_hint in actual_canonical or
                        actual_value in expected_hint or
                        expected_hint.replace(" ", "_") in actual_canonical or
                        expected_hint.replace(" ", "") in actual_value.replace(" ", "")
                    )

                    if type_match and value_match:
                        matches += 1
                        break

            result.entity_coverage = matches / len(result.expected_entities)
        elif not result.expected_entities:
            result.entity_coverage = 1.0  # No entities expected
        else:
            result.entity_coverage = 0.0  # Expected entities but got none

        # Final pass/fail determination
        result.is_pass = result.action_match and result.lane_appropriate

        if not result.is_pass:
            if not result.action_match:
                result.failure_reason = "action_mismatch"
            elif not result.lane_appropriate:
                result.failure_reason = "lane_inappropriate"

        return result

    def run_tests(self, test_data_path: str, limit: int = None) -> TestSummary:
        """
        Run all tests from the JSONL file

        Args:
            test_data_path: Path to the JSONL test file
            limit: Optional limit on number of tests to run

        Returns:
            TestSummary with results
        """
        # Load test data
        tests = []
        with open(test_data_path, 'r') as f:
            for line in f:
                if line.strip():
                    tests.append(json.loads(line))

        if limit:
            tests = tests[:limit]

        print(f"\n{'='*60}")
        print(f"CelesteOS Stress Test Runner")
        print(f"{'='*60}")
        print(f"Endpoint: {self.endpoint}")
        print(f"Tests to run: {len(tests)}")
        print(f"Request delay: {self.delay_seconds}s")
        print(f"Estimated time: {len(tests) * self.delay_seconds / 60:.1f} minutes")
        print(f"{'='*60}\n")

        self.start_time = time.time()
        self.results = []

        for i, test in enumerate(tests):
            # Progress indicator
            if self.verbose or (i + 1) % 10 == 0:
                print(f"[{i+1}/{len(tests)}] Testing: {test['query'][:50]}...")

            # Make request
            response, status_code, response_time = self._make_request(test["query"])

            # Evaluate result
            result = self._evaluate_result(test, response, status_code)
            result.response_time_ms = response_time  # Use actual request time
            self.results.append(result)

            # Log failures in verbose mode
            if self.verbose and not result.is_pass:
                print(f"  ❌ FAIL: {result.failure_reason}")
                print(f"     Expected: {result.expected_action}, Got: {result.response_action or result.response_intent}")

            # Rate limiting delay
            if i < len(tests) - 1:  # Don't delay after last test
                time.sleep(self.delay_seconds)

        self.end_time = time.time()

        return self._generate_summary()

    def _generate_summary(self) -> TestSummary:
        """Generate summary statistics from results"""
        summary = TestSummary()
        summary.total_tests = len(self.results)
        summary.test_duration_seconds = self.end_time - self.start_time if self.end_time and self.start_time else 0

        # Count pass/fail
        for result in self.results:
            if result.response_error:
                summary.errors += 1
            elif result.response_lane == "BLOCKED":
                summary.blocked += 1
                if result.is_pass:
                    summary.passed += 1
                else:
                    summary.failed += 1
            elif result.is_pass:
                summary.passed += 1
            else:
                summary.failed += 1

                # Track failure reasons
                reason = result.failure_reason or "unknown"
                summary.failures_by_reason[reason] = summary.failures_by_reason.get(reason, 0) + 1

                # Track failures by expected action
                action = result.expected_action
                summary.failures_by_action[action] = summary.failures_by_action.get(action, 0) + 1

        # Response time stats
        response_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        if response_times:
            summary.avg_response_time_ms = statistics.mean(response_times)
            summary.min_response_time_ms = min(response_times)
            summary.max_response_time_ms = max(response_times)

        # Accuracy metrics
        if summary.total_tests > 0:
            action_correct = sum(1 for r in self.results if r.action_match)
            summary.action_accuracy = action_correct / summary.total_tests

            lane_correct = sum(1 for r in self.results if r.lane_appropriate)
            summary.lane_accuracy = lane_correct / summary.total_tests

            entity_scores = [r.entity_coverage for r in self.results]
            summary.entity_coverage_avg = statistics.mean(entity_scores) if entity_scores else 0

        return summary

    def save_results(self, output_path: str):
        """Save detailed results to JSON file"""
        output = {
            "summary": self._generate_summary().to_dict(),
            "results": [r.to_dict() for r in self.results],
            "config": {
                "endpoint": self.endpoint,
                "user_id": self.user_id,
                "yacht_id": self.yacht_id,
                "delay_seconds": self.delay_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"\nResults saved to: {output_path}")

    def print_summary(self, summary: TestSummary):
        """Print formatted summary"""
        print(f"\n{'='*60}")
        print("STRESS TEST RESULTS")
        print(f"{'='*60}")

        print(f"\n📊 Overall Results:")
        print(f"   Total tests:     {summary.total_tests}")
        print(f"   ✅ Passed:        {summary.passed} ({summary.passed/summary.total_tests*100:.1f}%)")
        print(f"   ❌ Failed:        {summary.failed} ({summary.failed/summary.total_tests*100:.1f}%)")
        print(f"   ⚠️  Errors:        {summary.errors}")
        print(f"   🚫 Blocked:       {summary.blocked}")

        print(f"\n⏱️  Response Times:")
        print(f"   Average:         {summary.avg_response_time_ms:.0f}ms")
        print(f"   Min:             {summary.min_response_time_ms}ms")
        print(f"   Max:             {summary.max_response_time_ms}ms")

        print(f"\n📈 Accuracy Metrics:")
        print(f"   Action accuracy:      {summary.action_accuracy*100:.1f}%")
        print(f"   Lane accuracy:        {summary.lane_accuracy*100:.1f}%")
        print(f"   Entity coverage avg:  {summary.entity_coverage_avg*100:.1f}%")

        if summary.failures_by_reason:
            print(f"\n❌ Failures by Reason:")
            for reason, count in sorted(summary.failures_by_reason.items(), key=lambda x: -x[1]):
                print(f"   {reason}: {count}")

        if summary.failures_by_action:
            print(f"\n❌ Failures by Expected Action (top 10):")
            for action, count in sorted(summary.failures_by_action.items(), key=lambda x: -x[1])[:10]:
                print(f"   {action}: {count}")

        print(f"\n⏰ Test Duration: {summary.test_duration_seconds:.1f}s")
        print(f"{'='*60}\n")

    def get_failed_results(self) -> List[TestResult]:
        """Get list of failed tests for analysis"""
        return [r for r in self.results if not r.is_pass]


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="CelesteOS Micro-Action Stress Test Runner")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint (default: {DEFAULT_ENDPOINT})"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local endpoint (localhost:8000)"
    )
    parser.add_argument(
        "--test-file",
        default="tests/stress_test_queries.jsonl",
        help="Path to test JSONL file"
    )
    parser.add_argument(
        "--output",
        default="tests/stress_test_results.json",
        help="Output file for results"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of tests to run"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SECONDS,
        help="Delay between requests in seconds"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test (20 queries, 0.5s delay)"
    )

    args = parser.parse_args()

    # Quick test mode
    if args.quick:
        args.limit = 20
        args.delay = 0.5
        args.verbose = True

    # Endpoint selection
    endpoint = LOCAL_ENDPOINT if args.local else args.endpoint

    # Create runner
    runner = StressTestRunner(
        endpoint=endpoint,
        delay_seconds=args.delay,
        verbose=args.verbose
    )

    # Run tests
    summary = runner.run_tests(args.test_file, limit=args.limit)

    # Print summary
    runner.print_summary(summary)

    # Save results
    runner.save_results(args.output)

    # Exit with appropriate code
    if summary.failed > summary.total_tests * 0.1:  # >10% failure rate
        print("⚠️  High failure rate detected!")
        sys.exit(1)
    else:
        print("✅ Test run complete!")
        sys.exit(0)


if __name__ == "__main__":
    main()
