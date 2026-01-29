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
    - STAGING_API_URL environment variable (e.g., https://api-staging.backbuttoncloud.com)
    - STAGING_YACHT_ID environment variable
    - STAGING_JWT_CREW environment variable (real crew JWT)
    - STAGING_JWT_HOD environment variable (real HOD JWT)
    - Staging database with test data

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
# Configuration
# =============================================================================

STAGING_API_URL = os.environ.get('STAGING_API_URL', 'https://api-staging.backbuttoncloud.com')
STAGING_YACHT_ID = os.environ.get('STAGING_YACHT_ID')
STAGING_JWT_CREW = os.environ.get('STAGING_JWT_CREW')
STAGING_JWT_HOD = os.environ.get('STAGING_JWT_HOD')

# Test entity IDs (should exist in staging database)
STAGING_WORK_ORDER_ID = os.environ.get('STAGING_WORK_ORDER_ID')
STAGING_PART_ID = os.environ.get('STAGING_PART_ID')

# Validation
REQUIRED_ENV_VARS = [
    'STAGING_API_URL',
    'STAGING_YACHT_ID',
    'STAGING_JWT_CREW',
    'STAGING_JWT_HOD',
    'STAGING_WORK_ORDER_ID',
    'STAGING_PART_ID'
]

# =============================================================================
# Test Results Tracking
# =============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
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
# Preflight Checks
# =============================================================================

def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT payload (no signature verification - just inspect claims).

    Returns:
        JWT payload dict or None if decode fails
    """
    try:
        # JWT structure: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode payload (base64url)
        payload_b64 = parts[1]
        # Add padding if needed (base64url doesn't include padding)
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)

        return payload

    except Exception as e:
        print(f"⚠️  JWT decode failed: {e}")
        return None


def validate_jwt_payload(payload: Dict[str, Any], jwt_name: str) -> bool:
    """
    Validate JWT payload structure and claims.

    Checks:
    - exp (expiration) is in future
    - sub (user_id) is present
    - email is present

    Returns:
        True if valid, False otherwise
    """
    if not payload:
        print(f"❌ {jwt_name}: Invalid payload (empty or malformed)")
        return False

    # Check expiration
    exp = payload.get('exp')
    if not exp:
        print(f"❌ {jwt_name}: Missing 'exp' claim")
        return False

    now = time.time()
    if exp < now:
        expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
        print(f"❌ {jwt_name}: Token EXPIRED (exp: {expiry_date})")
        return False

    # Check user_id (sub)
    user_id = payload.get('sub')
    if not user_id:
        print(f"❌ {jwt_name}: Missing 'sub' (user_id) claim")
        return False

    # Check email
    email = payload.get('email')
    if not email:
        print(f"❌ {jwt_name}: Missing 'email' claim")
        return False

    # Print summary
    expiry_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
    ttl_hours = (exp - now) / 3600
    print(f"✅ {jwt_name}: Valid (user_id={user_id[:8]}..., email={email}, expires={expiry_date}, TTL={ttl_hours:.1f}h)")

    return True


def preflight_check_jwt_tokens():
    """
    Preflight: Decode and validate JWT tokens.

    Exit with code 1 if any JWT is invalid or expired.
    """
    print("\n" + "="*80)
    print("PREFLIGHT: JWT Token Validation")
    print("="*80)

    all_valid = True

    # Decode and validate CREW JWT
    crew_payload = decode_jwt(STAGING_JWT_CREW)
    if not validate_jwt_payload(crew_payload, "STAGING_JWT_CREW"):
        all_valid = False

    # Decode and validate HOD JWT
    hod_payload = decode_jwt(STAGING_JWT_HOD)
    if not validate_jwt_payload(hod_payload, "STAGING_JWT_HOD"):
        all_valid = False

    if not all_valid:
        print("\n❌ PREFLIGHT FAILED: One or more JWTs are invalid or expired")
        print("   Regenerate JWTs using:")
        print("   python tools/auth/generate_staging_jwts.py")
        sys.exit(1)

    print("✅ All JWTs valid\n")


def preflight_check_work_order():
    """
    Preflight: Fetch test work order to verify it exists.

    Exit with code 1 if work order not found.
    """
    print("="*80)
    print("PREFLIGHT: Work Order Fetch")
    print("="*80)

    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 1
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    if code == 404:
        print(f"❌ Work order not found: {STAGING_WORK_ORDER_ID}")
        print("   Check STAGING_WORK_ORDER_ID or seed staging database")
        sys.exit(1)
    elif code == 500:
        print(f"❌ 500 error fetching work order (API may be down)")
        print(f"   Response: {body}")
        sys.exit(1)
    elif code != 200:
        print(f"⚠️  Unexpected status code: {code}")
        print(f"   Response: {body}")
        print("   Proceeding with tests...")
    else:
        # Extract WO details from response
        wo_number = "unknown"
        wo_title = "unknown"

        # Try to find work order details in groups (V1 response structure)
        for group in body.get('groups', []):
            for item in group.get('items', []):
                if item.get('entity_id') == STAGING_WORK_ORDER_ID:
                    wo_title = item.get('title', 'unknown')
                    break

        print(f"✅ Work order found: {STAGING_WORK_ORDER_ID}")
        print(f"   Title: {wo_title[:60]}")
        print(f"   Groups returned: {len(body.get('groups', []))}")

    print()


# =============================================================================
# Test Data Generators
# =============================================================================

def get_test_link_data() -> Dict[str, Any]:
    """Generate test data for add_entity_link"""
    return {
        "source_entity_type": "work_order",
        "source_entity_id": STAGING_WORK_ORDER_ID,
        "target_entity_type": "part",
        "target_entity_id": STAGING_PART_ID,
        "link_type": "related",
        "note": "Test link from staging CI"
    }


def get_error_msg(body: Dict[str, Any]) -> str:
    """Extract error message from response (FastAPI uses 'detail', not 'error')."""
    return body.get('detail') or body.get('error') or str(body)

# =============================================================================
# Staging CI Tests (Subset of Docker Matrix)
# =============================================================================

def test_crew_view_related_200():
    """TEST 1: CREW can view related entities (200 OK)"""
    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 5
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}"
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
    link_data = get_test_link_data()
    link_data['note'] = "CREW attempt (should fail)"

    code, body = api_post("/v1/related/add", STAGING_JWT_CREW, link_data)

    try:
        assert code == 403, f"Expected 403, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        results.record_pass("test_crew_cannot_add_link_403")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_crew_cannot_add_link_403")
        else:
            results.record_fail("test_crew_cannot_add_link_403", e)

def test_hod_can_add_link_200():
    """TEST 3: HOD can add entity links (200 OK or 409 if exists)"""
    link_data = get_test_link_data()
    link_data['note'] = f"HOD link from staging CI at {time.time()}"

    code, body = api_post("/v1/related/add", STAGING_JWT_HOD, link_data)

    try:
        # Accept both 200 (created) and 409 (already exists)
        assert code in [200, 409], f"Expected 200 or 409, got {code}"

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
    params = {
        "entity_type": "invalid_entity",
        "entity_id": STAGING_WORK_ORDER_ID,
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
    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 3  # Request only 3 results per group
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}"

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

def test_limit_exceeds_max_400():
    """TEST 6: limit > 50 returns 400"""
    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 100  # Exceeds max of 50
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        results.record_pass("test_limit_exceeds_max_400")

    except AssertionError as e:
        if code == 500:
            results.record_500("test_limit_exceeds_max_400")
        else:
            results.record_fail("test_limit_exceeds_max_400", e)

def test_match_reasons_present():
    """TEST 7: match_reasons present in response items"""
    params = {
        "entity_type": "work_order",
        "entity_id": STAGING_WORK_ORDER_ID,
        "limit": 10
    }

    code, body = api_get("/v1/related", STAGING_JWT_CREW, params)

    try:
        assert code == 200, f"Expected 200, got {code}"

        # Check that items have match_reasons
        for group in body.get('groups', []):
            for item in group.get('items', []):
                assert 'match_reasons' in item, f"Missing match_reasons in item {item.get('id')}"
                assert isinstance(item['match_reasons'], list), "match_reasons should be a list"
                assert len(item['match_reasons']) > 0, "match_reasons should not be empty"

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
    """Validate required environment variables"""
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set all required variables before running staging CI tests.")
        sys.exit(1)

def main():
    """Run staging CI test suite"""
    print("="*80)
    print("P1 Show Related - Staging CI Tests")
    print("="*80)
    print(f"Staging API: {STAGING_API_URL}")
    print(f"Yacht ID: {STAGING_YACHT_ID}")
    print(f"Work Order ID: {STAGING_WORK_ORDER_ID}")
    print(f"Part ID: {STAGING_PART_ID}")
    print("="*80)
    print()

    # Validate environment
    validate_environment()

    # Preflight checks (JWT decode + WO fetch)
    preflight_check_jwt_tokens()
    preflight_check_work_order()

    # Run test suite (subset of Docker matrix)
    print("="*80)
    print("RUNNING TESTS")
    print("="*80)
    print()

    test_crew_view_related_200()
    test_crew_cannot_add_link_403()
    test_hod_can_add_link_200()
    test_invalid_entity_type_400()
    test_caps_enforced()
    test_limit_exceeds_max_400()
    test_match_reasons_present()

    # Print summary and exit
    exit_code = results.print_summary()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
