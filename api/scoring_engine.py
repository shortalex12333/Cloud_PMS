"""
Scoring Engine: Multi-Signal Fusion for CelesteOS Search
=========================================================

Combines multiple scoring signals to rank search results:
- Exact match (code, ID)
- Canonical match
- Fuzzy/ILIKE match quality
- Vector similarity
- Entity weight contribution
- Table bias
- Recency

Usage:
    from scoring_engine import ScoringEngine

    engine = ScoringEngine()
    scored = engine.score_results(results, query_context)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

# Weight each signal in final score
SIGNAL_WEIGHTS = {
    "exact_match": 0.30,      # Exact code/ID match
    "canonical_match": 0.20,  # Canonical form match
    "fuzzy_quality": 0.15,    # Substring/ILIKE match quality
    "vector_similarity": 0.10,# Embedding cosine similarity
    "entity_weight": 0.10,    # Original entity weight contribution
    "table_bias": 0.10,       # Table priority from routing
    "recency": 0.05,          # Recent data preference
}

# Exact match column types (get full 1.0 score)
EXACT_MATCH_COLUMNS = {
    "fault_code", "code", "part_number", "po_number",
    "certificate_number", "serial_number", "id"
}

# High-value columns for fuzzy matching
HIGH_VALUE_COLUMNS = {
    "name", "title", "label", "document_name"
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ScoreBreakdown:
    """Individual signal scores"""
    exact_match: float = 0.0
    canonical_match: float = 0.0
    fuzzy_quality: float = 0.0
    vector_similarity: float = 0.0
    entity_weight: float = 0.0
    table_bias: float = 0.0
    recency: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "exact_match": round(self.exact_match, 3),
            "canonical_match": round(self.canonical_match, 3),
            "fuzzy_quality": round(self.fuzzy_quality, 3),
            "vector_similarity": round(self.vector_similarity, 3),
            "entity_weight": round(self.entity_weight, 3),
            "table_bias": round(self.table_bias, 3),
            "recency": round(self.recency, 3),
        }


@dataclass
class ScoredResult:
    """Result with scoring metadata"""
    result: Dict[str, Any]
    final_score: float
    breakdown: ScoreBreakdown
    matched_entities: List[str]
    match_quality: str  # "exact", "canonical", "fuzzy", "vector"


@dataclass
class QueryContext:
    """Context for scoring calculations"""
    entities: List[Dict[str, Any]]
    intent: str
    yacht_id: Optional[str]
    terms: List[str]
    canonical_terms: List[str]
    has_embedding: bool


# =============================================================================
# SCORING ENGINE
# =============================================================================

class ScoringEngine:
    """
    Multi-signal scoring engine for search results.

    Combines:
    - Exact match detection
    - Canonical form matching
    - Fuzzy match quality
    - Vector similarity
    - Entity weights
    - Table bias
    - Recency
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or SIGNAL_WEIGHTS

    def check_exact_match(
        self,
        result: Dict[str, Any],
        terms: List[str],
        canonical_terms: List[str],
    ) -> Tuple[bool, str]:
        """
        Check if result has exact match on high-value column.

        Returns:
            (is_exact, matched_column)
        """
        for col in EXACT_MATCH_COLUMNS:
            if col not in result:
                continue

            val = str(result[col]).lower()

            # Check exact term match
            for term in terms:
                if val == term.lower():
                    return True, col

            # Check canonical match
            for canon in canonical_terms:
                if val == canon.lower():
                    return True, col

        return False, ""

    def check_canonical_match(
        self,
        result: Dict[str, Any],
        canonical_terms: List[str],
    ) -> Tuple[bool, str]:
        """
        Check if result matches a canonical form.

        Returns:
            (has_match, matched_field)
        """
        if not canonical_terms:
            return False, ""

        # Check common canonical columns
        canonical_cols = [
            "canonical", "canonical_label", "normalized_label",
            "code", "name", "label"
        ]

        for col in canonical_cols:
            if col not in result:
                continue

            val = str(result[col]).upper()

            for canon in canonical_terms:
                if val == canon.upper():
                    return True, col

        return False, ""

    def calculate_fuzzy_quality(
        self,
        result: Dict[str, Any],
        terms: List[str],
    ) -> float:
        """
        Calculate fuzzy match quality score (0-1).

        Higher score for:
        - Match in high-value column
        - Match at beginning of text
        - Higher ratio of matched text
        """
        if not terms:
            return 0.0

        best_score = 0.0

        for term in terms:
            term_lower = term.lower()

            for col, val in result.items():
                if val is None or col.startswith("_"):
                    continue

                val_str = str(val).lower()
                if term_lower not in val_str:
                    continue

                # Base score
                score = 0.5

                # High-value column bonus
                if col in HIGH_VALUE_COLUMNS:
                    score += 0.2

                # Position bonus (match at start)
                if val_str.startswith(term_lower):
                    score += 0.2
                elif val_str.find(term_lower) < 10:
                    score += 0.1

                # Coverage ratio
                ratio = len(term_lower) / max(len(val_str), 1)
                score += ratio * 0.1

                best_score = max(best_score, score)

        return min(1.0, best_score)

    def calculate_entity_weight_contribution(
        self,
        result: Dict[str, Any],
        entities: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate contribution from matched entity weights.

        Returns weighted average of matched entity weights (0-1).
        """
        if not entities:
            return 0.5  # Neutral if no entities

        total_weight = 0.0
        matched_weight = 0.0

        for entity in entities:
            entity_value = entity.get("value", "").lower()
            entity_weight = entity.get("canonical_weight", entity.get("weight", 1.0))

            total_weight += entity_weight

            # Check if entity matches result
            for val in result.values():
                if val is None:
                    continue
                if entity_value in str(val).lower():
                    matched_weight += entity_weight
                    break

        if total_weight == 0:
            return 0.5

        # Normalize to 0-1 (assuming max weight of 5)
        normalized = matched_weight / (total_weight * 5) if total_weight > 0 else 0
        return min(1.0, normalized * 2)  # Scale up since typical weights are 1-3

    def calculate_table_bias_score(
        self,
        result: Dict[str, Any],
    ) -> float:
        """
        Get table bias score (0-1).

        Uses _bias_score from routing if available.
        """
        bias = result.get("_bias_score", 1.0)
        # Normalize: 0 -> 0, 1 -> 0.33, 2 -> 0.67, 3 -> 1.0
        return min(1.0, bias / 3.0)

    def calculate_recency_score(
        self,
        result: Dict[str, Any],
        max_age_days: int = 365,
    ) -> float:
        """
        Calculate recency score (0-1).

        1.0 = today, 0 = max_age_days ago or older.
        """
        # Try common timestamp columns
        ts_cols = ["created_at", "updated_at", "detected_at", "reported_at"]

        for col in ts_cols:
            if col not in result or result[col] is None:
                continue

            try:
                ts = result[col]
                if isinstance(ts, str):
                    # Parse ISO format
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

                if isinstance(ts, datetime):
                    age = (datetime.now(ts.tzinfo) - ts).days
                    return max(0.0, 1.0 - age / max_age_days)
            except:
                continue

        return 0.5  # Neutral if no timestamp

    def score_result(
        self,
        result: Dict[str, Any],
        context: QueryContext,
    ) -> ScoredResult:
        """
        Calculate complete score for a single result.
        """
        breakdown = ScoreBreakdown()
        matched_entities = []
        match_quality = "fuzzy"

        # 1. Exact match
        is_exact, exact_col = self.check_exact_match(
            result, context.terms, context.canonical_terms
        )
        if is_exact:
            breakdown.exact_match = 1.0
            match_quality = "exact"

        # 2. Canonical match
        has_canonical, canon_col = self.check_canonical_match(
            result, context.canonical_terms
        )
        if has_canonical:
            breakdown.canonical_match = 1.0
            if match_quality != "exact":
                match_quality = "canonical"

        # 3. Fuzzy quality
        breakdown.fuzzy_quality = self.calculate_fuzzy_quality(
            result, context.terms
        )

        # 4. Vector similarity (if provided in result)
        breakdown.vector_similarity = result.get("_vector_score", 0.0)
        if breakdown.vector_similarity > 0.8 and match_quality == "fuzzy":
            match_quality = "vector"

        # 5. Entity weight contribution
        breakdown.entity_weight = self.calculate_entity_weight_contribution(
            result, context.entities
        )

        # Track matched entities
        for entity in context.entities:
            val = entity.get("value", "").lower()
            for rv in result.values():
                if rv and val in str(rv).lower():
                    matched_entities.append(entity.get("value"))
                    break

        # 6. Table bias
        breakdown.table_bias = self.calculate_table_bias_score(result)

        # 7. Recency
        breakdown.recency = self.calculate_recency_score(result)

        # Calculate weighted final score
        final_score = (
            self.weights["exact_match"] * breakdown.exact_match +
            self.weights["canonical_match"] * breakdown.canonical_match +
            self.weights["fuzzy_quality"] * breakdown.fuzzy_quality +
            self.weights["vector_similarity"] * breakdown.vector_similarity +
            self.weights["entity_weight"] * breakdown.entity_weight +
            self.weights["table_bias"] * breakdown.table_bias +
            self.weights["recency"] * breakdown.recency
        )

        # Apply guard rails
        final_score = self._apply_guard_rails(final_score, breakdown)

        return ScoredResult(
            result=result,
            final_score=round(final_score, 3),
            breakdown=breakdown,
            matched_entities=matched_entities,
            match_quality=match_quality,
        )

    def _apply_guard_rails(
        self,
        score: float,
        breakdown: ScoreBreakdown,
    ) -> float:
        """
        Apply sanity checks to prevent anomalous scores.
        """
        # Count high signals (>= 0.5)
        signals = [
            breakdown.exact_match,
            breakdown.canonical_match,
            breakdown.fuzzy_quality,
            breakdown.entity_weight,
        ]
        high_signals = sum(1 for s in signals if s >= 0.5)

        # Don't let score be too high without multiple strong signals
        if score > 0.7 and high_signals < 2:
            score *= 0.85

        # Penalize if high table bias but low actual match
        if breakdown.table_bias > 0.6 and breakdown.fuzzy_quality < 0.3:
            score *= 0.9

        return max(0.0, min(1.0, score))

    def score_results(
        self,
        results: List[Dict[str, Any]],
        context: QueryContext,
    ) -> List[ScoredResult]:
        """
        Score and sort multiple results.
        """
        scored = [self.score_result(r, context) for r in results]
        scored.sort(key=lambda x: x.final_score, reverse=True)
        return scored

    def diversify_results(
        self,
        scored_results: List[ScoredResult],
        top_n: int = 10,
        max_per_source: int = 3,
    ) -> List[ScoredResult]:
        """
        Promote diversity by limiting results per source table.
        """
        if len(scored_results) <= top_n:
            return scored_results

        diversified = []
        source_count = {}
        remaining = list(scored_results)

        while len(diversified) < top_n and remaining:
            for i, item in enumerate(remaining):
                source = item.result.get("_source_table", "unknown")

                if source_count.get(source, 0) < max_per_source:
                    diversified.append(item)
                    source_count[source] = source_count.get(source, 0) + 1
                    remaining.pop(i)
                    break
            else:
                # No valid item found, take highest score
                if remaining:
                    diversified.append(remaining.pop(0))

        return diversified + remaining

    def group_by_tier(
        self,
        scored_results: List[ScoredResult],
    ) -> Dict[str, List[ScoredResult]]:
        """
        Group results by quality tier.
        """
        return {
            "best": [r for r in scored_results if r.final_score >= 0.6],
            "good": [r for r in scored_results if 0.3 <= r.final_score < 0.6],
            "other": [r for r in scored_results if r.final_score < 0.3],
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def score_search_results(
    results: List[Dict[str, Any]],
    extraction_output: Dict[str, Any],
) -> Dict[str, Any]:
    """
    One-liner for n8n Code node.

    Usage in n8n:
        const scored = score_search_results(
            $input.all().map(i => i.json),
            $('Render Extract').first().json
        );
    """
    engine = ScoringEngine()

    # Build context
    context = QueryContext(
        entities=extraction_output.get("entities", []),
        intent=extraction_output.get("intent", "general_search"),
        yacht_id=extraction_output.get("body", {}).get("auth", {}).get("yacht_id"),
        terms=[e.get("value", "") for e in extraction_output.get("entities", [])],
        canonical_terms=[e.get("canonical", "") for e in extraction_output.get("entities", []) if e.get("canonical")],
        has_embedding=extraction_output.get("embedding") is not None,
    )

    # Score
    scored = engine.score_results(results, context)

    # Diversify
    diversified = engine.diversify_results(scored)

    # Group
    tiers = engine.group_by_tier(diversified)

    # Format output
    def format_result(sr: ScoredResult) -> Dict:
        return {
            **sr.result,
            "_final_score": sr.final_score,
            "_score_breakdown": sr.breakdown.to_dict(),
            "_matched_entities": sr.matched_entities,
            "_match_quality": sr.match_quality,
        }

    return {
        "status": "success",
        "total_results": len(diversified),
        "tiers": {
            "best": [format_result(r) for r in tiers["best"]],
            "good": [format_result(r) for r in tiers["good"]],
            "other": [format_result(r) for r in tiers["other"]],
        },
        "results": [format_result(r) for r in diversified],
        "metadata": {
            "intent": context.intent,
            "entity_count": len(context.entities),
            "best_count": len(tiers["best"]),
            "good_count": len(tiers["good"]),
            "other_count": len(tiers["other"]),
        }
    }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with sample data
    sample_results = [
        {
            "id": "part-001",
            "name": "Oil Filter",
            "part_number": "OF-1234",
            "manufacturer": "Racor",
            "description": "High-performance oil filter for main engine",
            "_source_table": "pms_parts",
            "_source_display": "Parts",
            "_bias_score": 2.5,
            "created_at": "2024-06-15T10:00:00Z",
        },
        {
            "id": "stock-001",
            "location": "Box 2D",
            "quantity": 5,
            "part_id": "part-001",
            "_source_table": "pms_inventory_stock",
            "_source_display": "Inventory",
            "_bias_score": 2.33,
            "created_at": "2024-01-10T10:00:00Z",
        },
        {
            "id": "equip-001",
            "name": "Main Engine",
            "code": "ME-1",
            "manufacturer": "MTU",
            "model": "16V4000",
            "_source_table": "pms_equipment",
            "_source_display": "Equipment",
            "_bias_score": 1.5,
            "created_at": "2023-06-01T10:00:00Z",
        },
    ]

    extraction_output = {
        "intent": "view_part_location",
        "intent_confidence": 0.88,
        "entities": [
            {
                "type": "location",
                "value": "box 2d",
                "canonical": "BOX_2D",
                "weight": 2,
                "canonical_weight": 1.6,
            }
        ],
        "embedding": None,
        "body": {"auth": {"yacht_id": "00000000-0000-0000-0000-000000000000"}}
    }

    result = score_search_results(sample_results, extraction_output)

    print("=" * 60)
    print("SCORING RESULTS")
    print("=" * 60)
    print(f"Total: {result['total_results']}")
    print(f"Best: {result['metadata']['best_count']}")
    print(f"Good: {result['metadata']['good_count']}")
    print(f"Other: {result['metadata']['other_count']}")
    print()

    for i, r in enumerate(result["results"][:5]):
        print(f"{i+1}. [{r['_source_display']}] {r.get('name', r.get('location', 'N/A'))}")
        print(f"   Score: {r['_final_score']} | Quality: {r['_match_quality']}")
        print(f"   Breakdown: {r['_score_breakdown']}")
        print()
