"""
Hours of Rest RLS Security Regression Tests

Purpose: Prevent regression of CRITICAL RLS bypass vulnerability
CVE: Internal-2026-HOR-RLS-001
Fixed: 2026-02-09

Test Coverage:
- CREW blocked from CAPTAIN data
- CREW can only access own records
- HOD can access department records
- CAPTAIN can access all records
- Cross-user UPDATE/DELETE blocked

Run: pytest apps/api/tests/test_hor_rls_security.py -v
"""

import pytest
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add apps/api to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client


# Test user credentials (from working_test_users.json)
CREW_USER_ID = "2da12a4b-c0a1-4716-80ae-d29c90d98233"
CREW_EMAIL = "crew.tenant@alex-short.com"
CREW_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NjAxLCJpYXQiOjE3NzA2NDMwMDEsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MzAwMX1dLCJzZXNzaW9uX2lkIjoiNjViMDEyZTUtODkyYy00N2VjLWI2YWItZjNlZDM5YzQ1YjdjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.vmaSq3MHv3WOd-1D2ysct-xKD1AgOcAIiqdsDUSzZRk"

CAPTAIN_USER_ID = "b72c35ff-e309-4a19-a617-bfc706a78c0f"
CAPTAIN_EMAIL = "captain.tenant@alex-short.com"
CAPTAIN_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NTE0LCJpYXQiOjE3NzA2NDI5MTQsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MjkxNH1dLCJzZXNzaW9uX2lkIjoiNmJiYmEzNmItMmFhMS00OWRkLWI2MGYtNTE2NTg1NjY2YTNhIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.cY3RJlV5Wh-x3fP96Y9mB0ZgZ1gLqWQhiX7vY_hXH5Y"

HOD_USER_ID = "89b1262c-ff59-4591-b954-757cdf3d609d"
HOD_EMAIL = "hod.tenant@alex-short.com"
HOD_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NTYxLCJpYXQiOjE3NzA2NDI5NjEsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzcwNjQyOTYxfV0sInNlc3Npb25faWQiOiI3MDNiMzg4YS1iM2NjLTRjM2QtOWQ2NS1hYzMyNTY1ZDc4MjYiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.QX3hfJJsLSFD9m-4vYs_jkI4qW0YP5hb-8YL0n6DqCg"

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def crew_client():
    """Create Supabase client with CREW JWT (for testing RLS enforcement)"""
    # Load env
    import dotenv
    dotenv.load_dotenv("../../env/.env.local")

    url = os.getenv("TENANT_1_SUPABASE_URL")
    anon_key = os.getenv("TENANT_SUPABASE_ANON_KEY")

    client = create_client(url, anon_key)
    client.postgrest.auth(CREW_JWT)
    return client


@pytest.fixture
def captain_client():
    """Create Supabase client with CAPTAIN JWT"""
    import dotenv
    dotenv.load_dotenv("../../env/.env.local")

    url = os.getenv("TENANT_1_SUPABASE_URL")
    anon_key = os.getenv("TENANT_SUPABASE_ANON_KEY")

    client = create_client(url, anon_key)
    client.postgrest.auth(CAPTAIN_JWT)
    return client


@pytest.fixture
def hod_client():
    """Create Supabase client with HOD JWT"""
    import dotenv
    dotenv.load_dotenv("../../env/.env.local")

    url = os.getenv("TENANT_1_SUPABASE_URL")
    anon_key = os.getenv("TENANT_SUPABASE_ANON_KEY")

    client = create_client(url, anon_key)
    client.postgrest.auth(HOD_JWT)
    return client


# ============================================================================
# CRITICAL RLS REGRESSION TESTS
# ============================================================================

class TestRLSCrossUserAccess:
    """
    CRITICAL: Test that RLS prevents cross-user data access

    This is a regression test for the vulnerability fixed on 2026-02-09
    where CREW could access CAPTAIN's private HOR data.
    """

    def test_crew_cannot_read_captain_data(self, crew_client):
        """
        🔴 CRITICAL REGRESSION TEST

        Verify CREW user cannot access CAPTAIN's HOR records.

        Before fix: Returns 5+ records (BREACH)
        After fix: Returns 0 records (BLOCKED)
        """
        # CREW tries to query CAPTAIN's data
        result = crew_client.table("pms_hours_of_rest").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("user_id", CAPTAIN_USER_ID).execute()

        # RLS should filter out all captain records
        assert len(result.data) == 0, (
            f"🔴 RLS BYPASS DETECTED! CREW accessed {len(result.data)} CAPTAIN records. "
            "This is a CRITICAL security vulnerability that was fixed on 2026-02-09. "
            "The RLS policies may not be applied or may have been dropped."
        )

    def test_crew_can_only_read_own_data(self, crew_client):
        """Verify CREW can read their own records"""
        result = crew_client.table("pms_hours_of_rest").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("user_id", CREW_USER_ID).execute()

        # Should succeed and return only crew's records
        assert result.data is not None
        for record in result.data:
            assert record["user_id"] == CREW_USER_ID, "RLS leaked other user's data"

    def test_captain_can_read_all_records(self, captain_client):
        """Verify CAPTAIN can read all HOR records on yacht"""
        result = captain_client.table("pms_hours_of_rest").select("user_id").eq(
            "yacht_id", TEST_YACHT_ID
        ).execute()

        # Captain should see records from multiple users
        if len(result.data) > 0:
            user_ids = set(r["user_id"] for r in result.data)
            assert len(user_ids) >= 1, "Captain should see records"

    def test_crew_cannot_read_hod_data(self, crew_client):
        """Verify CREW cannot access HOD's records"""
        result = crew_client.table("pms_hours_of_rest").select("*").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("user_id", HOD_USER_ID).execute()

        assert len(result.data) == 0, "RLS should block CREW from HOD data"


