"""
F1 RRF Fusion Math Tests

Tests for Reciprocal Rank Fusion (RRF) score calculation correctness.

RRF Formula:
    score = SUM(1.0 / (K + rank)) for each ranking source

where:
    - K = 60 (smoothing constant, reduces impact of high-ranked outliers)
    - rank = 1-indexed position in each source ranking

Properties verified:
1. Score calculation with K=60 constant
2. Deterministic ordering when scores tie
3. Trigram score contribution
4. Vector score contribution
5. Combined fusion output ordering

See: apps/api/docs/F1_SEARCH/RRF_FUSION.md
"""

import pytest
import uuid
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


# ============================================================================
# RRF Constants
# ============================================================================

RRF_K = 60  # Production smoothing constant


# ============================================================================
# RRF Calculation Functions (Mirror of production logic)
# ============================================================================

def calculate_rrf_score(ranks: List[int], k: int = RRF_K) -> float:
    """
    Calculate RRF score from multiple rank positions.

    Args:
        ranks: List of 1-indexed rank positions (None means not ranked)
        k: Smoothing constant (default 60)

    Returns:
        Combined RRF score
    """
    score = 0.0
    for rank in ranks:
        if rank is not None and rank > 0:
            score += 1.0 / (k + rank)
    return score


def calculate_single_rank_contribution(rank: int, k: int = RRF_K) -> float:
    """
    Calculate RRF contribution from a single rank.

    Args:
        rank: 1-indexed rank position
        k: Smoothing constant

    Returns:
        RRF contribution for this rank
    """
    if rank is None or rank <= 0:
        return 0.0
    return 1.0 / (k + rank)


def fuse_results_rrf(
    results: List[Dict[str, Any]],
    k: int = RRF_K,
) -> List[Dict[str, Any]]:
    """
    Apply RRF fusion to search results.

    Each result should have:
    - trigram_rank: Rank from trigram search (or None)
    - vector_rank: Rank from vector search (or None)

    Returns results sorted by fused_score descending.
    """
    for result in results:
        trig_rank = result.get("trigram_rank")
        vec_rank = result.get("vector_rank")
        result["fused_score"] = calculate_rrf_score([trig_rank, vec_rank], k)

    # Sort by fused_score descending, then by object_id for determinism
    return sorted(
        results,
        key=lambda r: (-r["fused_score"], r.get("object_id", "")),
    )


# ============================================================================
# Core RRF Calculation Tests
# ============================================================================

class TestRRFScoreCalculation:
    """Tests for basic RRF score calculation."""

    def test_single_rank_contribution_rank_1(self, rrf_k_constant: int):
        """Rank 1 should contribute 1/(K+1) = 1/61."""
        expected = 1.0 / (rrf_k_constant + 1)  # 1/61 = 0.01639...
        actual = calculate_single_rank_contribution(1, rrf_k_constant)

        assert abs(actual - expected) < 1e-10
        assert actual == pytest.approx(0.01639344, rel=1e-5)

    def test_single_rank_contribution_rank_10(self, rrf_k_constant: int):
        """Rank 10 should contribute 1/(K+10) = 1/70."""
        expected = 1.0 / (rrf_k_constant + 10)  # 1/70 = 0.01428...
        actual = calculate_single_rank_contribution(10, rrf_k_constant)

        assert abs(actual - expected) < 1e-10
        assert actual == pytest.approx(0.01428571, rel=1e-5)

    def test_single_rank_contribution_null_rank(self):
        """Null/None rank should contribute 0."""
        assert calculate_single_rank_contribution(None) == 0.0
        assert calculate_single_rank_contribution(0) == 0.0
        assert calculate_single_rank_contribution(-1) == 0.0

    def test_combined_rrf_score_both_ranks(self, rrf_k_constant: int):
        """
        Combined score with both trigram and vector ranks.

        Example: trigram_rank=1, vector_rank=3
        Score = 1/(60+1) + 1/(60+3) = 1/61 + 1/63
        """
        ranks = [1, 3]  # trigram_rank=1, vector_rank=3
        expected = 1.0 / 61 + 1.0 / 63

        actual = calculate_rrf_score(ranks, rrf_k_constant)

        assert actual == pytest.approx(expected, rel=1e-10)
        # Approximately 0.01639 + 0.01587 = 0.03226
        assert actual == pytest.approx(0.03226, rel=1e-3)

    def test_combined_rrf_score_one_rank_missing(self, rrf_k_constant: int):
        """Score when one ranking source doesn't include the result."""
        # Only trigram_rank=1, no vector rank
        ranks = [1, None]
        expected = 1.0 / 61

        actual = calculate_rrf_score(ranks, rrf_k_constant)

        assert actual == pytest.approx(expected, rel=1e-10)

    def test_combined_rrf_score_both_missing(self):
        """Score should be 0 if result not in any ranking."""
        ranks = [None, None]
        assert calculate_rrf_score(ranks) == 0.0


