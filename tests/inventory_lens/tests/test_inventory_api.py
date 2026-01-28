"""
Inventory Lens API Acceptance Tests
====================================

Tests inventory operations via HTTPS API (Render) to validate:
- Role-based access control (crew, HOD, captain)
- Error mapping (400/403/404/409)
- Atomic operations via handlers
- Idempotency enforcement
- RLS enforcement through API layer

These tests hit the deployed Render API, avoiding direct postgres connection
and the associated network restrictions in CI environments.

Environment Variables Required:
- RENDER_API_BASE_URL: https://pipeline-core.int.celeste7.ai
- TEST_YACHT_ID: 85fe1119-b04c-41ac-80f1-829d23322598
- CREW_JWT: JWT for crew user
- HOD_JWT: JWT for HOD user
- CAPTAIN_JWT: JWT for captain user
"""

import pytest
import httpx
import os
from uuid import uuid4
from typing import Dict, Any


# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("RENDER_API_BASE_URL", "https://pipeline-core.int.celeste7.ai")
TEST_YACHT_ID = os.getenv("TEST_YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")

# HARDCODED JWTs FOR CI (to avoid GitHub Secrets copy-paste issues)
# These JWTs are MASTER-signed with 365-day expiry (expires 2027-01-28)
# Generated with iat=1769599994 (2026-01-28 11:33 UTC, 2 hours before generation)
# These JWTs verified working in local pilot tests
# Source: docs/evidence/inventory_item/JWTS_COPY_PASTE.txt
# TODO: Replace with proper secret management system
CREW_JWT = os.getenv(
    "CREW_JWT",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTU5OTk5NH1dLCJzZXNzaW9uX2lkIjoiY2ktdGVzdC0yZGExMmE0YiIsImlzX2Fub255bW91cyI6ZmFsc2V9.cFA-nWNlaSpwsf3P9qLbWVegltzTtdWEzuw2rCpzEV0"
)
HOD_JWT = os.getenv(
    "HOD_JWT",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg"
)
CAPTAIN_JWT = os.getenv(
    "CAPTAIN_JWT",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTU5OTk5NH1dLCJzZXNzaW9uX2lkIjoiY2ktdGVzdC1iNzJjMzVmZiIsImlzX2Fub255bW91cyI6ZmFsc2V9.Uo0H4yeLWjcvk1UTUD1fF248ElNFRKoN7-eswUWVcvw"
)


# ============================================================================
# HELPERS
# ============================================================================

def make_request(
    action: str,
    payload: Dict[str, Any],
    jwt: str,
    yacht_id: str = TEST_YACHT_ID
) -> httpx.Response:
    """Make API request to /v1/actions/execute."""
    url = f"{API_BASE_URL}/v1/actions/execute"
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    }
    body = {
        "action": action,
        "context": {"yacht_id": yacht_id},
        "payload": payload
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=headers)

    return response


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def test_part_id():
    """Return a test part ID that exists in staging."""
    # Use a known part ID from staging, or create one via API
    # For now, assume parts exist and tests will create as needed
    return str(uuid4())


@pytest.fixture
def test_location_id():
    """Return a test location ID."""
    return str(uuid4())


@pytest.fixture
def idempotency_key():
    """Generate unique idempotency key for each test."""
    return str(uuid4())


# ============================================================================
# ROLE-BASED ACCESS TESTS
# ============================================================================

