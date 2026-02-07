#!/usr/bin/env python3
"""
Comprehensive E2E Search Evaluation Harness
============================================

Runs ALL verified queries through the production API and captures:
- Results count and types
- Actions rendered (buttons)
- Domain/intent detection
- Latency (ms)
- Role-based differences
- Structured filters applied

Data Sources:
- tests/search/goldset.jsonl (888 queries)
- apps/api/scenario_matrix.json (220 scenarios)
- tests/e2e/search_ranking_roles.spec.ts test cases

Output:
- test-results/e2e_comprehensive/results.csv
- test-results/e2e_comprehensive/summary.json
- test-results/e2e_comprehensive/failures.jsonl

Usage:
    python scripts/eval/e2e_comprehensive_eval.py
    python scripts/eval/e2e_comprehensive_eval.py --sample 100
    python scripts/eval/e2e_comprehensive_eval.py --role captain
    python scripts/eval/e2e_comprehensive_eval.py --parallel 3
"""

import json
import csv
import time
import argparse
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

# Try to import supabase for auth
try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    print("WARNING: supabase not installed, using direct API calls")

# =============================================================================
# CONFIG
# =============================================================================

SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw"

API_URL = "https://pipeline-core.int.celeste7.ai/search"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test accounts - using verified working accounts
USERS = {
    "crew": {"email": "crew.test@alex-short.com", "password": "Password2!"},
    "hod": {"email": "hod.test@alex-short.com", "password": "Password2!"},
    "captain": {"email": "x@alex-short.com", "password": "Password2!"},
}

# Paths
ROOT = Path(__file__).parent.parent.parent
GOLDSET_PATH = ROOT / "tests/search/goldset_v3.jsonl"  # Use relabeled goldset v3 (fixed intents)
GOLDSET_V1_PATH = ROOT / "tests/search/goldset.jsonl"  # Fallback to v1
SCENARIO_MATRIX_PATH = ROOT / "apps/api/scenario_matrix.json"
OUTPUT_DIR = ROOT / "test-results/e2e_comprehensive"

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class QueryTestCase:
    """A single query test case."""
    query: str
    source: str  # 'goldset', 'scenario_matrix', 'manual'
    category: str
    expected_domain: Optional[str] = None
    expected_intent: Optional[str] = None
    expected_mode: Optional[str] = None  # 'focused' or 'explore'
    expected_action: Optional[str] = None
    expected_types: List[str] = field(default_factory=list)
    expected_filters: Optional[Dict[str, Any]] = None
    role: str = "crew"
    difficulty: int = 1
    notes: Optional[str] = None


@dataclass
class QueryResult:
    """Result of running a query through the API."""
    # Input
    query: str
    role: str
    source: str
    category: str

    # Expectations
    expected_domain: Optional[str]
    expected_intent: Optional[str]
    expected_mode: Optional[str]
    expected_action: Optional[str]

    # API Response
    status_code: int
    results_count: int
    actions_count: int
    actions_list: str  # comma-separated

    # Context detection (with confidence)
    detected_domain: Optional[str]
    detected_intent: Optional[str]
    detected_mode: Optional[str]
    domain_confidence: float
    intent_confidence: float

    # Matches
    domain_match: bool
    intent_match: bool
    mode_match: bool

    # Performance
    latency_ms: int

    # Result types
    result_types: str  # comma-separated
    top_result_type: Optional[str]
    top_result_title: Optional[str]

    # Status
    status: str  # 'pass', 'fail', 'error'
    error: Optional[str] = None

    # Timestamp
    timestamp: str = ""


# =============================================================================
# DATA LOADING
# =============================================================================

