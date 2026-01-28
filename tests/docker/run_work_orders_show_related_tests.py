#!/usr/bin/env python3
"""
Docker Tests: P1 Show Related Feature
Feature: Work Order Lens - Show Related Entities
Date: 2026-01-28

Test Matrix (14 tests):
- CREW/HOD/Captain role matrix
- All error codes (400, 403, 404, 409, 500)
- Cross-yacht isolation (404 not 403)
- Duplicate link prevention (409)
- Self-link prevention (400)
- Invalid link_type (400)
- limit validation (0, negative, >50 all return 400)
- Match reasons presence
- Caps enforcement
- Explicit links roundtrip (add then read)
- Zero 500s requirement (HARD FAIL)

Run: python tests/docker/run_work_orders_show_related_tests.py
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# =============================================================================
# CONFIGURATION
# =============================================================================

# API and Supabase configuration
API_BASE_URL = os.getenv('API_BASE', os.getenv('API_BASE_URL', 'http://localhost:3000'))
MASTER_SUPABASE_URL = os.getenv('MASTER_SUPABASE_URL')
MASTER_SUPABASE_ANON_KEY = os.getenv('MASTER_SUPABASE_ANON_KEY')
TENANT_SUPABASE_URL = os.getenv('TENANT_SUPABASE_URL')
TENANT_SUPABASE_SERVICE_KEY = os.getenv('TENANT_SUPABASE_SERVICE_KEY')

# Test yacht IDs
YACHT_A_ID = os.getenv('YACHT_ID', os.getenv('TEST_YACHT_A_ID', '85fe1119-b04c-41ac-80f1-829d23322598'))
YACHT_B_ID = os.getenv('OTHER_YACHT_ID', os.getenv('TEST_YACHT_B_ID', '00000000-0000-0000-0000-000000000000'))

# Test entity IDs (seed these in Docker setup or use env vars)
TEST_WO_A_ID = os.getenv('TEST_WO_A_ID', '11111111-1111-1111-1111-11111111111a')
TEST_WO_B_ID = os.getenv('TEST_WO_B_ID', '11111111-1111-1111-1111-11111111111b')
TEST_PART_A_ID = os.getenv('TEST_PART_A_ID', '22222222-2222-2222-2222-22222222222a')

# Test users (for real JWT authentication)
TEST_PASSWORD = os.getenv('TEST_PASSWORD', 'Password2!')
TEST_USERS = {
    'crew': os.getenv('CREW_EMAIL', 'crew.test@alex-short.com'),
    'chief_engineer': os.getenv('HOD_EMAIL', 'hod.test@alex-short.com'),
    'captain': os.getenv('CAPTAIN_EMAIL', 'captain.test@alex-short.com'),
}

# JWT cache
_jwt_cache: Dict[str, str] = {}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_real_jwt(role: str) -> str:
    """Get real JWT from Supabase auth."""
    if role in _jwt_cache:
        return _jwt_cache[role]

    email = TEST_USERS.get(role)
    if not email:
        print(f"WARNING: No email configured for role {role}")
        return f"mock_jwt_{role}"

    if not MASTER_SUPABASE_URL or not MASTER_SUPABASE_ANON_KEY:
        print("WARNING: Supabase auth not configured, using mock JWT")
        return f"mock_jwt_{role}"

    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, json={
            "email": email,
            "password": TEST_PASSWORD
        }, timeout=10)
        if response.status_code == 200:
            jwt = response.json().get("access_token")
            _jwt_cache[role] = jwt
            return jwt
        print(f"WARNING: Auth failed for {email}: {response.status_code}")
        return f"mock_jwt_{role}"
    except Exception as e:
        print(f"WARNING: Auth error for {role}: {e}")
        return f"mock_jwt_{role}"


def get_test_jwt(yacht_id: str, role: str) -> str:
    """Get JWT for testing (uses real Supabase auth if configured)."""
    return get_real_jwt(role)


def api_get(endpoint: str, jwt: str) -> Tuple[int, Dict]:
    """Make GET request to API."""
    headers = {'Authorization': f'Bearer {jwt}'}
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        body = response.json()
    except:
        body = {'raw': response.text if 'response' in locals() else 'Connection failed'}
        return 0, body
    return response.status_code, body


def api_post(endpoint: str, jwt: str, data: Dict) -> Tuple[int, Dict]:
    """Make POST request to API."""
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=data)
        body = response.json()
    except:
        body = {'raw': response.text if 'response' in locals() else 'Connection failed'}
        return 0, body
    return response.status_code, body


def get_test_link_data(source_type='work_order', target_type='part', link_type='related'):
    """Generate test link data."""
    return {
        'source_entity_type': source_type,
        'source_entity_id': TEST_WO_A_ID,
        'target_entity_type': target_type,
        'target_entity_id': TEST_PART_A_ID,
        'link_type': link_type,
        'note': 'Test link created during Docker test'
    }


def get_error_msg(body: Dict) -> str:
    """Extract error message from response (FastAPI uses 'detail', not 'error')."""
    return body.get('detail') or body.get('error') or str(body)


# =============================================================================
# TEST SUITE
# =============================================================================

class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.has_500_errors = False

    def record_pass(self, test_name):
        self.passed += 1
        print(f"✅ PASS: {test_name}")

    def record_fail(self, test_name, error):
        self.failed += 1
        self.errors.append({'test': test_name, 'error': str(error)})
        print(f"❌ FAIL: {test_name} - {error}")

    def record_500(self, test_name):
        self.has_500_errors = True
        self.record_fail(test_name, "500 error detected (HARD FAIL)")

    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")

        if self.has_500_errors:
            print("\n⚠️  CRITICAL: 500 ERRORS DETECTED (HARD FAIL)")

        if self.errors:
            print("\nFailed Tests:")
            for err in self.errors:
                print(f"  - {err['test']}: {err['error']}")

        return self.failed == 0 and not self.has_500_errors


results = TestResults()


# =============================================================================
# TEST 1: CREW can view related entities (200)
# =============================================================================

def test_crew_read_200():
    """TEST 1: CREW can view related entities (200)"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    code, body = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=20", jwt_crew)

    try:
        assert code == 200, f"Expected 200, got {code}"
        assert 'groups' in body, "Missing 'groups' in response"
        assert 'add_related_enabled' in body, "Missing 'add_related_enabled' in response"
        assert 'group_counts' in body, "Missing 'group_counts' in response"

        # Verify match_reasons present when groups non-empty
        for group in body.get('groups', []):
            group_key = group.get('group_key', group.get('type', 'unknown'))
            if group.get('count', 0) > 0:
                assert len(group.get('items', [])) > 0, f"Group {group_key} has count > 0 but no items"
                for item in group['items']:
                    assert 'match_reasons' in item, f"Item {item.get('entity_id')} missing match_reasons"
                    assert len(item['match_reasons']) > 0, f"Item {item.get('entity_id')} has empty match_reasons"

        results.record_pass("test_crew_read_200")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_crew_read_200")
        else:
            results.record_fail("test_crew_read_200", e)


