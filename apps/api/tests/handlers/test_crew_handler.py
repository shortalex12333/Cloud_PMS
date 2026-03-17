"""
Unit tests for crew_handler.py — migrated from p0_actions_routes.py elif blocks.
Tests import from routes.handlers.crew_handler which must exist for tests to pass.

All crew handlers delegate to HoursOfRestHandlers class — tested for registry,
contract compliance, and delegation correctness.
"""
import inspect
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from routes.handlers.crew_handler import HANDLERS


# ============================================================================
# HELPERS
# ============================================================================

def base_ctx():
    return {"yacht_id": "y-1"}


def base_uc():
    return {"role": "captain", "tenant_key_alias": "y85fe1119", "department": "deck"}


# ============================================================================
# REGISTRY COMPLETENESS
# ============================================================================

def test_all_crew_actions_registered():
    expected = [
        "create_crew_template",
        "apply_crew_template",
        "list_crew_templates",
        "list_crew_warnings",
        "acknowledge_warning",
        "dismiss_warning",
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
# DELEGATION: crew template actions
# ============================================================================

@pytest.mark.asyncio
async def test_create_crew_template_delegates():
    mock_result = {"status": "success", "template_id": "t-new"}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.create_crew_template = AsyncMock(return_value=mock_result)

        result = await HANDLERS["create_crew_template"](
            payload={"name": "Standard Watch"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.create_crew_template.assert_awaited_once()
        # Verify entity_id=user_id and user_id=user_id
        call_kwargs = instance.create_crew_template.await_args.kwargs
        assert call_kwargs["entity_id"] == "u-1"
        assert call_kwargs["user_id"] == "u-1"


@pytest.mark.asyncio
async def test_apply_crew_template_delegates():
    mock_result = {"status": "success", "message": "Template applied"}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.apply_crew_template = AsyncMock(return_value=mock_result)

        result = await HANDLERS["apply_crew_template"](
            payload={"template_id": "t-1", "week_start": "2026-03-17"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.apply_crew_template.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_crew_templates_delegates():
    mock_result = {"status": "success", "templates": []}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.list_crew_templates = AsyncMock(return_value=mock_result)

        result = await HANDLERS["list_crew_templates"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.list_crew_templates.assert_awaited_once()
        # list is a READ action — no user_id param, uses params=
        call_kwargs = instance.list_crew_templates.await_args.kwargs
        assert "params" in call_kwargs


# ============================================================================
# DELEGATION: crew warning actions
# ============================================================================

@pytest.mark.asyncio
async def test_list_crew_warnings_delegates():
    mock_result = {"status": "success", "warnings": []}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.list_crew_warnings = AsyncMock(return_value=mock_result)

        result = await HANDLERS["list_crew_warnings"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.list_crew_warnings.assert_awaited_once()
        # entity_id should be user_id for list
        call_kwargs = instance.list_crew_warnings.await_args.kwargs
        assert call_kwargs["entity_id"] == "u-1"


@pytest.mark.asyncio
async def test_acknowledge_warning_delegates():
    mock_result = {"status": "success", "message": "Acknowledged"}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.acknowledge_warning = AsyncMock(return_value=mock_result)

        result = await HANDLERS["acknowledge_warning"](
            payload={"warning_id": "w-1"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.acknowledge_warning.assert_awaited_once()
        # entity_id should be warning_id from payload
        call_kwargs = instance.acknowledge_warning.await_args.kwargs
        assert call_kwargs["entity_id"] == "w-1"


@pytest.mark.asyncio
async def test_dismiss_warning_delegates():
    mock_result = {"status": "success", "message": "Dismissed"}
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.dismiss_warning = AsyncMock(return_value=mock_result)

        result = await HANDLERS["dismiss_warning"](
            payload={"warning_id": "w-2"},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=MagicMock(),
        )
        assert result == mock_result
        instance.dismiss_warning.assert_awaited_once()
        call_kwargs = instance.dismiss_warning.await_args.kwargs
        assert call_kwargs["entity_id"] == "w-2"


# ============================================================================
# DB CLIENT PASSTHROUGH
# ============================================================================

@pytest.mark.asyncio
async def test_db_client_passed_to_hor_constructor():
    """Verify the db_client from dispatcher is passed to HoursOfRestHandlers constructor."""
    sentinel_db = MagicMock(name="sentinel_db")
    with patch("routes.handlers.crew_handler.HoursOfRestHandlers") as MockCls:
        instance = MockCls.return_value
        instance.list_crew_templates = AsyncMock(return_value={"status": "success"})

        await HANDLERS["list_crew_templates"](
            payload={},
            context=base_ctx(), yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=sentinel_db,
        )
        MockCls.assert_called_once_with(sentinel_db)
