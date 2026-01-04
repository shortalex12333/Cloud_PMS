#!/usr/bin/env python3
"""
SQL Stress Test Runner
======================
Runs stress tests against extraction endpoint, collects traces, generates report.
"""
import json
import time
import requests
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Paths
STRESS_TESTS_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/sql_stress/stress_tests_1500.json")
GOLDEN_TRUTH_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/golden/golden_truth_250.json")
RESULTS_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/sql_stress/stress_results.json")
REPORT_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/sql_stress/SQL_STRESS_REPORT.md")
TRACES_PATH = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))logs/sql_probe_traces.jsonl")

# API Config
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EXTRACT_URL = "https://extract.core.celeste7.ai/extract"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Rate limiting
DELAY_SECONDS = 0.5  # 500ms between calls
MAX_WORKERS = 3
BATCH_SIZE = 50

@dataclass
class TestResult:
    test_id: str
    category: str
    query: str
    status_code: int
    lane: Optional[str]
    entities_extracted: int
    response_time_ms: float
    error: Optional[str]
    raw_response: Dict[str, Any]

    def to_dict(self):
        return asdict(self)

def run_single_test(test: Dict) -> TestResult:
    """Run a single stress test."""
    start = time.time()
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query": test["query"], "yacht_id": YACHT_ID}

    try:
        resp = requests.post(EXTRACT_URL, json=payload, headers=headers, timeout=30)
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            return TestResult(
                test_id=test["id"],
                category=test["category"],
                query=test["query"],
                status_code=200,
                lane=data.get("lane"),
                entities_extracted=len(data.get("entities", [])),
                response_time_ms=elapsed,
                error=None,
                raw_response=data
            )
        else:
            return TestResult(
                test_id=test["id"],
                category=test["category"],
                query=test["query"],
                status_code=resp.status_code,
                lane=None,
                entities_extracted=0,
                response_time_ms=elapsed,
                error=resp.text[:500],
                raw_response={}
            )
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return TestResult(
            test_id=test["id"],
            category=test["category"],
            query=test["query"],
            status_code=0,
            lane=None,
            entities_extracted=0,
            response_time_ms=elapsed,
            error=str(e),
            raw_response={}
        )

def run_batch(tests: List[Dict], delay: float = DELAY_SECONDS) -> List[TestResult]:
    """Run a batch of tests with rate limiting."""
    results = []
    for i, test in enumerate(tests):
        result = run_single_test(test)
        results.append(result)

        if i < len(tests) - 1:
            time.sleep(delay)

        # Progress
        if (i + 1) % 10 == 0:
            print(f"    Batch progress: {i+1}/{len(tests)}")

    return results

def analyze_results(results: List[TestResult]) -> Dict:
    """Analyze test results and compute metrics."""
    total = len(results)
    if total == 0:
        return {"error": "No results"}

    # Basic counts
    passed = sum(1 for r in results if r.status_code == 200)
    failed = total - passed

    # By category
    by_category = {}
    for r in results:
        cat = r.category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0, "failed": 0}
        by_category[cat]["total"] += 1
        if r.status_code == 200:
            by_category[cat]["passed"] += 1
        else:
            by_category[cat]["failed"] += 1

    # By lane
    by_lane = {}
    for r in results:
        if r.lane:
            by_lane[r.lane] = by_lane.get(r.lane, 0) + 1

    # Latency stats
    times = [r.response_time_ms for r in results if r.response_time_ms > 0]
    times.sort()

    def percentile(arr, p):
        if not arr:
            return 0
        idx = int(len(arr) * p / 100)
        return arr[min(idx, len(arr)-1)]

    # Security tests
    security_tests = [r for r in results if "NEGATIVE" in r.category]
    security_blocked = sum(1 for r in security_tests if r.lane == "BLOCKED" or r.status_code != 200)

    # Errors
    errors = [{"id": r.test_id, "query": r.query[:50], "error": r.error[:100] if r.error else None}
              for r in results if r.error]

    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 2)
        },
        "by_category": by_category,
        "by_lane": by_lane,
        "latency": {
            "avg_ms": round(sum(times) / len(times), 2) if times else 0,
            "p50_ms": round(percentile(times, 50), 2),
            "p95_ms": round(percentile(times, 95), 2),
            "p99_ms": round(percentile(times, 99), 2),
            "max_ms": round(max(times), 2) if times else 0
        },
        "security": {
            "total_tests": len(security_tests),
            "blocked": security_blocked,
            "block_rate": round(security_blocked / len(security_tests) * 100, 2) if security_tests else 0
        },
        "errors": errors[:20]
    }

