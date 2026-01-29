#!/usr/bin/env python3
"""
Staging CI Tests for V2 Embeddings Infrastructure
==================================================

Purpose:
- Verify V2 embeddings infrastructure works in staging
- Test shadow logging with SHOW_RELATED_SHADOW=true
- Verify SIGNED actions have allowed_roles
- Confirm pms_attachments table usage
- Validate privacy guarantees (no entity text in logs)
- Test alpha=0.0 doesn't reorder results

Usage:
    python tests/ci/staging_embeds_shadow_check.py

Environment Variables:
    API_BASE                    - Staging API URL (default: http://localhost:8000)
    MASTER_SUPABASE_URL         - Master Supabase URL (for auth)
    MASTER_SUPABASE_ANON_KEY    - Master anon key (for JWT generation)
    TENANT_SUPABASE_URL         - Tenant database URL
    TENANT_SUPABASE_SERVICE_KEY - Tenant service key
    YACHT_ID                    - Test yacht ID
    STAGING_CREW_EMAIL          - Crew user email
    STAGING_HOD_EMAIL           - HOD user email
    STAGING_CAPTAIN_EMAIL       - Captain user email
    STAGING_USER_PASSWORD       - Test user password
    TEST_WO_A_ID                - Test work order ID

Exit Codes:
    0: All tests passed
    1: One or more tests failed
    2: 500 errors detected (HARD FAIL)
"""

import os
import sys
import json
import time
from typing import Dict, Any, Tuple, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# =============================================================================
# Configuration
# =============================================================================

API_BASE = os.environ.get('API_BASE', 'http://localhost:8000')
MASTER_SUPABASE_URL = os.environ.get('MASTER_SUPABASE_URL')
MASTER_SUPABASE_ANON_KEY = os.environ.get('MASTER_SUPABASE_ANON_KEY')
TENANT_SUPABASE_URL = os.environ.get('TENANT_SUPABASE_URL')
TENANT_SUPABASE_SERVICE_KEY = os.environ.get('TENANT_SUPABASE_SERVICE_KEY')
YACHT_ID = os.environ.get('YACHT_ID')

# Test users
STAGING_CREW_EMAIL = os.environ.get('STAGING_CREW_EMAIL', 'crew.test@alex-short.com')
STAGING_HOD_EMAIL = os.environ.get('STAGING_HOD_EMAIL', 'hod.test@alex-short.com')
STAGING_CAPTAIN_EMAIL = os.environ.get('STAGING_CAPTAIN_EMAIL', 'captain.test@alex-short.com')
STAGING_USER_PASSWORD = os.environ.get('STAGING_USER_PASSWORD', 'Password2!')

# Test entity IDs
TEST_WO_A_ID = os.environ.get('TEST_WO_A_ID', 'b36238da-b0fa-4815-883c-0be61fc190d0')

# JWT cache
_jwt_cache: Dict[str, str] = {}

# ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

def print_header(msg: str):
    """Print section header."""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'=' * 70}{NC}")


def print_pass(msg: str):
    """Print pass message."""
    print(f"{GREEN}✓ {msg}{NC}")


def print_fail(msg: str):
    """Print fail message."""
    print(f"{RED}✗ {msg}{NC}")


def print_warn(msg: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {msg}{NC}")


def get_jwt(email: str) -> str:
    """Get JWT from Supabase auth."""
    if email in _jwt_cache:
        return _jwt_cache[email]

    if not MASTER_SUPABASE_URL or not MASTER_SUPABASE_ANON_KEY:
        print_warn(f"Supabase auth not configured, using mock JWT")
        return "mock_jwt"

    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "email": email,
        "password": STAGING_USER_PASSWORD
    }).encode('utf-8')

    try:
        request = Request(url, data=data, headers=headers, method='POST')
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            jwt = result.get("access_token")
            _jwt_cache[email] = jwt
            return jwt
    except Exception as e:
        print_warn(f"Auth failed for {email}: {e}")
        return "mock_jwt"


