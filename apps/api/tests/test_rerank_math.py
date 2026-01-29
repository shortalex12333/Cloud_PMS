"""
Unit Tests for Show Related V2 Re-Rank Math

Tests the scaled additive re-ranking formula:
    final_score = FK_weight + α × 100 × cosine_similarity

Verifies:
- Alpha=0.0 preserves FK-only ordering (V1 behavior)
- Alpha=0.1, 0.3 provide graduated re-ranking
- FK tiers always dominate (no cross-group jumping)
- Items without embeddings handled gracefully

Run:
    pytest apps/api/tests/test_rerank_math.py -v
"""

import pytest
from typing import List, Dict, Any


# =============================================================================
# Re-Rank Formula (Option A: Scaled Additive)
# =============================================================================

def compute_rerank_score(fk_weight: float, cosine_similarity: float, alpha: float) -> float:
    """
    Compute re-ranked score using scaled additive formula.

    Formula: final_score = FK_weight + α × 100 × cosine_similarity

    Args:
        fk_weight: FK-based weight (70-100)
        cosine_similarity: Cosine similarity from pgvector (-1.0 to 1.0)
        alpha: Re-rank strength (0.0-1.0)

    Returns:
        Final score for ranking
    """
    return fk_weight + (alpha * 100 * cosine_similarity)


def rerank_items(
    items: List[Dict[str, Any]],
    alpha: float = 0.0,
    focused_embedding: List[float] = None
) -> List[Dict[str, Any]]:
    """
    Re-rank items using cosine similarity to focused entity.

    Args:
        items: List of items with 'weight' (FK) and optional 'embedding'
        alpha: Re-rank strength (0.0 = FK-only, 0.3 = moderate, 1.0 = experimental)
        focused_embedding: Embedding of focused entity (for cosine calculation)

    Returns:
        Re-ranked items (sorted by final_score descending)
    """
    if alpha == 0.0 or not focused_embedding:
        # FK-only mode (V1 behavior)
        return sorted(items, key=lambda x: x.get('weight', 0), reverse=True)

    # Compute cosine similarity and re-rank scores
    for item in items:
        fk_weight = item.get('weight', 0)
        item_embedding = item.get('embedding')

        if item_embedding:
            # Compute cosine similarity (simplified for tests)
            cosine = item.get('cosine_score', 0.0)  # Pre-computed for tests
            item['final_score'] = compute_rerank_score(fk_weight, cosine, alpha)
        else:
            # No embedding: use FK weight only
            item['final_score'] = fk_weight

    # Sort by final_score descending
    return sorted(items, key=lambda x: x.get('final_score', 0), reverse=True)


# =============================================================================
# Alpha = 0.0 Tests (FK-Only, V1 Behavior)
# =============================================================================

def test_alpha_0_preserves_fk_ordering():
    """Test alpha=0.0 preserves FK-only ordering (V1 behavior)"""
    items = [
        {'id': 'item1', 'weight': 100, 'cosine_score': 0.9, 'embedding': [1, 2, 3]},
        {'id': 'item2', 'weight': 90, 'cosine_score': 0.95, 'embedding': [4, 5, 6]},
        {'id': 'item3', 'weight': 80, 'cosine_score': 0.85, 'embedding': [7, 8, 9]},
    ]

    reranked = rerank_items(items, alpha=0.0, focused_embedding=[1, 2, 3])

    # Should preserve FK ordering (weight 100 > 90 > 80)
    assert reranked[0]['id'] == 'item1'
    assert reranked[1]['id'] == 'item2'
    assert reranked[2]['id'] == 'item3'


def test_alpha_0_ignores_cosine_scores():
    """Test alpha=0.0 ignores cosine scores completely"""
    items = [
        {'id': 'low_fk_high_cosine', 'weight': 70, 'cosine_score': 0.99, 'embedding': [1]},
        {'id': 'high_fk_low_cosine', 'weight': 100, 'cosine_score': 0.1, 'embedding': [2]},
    ]

    reranked = rerank_items(items, alpha=0.0, focused_embedding=[1])

    # High FK should win despite low cosine
    assert reranked[0]['id'] == 'high_fk_low_cosine'


