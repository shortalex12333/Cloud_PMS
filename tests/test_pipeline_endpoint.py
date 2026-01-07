#!/usr/bin/env python3
"""
Pipeline V1 Endpoint Test Script
================================

Tests the deployed pipeline_v1 service on Render with spaced-out requests
to ensure continuity and identify cold start issues.

Usage:
    python test_pipeline_endpoint.py [--url URL] [--yacht-id YACHT_ID] [--delay SECONDS]

Default URL: https://celeste-pipeline-v1.onrender.com
"""

import argparse
import httpx
import time
import json
from datetime import datetime

# Default configuration
DEFAULT_URL = "https://celeste-pipeline-v1.onrender.com"
DEFAULT_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
DEFAULT_DELAY = 5  # seconds between requests

# Test queries covering different entity types
TEST_QUERIES = [
    # Part number searches
    {"query": "ENG-0008", "expected_type": "PART_NUMBER"},
    {"query": "FLT-0033", "expected_type": "PART_NUMBER"},

    # Location searches
    {"query": "inventory in Locker", "expected_type": "LOCATION"},
    {"query": "parts at Agent", "expected_type": "LOCATION"},

    # Equipment/system searches
    {"query": "fuel filter", "expected_type": "SYSTEM_NAME"},
    {"query": "turbocharger", "expected_type": "PART_NAME"},

    # Mixed queries
    {"query": "oil pump seal", "expected_type": "EQUIPMENT"},
    {"query": "main engine parts", "expected_type": "EQUIPMENT_NAME"},
]


def test_health(client: httpx.Client, base_url: str) -> dict:
    """Test health endpoint."""
    start = time.time()
    try:
        resp = client.get(f"{base_url}/health", timeout=30.0)
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            return {
                "endpoint": "/health",
                "status": "OK",
                "response_ms": elapsed,
                "pipeline_ready": data.get("pipeline_ready", False),
            }
        else:
            return {
                "endpoint": "/health",
                "status": "FAIL",
                "response_ms": elapsed,
                "error": f"HTTP {resp.status_code}",
            }
    except Exception as e:
        return {
            "endpoint": "/health",
            "status": "ERROR",
            "response_ms": (time.time() - start) * 1000,
            "error": str(e),
        }


def test_search(client: httpx.Client, base_url: str, query: str, yacht_id: str) -> dict:
    """Test search endpoint."""
    start = time.time()
    try:
        resp = client.post(
            f"{base_url}/search",
            json={"query": query, "yacht_id": yacht_id, "limit": 10},
            timeout=60.0,
        )
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            return {
                "endpoint": "/search",
                "query": query,
                "status": "OK",
                "response_ms": elapsed,
                "success": data.get("success", False),
                "total_count": data.get("total_count", 0),
                "entities": len(data.get("entities", [])),
                "plans": len(data.get("plans", [])),
                "timing": data.get("timing_ms", {}),
            }
        else:
            return {
                "endpoint": "/search",
                "query": query,
                "status": "FAIL",
                "response_ms": elapsed,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except Exception as e:
        return {
            "endpoint": "/search",
            "query": query,
            "status": "ERROR",
            "response_ms": (time.time() - start) * 1000,
            "error": str(e),
        }


def test_extract(client: httpx.Client, base_url: str, query: str) -> dict:
    """Test extract endpoint."""
    start = time.time()
    try:
        resp = client.post(
            f"{base_url}/extract",
            json={"query": query},
            timeout=30.0,
        )
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            entities = data.get("entities", [])
            return {
                "endpoint": "/extract",
                "query": query,
                "status": "OK",
                "response_ms": elapsed,
                "entities": [(e["type"], e["value"]) for e in entities],
            }
        else:
            return {
                "endpoint": "/extract",
                "query": query,
                "status": "FAIL",
                "response_ms": elapsed,
                "error": f"HTTP {resp.status_code}",
            }
    except Exception as e:
        return {
            "endpoint": "/extract",
            "query": query,
            "status": "ERROR",
            "response_ms": (time.time() - start) * 1000,
            "error": str(e),
        }


def run_tests(base_url: str, yacht_id: str, delay: float):
    """Run all tests with delays between requests."""
    print("=" * 70)
    print(f"PIPELINE V1 ENDPOINT TESTS")
    print(f"URL: {base_url}")
    print(f"Yacht: {yacht_id}")
    print(f"Delay: {delay}s between requests")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    with httpx.Client() as client:
        # Test 1: Health check (cold start)
        print("\n[1] Health check (may trigger cold start)...")
        result = test_health(client, base_url)
        results.append(result)
        print(f"    Status: {result['status']} ({result['response_ms']:.0f}ms)")
        if result.get("error"):
            print(f"    Error: {result['error']}")

        time.sleep(delay)

        # Test 2: Capabilities endpoint
        print("\n[2] Checking capabilities...")
        try:
            resp = client.get(f"{base_url}/capabilities", timeout=30.0)
            if resp.status_code == 200:
                caps = resp.json()
                print(f"    Active capabilities: {caps.get('active_count', 0)}")
            else:
                print(f"    Failed: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(delay)

        # Test 3: Entity type mappings
        print("\n[3] Checking entity-type mappings...")
        try:
            resp = client.get(f"{base_url}/entity-types", timeout=30.0)
            if resp.status_code == 200:
                mappings = resp.json()
                print(f"    Mapped entity types: {mappings.get('count', 0)}")
            else:
                print(f"    Failed: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(delay)

        # Test 4: Search queries
        print(f"\n[4] Running {len(TEST_QUERIES)} search tests...")
        for i, test in enumerate(TEST_QUERIES, 1):
            query = test["query"]
            print(f"\n    [{i}/{len(TEST_QUERIES)}] \"{query}\"")

            result = test_search(client, base_url, query, yacht_id)
            results.append(result)

            if result["status"] == "OK":
                print(f"        Entities: {result['entities']}, Results: {result['total_count']}, Time: {result['response_ms']:.0f}ms")
            else:
                print(f"        {result['status']}: {result.get('error', 'Unknown error')}")

            time.sleep(delay)

        # Test 5: Extract-only tests
        print(f"\n[5] Running extraction-only tests...")
        for query in ["ENG-0008-103", "inventory in deck 1", "turbocharger gasket"]:
            result = test_extract(client, base_url, query)
            results.append(result)

            if result["status"] == "OK":
                print(f"    \"{query}\" → {result['entities']} ({result['response_ms']:.0f}ms)")
            else:
                print(f"    \"{query}\" → {result['status']}: {result.get('error')}")

            time.sleep(delay)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    ok_count = sum(1 for r in results if r["status"] == "OK")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    error_count = sum(1 for r in results if r["status"] == "ERROR")

    print(f"Total tests: {len(results)}")
    print(f"  OK: {ok_count}")
    print(f"  FAIL: {fail_count}")
    print(f"  ERROR: {error_count}")

    response_times = [r["response_ms"] for r in results if "response_ms" in r]
    if response_times:
        print(f"\nResponse times:")
        print(f"  Min: {min(response_times):.0f}ms")
        print(f"  Max: {max(response_times):.0f}ms")
        print(f"  Avg: {sum(response_times)/len(response_times):.0f}ms")

    # Save results
    output_file = f"pipeline_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Pipeline V1 endpoint")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Service URL (default: {DEFAULT_URL})")
    parser.add_argument("--yacht-id", default=DEFAULT_YACHT_ID, help="Yacht UUID")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"Delay between requests in seconds (default: {DEFAULT_DELAY})")

    args = parser.parse_args()

    run_tests(args.url, args.yacht_id, args.delay)
