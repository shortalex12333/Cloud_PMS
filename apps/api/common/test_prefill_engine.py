"""
CelesteOS - Prefill Engine Unit Tests
======================================

Unit tests for the prefill engine components.

Run with:
    pytest apps/api/common/test_prefill_engine.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from common.field_metadata import FieldMetadata, LookupResult
from common.prefill_engine import (
    extract_entity_value,
    apply_compose_template,
    apply_value_map,
    generate_backend_auto_value,
    build_mutation_preview,
)


# =============================================================================
# TEST ENTITY EXTRACTION
# =============================================================================

def test_extract_entity_value_exact_match():
    """Test extracting entity with exact match."""
    entities = {"equipment": "main engine"}
    result = extract_entity_value("equipment", entities)
    assert result == "main engine"


def test_extract_entity_value_alias_match():
    """Test extracting entity with alias match."""
    entities = {"equipment_name": "main engine"}
    result = extract_entity_value("equipment", entities)
    assert result == "main engine"


def test_extract_entity_value_query_text():
    """Test extracting query_text."""
    result = extract_entity_value("query_text", {}, "test query")
    assert result == "test query"


def test_extract_entity_value_missing():
    """Test extracting missing entity returns None."""
    result = extract_entity_value("nonexistent", {})
    assert result is None


# =============================================================================
# TEST COMPOSE TEMPLATES
# =============================================================================

def test_apply_compose_template_simple():
    """Test simple compose template."""
    template = "{equipment} - {symptom}"
    entities = {"equipment": "main engine", "symptom": "overheating"}
    result = apply_compose_template(template, entities)
    assert result == "main engine - overheating"


def test_apply_compose_template_missing_entity():
    """Test compose template with missing entity keeps placeholder."""
    template = "{equipment} - {symptom}"
    entities = {"equipment": "main engine"}
    result = apply_compose_template(template, entities)
    assert result == "main engine - {symptom}"


def test_apply_compose_template_multiple_same_placeholder():
    """Test compose template with repeated placeholder."""
    template = "{equipment} ({equipment})"
    entities = {"equipment": "main engine"}
    result = apply_compose_template(template, entities)
    assert result == "main engine (main engine)"


# =============================================================================
# TEST VALUE MAPPING
# =============================================================================

def test_apply_value_map_exact_match():
    """Test value mapping with exact match."""
    value_map = {"urgent": "critical", "high": "high"}
    result = apply_value_map("urgent", value_map)
    assert result == "critical"


def test_apply_value_map_case_insensitive():
    """Test value mapping is case-insensitive."""
    value_map = {"urgent": "critical"}
    result = apply_value_map("URGENT", value_map)
    assert result == "critical"


def test_apply_value_map_no_match():
    """Test value mapping with no match returns original."""
    value_map = {"urgent": "critical"}
    result = apply_value_map("medium", value_map)
    assert result == "medium"


def test_apply_value_map_none_value():
    """Test value mapping with None returns None."""
    value_map = {"urgent": "critical"}
    result = apply_value_map(None, value_map)
    assert result is None


# =============================================================================
# TEST BACKEND AUTO VALUES
# =============================================================================

def test_generate_backend_auto_value_uuid():
    """Test generating UUID for id field."""
    metadata = FieldMetadata(name="id", classification="BACKEND_AUTO")
    result = generate_backend_auto_value("id", metadata, "yacht-123")
    assert result is not None
    assert len(result) == 36  # UUID format


def test_generate_backend_auto_value_yacht_id():
    """Test generating yacht_id returns context yacht_id."""
    metadata = FieldMetadata(name="yacht_id", classification="BACKEND_AUTO")
    result = generate_backend_auto_value("yacht_id", metadata, "yacht-123")
    assert result == "yacht-123"


def test_generate_backend_auto_value_user_id():
    """Test generating user_id returns context user_id."""
    metadata = FieldMetadata(name="user_id", classification="BACKEND_AUTO")
    result = generate_backend_auto_value("user_id", metadata, "yacht-123", "user-456")
    assert result == "user-456"


def test_generate_backend_auto_value_timestamp():
    """Test generating timestamp for created_at field."""
    metadata = FieldMetadata(name="created_at", classification="BACKEND_AUTO")
    result = generate_backend_auto_value("created_at", metadata, "yacht-123")
    assert result is not None
    assert "T" in result  # ISO format


# =============================================================================
# TEST BUILD MUTATION PREVIEW
# =============================================================================

@pytest.mark.asyncio
async def test_build_mutation_preview_simple():
    """Test building simple mutation preview without lookups."""
    field_metadata = {
        "yacht_id": FieldMetadata(
            name="yacht_id",
            classification="CONTEXT",
        ),
        "title": FieldMetadata(
            name="title",
            classification="REQUIRED",
            auto_populate_from="query_text",
        ),
        "priority": FieldMetadata(
            name="priority",
            classification="OPTIONAL",
            default="medium",
        ),
    }

    extracted_entities = {}

    preview = await build_mutation_preview(
        query_text="test query",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=Mock(),
        user_id="user-456",
    )

    assert preview["mutation_preview"]["yacht_id"] == "yacht-123"
    assert preview["mutation_preview"]["title"] == "test query"
    assert preview["mutation_preview"]["priority"] == "medium"
    assert preview["ready_to_commit"] == True
    assert len(preview["missing_required"]) == 0


@pytest.mark.asyncio
async def test_build_mutation_preview_with_compose_template():
    """Test building mutation preview with compose template."""
    field_metadata = {
        "title": FieldMetadata(
            name="title",
            classification="BACKEND_AUTO",
            auto_populate_from="equipment",
            compose_template="{equipment} - {symptom}",
        ),
    }

    extracted_entities = {
        "equipment": "main engine",
        "symptom": "overheating",
    }

    preview = await build_mutation_preview(
        query_text="test",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=Mock(),
    )

    assert preview["mutation_preview"]["title"] == "main engine - overheating"


@pytest.mark.asyncio
async def test_build_mutation_preview_with_value_map():
    """Test building mutation preview with value mapping."""
    field_metadata = {
        "priority": FieldMetadata(
            name="priority",
            classification="OPTIONAL",
            auto_populate_from="query_text",
            value_map={"urgent": "critical"},
        ),
    }

    extracted_entities = {"priority": "urgent"}

    preview = await build_mutation_preview(
        query_text="urgent",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=Mock(),
    )

    assert preview["mutation_preview"]["priority"] == "critical"


@pytest.mark.asyncio
async def test_build_mutation_preview_missing_required():
    """Test building mutation preview with missing required field."""
    field_metadata = {
        "equipment_id": FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
        ),
    }

    extracted_entities = {}  # No equipment entity

    preview = await build_mutation_preview(
        query_text="test",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=Mock(),
    )

    assert "equipment_id" in preview["missing_required"]
    assert preview["ready_to_commit"] == False


@pytest.mark.asyncio
async def test_build_mutation_preview_with_lookup_single_match():
    """Test building mutation preview with lookup (single match)."""
    field_metadata = {
        "equipment_id": FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
    }

    extracted_entities = {"equipment": "main engine"}

    # Mock lookup to return single match
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [{"id": "equipment-uuid-123", "name": "main engine"}]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value = mock_response

    preview = await build_mutation_preview(
        query_text="test",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=mock_client,
    )

    assert preview["mutation_preview"]["equipment_id"] == "equipment-uuid-123"
    assert preview["ready_to_commit"] == True


@pytest.mark.asyncio
async def test_build_mutation_preview_with_lookup_multiple_matches():
    """Test building mutation preview with lookup (ambiguous)."""
    field_metadata = {
        "equipment_id": FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
    }

    extracted_entities = {"equipment": "engine"}

    # Mock lookup to return multiple matches
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = [
        {"id": "eq-1", "name": "main engine", "category": "propulsion"},
        {"id": "eq-2", "name": "auxiliary engine", "category": "power"},
    ]
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value = mock_response

    preview = await build_mutation_preview(
        query_text="test",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=mock_client,
    )

    assert "equipment_id" not in preview["mutation_preview"]
    assert "equipment_id" in preview["dropdown_options"]
    assert len(preview["dropdown_options"]["equipment_id"]) == 2
    assert preview["ready_to_commit"] == False
    assert any("Ambiguous" in w for w in preview["warnings"])


@pytest.mark.asyncio
async def test_build_mutation_preview_with_lookup_no_match():
    """Test building mutation preview with lookup (no match)."""
    field_metadata = {
        "equipment_id": FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
    }

    extracted_entities = {"equipment": "nonexistent"}

    # Mock lookup to return no matches
    mock_client = Mock()
    mock_response = Mock()
    mock_response.data = []
    mock_client.table.return_value.select.return_value.eq.return_value.ilike.return_value.execute.return_value = mock_response

    preview = await build_mutation_preview(
        query_text="test",
        extracted_entities=extracted_entities,
        field_metadata=field_metadata,
        yacht_id="yacht-123",
        supabase_client=mock_client,
    )

    assert "equipment_id" in preview["missing_required"]
    assert preview["ready_to_commit"] == False
    assert any("No match found" in w for w in preview["warnings"])


# =============================================================================
# TEST FIELD METADATA VALIDATION
# =============================================================================

def test_field_metadata_validation_lookup_requires_auto_populate():
    """Test that lookup_required=True requires auto_populate_from."""
    with pytest.raises(ValueError, match="lookup_required=True requires auto_populate_from"):
        FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            lookup_required=True,
            # Missing auto_populate_from
        )


def test_field_metadata_validation_compose_template_requires_auto_populate():
    """Test that compose_template requires auto_populate_from."""
    with pytest.raises(ValueError, match="compose_template requires auto_populate_from"):
        FieldMetadata(
            name="title",
            classification="BACKEND_AUTO",
            compose_template="{equipment}",
            # Missing auto_populate_from
        )


def test_field_metadata_validation_backend_auto_requires_source():
    """Test that BACKEND_AUTO requires auto_populate_from or default."""
    with pytest.raises(ValueError, match="BACKEND_AUTO requires auto_populate_from or default"):
        FieldMetadata(
            name="unknown_field",
            classification="BACKEND_AUTO",
            # Missing both auto_populate_from and default
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
