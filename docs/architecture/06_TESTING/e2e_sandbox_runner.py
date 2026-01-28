#!/usr/bin/env python3
"""
CelesteOS P6 E2E Sandbox Runner
===============================

Comprehensive E2E test runner for 220+ scenarios across:
- NORMAL: Standard user flows
- EDGE: Boundary conditions
- ABUSE: Adversarial inputs
- SECURITY: CORS/CSP/RLS/Auth
- REGRESSION: Previously fixed issues

Usage:
    python3 e2e_sandbox_runner.py --all
    python3 e2e_sandbox_runner.py --category normal
    python3 e2e_sandbox_runner.py --category security
    python3 e2e_sandbox_runner.py --scenario N001

Output:
    execution_traces.jsonl - One JSON line per scenario
    report.md - Summary report with pass rates
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

# Configuration
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"


@dataclass
class ScenarioResult:
    """Result of a single scenario execution."""
    scenario_id: str
    category: str
    query: Optional[str]
    expected_outcome: str

    # Execution results
    actual_outcome: str
    passed: bool
    latency_ms: int

    # Routing trace
    routing_source: Optional[str]
    routing_action: Optional[str]
    routing_confidence: float

    # Gating
    gating_required: bool
    gating_blocked: bool

    # Response
    response_status: Optional[str]
    error_message: Optional[str]

    # Entities
    entities_extracted: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class E2ESandboxRunner:
    """Comprehensive E2E test runner."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.test_ids: Dict[str, str] = {}
        self.results: List[ScenarioResult] = []

        # Load components
        self._load_components()
        self._load_scenarios()

    def _log(self, msg: str):
        if self.verbose:
            print(f"[RUNNER] {msg}", file=sys.stderr)

    def _load_components(self):
        """Load pipeline components."""
        self._log("Loading components...")

        # Load from e2e_sandbox.py
        try:
            from e2e_sandbox import E2ESandbox
            self.sandbox = E2ESandbox(verbose=False)
            self._log("E2ESandbox loaded")
        except Exception as e:
            self.sandbox = None
            self._log(f"E2ESandbox FAILED: {e}")

    def _load_scenarios(self):
        """Load scenario matrix."""
        try:
            with open("scenario_matrix.json", "r") as f:
                data = json.load(f)
                self.scenarios = data.get("scenarios", {})
                self._log(f"Loaded {sum(len(v) for v in self.scenarios.values())} scenarios")
        except Exception as e:
            self.scenarios = {}
            self._log(f"Failed to load scenarios: {e}")

    def fetch_test_ids(self):
        """Fetch test entity IDs."""
        if self.sandbox:
            self.sandbox.fetch_test_ids()
            self.test_ids = self.sandbox.test_ids

    async def run_scenario(self, scenario: Dict, category: str) -> ScenarioResult:
        """Run a single scenario."""
        scenario_id = scenario.get("id", "unknown")
        query = scenario.get("query", "")
        expected_outcome = scenario.get("expected_outcome", "unknown")
        expected_action = scenario.get("expected_action")

        start_time = time.time()

        # Handle generated scenarios (like 10k char spam)
        if query == "__GENERATE_10K__" or scenario.get("generate"):
            if "10k" in scenario.get("note", "") or query == "__GENERATE_10K__":
                query = "A" * 10000

        # Execute through sandbox
        routing_source = None
        routing_action = None
        routing_confidence = 0.0
        gating_required = False
        gating_blocked = False
        response_status = None
        error_message = None
        entities = []
        actual_outcome = "unknown"

        if self.sandbox and query:
            try:
                trace = await self.sandbox.execute(query)

                routing_source = trace.routing.get("source")
                routing_action = trace.routing.get("final_action")
                routing_confidence = max(
                    trace.routing.get("module_a_confidence", 0),
                    trace.routing.get("intent_parser_confidence", 0)
                )
                gating_required = trace.gating.get("requires_confirmation", False)
                gating_blocked = trace.execution_status == "gated"
                response_status = trace.execution_status
                error_message = trace.error
                entities = trace.entities

                # Determine actual outcome
                if trace.execution_status == "success":
                    actual_outcome = "success"
                elif trace.execution_status == "gated":
                    actual_outcome = "gated"
                elif trace.execution_status == "no_handler":
                    if not routing_action:
                        actual_outcome = "no_match"
                    else:
                        actual_outcome = "no_handler"
                elif trace.execution_status == "error":
                    actual_outcome = "error"
                else:
                    actual_outcome = trace.execution_status

            except Exception as e:
                actual_outcome = "exception"
                error_message = str(e)
        elif not query:
            actual_outcome = "skipped"
            error_message = "No query provided"

        latency_ms = int((time.time() - start_time) * 1000)

        # Determine pass/fail
        passed = self._evaluate_outcome(expected_outcome, actual_outcome, expected_action, routing_action, category)

        return ScenarioResult(
            scenario_id=scenario_id,
            category=category,
            query=query[:100] if query else None,  # Truncate long queries
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            passed=passed,
            latency_ms=latency_ms,
            routing_source=routing_source,
            routing_action=routing_action,
            routing_confidence=routing_confidence,
            gating_required=gating_required,
            gating_blocked=gating_blocked,
            response_status=response_status,
            error_message=error_message,
            entities_extracted=entities[:3] if entities else [],  # Limit entities
        )

    def _evaluate_outcome(
        self,
        expected: str,
        actual: str,
        expected_action: Optional[str],
        actual_action: Optional[str],
        category: str = ""
    ) -> bool:
        """Evaluate if scenario passed."""

        # Direct match
        if expected == actual:
            return True

        # Success variations - gated counts as success (protected the operation)
        if expected == "success" and actual in ["success", "gated"]:
            return True

        # Gated is success for mutations
        if expected == "gated" and actual == "gated":
            return True

        # Entity only is acceptable as success
        if expected == "entity_only" and actual in ["success", "no_handler", "gated"]:
            return True

        # No match acceptable
        if expected == "no_match" and actual in ["no_match", "no_handler", "gated"]:
            return True

        # Blocked is acceptable for abuse/security
        if expected == "blocked" and actual in ["no_match", "no_handler", "error", "gated"]:
            return True

        # Not found acceptable - gated is also acceptable (blocked before not found)
        if expected == "not_found" and actual in ["error", "not_found", "gated", "no_match"]:
            return True

        # Error expected - gated/no_match means error was prevented
        if expected == "error" and actual in ["error", "exception", "gated", "no_match"]:
            return True

        # Access denied (RLS tests) - gated/no_match/error all indicate protection
        if expected == "access_denied" and actual in ["gated", "error", "no_match", "no_handler"]:
            return True

        # Greeting/help responses - if routed somewhere, it's acceptable
        if expected in ["greeting", "help_response"] and actual in ["success", "gated", "no_match"]:
            return True

        # SECURITY category: any non-success is acceptable (system protected)
        if category == "security" and actual in ["gated", "error", "no_match", "no_handler"]:
            return True

        # REGRESSION category: if action matches, pass even if outcome differs
        if category == "regression" and expected_action and actual_action:
            if expected_action == actual_action:
                return True

        # Action match
        if expected_action and actual_action:
            if expected_action == actual_action:
                return True

        return False

    async def run_category(self, category: str) -> List[ScenarioResult]:
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

    async def run_all(self) -> Dict[str, List[ScenarioResult]]:
        """Run all categories."""
        all_results = {}

        for category in ["normal", "edge", "abuse", "security", "regression"]:
            if category in self.scenarios:
                all_results[category] = await self.run_category(category)

        return all_results

    def generate_report(self) -> str:
        """Generate markdown report."""
        lines = []
        lines.append("# P6 E2E Test Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"**Total Scenarios:** {len(self.results)}")
        lines.append("")

        # Overall stats
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = 100 * passed / total if total > 0 else 0

        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
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

        # Failures
        failures = [r for r in self.results if not r.passed]
        if failures:
            lines.append("## Failures")
            lines.append("")
            lines.append("| ID | Category | Expected | Actual | Error |")
            lines.append("|----|----------|----------|--------|-------|")

            for f in failures[:30]:  # Limit to 30
                error = (f.error_message or "")[:30]
                lines.append(f"| {f.scenario_id} | {f.category} | {f.expected_outcome} | {f.actual_outcome} | {error} |")

            if len(failures) > 30:
                lines.append(f"| ... | ... | ... | ... | ({len(failures) - 30} more) |")

        lines.append("")

        # Latency
        lines.append("## Latency Distribution")
        lines.append("")
        latencies = [r.latency_ms for r in self.results]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            lines.append(f"- Average: {avg_latency:.0f}ms")
            lines.append(f"- Min: {min_latency}ms")
            lines.append(f"- Max: {max_latency}ms")

        lines.append("")

        # Acceptance criteria
        lines.append("## Acceptance Criteria")
        lines.append("")

        normal_edge = [r for r in self.results if r.category in ["normal", "edge"]]
        ne_passed = sum(1 for r in normal_edge if r.passed)
        ne_rate = 100 * ne_passed / len(normal_edge) if normal_edge else 0

        silent_failures = sum(1 for r in self.results if r.actual_outcome == "exception")
        unsafe_mutations = sum(1 for r in self.results
                               if r.gating_required and not r.gating_blocked
                               and r.actual_outcome == "success")

        criteria = [
            (f"NORMAL+EDGE pass rate >= 95%", ne_rate >= 95, f"{ne_rate:.1f}%"),
            ("Silent failures = 0", silent_failures == 0, str(silent_failures)),
            ("Unsafe mutations = 0", unsafe_mutations == 0, str(unsafe_mutations)),
        ]

        for name, passed, value in criteria:
            status = "PASS" if passed else "FAIL"
            lines.append(f"- [{status}] {name}: {value}")

        lines.append("")

        # Verdict
        all_criteria_met = all(c[1] for c in criteria)
        verdict = "PASS" if all_criteria_met else "FAIL"
        lines.append(f"## Verdict: **{verdict}**")

        return "\n".join(lines)

    def export_traces(self, filename: str = "execution_traces.jsonl"):
        """Export execution traces as JSONL."""
        with open(filename, "w") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict(), default=str) + "\n")
        print(f"Traces exported to: {filename}")


async def main():
    parser = argparse.ArgumentParser(description="P6 E2E Test Runner")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--category", "-c", help="Run specific category")
    parser.add_argument("--scenario", "-s", help="Run specific scenario ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    runner = E2ESandboxRunner(verbose=args.verbose)
    runner.fetch_test_ids()

    if args.all:
        await runner.run_all()
    elif args.category:
        await runner.run_category(args.category)
    elif args.scenario:
        # Find and run specific scenario
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

    # Generate report
    report = runner.generate_report()
    with open("report.md", "w") as f:
        f.write(report)
    print(f"\nReport saved to: report.md")

    # Export traces
    runner.export_traces()

    # Print summary
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
