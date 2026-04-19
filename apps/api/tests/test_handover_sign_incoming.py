"""
Handover sign_incoming — Unit + Integration Tests
==================================================

Covers the four backend bugs fixed in feat/handover04-incoming-sign:

  Bug 1: role gate too narrow  → crew can now ack
  Bug 2: state-machine collision → precondition reads review_status, not status
  Bug 3: missing ledger event + notification cascade
  Bug 4: entity endpoint omits incoming_* fields

Tests:

  Handler-level (mock Supabase, no HTTP):
    - sign_incoming succeeds when review_status='complete' and incoming_signed_at IS NULL
    - sign_incoming 409s when review_status != 'complete'
    - sign_incoming 409s on double-ack (incoming_signed_at already set)
    - ledger_events row is written with action='handover_acknowledged' + proof_hash
    - pms_audit_log row is written
    - notification cascade reaches outgoing_user + captain/manager

  Route-level (in-memory FastAPI, mock auth):
    - crew role can hit /sign/incoming (no longer 403 — regression test for Bug 1)
    - entity endpoint returns all incoming_* fields

LAW 17: in-memory httpx.AsyncClient.
"""

import os
import sys
import json
import uuid
import asyncio
import pytest
import pytest_asyncio
import httpx
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.handover_workflow_handlers import HandoverWorkflowHandlers

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OUTGOING_USER_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
EXPORT_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"


# ─────────────────────────────────────────────────────────────────────────────
# Supabase mock helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_db_mock(export_row, captured_writes=None):
    """
    Build a MagicMock Supabase client that:
      - returns `export_row` when .table('handover_exports').select(...).single().execute()
      - returns empty auth_users_roles by default
      - captures all .insert() and .update() calls into captured_writes dict
    """
    if captured_writes is None:
        captured_writes = {"inserts": [], "updates": []}

    def table(name):
        tbl = MagicMock()

        # SELECT chain: .select().eq().eq().single().execute() returns export_row
        def _select(*_args, **_kwargs):
            chain = MagicMock()
            resp = MagicMock()

            if name == "handover_exports":
                resp.data = export_row
            elif name == "auth_users_roles":
                # No extra recipients by default — tests can override
                resp.data = []
            else:
                resp.data = []

            chain.eq.return_value = chain
            chain.in_.return_value = chain
            chain.limit.return_value = chain
            chain.order.return_value = chain
            chain.single.return_value = chain
            chain.maybe_single.return_value = chain
            chain.execute.return_value = resp
            return chain

        def _insert(payload):
            captured_writes["inserts"].append({"table": name, "payload": payload})
            ichain = MagicMock()
            ichain.execute.return_value = MagicMock(data=[payload])
            return ichain

        def _update(payload):
            captured_writes["updates"].append({"table": name, "payload": payload})
            uchain = MagicMock()
            uchain.eq.return_value = uchain
            uchain.execute.return_value = MagicMock(data=[payload])
            return uchain

        def _upsert(payload, **_kwargs):
            # pms_notifications uses upsert with on_conflict; normalize list vs dict
            # and capture the same shape as insert so tests can assert against either.
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                captured_writes["inserts"].append({"table": name, "payload": item})
            ichain = MagicMock()
            ichain.execute.return_value = MagicMock(data=items)
            return ichain

        tbl.select.side_effect = _select
        tbl.insert.side_effect = _insert
        tbl.update.side_effect = _update
        tbl.upsert.side_effect = _upsert
        return tbl

    m = MagicMock()
    m.table.side_effect = table
    m._captured = captured_writes
    return m


def _valid_export_row(**overrides):
    row = {
        "id": EXPORT_ID,
        "yacht_id": YACHT_ID,
        "status": "completed",          # legacy column — ignored by handler
        "review_status": "complete",    # real state machine — gating column
        "document_hash": "sha256:abcdef",
        "signatures": {},
        "incoming_signed_at": None,
        "outgoing_user_id": OUTGOING_USER_ID,
        "exported_by_user_id": OUTGOING_USER_ID,
        "department": "engineering",
    }
    row.update(overrides)
    return row


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Handler unit tests (no HTTP — direct call)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sign_incoming_success_when_review_status_complete():
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    result = await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",  # Bug 1 regression: crew is allowed
        acknowledge_critical=True,
        note="All items reviewed.",
        method="typed",
    )

    assert result["status"] == "success"
    assert result["signoff_complete"] is True
    assert result["export_id"] == EXPORT_ID

    # Verify the UPDATE to handover_exports wrote incoming_* fields
    updates = [w for w in db._captured["updates"] if w["table"] == "handover_exports"]
    assert len(updates) == 1
    upd = updates[0]["payload"]
    assert upd["incoming_user_id"] == USER_ID
    assert upd["incoming_role"] == "crew"
    assert upd["incoming_acknowledged_critical"] is True
    assert upd["signoff_complete"] is True
    assert "incoming_signed_at" in upd