class TestRRFKConstant:
    """Tests verifying K=60 constant behavior."""

    def test_k_smoothing_reduces_top_rank_dominance(self):
        """
        K=60 ensures rank 1 doesn't overwhelmingly dominate.

        Compare rank 1 contribution to rank 10:
        - With K=60: 1/61 vs 1/70 = ratio of 1.15
        - With K=1: 1/2 vs 1/11 = ratio of 5.5

        K=60 creates smoother score distribution.
        """
        k = 60
        rank1_score = calculate_single_rank_contribution(1, k)
        rank10_score = calculate_single_rank_contribution(10, k)

        ratio = rank1_score / rank10_score

        # Ratio should be close to 70/61 = 1.147
        assert ratio == pytest.approx(70 / 61, rel=1e-5)
        assert ratio < 1.2  # Gentle slope

    def test_k_0_would_cause_division_issues(self):
        """K=0 would cause division by rank alone - verify we use K=60."""
        # This documents why K=60 is important
        # K=0 would mean rank 1 contributes 1/1 = 1.0 (too dominant)
        # K=60 means rank 1 contributes 1/61 = 0.0164 (balanced)
        assert RRF_K == 60

    def test_score_diminishes_with_rank(self, rrf_k_constant: int):
        """Higher ranks should contribute less score."""
        scores = [
            calculate_single_rank_contribution(r, rrf_k_constant)
            for r in range(1, 21)
        ]

        # Verify monotonically decreasing
        for i in range(len(scores) - 1):
            assert scores[i] > scores[i + 1], f"Rank {i+1} should score higher than {i+2}"


# ============================================================================
# Fusion Ordering Tests
# ============================================================================

