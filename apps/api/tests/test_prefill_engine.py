"""
Tests for prefill_engine.py

Verifies priority mapping and prepare response building.
"""

from common.prefill_engine import map_priority, PRIORITY_SYNONYMS


def test_map_priority_urgent():
    """Test 'urgent' maps to HIGH with high confidence."""
    value, conf = map_priority("urgent")
    assert value == "HIGH"
    assert conf >= 0.85


def test_map_priority_critical():
    """Test 'critical' maps to EMERGENCY with high confidence."""
    value, conf = map_priority("critical")
    assert value == "EMERGENCY"
    assert conf >= 0.85


def test_map_priority_exact_match():
    """Test exact match has higher confidence than fuzzy match."""
    exact_value, exact_conf = map_priority("urgent")
    fuzzy_value, fuzzy_conf = map_priority("  URGENT  ")

    assert exact_value == fuzzy_value == "HIGH"
    assert exact_conf > fuzzy_conf


def test_map_priority_asap():
    """Test 'asap' maps to HIGH."""
    value, conf = map_priority("asap")
    assert value == "HIGH"
    assert conf >= 0.85


def test_map_priority_medium():
    """Test 'medium' and 'normal' map to MEDIUM."""
    value1, conf1 = map_priority("medium")
    value2, conf2 = map_priority("normal")

    assert value1 == value2 == "MEDIUM"
    assert conf1 >= 0.85
    assert conf2 >= 0.85


def test_map_priority_low():
    """Test 'low' and 'minor' map to LOW."""
    value1, conf1 = map_priority("low")
    value2, conf2 = map_priority("minor")

    assert value1 == value2 == "LOW"
    assert conf1 >= 0.85
    assert conf2 >= 0.85


def test_map_priority_unknown():
    """Test unknown priority returns None with 0.0 confidence."""
    value, conf = map_priority("unknown_priority")
    assert value is None
    assert conf == 0.0


def test_map_priority_empty():
    """Test empty priority returns None with 0.0 confidence."""
    value, conf = map_priority("")
    assert value is None
    assert conf == 0.0


def test_map_priority_none():
    """Test None priority returns None with 0.0 confidence."""
    value, conf = map_priority(None)
    assert value is None
    assert conf == 0.0


def test_priority_synonyms_coverage():
    """Test all PRIORITY_SYNONYMS entries are valid."""
    expected_values = {"EMERGENCY", "HIGH", "MEDIUM", "LOW"}

    for synonym, mapped in PRIORITY_SYNONYMS.items():
        assert mapped in expected_values, f"Invalid mapping: {synonym} -> {mapped}"
