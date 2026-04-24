# apps/api/tests/test_close_work_order_bridge.py
"""
Unit tests for close_work_order → fault bookkeeping (PR-WO-6 + PR-WO-6b).

Correction (2026-04-24): the DB trigger `trg_wo_status_cascade_to_fault`
owns the pms_faults.status / resolved_at / resolved_by cascade. This handler
no longer duplicates those writes. What it DOES own:
    1. Setting pms_faults.work_order_id = wo_id (reverse-link; the trigger
       doesn't touch that column).
    2. Emitting a `fault_auto_resolved` ledger_events row (the trigger
       doesn't emit ledger).

Tests cover:
    * WO with no fault_id → no fault writes, no ledger emission.
    * WO with fault_id + fault in terminal state (resolved/closed) → no
      reverse-link, no ledger (idempotent).
    * WO with fault_id + non-terminal fault → reverse-link write + single
      ledger insert. Does NOT write pms_faults.status or resolved_at.
    * Reverse-link write fails → ledger still emitted (best-effort).
    * Ledger insert fails → bridge still succeeds (best-effort); WO close
      returns fault_auto_resolved=True.
    * WO update returns empty → ValueError, bridge never runs.
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


class _Query:
    """Fluent query stub that records operations and returns canned data."""

    def __init__(self, parent, table_name):
        self.parent = parent
        self.table_name = table_name
        self._filters = []
        self._op = None
        self._payload = None

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
        raise_key = (self.table_name, self._op)
        if self.parent.raise_on.get(raise_key):
            err = self.parent.raise_on[raise_key]
            self.parent.raise_on[raise_key] = None
            raise err

        canned_key = (self.table_name, self._op)
        canned = self.parent.canned.get(canned_key, {"data": [], "count": 0})
        return MagicMock(data=canned["data"], count=canned["count"])


class FakeClient:
    def __init__(self):
        self.calls = []
        self.canned = {}
        self.raise_on = {}

    def table(self, name):
        return _Query(self, name)


def _import_close_handler():
    from action_router.dispatchers.internal_dispatcher import close_work_order
    return close_work_order


def _base_canned(wo_fault_id=None, fault_status="open"):
    return {
        ("pms_work_orders", "select"): {
            "data": [{"id": WO, "fault_id": wo_fault_id}], "count": 1,
        },
        ("pms_faults", "select"): {
            "data": [{"id": FAULT, "status": fault_status, "work_order_id": None}],
            "count": 1,
        },
        ("pms_work_orders", "update"): {
            "data": [{"id": WO, "status": "completed", "completed_at": "2026-04-24T12:00:00"}],
            "count": 1,
        },
        ("pms_faults", "update"): {
            "data": [{"id": FAULT, "work_order_id": WO}], "count": 1,
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
async def test_wo_with_no_fault_id_skips_all_fault_bookkeeping():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=None)
    out = await _invoke(client)

    assert out["fault_auto_resolved"] is False
    assert out["linked_fault_id"] is None
    tables = [c["table"] for c in client.calls]
    assert "pms_faults" not in tables
    assert "ledger_events" not in tables


@pytest.mark.asyncio
async def test_wo_with_open_fault_writes_reverse_link_and_ledger():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT, fault_status="open")
    out = await _invoke(client)

    assert out["fault_auto_resolved"] is True
    assert out["linked_fault_id"] == FAULT

    # Correct semantics: this handler writes ONLY the reverse-link;
    # trg_wo_status_cascade_to_fault owns status/resolved_at/resolved_by.
    fault_updates = [
        c for c in client.calls
        if c["table"] == "pms_faults" and c["op"] == "update"
    ]
    assert len(fault_updates) == 1
    payload = fault_updates[0]["payload"]
    assert payload == {"work_order_id": WO}, (
        "handler must write ONLY work_order_id; the DB trigger owns status "
        "and resolved_* writes"
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
    assert ev["metadata"]["work_order_id"] == WO
    assert ev["metadata"]["previous_status"] == "open"


@pytest.mark.asyncio
async def test_fault_already_terminal_does_not_re_write_or_ledger():
    for terminal in ("resolved", "closed"):
        client = FakeClient()
        client.canned = _base_canned(wo_fault_id=FAULT, fault_status=terminal)
        out = await _invoke(client)

        assert out["fault_auto_resolved"] is False, terminal
        fault_updates = [
            c for c in client.calls
            if c["table"] == "pms_faults" and c["op"] == "update"
        ]
        assert fault_updates == []
        ledger_inserts = [
            c for c in client.calls
            if c["table"] == "ledger_events" and c["op"] == "insert"
        ]
        assert ledger_inserts == []


@pytest.mark.asyncio
async def test_reverse_link_write_failure_does_not_prevent_ledger():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT, fault_status="investigating")
    client.raise_on[("pms_faults", "update")] = Exception(
        "simulated RLS or transient DB error on reverse-link write"
    )

    out = await _invoke(client)
    assert out["fault_auto_resolved"] is True
    assert any(
        c["table"] == "ledger_events" and c["op"] == "insert"
        for c in client.calls
    ), "ledger emission must survive reverse-link failure"


@pytest.mark.asyncio
async def test_ledger_failure_does_not_fail_the_wo_close():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT, fault_status="work_ordered")
    client.raise_on[("ledger_events", "insert")] = Exception("ledger RLS denied")

    # Must not raise; response envelope still populated.
    out = await _invoke(client)
    assert out["fault_auto_resolved"] is True
    assert out["linked_fault_id"] == FAULT


@pytest.mark.asyncio
async def test_wo_not_found_raises_before_bookkeeping_runs():
    client = FakeClient()
    client.canned = _base_canned(wo_fault_id=FAULT)
    client.canned[("pms_work_orders", "update")] = {"data": [], "count": 0}

    with pytest.raises(ValueError, match="not found"):
        await _invoke(client)

    # No writes on the fault side, no ledger row.
    fault_updates = [
        c for c in client.calls
        if c["table"] == "pms_faults" and c["op"] == "update"
    ]
    assert fault_updates == []
    ledger_inserts = [
        c for c in client.calls
        if c["table"] == "ledger_events" and c["op"] == "insert"
    ]
    assert ledger_inserts == []
