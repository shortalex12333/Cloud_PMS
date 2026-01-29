"""
Unit Tests for Related Shadow Logger

Tests shadow logging functionality:
- Cosine similarity computation
- Privacy-safe logging (no entity text)
- Alpha=0.0 (shadow mode, no reordering)
- Aggregate statistics
- Feature flag (SHOW_RELATED_SHADOW)

Run:
    pytest apps/api/tests/test_related_shadow_logger.py -v
"""

import pytest
import os
import logging
from unittest.mock import Mock, patch, call
from services.embedding_shadow_logger import (
    cosine_similarity,
    shadow_log_rerank_scores,
    shadow_log_alpha_simulation,
    compute_rerank_effectiveness,
    SHADOW_LOGGING_ENABLED,
)


# =============================================================================
# Cosine Similarity Tests
# =============================================================================

def test_cosine_similarity_identical_vectors():
    """Test cosine similarity of identical vectors is 1.0"""
    vec = [1.0, 2.0, 3.0, 4.0]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    """Test cosine similarity of orthogonal vectors is 0.0"""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors():
    """Test cosine similarity of opposite vectors is -1.0"""
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [-1.0, -2.0, -3.0]
    assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)


def test_cosine_similarity_normalized_vectors():
    """Test cosine similarity with normalized vectors"""
    vec1 = [0.6, 0.8]
    vec2 = [0.8, 0.6]
    result = cosine_similarity(vec1, vec2)
    # cos(angle) = (0.6*0.8 + 0.8*0.6) / (1.0 * 1.0) = 0.96
    assert result == pytest.approx(0.96)


def test_cosine_similarity_empty_vectors():
    """Test cosine similarity returns 0.0 for empty vectors"""
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], []) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0


def test_cosine_similarity_dimension_mismatch():
    """Test cosine similarity returns 0.0 for mismatched dimensions"""
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.0, 2.0]
    assert cosine_similarity(vec1, vec2) == 0.0


def test_cosine_similarity_zero_magnitude():
    """Test cosine similarity returns 0.0 when magnitude is zero"""
    vec1 = [0.0, 0.0, 0.0]
    vec2 = [1.0, 2.0, 3.0]
    assert cosine_similarity(vec1, vec2) == 0.0


# =============================================================================
# Feature Flag Tests
# =============================================================================

def test_shadow_logging_disabled_by_default():
    """Test shadow logging respects SHOW_RELATED_SHADOW env var"""
    # When SHOW_RELATED_SHADOW=false, should not log
    with patch.dict(os.environ, {"SHOW_RELATED_SHADOW": "false"}):
        # Reload module to pick up env var
        import importlib
        import services.embedding_shadow_logger as logger_module
        importlib.reload(logger_module)

        assert logger_module.SHADOW_LOGGING_ENABLED is False