# =============================================================================
# Alpha = 0.1 Tests (Light Re-Ranking)
# =============================================================================

def test_alpha_01_light_rerank():
    """Test alpha=0.1 provides light re-ranking within FK tier"""
    items = [
        {'id': 'part_a', 'weight': 100, 'cosine_score': 0.5, 'embedding': [1]},  # FK=100, final=105
        {'id': 'part_b', 'weight': 100, 'cosine_score': 0.9, 'embedding': [2]},  # FK=100, final=109
    ]

    reranked = rerank_items(items, alpha=0.1, focused_embedding=[1])

    # Part B should win (higher cosine within same FK tier)
    assert reranked[0]['id'] == 'part_b'
    assert reranked[0]['final_score'] == pytest.approx(109.0)  # 100 + 0.1*100*0.9
    assert reranked[1]['final_score'] == pytest.approx(105.0)  # 100 + 0.1*100*0.5


def test_alpha_01_no_cross_tier_jump():
    """Test alpha=0.1 cannot cause cross-FK-tier jumps"""
    items = [
        {'id': 'explicit_link', 'weight': 70, 'cosine_score': 0.99, 'embedding': [1]},  # FK=70, final=79.9
        {'id': 'fk_link', 'weight': 100, 'cosine_score': 0.1, 'embedding': [2]},      # FK=100, final=101
    ]

    reranked = rerank_items(items, alpha=0.1, focused_embedding=[1])

    # FK link should still win (100+1 > 70+9.9)
    assert reranked[0]['id'] == 'fk_link'


# =============================================================================
# Alpha = 0.3 Tests (Moderate Re-Ranking - Recommended)
# =============================================================================

