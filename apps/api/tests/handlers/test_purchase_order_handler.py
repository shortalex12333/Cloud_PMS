"""
Unit tests for purchase_order_handler.py — migrated from p0_actions_routes.py elif blocks.
Tests import from routes.handlers.purchase_order_handler which must exist for tests to pass.
"""
import pytest
from unittest.mock import MagicMock

# Will fail until handler file exists
from routes.handlers.purchase_order_handler import HANDLERS


def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "po-1"}]
    # update chains
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    # insert chains (ledger)
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    return db


def make_db_empty():
    """Stub Supabase client — returns empty data (update fails)."""
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    db.table.return_value.insert.return_value.execute.return_value.data = []
    return db


def base_ctx():
    return {"yacht_id": "y-1"}


def base_uc(role="captain"):
    return {"role": role, "tenant_key_alias": "y85fe1119", "department": "engineering"}


# ============================================================================
# REGISTRY COMPLETENESS
# ============================================================================

@pytest.mark.asyncio
async def test_all_po_actions_registered():
    expected = [
        "submit_purchase_order",
        "approve_purchase_order",
        "mark_po_received",
        "cancel_purchase_order",
    ]
    for name in expected:
        assert name in HANDLERS, f"Action '{name}' not in HANDLERS"


# ============================================================================
# submit_purchase_order
# ============================================================================

@pytest.mark.asyncio
async def test_submit_purchase_order_success():
    result = await HANDLERS["submit_purchase_order"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "submitted" in result["message"].lower()


@pytest.mark.asyncio
async def test_submit_purchase_order_missing_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["submit_purchase_order"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_submit_purchase_order_update_fails():
    result = await HANDLERS["submit_purchase_order"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db_empty(),
    )
    assert result["status"] == "error"
    assert result["error_code"] == "UPDATE_FAILED"


# ============================================================================
# approve_purchase_order
# ============================================================================

@pytest.mark.asyncio
async def test_approve_purchase_order_success():
    result = await HANDLERS["approve_purchase_order"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(role="captain"), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_approve_purchase_order_forbidden_role():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["approve_purchase_order"](
            payload={"purchase_order_id": "po-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="crew"), db_client=make_db(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_approve_purchase_order_missing_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["approve_purchase_order"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="captain"), db_client=make_db(),
        )
    assert exc.value.status_code == 400


# ============================================================================
# mark_po_received
# ============================================================================

@pytest.mark.asyncio
async def test_mark_po_received_success():
    result = await HANDLERS["mark_po_received"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(role="chief_engineer"), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_mark_po_received_forbidden_role():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["mark_po_received"](
            payload={"purchase_order_id": "po-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="crew"), db_client=make_db(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_mark_po_received_missing_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["mark_po_received"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="captain"), db_client=make_db(),
        )
    assert exc.value.status_code == 400


# ============================================================================
# cancel_purchase_order
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_purchase_order_success():
    result = await HANDLERS["cancel_purchase_order"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(role="manager"), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_cancel_purchase_order_forbidden_role():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["cancel_purchase_order"](
            payload={"purchase_order_id": "po-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(role="crew"), db_client=make_db(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_cancel_purchase_order_update_fails():
    result = await HANDLERS["cancel_purchase_order"](
        payload={"purchase_order_id": "po-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(role="captain"), db_client=make_db_empty(),
    )
    assert result["status"] == "error"
    assert result["error_code"] == "UPDATE_FAILED"
