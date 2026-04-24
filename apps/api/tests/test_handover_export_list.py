"""
GET /v1/handover/exports — Exported-tab List Tests
==================================================

Exercises the scope + enrichment rules added for the /handover-export
"Exported" tab (Issue 11 / HANDOVER08):

  - HOD (chief_engineer / chief_officer / captain / manager) sees ALL yacht rows
  - non-HOD sees only rows they outgoing/incoming OR same-role back-to-back
  - outgoing_user_name / incoming_user_name resolved via auth_users_profiles
  - response shape matches Exported-tab UX spec

And the companion POST /v1/handover/export/{id}/signed-url endpoint:
  - HOD can mint
  - non-HOD on their own row can mint
  - stranger gets 403
  - missing document → 404

LAW 17: in-memory via httpx.AsyncClient, DB mocked via patch.
"""

from __future__ import annotations

import os
import sys
import uuid
import pytest
import pytest_asyncio
import httpx
from typing import Optional
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_service import app
from middleware.auth import get_authenticated_user

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OTHER_USER_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
EXPORT_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"

_AUTH_HOD = {
    "user_id": USER_ID,
    "email": "hod@yacht.test",
    "yacht_id": YACHT_ID,
    "org_id": YACHT_ID,
    "tenant_key_alias": "y85fe111",
    "role": "chief_engineer",
    "vessel_ids": [YACHT_ID],
    "is_fleet_user": False,
    "yacht_name": "M/Y Test",
}

_AUTH_CREW = {
    **_AUTH_HOD,
    "email": "crew@yacht.test",
    "role": "engineer",
}


def _row(
    export_id: str,
    outgoing_user_id: Optional[str] = None,
    outgoing_role: Optional[str] = None,
    incoming_user_id: Optional[str] = None,
    incoming_role: Optional[str] = None,
    review_status: str = "complete",
    signoff_complete: bool = True,
):
    return {
        "id": export_id,
        "draft_id": str(uuid.uuid4()),
        "yacht_id": YACHT_ID,
        "export_type": "html",
        "exported_at": "2026-04-20T10:00:00+00:00",
        "exported_by_user_id": outgoing_user_id,
        "document_hash": "abc",
        "export_status": "completed",
        "file_name": None,
        "period_start": "2026-04-01T00:00:00+00:00",
        "period_end": "2026-04-20T00:00:00+00:00",
        "department": "Engineering",
        "outgoing_user_id": outgoing_user_id,
        "outgoing_role": outgoing_role,
        "outgoing_signed_at": "2026-04-20T09:00:00+00:00",
        "incoming_user_id": incoming_user_id,
        "incoming_role": incoming_role,
        "incoming_signed_at": "2026-04-20T11:00:00+00:00" if incoming_user_id else None,
        "hod_signature": None,
        "hod_signed_at": "2026-04-20T12:00:00+00:00",
        "user_signed_at": "2026-04-20T09:00:00+00:00",
        "review_status": review_status,
        "signoff_complete": signoff_complete,
        "original_storage_url": "handover-exports/y/original/x.html",
        "signed_storage_url": "handover-exports/y/signed/x.html",
    }


def _build_db_mock(exports_rows, profile_rows=None, signer_result=None):
    """Mock that returns exports_rows for handover_exports, profile_rows
    for auth_users_profiles, and signer_result for storage.create_signed_url."""
    m = MagicMock()

    exports_chain = MagicMock()
    exports_exec = MagicMock()
    exports_exec.data = exports_rows
    exports_exec.count = len(exports_rows)
    exports_chain.execute.return_value = exports_exec
    for meth in ("eq", "or_", "order", "range", "limit", "in_", "neq"):
        getattr(exports_chain, meth).return_value = exports_chain

    profiles_chain = MagicMock()
    profiles_exec = MagicMock()
    profiles_exec.data = profile_rows or []
    profiles_chain.execute.return_value = profiles_exec
    for meth in ("eq", "in_", "order", "range", "limit"):
        getattr(profiles_chain, meth).return_value = profiles_chain

    def _select_table(name):
        tbl = MagicMock()
        if name == "handover_exports":
            tbl.select.return_value = exports_chain
        elif name == "auth_users_profiles":
            tbl.select.return_value = profiles_chain
        else:
            c = MagicMock()
            c.execute.return_value = MagicMock(data=[])
            for meth in ("eq", "or_", "order", "range", "limit", "in_"):
                getattr(c, meth).return_value = c
            tbl.select.return_value = c
        return tbl

    m.table.side_effect = _select_table

    # Storage signer
    storage_bucket = MagicMock()
    storage_bucket.create_signed_url.return_value = signer_result or {"signedURL": "https://signed.example/handover.html"}
    m.storage.from_.return_value = storage_bucket

    return m, exports_chain


@pytest_asyncio.fixture
async def client_hod():
    async def _mock_auth():
        return _AUTH_HOD
    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_crew():
    async def _mock_auth():
        return _AUTH_CREW
    app.dependency_overrides[get_authenticated_user] = _mock_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10.0) as c:
        yield c
    app.dependency_overrides.clear()


