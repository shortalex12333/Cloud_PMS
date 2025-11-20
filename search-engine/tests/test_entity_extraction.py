"""
Tests for entity extraction module
"""
import pytest
from services.entity_extraction import extract_entities, normalize_entity


def test_extract_fault_codes():
    """Test fault code extraction"""
    query = "main engine showing fault code E047"

    result = extract_entities(query)

    assert len(result.fault_codes) > 0
    assert "e047" in [fc.lower() for fc in result.fault_codes]
    assert result.confidence.get("fault_codes") == 1.0


def test_extract_equipment():
    """Test equipment extraction"""
    query = "starboard generator coolant leak"

    result = extract_entities(query)

    assert len(result.equipment) > 0
    # Should match "starboard generator" or "generator"
    equipment_lower = [e.lower() for e in result.equipment]
    assert any("generator" in e for e in equipment_lower)


def test_extract_part_numbers():
    """Test part number extraction"""
    query = "need to order part 2040N2 for the filter"

    result = extract_entities(query)

    assert len(result.part_numbers) > 0
    assert "2040n2" in [pn.lower() for pn in result.part_numbers]


def test_extract_action_words():
    """Test action word extraction"""
    query = "fix the stabiliser pump leak"

    result = extract_entities(query)

    assert len(result.action_words) > 0
    assert "fix" in result.action_words


def test_extract_document_types():
    """Test document type extraction"""
    query = "find the CAT 3516 manual"

    result = extract_entities(query)

    assert len(result.document_types) > 0
    assert "manual" in result.document_types


def test_extract_location():
    """Test location extraction"""
    query = "leak in the engine room"

    result = extract_entities(query)

    assert result.location is not None
    assert "engine" in result.location.lower()


def test_normalize_fault_code():
    """Test fault code normalization"""
    assert normalize_entity("E 047", "fault_code") == "E047"
    assert normalize_entity("e047", "fault_code") == "E047"


def test_complex_query():
    """Test complex query with multiple entities"""
    query = "fault code E047 on main engine, need to create work order and find manual"

    result = extract_entities(query)

    # Should extract multiple entity types
    assert len(result.fault_codes) > 0
    assert len(result.equipment) > 0 or len(result.system_names) > 0
    assert len(result.action_words) > 0
    assert len(result.document_types) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