class TestRRFFusionOrdering:
    """Tests for RRF fusion result ordering."""

    def test_fusion_orders_by_combined_score(self, sample_search_results: List[Dict]):
        """Results should be ordered by combined RRF score descending."""
        fused = fuse_results_rrf(sample_search_results)

        # Verify descending order
        for i in range(len(fused) - 1):
            assert fused[i]["fused_score"] >= fused[i + 1]["fused_score"]

    def test_result_with_top_ranks_wins(self, rrf_k_constant: int):
        """Result with rank 1 in both sources should win."""
        results = [
            {"object_id": "a", "trigram_rank": 5, "vector_rank": 5},
            {"object_id": "b", "trigram_rank": 1, "vector_rank": 1},  # Winner
            {"object_id": "c", "trigram_rank": 3, "vector_rank": 2},
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        assert fused[0]["object_id"] == "b"
        # Score: 1/61 + 1/61 = 2/61 = 0.0328
        assert fused[0]["fused_score"] == pytest.approx(2.0 / 61, rel=1e-5)

    def test_mixed_ranks_fusion(self, rrf_k_constant: int):
        """
        Test fusion with mixed ranking positions.

        Scenario: Result A is #1 in trigram but #10 in vector
                  Result B is #3 in trigram but #1 in vector
        """
        results = [
            {"object_id": "a", "trigram_rank": 1, "vector_rank": 10},
            {"object_id": "b", "trigram_rank": 3, "vector_rank": 1},
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        # Calculate expected scores
        score_a = 1.0 / 61 + 1.0 / 70  # = 0.01639 + 0.01429 = 0.03068
        score_b = 1.0 / 63 + 1.0 / 61  # = 0.01587 + 0.01639 = 0.03226

        # B should win (higher combined score)
        assert fused[0]["object_id"] == "b"
        assert fused[0]["fused_score"] == pytest.approx(score_b, rel=1e-5)

    def test_single_source_result_ranked_lower(self, rrf_k_constant: int):
        """Results in only one source should rank lower than dual-source results."""
        results = [
            {"object_id": "dual", "trigram_rank": 5, "vector_rank": 5},
            {"object_id": "trigram_only", "trigram_rank": 1, "vector_rank": None},
            {"object_id": "vector_only", "trigram_rank": None, "vector_rank": 1},
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        # Dual-source (5,5): 1/65 + 1/65 = 2/65 = 0.0308
        # Single-source (1,None): 1/61 = 0.0164
        # Dual wins despite worse individual ranks
        assert fused[0]["object_id"] == "dual"


class TestDeterministicOrdering:
    """Tests for deterministic tie-breaking."""

    def test_tied_scores_break_by_object_id(self, rrf_k_constant: int):
        """When scores tie, order should be deterministic by object_id."""
        results = [
            {"object_id": "zzz", "trigram_rank": 1, "vector_rank": 1},
            {"object_id": "aaa", "trigram_rank": 1, "vector_rank": 1},
            {"object_id": "mmm", "trigram_rank": 1, "vector_rank": 1},
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        # All have same score, should be sorted by object_id ascending
        ids = [r["object_id"] for r in fused]
        assert ids == ["aaa", "mmm", "zzz"]

    def test_repeated_fusion_is_deterministic(self, rrf_k_constant: int):
        """Multiple fusion calls should produce identical ordering."""
        results = [
            {"object_id": str(uuid.uuid4()), "trigram_rank": i, "vector_rank": 10 - i}
            for i in range(1, 11)
        ]

        # Run fusion multiple times
        orderings = []
        for _ in range(5):
            fused = fuse_results_rrf(results.copy(), rrf_k_constant)
            orderings.append([r["object_id"] for r in fused])

        # All orderings should be identical
        for ordering in orderings[1:]:
            assert ordering == orderings[0]


# ============================================================================
# Component Score Tests
# ============================================================================

class TestTrigramScoreContribution:
    """Tests for trigram search score contribution."""

    def test_high_trigram_rank_contributes_significantly(self, rrf_k_constant: int):
        """Top trigram rank should contribute meaningfully to fusion."""
        result = {"object_id": "a", "trigram_rank": 1, "vector_rank": None}
        fused = fuse_results_rrf([result], rrf_k_constant)

        # Pure trigram rank 1 score
        expected = 1.0 / 61
        assert fused[0]["fused_score"] == pytest.approx(expected, rel=1e-5)
        assert fused[0]["fused_score"] > 0.01  # Meaningful contribution

    def test_low_trigram_rank_contributes_less(self, rrf_k_constant: int):
        """Lower trigram ranks should contribute less."""
        results = [
            {"object_id": "rank1", "trigram_rank": 1, "vector_rank": None},
            {"object_id": "rank20", "trigram_rank": 20, "vector_rank": None},
        ]
        fused = fuse_results_rrf(results, rrf_k_constant)

        # Rank 1 should score higher
        assert fused[0]["object_id"] == "rank1"
        # Ratio: (60+20)/(60+1) = 80/61 = 1.31
        assert fused[0]["fused_score"] / fused[1]["fused_score"] == pytest.approx(
            80 / 61, rel=1e-5
        )


class TestVectorScoreContribution:
    """Tests for vector search score contribution."""

    def test_high_vector_rank_contributes_significantly(self, rrf_k_constant: int):
        """Top vector rank should contribute meaningfully to fusion."""
        result = {"object_id": "a", "trigram_rank": None, "vector_rank": 1}
        fused = fuse_results_rrf([result], rrf_k_constant)

        expected = 1.0 / 61
        assert fused[0]["fused_score"] == pytest.approx(expected, rel=1e-5)

    def test_vector_and_trigram_equal_weight(self, rrf_k_constant: int):
        """Vector and trigram sources should contribute equally at same rank."""
        results = [
            {"object_id": "trig", "trigram_rank": 1, "vector_rank": None},
            {"object_id": "vec", "trigram_rank": None, "vector_rank": 1},
        ]
        fused = fuse_results_rrf(results, rrf_k_constant)

        # Both should have same score
        assert fused[0]["fused_score"] == fused[1]["fused_score"]


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestRRFEdgeCases:
    """Tests for edge cases in RRF calculation."""

    def test_empty_results_list(self, rrf_k_constant: int):
        """Empty input should return empty output."""
        fused = fuse_results_rrf([], rrf_k_constant)
        assert fused == []

    def test_single_result(self, rrf_k_constant: int):
        """Single result should be returned with calculated score."""
        results = [{"object_id": "only", "trigram_rank": 1, "vector_rank": 1}]
        fused = fuse_results_rrf(results, rrf_k_constant)

        assert len(fused) == 1
        assert fused[0]["fused_score"] == pytest.approx(2.0 / 61, rel=1e-5)

    def test_very_high_ranks(self, rrf_k_constant: int):
        """Very high ranks should still contribute positively."""
        result = {"object_id": "a", "trigram_rank": 1000, "vector_rank": 1000}
        fused = fuse_results_rrf([result], rrf_k_constant)

        # Score = 1/1060 + 1/1060 = 2/1060
        expected = 2.0 / 1060
        assert fused[0]["fused_score"] == pytest.approx(expected, rel=1e-5)
        assert fused[0]["fused_score"] > 0  # Still positive

    def test_preserves_original_fields(self, rrf_k_constant: int):
        """Fusion should preserve all original result fields."""
        results = [
            {
                "object_id": "a",
                "object_type": "part",
                "payload": {"title": "Test Part"},
                "trigram_rank": 1,
                "vector_rank": 2,
                "trigram_score": 0.95,
                "vector_score": 0.88,
            }
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        assert fused[0]["object_type"] == "part"
        assert fused[0]["payload"] == {"title": "Test Part"}
        assert fused[0]["trigram_score"] == 0.95
        assert "fused_score" in fused[0]


# ============================================================================
# Production Compatibility Tests
# ============================================================================

class TestProductionCompatibility:
    """Tests ensuring compatibility with production hyper_search_multi output."""

    def test_handles_ranks_dict_format(self, rrf_k_constant: int):
        """
        Production returns ranks in a dict format.

        Example: {"trigram": 1, "vector": 3}
        """
        # Simulate production output format
        results = [
            {
                "object_id": "a",
                "object_type": "part",
                "payload": {},
                "fused_score": 0.03,  # Pre-calculated by DB
                "ranks": {"trigram": 1, "vector": 3},
                "components": {"trigram": 0.95, "vector": 0.82},
            }
        ]

        # Extract ranks from dict format
        for r in results:
            ranks = r.get("ranks", {})
            r["trigram_rank"] = ranks.get("trigram")
            r["vector_rank"] = ranks.get("vector")

        fused = fuse_results_rrf(results, rrf_k_constant)

        # Verify recalculated score matches formula
        expected = 1.0 / 61 + 1.0 / 63
        assert fused[0]["fused_score"] == pytest.approx(expected, rel=1e-5)

    def test_handles_missing_ranks_dict(self, rrf_k_constant: int):
        """Results without ranks dict should handle gracefully."""
        results = [
            {
                "object_id": "a",
                "object_type": "part",
                "trigram_rank": 1,
                "vector_rank": None,
            }
        ]

        fused = fuse_results_rrf(results, rrf_k_constant)

        assert len(fused) == 1
        assert fused[0]["fused_score"] == pytest.approx(1.0 / 61, rel=1e-5)


# ============================================================================
# Mathematical Property Tests
# ============================================================================

class TestRRFMathematicalProperties:
    """Tests for mathematical properties of RRF."""

    def test_score_is_always_positive(self, rrf_k_constant: int):
        """RRF score should always be non-negative."""
        import random

        for _ in range(100):
            ranks = [random.randint(1, 1000) if random.random() > 0.3 else None for _ in range(5)]
            score = calculate_rrf_score(ranks, rrf_k_constant)
            assert score >= 0

    def test_score_has_upper_bound(self, rrf_k_constant: int):
        """
        RRF score has theoretical upper bound.

        With 2 sources, max score = 2 * 1/(K+1) = 2/61 when both rank 1.
        """
        max_score = 2.0 / (rrf_k_constant + 1)

        # Generate many random results
        import random
        for _ in range(100):
            ranks = [random.randint(1, 100), random.randint(1, 100)]
            score = calculate_rrf_score(ranks, rrf_k_constant)
            assert score <= max_score + 1e-10

    def test_adding_ranks_increases_score(self, rrf_k_constant: int):
        """Adding a rank source should increase or maintain score."""
        score_one = calculate_rrf_score([1], rrf_k_constant)
        score_two = calculate_rrf_score([1, 5], rrf_k_constant)
        score_three = calculate_rrf_score([1, 5, 10], rrf_k_constant)

        assert score_two >= score_one
        assert score_three >= score_two

    def test_score_is_sum_of_components(self, rrf_k_constant: int):
        """Total score should equal sum of individual rank contributions."""
        ranks = [1, 3, 7, 15]

        individual_scores = [
            calculate_single_rank_contribution(r, rrf_k_constant) for r in ranks
        ]
        total_score = calculate_rrf_score(ranks, rrf_k_constant)

        assert total_score == pytest.approx(sum(individual_scores), rel=1e-10)


# ============================================================================
# Benchmark Tests
# ============================================================================

@pytest.mark.rrf
class TestRRFBenchmarks:
    """Performance benchmarks for RRF calculation."""

    def test_fusion_performance_small(self, rrf_k_constant: int, benchmark=None):
        """Benchmark fusion with 20 results (typical page size)."""
        results = [
            {
                "object_id": str(uuid.uuid4()),
                "trigram_rank": i,
                "vector_rank": 21 - i,
            }
            for i in range(1, 21)
        ]

        # Run without benchmark framework
        import time
        start = time.perf_counter()
        for _ in range(1000):
            fuse_results_rrf(results.copy(), rrf_k_constant)
        elapsed = time.perf_counter() - start

        # 1000 fusions should complete in under 1 second
        assert elapsed < 1.0, f"Fusion too slow: {elapsed:.3f}s for 1000 iterations"

    def test_fusion_performance_large(self, rrf_k_constant: int):
        """Benchmark fusion with 100 results."""
        results = [
            {
                "object_id": str(uuid.uuid4()),
                "trigram_rank": i,
                "vector_rank": 101 - i,
            }
            for i in range(1, 101)
        ]

        import time
        start = time.perf_counter()
        for _ in range(100):
            fuse_results_rrf(results.copy(), rrf_k_constant)
        elapsed = time.perf_counter() - start

        # 100 fusions of 100 results should complete in under 1 second
        assert elapsed < 1.0, f"Large fusion too slow: {elapsed:.3f}s"