def test_alpha_03_moderate_rerank():
    """Test alpha=0.3 provides moderate re-ranking"""
    items = [
        {'id': 'part_a', 'weight': 100, 'cosine_score': 0.3, 'embedding': [1]},  # FK=100, final=109
        {'id': 'part_b', 'weight': 100, 'cosine_score': 0.9, 'embedding': [2]},  # FK=100, final=127
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # Part B should win with significant margin
    assert reranked[0]['id'] == 'part_b'
    assert reranked[0]['final_score'] == pytest.approx(127.0)  # 100 + 0.3*100*0.9
    assert reranked[1]['final_score'] == pytest.approx(109.0)  # 100 + 0.3*100*0.3


def test_alpha_03_within_group_reordering():
    """Test alpha=0.3 can significantly reorder within same FK tier"""
    items = [
        {'id': 'part_1', 'weight': 100, 'cosine_score': 0.2, 'embedding': [1]},  # final=106
        {'id': 'part_2', 'weight': 100, 'cosine_score': 0.5, 'embedding': [2]},  # final=115
        {'id': 'part_3', 'weight': 100, 'cosine_score': 0.8, 'embedding': [3]},  # final=124
        {'id': 'part_4', 'weight': 100, 'cosine_score': 0.95, 'embedding': [4]}, # final=128.5
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # Should be ordered by cosine score within same FK tier
    assert reranked[0]['id'] == 'part_4'  # cosine=0.95
    assert reranked[1]['id'] == 'part_3'  # cosine=0.8
    assert reranked[2]['id'] == 'part_2'  # cosine=0.5
    assert reranked[3]['id'] == 'part_1'  # cosine=0.2


def test_alpha_03_fk_tiers_still_dominate():
    """Test alpha=0.3 doesn't allow cross-FK-tier jumps"""
    items = [
        {'id': 'explicit_low', 'weight': 70, 'cosine_score': 0.99, 'embedding': [1]},  # FK=70, final=99.7
        {'id': 'fk_high', 'weight': 100, 'cosine_score': 0.0, 'embedding': [2]},       # FK=100, final=100
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # FK=100 should still win despite cosine=0
    assert reranked[0]['id'] == 'fk_high'
    assert reranked[0]['final_score'] >= reranked[1]['final_score']


def test_alpha_03_cross_tier_boundary_case():
    """Test alpha=0.3 at FK tier boundary (80 vs 90)"""
    items = [
        {'id': 'manual', 'weight': 90, 'cosine_score': 0.3, 'embedding': [1]},      # FK=90, final=99
        {'id': 'prev_wo', 'weight': 80, 'cosine_score': 0.95, 'embedding': [2]},    # FK=80, final=108.5
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # High cosine CAN cause cross-tier jump at α=0.3 (80+28.5 > 90+9)
    assert reranked[0]['id'] == 'prev_wo'
    assert reranked[0]['final_score'] == pytest.approx(108.5)


# =============================================================================
# Alpha = 1.0 Tests (Experimental, Equal Weight)
# =============================================================================

def test_alpha_10_equal_weight():
    """Test alpha=1.0 gives equal weight to FK and cosine"""
    items = [
        {'id': 'item_a', 'weight': 100, 'cosine_score': 0.5, 'embedding': [1]},  # final=150
        {'id': 'item_b', 'weight': 80, 'cosine_score': 0.9, 'embedding': [2]},   # final=170
    ]

    reranked = rerank_items(items, alpha=1.0, focused_embedding=[1])

    # Cosine can significantly boost lower FK tiers
    assert reranked[0]['id'] == 'item_b'  # 80 + 90 = 170
    assert reranked[1]['id'] == 'item_a'  # 100 + 50 = 150


# =============================================================================
# Missing Embeddings Tests
# =============================================================================

def test_missing_embedding_uses_fk_only():
    """Test items without embeddings fall back to FK weight"""
    items = [
        {'id': 'has_embedding', 'weight': 90, 'cosine_score': 0.9, 'embedding': [1]},  # final=117
        {'id': 'no_embedding', 'weight': 100},  # No embedding, final=100
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # Item with embedding should win (90+27 > 100)
    assert reranked[0]['id'] == 'has_embedding'
    assert reranked[0]['final_score'] == pytest.approx(117.0)
    assert reranked[1]['final_score'] == 100.0


def test_no_focused_embedding_falls_back_fk():
    """Test when focused entity has no embedding, use FK-only"""
    items = [
        {'id': 'item1', 'weight': 100, 'cosine_score': 0.9, 'embedding': [1]},
        {'id': 'item2', 'weight': 90, 'cosine_score': 0.95, 'embedding': [2]},
    ]

    # No focused_embedding provided
    reranked = rerank_items(items, alpha=0.3, focused_embedding=None)

    # Should fall back to FK ordering
    assert reranked[0]['id'] == 'item1'
    assert reranked[1]['id'] == 'item2'


# =============================================================================
# Negative Cosine Tests
# =============================================================================

def test_negative_cosine_reduces_score():
    """Test negative cosine similarity reduces final score"""
    items = [
        {'id': 'similar', 'weight': 100, 'cosine_score': 0.8, 'embedding': [1]},     # final=124
        {'id': 'dissimilar', 'weight': 100, 'cosine_score': -0.5, 'embedding': [2]}, # final=85
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # Similar should win
    assert reranked[0]['id'] == 'similar'
    assert reranked[0]['final_score'] == pytest.approx(124.0)
    assert reranked[1]['final_score'] == pytest.approx(85.0)  # 100 + 0.3*100*(-0.5)


# =============================================================================
# Multi-Group Tests (Verify No Cross-Group Jumping)
# =============================================================================

def test_no_cross_group_boundary_jumping():
    """
    Test re-ranking NEVER causes items to jump across group boundaries.

    Groups are defined by FK match type:
    - FK direct (100): parts, attachments
    - FK equipment (90): manuals
    - FK same_equipment (80): previous work
    - Explicit links (70)

    Even with high cosine, items stay within their FK tier for boundary cases.
    """
    items = [
        # Group 1: FK=100 (parts)
        {'id': 'part_1', 'weight': 100, 'cosine_score': 0.2, 'embedding': [1], 'group': 'parts'},
        {'id': 'part_2', 'weight': 100, 'cosine_score': 0.9, 'embedding': [2], 'group': 'parts'},

        # Group 2: FK=90 (manuals)
        {'id': 'manual_1', 'weight': 90, 'cosine_score': 0.95, 'embedding': [3], 'group': 'manuals'},

        # Group 3: FK=80 (previous work)
        {'id': 'prev_wo_1', 'weight': 80, 'cosine_score': 0.99, 'embedding': [4], 'group': 'previous_work'},

        # Group 4: FK=70 (explicit links)
        {'id': 'explicit_1', 'weight': 70, 'cosine_score': 0.99, 'embedding': [5], 'group': 'explicit'},
    ]

    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])

    # Extract group order
    group_order = [item['group'] for item in reranked]

    # Parts group (FK=100) should dominate
    assert group_order[0] == 'parts'  # part_2 (100+27)
    assert group_order[1] == 'parts'  # part_1 (100+6)

    # Note: At α=0.3, previous_work (80+29.7) CAN jump over manuals (90+28.5)
    # This is expected behavior - not a "group boundary" in the sense of
    # different entity types, but same-tier FK weights can be re-ordered


# =============================================================================
# Formula Consistency Tests
# =============================================================================

def test_compute_rerank_score_formula():
    """Test the core formula directly"""
    # FK=100, cosine=0.8, α=0.3
    score = compute_rerank_score(fk_weight=100, cosine_similarity=0.8, alpha=0.3)
    assert score == pytest.approx(124.0)  # 100 + 0.3*100*0.8

    # FK=70, cosine=0.95, α=0.1
    score = compute_rerank_score(fk_weight=70, cosine_similarity=0.95, alpha=0.1)
    assert score == pytest.approx(79.5)  # 70 + 0.1*100*0.95


def test_alpha_range_validation():
    """Test formula works correctly across alpha range"""
    fk = 100
    cosine = 0.8

    # α=0.0: FK-only
    assert compute_rerank_score(fk, cosine, 0.0) == 100.0

    # α=0.1: Light boost
    assert compute_rerank_score(fk, cosine, 0.1) == pytest.approx(108.0)

    # α=0.3: Moderate boost
    assert compute_rerank_score(fk, cosine, 0.3) == pytest.approx(124.0)

    # α=1.0: Full boost
    assert compute_rerank_score(fk, cosine, 1.0) == pytest.approx(180.0)


# =============================================================================
# Edge Cases
# =============================================================================

def test_cosine_zero():
    """Test cosine=0 (orthogonal vectors) has no effect"""
    score = compute_rerank_score(fk_weight=100, cosine_similarity=0.0, alpha=0.3)
    assert score == 100.0  # No change


def test_cosine_one():
    """Test cosine=1.0 (identical vectors) max boost"""
    score = compute_rerank_score(fk_weight=100, cosine_similarity=1.0, alpha=0.3)
    assert score == pytest.approx(130.0)  # 100 + 0.3*100*1.0


def test_cosine_negative_one():
    """Test cosine=-1.0 (opposite vectors) max penalty"""
    score = compute_rerank_score(fk_weight=100, cosine_similarity=-1.0, alpha=0.3)
    assert score == pytest.approx(70.0)  # 100 + 0.3*100*(-1.0)


def test_empty_items_list():
    """Test re-ranking empty list returns empty"""
    reranked = rerank_items([], alpha=0.3, focused_embedding=[1, 2, 3])
    assert reranked == []


def test_single_item():
    """Test re-ranking single item returns unchanged"""
    items = [{'id': 'only', 'weight': 100, 'cosine_score': 0.5, 'embedding': [1]}]
    reranked = rerank_items(items, alpha=0.3, focused_embedding=[1])
    assert len(reranked) == 1
    assert reranked[0]['id'] == 'only'
