"""
Handover `status` column retirement — regression tests (PR #642 follow-up)
===========================================================================

Background
----------
`handover_exports` had two parallel state-tracking columns:
  - `review_status`  — the real state machine (pending_review →
    pending_hod_signature → complete). Written by /submit + /countersign.
  - `status`         — legacy label (pending_outgoing → pending_incoming →
    completed). Historically written by the dual-signature handler path.

PR #642 retired `status` as the state-machine driver. These tests pin the
retirement so it does not silently regress.

Covered
-------
  1. `sign_outgoing` no longer writes `status='pending_incoming'` to
     handover_exports. The outgoing signature fields (outgoing_user_id,
     outgoing_role, outgoing_signed_at, outgoing_comments, signatures) are
     still written.
  2. `get_pending_handovers(role_filter='incoming')` filters on
     `review_status='complete' AND incoming_signed_at IS NULL`, NOT on
     `status='pending_incoming'`.
  3. `get_pending_handovers(role_filter='outgoing')` filters on
     `review_status` + `outgoing_signed_at IS NULL`, NOT on
     `status='pending_outgoing'`.

These tests use in-memory MagicMock Supabase chains (same style as
`test_handover_sign_incoming.py`) so they run with no DB and no network.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.handover_workflow_handlers import HandoverWorkflowHandlers

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXPORT_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


# ─────────────────────────────────────────────────────────────────────────────
# Supabase mock helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_db_mock(export_row, captured=None, filter_trace=None):
    """
    Mock Supabase client that:
      - returns `export_row` on single-row fetches against handover_exports
      - captures all .update() calls in `captured['updates']`
      - records every filter operator applied to a select() chain in
        `filter_trace` (list of ('op', args, kwargs) tuples, one per
        operator per table)
    """
    if captured is None:
        captured = {"inserts": [], "updates": []}
    if filter_trace is None:
        filter_trace = []

    def table(name):
        tbl = MagicMock()

        def _select(*_args, **_kwargs):
            chain = MagicMock()
            resp = MagicMock()

            # Default: return export_row for single-row selects on handover_exports.
            if name == "handover_exports":
                resp.data = export_row
            else:
                resp.data = []

            # Record each filter so tests can assert the semantics of the query.
            def _record(op):
                def _fn(*args, **kwargs):
                    filter_trace.append({"table": name, "op": op, "args": args, "kwargs": kwargs})
                    return chain
                return _fn

            chain.eq.side_effect = _record("eq")
            chain.neq.side_effect = _record("neq")
            chain.in_.side_effect = _record("in_")
            chain.is_.side_effect = _record("is_")
            chain.or_.side_effect = _record("or_")
            chain.gte.side_effect = _record("gte")
            chain.lte.side_effect = _record("lte")
            chain.order.side_effect = _record("order")
            chain.limit.side_effect = _record("limit")
            chain.single.side_effect = _record("single")
            chain.maybe_single.side_effect = _record("maybe_single")
            chain.execute.return_value = resp
            return chain

        def _insert(payload):
            captured["inserts"].append({"table": name, "payload": payload})
            ichain = MagicMock()
            ichain.execute.return_value = MagicMock(data=[payload])
            return ichain

        def _update(payload):
            captured["updates"].append({"table": name, "payload": payload})
            uchain = MagicMock()
            uchain.eq.return_value = uchain
            uchain.execute.return_value = MagicMock(data=[payload])
            return uchain

        tbl.select.side_effect = _select
        tbl.insert.side_effect = _insert
        tbl.update.side_effect = _update
        return tbl

    m = MagicMock()
    m.table.side_effect = table
    m._captured = captured
    m._filter_trace = filter_trace
    return m


def _valid_export_row_for_outgoing(**overrides):
    """Export in state 'ready for outgoing sign' — status still written by
    generate_export for now, per the T4 caveat."""
    row = {
        "id": EXPORT_ID,
        "yacht_id": YACHT_ID,
        "status": "pending_outgoing",   # legacy, read as precondition only
        "review_status": "pending_review",
        "document_hash": "sha256:abcdef",
        "signatures": {},
        "outgoing_signed_at": None,
        "incoming_signed_at": None,
    }
    row.update(overrides)
    return row


# ─────────────────────────────────────────────────────────────────────────────
# Retirement tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sign_outgoing_no_longer_writes_legacy_status():
    """
    After sign_outgoing succeeds, the UPDATE to handover_exports must NOT
    include status='pending_incoming'. review_status stays the source of truth;
    the retired legacy write is gone.
    """
    db = _make_db_mock(_valid_export_row_for_outgoing())
    h = HandoverWorkflowHandlers(db)

    result = await h.sign_outgoing(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="captain",
        note="Outgoing sig",
        method="typed",
    )

    assert result["status"] == "success", result

    updates = [u for u in db._captured["updates"] if u["table"] == "handover_exports"]
    assert len(updates) == 1, f"expected exactly one handover_exports update, got {updates}"
    payload = updates[0]["payload"]

    # The retired legacy write. MUST be absent.
    assert "status" not in payload, (
        f"sign_outgoing still writes legacy `status` column: {payload}. "
        "This column was retired as state driver by PR #642."
    )
    # Canonical signature fields still present.
    assert payload["outgoing_user_id"] == USER_ID
    assert payload["outgoing_role"] == "captain"
    assert "outgoing_signed_at" in payload
    assert payload["outgoing_comments"] == "Outgoing sig"
    assert "signatures" in payload


@pytest.mark.asyncio
async def test_get_pending_handovers_incoming_uses_review_status():
    """
    role_filter='incoming' must gate on review_status='complete' AND
    incoming_signed_at IS NULL — NOT on status='pending_incoming'.
    """
    db = _make_db_mock(export_row=[])
    h = HandoverWorkflowHandlers(db)

    await h.get_pending_handovers(
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        role_filter="incoming",
    )

    trace = db._filter_trace
    # No filter may ever target the legacy status column.
    assert not any(
        f["op"] == "eq" and len(f["args"]) >= 2
        and f["args"][0] == "status"
        and f["args"][1] in ("pending_incoming", "pending_outgoing")
        for f in trace
    ), f"legacy status filter leaked into get_pending_handovers(incoming): {trace}"

    # review_status='complete' must be applied.
    assert any(
        f["op"] == "eq" and f["args"] == ("review_status", "complete")
        for f in trace
    ), f"review_status='complete' filter missing: {trace}"

    # incoming_signed_at IS NULL must be applied.
    assert any(
        f["op"] == "is_" and f["args"] == ("incoming_signed_at", "null")
        for f in trace
    ), f"incoming_signed_at IS NULL filter missing: {trace}"


@pytest.mark.asyncio
async def test_get_pending_handovers_outgoing_uses_review_status():
    """
    role_filter='outgoing' must gate on review_status (pre-complete states)
    AND outgoing_signed_at IS NULL — NOT on status='pending_outgoing'.
    """
    db = _make_db_mock(export_row=[])
    h = HandoverWorkflowHandlers(db)

    await h.get_pending_handovers(
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        role_filter="outgoing",
    )

    trace = db._filter_trace
    assert not any(
        f["op"] == "eq" and len(f["args"]) >= 2
        and f["args"][0] == "status"
        and f["args"][1] == "pending_outgoing"
        for f in trace
    ), f"legacy status='pending_outgoing' filter leaked: {trace}"

    # Must filter on review_status (pre-complete).
    assert any(
        f["op"] == "in_"
        and f["args"][0] == "review_status"
        and "pending_review" in f["args"][1]
        for f in trace
    ), f"review_status pre-complete filter missing: {trace}"

    # Must filter on outgoing_signed_at IS NULL.
    assert any(
        f["op"] == "is_" and f["args"] == ("outgoing_signed_at", "null")
        for f in trace
    ), f"outgoing_signed_at IS NULL filter missing: {trace}"