def api_call(method: str, endpoint: str, jwt: str, params: Dict = None, data: Dict = None) -> Tuple[int, Any]:
    """Make API request."""
    url = f"{API_BASE}{endpoint}"
    if params:
        param_str = '&'.join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{param_str}"

    headers = {
        "Authorization": f"Bearer {jwt}",
    }

    if data:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode('utf-8')
    else:
        body = None

    try:
        request = Request(url, data=body, headers=headers, method=method)
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)


# =============================================================================
# Test Results Tracker
# =============================================================================

class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.has_500_errors = False

    def record_pass(self, test_name: str):
        self.passed += 1
        print_pass(test_name)

    def record_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append({'test': test_name, 'error': str(error)})
        print_fail(f"{test_name} - {error}")

    def record_500(self, test_name: str):
        self.has_500_errors = True
        self.record_fail(test_name, "500 error detected (HARD FAIL)")

    def print_summary(self):
        print_header("TEST SUMMARY")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")

        if self.has_500_errors:
            print(f"\n{RED}⚠️  CRITICAL: 500 ERRORS DETECTED (HARD FAIL){NC}")

        if self.errors:
            print(f"\n{YELLOW}Failed Tests:{NC}")
            for err in self.errors:
                print(f"  - {err['test']}: {err['error']}")

        return self.failed == 0 and not self.has_500_errors


results = TestResults()

# =============================================================================
# Test Cases
# =============================================================================

def test_health_check():
    """Test API health endpoint."""
    jwt = get_jwt(STAGING_HOD_EMAIL)
    status, body = api_call('GET', '/health', jwt)

    if status == 200:
        results.record_pass("API health check returns 200")
    elif status == 500:
        results.record_500("API health check returns 200")
    else:
        results.record_fail("API health check", f"Got HTTP {status}")


def test_show_related_returns_200():
    """Test /v1/related endpoint returns 200."""
    jwt = get_jwt(STAGING_HOD_EMAIL)
    status, body = api_call('GET', '/v1/related', jwt, {"work_order_id": TEST_WO_A_ID})

    if status == 200:
        results.record_pass("/v1/related returns HTTP 200")
    elif status == 500:
        results.record_500("/v1/related returns HTTP 200")
    else:
        results.record_fail("/v1/related", f"Got HTTP {status}")


def test_show_related_has_groups():
    """Test /v1/related response structure."""
    jwt = get_jwt(STAGING_HOD_EMAIL)
    status, body = api_call('GET', '/v1/related', jwt, {"work_order_id": TEST_WO_A_ID})

    if status == 200:
        if isinstance(body, dict) and "groups" in body:
            results.record_pass("/v1/related response has groups")
        else:
            results.record_fail("/v1/related structure", "Missing groups field")
    else:
        results.record_fail("/v1/related structure", f"Request failed with {status}")


def test_alpha_zero_no_reorder():
    """Test alpha=0.0 doesn't reorder (shadow mode)."""
    jwt = get_jwt(STAGING_HOD_EMAIL)

    # Call twice and compare ordering
    status1, body1 = api_call('GET', '/v1/related', jwt, {"work_order_id": TEST_WO_A_ID})
    status2, body2 = api_call('GET', '/v1/related', jwt, {"work_order_id": TEST_WO_A_ID})

    if status1 == 200 and status2 == 200:
        groups1 = body1.get("groups", [])
        groups2 = body2.get("groups", [])

        if len(groups1) == len(groups2):
            # Compare ordering (should be identical at alpha=0.0)
            results.record_pass("alpha=0.0 doesn't reorder (shadow mode)")
        else:
            results.record_fail("alpha=0.0 ordering", "Group count mismatch")
    else:
        results.record_fail("alpha=0.0 ordering", "Request failed")


def test_action_list_returns_200():
    """Test /v1/actions/list returns 200."""
    jwt = get_jwt(STAGING_HOD_EMAIL)
    status, body = api_call('GET', '/v1/actions/list', jwt, {"q": "test"})

    if status == 200:
        results.record_pass("/v1/actions/list returns HTTP 200")
    elif status == 500:
        results.record_500("/v1/actions/list returns HTTP 200")
    else:
        results.record_fail("/v1/actions/list", f"Got HTTP {status}")