# ── LIST tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_exports_hod_sees_all(client_hod):
    """HOD role skips the or_() filter — sees every row on yacht."""
    rows = [
        _row(str(uuid.uuid4()), outgoing_user_id=OTHER_USER_ID, outgoing_role="engineer"),
        _row(str(uuid.uuid4()), outgoing_user_id=USER_ID, outgoing_role="chief_engineer"),
    ]
    profiles = [
        {"id": OTHER_USER_ID, "name": "Other Crew", "email": "other@y.test"},
        {"id": USER_ID, "name": "Chief HOD", "email": "hod@y.test"},
    ]
    db, exports_chain = _build_db_mock(rows, profile_rows=profiles)
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_hod.get("/v1/handover/exports")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "all"
    assert body["count"] == 2
    assert body["exports"][0]["outgoing_user_name"] in ("Other Crew", "Chief HOD")
    # or_() must NOT have been called for HOD role.
    assert exports_chain.or_.call_count == 0


@pytest.mark.asyncio
async def test_list_exports_crew_applies_or_filter(client_crew):
    """Non-HOD role calls or_() with the four-predicate same-role scope."""
    row = _row(
        str(uuid.uuid4()),
        outgoing_user_id=USER_ID,
        outgoing_role="engineer",
        incoming_user_id=OTHER_USER_ID,
        incoming_role="engineer",
    )
    profiles = [
        {"id": USER_ID, "name": "Me Engineer", "email": "me@y.test"},
        {"id": OTHER_USER_ID, "name": "Peer Engineer", "email": "peer@y.test"},
    ]
    db, exports_chain = _build_db_mock([row], profile_rows=profiles)
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_crew.get("/v1/handover/exports")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == "own_and_same_role"
    assert body["count"] == 1
    assert exports_chain.or_.call_count == 1
    filter_arg = exports_chain.or_.call_args[0][0]
    assert f"outgoing_user_id.eq.{USER_ID}" in filter_arg
    assert f"incoming_user_id.eq.{USER_ID}" in filter_arg
    assert "outgoing_role.eq.engineer" in filter_arg
    assert "incoming_role.eq.engineer" in filter_arg

    exported = body["exports"][0]
    assert exported["outgoing_user_name"] == "Me Engineer"
    assert exported["incoming_user_name"] == "Peer Engineer"
    # Storage URLs must NOT leak raw.
    assert "signed_storage_url" not in exported
    assert "original_storage_url" not in exported
    assert exported["has_signed_document"] is True
    assert exported["has_original_document"] is True


@pytest.mark.asyncio
async def test_list_exports_empty_no_profiles_lookup(client_crew):
    """Zero rows → no profile lookup, returns empty list not null."""
    db, _ = _build_db_mock([])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_crew.get("/v1/handover/exports")

    assert resp.status_code == 200
    body = resp.json()
    assert body["exports"] == []
    assert body["count"] == 0


# ── SIGNED-URL tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_signed_url_hod_success(client_hod):
    """HOD mints signed URL regardless of outgoing/incoming role."""
    row = _row(EXPORT_ID, outgoing_user_id=OTHER_USER_ID, outgoing_role="engineer")
    db, _ = _build_db_mock([row])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_hod.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 200
    body = resp.json()
    assert body["url"].startswith("https://")
    assert body["ttl_seconds"] == 300
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_signed_url_own_row_success(client_crew):
    """Non-HOD outgoing user on the row can mint."""
    row = _row(EXPORT_ID, outgoing_user_id=USER_ID, outgoing_role="engineer")
    db, _ = _build_db_mock([row])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_crew.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signed_url_same_role_success(client_crew):
    """Non-HOD with same role on incoming side can mint (back-to-back peer)."""
    row = _row(
        EXPORT_ID,
        outgoing_user_id=OTHER_USER_ID,
        outgoing_role="engineer",  # matches crew's engineer role
    )
    db, _ = _build_db_mock([row])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_crew.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signed_url_stranger_forbidden(client_crew):
    """Non-HOD with no role/user overlap gets 403."""
    row = _row(
        EXPORT_ID,
        outgoing_user_id=OTHER_USER_ID,
        outgoing_role="deck",
        incoming_user_id=OTHER_USER_ID,
        incoming_role="deck",
    )
    db, _ = _build_db_mock([row])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_crew.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_signed_url_missing_export(client_hod):
    """Unknown export → 404."""
    db, _ = _build_db_mock([])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_hod.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_signed_url_no_document(client_hod):
    """Row exists but no signed/original URL → 404."""
    row = _row(EXPORT_ID, outgoing_user_id=USER_ID, outgoing_role="chief_engineer")
    row["signed_storage_url"] = None
    row["original_storage_url"] = None
    db, _ = _build_db_mock([row])
    with patch("integrations.supabase.get_supabase_client", return_value=db):
        resp = await client_hod.post(f"/v1/handover/export/{EXPORT_ID}/signed-url")

    assert resp.status_code == 404
