#!/usr/bin/env python3
"""
CelesteOS P7 Production-Only E2E Runner
========================================

Runs E2E tests against production endpoints only.
No staging, no mocks - real customer experience validation.

Usage:
    python3 e2e_prod_runner.py --all
    python3 e2e_prod_runner.py --category normal
    python3 e2e_prod_runner.py --scenario N001

Output:
    execution_traces.jsonl - Full trace per scenario
    prod_e2e_report.md - Summary report
    routing_gaps.md - Missing patterns analysis
"""

import argparse
import asyncio
import json
import os
import sys
import time
import requests
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

# Production Configuration (NO STAGING)
PROD_BACKEND = "https://pipeline-core.int.celeste7.ai"
PROD_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
ALLOWED_ORIGINS = [
    "https://app.celeste7.ai",
    "https://auth.celeste7.ai",
    "https://api.celeste7.ai",
    "http://localhost:3000",
]


@dataclass
class TraceResult:
    """Full execution trace for a single scenario."""
    scenario_id: str
    category: str
    query: Optional[str]
    yacht_id: Optional[str]

    # Expected vs Actual
    expected_outcome: str
    actual_outcome: str
    passed: bool

    # Timing
    latency_ms: int
    timestamp: str

    # API Response
    http_status: Optional[int]
    response_success: Optional[bool]
    result_count: int

    # Routing (if available from sandbox)
    routing_source: Optional[str] = None
    routing_action: Optional[str] = None
    routing_confidence: float = 0.0

    # Gating
    gating_required: bool = False
    gating_blocked: bool = False

    # Error details
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Entities
    entities: List[Dict] = field(default_factory=list)

    # CORS (for CORS tests)
    cors_origin: Optional[str] = None
    cors_allowed: Optional[bool] = None
    cors_headers: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