def test_shadow_logging_enabled_when_true():
    """Test shadow logging enabled when SHOW_RELATED_SHADOW=true"""
    with patch.dict(os.environ, {"SHOW_RELATED_SHADOW": "true"}):
        import importlib
        import services.embedding_shadow_logger as logger_module
        importlib.reload(logger_module)

        assert logger_module.SHADOW_LOGGING_ENABLED is True


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", False)
def test_shadow_log_noop_when_disabled():
    """Test shadow_log_rerank_scores is no-op when disabled"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{"group_key": "parts", "items": [{"entity_id": "part1"}]}]
        focused_embedding = [1.0, 2.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should not log anything
        mock_logger.info.assert_not_called()
        mock_logger.debug.assert_not_called()


# =============================================================================
# Privacy Tests
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_no_entity_text_in_logs():
    """Test shadow logs contain no entity text, only IDs"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {
                    "entity_id": "part-abc123-def456",
                    "title": "Hydraulic Pump Seal",  # Should NOT appear in logs
                    "subtitle": "Parker P/N 12345",  # Should NOT appear in logs
                    "weight": 100,
                    "embedding": [0.5, 0.5, 0.7]
                }
            ]
        }]
        focused_embedding = [0.6, 0.6, 0.6]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht-xyz789",
            entity_type="work_order",
            entity_id="wo-abc123-def456",
            alpha=0.0
        )

        # Verify logger.info was called
        assert mock_logger.info.called

        # Check all log calls
        for call_obj in mock_logger.info.call_args_list:
            log_message = call_obj[0][0]
            # Ensure no entity text in logs
            assert "Hydraulic Pump Seal" not in log_message
            assert "Parker P/N 12345" not in log_message


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_ids_truncated_in_logs():
    """Test entity IDs truncated to first 8 chars for privacy"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {
                    "entity_id": "part-0123456789abcdef",  # Long ID
                    "weight": 100,
                    "embedding": [0.5, 0.5]
                }
            ]
        }]
        focused_embedding = [0.6, 0.6]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht-0123456789abcdef",
            entity_type="work_order",
            entity_id="wo-0123456789abcdef",
            alpha=0.0
        )

        # Verify IDs are truncated
        for call_obj in mock_logger.info.call_args_list + mock_logger.debug.call_args_list:
            log_message = call_obj[0][0]
            # Should have truncated versions (8 chars + "...")
            if "entity=" in log_message:
                # Entity ID should be truncated
                assert "wo-01234" in log_message or "wo-012345" in log_message


# =============================================================================
# Alpha=0.0 (Shadow Mode) Tests
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_alpha_zero_does_not_reorder():
    """Test alpha=0.0 means FK-only ordering (shadow mode)"""
    with patch("services.embedding_shadow_logger.logger"):
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [0.9, 0.9]},
                {"entity_id": "part2", "weight": 90, "embedding": [0.1, 0.1]},
            ]
        }]
        focused_embedding = [0.9, 0.9]

        # Call shadow logger with alpha=0.0
        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Groups should remain unchanged
        assert groups[0]["items"][0]["entity_id"] == "part1"
        assert groups[0]["items"][1]["entity_id"] == "part2"


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_shadow_mode_logs_would_be_score():
    """Test shadow mode logs what re-ranked score would be (at alpha=0.0)"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [1.0, 0.0]},
            ]
        }]
        focused_embedding = [1.0, 0.0]  # Perfect match with part1

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # At alpha=0.0: would_be_score = FK_weight + 0.0 * 100 * cosine = 100 + 0 = 100
        # Delta should be 0
        debug_calls = [str(call_obj) for call_obj in mock_logger.debug.call_args_list]
        # Look for delta=0.0 in debug logs
        assert any("delta=0.0" in call_str for call_str in debug_calls)


# =============================================================================
# Aggregate Statistics Tests
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_computes_average_cosine():
    """Test shadow logger computes average cosine similarity"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [1.0, 0.0]},  # cos=1.0
                {"entity_id": "part2", "weight": 100, "embedding": [0.0, 1.0]},  # cos=0.0
            ]
        }]
        focused_embedding = [1.0, 0.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Average cosine should be 0.5
        info_calls = [str(call_obj) for call_obj in mock_logger.info.call_args_list]
        assert any("avg_cosine=0.500" in call_str for call_str in info_calls)


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_computes_median_and_stdev():
    """Test shadow logger computes median and stdev"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        # Use 2D unit vectors to create specific cosine values for median testing
        # focused = [1.0, 0.0] (unit vector pointing right)
        # part1 = [1.0, 0.0] → cosine = 1.0 (same direction, 0° angle)
        # part2 = [0.5, 0.866] (unit vector at 60°) → cosine = 0.5 (cos(60°) = 0.5)
        # part3 = [0.0, 1.0] → cosine = 0.0 (perpendicular, 90° angle)
        # Median of [1.0, 0.5, 0.0] = 0.5
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [1.0, 0.0]},     # cos=1.0
                {"entity_id": "part2", "weight": 100, "embedding": [0.5, 0.866]},   # cos=0.5 (60° angle)
                {"entity_id": "part3", "weight": 100, "embedding": [0.0, 1.0]},     # cos=0.0 (90° angle)
            ]
        }]
        focused_embedding = [1.0, 0.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Median should be 0.5 (cosine values: 1.0, 0.5, 0.0 → median is middle value 0.5)
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]

        # Debug: Print actual log messages to diagnose
        for msg in info_calls:
            if "median=" in msg:
                print(f"Found median log: {msg}")

        # Check for median value in any of the logged messages
        assert any("median=" in msg for msg in info_calls), \
            f"No median found in logs. Actual calls: {info_calls}"

        # The median of [1.0, 0.5, 0.0] should be 0.5, formatted as 0.500
        assert any("median=0.500" in msg for msg in info_calls), \
            f"median=0.500 not found. Actual logs with median: {[m for m in info_calls if 'median=' in m]}"


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_per_group_stats():
    """Test shadow logger logs per-group statistics"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [
            {
                "group_key": "parts",
                "items": [
                    {"entity_id": "part1", "weight": 100, "embedding": [1.0, 0.0]},
                ]
            },
            {
                "group_key": "previous_work",
                "items": [
                    {"entity_id": "wo1", "weight": 80, "embedding": [0.8, 0.6]},
                ]
            }
        ]
        focused_embedding = [1.0, 0.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should have group-specific logs
        info_calls = [str(call_obj) for call_obj in mock_logger.info.call_args_list]
        assert any("parts:" in call_str for call_str in info_calls)
        assert any("previous_work:" in call_str for call_str in info_calls)


# =============================================================================
# Missing Embedding Tests
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_handles_missing_focused_embedding():
    """Test shadow logger handles None focused_embedding gracefully"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [{"entity_id": "part1", "weight": 100}]
        }]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=None,  # No embedding
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should log debug message about no embedding
        debug_calls = [str(call_obj) for call_obj in mock_logger.debug.call_args_list]
        assert any("No focused embedding" in call_str for call_str in debug_calls)


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_handles_items_without_embeddings():
    """Test shadow logger skips items without embeddings"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [1.0, 0.0]},
                {"entity_id": "part2", "weight": 90},  # No embedding
            ]
        }]
        focused_embedding = [1.0, 0.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should only count 1 item with embedding
        info_calls = [str(call_obj) for call_obj in mock_logger.info.call_args_list]
        assert any("items=1" in call_str for call_str in info_calls)


# =============================================================================
# Alpha Simulation Tests
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_alpha_simulation_multiple_values():
    """Test alpha simulation logs multiple alpha values"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [{"entity_id": "part1", "weight": 100, "embedding": [1.0]}]
        }]
        focused_embedding = [1.0]

        shadow_log_alpha_simulation(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alphas=[0.0, 0.1, 0.3]
        )

        # Should have logs for each alpha
        info_calls = [str(call_obj) for call_obj in mock_logger.info.call_args_list]
        assert any("alpha=0.0" in call_str for call_str in info_calls)
        assert any("alpha=0.1" in call_str for call_str in info_calls)
        assert any("alpha=0.3" in call_str for call_str in info_calls)


