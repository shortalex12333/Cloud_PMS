#!/usr/bin/env python3
"""
shopping_list Stress Testing

Productionized replacement for ad-hoc stress_actions_endpoints.py

Purpose:
- Prove 0×500 under concurrent load (hard requirement)
- Capture P50/P95/P99 latencies
- Status code breakdown (200/4xx/5xx)
- Pass/fail verdict

Citations:
- 500 as hard fail: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249
  "500 indicates bug in contracts/stress"
- Verdict thresholds: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:708
  "Success rate, P95 latencies, 0×500 requirement"
- Evidence artifacts: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:815
  "Report P50/P95/P99, status breakdown, verdict"

Generated from: docs/pipeline/templates/lens_ops/stress_test_template.py
"""

import os
import sys
import time
import statistics
import requests
import jwt as pyjwt
import json
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

# Configuration
API_BASE = os.getenv('STAGING_API_URL', 'https://pipeline-core.int.celeste7.ai')
TENANT_URL = os.getenv('TENANT_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
JWT_SECRET = os.getenv('STAGING_JWT_SECRET')

# Lens configuration
LENS_ID = "shopping_list"  # e.g., "faults"
DOMAIN = "shopping_list"  # e.g., "faults"

# Test user (HOD with chief_engineer role)
TEST_USER_ID = "05a488fd-e099-4d18-bf86-d87afba4fcdf"
TEST_USER_EMAIL = "hod.test@alex-short.com"

# Stress test parameters
LIST_CONCURRENCY = 50  # Number of concurrent requests to /list
EXECUTE_CONCURRENCY = 30  # Number of concurrent requests to /execute (READ variant)


def generate_jwt(user_id: str, email: str) -> str:
    """Generate a fresh JWT token."""
    if not JWT_SECRET:
        raise ValueError("STAGING_JWT_SECRET not set")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=2)
    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": f"{TENANT_URL}/auth/v1",
        "sub": user_id,
        "email": email,
        "phone": "",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"stress-{int(now.timestamp())}"
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def make_request(jwt_token: str, endpoint: str, method: str = "GET", payload: Dict = None) -> Dict[str, Any]:
    """
    Make HTTP request and capture metrics.

    Returns: {status_code, latency_ms, success, error}
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    start = time.time()
    try:
        if method.upper() == "GET":
            r = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=30)
        else:
            r = requests.post(f"{API_BASE}{endpoint}", headers=headers, json=payload, timeout=30)

        latency_ms = int((time.time() - start) * 1000)

        return {
            "status_code": r.status_code,
            "latency_ms": latency_ms,
            "success": r.status_code < 400,
            "error": None
        }
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "status_code": 0,
            "latency_ms": latency_ms,
            "success": False,
            "error": str(e)
        }


def stress_test_list(jwt_token: str, concurrency: int) -> List[Dict[str, Any]]:
    """
    Stress test /v1/actions/list endpoint.

    Returns: list of result dicts
    """
    print(f"\nStress Testing: GET /v1/actions/list?domain=shopping_list")
    print(f"Concurrency: {concurrency} requests")
    print("-" * 80)

    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(make_request, jwt_token, f"/v1/actions/list?domain=shopping_list")
            for _ in range(concurrency)
        ]

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "status_code": 0,
                    "latency_ms": 0,
                    "success": False,
                    "error": str(e)
                })

    return results


def stress_test_execute(jwt_token: str, concurrency: int) -> List[Dict[str, Any]]:
    """
    Stress test /v1/actions/execute endpoint (READ variant).

    Uses a READ action (e.g., view_fault_detail) with fake ID to avoid
    polluting database while testing error handling.

    Returns: list of result dicts
    """
    print(f"\nStress Testing: POST /v1/actions/execute (READ variant)")
    print(f"Concurrency: {concurrency} requests")
    print("-" * 80)

    # READ action payload (fake entity ID for stress testing)
    # This will return 404 (expected), but we're testing for 0×500
    payload = {
        "action": "view_shopping_list_item_history",  # e.g., "view_fault_detail"
        "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
        "payload": {
            "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
            "item_id": "00000000-0000-0000-0000-000000000000"  # Fake ID
        }
    }

    results = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(make_request, jwt_token, "/v1/actions/execute", "POST", payload)
            for _ in range(concurrency)
        ]

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "status_code": 0,
                    "latency_ms": 0,
                    "success": False,
                    "error": str(e)
                })

    return results


def analyze_results(results: List[Dict], test_name: str) -> Dict[str, Any]:
    """
    Analyze stress test results.

    Returns: {
        total_requests,
        status_breakdown: {200, 4xx, 5xx},
        latencies: {p50, p95, p99, min, max},
        errors_500,
        success_rate,
        verdict
    }
    """
    total = len(results)

    # Status code breakdown
    status_codes = [r["status_code"] for r in results]
    status_2xx = sum(1 for s in status_codes if 200 <= s < 300)
    status_4xx = sum(1 for s in status_codes if 400 <= s < 500)
    status_5xx = sum(1 for s in status_codes if s >= 500)

    # Latencies
    latencies = sorted([r["latency_ms"] for r in results if r["latency_ms"] > 0])
    if latencies:
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
        p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0]
        latency_min = min(latencies)
        latency_max = max(latencies)
    else:
        p50 = p95 = p99 = latency_min = latency_max = 0

    # Success rate
    success_count = sum(1 for r in results if r["success"])
    success_rate = (success_count / total * 100) if total > 0 else 0.0

    # Verdict: PASS if 0×500 (hard requirement)
    # Citation: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249
    # "500 means failure"
    verdict = "PASS" if status_5xx == 0 else "FAIL"

    return {
        "test_name": test_name,
        "total_requests": total,
        "status_breakdown": {
            "200": status_2xx,
            "4xx": status_4xx,
            "5xx": status_5xx
        },
        "latencies": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "min": round(latency_min, 2),
            "max": round(latency_max, 2)
        },
        "errors_500": status_5xx,
        "success_rate": round(success_rate, 2),
        "verdict": verdict
    }


def print_analysis(analysis: Dict[str, Any]):
    """Print stress test analysis."""
    print(f"\nTest: {analysis['test_name']}")
    print("-" * 80)
    print(f"Total Requests: {analysis['total_requests']}")
    print(f"Status Breakdown:")
    print(f"  - 200 OK: {analysis['status_breakdown']['200']}")
    print(f"  - 4xx Client Error: {analysis['status_breakdown']['4xx']}")
    print(f"  - 5xx Server Error: {analysis['status_breakdown']['5xx']}")
    print(f"\nLatencies:")
    print(f"  - P50 (median): {analysis['latencies']['p50']} ms")
    print(f"  - P95: {analysis['latencies']['p95']} ms")
    print(f"  - P99: {analysis['latencies']['p99']} ms")
    print(f"  - Min: {analysis['latencies']['min']} ms")
    print(f"  - Max: {analysis['latencies']['max']} ms")
    print(f"\nSuccess Rate: {analysis['success_rate']}%")
    print(f"Errors (5xx): {analysis['errors_500']}")
    print(f"\nVerdict: {'✅ ' + analysis['verdict'] if analysis['verdict'] == 'PASS' else '❌ ' + analysis['verdict']}")

    if analysis['verdict'] == 'PASS':
        print("  (0×500 requirement met)")
    else:
        print(f"  ({analysis['errors_500']}×500 detected - hard requirement failed)")


def main():
    print("=" * 80)
    print(f"{LENS_ID.upper()} STRESS TESTING")
    print("=" * 80)
    print(f"\nEnvironment: {API_BASE}")
    print(f"Domain: shopping_list")
    print(f"Tests: /list ({LIST_CONCURRENCY} concurrent), /execute ({EXECUTE_CONCURRENCY} concurrent)")

    # Generate JWT
    jwt_token = generate_jwt(TEST_USER_ID, TEST_USER_EMAIL)

    # Test 1: /v1/actions/list
    results_list = stress_test_list(jwt_token, LIST_CONCURRENCY)
    analysis_list = analyze_results(results_list, "/v1/actions/list")
    print_analysis(analysis_list)

    # Test 2: /v1/actions/execute (READ variant)
    results_execute = stress_test_execute(jwt_token, EXECUTE_CONCURRENCY)
    analysis_execute = analyze_results(results_execute, "/v1/actions/execute")
    print_analysis(analysis_execute)

    # Overall verdict
    print("\n" + "=" * 80)
    print("OVERALL VERDICT")
    print("=" * 80)

    total_requests = analysis_list["total_requests"] + analysis_execute["total_requests"]
    total_5xx = analysis_list["errors_500"] + analysis_execute["errors_500"]

    print(f"\nTotal Requests: {total_requests}")
    print(f"Total 5xx Errors: {total_5xx}")

    if total_5xx == 0:
        print("\n✅ PASS: 0×500 across all requests (hard requirement met)")
        print("\nCitation: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249")
        print("  '500 means failure' - Zero 5xx errors confirms system stability")
        overall_verdict = "PASS"
        exit_code = 0
    else:
        print(f"\n❌ FAIL: {total_5xx}×500 errors detected (hard requirement failed)")
        print("\nCitation: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249")
        print("  '500 means failure' - Any 5xx error indicates bug in contracts/stress")
        overall_verdict = "FAIL"
        exit_code = 1

    # Save results to evidence file
    evidence_dir = "verification_handoff/phase6"
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_file = f"{evidence_dir}/{LENS_ID.upper()}_STRESS_RESULTS.md"

    with open(evidence_file, "w") as f:
        f.write(f"# {LENS_ID.upper()} Stress Test Results\n\n")
        f.write(f"**Test Date:** {datetime.now(timezone.utc).date()}\n")
        f.write(f"**Environment:** {API_BASE}\n")
        f.write(f"**Domain:** shopping_list\n")
        f.write(f"**Result:** {'✅ PASS' if overall_verdict == 'PASS' else '❌ FAIL'} ({total_5xx}×500)\n\n")
        f.write("---\n\n")

        f.write("## Test 1: /v1/actions/list\n\n")
        f.write(f"**Concurrency:** {LIST_CONCURRENCY} requests\n\n")
        f.write(f"**Status Breakdown:**\n")
        f.write(f"- 200 OK: {analysis_list['status_breakdown']['200']}\n")
        f.write(f"- 4xx: {analysis_list['status_breakdown']['4xx']}\n")
        f.write(f"- 5xx: {analysis_list['status_breakdown']['5xx']}\n\n")
        f.write(f"**Latencies:**\n")
        f.write(f"- P50: {analysis_list['latencies']['p50']} ms\n")
        f.write(f"- P95: {analysis_list['latencies']['p95']} ms\n")
        f.write(f"- P99: {analysis_list['latencies']['p99']} ms\n\n")
        f.write(f"**Verdict:** {'✅ PASS' if analysis_list['verdict'] == 'PASS' else '❌ FAIL'}\n\n")

        f.write("---\n\n")

        f.write("## Test 2: /v1/actions/execute\n\n")
        f.write(f"**Concurrency:** {EXECUTE_CONCURRENCY} requests\n\n")
        f.write(f"**Status Breakdown:**\n")
        f.write(f"- 200 OK: {analysis_execute['status_breakdown']['200']}\n")
        f.write(f"- 4xx: {analysis_execute['status_breakdown']['4xx']}\n")
        f.write(f"- 5xx: {analysis_execute['status_breakdown']['5xx']}\n\n")
        f.write(f"**Latencies:**\n")
        f.write(f"- P50: {analysis_execute['latencies']['p50']} ms\n")
        f.write(f"- P95: {analysis_execute['latencies']['p95']} ms\n")
        f.write(f"- P99: {analysis_execute['latencies']['p99']} ms\n\n")
        f.write(f"**Verdict:** {'✅ PASS' if analysis_execute['verdict'] == 'PASS' else '❌ FAIL'}\n\n")

        f.write("---\n\n")

        f.write("## Overall Verdict\n\n")
        f.write(f"**Total Requests:** {total_requests}\n")
        f.write(f"**Total 5xx Errors:** {total_5xx}\n")
        f.write(f"**Result:** {'✅ PASS' if overall_verdict == 'PASS' else '❌ FAIL'}\n\n")

        if overall_verdict == "PASS":
            f.write("**Evidence:** 0×500 across all requests (hard requirement met)\n\n")
            f.write("**Citation:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`\n")
            f.write("> '500 means failure' - Zero 5xx errors confirms system stability under concurrent load\n")
        else:
            f.write(f"**Evidence:** {total_5xx}×500 errors detected (hard requirement failed)\n\n")
            f.write("**Citation:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`\n")
            f.write("> '500 means failure' - Any 5xx error indicates bug in contracts/stress\n")

    print(f"\n✅ Results saved to: {evidence_file}")

    # Save JSON for machine parsing
    json_file = f"{evidence_dir}/{LENS_ID.upper()}_STRESS_RESULTS.json"
    with open(json_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": API_BASE,
            "lens_id": LENS_ID,
            "domain": DOMAIN,
            "tests": [analysis_list, analysis_execute],
            "overall_verdict": overall_verdict,
            "total_requests": total_requests,
            "total_5xx": total_5xx
        }, f, indent=2)

    print(f"✅ JSON results saved to: {json_file}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
