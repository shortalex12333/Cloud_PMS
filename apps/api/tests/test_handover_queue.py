"""
GET /v1/handover/queue — Integration Tests
==========================================

Tests the aggregated handover candidates endpoint.

Three test groups:
  200 happy path   — all 5 sections return arrays (never null)
  200 partial      — ?include[]=faults returns only faults, others empty
  401 unauthed     — no token → 401

LAW 17: in-memory via httpx.AsyncClient, DB mocked via patch.
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
import httpx
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_service import app
from middleware.auth import get_authenticated_user

# ── Constants ─────────────────────────────────────────────────────────────────

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

_AUTH = {
    "user_id": USER_ID,
    "email": "test@yacht.test",
    "yacht_id": YACHT_ID,
    "org_id": YACHT_ID,
    "tenant_key_alias": "y85fe111",
    "role": "chief_engineer",
    "vessel_ids": [YACHT_ID],
    "is_fleet_user": False,
    "yacht_name": "M/Y Test",
}

FAULT_ROW = {
    "id": str(uuid.uuid4()),
    "title": "Main engine oil leak",
    "severity": "high",
    "equipment_name": "Main Engine",
    "created_at": "2026-04-01T10:00:00+00:00",
}

WO_ROW = {
    "id": str(uuid.uuid4()),
    "title": "Replace fuel filter",
    "priority": "high",
    "due_at": "2026-03-01T00:00:00+00:00",
    "assigned_to": USER_ID,
}

PART_ROW_LOW = {
    "id": str(uuid.uuid4()),
    "name": "Oil Filter",
    "quantity_on_hand": 0,
    "minimum_quantity": 2,
}

PART_ROW_OK = {
    "id": str(uuid.uuid4()),
    "name": "Fuel Filter",
    "quantity_on_hand": 5,
    "minimum_quantity": 1,
}

ORDER_ROW = {
    "id": str(uuid.uuid4()),
    "po_number": "PO-2026-001",
    "status": "pending",
    "created_at": "2026-04-02T08:00:00+00:00",
}

QUEUED_ROW = {
    "id": str(uuid.uuid4()),
    "entity_type": "fault",
    "entity_id": str(uuid.uuid4()),
    "summary": "Fuel leak reported by deckhand",
    "priority": "high",
}


def _build_db_mock(
    faults=None, work_orders=None, parts=None, orders=None, queued=None
):
    """Build a Supabase mock that returns configured data per table."""
    m = MagicMock()

    def _chain(data):
        c = MagicMock()
        r = MagicMock()
        r.data = data if data is not None else []
        # All filter/order chains ultimately return the same result
        c.execute.return_value = r
        c.eq.return_value = c
        c.neq.return_value = c
        c.lt.return_value = c
        c.in_.return_value = c
        c.not_ = c
        c.order.return_value = c
        c.limit.return_value = c
        return c

    def _select(table_name):
        tbl = MagicMock()
        if "fault" in table_name:
            tbl.select.return_value = _chain(faults if faults is not None else [])
        elif "work_order" in table_name:
            tbl.select.return_value = _chain(work_orders if work_orders is not None else [])
        elif "pms_parts" in table_name:
            tbl.select.return_value = _chain(parts if parts is not None else [])
        elif "purchase_order" in table_name:
            tbl.select.return_value = _chain(orders if orders is not None else [])
        elif "handover_items" in table_name:
            tbl.select.return_value = _chain(queued if queued is not None else [])
        else:
            tbl.select.return_value = _chain([])
        return tbl

    m.table.side_effect = _select
    return m


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    """Unauthenticated client."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c


@pytest_asyncio.fixture
async def auth_client():
    """Authenticated client with mocked auth."""
    async def _mock_auth():
        return _AUTH

    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handover_queue_200_all_sections(auth_client):
    """Happy path: all 5 sections return arrays with correct shape."""
    db = _build_db_mock(
        faults=[FAULT_ROW],
        work_orders=[WO_ROW],
        parts=[PART_ROW_LOW, PART_ROW_OK],
        orders=[ORDER_ROW],
        queued=[QUEUED_ROW],
    )
    with patch("routes.p0_actions_routes.get_tenant_supabase_client", return_value=db):
        resp = await auth_client.get("/v1/handover/queue")

    assert resp.status_code == 200
    body = resp.json()

    # All sections present and are lists
    assert isinstance(body["open_faults"], list)
    assert isinstance(body["overdue_work_orders"], list)
    assert isinstance(body["low_stock_parts"], list)
    assert isinstance(body["pending_orders"], list)
    assert isinstance(body["already_queued"], list)
    assert isinstance(body["counts"], dict)

    # Correct data returned
    assert len(body["open_faults"]) == 1
    assert body["open_faults"][0]["title"] == "Main engine oil leak"

    assert len(body["overdue_work_orders"]) == 1
    assert body["overdue_work_orders"][0]["priority"] == "high"

    # Only the low-stock part returned (qty 0 <= min 2), not the ok one (qty 5 > min 1)
    assert len(body["low_stock_parts"]) == 1
    assert body["low_stock_parts"][0]["current_qty"] == 0

    assert len(body["pending_orders"]) == 1
    assert body["pending_orders"][0]["title"] == "PO-2026-001"

    assert len(body["already_queued"]) == 1
    assert body["already_queued"][0]["entity_type"] == "fault"

    # counts matches lengths
    assert body["counts"]["faults"] == 1
    assert body["counts"]["work_orders"] == 1
    assert body["counts"]["parts"] == 1
    assert body["counts"]["orders"] == 1
    assert body["counts"]["already_queued"] == 1


@pytest.mark.asyncio
async def test_handover_queue_200_empty_arrays_not_null(auth_client):
    """When tables return no rows, response is empty arrays — never null/None."""
    db = _build_db_mock()  # all empty
    with patch("routes.p0_actions_routes.get_tenant_supabase_client", return_value=db):
        resp = await auth_client.get("/v1/handover/queue")

    assert resp.status_code == 200
    body = resp.json()
    assert body["open_faults"] == []
    assert body["overdue_work_orders"] == []
    assert body["low_stock_parts"] == []
    assert body["pending_orders"] == []
    assert body["already_queued"] == []
    assert body["counts"] == {
        "faults": 0, "work_orders": 0, "parts": 0, "orders": 0, "already_queued": 0
    }


@pytest.mark.asyncio
async def test_handover_queue_200_include_filter(auth_client):
    """?include[]=faults should return only faults; other sections empty."""
    db = _build_db_mock(faults=[FAULT_ROW], work_orders=[WO_ROW])
    with patch("routes.p0_actions_routes.get_tenant_supabase_client", return_value=db):
        resp = await auth_client.get("/v1/handover/queue?include=faults")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["open_faults"]) == 1
    assert body["overdue_work_orders"] == []
    assert body["low_stock_parts"] == []
    assert body["pending_orders"] == []
    assert body["already_queued"] == []


@pytest.mark.asyncio
async def test_handover_queue_401_no_token(client):
    """No token → 401 from get_authenticated_user."""
    resp = await client.get("/v1/handover/queue")
    assert resp.status_code == 401
