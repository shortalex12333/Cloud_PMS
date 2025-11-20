"""
Tests for Risk Scoring Engine

Tests the weighted risk score calculation and trend detection.
"""

import pytest
from services.scoring import RiskScorer


@pytest.fixture
def scorer():
    """Fixture to provide RiskScorer instance"""
    return RiskScorer()


def test_risk_score_calculation(scorer):
    """Test risk score calculation with known signal values"""
    mock_signals = {
        "signals": {
            "fault": {"overall": 0.8},
            "work_order": {"overall": 0.6},
            "crew_behavior": {"overall": 0.4},
            "part_consumption": {"overall": 0.5},
            "global_knowledge": {"overall": 0.3}
        }
    }

    risk_score = scorer.calculate_risk_score(mock_signals)

    # Expected: 0.35*0.8 + 0.25*0.6 + 0.15*0.4 + 0.15*0.5 + 0.10*0.3
    #         = 0.28 + 0.15 + 0.06 + 0.075 + 0.03 = 0.595
    expected = 0.595
    assert abs(risk_score - expected) < 0.01

    # Score should be in valid range
    assert 0.0 <= risk_score <= 1.0


def test_risk_score_all_zeros(scorer):
    """Test risk score when all signals are zero"""
    mock_signals = {
        "signals": {
            "fault": {"overall": 0.0},
            "work_order": {"overall": 0.0},
            "crew_behavior": {"overall": 0.0},
            "part_consumption": {"overall": 0.0},
            "global_knowledge": {"overall": 0.0}
        }
    }

    risk_score = scorer.calculate_risk_score(mock_signals)
    assert risk_score == 0.0


def test_risk_score_all_max(scorer):
    """Test risk score when all signals are at maximum"""
    mock_signals = {
        "signals": {
            "fault": {"overall": 1.0},
            "work_order": {"overall": 1.0},
            "crew_behavior": {"overall": 1.0},
            "part_consumption": {"overall": 1.0},
            "global_knowledge": {"overall": 1.0}
        }
    }

    risk_score = scorer.calculate_risk_score(mock_signals)
    assert risk_score == 1.0


def test_risk_category_classification(scorer):
    """Test risk category classification"""
    assert scorer.get_risk_category(0.2) == "normal"
    assert scorer.get_risk_category(0.5) == "monitor"
    assert scorer.get_risk_category(0.65) == "emerging"
    assert scorer.get_risk_category(0.85) == "high"
    assert scorer.get_risk_category(1.0) == "high"


def test_trend_calculation(scorer):
    """Test trend calculation logic"""
    # Improving trend
    assert scorer.calculate_trend(0.3, 0.5) == "↓"

    # Worsening trend
    assert scorer.calculate_trend(0.7, 0.5) == "↑"

    # Stable trend
    assert scorer.calculate_trend(0.5, 0.52) == "→"

    # First calculation (no previous)
    assert scorer.calculate_trend(0.5, None) == "→"


def test_signal_weights_sum_to_one(scorer):
    """Test that signal weights sum to 1.0"""
    total_weight = sum(scorer.WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.001


def test_contributing_factors_extraction(scorer):
    """Test extraction of contributing factors from signals"""
    mock_signals = {
        "signals": {
            "fault": {
                "overall": 0.7,
                "frequency_score": 0.8,
                "clustering_score": 0.7,
                "severity_score": 0.6
            },
            "work_order": {
                "overall": 0.6,
                "overdue_score": 0.7
            },
            "crew_behavior": {
                "overall": 0.5,
                "search_score": 0.6
            },
            "equipment_behavior": {
                "overall": 0.4
            },
            "part_consumption": {
                "overall": 0.3
            },
            "global_knowledge": {
                "overall": 0.2
            }
        }
    }

    factors = scorer.get_contributing_factors(mock_signals)

    assert isinstance(factors, list)
    assert len(factors) > 0
    assert any("fault" in f.lower() for f in factors)