def load_goldset(path: Path) -> List[QueryTestCase]:
    """Load goldset.jsonl or goldset_v2.jsonl into test cases."""
    # Try v2 first, fallback to v1
    if not path.exists():
        if GOLDSET_V1_PATH.exists():
            print(f"WARNING: v2 goldset not found, falling back to v1")
            path = GOLDSET_V1_PATH
        else:
            print(f"WARNING: Goldset not found at {path}")
            return []

    cases = []
    with open(path, 'r') as f:
        for line in f:
            try:
                item = json.loads(line.strip())

                # Support both v1 (lens) and v2 (expected_domain) formats
                expected_domain = item.get('expected_domain', item.get('lens'))
                expected_intent = item.get('expected_intent', 'READ')
                expected_mode = item.get('expected_mode')
                expected_filters = item.get('expected_filters')

                cases.append(QueryTestCase(
                    query=item.get('query', ''),
                    source='goldset',
                    category=item.get('category', item.get('lens', 'unknown')),
                    expected_domain=expected_domain,
                    expected_intent=expected_intent,
                    expected_mode=expected_mode,
                    expected_action=item.get('button'),
                    expected_types=item.get('expected_object_types', []),
                    expected_filters=expected_filters,
                    role=item.get('role', 'crew'),
                    difficulty=item.get('difficulty', 1),
                    notes=item.get('notes'),
                ))
            except json.JSONDecodeError:
                continue

    return cases


def load_scenario_matrix(path: Path) -> List[QueryTestCase]:
    """Load scenario_matrix.json into test cases."""
    if not path.exists():
        print(f"WARNING: Scenario matrix not found at {path}")
        return []

    with open(path, 'r') as f:
        data = json.load(f)

    cases = []
    for category, scenarios in data.get('scenarios', {}).items():
        for scenario in scenarios:
            query = scenario.get('query', '')
            if not query or query.startswith('__GENERATE'):
                continue

            # Detect intent from expected_action or query
            expected_action = scenario.get('expected_action')
            intent = 'READ'
            if expected_action:
                if 'create' in expected_action or 'add' in expected_action:
                    intent = 'CREATE'
                elif 'update' in expected_action or 'edit' in expected_action:
                    intent = 'UPDATE'
                elif 'delete' in expected_action or 'remove' in expected_action:
                    intent = 'DELETE'
                elif 'export' in expected_action:
                    intent = 'EXPORT'
                elif 'approve' in expected_action or 'sign' in expected_action:
                    intent = 'APPROVE'

            cases.append(QueryTestCase(
                query=query,
                source='scenario_matrix',
                category=category,
                expected_domain=None,  # Scenario matrix doesn't specify domain
                expected_intent=intent,
                expected_action=expected_action,
                expected_types=[],
                role='crew',
                difficulty=2 if category == 'edge' else (3 if category in ['abuse', 'security'] else 1),
                notes=scenario.get('note'),
            ))

    return cases


def load_all_queries() -> List[QueryTestCase]:
    """Load all query sources."""
    all_cases = []

    # Load goldset
    goldset = load_goldset(GOLDSET_PATH)
    print(f"  Loaded {len(goldset)} queries from goldset.jsonl")
    all_cases.extend(goldset)

    # Load scenario matrix
    scenarios = load_scenario_matrix(SCENARIO_MATRIX_PATH)
    print(f"  Loaded {len(scenarios)} queries from scenario_matrix.json")
    all_cases.extend(scenarios)

    # Add manual test cases for comprehensive coverage
    manual_cases = [
        QueryTestCase(query="show me parts", source="manual", category="parts", expected_domain="part", expected_intent="READ"),
        QueryTestCase(query="receiving draft status", source="manual", category="receiving", expected_domain="receiving", expected_intent="READ"),
        QueryTestCase(query="hours of rest violations", source="manual", category="hours_of_rest", expected_domain="hours_of_rest", expected_intent="READ"),
        QueryTestCase(query="create work order for generator", source="manual", category="work_order", expected_domain="work_order", expected_intent="CREATE"),
        QueryTestCase(query="FLT-0170-576", source="manual", category="parts", expected_domain="part", expected_intent="READ"),
        QueryTestCase(query="watermaker 1 manual", source="manual", category="document", expected_domain="document", expected_intent="READ"),
        QueryTestCase(query="open faults", source="manual", category="fault", expected_domain="fault", expected_intent="READ"),
        QueryTestCase(query="low stock inventory", source="manual", category="inventory", expected_domain="inventory", expected_intent="READ"),
        QueryTestCase(query="main engine status", source="manual", category="equipment", expected_domain="equipment", expected_intent="READ"),
        QueryTestCase(query="update stock levels", source="manual", category="inventory", expected_domain="inventory", expected_intent="UPDATE"),
    ]
    print(f"  Added {len(manual_cases)} manual test cases")
    all_cases.extend(manual_cases)

    return all_cases


