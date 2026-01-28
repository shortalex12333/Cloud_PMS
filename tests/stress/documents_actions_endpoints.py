#!/usr/bin/env python3
"""
Document Lens v2 - Stress Testing

Purpose:
- Concurrent load testing of document action endpoints
- Verify 0×500 errors under load
- Measure P50/P95/P99 latencies
- Evidence-based reporting

Canon:
- 500 is ALWAYS failure (testing_success_ci:cd.md:249)
- Evidence artifacts required (testing_success_ci:cd.md:815)
- Verdict: PASS only if 0×500

Usage:
    export STAGING_API_URL="https://..."
    export STAGING_JWT_SECRET="..."
    python3 tests/stress/documents_actions_endpoints.py
"""

import os
import sys
import time
import json
import statistics
import concurrent.futures
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

# Configuration
API_BASE = os.getenv('STAGING_API_URL', os.getenv('API_BASE_URL', 'https://pipeline-core.int.celeste7.ai'))
JWT_SECRET = os.getenv('STAGING_JWT_SECRET', os.getenv('TENANT_SUPABASE_JWT_SECRET'))
TENANT_URL = os.getenv('TENANT_SUPABASE_URL', 'https://xyzcompany.supabase.co')

# Test configuration
LENS_ID = "documents"
DOMAIN = "documents"
YACHT_ID = os.getenv('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')
HOD_USER_ID = os.getenv('TEST_HOD_USER_ID', '05a488fd-e099-4d18-bf86-d87afba4fcdf')
HOD_EMAIL = os.getenv('TEST_HOD_EMAIL', 'hod.test@alex-short.com')

# Stress test parameters
CONCURRENCY = 10  # Number of concurrent requests
REQUESTS_PER_ENDPOINT = 20  # Total requests per endpoint
TIMEOUT_SECONDS = 30

# Results storage
results: List[Dict] = []


def generate_jwt(user_id: str, email: str, role: str = "chief_engineer") -> str:
    """Generate JWT for testing."""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET not set")

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


def make_request(jwt_token: str, endpoint: str, method: str = "GET", payload: Dict = None) -> Dict:
    """Make a single request and return result."""
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    start = time.time()
    try:
        if method.upper() == "GET":
            r = requests.get(f"{API_BASE}{endpoint}", headers=headers, timeout=TIMEOUT_SECONDS)
        else:
            r = requests.post(f"{API_BASE}{endpoint}", headers=headers, json=payload, timeout=TIMEOUT_SECONDS)

        latency_ms = int((time.time() - start) * 1000)

        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": r.status_code,
            "latency_ms": latency_ms,
            "success": 200 <= r.status_code < 300,
            "is_5xx": r.status_code >= 500,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": 0,
            "latency_ms": latency_ms,
            "success": False,
            "is_5xx": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def run_concurrent_requests(jwt_token: str, endpoint: str, method: str, payload: Dict, count: int) -> List[Dict]:
    """Run concurrent requests to an endpoint."""
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(make_request, jwt_token, endpoint, method, payload)
            for _ in range(count)
        ]

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    return results


def compute_percentiles(latencies: List[int]) -> Dict[str, int]:
    """Compute P50, P95, P99 latencies."""
    if not latencies:
        return {"p50": 0, "p95": 0, "p99": 0}

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    return {
        "p50": sorted_latencies[int(n * 0.50)],
        "p95": sorted_latencies[min(int(n * 0.95), n - 1)],
        "p99": sorted_latencies[min(int(n * 0.99), n - 1)]
    }