# =============================================================================
# TEST 2: CREW cannot add entity links (403)
# =============================================================================

def test_crew_add_link_403():
    """TEST 2: CREW cannot add entity links (403)"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    link_data = get_test_link_data()
    code, body = api_post("/v1/related/add", jwt_crew, link_data)

    try:
        assert code == 403, f"Expected 403, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'permission' in err_msg.lower() or 'forbidden' in err_msg.lower() or 'authorized' in err_msg.lower(), \
            f"Error message should mention permissions, got: {err_msg}"

        results.record_pass("test_crew_add_link_403")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_crew_add_link_403")
        else:
            results.record_fail("test_crew_add_link_403", e)


# =============================================================================
# TEST 3: HOD can add entity links (200)
# =============================================================================

def test_hod_add_link_200():
    """TEST 3: HOD can add entity links (200)"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')
    link_data = get_test_link_data()
    code, body = api_post("/v1/related/add", jwt_hod, link_data)

    try:
        # Allow 200 (success) or 409 (duplicate from previous test run)
        assert code in [200, 409], f"Expected 200 or 409, got {code}"

        if code == 200:
            assert 'link_id' in body, "Missing 'link_id' in response"

        results.record_pass("test_hod_add_link_200")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_hod_add_link_200")
        else:
            results.record_fail("test_hod_add_link_200", e)


# =============================================================================
# TEST 4: Duplicate link returns 409
# =============================================================================

def test_duplicate_link_409():
    """TEST 4: Duplicate link returns 409"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')
    link_data = get_test_link_data()

    # Add link first time (may already exist from TEST 3)
    code1, body1 = api_post("/v1/related/add", jwt_hod, link_data)

    # Try adding same link again
    code2, body2 = api_post("/v1/related/add", jwt_hod, link_data)

    try:
        assert code2 == 409, f"Expected 409 on duplicate, got {code2}"
        err_msg = get_error_msg(body2)
        assert err_msg, "Missing error message in response"
        assert 'already exists' in err_msg.lower() or 'duplicate' in err_msg.lower(), \
            f"Error message should mention duplicate/already exists, got: {err_msg}"

        results.record_pass("test_duplicate_link_409")
    except AssertionError as e:
        if code2 == 500:
            results.record_500("test_duplicate_link_409")
        else:
            results.record_fail("test_duplicate_link_409", e)


# =============================================================================
# TEST 5: source == target returns 400
# =============================================================================

def test_self_link_400():
    """TEST 5: source == target returns 400"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')
    self_link_data = {
        'source_entity_type': 'work_order',
        'source_entity_id': TEST_WO_A_ID,
        'target_entity_type': 'work_order',
        'target_entity_id': TEST_WO_A_ID,  # SAME as source
        'link_type': 'related'
    }
    code, body = api_post("/v1/related/add", jwt_hod, self_link_data)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'self' in err_msg.lower() or 'source == target' in err_msg.lower(), \
            f"Error message should mention self-link, got: {err_msg}"

        results.record_pass("test_self_link_400")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_self_link_400")
        else:
            results.record_fail("test_self_link_400", e)