# =============================================================================
# AUTHENTICATION
# =============================================================================

def get_auth_token(role: str) -> Optional[str]:
    """Get auth token for a role."""
    if not HAS_SUPABASE:
        return None

    user = USERS.get(role)
    if not user:
        print(f"WARNING: Unknown role '{role}'")
        return None

    try:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        auth = client.auth.sign_in_with_password({
            "email": user["email"],
            "password": user["password"]
        })
        return auth.session.access_token
    except Exception as e:
        print(f"WARNING: Auth failed for {role}: {e}")
        return None


# =============================================================================
# API CALLS
# =============================================================================

def execute_query(
    query: str,
    token: str,
    yacht_id: str = YACHT_ID,
    limit: int = 10,
) -> Tuple[Dict[str, Any], int, int]:
    """
    Execute a search query against the API.

    Returns: (response_data, status_code, latency_ms)
    """
    start = time.time()

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "yacht_id": yacht_id,
                "limit": limit,
            },
            timeout=30,
        )

        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code == 200:
            return resp.json(), resp.status_code, latency_ms
        else:
            return {"error": resp.text}, resp.status_code, latency_ms

    except requests.Timeout:
        latency_ms = int((time.time() - start) * 1000)
        return {"error": "Timeout"}, 504, latency_ms
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"error": str(e)}, 500, latency_ms


def evaluate_query(
    test_case: QueryTestCase,
    token: str,
    role: str,
) -> QueryResult:
    """Evaluate a single query and return structured result."""

    # Execute query
    response, status_code, latency_ms = execute_query(test_case.query, token)

    # Parse response - check for actual error value, not just key existence
    if status_code != 200 or response.get("error"):
        return QueryResult(
            query=test_case.query,
            role=role,
            source=test_case.source,
            category=test_case.category,
            expected_domain=test_case.expected_domain,
            expected_intent=test_case.expected_intent,
            expected_mode=test_case.expected_mode,
            expected_action=test_case.expected_action,
            status_code=status_code,
            results_count=0,
            actions_count=0,
            actions_list="",
            detected_domain=None,
            detected_intent=None,
            detected_mode=None,
            domain_confidence=0.0,
            intent_confidence=0.0,
            domain_match=False,
            intent_match=False,
            mode_match=False,
            latency_ms=latency_ms,
            result_types="",
            top_result_type=None,
            top_result_title=None,
            status="error",
            error=response.get("error", "Unknown error"),
            timestamp=datetime.utcnow().isoformat(),
        )

    # Extract data
    context = response.get("context", {}) or {}
    results = response.get("results", []) or []
    actions = response.get("actions", []) or []

    detected_domain = context.get("domain")
    detected_intent = context.get("intent")
    detected_mode = context.get("mode")
    domain_confidence = context.get("domain_confidence", 0.0) or 0.0
    intent_confidence = context.get("intent_confidence", 0.0) or 0.0

    # Get result types
    result_types = [r.get("type", "unknown") for r in results]
    top_result = results[0] if results else {}

    # Check matches
    # Domain match: expected is None (any) OR matches detected
    domain_match = (
        test_case.expected_domain is None or
        detected_domain == test_case.expected_domain
    )

    # Intent match: expected is None (any) OR matches detected
    intent_match = (
        test_case.expected_intent is None or
        detected_intent == test_case.expected_intent
    )

    # Mode match: expected is None (any) OR matches detected
    mode_match = (
        test_case.expected_mode is None or
        detected_mode == test_case.expected_mode
    )

    # Determine status - now includes mode matching
    # Pass if domain, intent, and mode all match
    status = "pass" if (domain_match and intent_match and mode_match) else "fail"

    return QueryResult(
        query=test_case.query,
        role=role,
        source=test_case.source,
        category=test_case.category,
        expected_domain=test_case.expected_domain,
        expected_intent=test_case.expected_intent,
        expected_mode=test_case.expected_mode,
        expected_action=test_case.expected_action,
        status_code=status_code,
        results_count=len(results),
        actions_count=len(actions),
        actions_list=",".join([a.get("action", "") for a in actions]),
        detected_domain=detected_domain,
        detected_intent=detected_intent,
        detected_mode=detected_mode,
        domain_confidence=domain_confidence,
        intent_confidence=intent_confidence,
        domain_match=domain_match,
        intent_match=intent_match,
        mode_match=mode_match,
        latency_ms=latency_ms,
        result_types=",".join(set(result_types)),
        top_result_type=top_result.get("type"),
        top_result_title=top_result.get("title", top_result.get("payload", {}).get("title", ""))[:100] if top_result else None,
        status=status,
        error=None,
        timestamp=datetime.utcnow().isoformat(),
    )


