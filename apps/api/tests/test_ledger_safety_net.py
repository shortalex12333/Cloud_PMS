"""
Phase B — Ledger Safety Net Integration Test
=============================================

Verifies that when an adapter action (going through internal_adapter.py) completes
successfully without a handler-level ledger write, the dispatcher-level safety net
writes a generic ledger_events row.

Also verifies that Phase A handlers (which set _ledger_written: True) do NOT trigger
the safety net a second time.

LAW 17: in-memory via httpx.AsyncClient. DB and INTERNAL_HANDLERS mocked.
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
import httpx
from unittest.mock import MagicMock, AsyncMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_service import app
from middleware.auth import get_authenticated_user

# ── Constants ─────────────────────────────────────────────────────────────────

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

_AUTH = {
    "user_id": USER_ID,
    "email": "test@yacht.test",
    "yacht_id": YACHT_ID,
    "org_id": YACHT_ID,
    "tenant_key_alias": "y85fe111",
    "role": "chief_engineer",
    "vessel_ids": [YACHT_ID],
    "is_fleet_user": False,
}

# Payload for an adapter action that exists in ACTION_METADATA
# Using "archive_fault" (event_type=update, entity_type=fault, entity_id_field=fault_id)
ARCHIVE_FAULT_PAYLOAD = {
    "action": "archive_fault",
    "payload": {"fault_id": str(uuid.uuid4())},
    "context": {"yacht_id": YACHT_ID},
}


def _make_mock_db(insert_success=True):
    """Mock DB client that records calls to ledger_events.insert."""
    db = MagicMock()

    # Default chain for any table/select/eq chain
    chain = MagicMock()
    r = MagicMock()
    r.data = [{"id": str(uuid.uuid4())}]
    chain.execute.return_value = r
    chain.eq.return_value = chain
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.upsert.return_value = chain

    db.table.return_value = chain
    return db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def auth_client():
    async def _mock_auth():
        return _AUTH

    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=15.0) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safety_net_fires_for_adapter_action(auth_client):
    """
    When an adapter action returns success without _ledger_written,
    the dispatcher safety net should insert a row into ledger_events.
    """
    mock_db = _make_mock_db()
    ledger_insert_calls = []

    # Track calls to ledger_events specifically
    original_table = mock_db.table.side_effect

    def _track_table(table_name):
        tbl = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"id": "ok"}])
        chain.eq.return_value = chain
        chain.insert.return_value = chain

        if table_name == "ledger_events":
            def _track_insert(data):
                ledger_insert_calls.append(data)
                return chain
            chain.insert.side_effect = _track_insert

        tbl.select.return_value = chain
        tbl.insert.return_value = chain
        tbl.update.return_value = chain
        return tbl

    mock_db.table.side_effect = _track_table

    # The adapter action calls INTERNAL_HANDLERS["archive_fault"] → must return success
    async def _mock_archive_fault(params):
        return {"status": "success", "message": "Fault archived"}
        # Note: no _ledger_written key — safety net should fire

    with patch("routes.p0_actions_routes.get_tenant_supabase_client", return_value=mock_db), \
         patch("action_router.dispatchers.internal_dispatcher.INTERNAL_HANDLERS",
               {"archive_fault": _mock_archive_fault}):
        resp = await auth_client.post("/v1/actions/execute", json=ARCHIVE_FAULT_PAYLOAD)

    # The action itself should succeed (200 or at least not 500)
    assert resp.status_code in (200, 400), f"Unexpected status: {resp.status_code} — {resp.text}"

    # Safety net must have written to ledger_events
    assert len(ledger_insert_calls) >= 1, (
        "Safety net did not write to ledger_events — _ledger_written flag not working"
    )
    written = ledger_insert_calls[0]
    assert written.get("action") == "archive_fault"
    assert written.get("entity_type") == "fault"
    assert written.get("event_type") == "update"
    assert written.get("yacht_id") == YACHT_ID


@pytest.mark.asyncio
async def test_safety_net_skips_when_ledger_written_set(auth_client):
    """
    When a handler sets _ledger_written: True, the safety net must NOT
    write a second entry to ledger_events.
    """
    mock_db = _make_mock_db()
    ledger_insert_calls = []

    def _track_table(table_name):
        tbl = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"id": "ok"}])
        chain.eq.return_value = chain

        if table_name == "ledger_events":
            def _track_insert(data):
                ledger_insert_calls.append(data)
                return chain
            chain.insert.side_effect = _track_insert
        else:
            chain.insert.return_value = chain

        tbl.select.return_value = chain
        tbl.insert.return_value = chain
        tbl.update.return_value = chain
        return tbl

    mock_db.table.side_effect = _track_table

    # Handler already writes ledger and sets the flag
    async def _mock_handler_with_flag(params):
        return {"status": "success", "message": "Done", "_ledger_written": True}

    with patch("routes.p0_actions_routes.get_tenant_supabase_client", return_value=mock_db), \
         patch("action_router.dispatchers.internal_dispatcher.INTERNAL_HANDLERS",
               {"archive_fault": _mock_handler_with_flag}):
        resp = await auth_client.post("/v1/actions/execute", json=ARCHIVE_FAULT_PAYLOAD)

    assert resp.status_code in (200, 400)
    # Safety net must NOT have added an extra entry (handler already wrote one if it wanted)
    safety_net_writes = [c for c in ledger_insert_calls if c.get("action") == "archive_fault"]
    assert len(safety_net_writes) == 0, (
        f"Safety net fired despite _ledger_written=True: {safety_net_writes}"
    )