# =============================================================================
# TEST 6: Invalid entity_type returns 400
# =============================================================================

def test_invalid_entity_type_400():
    """TEST 6: Invalid entity_type returns 400"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    code, body = api_get(f"/v1/related?entity_type=foo&entity_id={TEST_WO_A_ID}", jwt_crew)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'invalid' in err_msg.lower() or 'entity_type' in err_msg.lower(), \
            f"Error message should mention invalid entity_type, got: {err_msg}"

        results.record_pass("test_invalid_entity_type_400")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_invalid_entity_type_400")
        else:
            results.record_fail("test_invalid_entity_type_400", e)


# =============================================================================
# TEST 7: Non-existent entity returns 404
# =============================================================================

def test_not_found_404():
    """TEST 7: Non-existent entity returns 404"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    fake_id = '00000000-0000-0000-0000-000000000000'
    code, body = api_get(f"/v1/related?entity_type=work_order&entity_id={fake_id}", jwt_crew)

    try:
        assert code == 404, f"Expected 404, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'not found' in err_msg.lower(), \
            f"Error message should mention 'not found', got: {err_msg}"

        results.record_pass("test_not_found_404")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_not_found_404")
        else:
            results.record_fail("test_not_found_404", e)


# =============================================================================
# TEST 8: Cross-yacht entity returns 404 (not 403)
# =============================================================================

def test_cross_yacht_404():
    """TEST 8: Cross-yacht entity returns 404 (not 403, avoid yacht enumeration)"""
    jwt_yacht_a = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    code, body = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_B_ID}", jwt_yacht_a)

    try:
        assert code == 404, f"Expected 404 (not 403), got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'not found' in err_msg.lower(), \
            f"Error message should say 'not found' (not 'forbidden'), got: {err_msg}"

        results.record_pass("test_cross_yacht_404")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_cross_yacht_404")
        else:
            results.record_fail("test_cross_yacht_404", e)


# =============================================================================
# TEST 9: Caps enforced (limit param respected)
# =============================================================================

def test_caps_enforced():
    """TEST 9: Caps enforced (limit param respected)"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    code, body = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=5", jwt_crew)

    try:
        assert code == 200, f"Expected 200, got {code}"

        for group in body.get('groups', []):
            group_key = group.get('group_key', group.get('type', 'unknown'))
            assert len(group.get('items', [])) <= 5, \
                f"Group {group_key} has {len(group['items'])} items, expected <= 5"

        results.record_pass("test_caps_enforced")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_caps_enforced")
        else:
            results.record_fail("test_caps_enforced", e)


# =============================================================================
# TEST 10: Invalid link_type returns 400
# =============================================================================

def test_invalid_link_type_400():
    """TEST 10: Invalid link_type returns 400"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')
    invalid_link_data = get_test_link_data(link_type='invalid_type')
    code, body = api_post("/v1/related/add", jwt_hod, invalid_link_data)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'invalid' in err_msg.lower() or 'link_type' in err_msg.lower(), \
            f"Error message should mention invalid link_type, got: {err_msg}"

        results.record_pass("test_invalid_link_type_400")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_invalid_link_type_400")
        else:
            results.record_fail("test_invalid_link_type_400", e)


# =============================================================================
# TEST 11: Note too long returns 400
# =============================================================================

def test_note_too_long_400():
    """TEST 11: Note too long returns 400 (max 500 chars)"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')
    long_note_data = get_test_link_data()
    long_note_data['note'] = 'x' * 501  # 501 chars (over limit)
    code, body = api_post("/v1/related/add", jwt_hod, long_note_data)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'note' in err_msg.lower() or 'character' in err_msg.lower() or '500' in err_msg, \
            f"Error message should mention note length, got: {err_msg}"

        results.record_pass("test_note_too_long_400")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_note_too_long_400")
        else:
            results.record_fail("test_note_too_long_400", e)


# =============================================================================
# TEST 12: Limit > 50 returns 400
# =============================================================================

def test_limit_too_high_400():
    """TEST 12: Limit > 50 returns 400 (max 50)"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')
    code, body = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=100", jwt_crew)

    try:
        assert code == 400, f"Expected 400, got {code}"
        err_msg = get_error_msg(body)
        assert err_msg, "Missing error message in response"
        assert 'limit' in err_msg.lower() or '50' in err_msg, \
            f"Error message should mention limit, got: {err_msg}"

        results.record_pass("test_limit_too_high_400")
    except AssertionError as e:
        if code == 500:
            results.record_500("test_limit_too_high_400")
        else:
            results.record_fail("test_limit_too_high_400", e)


