#!/usr/bin/env python3
"""
Staging CI Tests for P1 Show Related (Work Order Lens)

Purpose:
- Verify Show Related API works correctly in staging environment
- Uses REAL JWTs from staging auth system
- Subset of Docker test matrix (key scenarios only)
- Attaches sample response to stdout for audit trail

Usage:
    python tests/ci/staging_work_orders_show_related.py

Requirements:
    - STAGING_API_URL or BASE_URL environment variable
    - STAGING_YACHT_ID or TEST_USER_YACHT_ID environment variable
    - STAGING_JWT_CREW or STAGING_CREW_JWT environment variable
    - STAGING_JWT_HOD or STAGING_HOD_JWT environment variable
    - TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_ROLE_KEY for dynamic entity fetch

Exit Codes:
    0: All tests passed
    1: One or more tests failed
    2: 500 errors detected (HARD FAIL)
"""

import os
import sys
import json
import time
import base64
from typing import Dict, Any, Tuple, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# =============================================================================
# Configuration (supports multiple env var naming conventions)
# =============================================================================

# API URL - check multiple names
STAGING_API_URL = (
    os.environ.get('STAGING_API_URL') or
    os.environ.get('BASE_URL') or
    os.environ.get('RENDER_API_URL') or
    'https://api-staging.backbuttoncloud.com'
)

# Yacht ID - check multiple names
STAGING_YACHT_ID = (
    os.environ.get('STAGING_YACHT_ID') or
    os.environ.get('TEST_USER_YACHT_ID')
)

# JWTs - check multiple names
STAGING_JWT_CREW = (
    os.environ.get('STAGING_JWT_CREW') or
    os.environ.get('STAGING_CREW_JWT')
)
STAGING_JWT_HOD = (
    os.environ.get('STAGING_JWT_HOD') or
    os.environ.get('STAGING_HOD_JWT')
)

# Test entity IDs (will be fetched dynamically if not provided)
STAGING_WORK_ORDER_ID = os.environ.get('STAGING_WORK_ORDER_ID')
STAGING_PART_ID = os.environ.get('STAGING_PART_ID')

# Tenant Supabase for dynamic entity lookup
TENANT_SUPABASE_URL = os.environ.get('TENANT_SUPABASE_URL')
TENANT_SUPABASE_SERVICE_KEY = (
    os.environ.get('TENANT_SUPABASE_SERVICE_ROLE_KEY') or
    os.environ.get('TENANT_SUPABASE_SERVICE_KEY')
)

# Track if we have valid entities for dependent tests
HAS_VALID_WORK_ORDER = False
HAS_VALID_PART = False