def run_stress_tests() -> Dict:
    """Run all stress tests."""
    print("=" * 80)
    print("DOCUMENT LENS V2 - STRESS TESTING")
    print("=" * 80)
    print(f"API Base: {API_BASE}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Requests per endpoint: {REQUESTS_PER_ENDPOINT}")
    print()

    # Generate JWT
    jwt_token = generate_jwt(HOD_USER_ID, HOD_EMAIL)

    all_results = []
    endpoint_summaries = []

    # Test endpoints
    # NOTE: get_document_url excluded - requires existing document_id
    #       Tested in staging acceptance with real documents instead
    endpoints = [
        {
            "name": "list_actions",
            "endpoint": f"/v1/actions/list?domain={DOMAIN}",
            "method": "GET",
            "payload": None
        },
        {
            "name": "execute_list_documents",
            "endpoint": "/v1/actions/execute",
            "method": "POST",
            "payload": {
                "action": "list_documents",
                "context": {"yacht_id": YACHT_ID},
                "payload": {"limit": 10}
            }
        }
    ]

    for ep in endpoints:
        print(f"\n--- Testing: {ep['name']} ---")
        print(f"Endpoint: {ep['method']} {ep['endpoint']}")

        results = run_concurrent_requests(
            jwt_token,
            ep["endpoint"],
            ep["method"],
            ep["payload"],
            REQUESTS_PER_ENDPOINT
        )
        all_results.extend(results)

        # Compute summary
        latencies = [r["latency_ms"] for r in results]
        percentiles = compute_percentiles(latencies)
        count_2xx = sum(1 for r in results if 200 <= r["status_code"] < 300)
        count_4xx = sum(1 for r in results if 400 <= r["status_code"] < 500)
        count_5xx = sum(1 for r in results if r["is_5xx"])
        count_error = sum(1 for r in results if r.get("error"))

        summary = {
            "name": ep["name"],
            "total_requests": len(results),
            "count_2xx": count_2xx,
            "count_4xx": count_4xx,
            "count_5xx": count_5xx,
            "count_error": count_error,
            "p50_ms": percentiles["p50"],
            "p95_ms": percentiles["p95"],
            "p99_ms": percentiles["p99"]
        }
        endpoint_summaries.append(summary)

        print(f"  Results: {count_2xx}×2xx, {count_4xx}×4xx, {count_5xx}×5xx, {count_error}×error")
        print(f"  Latency: P50={percentiles['p50']}ms, P95={percentiles['p95']}ms, P99={percentiles['p99']}ms")

    # Overall summary
    total_5xx = sum(s["count_5xx"] for s in endpoint_summaries)
    total_requests = sum(s["total_requests"] for s in endpoint_summaries)
    all_latencies = [r["latency_ms"] for r in all_results]
    overall_percentiles = compute_percentiles(all_latencies)

    # Verdict: PASS only if 0×500
    verdict = "PASS" if total_5xx == 0 else "FAIL"
    verdict_reason = f"{total_5xx}×500 errors" if total_5xx > 0 else "0×500 errors"

    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS")
    print("=" * 80)
    print(f"Total Requests: {total_requests}")
    print(f"5xx Errors: {total_5xx}")
    print(f"Overall P50: {overall_percentiles['p50']}ms")
    print(f"Overall P95: {overall_percentiles['p95']}ms")
    print(f"Overall P99: {overall_percentiles['p99']}ms")
    print(f"\nVERDICT: {verdict} ({verdict_reason})")
    print("=" * 80)

    return {
        "lens_id": LENS_ID,
        "domain": DOMAIN,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "api_base": API_BASE,
            "concurrency": CONCURRENCY,
            "requests_per_endpoint": REQUESTS_PER_ENDPOINT
        },
        "endpoint_summaries": endpoint_summaries,
        "overall": {
            "total_requests": total_requests,
            "total_5xx": total_5xx,
            "p50_ms": overall_percentiles["p50"],
            "p95_ms": overall_percentiles["p95"],
            "p99_ms": overall_percentiles["p99"]
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason
    }


def write_evidence(results: Dict):
    """Write evidence artifact."""
    # Create output directory
    output_dir = Path("verification_handoff/phase6")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write markdown report
    report_path = output_dir / "DOCUMENTS_STRESS_RESULTS.md"
    with open(report_path, "w") as f:
        f.write(f"# Document Lens v2 - Stress Test Results\n\n")
        f.write(f"**Date:** {results['timestamp']}\n")
        f.write(f"**Verdict:** {results['verdict']} ({results['verdict_reason']})\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- API Base: {results['config']['api_base']}\n")
        f.write(f"- Concurrency: {results['config']['concurrency']}\n")
        f.write(f"- Requests per endpoint: {results['config']['requests_per_endpoint']}\n\n")

        f.write("## Endpoint Results\n\n")
        f.write("| Endpoint | Total | 2xx | 4xx | 5xx | P50 | P95 | P99 |\n")
        f.write("|----------|-------|-----|-----|-----|-----|-----|-----|\n")
        for ep in results['endpoint_summaries']:
            f.write(f"| {ep['name']} | {ep['total_requests']} | {ep['count_2xx']} | {ep['count_4xx']} | {ep['count_5xx']} | {ep['p50_ms']}ms | {ep['p95_ms']}ms | {ep['p99_ms']}ms |\n")

        f.write(f"\n## Overall\n\n")
        f.write(f"- Total Requests: {results['overall']['total_requests']}\n")
        f.write(f"- 5xx Errors: {results['overall']['total_5xx']}\n")
        f.write(f"- P50: {results['overall']['p50_ms']}ms\n")
        f.write(f"- P95: {results['overall']['p95_ms']}ms\n")
        f.write(f"- P99: {results['overall']['p99_ms']}ms\n\n")

        f.write(f"## Verdict\n\n")
        f.write(f"**{results['verdict']}** - {results['verdict_reason']}\n")

    print(f"\n✅ Evidence written to: {report_path}")

    # Write JSON for machine consumption
    json_path = output_dir / "DOCUMENTS_STRESS_RESULTS.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ JSON written to: {json_path}")


def main():
    """Main entry point."""
    if not JWT_SECRET:
        print("ERROR: STAGING_JWT_SECRET or TENANT_SUPABASE_JWT_SECRET not set")
        sys.exit(1)

    results = run_stress_tests()
    write_evidence(results)

    # Exit with code based on verdict
    sys.exit(0 if results["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
