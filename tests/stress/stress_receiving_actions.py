"""
Receiving Lens v1 - Stress Test
================================

Stress tests receiving actions with concurrent requests.

Requirements:
- TEST_JWT (Chief Engineer or HOD role)
- API_BASE_URL (default: http://localhost:8000)
- OUTPUT_JSON (optional: path to save results)

Run:
    OUTPUT_JSON=receiving-stress.json TEST_JWT="$CHIEF_ENGINEER_JWT" python tests/stress/stress_receiving_actions.py
"""

import os
import sys
import time
import json
import httpx
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_JWT = os.environ.get("TEST_JWT")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TEST_YACHT_ID = os.environ.get("TEST_YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")
OUTPUT_JSON = os.environ.get("OUTPUT_JSON")

# Stress parameters
CONCURRENT_REQUESTS = 50
ACTIONS_PER_TYPE = 10

if not TEST_JWT:
    print("ERROR: TEST_JWT environment variable not set")
    sys.exit(1)

# ============================================================================
# TEST ACTIONS
# ============================================================================

def create_receiving(client, headers):
    """Create a receiving record."""
    start = time.time()
    try:
        response = client.post(
            "/v1/actions/execute",
            json={
                "action": "create_receiving",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {
                    "vendor_reference": f"STRESS-{uuid.uuid4().hex[:8]}",
                    "received_date": datetime.now().date().isoformat(),
                }
            },
            headers=headers,
            timeout=10.0
        )
        duration = time.time() - start
        return {
            "action": "create_receiving",
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "success": response.status_code == 200,
            "receiving_id": response.json().get("receiving_id") if response.status_code == 200 else None
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "action": "create_receiving",
            "status_code": 500,
            "duration_ms": duration * 1000,
            "success": False,
            "error": str(e)
        }


def add_receiving_item(client, headers, receiving_id):
    """Add a line item to receiving."""
    start = time.time()
    try:
        response = client.post(
            "/v1/actions/execute",
            json={
                "action": "add_receiving_item",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {
                    "receiving_id": receiving_id,
                    "description": f"Stress test item {uuid.uuid4().hex[:8]}",
                    "quantity_received": 1,
                }
            },
            headers=headers,
            timeout=10.0
        )
        duration = time.time() - start
        return {
            "action": "add_receiving_item",
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "success": response.status_code == 200,
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "action": "add_receiving_item",
            "status_code": 500,
            "duration_ms": duration * 1000,
            "success": False,
            "error": str(e)
        }


def view_receiving_history(client, headers, receiving_id):
    """View receiving history (READ)."""
    start = time.time()
    try:
        response = client.post(
            "/v1/actions/execute",
            json={
                "action": "view_receiving_history",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {"receiving_id": receiving_id}
            },
            headers=headers,
            timeout=10.0
        )
        duration = time.time() - start
        return {
            "action": "view_receiving_history",
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "success": response.status_code == 200,
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "action": "view_receiving_history",
            "status_code": 500,
            "duration_ms": duration * 1000,
            "success": False,
            "error": str(e)
        }


def update_receiving_fields(client, headers, receiving_id):
    """Update receiving fields."""
    start = time.time()
    try:
        response = client.post(
            "/v1/actions/execute",
            json={
                "action": "update_receiving_fields",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {
                    "receiving_id": receiving_id,
                    "vendor_name": f"Vendor-{uuid.uuid4().hex[:8]}",
                }
            },
            headers=headers,
            timeout=10.0
        )
        duration = time.time() - start
        return {
            "action": "update_receiving_fields",
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "success": response.status_code == 200,
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "action": "update_receiving_fields",
            "status_code": 500,
            "duration_ms": duration * 1000,
            "success": False,
            "error": str(e)
        }


# ============================================================================
# STRESS TEST RUNNER
# ============================================================================