# =============================================================================
# BATCH EVALUATION
# =============================================================================

def run_evaluation(
    test_cases: List[QueryTestCase],
    roles: List[str] = None,
    sample_size: Optional[int] = None,
    parallel: int = 1,
) -> Tuple[List[QueryResult], Dict[str, Any]]:
    """
    Run evaluation on all test cases for specified roles.

    Returns: (results_list, summary_dict)
    """
    if roles is None:
        roles = ["crew", "hod", "captain"]

    if sample_size:
        test_cases = test_cases[:sample_size]

    # Get tokens for all roles
    tokens = {}
    for role in roles:
        token = get_auth_token(role)
        if token:
            tokens[role] = token
            print(f"  ✓ Authenticated as {role}")
        else:
            print(f"  ✗ Failed to authenticate as {role}")

    if not tokens:
        print("ERROR: No valid tokens obtained")
        return [], {}

    # Run evaluations
    results = []
    total = len(test_cases) * len(tokens)
    completed = 0

    print(f"\nEvaluating {len(test_cases)} queries × {len(tokens)} roles = {total} total")
    print("-" * 70)

    start_time = time.time()

    for role, token in tokens.items():
        print(f"\n[{role.upper()}] Running {len(test_cases)} queries...")

        role_start = time.time()
        role_results = []

        for i, test_case in enumerate(test_cases):
            result = evaluate_query(test_case, token, role)
            role_results.append(result)
            completed += 1

            if (i + 1) % 50 == 0:
                elapsed = time.time() - role_start
                rate = (i + 1) / elapsed
                print(f"  [{i+1}/{len(test_cases)}] {rate:.1f} q/s | pass={sum(1 for r in role_results if r.status == 'pass')}")

        results.extend(role_results)

        # Role summary
        role_elapsed = time.time() - role_start
        role_pass = sum(1 for r in role_results if r.status == "pass")
        role_fail = sum(1 for r in role_results if r.status == "fail")
        role_error = sum(1 for r in role_results if r.status == "error")
        avg_latency = sum(r.latency_ms for r in role_results) / len(role_results) if role_results else 0

        print(f"  ✓ {role.upper()}: {role_pass} pass, {role_fail} fail, {role_error} error | avg latency: {avg_latency:.0f}ms | {role_elapsed:.1f}s")

    total_elapsed = time.time() - start_time

    # Build summary
    summary = build_summary(results, total_elapsed)

    return results, summary


