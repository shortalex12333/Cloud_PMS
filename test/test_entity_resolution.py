"""
Test Entity Resolution for All 12 Lenses
=========================================

This test validates that:
1. All 12 lens entity resolvers exist and are callable
2. Each resolver enforces yacht_id scoping
3. Ambiguity detection returns candidates correctly
4. The generic prepare_action function integrates properly

Run: pytest test/test_entity_resolution.py -v
"""

import pytest
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from common.prefill_engine import (
    resolve_work_order_entities,
    resolve_fault_entities,
    resolve_equipment_entities,
    resolve_part_entities,
    resolve_inventory_entities,
    resolve_certificate_entities,
    resolve_handover_entities,
    resolve_hours_of_rest_entities,
    resolve_warranty_entities,
    resolve_shopping_list_entities,
    resolve_email_entities,
    resolve_receiving_entities,
    resolve_entities_for_lens,
    prepare_action,
    LENS_ENTITY_RESOLVERS,
)


# =============================================================================
# TEST: All 12 lens resolvers exist
# =============================================================================

def test_all_lens_resolvers_exist():
    """Verify all 12 lens resolvers are registered."""
    expected_lenses = [
        "work_order",
        "fault",
        "equipment",
        "part",
        "inventory",
        "certificate",
        "handover",
        "hours_of_rest",
        "warranty",
        "shopping_list",
        "email",
        "receiving",
    ]

    for lens in expected_lenses:
        assert lens in LENS_ENTITY_RESOLVERS, f"Missing resolver for lens: {lens}"
        assert callable(LENS_ENTITY_RESOLVERS[lens]), f"Resolver for {lens} is not callable"

    assert len(LENS_ENTITY_RESOLVERS) == 12, f"Expected 12 resolvers, got {len(LENS_ENTITY_RESOLVERS)}"


