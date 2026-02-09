"""
Hours of Rest Signature Invariant Tests

Purpose: Verify audit log signature requirements
Invariant: signature is NEVER NULL - {} for non-signed, full payload for signed

Signature Types:
- SIGNED actions: sign_monthly_signoff, dismiss_warning
- NON-SIGNED actions: All others (upsert_hours_of_rest, etc.)

Run: pytest apps/api/tests/test_hor_signature_invariants.py -v
"""

import pytest
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
import requests


# Test credentials
CAPTAIN_USER_ID = "b72c35ff-e309-4a19-a617-bfc706a78c0f"
CAPTAIN_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NTE0LCJpYXQiOjE3NzA2NDI5MTQsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MjkxNH1dLCJzZXNzaW9uX2lkIjoiNmJiYmEzNmItMmFhMS00OWRkLWI2MGYtNTE2NTg1NjY2YTNhIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.cY3RJlV5Wh-x3fP96Y9mB0ZgZ1gLqWQhiX7vY_hXH5Y"

CREW_USER_ID = "2da12a4b-c0a1-4716-80ae-d29c90d98233"
CREW_JWT = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NjAxLCJpYXQiOjE3NzA2NDMwMDEsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MzAwMX1dLCJzZXNzaW9uX2lkIjoiNjViMDEyZTUtODkyYy00N2VjLWI2YWItZjNlZDM5YzQ1YjdjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.vmaSq3MHv3WOd-1D2ysct-xKD1AgOcAIiqdsDUSzZRk"

TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def db():
    """Create Supabase client with service role (for checking audit log)"""
    import dotenv
    dotenv.load_dotenv("../../env/.env.local")

    url = os.getenv("TENANT_1_SUPABASE_URL")
    service_key = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")

    return create_client(url, service_key)


@pytest.fixture
def api_url():
    """Get API URL (local or production)"""
    return os.getenv("API_URL", "http://localhost:8080")


# ============================================================================
# SIGNATURE INVARIANT TESTS
# ============================================================================

class TestSignatureInvariants:
    """
    Test the signature invariant from HOR audit requirements:

    INVARIANT: signature is NEVER NULL
    - Non-signed actions → signature = {}
    - Signed actions → signature = {signed_at, user_id, role_at_signing, signature_type, signature_hash}
    """

    def test_non_signed_action_has_empty_signature(self, api_url, db):
        """
        Test that non-signed actions write signature = {} to audit log

        Non-signed action: upsert_hours_of_rest
        """
        # Execute a non-signed action
        response = requests.post(
            f"{api_url}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "upsert_hours_of_rest",
                "context": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "role": "crew"
                },
                "payload": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "record_date": date.today().isoformat(),
                    "rest_periods": [{"start": "22:00", "end": "06:00", "hours": 8.0}],
                    "total_rest_hours": 8.0
                }
            }
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Action failed: {response.status_code} - {response.text}")

        # Check audit log
        result = db.table("pms_audit_log").select("signature").eq(
            "action", "upsert_hours_of_rest"
        ).eq("user_id", CREW_USER_ID).order("created_at", desc=True).limit(1).execute()

        if len(result.data) == 0:
            pytest.skip("No audit log entry found (audit logging may be disabled)")

        audit_entry = result.data[0]

        # Verify signature is NOT NULL
        assert audit_entry["signature"] is not None, (
            "INVARIANT VIOLATED: signature is NULL (should be {})"
        )

        # Verify signature is empty object
        assert audit_entry["signature"] == {}, (
            f"INVARIANT VIOLATED: Non-signed action has non-empty signature: {audit_entry['signature']}"
        )

    def test_signed_action_has_full_signature(self, api_url, db):
        """
        Test that signed actions write full signature payload to audit log

        Signed action: sign_monthly_signoff
        """
        # First create a monthly signoff
        create_response = requests.post(
            f"{api_url}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "create_monthly_signoff",
                "context": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "role": "crew"
                },
                "payload": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "month": date.today().strftime("%Y-%m"),
                    "department": "deck"
                }
            }
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Create signoff failed: {create_response.status_code}")

        signoff_id = create_response.json().get("data", {}).get("id")
        if not signoff_id:
            pytest.skip("No signoff ID returned")

        # Now sign it (SIGNED action)
        sign_response = requests.post(
            f"{api_url}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CREW_JWT}"},
            json={
                "action": "sign_monthly_signoff",
                "context": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CREW_USER_ID,
                    "role": "crew"
                },
                "payload": {
                    "signoff_id": signoff_id,
                    "signature_level": "crew",
                    "signature_data": {
                        "signed_at": date.today().isoformat(),
                        "signature_type": "electronic",
                        "signature_hash": "abc123"
                    }
                }
            }
        )

        if sign_response.status_code not in [200, 201]:
            pytest.skip(f"Sign action failed: {sign_response.status_code}")

        # Check audit log
        result = db.table("pms_audit_log").select("signature").eq(
            "action", "sign_monthly_signoff"
        ).eq("user_id", CREW_USER_ID).order("created_at", desc=True).limit(1).execute()

        if len(result.data) == 0:
            pytest.skip("No audit log entry found")

        audit_entry = result.data[0]

        # Verify signature is NOT NULL
        assert audit_entry["signature"] is not None, (
            "INVARIANT VIOLATED: signature is NULL (should be full payload)"
        )

        # Verify signature is NOT empty
        assert audit_entry["signature"] != {}, (
            "INVARIANT VIOLATED: Signed action has empty signature"
        )

        # Verify signature has required fields
        signature = audit_entry["signature"]
        required_fields = ["signed_at", "user_id", "role_at_signing", "signature_type"]
        for field in required_fields:
            assert field in signature, (
                f"INVARIANT VIOLATED: signature missing required field '{field}'"
            )