def build_summary(results: List[QueryResult], elapsed_seconds: float) -> Dict[str, Any]:
    """Build summary statistics from results."""

    total = len(results)
    if total == 0:
        return {"error": "No results"}

    passes = sum(1 for r in results if r.status == "pass")
    fails = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")

    latencies = [r.latency_ms for r in results if r.status != "error"]

    # Domain/intent/mode accuracy
    domain_matches = sum(1 for r in results if r.domain_match and r.expected_domain is not None)
    domain_total = sum(1 for r in results if r.expected_domain is not None)

    intent_matches = sum(1 for r in results if r.intent_match and r.expected_intent is not None)
    intent_total = sum(1 for r in results if r.expected_intent is not None)

    mode_matches = sum(1 for r in results if r.mode_match and r.expected_mode is not None)
    mode_total = sum(1 for r in results if r.expected_mode is not None)

    # Average confidence scores
    domain_confidences = [r.domain_confidence for r in results if r.status != "error"]
    intent_confidences = [r.intent_confidence for r in results if r.status != "error"]

    # By role breakdown
    by_role = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "error": 0, "latency_sum": 0})
    for r in results:
        by_role[r.role]["total"] += 1
        by_role[r.role][r.status] += 1
        by_role[r.role]["latency_sum"] += r.latency_ms

    # By source breakdown
    by_source = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "error": 0})
    for r in results:
        by_source[r.source]["total"] += 1
        by_source[r.source][r.status] += 1

    # By category breakdown
    by_category = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "error": 0})
    for r in results:
        by_category[r.category]["total"] += 1
        by_category[r.category][r.status] += 1

    # Actions analysis
    queries_with_actions = sum(1 for r in results if r.actions_count > 0)
    all_actions = []
    for r in results:
        if r.actions_list:
            all_actions.extend(r.actions_list.split(","))
    action_counts = defaultdict(int)
    for a in all_actions:
        if a:
            action_counts[a] += 1

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "total_queries": total,
        "pass_count": passes,
        "fail_count": fails,
        "error_count": errors,
        "pass_rate": round(100 * passes / total, 1),
        "domain_accuracy": round(100 * domain_matches / domain_total, 1) if domain_total else None,
        "intent_accuracy": round(100 * intent_matches / intent_total, 1) if intent_total else None,
        "mode_accuracy": round(100 * mode_matches / mode_total, 1) if mode_total else None,
        "domain_confidence_avg": round(sum(domain_confidences) / len(domain_confidences), 2) if domain_confidences else 0,
        "intent_confidence_avg": round(sum(intent_confidences) / len(intent_confidences), 2) if intent_confidences else 0,
        "latency_mean_ms": round(sum(latencies) / len(latencies), 0) if latencies else 0,
        "latency_p50_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        "latency_p95_ms": sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0,
        "latency_max_ms": max(latencies) if latencies else 0,
        "queries_with_actions": queries_with_actions,
        "queries_with_actions_pct": round(100 * queries_with_actions / total, 1),
        "by_role": {
            role: {
                "total": data["total"],
                "pass_rate": round(100 * data["pass"] / data["total"], 1) if data["total"] else 0,
                "avg_latency_ms": round(data["latency_sum"] / data["total"], 0) if data["total"] else 0,
            }
            for role, data in by_role.items()
        },
        "by_source": {
            source: {
                "total": data["total"],
                "pass_rate": round(100 * data["pass"] / data["total"], 1) if data["total"] else 0,
            }
            for source, data in by_source.items()
        },
        "by_category_top10": dict(sorted(
            [(cat, round(100 * data["pass"] / data["total"], 1) if data["total"] else 0)
             for cat, data in by_category.items()],
            key=lambda x: -x[1]
        )[:10]),
        "top_actions": dict(sorted(action_counts.items(), key=lambda x: -x[1])[:15]),
    }


# =============================================================================
# OUTPUT
# =============================================================================

