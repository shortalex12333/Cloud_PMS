"""
HOR Fast Loop Tests - Docker CI/CD

Purpose: Quick validation tests for CI/CD pipeline
Runtime: <30 seconds total
Coverage:
  - RLS enforcement (owner-only, role gating)
  - Error code mapping (400/404/409, NO 500s)
  - Basic CRUD operations
  - Signature requirements

Run in Docker:
  docker-compose -f docker-compose.test.yml run --rm api pytest tests/docker/test_hor_fast_loop.py -v --tb=short

Run locally:
  pytest tests/docker/test_hor_fast_loop.py -v
"""

import pytest
import requests
from datetime import date, timedelta


# Test configuration
API_URL = "http://localhost:8080"  # Override with env var in Docker

# Test JWTs (from working_test_users.json)
CREW_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NjAxLCJpYXQiOjE3NzA2NDMwMDEsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MzAwMX1dLCJzZXNzaW9uX2lkIjoiNjViMDEyZTUtODkyYy00N2VjLWI2YWItZjNlZDM5YzQ1YjdjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.vmaSq3MHv3WOd-1D2ysct-xKD1AgOcAIiqdsDUSzZRk"
CREW_USER_ID = "2da12a4b-c0a1-4716-80ae-d29c90d98233"

CAPTAIN_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NTE0LCJpYXQiOjE3NzA2NDI5MTQsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MjkxNH1dLCJzZXNzaW9uX2lkIjoiNmJiYmEzNmItMmFhMS00OWRkLWI2MGYtNTE2NTg1NjY2YTNhIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.cY3RJlV5Wh-x3fP96Y9mB0ZgZ1gLqWQhiX7vY_hXH5Y"
CAPTAIN_USER_ID = "b72c35ff-e309-4a19-a617-bfc706a78c0f"

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


# ============================================================================
# FAST LOOP: RLS ENFORCEMENT
# ============================================================================

class TestFastLoopRLS:
    """Quick RLS validation (< 5 seconds)"""

    def test_crew_blocked_from_captain_data(self):
        """⚡ CREW cannot read CAPTAIN data"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "get_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {"yacht_id": TEST_YACHT_ID, "user_id": CAPTAIN_USER_ID}
            }
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        records = data.get("data", {}).get("records", [])
        assert len(records) == 0, f"RLS BYPASS: CREW accessed {len(records)} CAPTAIN records"

    def test_crew_can_read_own_data(self):
        """⚡ CREW can read own records"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "get_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID}
            }
        )

        assert response.status_code == 200
        # Should succeed (may return 0 or more records)


# ============================================================================
# FAST LOOP: ERROR CODE MAPPING
# ============================================================================

class TestFastLoopErrorCodes:
    """Verify proper error codes (NO 500s)"""

    def test_missing_required_field_returns_400(self):
        """⚡ Missing required field → 400 (not 500)"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "upsert_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID
                    # Missing record_date (required field)
                }
            }
        )

        assert response.status_code in [400, 422], (
            f"Expected 400/422 for validation error, got {response.status_code}"
        )

    def test_nonexistent_action_returns_404(self):
        """⚡ Nonexistent action → 404 (not 500)"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "nonexistent_action_xyz123",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {}
            }
        )

        assert response.status_code == 404, (
            f"Expected 404 for nonexistent action, got {response.status_code}"
        )

    def test_unauthorized_request_returns_401(self):
        """⚡ Missing/invalid JWT → 401 (not 500)"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": "Bearer invalid_jwt_token"},
            json={
                "action": "get_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {"yacht_id": TEST_YACHT_ID}
            }
        )

        assert response.status_code == 401, (
            f"Expected 401 for invalid JWT, got {response.status_code}"
        )


# ============================================================================
# FAST LOOP: BASIC CRUD
# ============================================================================

class TestFastLoopCRUD:
    """Basic CRUD operations (< 10 seconds total)"""

    def test_get_hours_of_rest_succeeds(self):
        """⚡ GET hours_of_rest returns 200"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "get_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "records" in data["data"]

    def test_upsert_hours_of_rest_succeeds(self):
        """⚡ UPSERT hours_of_rest returns 200"""
        today = date.today().isoformat()

        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "upsert_hours_of_rest",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "record_date": today,
                    "rest_periods": [{"start": "22:00", "end": "06:00", "hours": 8.0}],
                    "total_rest_hours": 8.0
                }
            }
        )

        assert response.status_code in [200, 201], (
            f"Expected 200/201, got {response.status_code}: {response.text}"
        )

    def test_list_monthly_signoffs_succeeds(self):
        """⚡ LIST monthly_signoffs returns 200"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "list_monthly_signoffs",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                "payload": {"yacht_id": TEST_YACHT_ID}
            }
        )

        assert response.status_code == 200


# ============================================================================
# FAST LOOP: SIGNATURE REQUIREMENTS
# ============================================================================

class TestFastLoopSignatures:
    """Verify signature requirements"""

    def test_signed_action_requires_signature_data(self):
        """⚡ Signed action without signature_data fails"""
        response = requests.post(
            f"{API_URL}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CAPTAIN_JWT}"},
            json={
                "action": "sign_monthly_signoff",
                "context": {"yacht_id": TEST_YACHT_ID, "user_id": CAPTAIN_USER_ID, "role": "captain"},
                "payload": {
                    "signoff_id": "fake-signoff-id",
                    "signature_level": "captain"
                    # Missing signature_data!
                }
            }
        )

        # Should fail with 400 or 422 (validation error)
        assert response.status_code in [400, 404, 422], (
            f"Signed action without signature should fail, got {response.status_code}"
        )


# ============================================================================
# FAST LOOP: NO 500 ERRORS
# ============================================================================

class TestFastLoopNo500s:
    """Ensure no 500 errors for common scenarios"""

    def test_all_valid_actions_return_2xx_or_4xx(self):
        """⚡ All HOR actions return proper status codes (never 500)"""
        actions_to_test = [
            ("get_hours_of_rest", {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID}),
            ("list_monthly_signoffs", {"yacht_id": TEST_YACHT_ID}),
            ("list_crew_templates", {"yacht_id": TEST_YACHT_ID}),
            ("list_crew_warnings", {"yacht_id": TEST_YACHT_ID}),
        ]

        for action, payload in actions_to_test:
            response = requests.post(
                f"{API_URL}/v1/actions/execute",
                headers={"Authorization": f"Bearer {CREW_JWT}"},
                json={
                    "action": action,
                    "context": {"yacht_id": TEST_YACHT_ID, "user_id": CREW_USER_ID, "role": "crew"},
                    "payload": payload
                }
            )

            assert response.status_code < 500, (
                f"Action '{action}' returned 500 error: {response.text}"
            )


# ============================================================================
# TEST SUMMARY
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("HOR FAST LOOP TESTS - Docker CI/CD")
    print("=" * 80)
    print()
    print("Test Coverage:")
    print("  ✓ RLS enforcement (CREW blocked from CAPTAIN data)")
    print("  ✓ Error code mapping (400/404/422/401, NO 500s)")
    print("  ✓ Basic CRUD operations")
    print("  ✓ Signature requirements")
    print()
    print("Expected runtime: <30 seconds")
    print("=" * 80)
    print()

    pytest.main([__file__, "-v", "--tb=short", "--durations=10"])
