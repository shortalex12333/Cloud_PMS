"""
Unit tests for hours_of_rest_handler.py — migrated from p0_actions_routes.py elif blocks.
Tests import from routes.handlers.hours_of_rest_handler which must exist for tests to pass.

Crew Lens v3 handlers delegate to HoursOfRestHandlers class — tested for registry + delegation.
"""
import inspect
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from routes.handlers.hours_of_rest_handler import HANDLERS


# ============================================================================
# HELPERS
# ============================================================================

def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "hor-1", "crew_id": "c-1", "date": "2026-03-17"}]
    # select → eq → eq → gte/lte → order → limit → execute
    chain = db.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value.data = rows
    chain.maybe_single.return_value.execute.return_value.data = rows[0] if rows else None
    # update chain
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = rows
    # insert chain
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    return db


def make_db_empty():
    """Stub Supabase client — returns empty data."""
    db = MagicMock()
    chain = db.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.lte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value.data = []
    chain.maybe_single.return_value.execute.return_value.data = None
    db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = []
    return db


def base_ctx():
    return {"yacht_id": "y-1"}


def base_uc():
    return {"role": "captain", "tenant_key_alias": "y85fe1119", "department": "deck"}


# ============================================================================
# REGISTRY COMPLETENESS
# ============================================================================

def test_all_hor_actions_registered():
    expected = [
        "get_hours_of_rest",
        "upsert_hours_of_rest",
        "get_monthly_signoff",
        "list_monthly_signoffs",
        "create_monthly_signoff",
        "sign_monthly_signoff",
    ]
    for name in expected:
        assert name in HANDLERS, f"Action '{name}' not in HANDLERS"


def test_handler_signatures_match_contract():
    """All handlers must match the Phase 4 handler contract."""
    expected_params = {"payload", "context", "yacht_id", "user_id", "user_context", "db_client"}
    for action_name, fn in HANDLERS.items():
        sig = inspect.signature(fn)
        actual_params = set(sig.parameters.keys())
        assert actual_params == expected_params, (
            f"Handler '{action_name}' has params {actual_params}, expected {expected_params}"
        )


# ============================================================================
# DELEGATION: get_hours_of_rest (delegates to HoursOfRestHandlers)
# ============================================================================

@pytest.mark.asyncio
async def test_get_hours_of_rest_delegates():
    """Verify get_hours_of_rest instantiates HoursOfRestHandlers and delegates."""
    mock_result = {"status": "success", "records": []}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.get_hours_of_rest = AsyncMock(return_value=mock_result)

        result = await HANDLERS["get_hours_of_rest"](
            payload={"user_id": "u-target"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.get_hours_of_rest.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_hours_of_rest_delegates():
    """Verify upsert_hours_of_rest instantiates HoursOfRestHandlers and delegates."""
    mock_result = {"status": "success", "message": "Upserted"}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.upsert_hours_of_rest = AsyncMock(return_value=mock_result)

        result = await HANDLERS["upsert_hours_of_rest"](
            payload={"record_date": "2026-03-17", "rest_periods": []},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.upsert_hours_of_rest.assert_awaited_once()


# ============================================================================
# DELEGATION: monthly signoff actions
# ============================================================================

@pytest.mark.asyncio
async def test_get_monthly_signoff_delegates():
    mock_result = {"status": "success", "signoff": {}}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.get_monthly_signoff = AsyncMock(return_value=mock_result)

        result = await HANDLERS["get_monthly_signoff"](
            payload={"signoff_id": "s-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.get_monthly_signoff.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_monthly_signoffs_delegates():
    mock_result = {"status": "success", "signoffs": []}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.list_monthly_signoffs = AsyncMock(return_value=mock_result)

        result = await HANDLERS["list_monthly_signoffs"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.list_monthly_signoffs.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_monthly_signoff_delegates():
    mock_result = {"status": "success", "signoff_id": "s-new"}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.create_monthly_signoff = AsyncMock(return_value=mock_result)

        result = await HANDLERS["create_monthly_signoff"](
            payload={"month": "2026-03"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.create_monthly_signoff.assert_awaited_once()


@pytest.mark.asyncio
async def test_sign_monthly_signoff_delegates():
    mock_result = {"status": "success", "message": "Signed"}
    with patch("routes.handlers.hours_of_rest_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.sign_monthly_signoff = AsyncMock(return_value=mock_result)

        result = await HANDLERS["sign_monthly_signoff"](
            payload={"signoff_id": "s-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.sign_monthly_signoff.assert_awaited_once()


# ============================================================================
# GUARDS: signoff_id validation
# ============================================================================

@pytest.mark.asyncio
async def test_get_monthly_signoff_missing_signoff_id():
    """get_monthly_signoff must raise 400 when signoff_id is missing."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["get_monthly_signoff"](
            payload={},  # missing signoff_id
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
    assert exc.value.status_code == 400
    assert "signoff_id is required" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_sign_monthly_signoff_missing_signoff_id():
    """sign_monthly_signoff must raise 400 when signoff_id is missing."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["sign_monthly_signoff"](
            payload={},  # missing signoff_id
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
    assert exc.value.status_code == 400
    assert "signoff_id is required" in str(exc.value.detail)
