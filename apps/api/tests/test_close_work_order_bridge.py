# apps/api/tests/test_close_work_order_bridge.py
"""
Unit tests for the close_work_order → fault auto-resolve bridge (PR-WO-6).

Verifies:
    * WO with no fault_id → no fault mutation, no ledger emission.
    * WO with fault_id + fault already resolved → no re-write (idempotent).
    * WO with fault_id + fault open → fault.status='resolved' + ledger row +
      resolved_by_work_order_id FK written.
    * FK write fails (column missing) → retries without FK, bridge still
      transitions fault status and emits ledger.
    * Bridge exceptions never fail the WO close.

All supabase-py interactions are mocked via a fake client that records calls.
No DB, no network.
"""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


YACHT = "yacht-uuid-1"
USER = "user-uuid-1"
WO = "wo-uuid-1"
FAULT = "fault-uuid-1"


# ── Fake supabase client ───────────────────────────────────────────────────


class _Query:
    """Fluent query stub that records operations and returns canned data."""

    def __init__(self, parent, table_name):
        self.parent = parent
        self.table_name = table_name
        self._filters = []
        self._op = None
        self._payload = None

    # chainable filter methods (all no-ops recording filter state)
    def select(self, _cols):
        self._op = "select"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, k, v):
        self._filters.append(("eq", k, v))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        self.parent.calls.append({
            "table": self.table_name,
            "op": self._op,
            "payload": self._payload,
            "filters": tuple(self._filters),
        })
        if self._op == "update" and self.parent.update_raises_on.get(self.table_name):
            err = self.parent.update_raises_on[self.table_name]
            # Raise only the first time — mimic "column does not exist"
            self.parent.update_raises_on[self.table_name] = None
            raise err

        canned_key = (self.table_name, self._op)
        canned = self.parent.canned.get(canned_key, {"data": [], "count": 0})
        return MagicMock(data=canned["data"], count=canned["count"])


class FakeClient:
    def __init__(self):
        self.calls = []
        self.canned = {}
        self.update_raises_on = {}

    def table(self, name):
        return _Query(self, name)


# ── Test harness ───────────────────────────────────────────────────────────


def _import_close_handler():
    from action_router.dispatchers.internal_dispatcher import close_work_order
    return close_work_order


def _base_canned(wo_fault_id=None, fault_status="open"):
    """Canned responses for: pre-read WO, read fault, update WO."""
    return {
        ("pms_work_orders", "select"): {
            "data": [{"id": WO, "fault_id": wo_fault_id}], "count": 1,
        },
        ("pms_faults", "select"): {
            "data": [{"id": FAULT, "status": fault_status}], "count": 1,
        },
        ("pms_work_orders", "update"): {
            "data": [{"id": WO, "status": "completed", "completed_at": "2026-04-23T21:00:00"}],
            "count": 1,
        },
        ("pms_faults", "update"): {
            "data": [{"id": FAULT, "status": "resolved"}], "count": 1,
        },
        ("ledger_events", "insert"): {"data": [{"id": "ledger-1"}], "count": 1},
    }


async def _invoke(client):
    fn = _import_close_handler()
    with patch(
        "action_router.dispatchers.internal_dispatcher.get_supabase_client",
        return_value=client,
    ):
        return await fn({
            "yacht_id": YACHT,
            "work_order_id": WO,
            "user_id": USER,
        })


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wo_with_no_fault_id_does_not_touch_faults_or_ledger():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=None)
    out = await _invoke(client)

    assert out["fault_auto_resolved"] is False
    assert out["linked_fault_id"] is None
    tables_hit = [c["table"] for c in client.calls]
    assert "pms_faults" not in tables_hit
    assert "ledger_events" not in tables_hit


@pytest.mark.asyncio
async def test_wo_with_open_fault_transitions_and_emits_ledger():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT, fault_status="open")
    out = await _invoke(client)

    assert out["fault_auto_resolved"] is True
    assert out["linked_fault_id"] == FAULT

    fault_updates = [
        c for c in client.calls
        if c["table"] == "pms_faults" and c["op"] == "update"
    ]
    assert len(fault_updates) == 1, "fault should be updated exactly once"
    payload = fault_updates[0]["payload"]
    assert payload["status"] == "resolved"
    assert payload["resolved_by"] == USER
    assert payload["resolved_by_work_order_id"] == WO, (
        "FK write must be present when the column exists"
    )

    ledger_inserts = [
        c for c in client.calls
        if c["table"] == "ledger_events" and c["op"] == "insert"
    ]
    assert len(ledger_inserts) == 1
    ev = ledger_inserts[0]["payload"]
    assert ev["action"] == "fault_auto_resolved"
    assert ev["entity_type"] == "fault"
    assert ev["entity_id"] == FAULT


@pytest.mark.asyncio
async def test_fault_already_resolved_is_not_re_written():
    for terminal in ("resolved", "closed"):
        client = FakeClient()
        client.canned = _base_canned(wo_fault_id=FAULT, fault_status=terminal)
        out = await _invoke(client)

        assert out["fault_auto_resolved"] is False, terminal
        fault_updates = [
            c for c in client.calls
            if c["table"] == "pms_faults" and c["op"] == "update"
        ]
        assert fault_updates == [], f"idempotent on terminal status={terminal}"
        ledger_inserts = [
            c for c in client.calls
            if c["table"] == "ledger_events" and c["op"] == "insert"
        ]
        assert ledger_inserts == [], "no ledger row when fault untouched"


@pytest.mark.asyncio
async def test_fk_column_absent_falls_back_without_fk():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT, fault_status="open")
    # First update on pms_faults raises (simulating missing column); second call succeeds.
    client.update_raises_on["pms_faults"] = Exception(
        'column "resolved_by_work_order_id" of relation "pms_faults" does not exist'
    )

    out = await _invoke(client)

    assert out["fault_auto_resolved"] is True

    fault_updates = [
        c for c in client.calls
        if c["table"] == "pms_faults" and c["op"] == "update"
    ]
    assert len(fault_updates) == 2, "first call with FK raises; retry without FK"
    assert "resolved_by_work_order_id" in fault_updates[0]["payload"]
    assert "resolved_by_work_order_id" not in fault_updates[1]["payload"]
    # Ledger event still emitted
    assert any(c["table"] == "ledger_events" for c in client.calls)


@pytest.mark.asyncio
async def test_wo_not_found_raises_before_bridge_runs():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT)
    client.canned[("pms_work_orders", "update")] = {"data": [], "count": 0}

    with pytest.raises(ValueError, match="not found"):
        await _invoke(client)

    # Bridge must not have fired
    fault_updates = [
        c for c in client.calls
        if c["table"] == "pms_faults" and c["op"] == "update"
    ]
    assert fault_updates == []