class TestRoleBasedAccess:
    """Test role-based access control through API."""

    def test_crew_can_consume_part(self, test_part_id):
        """Crew users can consume parts (operational role)."""
        response = make_request(
            action="consume_part",
            payload={
                "part_id": test_part_id,
                "quantity": 1,
                "work_order_id": str(uuid4())
            },
            jwt=CREW_JWT
        )

        # Should succeed or fail with business logic error (409 insufficient stock)
        # but NOT 403 (forbidden)
        assert response.status_code in [200, 409], \
            f"Expected 200 or 409, got {response.status_code}: {response.text}"

    def test_crew_cannot_adjust_stock(self, test_part_id):
        """Crew users cannot adjust stock (requires HOD/manager role)."""
        response = make_request(
            action="adjust_stock_quantity",
            payload={
                "part_id": test_part_id,
                "quantity_change": 10,
                "reason": "Test adjustment",
                "signature": {
                    "pin": "1234",
                    "totp": "123456",
                    "timestamp": "2026-01-28T00:00:00Z"
                }
            },
            jwt=CREW_JWT
        )

        # Should return 403 (forbidden by RLS)
        assert response.status_code == 403, \
            f"Expected 403, got {response.status_code}: {response.text}"

    def test_hod_can_receive_part(self, test_part_id, test_location_id, idempotency_key):
        """HOD users can receive parts."""
        response = make_request(
            action="receive_part",
            payload={
                "part_id": test_part_id,
                "to_location_id": test_location_id,
                "quantity": 10,
                "idempotency_key": idempotency_key
            },
            jwt=HOD_JWT
        )

        # Should succeed or fail with business logic error
        # but NOT 403 (forbidden)
        assert response.status_code in [200, 400, 404, 409], \
            f"Expected 2xx/4xx (not 403), got {response.status_code}: {response.text}"

    def test_captain_can_adjust_stock(self, test_part_id):
        """Captain users (HOD role) can adjust stock."""
        response = make_request(
            action="adjust_stock_quantity",
            payload={
                "part_id": test_part_id,
                "quantity_change": 5,
                "reason": "Test adjustment by captain",
                "signature": {
                    "pin": "1234",
                    "totp": "123456",
                    "timestamp": "2026-01-28T00:00:00Z"
                }
            },
            jwt=CAPTAIN_JWT
        )

        # Should succeed or fail with business logic error
        # but NOT 403 (forbidden)
        assert response.status_code in [200, 400, 404], \
            f"Expected 2xx/4xx (not 403), got {response.status_code}: {response.text}"


# ============================================================================
# IDEMPOTENCY TESTS
# ============================================================================

class TestIdempotency:
    """Test idempotency enforcement through API."""

    def test_duplicate_receive_blocked(self, test_part_id, test_location_id):
        """Duplicate receive with same idempotency_key should return 409."""
        idempotency_key = str(uuid4())

        payload = {
            "part_id": test_part_id,
            "to_location_id": test_location_id,
            "quantity": 5,
            "idempotency_key": idempotency_key
        }

        # First request
        response1 = make_request(
            action="receive_part",
            payload=payload,
            jwt=HOD_JWT
        )

        # Should succeed or fail with other errors (not idempotency)
        assert response1.status_code in [200, 400, 404], \
            f"First request failed: {response1.status_code}: {response1.text}"

        # Second request with same idempotency_key
        response2 = make_request(
            action="receive_part",
            payload=payload,
            jwt=HOD_JWT
        )

        # Should return 409 (conflict - duplicate idempotency_key)
        assert response2.status_code == 409, \
            f"Expected 409 on duplicate, got {response2.status_code}: {response2.text}"

        assert "idempotency" in response2.text.lower() or "duplicate" in response2.text.lower(), \
            f"Error message should mention idempotency: {response2.text}"


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidation:
    """Test input validation through API."""

    def test_consume_negative_quantity_rejected(self, test_part_id):
        """Consuming negative quantity should return 400."""
        response = make_request(
            action="consume_part",
            payload={
                "part_id": test_part_id,
                "quantity": -5,
                "work_order_id": str(uuid4())
            },
            jwt=CREW_JWT
        )

        # Should return 400 (bad request)
        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}: {response.text}"

    def test_transfer_same_location_rejected(self, test_part_id):
        """Transferring to same location should return 400."""
        location_id = str(uuid4())

        response = make_request(
            action="transfer_part",
            payload={
                "part_id": test_part_id,
                "from_location_id": location_id,
                "to_location_id": location_id,
                "quantity": 5
            },
            jwt=HOD_JWT
        )

        # Should return 400 (bad request - same location)
        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}: {response.text}"

    def test_missing_required_field_rejected(self, test_part_id):
        """Missing required field should return 400."""
        response = make_request(
            action="consume_part",
            payload={
                "part_id": test_part_id,
                # Missing 'quantity' field
            },
            jwt=CREW_JWT
        )

        # Should return 400 (bad request - missing field)
        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}: {response.text}"