# =============================================================================
# TEST 13: Limit <= 0 returns 400
# =============================================================================

def test_limit_zero_or_negative_400():
    """TEST 13: limit <= 0 returns 400"""
    jwt_crew = get_test_jwt(yacht_id=YACHT_A_ID, role='crew')

    # Test limit = 0
    code1, body1 = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=0", jwt_crew)

    # Test limit = -1
    code2, body2 = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=-1", jwt_crew)

    try:
        assert code1 == 400 or code1 == 422, f"Expected 400/422 for limit=0, got {code1}"
        err_msg1 = get_error_msg(body1)
        assert err_msg1, "Missing error message in response for limit=0"

        assert code2 == 400 or code2 == 422, f"Expected 400/422 for limit=-1, got {code2}"
        err_msg2 = get_error_msg(body2)
        assert err_msg2, "Missing error message in response for limit=-1"

        results.record_pass("test_limit_zero_or_negative_400")
    except AssertionError as e:
        if code1 == 500 or code2 == 500:
            results.record_500("test_limit_zero_or_negative_400")
        else:
            results.record_fail("test_limit_zero_or_negative_400", e)


# =============================================================================
# TEST 14: Explicit links roundtrip (add link, then verify in read)
# =============================================================================

def test_explicit_links_roundtrip():
    """TEST 14: Add entity link, then verify it appears in explicit_links group"""
    jwt_hod = get_test_jwt(yacht_id=YACHT_A_ID, role='chief_engineer')

    # Create unique link data using timestamp to avoid duplicates
    unique_link_data = get_test_link_data()
    unique_link_data['note'] = f'Roundtrip test {datetime.now().timestamp()}'

    # Step 1: Add link
    code_add, body_add = api_post("/v1/related/add", jwt_hod, unique_link_data)

    try:
        # Allow 200 (created) or 409 (already exists from earlier run)
        assert code_add in [200, 409], f"Expected 200 or 409 for add, got {code_add}"

        # Step 2: Read related entities
        code_read, body_read = api_get(f"/v1/related?entity_type=work_order&entity_id={TEST_WO_A_ID}&limit=20", jwt_hod)

        assert code_read == 200, f"Expected 200 for read, got {code_read}"
        assert 'groups' in body_read, "Missing 'groups' in read response"

        # Step 3: Verify link appears in groups (merged into target entity type group)
        # The link should be merged into the 'parts' group since target_entity_type='part'
        found_link = False
        for group in body_read['groups']:
            # Link should be in parts group (target_entity_type='part')
            group_key = group.get('group_key', group.get('type', ''))
            if group_key == 'parts':
                for item in group.get('items', []):
                    if item['entity_id'] == TEST_PART_A_ID:
                        # Check that match_reasons includes explicit_link
                        match_reasons = item.get('match_reasons', [])
                        if any('explicit_link' in reason for reason in match_reasons):
                            found_link = True
                            break

            if found_link:
                break

        assert found_link, f"Added link not found in related entities response (target: {TEST_PART_A_ID})"

        results.record_pass("test_explicit_links_roundtrip")
    except AssertionError as e:
        if code_add == 500 or (code_read if 'code_read' in locals() else 0) == 500:
            results.record_500("test_explicit_links_roundtrip")
        else:
            results.record_fail("test_explicit_links_roundtrip", e)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*80)
    print("P1 SHOW RELATED - DOCKER TEST SUITE")
    print("="*80)
    print(f"API URL: {API_BASE_URL}")
    print(f"Yacht A: {YACHT_A_ID}")
    print(f"Yacht B: {YACHT_B_ID}")
    print(f"Test WO: {TEST_WO_A_ID}")
    print(f"Test Part: {TEST_PART_A_ID}")
    print("="*80 + "\n")

    # Run all tests
    print("\n🧪 Running tests...\n")

    test_crew_read_200()
    test_crew_add_link_403()
    test_hod_add_link_200()
    test_duplicate_link_409()
    test_self_link_400()
    test_invalid_entity_type_400()
    test_not_found_404()
    test_cross_yacht_404()
    test_caps_enforced()
    test_invalid_link_type_400()
    test_note_too_long_400()
    test_limit_too_high_400()
    test_limit_zero_or_negative_400()
    test_explicit_links_roundtrip()

    # Print summary
    success = results.print_summary()

    if success:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