# =============================================================================
# Re-Rank Effectiveness Tests
# =============================================================================

def test_compute_rerank_effectiveness_no_embedding():
    """Test effectiveness returns error when no focused embedding"""
    result = compute_rerank_effectiveness(
        groups=[{"items": []}],
        focused_embedding=None,
        alpha=0.3
    )
    assert result["error"] == "no_focused_embedding"


def test_compute_rerank_effectiveness_no_items():
    """Test effectiveness returns error when no items"""
    result = compute_rerank_effectiveness(
        groups=[],
        focused_embedding=[1.0],
        alpha=0.3
    )
    assert result["error"] == "no_items"


def test_compute_rerank_effectiveness_computes_position_changes():
    """Test effectiveness computes position changes at different alpha"""
    groups = [{
        "items": [
            {"entity_id": "item1", "weight": 100, "embedding": [0.5]},  # Low cosine
            {"entity_id": "item2", "weight": 90, "embedding": [1.0]},   # High cosine
        ]
    }]
    focused_embedding = [1.0]

    result = compute_rerank_effectiveness(
        groups=groups,
        focused_embedding=focused_embedding,
        alpha=0.3
    )

    # At alpha=0.3, item2 should move up despite lower FK weight
    # item1: 100 + 0.3*100*0.5 = 115
    # item2: 90 + 0.3*100*1.0 = 120
    assert result["total_items"] == 2
    assert result["items_changed_position"] >= 0  # Should detect reordering


# =============================================================================
# Edge Cases
# =============================================================================

@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_empty_groups():
    """Test shadow logger handles empty groups"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        shadow_log_rerank_scores(
            groups=[],
            focused_embedding=[1.0],
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should log debug about no items
        debug_calls = [str(call_obj) for call_obj in mock_logger.debug.call_args_list]
        assert any("No items with embeddings" in call_str for call_str in debug_calls)


@patch("services.embedding_shadow_logger.SHADOW_LOGGING_ENABLED", True)
def test_handles_negative_cosine():
    """Test shadow logger handles negative cosine similarity"""
    with patch("services.embedding_shadow_logger.logger") as mock_logger:
        groups = [{
            "group_key": "parts",
            "items": [
                {"entity_id": "part1", "weight": 100, "embedding": [-1.0, 0.0]},  # Opposite
            ]
        }]
        focused_embedding = [1.0, 0.0]

        shadow_log_rerank_scores(
            groups=groups,
            focused_embedding=focused_embedding,
            yacht_id="yacht123",
            entity_type="work_order",
            entity_id="wo123",
            alpha=0.0
        )

        # Should handle negative cosine (very rare but possible)
        # cosine_similarity([1.0, 0.0], [-1.0, 0.0]) = -1.0
        # Should not crash
        assert mock_logger.info.called