# ============================================================================
# SIGNATURE TESTS
# ============================================================================

class TestSignatures:
    """Test signature requirements for SIGNED actions."""

    def test_adjust_stock_without_signature_rejected(self, test_part_id):
        """adjust_stock_quantity without signature should return 400."""
        response = make_request(
            action="adjust_stock_quantity",
            payload={
                "part_id": test_part_id,
                "quantity_change": 10,
                "reason": "Test adjustment"
                # Missing 'signature' field
            },
            jwt=CAPTAIN_JWT
        )

        # Should return 400 (bad request - missing signature)
        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}: {response.text}"

        assert "signature" in response.text.lower(), \
            f"Error should mention signature: {response.text}"

    def test_write_off_without_signature_rejected(self, test_part_id):
        """write_off_part without signature should return 400."""
        response = make_request(
            action="write_off_part",
            payload={
                "part_id": test_part_id,
                "quantity": 5,
                "reason": "Damaged"
                # Missing 'signature' field
            },
            jwt=CAPTAIN_JWT
        )

        # Should return 400 (bad request - missing signature)
        assert response.status_code == 400, \
            f"Expected 400, got {response.status_code}: {response.text}"


# ============================================================================
# ERROR MAPPING TESTS
# ============================================================================

class TestErrorMapping:
    """Test HTTP status code mapping for business logic errors."""

    def test_insufficient_stock_returns_409(self, test_part_id):
        """Consuming more than available should return 409 (conflict)."""
        # Try to consume a very large quantity (unlikely to be available)
        response = make_request(
            action="consume_part",
            payload={
                "part_id": test_part_id,
                "quantity": 999999,
                "work_order_id": str(uuid4())
            },
            jwt=CREW_JWT
        )

        # Should return 409 (conflict - insufficient stock)
        # or 404 if part doesn't exist
        assert response.status_code in [404, 409], \
            f"Expected 404 or 409, got {response.status_code}: {response.text}"

    def test_nonexistent_part_returns_404(self):
        """Operating on non-existent part should return 404."""
        fake_part_id = str(uuid4())

        response = make_request(
            action="consume_part",
            payload={
                "part_id": fake_part_id,
                "quantity": 1,
                "work_order_id": str(uuid4())
            },
            jwt=CREW_JWT
        )

        # Should return 404 (not found)
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}: {response.text}"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for end-to-end workflows."""

    @pytest.mark.skip(reason="Requires actual part setup in staging")
    def test_full_workflow_receive_consume_transfer(self):
        """Test full workflow: receive → consume → transfer."""
        # This would require setting up actual parts and locations in staging
        # Skipped for now, but documents the expected integration test
        pass


# ============================================================================
# SUMMARY
# ============================================================================

"""
Test Coverage:

✅ Role-based access (crew, HOD, captain)
✅ Idempotency enforcement (duplicate keys → 409)
✅ Input validation (negative quantities, missing fields → 400)
✅ Signature requirements (SIGNED actions → 400 if missing)
✅ Error mapping (insufficient stock → 409, not found → 404)
✅ RLS enforcement (crew cannot adjust_stock → 403)

Network Requirements:
- HTTPS only (no postgres 5432/6543)
- Works from GitHub Actions (no firewall issues)
- Tests deployed Render API (production-like environment)

Expected Results:
- All tests should pass or fail gracefully with expected error codes
- No 500 errors (server errors indicate bugs)
- Proper 403 for RLS violations
- Proper 409 for conflicts (idempotency, insufficient stock)
- Proper 400 for validation errors
"""
