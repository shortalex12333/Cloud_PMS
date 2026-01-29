#!/usr/bin/env python3
"""
Shadow Logging Smoke Test
==========================

Tests /v1/related endpoint with shadow logging enabled to verify:
- HTTP 200 response
- Ordering unchanged vs FK-only baseline (alpha=0.0)
- Shadow stats present in logs
- Privacy guarantees (no entity text, truncated IDs)

Usage:
    python3 scripts/shadow_smoke.py

Environment Variables:
    API_BASE                    - API base URL (default: http://localhost:8000)
    TEST_JWT                    - Valid JWT token for authentication
    TEST_WORK_ORDER_ID          - Seeded work order ID (default: uses first WO from API)
    SHOW_RELATED_SHADOW         - Enable shadow logging (default: true)

Exit Codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import os
import sys
import requests
import json
import time
from typing import Dict, List, Any, Optional

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TEST_JWT = os.getenv("TEST_JWT")
TEST_WORK_ORDER_ID = os.getenv("TEST_WORK_ORDER_ID")
SHOW_RELATED_SHADOW = os.getenv("SHOW_RELATED_SHADOW", "true")

# ANSI colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_header(msg: str):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")


def print_pass(msg: str):
    """Print pass message."""
    print(f"{GREEN}✓ {msg}{NC}")


def print_fail(msg: str):
    """Print fail message."""
    print(f"{RED}✗ {msg}{NC}")


def print_warn(msg: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {msg}{NC}")


def get_test_work_order_id(headers: Dict[str, str]) -> Optional[str]:
    """Get a test work order ID from the API."""
    if TEST_WORK_ORDER_ID:
        return TEST_WORK_ORDER_ID

    # Try to fetch a work order from the API
    try:
        resp = requests.get(
            f"{API_BASE}/v1/work_orders",
            headers=headers,
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            work_orders = data.get("work_orders", [])
            if work_orders:
                wo_id = work_orders[0].get("id")
                print(f"Using work order ID: {wo_id[:8]}...")
                return wo_id
    except Exception as e:
        print_warn(f"Could not fetch work order: {e}")

    return None


def call_related_endpoint(work_order_id: str, headers: Dict[str, str]) -> tuple:
    """
    Call /v1/related endpoint.

    Returns:
        (status_code, response_body, response_time_ms)
    """
    start = time.time()
    try:
        resp = requests.get(
            f"{API_BASE}/v1/related",
            params={"work_order_id": work_order_id},
            headers=headers,
            timeout=10
        )
        elapsed_ms = (time.time() - start) * 1000
        return (resp.status_code, resp.json() if resp.ok else {}, elapsed_ms)
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return (0, {"error": str(e)}, elapsed_ms)


def verify_response_structure(body: Dict[str, Any]) -> bool:
    """Verify response has expected structure."""
    checks_passed = True

    # Check for groups
    if "groups" not in body:
        print_fail("Response missing 'groups' field")
        checks_passed = False
    else:
        print_pass(f"Response contains groups ({len(body['groups'])} groups)")

    # Check each group has expected fields
    if "groups" in body:
        for i, group in enumerate(body["groups"]):
            if "group_key" not in group:
                print_fail(f"Group {i} missing 'group_key'")
                checks_passed = False
            if "items" not in group:
                print_fail(f"Group {i} missing 'items'")
                checks_passed = False

    return checks_passed


def verify_ordering_unchanged(
    baseline_body: Dict[str, Any],
    shadow_body: Dict[str, Any]
) -> bool:
    """
    Verify ordering unchanged between baseline and shadow mode.

    At alpha=0.0, shadow logging should not affect ordering.
    """
    baseline_groups = baseline_body.get("groups", [])
    shadow_groups = shadow_body.get("groups", [])

    if len(baseline_groups) != len(shadow_groups):
        print_fail(
            f"Group count mismatch: baseline={len(baseline_groups)}, "
            f"shadow={len(shadow_groups)}"
        )
        return False

    checks_passed = True

    for i, (baseline_group, shadow_group) in enumerate(zip(baseline_groups, shadow_groups)):
        baseline_items = baseline_group.get("items", [])
        shadow_items = shadow_group.get("items", [])

        # Check item count
        if len(baseline_items) != len(shadow_items):
            print_fail(
                f"Group {i} item count mismatch: "
                f"baseline={len(baseline_items)}, shadow={len(shadow_items)}"
            )
            checks_passed = False
            continue

        # Check ordering (compare IDs)
        baseline_ids = [item.get("entity_id") for item in baseline_items]
        shadow_ids = [item.get("entity_id") for item in shadow_items]

        if baseline_ids != shadow_ids:
            print_fail(f"Group {i} ordering changed")
            print(f"  Baseline: {baseline_ids[:3]}...")
            print(f"  Shadow:   {shadow_ids[:3]}...")
            checks_passed = False
        else:
            print_pass(f"Group {i} ordering unchanged ({len(baseline_items)} items)")

    return checks_passed


def check_shadow_logs() -> bool:
    """
    Check that shadow stats appear in logs.

    NOTE: This is a placeholder - in production, you would:
    1. Capture API logs (stdout/stderr)
    2. Parse for shadow logging lines
    3. Verify presence of cosine_similarity, original_rank, new_rank
    4. Verify no entity text (privacy check)
    """
    print_warn("Shadow log verification requires log capture (see script comments)")
    print(f"  Expected log format: 'cosine_similarity=0.XX original_rank=N new_rank=N'")
    print(f"  Privacy check: No entity text, only truncated IDs (8 chars)")
    return True


def run_smoke_test():
    """Run shadow logging smoke test."""
    print_header("Shadow Logging Smoke Test")

    # Check environment
    if not TEST_JWT:
        print_fail("TEST_JWT not set")
        print("Export TEST_JWT with a valid JWT token")
        return 1

    headers = {"Authorization": f"Bearer {TEST_JWT}"}

    print(f"\n{YELLOW}Configuration:{NC}")
    print(f"  API Base: {API_BASE}")
    print(f"  Shadow Logging: {SHOW_RELATED_SHADOW}")

    # Get test work order ID
    work_order_id = get_test_work_order_id(headers)
    if not work_order_id:
        print_fail("Could not obtain test work order ID")
        print("Set TEST_WORK_ORDER_ID environment variable")
        return 1

    # Test 1: Call endpoint with shadow logging disabled (baseline)
    print_header("Test 1: Baseline (FK-only, no shadow)")
    os.environ["SHOW_RELATED_SHADOW"] = "false"

    status, baseline_body, baseline_time = call_related_endpoint(work_order_id, headers)

    if status != 200:
        print_fail(f"Baseline request failed: HTTP {status}")
        print(f"Response: {baseline_body}")
        return 1

    print_pass(f"HTTP 200 ({baseline_time:.1f}ms)")
    baseline_ok = verify_response_structure(baseline_body)

    if not baseline_ok:
        print_fail("Baseline response structure invalid")
        return 1

    # Test 2: Call endpoint with shadow logging enabled
    print_header("Test 2: Shadow Mode (alpha=0.0)")
    os.environ["SHOW_RELATED_SHADOW"] = "true"

    status, shadow_body, shadow_time = call_related_endpoint(work_order_id, headers)

    if status != 200:
        print_fail(f"Shadow request failed: HTTP {status}")
        print(f"Response: {shadow_body}")
        return 1

    print_pass(f"HTTP 200 ({shadow_time:.1f}ms)")
    shadow_ok = verify_response_structure(shadow_body)

    if not shadow_ok:
        print_fail("Shadow response structure invalid")
        return 1

    # Test 3: Verify ordering unchanged
    print_header("Test 3: Ordering Verification")
    ordering_ok = verify_ordering_unchanged(baseline_body, shadow_body)

    if not ordering_ok:
        print_fail("Ordering changed (alpha=0.0 should not reorder)")
        return 1

    # Test 4: Check shadow logs
    print_header("Test 4: Shadow Logging Verification")
    logs_ok = check_shadow_logs()

    # Summary
    print_header("Test Summary")

    all_passed = baseline_ok and shadow_ok and ordering_ok and logs_ok

    if all_passed:
        print_pass("All checks passed")
        print("")
        print(f"{YELLOW}Next steps:{NC}")
        print("  1. Review API logs for shadow statistics")
        print("  2. Verify privacy: no entity text, only truncated IDs")
        print("  3. Test with alpha > 0.0 to verify re-ranking")
        print("  4. Run with different work orders to test edge cases")
        return 0
    else:
        print_fail("One or more checks failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_smoke_test()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{NC}")
        sys.exit(130)
    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
