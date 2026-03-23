"""
Tests for routes/show_related_signal_routes.py — signal discovery endpoint.

Coverage:
  - asyncpg happy path (200)
  - Fallback on TimeoutError
  - Fallback on asyncpg.QueryCanceledError
  - Fallback on missing DSN (ValueError)
  - 400 on invalid entity_type
  - HTTPException passthrough (not swallowed into fallback)

Runs in-memory (LAW 17): no real DB, all external deps are mocked.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import asyncpg
from contextlib import asynccontextmanager
from fastapi import HTTPException

from routes.show_related_signal_routes import view_signal_related, VALID_ENTITY_TYPES


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
ENTITY_ID = uuid4()

AUTH_DICT = {
    "user_id": USER_ID,
    "org_id": YACHT_ID,
    "yacht_id": YACHT_ID,
    "role": "crew",
    "locale": None,
    "tenant_key_alias": "y85fe111",
}

SIGNAL_SUCCESS = {
    "status": "success",
    "entity_type": "work_order",
    "entity_id": str(ENTITY_ID),
    "entity_text": "Replace fuel filters; equipment: main engine",
    "items": [],
    "count": 0,
    "signal_source": "entity_embedding",
    "metadata": {"limit": 10, "embedding_generated": True},
}


def _make_pool_mock():
    """Build a mock pool whose acquire() works as an async context manager."""
    mock_conn = AsyncMock()
    mock_pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire
    return mock_pool, mock_conn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("routes.show_related_signal_routes.get_signal_related", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_db_pool", new_callable=AsyncMock)
async def test_signal_200_asyncpg_path(mock_get_pool, mock_get_signal):
    """Happy path: asyncpg pool available, handler returns success."""
    mock_pool, _ = _make_pool_mock()
    mock_get_pool.return_value = mock_pool

    mock_get_signal.return_value = SIGNAL_SUCCESS

    result = await view_signal_related(
        entity_type="work_order",
        entity_id=ENTITY_ID,
        limit=10,
        auth=AUTH_DICT,
    )

    assert result["status"] == "success"
    assert result["entity_type"] == "work_order"
    mock_get_signal.assert_awaited_once()


@pytest.mark.asyncio
@patch("routes.show_related_signal_routes.get_tenant_client")
@patch("routes.show_related_signal_routes.get_signal_related_supabase", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_signal_related", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_db_pool", new_callable=AsyncMock)
async def test_signal_fallback_on_timeout(mock_get_pool, mock_get_signal, mock_sb_handler, mock_tenant):
    """TimeoutError from asyncpg triggers Supabase fallback."""
    mock_pool, _ = _make_pool_mock()
    mock_get_pool.return_value = mock_pool

    mock_get_signal.side_effect = TimeoutError("statement timeout")
    mock_tenant.return_value = MagicMock()
    mock_sb_handler.return_value = SIGNAL_SUCCESS

    result = await view_signal_related(
        entity_type="work_order",
        entity_id=ENTITY_ID,
        limit=10,
        auth=AUTH_DICT,
    )

    assert result["status"] == "success"
    mock_sb_handler.assert_awaited_once()


@pytest.mark.asyncio
@patch("routes.show_related_signal_routes.get_tenant_client")
@patch("routes.show_related_signal_routes.get_signal_related_supabase", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_signal_related", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_db_pool", new_callable=AsyncMock)
async def test_signal_fallback_on_query_canceled(mock_get_pool, mock_get_signal, mock_sb_handler, mock_tenant):
    """asyncpg.QueryCanceledError triggers Supabase fallback."""
    mock_pool, _ = _make_pool_mock()
    mock_get_pool.return_value = mock_pool

    mock_get_signal.side_effect = asyncpg.QueryCanceledError("canceling statement due to statement timeout")
    mock_tenant.return_value = MagicMock()
    mock_sb_handler.return_value = SIGNAL_SUCCESS

    result = await view_signal_related(
        entity_type="work_order",
        entity_id=ENTITY_ID,
        limit=10,
        auth=AUTH_DICT,
    )

    assert result["status"] == "success"
    mock_sb_handler.assert_awaited_once()


@pytest.mark.asyncio
@patch("routes.show_related_signal_routes.get_tenant_client")
@patch("routes.show_related_signal_routes.get_signal_related_supabase", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_db_pool", new_callable=AsyncMock)
async def test_signal_fallback_on_missing_dsn(mock_get_pool, mock_sb_handler, mock_tenant):
    """ValueError('not configured') from get_db_pool triggers Supabase fallback."""
    mock_get_pool.side_effect = ValueError("READ_DB_DSN or DATABASE_URL not configured")
    mock_tenant.return_value = MagicMock()
    mock_sb_handler.return_value = SIGNAL_SUCCESS

    result = await view_signal_related(
        entity_type="work_order",
        entity_id=ENTITY_ID,
        limit=10,
        auth=AUTH_DICT,
    )

    assert result["status"] == "success"
    mock_sb_handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_signal_400_invalid_entity_type():
    """Invalid entity_type returns 400, not 500."""
    with pytest.raises(HTTPException) as exc_info:
        await view_signal_related(
            entity_type="garbage",
            entity_id=ENTITY_ID,
            limit=10,
            auth=AUTH_DICT,
        )
    assert exc_info.value.status_code == 400
    assert "Invalid entity_type" in exc_info.value.detail


@pytest.mark.asyncio
@patch("routes.show_related_signal_routes.get_signal_related", new_callable=AsyncMock)
@patch("routes.show_related_signal_routes.get_db_pool", new_callable=AsyncMock)
async def test_signal_reraises_http_exception(mock_get_pool, mock_get_signal):
    """HTTPException from handler is NOT swallowed into fallback."""
    mock_pool, _ = _make_pool_mock()
    mock_get_pool.return_value = mock_pool

    mock_get_signal.side_effect = HTTPException(status_code=404, detail="Entity not found")

    with pytest.raises(HTTPException) as exc_info:
        await view_signal_related(
            entity_type="work_order",
            entity_id=ENTITY_ID,
            limit=10,
            auth=AUTH_DICT,
        )
    assert exc_info.value.status_code == 404
