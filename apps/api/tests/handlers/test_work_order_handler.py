"""
Unit tests for work_order_handler.py — migrated from p0_actions_routes.py elif blocks.
Tests import from routes.handlers.work_order_handler which must exist for tests to pass.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

# Will fail until handler file exists
from routes.handlers.work_order_handler import HANDLERS


def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "wo-1"}]
    # update chains
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    # insert chains
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    # upsert chains
    db.table.return_value.upsert.return_value.execute.return_value.data = rows
    # select chains (various depths)
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = rows[0] if rows else None
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = rows[0] if rows else None
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = rows
    # in_ chains for view_worklist
    db.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = rows
    # select all for export
    db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = rows
    return db


def base_ctx(yacht_id="y-1"):
    return {"yacht_id": yacht_id}


def base_uc():
    return {"role": "captain", "tenant_key_alias": "y85fe1119", "department": "engineering"}


# ============================================================================
# ALIAS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_wo_alias_same_function():
    assert HANDLERS["update_wo"] is HANDLERS["update_work_order"]


@pytest.mark.asyncio
async def test_assign_wo_alias_same_function():
    assert HANDLERS["assign_wo"] is HANDLERS["assign_work_order"]


@pytest.mark.asyncio
async def test_complete_work_order_alias():
    assert HANDLERS["complete_work_order"] is HANDLERS["close_work_order"]


@pytest.mark.asyncio
async def test_log_work_hours_alias():
    assert HANDLERS["log_work_hours"] is HANDLERS["add_wo_hours"]


@pytest.mark.asyncio
async def test_add_part_to_wo_alias():
    assert HANDLERS["add_part_to_wo"] is HANDLERS["add_wo_part"]


@pytest.mark.asyncio
async def test_add_note_to_wo_alias():
    assert HANDLERS["add_note_to_wo"] is HANDLERS["add_wo_note"]


@pytest.mark.asyncio
async def test_begin_wo_alias():
    assert HANDLERS["begin_wo"] is HANDLERS["start_work_order"]


@pytest.mark.asyncio
async def test_cancel_wo_alias():
    assert HANDLERS["cancel_wo"] is HANDLERS["cancel_work_order"]


@pytest.mark.asyncio
async def test_create_wo_alias():
    assert HANDLERS["create_wo"] is HANDLERS["create_work_order"]


# ============================================================================
# HANDLER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_work_order():
    result = await HANDLERS["update_work_order"](
        payload={"work_order_id": "wo-1", "title": "New"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_assign_work_order():
    result = await HANDLERS["assign_work_order"](
        payload={"work_order_id": "wo-1", "assigned_to": "crew-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_close_work_order():
    result = await HANDLERS["close_work_order"](
        payload={"work_order_id": "wo-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_add_wo_hours():
    result = await HANDLERS["add_wo_hours"](
        payload={"work_order_id": "wo-1", "hours": 3, "description": "Test work"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_add_wo_part():
    result = await HANDLERS["add_wo_part"](
        payload={"work_order_id": "wo-1", "part_id": "p-1", "quantity": 2},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_add_wo_part_missing_part_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["add_wo_part"](
            payload={"work_order_id": "wo-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_wo_note():
    result = await HANDLERS["add_wo_note"](
        payload={"work_order_id": "wo-1", "note_text": "Test note"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_start_work_order():
    result = await HANDLERS["start_work_order"](
        payload={"work_order_id": "wo-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_cancel_work_order():
    result = await HANDLERS["cancel_work_order"](
        payload={"work_order_id": "wo-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_create_work_order():
    db = make_db([{"id": "new-wo"}])
    result = await HANDLERS["create_work_order"](
        payload={"title": "New WO", "priority": "routine"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "work_order_id" in result


@pytest.mark.asyncio
async def test_create_work_order_missing_title():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["create_work_order"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_list_work_orders(monkeypatch):
    """list_work_orders delegates to handlers.list_handlers.ListHandlers — mock that class."""
    mock_list_handler = MagicMock()
    mock_list_handler.list_work_orders = AsyncMock(return_value={"status": "success", "data": [], "total": 0})
    mock_cls = MagicMock(return_value=mock_list_handler)
    monkeypatch.setattr("handlers.list_handlers.ListHandlers", mock_cls)

    result = await HANDLERS["list_work_orders"](
        payload={},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_view_work_order_detail():
    db = make_db([{"id": "wo-1", "title": "Test WO"}])
    result = await HANDLERS["view_work_order_detail"](
        payload={"work_order_id": "wo-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "work_order" in result


@pytest.mark.asyncio
async def test_view_work_order_checklist():
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        "id": "wo-1",
        "metadata": {"checklist": [{"text": "Step 1", "completed": True}, {"text": "Step 2", "completed": False}]}
    }
    result = await HANDLERS["view_work_order_checklist"](
        payload={"work_order_id": "wo-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert result["progress"]["completed"] == 1
    assert result["progress"]["total"] == 2


@pytest.mark.asyncio
async def test_view_worklist():
    result = await HANDLERS["view_worklist"](
        payload={},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "worklist" in result


@pytest.mark.asyncio
async def test_add_worklist_task():
    db = make_db([{"id": "task-1"}])
    result = await HANDLERS["add_worklist_task"](
        payload={"task_description": "Fix hull paint"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "task_id" in result


@pytest.mark.asyncio
async def test_add_worklist_task_missing_description():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["add_worklist_task"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_export_worklist():
    result = await HANDLERS["export_worklist"](
        payload={},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"
    assert "data" in result


@pytest.mark.asyncio
async def test_view_work_order_history():
    db = make_db([{"id": "wo-1"}])
    result = await HANDLERS["view_work_order_history"](
        payload={"equipment_id": "eq-1"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "work_orders" in result


@pytest.mark.asyncio
async def test_view_work_order_history_missing_equipment_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["view_work_order_history"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_worklist_progress():
    result = await HANDLERS["update_worklist_progress"](
        payload={"worklist_item_id": "wl-1", "progress": 50},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_update_worklist_progress_missing_fields():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["update_worklist_progress"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_work_order_for_equipment_success():
    db = make_db([{"id": "new-wo"}])
    result = await HANDLERS["create_work_order_for_equipment"](
        payload={"type": "corrective", "priority": "routine"},
        context={"yacht_id": "y-1", "equipment_id": "eq-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "work_order_id" in result


@pytest.mark.asyncio
async def test_create_work_order_for_equipment_missing_equipment_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["create_work_order_for_equipment"](
            payload={"type": "corrective", "priority": "routine"},
            context={"yacht_id": "y-1"},  # no equipment_id
            yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


# ============================================================================
# REGISTRY COMPLETENESS
# ============================================================================

@pytest.mark.asyncio
async def test_add_work_order_photo_success():
    """add_work_order_photo stores photo URL in WO metadata."""
    db = MagicMock()
    wo_record = {"id": "wo-1", "metadata": {}}
    # Existence check: select("id").eq(id).eq(yacht_id).single().execute()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = wo_record
    # Metadata fetch: select("metadata").eq(id).single().execute()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = wo_record
    # Update chain
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [wo_record]

    result = await HANDLERS["add_work_order_photo"](
        payload={"work_order_id": "wo-1", "photo_url": "https://example.com/photo.jpg"},
        context={"yacht_id": "y-1", "work_order_id": "wo-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_add_work_order_photo_missing_fields():
    """add_work_order_photo raises 400 when photo_url is absent."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["add_work_order_photo"](
            payload={"work_order_id": "wo-1"},  # missing photo_url
            context={"yacht_id": "y-1"},
            yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_parts_to_work_order_success():
    """add_parts_to_work_order stores part link in WO metadata."""
    db = MagicMock()
    wo_record = {"id": "wo-1", "metadata": {}}
    # Existence check: select("id").eq(id).eq(yacht_id).single().execute()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = wo_record
    # Metadata fetch: select("metadata").eq(id).single().execute()
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = wo_record
    # Update chain
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [wo_record]

    result = await HANDLERS["add_parts_to_work_order"](
        payload={"work_order_id": "wo-1", "part_id": "p-1", "quantity": 2},
        context={"yacht_id": "y-1", "work_order_id": "wo-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_add_parts_to_work_order_missing_fields():
    """add_parts_to_work_order raises 400 when part_id is absent."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["add_parts_to_work_order"](
            payload={"work_order_id": "wo-1"},  # missing part_id
            context={"yacht_id": "y-1"},
            yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_all_aliases_registered():
    """Test all aliases that should exist based on the elif chain."""
    expected = [
        "update_work_order", "update_wo",
        "assign_work_order", "assign_wo",
        "close_work_order", "complete_work_order",
        "add_wo_hours", "log_work_hours",
        "add_wo_part", "add_part_to_wo",
        "add_wo_note", "add_note_to_wo",
        "start_work_order", "begin_wo",
        "cancel_work_order", "cancel_wo",
        "create_work_order", "create_wo",
        "list_work_orders",
        "view_work_order_detail", "view_work_order", "get_work_order",
        "view_work_order_checklist",
        "view_worklist",
        "add_worklist_task",
        "export_worklist",
        "view_work_order_history",
        "update_worklist_progress",
        "create_work_order_for_equipment",
        "add_work_order_photo",
        "add_parts_to_work_order",
    ]
    for alias in expected:
        assert alias in HANDLERS, f"Alias '{alias}' not in HANDLERS"