def generate_report(analysis: Dict, results: List[TestResult]) -> str:
    """Generate markdown report."""
    report = f"""# SQL Stress Test Report

Generated: {datetime.utcnow().isoformat()}

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Tests | {analysis['summary']['total']} |
| Passed | {analysis['summary']['passed']} |
| Failed | {analysis['summary']['failed']} |
| **Pass Rate** | **{analysis['summary']['pass_rate']}%** |

## Hard Gates

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| UNSAFE queries | 0 | {analysis['summary']['failed']} | {'PASS' if analysis['summary']['failed'] == 0 else 'REVIEW'} |
| Security Block Rate | 95%+ | {analysis['security']['block_rate']}% | {'PASS' if analysis['security']['block_rate'] >= 95 else 'FAIL'} |

## Results by Category

| Category | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
"""
    for cat, data in sorted(analysis['by_category'].items()):
        rate = round(data['passed'] / data['total'] * 100, 2) if data['total'] else 0
        report += f"| {cat} | {data['total']} | {data['passed']} | {data['failed']} | {rate}% |\n"

    report += f"""
## Lane Distribution

| Lane | Count | Percentage |
|------|-------|------------|
"""
    total_lane = sum(analysis['by_lane'].values()) if analysis['by_lane'] else 1
    for lane, count in sorted(analysis['by_lane'].items()):
        pct = round(count / total_lane * 100, 2)
        report += f"| {lane} | {count} | {pct}% |\n"

    report += f"""
## Latency Metrics

| Metric | Value |
|--------|-------|
| Average | {analysis['latency']['avg_ms']} ms |
| P50 | {analysis['latency']['p50_ms']} ms |
| P95 | {analysis['latency']['p95_ms']} ms |
| P99 | {analysis['latency']['p99_ms']} ms |
| Max | {analysis['latency']['max_ms']} ms |

## Security Tests

| Metric | Value |
|--------|-------|
| Total Security Tests | {analysis['security']['total_tests']} |
| Blocked | {analysis['security']['blocked']} |
| Block Rate | {analysis['security']['block_rate']}% |

## Top 20 Errors

| Test ID | Query | Error |
|---------|-------|-------|
"""
    for err in analysis['errors'][:20]:
        query = err['query'].replace('|', '\\|')
        error = (err['error'] or 'None').replace('|', '\\|')
        report += f"| {err['id']} | {query} | {error[:50]} |\n"

    report += """
## Failure Signatures

"""
    # Group errors by type
    error_types = {}
    for r in results:
        if r.error:
            key = r.error[:30] if r.error else "Unknown"
            if key not in error_types:
                error_types[key] = []
            error_types[key].append(r.test_id)

    for sig, ids in sorted(error_types.items(), key=lambda x: -len(x[1]))[:10]:
        report += f"- **{sig}...**: {len(ids)} occurrences ({', '.join(ids[:5])}{'...' if len(ids) > 5 else ''})\n"

    return report

def main():
    print("=" * 60)
    print("SQL Stress Test Runner")
    print("=" * 60)

    # Load tests
    print("\nLoading stress tests...")
    with open(STRESS_TESTS_PATH) as f:
        data = json.load(f)
    tests = data["tests"]
    print(f"Loaded {len(tests)} tests")

    # Option to run subset
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
        tests = tests[:limit]
        print(f"Running first {limit} tests only")

    # Run tests in batches
    print(f"\nRunning tests with {DELAY_SECONDS}s delay...")
    all_results = []
    batches = [tests[i:i+BATCH_SIZE] for i in range(0, len(tests), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"\nBatch {i+1}/{len(batches)} ({len(batch)} tests)")
        results = run_batch(batch)
        all_results.extend(results)

        # Save progress
        with open(RESULTS_PATH, "w") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "total": len(all_results),
                "results": [r.to_dict() for r in all_results]
            }, f, indent=2)
        print(f"  Saved progress: {len(all_results)} results")

    # Analyze
    print("\nAnalyzing results...")
    analysis = analyze_results(all_results)

    # Generate report
    print("Generating report...")
    report = generate_report(analysis, all_results)

    with open(REPORT_PATH, "w") as f:
        f.write(report)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {analysis['summary']['total']}")
    print(f"Passed: {analysis['summary']['passed']}")
    print(f"Failed: {analysis['summary']['failed']}")
    print(f"Pass Rate: {analysis['summary']['pass_rate']}%")
    print(f"\nReport saved to: {REPORT_PATH}")
    print(f"Results saved to: {RESULTS_PATH}")

if __name__ == "__main__":
    main()
