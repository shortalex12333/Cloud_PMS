"""
Unit tests for receiving_handler.py — migrated from p0_actions_routes.py elif blocks.
Tests import from routes.handlers.receiving_handler which must exist for tests to pass.
"""
import pytest
from unittest.mock import MagicMock

# Will fail until handler file exists
from routes.handlers.receiving_handler import HANDLERS


def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "rec-1", "status": "draft"}]
    # update chains
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    # insert chains (ledger)
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    # select chains (for edit_receiving)
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = rows[0] if rows else None
    return db


def make_db_empty():
    """Stub Supabase client — returns empty data."""
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = []
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    return db


def base_ctx():
    return {"yacht_id": "y-1"}


def base_uc():
    return {"role": "captain", "tenant_key_alias": "y85fe1119", "department": "engineering"}


# ============================================================================
# REGISTRY COMPLETENESS
# ============================================================================

@pytest.mark.asyncio
async def test_all_receiving_actions_registered():
    expected = [
        "submit_receiving_for_review",
        "edit_receiving",
    ]
    for name in expected:
        assert name in HANDLERS, f"Action '{name}' not in HANDLERS"


# ============================================================================
# submit_receiving_for_review
# ============================================================================

@pytest.mark.asyncio
async def test_submit_receiving_for_review_success():
    result = await HANDLERS["submit_receiving_for_review"](
        payload={"receiving_id": "rec-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "review" in result["message"].lower()


@pytest.mark.asyncio
async def test_submit_receiving_for_review_missing_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["submit_receiving_for_review"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_submit_receiving_for_review_from_context():
    """receiving_id can come from context if not in payload."""
    result = await HANDLERS["submit_receiving_for_review"](
        payload={},
        context={"yacht_id": "y-1", "receiving_id": "rec-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_submit_receiving_for_review_update_fails():
    result = await HANDLERS["submit_receiving_for_review"](
        payload={"receiving_id": "rec-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db_empty(),
    )
    assert result["status"] == "error"
    assert result["error_code"] == "UPDATE_FAILED"


# ============================================================================
# edit_receiving
# ============================================================================

@pytest.mark.asyncio
async def test_edit_receiving_success():
    result = await HANDLERS["edit_receiving"](
        payload={"receiving_id": "rec-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "data" in result


@pytest.mark.asyncio
async def test_edit_receiving_missing_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["edit_receiving"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_edit_receiving_not_found():
    result = await HANDLERS["edit_receiving"](
        payload={"receiving_id": "rec-missing"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db_empty(),
    )
    assert result["status"] == "error"
    assert result["error_code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_edit_receiving_from_context():
    """receiving_id can come from context if not in payload."""
    result = await HANDLERS["edit_receiving"](
        payload={},
        context={"yacht_id": "y-1", "receiving_id": "rec-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "data" in result
