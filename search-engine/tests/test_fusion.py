"""
Tests for fusion engine
"""
import pytest
from datetime import datetime, timedelta
from services.fusion import (
    calculate_recency_boost,
    calculate_age_penalty,
    deduplicate_results
)


def test_recency_boost_recent():
    """Test recency boost for recent items"""
    data = {
        "detected_at": datetime.now().isoformat()
    }

    boost = calculate_recency_boost(data)

    assert boost >= 0.05  # Should get boost for recent items


def test_recency_boost_old():
    """Test no boost for old items"""
    old_date = (datetime.now() - timedelta(days=200)).isoformat()
    data = {
        "detected_at": old_date
    }

    boost = calculate_recency_boost(data)

    assert boost == 0.0  # No boost for items > 90 days


def test_age_penalty_very_old():
    """Test penalty for very old items"""
    very_old = (datetime.now() - timedelta(days=800)).isoformat()
    data = {
        "created_at": very_old
    }

    penalty = calculate_age_penalty(data)

    assert penalty > 0.0  # Should penalize items > 2 years


def test_deduplicate_results():
    """Test result deduplication"""
    results = [
        {"id": "123", "type": "fault", "similarity": 0.8},
        {"id": "456", "type": "part", "similarity": 0.9},
        {"id": "123", "type": "fault", "similarity": 0.95},  # Duplicate with higher score
    ]

    deduplicated = deduplicate_results(results)

    assert len(deduplicated) == 2
    # Should keep the higher-scoring duplicate
    fault_item = next(r for r in deduplicated if r["id"] == "123")
    assert fault_item["similarity"] == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