# =============================================================================
# Test Results Tracking
# =============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.has_500_errors = False
        self.sample_responses = []

    def record_pass(self, test_name: str):
        self.passed += 1
        print(f"✅ {test_name}")

    def record_fail(self, test_name: str, error: Any):
        self.failed += 1
        error_msg = str(error)
        self.errors.append(f"{test_name}: {error_msg}")
        print(f"❌ {test_name}: {error_msg}")

    def record_skip(self, test_name: str, reason: str):
        self.skipped += 1
        print(f"⏭️  {test_name}: SKIPPED ({reason})")

    def record_500(self, test_name: str):
        self.has_500_errors = True
        self.record_fail(test_name, "500 error detected (HARD FAIL)")

    def record_sample_response(self, test_name: str, response: Dict[str, Any]):
        """Attach sample response for audit trail"""
        self.sample_responses.append({
            "test_name": test_name,
            "timestamp": time.time(),
            "response": response
        })

    def print_summary(self):
        print("\n" + "="*80)
        print("STAGING CI TEST RESULTS")
        print("="*80)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Skipped: {self.skipped}")
        print(f"500 Errors: {'YES (HARD FAIL)' if self.has_500_errors else 'NO'}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        # Print sample responses for audit
        if self.sample_responses:
            print("\n" + "="*80)
            print("SAMPLE RESPONSES (Audit Trail)")
            print("="*80)
            for sample in self.sample_responses:
                print(f"\nTest: {sample['test_name']}")
                print(f"Timestamp: {sample['timestamp']}")
                print(f"Response:\n{json.dumps(sample['response'], indent=2)}")

        print("\n" + "="*80)

        if self.has_500_errors:
            return 2  # Exit code 2 for 500 errors
        elif self.failed > 0:
            return 1  # Exit code 1 for test failures
        else:
            return 0  # Exit code 0 for success

results = TestResults()

# =============================================================================
# JWT Decode Helper (for yacht validation)
# =============================================================================

def decode_jwt_payload(jwt: str) -> Optional[Dict[str, Any]]:
    """Decode JWT payload (without verification) to inspect claims."""
    try:
        parts = jwt.split('.')
        if len(parts) != 3:
            return None

        # Decode payload (middle part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"WARNING: Could not decode JWT: {e}")
        return None


def validate_jwt_yacht_alignment():
    """Check if JWT yacht claims align with STAGING_YACHT_ID."""
    print("\n--- JWT Yacht Alignment Check ---")

    for jwt_name, jwt_value in [("CREW", STAGING_JWT_CREW), ("HOD", STAGING_JWT_HOD)]:
        if not jwt_value:
            print(f"  {jwt_name}: NOT SET")
            continue

        payload = decode_jwt_payload(jwt_value)
        if not payload:
            print(f"  {jwt_name}: Could not decode")
            continue

        # Check common yacht claim locations
        jwt_yacht = (
            payload.get('yacht_id') or
            payload.get('user_metadata', {}).get('yacht_id') or
            payload.get('app_metadata', {}).get('yacht_id')
        )

        if jwt_yacht:
            match = "✅ MATCH" if jwt_yacht == STAGING_YACHT_ID else "⚠️  MISMATCH"
            print(f"  {jwt_name}: yacht_id={jwt_yacht} {match}")
        else:
            print(f"  {jwt_name}: No yacht_id claim (will use tenant lookup)")

    print("--- End JWT Check ---\n")


# =============================================================================
# HTTP Helpers
# =============================================================================

def api_get(endpoint: str, jwt: str, params: Dict[str, Any] = None) -> Tuple[int, Dict[str, Any]]:
    """Make GET request to staging API"""
    url = f"{STAGING_API_URL}{endpoint}"

    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"

    req = Request(url)
    req.add_header('Authorization', f'Bearer {jwt}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urlopen(req) as response:
            body = json.loads(response.read().decode('utf-8'))
            return response.status, body
    except HTTPError as e:
        try:
            body = json.loads(e.read().decode('utf-8'))
        except:
            body = {"error": e.reason}
        return e.code, body
    except URLError as e:
        return 0, {"error": str(e)}

def api_post(endpoint: str, jwt: str, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """Make POST request to staging API"""
    url = f"{STAGING_API_URL}{endpoint}"

    req = Request(url, data=json.dumps(data).encode('utf-8'), method='POST')
    req.add_header('Authorization', f'Bearer {jwt}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urlopen(req) as response:
            body = json.loads(response.read().decode('utf-8'))
            return response.status, body
    except HTTPError as e:
        try:
            body = json.loads(e.read().decode('utf-8'))
        except:
            body = {"error": e.reason}
        return e.code, body
    except URLError as e:
        return 0, {"error": str(e)}

# =============================================================================
# Dynamic Entity Fetch (Preflight)
# =============================================================================

def fetch_test_entities() -> bool:
    """
    Fetch valid work order and part IDs from tenant database.

    CRITICAL: Fetches WO for STAGING_YACHT_ID with deleted_at IS NULL.
    This ensures the handler's entity lookup will find it.
    """
    global STAGING_WORK_ORDER_ID, STAGING_PART_ID, STAGING_YACHT_ID
    global HAS_VALID_WORK_ORDER, HAS_VALID_PART

    # If already provided and we trust them, use them
    if STAGING_WORK_ORDER_ID and STAGING_PART_ID:
        print(f"Using provided entity IDs:")
        print(f"  WO: {STAGING_WORK_ORDER_ID}")
        print(f"  Part: {STAGING_PART_ID}")
        HAS_VALID_WORK_ORDER = True
        HAS_VALID_PART = True
        return True

    if not TENANT_SUPABASE_URL or not TENANT_SUPABASE_SERVICE_KEY:
        print("WARNING: Cannot fetch entities - TENANT_SUPABASE_URL/KEY not set")
        print("Set STAGING_WORK_ORDER_ID and STAGING_PART_ID manually")
        return False

    if not STAGING_YACHT_ID:
        print("WARNING: Cannot fetch entities - STAGING_YACHT_ID not set")
        return False

    try:
        headers = {
            "apikey": TENANT_SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {TENANT_SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }

        # Fetch a work order for THIS yacht with deleted_at IS NULL
        wo_url = (
            f"{TENANT_SUPABASE_URL}/rest/v1/pms_work_orders"
            f"?select=id,yacht_id,deleted_at,status,title"
            f"&yacht_id=eq.{STAGING_YACHT_ID}"
            f"&deleted_at=is.null"
            f"&limit=1"
        )

        print(f"Fetching work order for yacht {STAGING_YACHT_ID}...")
        req = Request(wo_url)
        for k, v in headers.items():
            req.add_header(k, v)

        with urlopen(req) as response:
            work_orders = json.loads(response.read().decode('utf-8'))
            if work_orders:
                wo = work_orders[0]
                STAGING_WORK_ORDER_ID = wo['id']
                HAS_VALID_WORK_ORDER = True
                print(f"  Found WO: {STAGING_WORK_ORDER_ID}")
                print(f"    yacht_id: {wo.get('yacht_id')}")
                print(f"    deleted_at: {wo.get('deleted_at')}")
                print(f"    status: {wo.get('status')}")
                print(f"    title: {wo.get('title', '')[:50]}")
            else:
                print(f"  WARNING: No work orders found for yacht {STAGING_YACHT_ID}")
                print("  GET /v1/related tests will be skipped")

        # Fetch a part for THIS yacht with deleted_at IS NULL
        part_url = (
            f"{TENANT_SUPABASE_URL}/rest/v1/pms_parts"
            f"?select=id,yacht_id,deleted_at,name"
            f"&yacht_id=eq.{STAGING_YACHT_ID}"
            f"&deleted_at=is.null"
            f"&limit=1"
        )

        print(f"Fetching part for yacht {STAGING_YACHT_ID}...")
        req = Request(part_url)
        for k, v in headers.items():
            req.add_header(k, v)

        with urlopen(req) as response:
            parts = json.loads(response.read().decode('utf-8'))
            if parts:
                part = parts[0]
                STAGING_PART_ID = part['id']
                HAS_VALID_PART = True
                print(f"  Found Part: {STAGING_PART_ID}")
                print(f"    name: {part.get('name', '')[:50]}")
            else:
                print(f"  WARNING: No parts found for yacht {STAGING_YACHT_ID}")
                print("  Add link tests will be skipped")

        return HAS_VALID_WORK_ORDER

    except Exception as e:
        print(f"ERROR: Failed to fetch entities: {e}")
        return False


# =============================================================================
# Test Data Generators
# =============================================================================

def get_test_link_data() -> Dict[str, Any]:
    """Generate test data for add_entity_link"""
    data = {
        "source_entity_type": "work_order",
        "source_entity_id": STAGING_WORK_ORDER_ID,
        "target_entity_type": "part",
        "target_entity_id": STAGING_PART_ID,
        "link_type": "related",
        "note": "Test link from staging CI"
    }
    if STAGING_YACHT_ID:
        data["yacht_id"] = STAGING_YACHT_ID
    return data


def get_error_msg(body: Dict[str, Any]) -> str:
    """Extract error message from response (FastAPI uses 'detail', not 'error')."""
    return body.get('detail') or body.get('error') or str(body)

# =============================================================================
# Staging CI Tests (Subset of Docker Matrix)
# =============================================================================

def test_crew_view_related_200():
    """TEST 1: CREW can view related entities (200 OK)"""
    if not HAS_VALID_WORK_ORDER:
        results.record_skip("test_crew_view_related_200", "No valid work order for yacht")
        return

    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 5
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}. Response: {get_error_msg(body)}"
        assert 'groups' in body, "Missing 'groups' in response"

        # Verify structure
        groups = body['groups']
        assert isinstance(groups, list), "groups should be a list"

        # Attach sample response for audit
        results.record_sample_response("test_crew_view_related_200", body)
        results.record_pass("test_crew_view_related_200")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_crew_view_related_200")
        else:
            results.record_fail("test_crew_view_related_200", e)

def test_crew_cannot_add_link_403():
    """TEST 2: CREW cannot add entity links (403 Forbidden)"""
    if not HAS_VALID_WORK_ORDER or not HAS_VALID_PART:
        results.record_skip("test_crew_cannot_add_link_403", "Missing WO or Part for yacht")
        return

    link_data = get_test_link_data()
    link_data['note'] = "CREW attempt (should fail)"

    code, body = api_post("/v1/related/add", STAGING_JWT_CREW, link_data)

    try:
        assert code == 403, f"Expected 403, got {code}. Response: {get_error_msg(body)}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert "not authorized" in err_msg.lower() or "hod" in err_msg.lower(), \
            f"Expected role-related error, got: {err_msg}"
        results.record_pass("test_crew_cannot_add_link_403")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_crew_cannot_add_link_403")
        else:
            results.record_fail("test_crew_cannot_add_link_403", e)

def test_hod_can_add_link_200():
    """TEST 3: HOD can add entity links (200 OK or 409 if exists)"""
    if not HAS_VALID_WORK_ORDER or not HAS_VALID_PART:
        results.record_skip("test_hod_can_add_link_200", "Missing WO or Part for yacht")
        return

    link_data = get_test_link_data()
    link_data['note'] = f"HOD link from staging CI at {time.time()}"

    code, body = api_post("/v1/related/add", STAGING_JWT_HOD, link_data)

    try:
        # Accept both 200 (created) and 409 (already exists)
        assert code in [200, 409], f"Expected 200 or 409, got {code}. Response: {get_error_msg(body)}"

        if code == 200:
            assert 'link_id' in body, "Missing 'link_id' in response"
            # Attach sample response for audit
            results.record_sample_response("test_hod_can_add_link_200", body)

        results.record_pass("test_hod_can_add_link_200")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_hod_can_add_link_200")
        else:
            results.record_fail("test_hod_can_add_link_200", e)

def test_invalid_entity_type_400():
    """TEST 4: Invalid entity_type returns 400"""
    # This test doesn't require a valid entity - it tests validation
    params = {
        "entity_type": "invalid_entity",
        "entity_id": STAGING_WORK_ORDER_ID or "00000000-0000-0000-0000-000000000000",
        "limit": 5
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        results.record_pass("test_invalid_entity_type_400")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_invalid_entity_type_400")
        else:
            results.record_fail("test_invalid_entity_type_400", e)

def test_caps_enforced():
    """TEST 5: Caps enforced (limit parameter respected per group)"""
    if not HAS_VALID_WORK_ORDER:
        results.record_skip("test_caps_enforced", "No valid work order for yacht")
        return

    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 3  # Request only 3 results per group
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}. Response: {get_error_msg(body)}"

        # Verify each group respects the limit
        for group in body.get('groups', []):
            group_key = group.get('group_key', group.get('type', 'unknown'))
            item_count = len(group.get('items', []))
            assert item_count <= 3, f"Group {group_key} has {item_count} items, expected <= 3"

        results.record_pass("test_caps_enforced")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_caps_enforced")
        else:
            results.record_fail("test_caps_enforced", e)

def test_limit_exceeds_max_4xx():
    """TEST 6: limit > 50 returns 400 or 422 (FastAPI validation)"""
    # This test doesn't require a valid entity - it tests validation
    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID or "00000000-0000-0000-0000-000000000000",
        "limit": 100  # Exceeds max of 50
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        # Accept both 400 (handler) and 422 (FastAPI Pydantic validation)
        assert code in [400, 422], f"Expected 400 or 422, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        results.record_pass("test_limit_exceeds_max_4xx")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_limit_exceeds_max_4xx")
        else:
            results.record_fail("test_limit_exceeds_max_4xx", e)

def test_match_reasons_present():
    """TEST 7: match_reasons present in response items"""
    if not HAS_VALID_WORK_ORDER:
        results.record_skip("test_match_reasons_present", "No valid work order for yacht")
        return

    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 10
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}. Response: {get_error_msg(body)}"

        # Check that items have match_reasons (if any items exist)
        has_items = False
        for group in body.get('groups', []):
            for item in group.get('items', []):
                has_items = True
                assert 'match_reasons' in item, f"Missing match_reasons in item {item.get('entity_id')}"
                assert isinstance(item['match_reasons'], list), "match_reasons should be a list"
                assert len(item['match_reasons']) > 0, "match_reasons should not be empty"

        # Pass even if no items (empty groups are valid)
        results.record_pass("test_match_reasons_present")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_match_reasons_present")
        else:
            results.record_fail("test_match_reasons_present", e)

# =============================================================================
# Main Test Runner
# =============================================================================

def validate_environment():
    """Validate required environment variables and fetch entities if needed."""
    global HAS_VALID_WORK_ORDER, HAS_VALID_PART

    print("\n--- Environment Validation ---")

    # Check for JWTs (required)
    if not STAGING_JWT_CREW:
        print("❌ Missing STAGING_JWT_CREW or STAGING_CREW_JWT")
        sys.exit(1)
    if not STAGING_JWT_HOD:
        print("❌ Missing STAGING_JWT_HOD or STAGING_HOD_JWT")
        sys.exit(1)

    print(f"✅ STAGING_JWT_CREW: set")
    print(f"✅ STAGING_JWT_HOD: set")

    # Check yacht ID
    if not STAGING_YACHT_ID:
        print("⚠️  STAGING_YACHT_ID not set - will try to infer from entities")

    # Validate JWT yacht alignment
    validate_jwt_yacht_alignment()

    # Fetch test entities if not provided
    if not STAGING_WORK_ORDER_ID or not STAGING_PART_ID:
        print("\nFetching test entities from tenant DB...")
        fetch_test_entities()
    else:
        HAS_VALID_WORK_ORDER = True
        HAS_VALID_PART = True

    print("\n✅ Environment validated")
    print("--- End Validation ---\n")


def main():
    """Run staging CI test suite"""
    print("="*80)
    print("P1 Show Related - Staging CI Tests")
    print("="*80)

    # Validate environment first (may fetch entities)
    validate_environment()

    # Print configuration after validation
    print(f"Staging API: {STAGING_API_URL}")
    print(f"Yacht ID: {STAGING_YACHT_ID or 'N/A'}")
    print(f"Work Order ID: {STAGING_WORK_ORDER_ID or 'N/A'}")
    print(f"Part ID: {STAGING_PART_ID or 'N/A'}")
    print(f"Has Valid WO: {HAS_VALID_WORK_ORDER}")
    print(f"Has Valid Part: {HAS_VALID_PART}")
    print("="*80)
    print()

    # Run test suite (subset of Docker matrix)
    test_crew_view_related_200()
    test_crew_cannot_add_link_403()
    test_hod_can_add_link_200()
    test_invalid_entity_type_400()
    test_caps_enforced()
    test_limit_exceeds_max_4xx()
    test_match_reasons_present()

    # Print summary and exit
    exit_code = results.print_summary()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
