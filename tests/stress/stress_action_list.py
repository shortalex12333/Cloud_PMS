#!/usr/bin/env python3
"""
Stress test for /v1/actions/list endpoint.

Usage:
    TEST_JWT="$JWT" python tests/stress/stress_action_list.py

Environment Variables:
    API_BASE        - API base URL (default: http://localhost:8000)
    TEST_JWT        - JWT token for authentication (required)
    CONCURRENCY     - Number of concurrent workers (default: 10)
    REQUESTS        - Requests per worker (default: 100)

Example:
    # Light load test
    CONCURRENCY=5 REQUESTS=20 TEST_JWT="$JWT" python tests/stress/stress_action_list.py

    # Heavy load test
    CONCURRENCY=50 REQUESTS=200 TEST_JWT="$JWT" python tests/stress/stress_action_list.py
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
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
JWT = os.getenv("TEST_JWT")
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
REQUESTS_PER_WORKER = int(os.getenv("REQUESTS", "100"))
OUTPUT_JSON = os.getenv("OUTPUT_JSON", "")  # Optional: path to write JSON results

# Test queries to cycle through
QUERIES = [
    "add certificate",
    "create work order",
    "link document",
    "update certificate",
    "supersede",
    "close work order",
]

# Domains to test
DOMAINS = ["certificates", "work_orders", ""]


def make_request(query: str, domain: str) -> dict:
    """Make a single request and return timing/status info."""
    start = time.time()
    try:
        params = {"q": query}
        if domain:
            params["domain"] = domain

        resp = requests.get(
            f"{API_BASE}/v1/actions/list",
            params=params,
            headers={"Authorization": f"Bearer {JWT}"},
            timeout=10
        )
        latency = (time.time() - start) * 1000

        return {
            "status": resp.status_code,
            "latency_ms": latency,
            "success": resp.status_code == 200,
            "query": query,
            "domain": domain,
            "actions_count": len(resp.json().get("actions", [])) if resp.status_code == 200 else 0,
        }
    except requests.exceptions.Timeout:
        return {
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "query": query,
            "domain": domain,
            "error": "timeout",
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "query": query,
            "domain": domain,
            "error": f"connection_error: {str(e)[:100]}",
        }
    except Exception as e:
        return {
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "query": query,
            "domain": domain,
            "error": str(e)[:100],
        }


def run_stress_test() -> int:
    """Run the stress test and return exit code (0=pass, 1=fail)."""
    if not JWT:
        print("Error: TEST_JWT environment variable required")
        print("Get a JWT by logging in and copying from browser dev tools")
        return 1

    total_requests = CONCURRENCY * REQUESTS_PER_WORKER
    print("=" * 60)
    print("STRESS TEST: /v1/actions/list")
    print("=" * 60)
    print(f"Target: {API_BASE}/v1/actions/list")
    print(f"Workers: {CONCURRENCY}")
    print(f"Requests per worker: {REQUESTS_PER_WORKER}")
    print(f"Total requests: {total_requests}")
    print(f"Start time: {datetime.now().isoformat()}")
    print("=" * 60)

    # Verify API is reachable
    print("\nVerifying API health...")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5)
        if health.status_code != 200:
            print(f"Warning: Health check returned {health.status_code}")
        else:
            print("API healthy")
    except Exception as e:
        print(f"Warning: Could not reach API health endpoint: {e}")

    # Run stress test
    print(f"\nRunning {total_requests} requests with {CONCURRENCY} concurrent workers...")
    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = []
        for i in range(total_requests):
            query = QUERIES[i % len(QUERIES)]
            domain = DOMAINS[i % len(DOMAINS)]
            futures.append(executor.submit(make_request, query, domain))

        # Collect results with progress
        completed = 0
        for future in as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed % 100 == 0:
                print(f"  Progress: {completed}/{total_requests} ({completed/total_requests*100:.0f}%)")

    total_time = time.time() - start_time

    # Analyze results
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["latency_ms"] for r in successes]

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print("=" * 60)
    print(f"Total requests: {len(results)}")
    print(f"Successful: {len(successes)} ({len(successes)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failures)} ({len(failures)/len(results)*100:.1f}%)")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.1f} req/s")

    if latencies:
        sorted_latencies = sorted(latencies)
        p50_idx = int(len(sorted_latencies) * 0.50)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        print(f"\n{'=' * 60}")
        print("LATENCY (ms)")
        print("=" * 60)
        print(f"Min:    {min(latencies):.1f}")
        print(f"Max:    {max(latencies):.1f}")
        print(f"Mean:   {statistics.mean(latencies):.1f}")
        print(f"Median: {statistics.median(latencies):.1f}")
        print(f"P50:    {sorted_latencies[p50_idx]:.1f}")
        print(f"P95:    {sorted_latencies[p95_idx]:.1f}")
        print(f"P99:    {sorted_latencies[p99_idx]:.1f}")

    # Status code breakdown
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    print(f"\n{'=' * 60}")
    print("STATUS CODES")
    print("=" * 60)
    for status, count in sorted(status_counts.items()):
        pct = count / len(results) * 100
        bar = "#" * int(pct / 2)
        status_label = {0: "Timeout/Error", 200: "OK", 401: "Unauthorized", 403: "Forbidden", 500: "Server Error"}.get(status, str(status))
        print(f"  {status} ({status_label}): {count} ({pct:.1f}%) {bar}")

    # Error breakdown (if any)
    if failures:
        error_counts = {}
        for f in failures:
            err = f.get("error", f"status_{f['status']}")
            error_counts[err] = error_counts.get(err, 0) + 1

        print(f"\n{'=' * 60}")
        print("ERRORS")
        print("=" * 60)
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {err}: {count}")

    # Determine pass/fail
    success_rate = len(successes) / len(results) if results else 0
    p95_latency = sorted_latencies[p95_idx] if latencies else float('inf')

    print(f"\n{'=' * 60}")
    print("VERDICT")
    print("=" * 60)

    exit_code = 0
    if success_rate >= 0.99 and p95_latency < 500:
        print("PASS: >99% success rate, P95 < 500ms")
    elif success_rate >= 0.95 and p95_latency < 1000:
        print("WARN: Success rate 95-99% or P95 500-1000ms")
    else:
        print(f"FAIL: Success rate {success_rate*100:.1f}% (need >95%), P95 {p95_latency:.0f}ms (need <1000ms)")
        exit_code = 1

    # Write JSON output if requested
    if OUTPUT_JSON:
        output = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "api_base": API_BASE,
                "concurrency": CONCURRENCY,
                "requests_per_worker": REQUESTS_PER_WORKER,
                "total_requests": total_requests,
            },
            "results": {
                "total": len(results),
                "successful": len(successes),
                "failed": len(failures),
                "success_rate": success_rate,
                "total_time_s": total_time,
                "throughput_rps": len(results) / total_time,
            },
            "latency_ms": {
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
                "mean": statistics.mean(latencies) if latencies else None,
                "median": statistics.median(latencies) if latencies else None,
                "p95": sorted_latencies[p95_idx] if latencies else None,
                "p99": sorted_latencies[p99_idx] if latencies else None,
            },
            "status_codes": status_counts,
            "verdict": "PASS" if exit_code == 0 else "FAIL",
        }
        with open(OUTPUT_JSON, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nJSON results written to: {OUTPUT_JSON}")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_stress_test())