def save_results(
    results: List[QueryResult],
    summary: Dict[str, Any],
    output_dir: Path,
):
    """Save results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save CSV
    csv_path = output_dir / "results.csv"
    if results:
        fieldnames = list(asdict(results[0]).keys())
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(asdict(r))
        print(f"  ✓ Saved {len(results)} results to {csv_path}")

    # Save summary JSON
    summary_path = output_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Saved summary to {summary_path}")

    # Save failures
    failures = [r for r in results if r.status in ("fail", "error")]
    if failures:
        failures_path = output_dir / "failures.jsonl"
        with open(failures_path, 'w') as f:
            for r in failures:
                f.write(json.dumps(asdict(r)) + "\n")
        print(f"  ✓ Saved {len(failures)} failures to {failures_path}")

    # Save per-role CSVs
    roles = set(r.role for r in results)
    for role in roles:
        role_results = [r for r in results if r.role == role]
        role_path = output_dir / f"results_{role}.csv"
        with open(role_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in role_results:
                writer.writerow(asdict(r))
        print(f"  ✓ Saved {len(role_results)} {role} results to {role_path}")


def print_summary(summary: Dict[str, Any]):
    """Print summary to console."""
    print("\n" + "=" * 70)
    print(" E2E COMPREHENSIVE EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total queries:      {summary['total_queries']}")
    print(f"Pass rate:          {summary['pass_rate']}%")
    print(f"Domain accuracy:    {summary.get('domain_accuracy', 'N/A')}%")
    print(f"Intent accuracy:    {summary.get('intent_accuracy', 'N/A')}%")
    print(f"Mode accuracy:      {summary.get('mode_accuracy', 'N/A')}%")
    print(f"Domain confidence:  {summary.get('domain_confidence_avg', 0):.2f}")
    print(f"Intent confidence:  {summary.get('intent_confidence_avg', 0):.2f}")
    print(f"Queries w/ actions: {summary['queries_with_actions_pct']}%")
    print(f"Latency (mean):     {summary['latency_mean_ms']}ms")
    print(f"Latency (P95):      {summary['latency_p95_ms']}ms")
    print(f"Elapsed time:       {summary['elapsed_seconds']}s")

    print("\nBy Role:")
    for role, data in summary.get("by_role", {}).items():
        print(f"  {role:10} | {data['total']:4} queries | {data['pass_rate']:5.1f}% pass | {data['avg_latency_ms']:.0f}ms avg")

    print("\nBy Source:")
    for source, data in summary.get("by_source", {}).items():
        print(f"  {source:15} | {data['total']:4} queries | {data['pass_rate']:5.1f}% pass")

    print("\nTop Actions Rendered:")
    for action, count in list(summary.get("top_actions", {}).items())[:10]:
        print(f"  {action:30} | {count}")

    print("=" * 70)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Comprehensive E2E search evaluation")
    parser.add_argument("--sample", type=int, help="Sample N queries (for quick testing)")
    parser.add_argument("--role", choices=["crew", "hod", "captain"], help="Test single role only")
    parser.add_argument("--source", choices=["goldset", "scenario_matrix", "manual"], help="Filter by source")
    parser.add_argument("--parallel", type=int, default=1, help="Parallel workers (not yet implemented)")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    print("=" * 70)
    print(" COMPREHENSIVE E2E SEARCH EVALUATION")
    print("=" * 70)
    print(f"API: {API_URL}")
    print(f"Yacht: {YACHT_ID}")
    print(f"Output: {args.output}")
    print()

    # Load queries
    print("Loading queries...")
    all_cases = load_all_queries()
    print(f"  Total: {len(all_cases)} queries")

    # Filter by source if specified
    if args.source:
        all_cases = [c for c in all_cases if c.source == args.source]
        print(f"  Filtered to {len(all_cases)} from {args.source}")

    # Determine roles
    roles = [args.role] if args.role else ["crew", "hod", "captain"]
    print(f"\nRoles: {', '.join(roles)}")

    # Run evaluation
    print("\nAuthenticating...")
    results, summary = run_evaluation(
        all_cases,
        roles=roles,
        sample_size=args.sample,
        parallel=args.parallel,
    )

    # Save results
    print("\nSaving results...")
    save_results(results, summary, args.output)

    # Print summary
    print_summary(summary)

    # Exit code based on pass rate
    if summary.get("pass_rate", 0) >= 80:
        print("\n✅ EVALUATION PASSED (≥80% pass rate)")
        return 0
    else:
        print("\n❌ EVALUATION FAILED (<80% pass rate)")
        return 1


if __name__ == "__main__":
    exit(main())