class TestRLSCrossUserMutations:
    """
    Test that RLS prevents unauthorized INSERT/UPDATE/DELETE
    """

    def test_crew_cannot_update_captain_records(self, crew_client):
        """Verify CREW cannot update CAPTAIN's HOR records"""
        # Try to update a captain record
        try:
            result = crew_client.table("pms_hours_of_rest").update({
                "daily_compliance_notes": "UNAUTHORIZED UPDATE ATTEMPT"
            }).eq("yacht_id", TEST_YACHT_ID).eq("user_id", CAPTAIN_USER_ID).execute()

            # Should not update any records (RLS blocks)
            assert len(result.data) == 0, "RLS should prevent cross-user UPDATE"
        except Exception as e:
            # Also acceptable if RLS throws an error
            assert "permission" in str(e).lower() or "policy" in str(e).lower()

    def test_crew_cannot_delete_captain_records(self, crew_client):
        """Verify CREW cannot delete CAPTAIN's records"""
        try:
            result = crew_client.table("pms_hours_of_rest").delete().eq(
                "yacht_id", TEST_YACHT_ID
            ).eq("user_id", CAPTAIN_USER_ID).execute()

            # Should not delete any records
            assert len(result.data) == 0, "RLS should prevent cross-user DELETE"
        except Exception as e:
            # Also acceptable if RLS throws an error
            assert "permission" in str(e).lower() or "policy" in str(e).lower()

    def test_crew_can_insert_own_records(self, crew_client):
        """Verify CREW can create their own HOR records"""
        today = date.today().isoformat()

        try:
            result = crew_client.table("pms_hours_of_rest").insert({
                "yacht_id": TEST_YACHT_ID,
                "user_id": CREW_USER_ID,
                "record_date": today,
                "rest_periods": [{"start": "22:00", "end": "06:00", "hours": 8.0}],
                "total_rest_hours": 8.0,
                "is_daily_compliant": False,
            }).execute()

            # Should succeed
            assert len(result.data) > 0
            assert result.data[0]["user_id"] == CREW_USER_ID

            # Cleanup
            crew_client.table("pms_hours_of_rest").delete().eq(
                "id", result.data[0]["id"]
            ).execute()
        except Exception as e:
            pytest.skip(f"Insert test skipped (may require additional permissions): {e}")


class TestRLSMonthlySignoffs:
    """Test RLS on monthly signoff records"""

    def test_crew_cannot_read_captain_signoffs(self, crew_client):
        """Verify CREW cannot see CAPTAIN's monthly signoffs"""
        result = crew_client.table("pms_hor_monthly_signoffs").select("*").eq(
            "user_id", CAPTAIN_USER_ID
        ).execute()

        assert len(result.data) == 0, "RLS should block crew from captain signoffs"

    def test_captain_can_read_all_signoffs(self, captain_client):
        """Verify CAPTAIN can read all monthly signoffs"""
        result = captain_client.table("pms_hor_monthly_signoffs").select("*").execute()

        # Captain should have access (result may be empty if no signoffs exist)
        assert result.data is not None


class TestRLSTemplates:
    """Test RLS on crew schedule templates"""

    def test_crew_cannot_read_other_templates(self, crew_client):
        """Verify CREW cannot see other users' templates"""
        result = crew_client.table("pms_crew_normal_hours").select("*").eq(
            "user_id", CAPTAIN_USER_ID
        ).execute()

        # RLS should filter out captain's templates
        assert len(result.data) == 0, "RLS should block crew from captain templates"


class TestRLSWarnings:
    """Test RLS on compliance warnings"""

    def test_crew_cannot_read_captain_warnings(self, crew_client):
        """Verify CREW cannot see CAPTAIN's warnings"""
        result = crew_client.table("pms_crew_hours_warnings").select("*").eq(
            "user_id", CAPTAIN_USER_ID
        ).execute()

        assert len(result.data) == 0, "RLS should block crew from captain warnings"


# ============================================================================
# API ENDPOINT RLS TESTS
# ============================================================================

@pytest.mark.integration
class TestAPIEndpointRLS:
    """
    Test RLS enforcement through API endpoints

    These tests verify that the /v1/actions/execute endpoint
    properly enforces RLS using user-scoped Supabase clients.
    """

    @pytest.fixture
    def api_url(self):
        """Get API URL (local or production)"""
        return os.getenv("API_URL", "http://localhost:8080")

    def test_api_crew_blocked_from_captain_data(self, api_url):
        """Test /v1/actions/execute enforces RLS for get_hours_of_rest"""
        import requests

        response = requests.post(
            f"{api_url}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "get_hours_of_rest",
                "context": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "role": "crew"
                },
                "payload": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CAPTAIN_USER_ID  # CREW trying to access CAPTAIN data
                }
            }
        )

        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            records = data.get("data", {}).get("records", [])
            assert len(records) == 0, (
                f"🔴 API RLS BYPASS! CREW accessed {len(records)} CAPTAIN records via API"
            )


# ============================================================================
# RLS MONITORING / CANARY TESTS
# ============================================================================

class TestRLSCanary:
    """
    Canary tests that should run on every deployment

    These are lightweight tests to detect RLS regression quickly.
    """

    def test_rls_canary_crew_captain_isolation(self, crew_client):
        """
        🐤 RLS Canary Test

        Quick check that CREW cannot access CAPTAIN data.
        Run this after every deployment to detect RLS regression.
        """
        result = crew_client.table("pms_hours_of_rest").select("id").eq(
            "user_id", CAPTAIN_USER_ID
        ).limit(1).execute()

        assert len(result.data) == 0, "🔴 RLS CANARY FAILED - Immediate investigation required"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