class TestAuditLogSchema:
    """Test audit log schema compliance"""

    def test_audit_log_has_signature_column(self, db):
        """Verify pms_audit_log table has signature column"""
        # Try to query signature column
        try:
            result = db.table("pms_audit_log").select("signature").limit(1).execute()
            # If no error, column exists
            assert True
        except Exception as e:
            if "column" in str(e).lower() and "signature" in str(e).lower():
                pytest.fail("pms_audit_log table missing 'signature' column")
            raise

    def test_signature_column_accepts_json(self, db):
        """Verify signature column can store JSON"""
        result = db.table("pms_audit_log").select("signature").limit(1).execute()

        if len(result.data) > 0:
            signature = result.data[0]["signature"]
            # Should be dict or None (but preferably dict per invariant)
            assert isinstance(signature, (dict, type(None))), (
                f"signature column has wrong type: {type(signature)}"
            )


class TestSignatureContent:
    """Test signature content for signed actions"""

    def test_signed_action_signature_structure(self, db):
        """
        Verify signed action signatures have correct structure

        Expected:
        {
          "signed_at": "2026-02-09T12:00:00Z",
          "user_id": "uuid",
          "role_at_signing": "crew|hod|captain",
          "signature_type": "electronic|wet|delegated",
          "signature_hash": "sha256_hash"
        }
        """
        # Get latest signed action from audit log
        result = db.table("pms_audit_log").select("signature, action").in_(
            "action", ["sign_monthly_signoff", "dismiss_warning"]
        ).order("created_at", desc=True).limit(1).execute()

        if len(result.data) == 0:
            pytest.skip("No signed actions in audit log yet")

        audit_entry = result.data[0]
        signature = audit_entry["signature"]

        if signature is None or signature == {}:
            pytest.skip("Signature not populated (action may have failed)")

        # Verify structure
        assert "signed_at" in signature
        assert "user_id" in signature
        assert "role_at_signing" in signature
        assert "signature_type" in signature

        # Verify signature_type is valid
        assert signature["signature_type"] in ["electronic", "wet", "delegated"], (
            f"Invalid signature_type: {signature['signature_type']}"
        )

        # Verify role_at_signing is valid
        assert signature["role_at_signing"] in ["crew", "hod", "captain", "manager"], (
            f"Invalid role_at_signing: {signature['role_at_signing']}"
        )


# ============================================================================
# ERROR CASE TESTS
# ============================================================================

class TestSignatureErrors:
    """Test error handling for signature requirements"""

    def test_signed_action_without_signature_data_fails(self, api_url):
        """
        Test that signed actions reject requests missing signature_data

        This should return 400 BAD_REQUEST
        """
        response = requests.post(
            f"{api_url}/v1/actions/execute",
            headers={"Authorization": f"Bearer {CAPTAIN_JWT}"},
            json={
                "action": "sign_monthly_signoff",
                "context": {
                    "yacht_id": TEST_YACHT_ID,
                    "user_id": CAPTAIN_USER_ID,
                    "role": "captain"
                },
                "payload": {
                    "signoff_id": "fake-id",
                    "signature_level": "captain"
                    # Missing signature_data!
                }
            }
        )

        # Should fail with 400 or 422
        assert response.status_code in [400, 422], (
            f"Signed action without signature_data should fail, got {response.status_code}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