@pytest.mark.asyncio
async def test_sign_incoming_rejects_when_review_status_not_complete():
    """Bug 2 regression — must NOT read legacy `status` column."""
    db = _make_db_mock(_valid_export_row(review_status="pending_hod_signature"))
    h = HandoverWorkflowHandlers(db)

    result = await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_STATUS"
    assert "review_status" in result["message"]


@pytest.mark.asyncio
async def test_sign_incoming_rejects_double_ack():
    db = _make_db_mock(
        _valid_export_row(incoming_signed_at="2026-04-17T12:00:00+00:00")
    )
    h = HandoverWorkflowHandlers(db)

    result = await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_STATUS"
    assert "already" in result["message"].lower()


@pytest.mark.asyncio
async def test_sign_incoming_rejects_unacknowledged_critical():
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    result = await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=False,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "CRITICAL_NOT_ACKNOWLEDGED"


@pytest.mark.asyncio
async def test_sign_incoming_writes_ledger_event_with_proof_hash():
    """Bug 3 regression — ledger_events MUST receive a handover_acknowledged row."""
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    ledger_inserts = [
        w for w in db._captured["inserts"] if w["table"] == "ledger_events"
    ]
    assert len(ledger_inserts) >= 1, "Expected at least one ledger_events insert"

    actor_event = next(
        w for w in ledger_inserts if w["payload"]["user_id"] == USER_ID
    )
    p = actor_event["payload"]
    assert p["action"] == "handover_acknowledged"
    assert p["entity_type"] == "handover_export"
    assert p["entity_id"] == EXPORT_ID
    assert p["yacht_id"] == YACHT_ID
    assert p["event_type"] == "handover"
    assert "proof_hash" in p and len(p["proof_hash"]) == 64  # sha256 hex
    assert p["metadata"]["acknowledged_critical"] is True
    assert p["metadata"]["export_id"] == EXPORT_ID


@pytest.mark.asyncio
async def test_sign_incoming_writes_audit_log():
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    audit_inserts = [
        w for w in db._captured["inserts"] if w["table"] == "pms_audit_log"
    ]
    assert len(audit_inserts) >= 1
    p = audit_inserts[0]["payload"]
    assert p["action"] == "handover_acknowledged"
    assert p["entity_type"] == "handover_export"
    assert p["actor_id"] == USER_ID


@pytest.mark.asyncio
async def test_sign_incoming_writes_notification_bell_rows():
    """Bell regression — recipients (NOT actor) must receive pms_notifications rows
    so the notification bell endpoint surfaces the event. Actor is self-audited via
    ledger/audit but not via pms_notifications (skip-self convention)."""
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    notif_inserts = [
        w for w in db._captured["inserts"] if w["table"] == "pms_notifications"
    ]
    assert notif_inserts, (
        "Expected at least one pms_notifications upsert — bell would stay silent"
    )

    # Outgoing user must get a bell row
    recipient_ids = {w["payload"]["user_id"] for w in notif_inserts}
    assert OUTGOING_USER_ID in recipient_ids
    # Actor must NOT get a bell row (self-skip convention)
    assert USER_ID not in recipient_ids

    p = notif_inserts[0]["payload"]
    assert p["notification_type"] == "handover_acknowledged"
    assert p["entity_type"] == "handover_export"
    assert p["entity_id"] == EXPORT_ID
    assert p["yacht_id"] == YACHT_ID
    assert p["triggered_by"] == USER_ID
    assert p["is_read"] is False
    assert p["idempotency_key"] == f"handover_acknowledged:{EXPORT_ID}:{OUTGOING_USER_ID}"
    assert p["title"]  # non-empty
    assert p["body"]   # non-empty


