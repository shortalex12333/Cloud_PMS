"""
Regression Test: acknowledge_fault Action

This test ensures the acknowledge_fault action:
1. Returns HTTP 200/201
2. Updates pms_faults.status from 'open' to 'investigating'
3. Requires yacht isolation (fault must belong to user's yacht)

Run: pytest tests/api/test_acknowledge_fault.py -v
"""

import pytest
import os
import requests
from datetime import datetime, timezone
from supabase import create_client

# Test configuration
TENANT_SUPABASE_URL = os.getenv("TENANT_SUPABASE_URL", "https://vzsohavtuotocgrfkfyd.supabase.co")
TENANT_SERVICE_KEY = os.getenv("TENANT_SUPABASE_SERVICE_ROLE_KEY")
API_URL = os.getenv("ACTION_ROUTER_URL", "https://pipeline-core.int.celeste7.ai/v1/actions/execute")

# Test data
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_FAULT_ID = "e2e00002-0002-0002-0002-000000000001"


@pytest.fixture
def supabase_client():
    """Create Supabase client for direct DB verification."""
    if not TENANT_SERVICE_KEY:
        pytest.skip("TENANT_SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY)


@pytest.fixture
def reset_fault_status(supabase_client):
    """Reset fault to 'open' before each test."""
    supabase_client.table("pms_faults").update({
        "status": "open",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", TEST_FAULT_ID).eq("yacht_id", TEST_YACHT_ID).execute()
    yield
    # Cleanup: reset back to open after test
    supabase_client.table("pms_faults").update({
        "status": "open",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", TEST_FAULT_ID).eq("yacht_id", TEST_YACHT_ID).execute()


class TestAcknowledgeFault:
    """Regression tests for acknowledge_fault action."""

    def test_acknowledge_fault_returns_200(self, supabase_client, reset_fault_status):
        """
        REGRESSION: acknowledge_fault must return HTTP 200.

        If this test fails, the backend handler is broken.
        """
        # Get auth token (would normally come from Supabase auth)
        # For regression test, use service key auth
        response = requests.post(
            API_URL,
            json={
                "action": "acknowledge_fault",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {"fault_id": TEST_FAULT_ID}
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TENANT_SERVICE_KEY}"
            }
        )

        # Assert HTTP 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        # Assert success status in response
        data = response.json()
        assert data.get("status") == "success", f"Expected success, got: {data}"

    def test_acknowledge_fault_updates_db_status(self, supabase_client, reset_fault_status):
        """
        REGRESSION: acknowledge_fault must change status to 'investigating'.

        DB proof is required - not just API response.
        """
        # Query status BEFORE
        before = supabase_client.table("pms_faults")\
            .select("status")\
            .eq("id", TEST_FAULT_ID)\
            .eq("yacht_id", TEST_YACHT_ID)\
            .single().execute()

        assert before.data["status"] == "open", "Precondition: fault should be 'open'"

        # Execute action
        response = requests.post(
            API_URL,
            json={
                "action": "acknowledge_fault",
                "context": {"yacht_id": TEST_YACHT_ID},
                "payload": {"fault_id": TEST_FAULT_ID}
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TENANT_SERVICE_KEY}"
            }
        )
        assert response.status_code == 200

        # Query status AFTER
        after = supabase_client.table("pms_faults")\
            .select("status")\
            .eq("id", TEST_FAULT_ID)\
            .eq("yacht_id", TEST_YACHT_ID)\
            .single().execute()

        # Assert status changed
        assert after.data["status"] == "investigating", \
            f"Expected 'investigating', got '{after.data['status']}'"

    def test_acknowledge_fault_requires_yacht_isolation(self, supabase_client):
        """
        REGRESSION: acknowledge_fault must enforce yacht isolation.

        A fault from a different yacht must return 404.
        """
        WRONG_YACHT_ID = "00000000-0000-0000-0000-000000000000"

        response = requests.post(
            API_URL,
            json={
                "action": "acknowledge_fault",
                "context": {"yacht_id": WRONG_YACHT_ID},
                "payload": {"fault_id": TEST_FAULT_ID}
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TENANT_SERVICE_KEY}"
            }
        )

        # Should return 404 (fault not found for this yacht)
        assert response.status_code in [403, 404], \
            f"Expected 403/404 for wrong yacht, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
