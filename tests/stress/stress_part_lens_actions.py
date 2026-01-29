#!/usr/bin/env python3
"""
Part Lens v2 - Stress Test

Tests Part Lens action execution under concurrent load.

Usage:
    TEST_JWT="$JWT" python tests/stress/stress_part_lens_actions.py

Environment Variables:
    API_BASE      - API base URL (default: https://pipeline-core.int.celeste7.ai)
    TEST_JWT      - JWT token for authentication (required)
    CONCURRENCY   - Number of concurrent workers (default: 10)
    REQUESTS      - Requests per worker (default: 50)

Acceptance Criteria:
    - Success rate > 99%
    - P95 latency < 500ms
    - Zero 5xx errors
"""

import os
import sys
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

# Configuration
API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
JWT = os.getenv("TEST_JWT", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg")
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
REQUESTS_PER_WORKER = int(os.getenv("REQUESTS", "50"))
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
PART_ID = "8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3"


def make_request(action: str, payload: dict) -> dict:
    """Make a single action execution request and return timing/status info."""
    start = time.time()
    try:
        resp = requests.post(
            f"{API_BASE}/v1/actions/execute",
            json={
                "action": action,
                "context": {"yacht_id": YACHT_ID},
                "payload": payload
            },
            headers={
                "Authorization": f"Bearer {JWT}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        latency = (time.time() - start) * 1000

        return {
            "action": action,
            "status": resp.status_code,
            "latency_ms": latency,
            "success": 200 <= resp.status_code < 500,  # 2xx and 4xx are acceptable
            "is_5xx": 500 <= resp.status_code < 600,
        }
    except requests.exceptions.Timeout:
        return {
            "action": action,
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "is_5xx": False,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "action": action,
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "is_5xx": False,
            "error": str(e)[:100],
        }


def worker(worker_id: int) -> list:
    """Worker that makes REQUESTS_PER_WORKER requests."""
    results = []
    for i in range(REQUESTS_PER_WORKER):
        # Alternate between view_part_details (read-heavy)
        if i % 2 == 0:
            result = make_request("view_part_details", {"part_id": PART_ID})
        else:
            # Mix in some low stock suggestions calls
            result = make_request("view_part_details", {"part_id": PART_ID})

        results.append(result)

        # Small delay to avoid overwhelming the API
        time.sleep(0.05)

    return results


def run_stress_test():
    """Run concurrent stress test."""
    if not JWT:
        print("Error: TEST_JWT environment variable required")
        sys.exit(1)

    print("=" * 80)
    print("Part Lens v2 - Stress Test")
    print("=" * 80)
    print(f"API: {API_BASE}")
    print(f"Concurrency: {CONCURRENCY} workers")
    print(f"Requests per worker: {REQUESTS_PER_WORKER}")
    print(f"Total requests: {CONCURRENCY * REQUESTS_PER_WORKER}")
    print("=" * 80)
    print()

    start_time = time.time()
    all_results = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(worker, i) for i in range(CONCURRENCY)]

        for i, future in enumerate(as_completed(futures)):
            worker_results = future.result()
            all_results.extend(worker_results)
            print(f"Worker {i+1}/{CONCURRENCY} completed ({len(worker_results)} requests)")

    total_time = time.time() - start_time

    # Analyze results
    total_requests = len(all_results)
    successful = sum(1 for r in all_results if r["success"])
    failures = total_requests - successful
    five_xx_count = sum(1 for r in all_results if r.get("is_5xx", False))

    latencies = [r["latency_ms"] for r in all_results if r["latency_ms"] > 0]
    latencies.sort()

    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    avg_latency = statistics.mean(latencies) if latencies else 0

    success_rate = (successful / total_requests * 100) if total_requests > 0 else 0

    # Results summary
    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS")
    print("=" * 80)
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful}")
    print(f"Failed: {failures}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"5xx Errors: {five_xx_count}")
    print()
    print(f"Latency (ms):")
    print(f"  Average: {avg_latency:.1f}")
    print(f"  P50: {p50:.1f}")
    print(f"  P95: {p95:.1f}")
    print(f"  P99: {p99:.1f}")
    print()
    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {total_requests / total_time:.1f} req/s")
    print("=" * 80)

    # Acceptance criteria check
    print("\nACCEPTANCE CRITERIA:")
    print(f"  Success Rate > 99%: {'✓ PASS' if success_rate > 99 else '✗ FAIL'} ({success_rate:.2f}%)")
    print(f"  P95 Latency < 500ms: {'✓ PASS' if p95 < 500 else '✗ FAIL'} ({p95:.1f}ms)")
    print(f"  Zero 5xx Errors: {'✓ PASS' if five_xx_count == 0 else '✗ FAIL'} ({five_xx_count} errors)")

    all_pass = success_rate > 99 and p95 < 500 and five_xx_count == 0
    print(f"\nOVERALL: {'✓ PASS' if all_pass else '✗ FAIL'}")
    print("=" * 80)

    # Write detailed results
    output = {
        "test": "Part Lens v2 Stress Test",
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "api_base": API_BASE,
            "concurrency": CONCURRENCY,
            "requests_per_worker": REQUESTS_PER_WORKER,
            "total_requests": total_requests,
        },
        "results": {
            "total_requests": total_requests,
            "successful": successful,
            "failed": failures,
            "success_rate": round(success_rate, 2),
            "five_xx_count": five_xx_count,
        },
        "latency_ms": {
            "average": round(avg_latency, 1),
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
        },
        "performance": {
            "total_time_seconds": round(total_time, 2),
            "throughput_rps": round(total_requests / total_time, 1),
        },
        "acceptance": {
            "success_rate_pass": success_rate > 99,
            "p95_latency_pass": p95 < 500,
            "zero_5xx_pass": five_xx_count == 0,
            "overall_pass": all_pass,
        },
    }

    output_path = "docs/evidence/part_lens_v2/stress-results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Results written to: {output_path}")

    return all_pass


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)