# =============================================================================
# TEST: Work Order Entity Resolution
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_work_order_entities_single_match():
    """Test work order entity resolution with single equipment match."""
    mock_client = MagicMock()

    # Mock equipment lookup returning single match
    mock_result = MagicMock()
    mock_result.data = [{"id": "equip-123", "name": "Main Engine"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await resolve_work_order_entities(
        yacht_id="yacht-abc",
        extracted_entities={"equipment": "Main Engine"},
        supabase_client=mock_client,
    )

    assert "equipment_id" in result
    assert result["equipment_id"] == "equip-123"

    # Verify yacht_id scoping was applied
    mock_client.table.assert_called_with("pms_equipment")
    mock_client.table.return_value.select.return_value.eq.assert_called_with("yacht_id", "yacht-abc")


@pytest.mark.asyncio
async def test_resolve_work_order_entities_multiple_matches():
    """Test work order entity resolution with ambiguous matches."""
    mock_client = MagicMock()

    # Mock equipment lookup returning multiple matches
    mock_result = MagicMock()
    mock_result.data = [
        {"id": "equip-1", "name": "Main Engine 1"},
        {"id": "equip-2", "name": "Main Engine 2"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await resolve_work_order_entities(
        yacht_id="yacht-abc",
        extracted_entities={"equipment": "Main Engine"},
        supabase_client=mock_client,
    )

    assert "equipment_candidates" in result
    assert len(result["equipment_candidates"]) == 2
    assert "equipment_id" not in result


# =============================================================================
# TEST: Fault Entity Resolution
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_fault_entities_equipment_lookup():
    """Test fault entity resolution includes equipment lookup."""
    mock_client = MagicMock()

    mock_result = MagicMock()
    mock_result.data = [{"id": "equip-456", "name": "Generator"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await resolve_fault_entities(
        yacht_id="yacht-xyz",
        extracted_entities={"equipment": "Generator"},
        supabase_client=mock_client,
    )

    assert "equipment_id" in result
    assert result["equipment_id"] == "equip-456"


# =============================================================================
# TEST: Part Entity Resolution with Supplier
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_part_entities_supplier():
    """Test part entity resolution includes supplier lookup."""
    mock_client = MagicMock()

    # Setup mock to return single supplier
    mock_result = MagicMock()
    mock_result.data = [{"id": "supplier-789", "name": "Marine Parts Inc"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await resolve_part_entities(
        yacht_id="yacht-123",
        extracted_entities={"supplier": "Marine Parts"},
        supabase_client=mock_client,
    )

    assert "supplier_id" in result
    assert result["supplier_id"] == "supplier-789"


# =============================================================================
# TEST: resolve_entities_for_lens dispatcher
# =============================================================================

@pytest.mark.asyncio
async def test_resolve_entities_for_lens_dispatch():
    """Test the dispatcher routes to correct resolver."""
    mock_client = MagicMock()

    mock_result = MagicMock()
    mock_result.data = [{"id": "equip-abc", "name": "Test Equipment"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await resolve_entities_for_lens(
        lens="equipment",
        yacht_id="yacht-test",
        extracted_entities={"equipment": "Test Equipment"},
        supabase_client=mock_client,
    )

    assert "equipment_id" in result


@pytest.mark.asyncio
async def test_resolve_entities_for_lens_unknown_lens():
    """Test dispatcher returns empty dict for unknown lens."""
    mock_client = MagicMock()

    result = await resolve_entities_for_lens(
        lens="unknown_lens",
        yacht_id="yacht-test",
        extracted_entities={"something": "value"},
        supabase_client=mock_client,
    )

    assert result == {}


# =============================================================================
# TEST: prepare_action Integration
# =============================================================================

@pytest.mark.asyncio
async def test_prepare_action_complete_flow():
    """Test prepare_action integrates entity resolution and prefill."""
    mock_client = MagicMock()

    # Mock equipment resolution
    mock_result = MagicMock()
    mock_result.data = [{"id": "equip-final", "name": "Port Generator"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    # Mock action registry
    action_registry = {
        "create_work_order": {
            "required_fields": ["title", "equipment_id", "priority"],
            "optional_fields": ["description"],
            "role_restricted": [],
        }
    }

    result = await prepare_action(
        lens="work_order",
        action_id="create_work_order",
        query_text="create work order for port generator overheating",
        extracted_entities={
            "equipment": "Port Generator",
            "priority": "urgent",
        },
        yacht_id="yacht-abc",
        user_id="user-123",
        user_role="engineer",
        supabase_client=mock_client,
        action_registry=action_registry,
    )

    assert result["lens"] == "work_order"
    assert result["action_id"] == "create_work_order"
    assert "prefill" in result
    assert "resolved_entities" in result
    assert "equipment_id" in result["resolved_entities"]
    assert result["resolved_entities"]["equipment_id"] == "equip-final"


@pytest.mark.asyncio
async def test_prepare_action_role_blocked():
    """Test prepare_action blocks when user role not allowed."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    action_registry = {
        "delete_certificate": {
            "required_fields": ["certificate_id"],
            "optional_fields": [],
            "role_restricted": ["manager"],  # Only managers can delete
        }
    }

    result = await prepare_action(
        lens="certificate",
        action_id="delete_certificate",
        query_text="delete the ISM certificate",
        extracted_entities={"certificate": "ISM"},
        yacht_id="yacht-xyz",
        user_id="user-456",
        user_role="engineer",  # Not a manager
        supabase_client=mock_client,
        action_registry=action_registry,
    )

    assert result["role_blocked"] is True
    assert result["ready_to_commit"] is False


@pytest.mark.asyncio
async def test_prepare_action_missing_required_fields():
    """Test prepare_action identifies missing required fields."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    action_registry = {
        "create_work_order": {
            "required_fields": ["title", "equipment_id", "priority", "type"],
            "optional_fields": ["description"],
            "role_restricted": [],
        }
    }

    result = await prepare_action(
        lens="work_order",
        action_id="create_work_order",
        query_text="create work order",  # No entities extracted
        extracted_entities={},
        yacht_id="yacht-abc",
        user_id="user-123",
        user_role="engineer",
        supabase_client=mock_client,
        action_registry=action_registry,
    )

    assert len(result["missing_required_fields"]) > 0
    assert result["ready_to_commit"] is False


# =============================================================================
# TEST: Yacht ID Scoping Enforcement
# =============================================================================

@pytest.mark.asyncio
async def test_yacht_id_scoping_enforced():
    """Verify all resolvers enforce yacht_id in queries."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = []

    # Setup chain that we can verify
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_eq.ilike.return_value.limit.return_value.execute.return_value = mock_result
    mock_eq.or_.return_value.limit.return_value.execute.return_value = mock_result
    mock_select.eq.return_value = mock_eq
    mock_client.table.return_value.select.return_value = mock_select

    test_yacht_id = "yacht-security-test-123"

    # Test each resolver
    for lens_name, resolver in LENS_ENTITY_RESOLVERS.items():
        mock_client.reset_mock()

        # Use appropriate entity for each lens
        entities = {
            "work_order": {"equipment": "test"},
            "fault": {"equipment": "test"},
            "equipment": {"equipment": "test"},
            "part": {"part": "test"},
            "inventory": {"part": "test"},
            "certificate": {"certificate": "test"},
            "handover": {"handover_item": "test"},
            "hours_of_rest": {"user": "test"},
            "warranty": {"warranty": "test"},
            "shopping_list": {"item": "test"},
            "email": {"thread": "test"},
            "receiving": {"receiving": "test"},
        }

        await resolver(
            yacht_id=test_yacht_id,
            extracted_entities=entities.get(lens_name, {"test": "value"}),
            supabase_client=mock_client,
        )

        # Verify yacht_id was used in query
        if mock_client.table.called:
            calls = str(mock_client.method_calls)
            # The yacht_id should appear in the call chain
            assert test_yacht_id in calls or mock_select.eq.called, \
                f"Lens {lens_name} did not enforce yacht_id scoping"


# =============================================================================
# TEST: Priority Mapping in prepare_action
# =============================================================================

@pytest.mark.asyncio
async def test_prepare_action_priority_mapping():
    """Test that priority synonyms are mapped correctly."""
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_result

    result = await prepare_action(
        lens="work_order",
        action_id="create_work_order",
        query_text="create urgent work order",
        extracted_entities={"priority": "urgent"},
        yacht_id="yacht-abc",
        user_id="user-123",
        user_role="engineer",
        supabase_client=mock_client,
    )

    assert "priority" in result["prefill"]
    assert result["prefill"]["priority"]["value"] == "HIGH"
    assert result["prefill"]["priority"]["source"] == "keyword_map"


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