@pytest.mark.asyncio
async def test_sign_incoming_cascades_to_outgoing_user():
    db = _make_db_mock(_valid_export_row())
    h = HandoverWorkflowHandlers(db)

    await h.sign_incoming(
        export_id=EXPORT_ID,
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_role="crew",
        acknowledge_critical=True,
    )

    ledger_inserts = [
        w for w in db._captured["inserts"] if w["table"] == "ledger_events"
    ]
    user_ids = {w["payload"]["user_id"] for w in ledger_inserts}
    assert USER_ID in user_ids
    assert OUTGOING_USER_ID in user_ids, (
        "Outgoing user (writer of the handover) must receive a ledger notification"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Route-level tests (in-memory FastAPI + mocked auth)
# ─────────────────────────────────────────────────────────────────────────────

from pipeline_service import app  # noqa: E402
from middleware.auth import get_authenticated_user  # noqa: E402


def _auth(role: str):
    return {
        "user_id": USER_ID,
        "email": "crew@yacht.test",
        "yacht_id": YACHT_ID,
        "org_id": YACHT_ID,
        "tenant_key_alias": "y85fe111",
        "role": role,
        "vessel_ids": [YACHT_ID],
        "is_fleet_user": False,
        "yacht_name": "M/Y Test",
    }


@pytest_asyncio.fixture
async def crew_client():
    async def _mock_auth():
        return _auth("crew")

    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=10.0
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sign_incoming_route_crew_no_longer_403(crew_client):
    """Bug 1 regression — crew role previously got 403; now must be allowed through."""
    db = _make_db_mock(_valid_export_row())

    # Patch both: the handler factory + the handler's db (used inside the handler).
    fake_handlers = {
        "handover_workflow_handlers": HandoverWorkflowHandlers(db),
    }
    with patch(
        "routes.p0_actions_routes.get_handlers_for_tenant",
        return_value=fake_handlers,
    ):
        resp = await crew_client.post(
            f"/v1/actions/handover/{EXPORT_ID}/sign/incoming",
            params={"acknowledge_critical": True, "method": "typed"},
        )

    # Must NOT be 403. 200 is the happy path; anything else indicates the role gate
    # was not removed.
    assert resp.status_code != 403, f"crew got 403 — gate not removed: {resp.text}"
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["signoff_complete"] is True


@pytest.mark.asyncio
async def test_entity_endpoint_returns_incoming_fields(crew_client):
    """Bug 4 regression — entity endpoint must return all incoming_* fields."""
    incoming_signed_at = "2026-04-17T12:34:56+00:00"
    export_row = {
        "id": EXPORT_ID,
        "yacht_id": YACHT_ID,
        "review_status": "complete",
        "export_status": "exported",
        "document_hash": "sha256:abcdef",
        "department": "engineering",
        "user_signature": None,
        "hod_signature": None,
        "exported_at": "2026-04-17T10:00:00+00:00",
        "created_at": "2026-04-17T09:00:00+00:00",
        "edited_content": {"sections": []},
        "draft_id": None,
        "original_storage_url": "",
        "file_name": "",
        # Incoming-ack fields
        "incoming_user_id": USER_ID,
        "incoming_role": "crew",
        "incoming_signed_at": incoming_signed_at,
        "incoming_comments": "Acknowledged.",
        "incoming_acknowledged_critical": True,
        "signoff_complete": True,
        "signatures": {
            "incoming": {
                "payload": {"signer_user_id": USER_ID},
                "signature": "aabbcc",
                "alg": "HS256",
                "typ": "soft",
            }
        },
    }

    def _tenant_client(*_a, **_kw):
        m = MagicMock()

        def _table(name):
            tbl = MagicMock()

            def _select(*_s_args, **_s_kwargs):
                chain = MagicMock()
                resp = MagicMock()
                if name == "handover_exports":
                    resp.data = export_row
                elif name == "auth_users_profiles":
                    resp.data = [{"name": "Crew Member", "email": "crew@test.com"}]
                else:
                    resp.data = []
                chain.eq.return_value = chain
                chain.in_.return_value = chain
                chain.limit.return_value = chain
                chain.maybe_single.return_value = chain
                chain.execute.return_value = resp
                return chain

            tbl.select.side_effect = _select
            return tbl

        m.table.side_effect = _table
        m.storage = MagicMock()
        return m

    with patch("routes.entity_routes.get_tenant_client", side_effect=_tenant_client):
        resp = await crew_client.get(f"/v1/entity/handover_export/{EXPORT_ID}")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # All incoming_* fields present
    assert body["incoming_user_id"] == USER_ID
    assert body["incoming_user_name"] == "Crew Member"
    assert body["incoming_role"] == "crew"
    assert body["incoming_signed_at"] == incoming_signed_at
    assert body["incoming_comments"] == "Acknowledged."
    assert body["incoming_acknowledged_critical"] is True
    assert body["signoff_complete"] is True
    assert body["incoming_signature"] is not None
    assert body["incoming_signature"]["signature"] == "aabbcc"