def run_stress_test():
    """Run stress test and collect metrics."""
    print("="*80)
    print("Receiving Lens v1 - Stress Test")
    print("="*80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Yacht ID: {TEST_YACHT_ID}")
    print(f"Concurrent Requests: {CONCURRENT_REQUESTS}")
    print(f"Actions per type: {ACTIONS_PER_TYPE}")
    print("="*80)

    headers = {"Authorization": f"Bearer {TEST_JWT}"}
    results = []

    # Phase 1: Create receiving records
    print("\nPhase 1: Creating receiving records...")
    receiving_ids = []
    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            futures = [
                executor.submit(create_receiving, client, headers)
                for _ in range(ACTIONS_PER_TYPE)
            ]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if result["success"] and result.get("receiving_id"):
                    receiving_ids.append(result["receiving_id"])
                print(f"  Created: {result['status_code']} ({result['duration_ms']:.1f}ms)")

    print(f"Created {len(receiving_ids)} receiving records")

    if not receiving_ids:
        print("ERROR: No receiving records created. Cannot proceed with stress test.")
        return results

    # Phase 2: Mix of READ and MUTATE operations
    print("\nPhase 2: Mixed operations (READ + MUTATE)...")
    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            futures = []

            # Add items
            for _ in range(ACTIONS_PER_TYPE):
                receiving_id = receiving_ids[_ % len(receiving_ids)]
                futures.append(executor.submit(add_receiving_item, client, headers, receiving_id))

            # View history (READ)
            for _ in range(ACTIONS_PER_TYPE):
                receiving_id = receiving_ids[_ % len(receiving_ids)]
                futures.append(executor.submit(view_receiving_history, client, headers, receiving_id))

            # Update fields
            for _ in range(ACTIONS_PER_TYPE):
                receiving_id = receiving_ids[_ % len(receiving_ids)]
                futures.append(executor.submit(update_receiving_fields, client, headers, receiving_id))

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                status = "✓" if result["success"] else "✗"
                print(f"  {status} {result['action']}: {result['status_code']} ({result['duration_ms']:.1f}ms)")

    # Analyze results
    print("\n" + "="*80)
    print("Results Summary")
    print("="*80)

    status_codes = Counter(r["status_code"] for r in results)
    actions = Counter(r["action"] for r in results)
    durations = [r["duration_ms"] for r in results]
    durations.sort()

    success_count = sum(1 for r in results if r["success"])
    failure_count = len(results) - success_count

    print(f"\nTotal Requests: {len(results)}")
    print(f"Success: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"Failures: {failure_count} ({failure_count/len(results)*100:.1f}%)")

    print("\nStatus Code Distribution:")
    for code, count in sorted(status_codes.items()):
        print(f"  {code}: {count}")

    print("\nAction Distribution:")
    for action, count in sorted(actions.items()):
        print(f"  {action}: {count}")

    print("\nLatency Percentiles (ms):")
    print(f"  P50: {durations[int(len(durations)*0.5)]:.1f}")
    print(f"  P95: {durations[int(len(durations)*0.95)]:.1f}")
    print(f"  P99: {durations[int(len(durations)*0.99)]:.1f}")
    print(f"  Max: {max(durations):.1f}")

    # Check for 500s
    server_errors = [r for r in results if r["status_code"] >= 500]
    if server_errors:
        print(f"\n⚠️  WARNING: {len(server_errors)} server errors (500+) detected!")
        for err in server_errors[:5]:  # Show first 5
            print(f"  - {err['action']}: {err.get('error', 'Unknown error')}")
    else:
        print("\n✅ PASS: Zero 500s detected")

    # Save to JSON if requested
    if OUTPUT_JSON:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "api_base_url": API_BASE_URL,
                "yacht_id": TEST_YACHT_ID,
                "concurrent_requests": CONCURRENT_REQUESTS,
                "actions_per_type": ACTIONS_PER_TYPE,
            },
            "summary": {
                "total_requests": len(results),
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_count/len(results)*100,
                "status_codes": dict(status_codes),
                "actions": dict(actions),
                "latency_p50": durations[int(len(durations)*0.5)],
                "latency_p95": durations[int(len(durations)*0.95)],
                "latency_p99": durations[int(len(durations)*0.99)],
                "latency_max": max(durations),
                "server_errors": len(server_errors),
            },
            "results": results
        }
        with open(OUTPUT_JSON, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {OUTPUT_JSON}")

    print("="*80)

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    results = run_stress_test()

    # Exit with error if any 500s detected
    server_errors = sum(1 for r in results if r["status_code"] >= 500)
    if server_errors > 0:
        print(f"\n❌ FAIL: {server_errors} server errors detected")
        sys.exit(1)
    else:
        print("\n✅ PASS: Stress test completed successfully")
        sys.exit(0)
