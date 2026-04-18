"""
T4 — `sign_outgoing` deprecation warning regression test
=========================================================

Background
----------
Task T4 consolidated the twin HTTP signing paths for handover. The line-by-line
parity audit (see `docs/ongoing_work/handover/ARCHITECTURE.md` §9) found that
`POST /v1/actions/handover/{id}/sign/outgoing` is a feature-poor duplicate of
`POST /v1/handover/export/{id}/submit`. The canonical author-sign path is
`/submit`; the deprecated `/sign/outgoing` (and the handler method backing it)
must log a WARN on every invocation so that lingering callers surface during
the one-release deprecation window.

This test pins the deprecation signal: if a future refactor removes the
`logger.warning(...)` without also removing the function, the deprecation
window silently collapses and stragglers will never show up in logs.

Scope
-----
- `HandoverWorkflowHandlers.sign_outgoing` emits `logger.warning` whose record
  matches the contract string ("DEPRECATED" + "sign_outgoing" + the new
  canonical path `/submit`).

Run
---
    cd apps/api && pytest tests/test_handover_sign_outgoing_deprecation.py -v

No DB, no network — pure in-memory MagicMock Supabase chain.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.handover_workflow_handlers import HandoverWorkflowHandlers

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXPORT_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


def _valid_export_row():
    return {
        "id": EXPORT_ID,
        "yacht_id": YACHT_ID,
        "status": "pending_outgoing",
        "review_status": "pending_review",
        "document_hash": "sha256:abcdef",
        "signatures": {},
        "outgoing_signed_at": None,
        "incoming_signed_at": None,
    }


def _make_db_mock(export_row):
    """Minimal Supabase mock — returns `export_row` on a single-row select against
    handover_exports and swallows .update()/.insert() calls."""
    def table(_name):
        tbl = MagicMock()

        def _select(*_args, **_kwargs):
            chain = MagicMock()
            resp = MagicMock()
            resp.data = export_row
            chain.eq.return_value = chain
            chain.in_.return_value = chain
            chain.is_.return_value = chain
            chain.single.return_value = chain
            chain.maybe_single.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain
            chain.execute.return_value = resp
            return chain

        def _update(_payload):
            uchain = MagicMock()
            uchain.eq.return_value = uchain
            uchain.execute.return_value = MagicMock(data=[{}])
            return uchain

        def _insert(_payload):
            ichain = MagicMock()
            ichain.execute.return_value = MagicMock(data=[{}])
            return ichain

        tbl.select.side_effect = _select
        tbl.update.side_effect = _update
        tbl.insert.side_effect = _insert
        return tbl

    m = MagicMock()
    m.table.side_effect = table
    return m


@pytest.mark.asyncio
async def test_sign_outgoing_emits_deprecation_warning(caplog):
    """
    Invoking `HandoverWorkflowHandlers.sign_outgoing` MUST emit a WARN-level log
    that:
      - contains the literal string "DEPRECATED"
      - names `sign_outgoing`
      - points the caller at the canonical path (`/v1/handover/export/{id}/submit`)

    If this test regresses, the one-release deprecation window is broken.
    """
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    # caplog captures on the module logger for handover_workflow_handlers.
    caplog.set_level("WARNING", logger="handlers.handover_workflow_handlers")

    result = await h.sign_outgoing(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="captain",
        note=None,
        method="typed",
    )

    # The call itself still succeeds — deprecation is a warning, not a block.
    assert result["status"] == "success", result

    warnings = [
        rec for rec in caplog.records
        if rec.levelname == "WARNING"
        and "DEPRECATED" in rec.getMessage()
        and "sign_outgoing" in rec.getMessage()
    ]
    assert warnings, (
        "sign_outgoing must emit a WARN log containing 'DEPRECATED' and "
        "'sign_outgoing' on every invocation (T4 consolidation). "
        f"Captured records: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )

    # Migration pointer must be present so the log is actionable.
    msg = warnings[0].getMessage()
    assert "/submit" in msg, (
        "Deprecation log must point callers at the canonical path "
        f"'/v1/handover/export/{{id}}/submit'. Got: {msg!r}"
    )


@pytest.mark.asyncio
async def test_sign_outgoing_still_returns_success_during_deprecation():
    """
    The deprecation window is one release: the route must still fulfil real
    calls, only logging. If this flips to error/410 it must happen as its own
    PR with the removal plan executed (see ARCHITECTURE.md §9 step 2+).
    """
    db = _make_db_mock(_valid_export_row())
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
    assert result["export_id"] == EXPORT_ID
    assert result["signed_by"] == USER_ID
