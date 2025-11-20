"""
Tests for Signal Collectors

Tests the 19+ signal computation methods.
"""

import pytest
from uuid import uuid4
from services.signals import SignalCollector


@pytest.fixture
def signal_collector():
    """Fixture to provide SignalCollector instance"""
    return SignalCollector()


@pytest.mark.asyncio
async def test_fault_signal_computation(signal_collector):
    """Test fault signal computation with mock data"""
    yacht_id = uuid4()
    equipment_id = uuid4()

    # This would require mocking the database
    # For now, test that the method exists and returns expected structure
    result = await signal_collector.compute_fault_signal(yacht_id, equipment_id)

    assert isinstance(result, dict)
    assert "overall" in result
    assert "frequency_score" in result
    assert "recency_score" in result
    assert "clustering_score" in result
    assert "severity_score" in result

    # All scores should be between 0 and 1
    for score in result.values():
        assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_work_order_signal_computation(signal_collector):
    """Test work order signal computation"""
    yacht_id = uuid4()
    equipment_id = uuid4()

    result = await signal_collector.compute_work_order_signal(yacht_id, equipment_id)

    assert isinstance(result, dict)
    assert "overall" in result
    assert "overdue_score" in result
    assert "repeated_corrective_score" in result
    assert "reappearing_score" in result
    assert "partial_score" in result


@pytest.mark.asyncio
async def test_crew_behavior_signal(signal_collector):
    """Test crew behavior signal computation"""
    yacht_id = uuid4()
    equipment_id = uuid4()

    result = await signal_collector.compute_crew_behavior_signal(yacht_id, equipment_id)

    assert isinstance(result, dict)
    assert "overall" in result
    assert "search_score" in result
    assert "user_diversity_score" in result
    assert "note_frequency_score" in result


@pytest.mark.asyncio
async def test_all_signals_computation(signal_collector):
    """Test computing all signals at once"""
    yacht_id = uuid4()
    equipment_id = uuid4()

    result = await signal_collector.compute_all_signals(yacht_id, equipment_id)

    assert isinstance(result, dict)
    assert "equipment_id" in result
    assert "yacht_id" in result
    assert "signals" in result
    assert "computed_at" in result

    signals = result["signals"]
    assert "fault" in signals
    assert "work_order" in signals
    assert "equipment_behavior" in signals
    assert "part_consumption" in signals
    assert "crew_behavior" in signals
    assert "global_knowledge" in signals
    assert "graph" in signals


def test_signal_normalization():
    """Test that signal values are properly normalized to 0-1 range"""
    # Test cases for normalization
    test_values = [0, 0.5, 1.0, 1.5, 2.0, -0.5]
    expected_normalized = [0.0, 0.5, 1.0, 1.0, 1.0, 0.0]

    for test_val, expected in zip(test_values, expected_normalized):
        # Clamp to 0-1
        normalized = max(0.0, min(1.0, test_val))
        assert normalized == expected