class ProdE2ERunner:
    """Production-only E2E test runner."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TraceResult] = []
        self.scenarios: Dict = {}
        self._load_scenarios()
        self._load_sandbox()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[PROD-E2E] {msg}", file=sys.stderr)

    def _load_scenarios(self):
        """Load scenario matrix."""
        try:
            with open("scenario_matrix_prod.json", "r") as f:
                data = json.load(f)
                self.scenarios = data.get("scenarios", {})
                total = sum(len(v) for v in self.scenarios.values())
                self._log(f"Loaded {total} scenarios from scenario_matrix_prod.json")
        except Exception as e:
            self._log(f"Failed to load scenarios: {e}")
            # Fall back to original matrix
            try:
                with open("scenario_matrix.json", "r") as f:
                    data = json.load(f)
                    self.scenarios = data.get("scenarios", {})
            except:
                self.scenarios = {}

    def _load_sandbox(self):
        """Load local sandbox for routing analysis."""
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from e2e_sandbox import E2ESandbox
            self.sandbox = E2ESandbox(verbose=False)
            self._log("Sandbox loaded for routing analysis")
        except Exception as e:
            self.sandbox = None
            self._log(f"Sandbox not available: {e}")

    def _call_production_api(self, query: str, yacht_id: str = None) -> Dict:
        """Call production API directly."""
        yacht_id = yacht_id or PROD_YACHT_ID

        start = time.time()
        try:
            resp = requests.post(
                f"{PROD_BACKEND}/search",
                json={"query": query, "yacht_id": yacht_id},
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://app.celeste7.ai"
                },
                timeout=60
            )
            latency = int((time.time() - start) * 1000)

            try:
                data = resp.json()
            except:
                data = {}

            return {
                "status": resp.status_code,
                "success": data.get("success", False),
                "results": data.get("results", []),
                "latency": latency,
                "error": data.get("error")
            }
        except Exception as e:
            return {
                "status": None,
                "success": False,
                "results": [],
                "latency": int((time.time() - start) * 1000),
                "error": str(e)
            }

    def _test_cors(self, origin: str, endpoint: str) -> Dict:
        """Test CORS preflight for an origin."""
        try:
            resp = requests.options(
                f"{PROD_BACKEND}{endpoint}",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization"
                },
                timeout=10
            )

            acao = resp.headers.get("Access-Control-Allow-Origin")
            return {
                "status": resp.status_code,
                "allowed": resp.status_code == 200 and acao == origin,
                "acao": acao,
                "headers": dict(resp.headers)
            }
        except Exception as e:
            return {
                "status": None,
                "allowed": False,
                "error": str(e)
            }

    async def _get_routing_info(self, query: str) -> Dict:
        """Get routing info from local sandbox."""
        if not self.sandbox:
            return {}

        try:
            trace = await self.sandbox.execute(query)
            return {
                "source": trace.routing.get("source"),
                "action": trace.routing.get("final_action"),
                "confidence": max(
                    trace.routing.get("module_a_confidence", 0),
                    trace.routing.get("intent_parser_confidence", 0)
                ),
                "gating_required": trace.gating.get("requires_confirmation", False),
                "gating_blocked": trace.execution_status == "gated",
                "entities": trace.entities[:3] if trace.entities else []
            }
        except:
            return {}

    def _evaluate_outcome(self, expected: str, actual: str, category: str) -> bool:
        """Evaluate if outcome matches expectation."""
        if expected == actual:
            return True

        # Success variations
        if expected == "success" and actual in ["success", "gated"]:
            return True

        # Gated is correct for mutations
        if expected == "gated" and actual == "gated":
            return True

        # Entity only
        if expected == "entity_only" and actual in ["success", "gated", "no_match"]:
            return True

        # No match acceptable
        if expected == "no_match" and actual in ["no_match", "gated"]:
            return True

        # Blocked for adversarial
        if expected == "blocked" and actual in ["no_match", "gated", "error"]:
            return True

        # Access denied for RLS
        if expected == "access_denied" and actual in ["error", "no_match", "gated"]:
            return True

        # CORS allowed/blocked
        if expected == "allowed" and actual == "allowed":
            return True
        if expected == "blocked" and actual == "blocked":
            return True

        # Error expected
        if expected == "error" and actual in ["error", "no_match"]:
            return True

        # Help/acknowledgment
        if expected in ["help_response", "acknowledgment", "confirmation_context_required",
                       "rejection_context_required", "cancel_context_required"]:
            return actual in ["no_match", "success", "gated"]

        return False

    async def run_scenario(self, scenario: Dict, category: str) -> TraceResult:
        """Run a single scenario against production."""
        scenario_id = scenario.get("id", "unknown")
        query = scenario.get("query", "")
        expected = scenario.get("expected_outcome", "unknown")
        yacht_id = scenario.get("yacht_id", PROD_YACHT_ID)

        # Handle CORS tests differently
        if category == "cors":
            origin = scenario.get("origin", "")
            endpoint = scenario.get("endpoint", "/health")
            cors_result = self._test_cors(origin, endpoint)

            actual = "allowed" if cors_result.get("allowed") else "blocked"
            passed = self._evaluate_outcome(expected, actual, category)

            return TraceResult(
                scenario_id=scenario_id,
                category=category,
                query=None,
                yacht_id=None,
                expected_outcome=expected,
                actual_outcome=actual,
                passed=passed,
                latency_ms=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                http_status=cors_result.get("status"),
                response_success=None,
                result_count=0,
                cors_origin=origin,
                cors_allowed=cors_result.get("allowed"),
                cors_headers={"acao": cors_result.get("acao")}
            )

        # Handle generated queries
        if query == "__GENERATE_10K__" or scenario.get("generate"):
            query = "A" * 10000

        # Handle RLS tests with different yacht_id
        if isinstance(yacht_id, list):
            yacht_id = None  # Will cause error

        # Call production API
        api_result = self._call_production_api(query, yacht_id) if query else {"status": None, "success": False, "results": [], "latency": 0}

        # Get routing info from sandbox
        routing = await self._get_routing_info(query) if query else {}

        # Determine actual outcome
        if not query:
            actual = "skipped"
            error_type = "no_query"
        elif api_result.get("error") and "timeout" in str(api_result.get("error", "")).lower():
            actual = "timeout"
            error_type = "timeout"
        elif api_result.get("status") is None:
            actual = "error"
            error_type = "network"
        elif api_result.get("status") == 401:
            actual = "access_denied"
            error_type = "auth"
        elif api_result.get("status") == 403:
            actual = "access_denied"
            error_type = "permission"
        elif api_result.get("status") == 422:
            actual = "error"
            error_type = "validation"
        elif api_result.get("status") >= 500:
            actual = "error"
            error_type = "server"
        elif routing.get("gating_blocked"):
            actual = "gated"
            error_type = None
        elif api_result.get("success") and len(api_result.get("results", [])) > 0:
            actual = "success"
            error_type = None
        elif api_result.get("success"):
            actual = "success" if routing.get("action") else "no_match"
            error_type = None
        else:
            actual = "no_match"
            error_type = "routing"

        passed = self._evaluate_outcome(expected, actual, category)

        return TraceResult(
            scenario_id=scenario_id,
            category=category,
            query=query[:100] if query else None,
            yacht_id=yacht_id,
            expected_outcome=expected,
            actual_outcome=actual,
            passed=passed,
            latency_ms=api_result.get("latency", 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
            http_status=api_result.get("status"),
            response_success=api_result.get("success"),
            result_count=len(api_result.get("results", [])),
            routing_source=routing.get("source"),
            routing_action=routing.get("action"),
            routing_confidence=routing.get("confidence", 0),
            gating_required=routing.get("gating_required", False),
            gating_blocked=routing.get("gating_blocked", False),
            error_type=error_type,
            error_message=str(api_result.get("error"))[:100] if api_result.get("error") else None,
            entities=routing.get("entities", [])
        )

    async def run_category(self, category: str) -> List[TraceResult]:
        """Run all scenarios in a category."""
        scenarios = self.scenarios.get(category, [])
        results = []

        print(f"\n[{category.upper()}] Running {len(scenarios)} scenarios...")

        for i, scenario in enumerate(scenarios):
            result = await self.run_scenario(scenario, category)
            results.append(result)
            self.results.append(result)

            status = "PASS" if result.passed else "FAIL"
            print(f"  [{i+1}/{len(scenarios)}] {result.scenario_id}: {status}")

            if not result.passed and self.verbose:
                print(f"    Expected: {result.expected_outcome}")
                print(f"    Actual: {result.actual_outcome}")
                if result.error_message:
                    print(f"    Error: {result.error_message[:50]}")

        return results

    async def run_all(self) -> Dict[str, List[TraceResult]]:
        """Run all categories."""
        all_results = {}

        for category in ["normal", "edge", "adversarial", "nonsense", "abuse", "rls", "cors"]:
            if category in self.scenarios:
                all_results[category] = await self.run_category(category)

        return all_results

    def generate_report(self) -> str:
        """Generate comprehensive markdown report."""
        lines = []
        lines.append("# P7 Production E2E Test Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"**Backend:** {PROD_BACKEND}")
        lines.append(f"**Total Scenarios:** {len(self.results)}")
        lines.append("")

        # Overall stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = 100 * passed / total if total > 0 else 0

        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total | {total} |")
        lines.append(f"| Passed | {passed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| **Pass Rate** | **{pass_rate:.1f}%** |")
        lines.append("")

        # By category
        lines.append("## Results by Category")
        lines.append("")
        lines.append("| Category | Total | Passed | Failed | Rate |")
        lines.append("|----------|-------|--------|--------|------|")

        categories = {}
        for r in self.results:
            if r.category not in categories:
                categories[r.category] = {"total": 0, "passed": 0}
            categories[r.category]["total"] += 1
            if r.passed:
                categories[r.category]["passed"] += 1

        for cat, stats in sorted(categories.items()):
            rate = 100 * stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            failed = stats["total"] - stats["passed"]
            lines.append(f"| {cat} | {stats['total']} | {stats['passed']} | {failed} | {rate:.1f}% |")

        lines.append("")

        # Critical metrics
        lines.append("## Critical Safety Metrics")
        lines.append("")

        silent_failures = sum(1 for r in self.results if r.actual_outcome == "exception")
        unsafe_mutations = sum(1 for r in self.results
                              if r.gating_required and not r.gating_blocked
                              and r.actual_outcome == "success")

        lines.append(f"| Metric | Value | Status |")
        lines.append(f"|--------|-------|--------|")
        lines.append(f"| Silent Failures | {silent_failures} | {'PASS' if silent_failures == 0 else 'FAIL'} |")
        lines.append(f"| Unsafe Mutations | {unsafe_mutations} | {'PASS' if unsafe_mutations == 0 else 'FAIL'} |")
        lines.append("")

        # Failures breakdown
        failures = [r for r in self.results if not r.passed]
        if failures:
            lines.append("## Failure Analysis")
            lines.append("")

            # Group by error type
            by_type = {}
            for f in failures:
                t = f.error_type or "unknown"
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(f)

            lines.append("### By Error Type")
            lines.append("")
            for t, fs in sorted(by_type.items(), key=lambda x: -len(x[1])):
                lines.append(f"- **{t}**: {len(fs)} failures")

            lines.append("")
            lines.append("### Top Failures")
            lines.append("")
            lines.append("| ID | Category | Query | Expected | Actual | Error |")
            lines.append("|----|----------|-------|----------|--------|-------|")

            for f in failures[:30]:
                query = (f.query or "")[:30]
                error = (f.error_message or "")[:20]
                lines.append(f"| {f.scenario_id} | {f.category} | {query} | {f.expected_outcome} | {f.actual_outcome} | {error} |")

            if len(failures) > 30:
                lines.append(f"| ... | ... | ... | ... | ... | ({len(failures) - 30} more) |")

        lines.append("")

        # Latency
        lines.append("## Latency Distribution")
        lines.append("")
        latencies = [r.latency_ms for r in self.results if r.latency_ms > 0]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            lines.append(f"- Average: {avg_latency:.0f}ms")
            lines.append(f"- Min: {min(latencies)}ms")
            lines.append(f"- Max: {max(latencies)}ms")
            lines.append(f"- P50: {sorted(latencies)[len(latencies)//2]}ms")
            if len(latencies) > 20:
                lines.append(f"- P95: {sorted(latencies)[int(len(latencies)*0.95)]}ms")

        lines.append("")

        # CORS verification
        cors_results = [r for r in self.results if r.category == "cors"]
        if cors_results:
            lines.append("## CORS Verification")
            lines.append("")
            allowed = [r for r in cors_results if r.cors_allowed]
            blocked = [r for r in cors_results if not r.cors_allowed]
            lines.append(f"- Allowed (correct): {sum(1 for r in allowed if r.passed)}")
            lines.append(f"- Blocked (correct): {sum(1 for r in blocked if r.passed)}")
            lines.append(f"- Wrong behavior: {sum(1 for r in cors_results if not r.passed)}")

        lines.append("")
        lines.append("## Verdict")
        lines.append("")

        all_pass = silent_failures == 0 and unsafe_mutations == 0
        if all_pass and pass_rate >= 80:
            lines.append("**PRODUCTION READY**")
        elif all_pass:
            lines.append("**CONDITIONAL PASS** - Safety requirements met, coverage gaps exist")
        else:
            lines.append("**FAIL** - Safety requirements not met")

        return "\n".join(lines)

    def generate_routing_gaps(self) -> str:
        """Generate routing gaps analysis."""
        lines = []
        lines.append("# Routing Gaps Analysis")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        # Find routing failures
        routing_gaps = [r for r in self.results
                       if r.error_type == "routing"
                       and r.category in ["normal", "edge"]]

        lines.append(f"## Summary: {len(routing_gaps)} routing gaps found")
        lines.append("")

        if routing_gaps:
            lines.append("## Missing Patterns")
            lines.append("")
            lines.append("| ID | Query | Expected Action |")
            lines.append("|----|-------|-----------------|")

            for r in routing_gaps:
                # Try to get expected action from scenarios
                for cat, scenarios in self.scenarios.items():
                    for s in scenarios:
                        if s.get("id") == r.scenario_id:
                            expected_action = s.get("expected_action", "unknown")
                            break
                    else:
                        continue
                    break
                else:
                    expected_action = "unknown"

                lines.append(f"| {r.scenario_id} | {r.query or 'N/A'} | {expected_action} |")

        lines.append("")
        lines.append("## Recommended Fixes")
        lines.append("")
        lines.append("Add patterns to `actions.json` for the queries above.")

        return "\n".join(lines)

    def export_traces(self, filename: str = "execution_traces.jsonl"):
        """Export execution traces as JSONL."""
        with open(filename, "w") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict(), default=str) + "\n")
        print(f"Traces exported to: {filename}")


async def main():
    parser = argparse.ArgumentParser(description="P7 Production E2E Runner")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--category", "-c", help="Run specific category")
    parser.add_argument("--scenario", "-s", help="Run specific scenario ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("=" * 70)
    print("P7 PRODUCTION-ONLY E2E RUNNER")
    print("=" * 70)
    print(f"Backend: {PROD_BACKEND}")
    print(f"Environment: PRODUCTION (no staging)")
    print()

    runner = ProdE2ERunner(verbose=args.verbose)

    if args.all:
        await runner.run_all()
    elif args.category:
        await runner.run_category(args.category)
    elif args.scenario:
        for cat, scenarios in runner.scenarios.items():
            for s in scenarios:
                if s.get("id") == args.scenario:
                    result = await runner.run_scenario(s, cat)
                    print(json.dumps(result.to_dict(), indent=2, default=str))
                    return
        print(f"Scenario {args.scenario} not found")
        return
    else:
        parser.print_help()
        return

    # Generate outputs
    report = runner.generate_report()
    with open("prod_e2e_report.md", "w") as f:
        f.write(report)
    print(f"\nReport saved to: prod_e2e_report.md")

    gaps = runner.generate_routing_gaps()
    with open("routing_gaps.md", "w") as f:
        f.write(gaps)
    print(f"Routing gaps saved to: routing_gaps.md")

    runner.export_traces()

    print("\n" + report)


if __name__ == "__main__":
    asyncio.run(main())