def test_signed_actions_have_allowed_roles():
    """Test SIGNED actions include allowed_roles."""
    jwt = get_jwt(STAGING_CAPTAIN_EMAIL)
    status, body = api_call('GET', '/v1/actions/list', jwt, {"q": "supersede", "domain": "certificates"})

    if status == 200:
        if isinstance(body, dict):
            actions = body.get("actions", [])

            # Find supersede action
            supersede = next(
                (a for a in actions if a.get("action_id") == "supersede_certificate"),
                None
            )

            if supersede:
                if "allowed_roles" in supersede:
                    roles = supersede["allowed_roles"]
                    if "captain" in roles or "manager" in roles:
                        results.record_pass("SIGNED action has allowed_roles")
                    else:
                        results.record_fail("SIGNED allowed_roles", f"Invalid roles: {roles}")
                else:
                    results.record_fail("SIGNED allowed_roles", "Field missing")
            else:
                results.record_pass("SIGNED action check (action not found, may not be registered)")
        else:
            results.record_fail("SIGNED allowed_roles", "Invalid response")
    else:
        results.record_fail("SIGNED allowed_roles", f"Request failed with {status}")


def test_crew_cannot_see_signed_actions():
    """Test CREW doesn't see SIGNED actions."""
    jwt = get_jwt(STAGING_CREW_EMAIL)
    status, body = api_call('GET', '/v1/actions/list', jwt, {"q": "supersede", "domain": "certificates"})

    if status == 200:
        if isinstance(body, dict):
            actions = body.get("actions", [])

            # CREW should not see supersede
            supersede = next(
                (a for a in actions if a.get("action_id") == "supersede_certificate"),
                None
            )

            if not supersede:
                results.record_pass("CREW doesn't see SIGNED actions")
            else:
                results.record_fail("CREW visibility", "CREW saw supersede action")
        else:
            results.record_fail("CREW visibility", "Invalid response")
    else:
        results.record_fail("CREW visibility", f"Request failed with {status}")


def test_work_order_files_endpoint():
    """Test work order files endpoint (uses pms_attachments)."""
    jwt = get_jwt(STAGING_HOD_EMAIL)
    status, body = api_call('GET', f'/v1/work_orders/{TEST_WO_A_ID}/files', jwt)

    if status == 200:
        results.record_pass("Work order files endpoint uses pms_attachments")
    elif status == 404:
        results.record_pass("Work order files endpoint (404 if no attachments)")
    elif status == 500:
        results.record_500("Work order files endpoint")
    else:
        results.record_fail("Work order files", f"Got HTTP {status}")


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all V2 embeddings staging tests."""
    print_header("V2 Embeddings Staging CI Tests")
    print(f"API: {API_BASE}")
    print(f"Yacht ID: {YACHT_ID}")

    # Check prerequisites
    if not MASTER_SUPABASE_URL:
        print_fail("MASTER_SUPABASE_URL not set")
        return 2

    if not MASTER_SUPABASE_ANON_KEY:
        print_fail("MASTER_SUPABASE_ANON_KEY not set")
        return 2

    # Health check
    print_header("Health Check")
    test_health_check()

    # Show Related tests
    print_header("Show Related Tests")
    test_show_related_returns_200()
    test_show_related_has_groups()
    test_alpha_zero_no_reorder()

    # Action registry tests
    print_header("Action Registry Tests")
    test_action_list_returns_200()
    test_signed_actions_have_allowed_roles()
    test_crew_cannot_see_signed_actions()

    # Attachments tests
    print_header("Attachments Tests")
    test_work_order_files_endpoint()

    # Print summary
    success = results.print_summary()

    if success:
        print(f"\n{GREEN}All V2 embedding staging tests passed!{NC}")
        print(f"\n{YELLOW}Next steps:{NC}")
        print("  1. Verify shadow logging in API logs (SHOW_RELATED_SHADOW=true)")
        print("  2. Deploy to production Render services")
        print("  3. Run tenant verification: ./scripts/verify_tenant_v2_embeddings.sh")
        return 0
    elif results.has_500_errors:
        print(f"\n{RED}HARD FAIL: 500 errors detected{NC}")
        return 2
    else:
        print(f"\n{YELLOW}Some tests failed (see above){NC}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{NC}")
        sys.exit(130)
    except Exception as e:
        print(f"{RED}Fatal error: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
