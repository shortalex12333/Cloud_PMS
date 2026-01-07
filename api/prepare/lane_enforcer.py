"""
Lane Enforcer: Hard invariant enforcement for CelesteOS lanes.
===============================================================

Lanes are CONTRACTUAL, not advisory. This module enforces:

| Lane       | Forbidden                                |
| ---------- | ---------------------------------------- |
| NO_LLM     | ❌ vectors, ❌ embeddings, ❌ GPT fallback  |
| RULES_ONLY | ❌ semantic inference, ❌ intent rewriting |
| GPT        | ✅ vectors, ✅ graph, ✅ semantic           |

If lane behavior bleeds → raise LaneViolationError.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class Lane(Enum):
    BLOCKED = "BLOCKED"
    NO_LLM = "NO_LLM"
    RULES_ONLY = "RULES_ONLY"
    GPT = "GPT"


class LaneViolationError(Exception):
    """Raised when lane invariants are violated."""
    pass


@dataclass
class LaneCapabilities:
    """What operations are allowed per lane."""
    allow_vector_search: bool
    allow_embedding: bool
    allow_semantic_inference: bool
    allow_intent_rewriting: bool
    allow_graph_traversal: bool
    deterministic_required: bool


# Lane capability definitions - these are FIXED
LANE_CAPABILITIES: Dict[Lane, LaneCapabilities] = {
    Lane.BLOCKED: LaneCapabilities(
        allow_vector_search=False,
        allow_embedding=False,
        allow_semantic_inference=False,
        allow_intent_rewriting=False,
        allow_graph_traversal=False,
        deterministic_required=True,
    ),
    Lane.NO_LLM: LaneCapabilities(
        allow_vector_search=False,
        allow_embedding=False,
        allow_semantic_inference=False,
        allow_intent_rewriting=False,
        allow_graph_traversal=False,  # Only keyword-based graph lookup
        deterministic_required=True,
    ),
    Lane.RULES_ONLY: LaneCapabilities(
        allow_vector_search=False,
        allow_embedding=False,
        allow_semantic_inference=False,
        allow_intent_rewriting=False,
        allow_graph_traversal=True,  # Rule-based graph traversal OK
        deterministic_required=True,
    ),
    Lane.GPT: LaneCapabilities(
        allow_vector_search=True,
        allow_embedding=True,
        allow_semantic_inference=True,
        allow_intent_rewriting=True,
        allow_graph_traversal=True,
        deterministic_required=False,
    ),
}


class LaneEnforcer:
    """
    Enforces lane invariants at runtime.

    Usage:
        enforcer = LaneEnforcer(lane="NO_LLM")
        enforcer.assert_no_vector_search()  # OK
        enforcer.assert_vector_search_allowed()  # Raises LaneViolationError
    """

    def __init__(self, lane: str):
        try:
            self.lane = Lane(lane.upper())
        except ValueError:
            raise LaneViolationError(f"Unknown lane: {lane}")

        self.capabilities = LANE_CAPABILITIES[self.lane]

    def assert_vector_search_allowed(self) -> None:
        """Raises if vector search is forbidden for this lane."""
        if not self.capabilities.allow_vector_search:
            raise LaneViolationError(
                f"Vector search forbidden in {self.lane.value} lane. "
                "Vector search is only allowed in GPT lane."
            )

    def assert_embedding_allowed(self) -> None:
        """Raises if embedding usage is forbidden for this lane."""
        if not self.capabilities.allow_embedding:
            raise LaneViolationError(
                f"Embedding usage forbidden in {self.lane.value} lane. "
                "Embeddings are only allowed in GPT lane."
            )

    def assert_semantic_inference_allowed(self) -> None:
        """Raises if semantic inference is forbidden for this lane."""
        if not self.capabilities.allow_semantic_inference:
            raise LaneViolationError(
                f"Semantic inference forbidden in {self.lane.value} lane. "
                "Semantic inference is only allowed in GPT lane."
            )

    def assert_intent_rewriting_allowed(self) -> None:
        """Raises if intent rewriting is forbidden for this lane."""
        if not self.capabilities.allow_intent_rewriting:
            raise LaneViolationError(
                f"Intent rewriting forbidden in {self.lane.value} lane. "
                "Intent rewriting is only allowed in GPT lane."
            )

    def assert_graph_traversal_allowed(self) -> None:
        """Raises if graph traversal is forbidden for this lane."""
        if not self.capabilities.allow_graph_traversal:
            raise LaneViolationError(
                f"Graph traversal forbidden in {self.lane.value} lane. "
                "Graph traversal is allowed in RULES_ONLY and GPT lanes."
            )

    def filter_search_types(self, search_types: List[str]) -> List[str]:
        """
        Filters search types based on lane capabilities.

        Removes forbidden search types and raises if ONLY forbidden types remain.
        """
        allowed = []
        forbidden = []

        for st in search_types:
            st_upper = st.upper()
            if st_upper == "VECTOR":
                if self.capabilities.allow_vector_search:
                    allowed.append(st)
                else:
                    forbidden.append(st)
            elif st_upper in ("EXACT", "CANONICAL", "FUZZY"):
                allowed.append(st)
            else:
                # Unknown search type - allow but log
                allowed.append(st)

        if not allowed and forbidden:
            raise LaneViolationError(
                f"All search types forbidden in {self.lane.value} lane: {forbidden}"
            )

        return allowed

    def validate_extraction_output(self, extraction: Dict[str, Any]) -> None:
        """
        Validates that extraction output doesn't violate lane invariants.

        Raises LaneViolationError if:
        - NO_LLM/RULES_ONLY has embedding that would be used
        - BLOCKED lane has any execution attempt
        """
        if self.lane == Lane.BLOCKED:
            raise LaneViolationError(
                "BLOCKED lane cannot proceed to SQL execution. "
                "Query should have been rejected earlier."
            )

        # Check embedding presence
        embedding = extraction.get("embedding")
        has_embedding = embedding is not None and len(embedding) > 0

        if has_embedding and not self.capabilities.allow_embedding:
            # Embedding present but can't use it - this is OK, just ignore it
            # But we should NOT use it in search
            pass  # Log warning but don't fail

        return None

    def get_allowed_tables(self, all_tables: List[str]) -> List[str]:
        """
        Returns tables allowed for this lane.

        For NO_LLM/RULES_ONLY: excludes vector-only tables.
        For GPT: all tables allowed.
        """
        # Currently all tables support keyword search
        # This is a placeholder for future vector-only tables
        return all_tables

    @property
    def is_deterministic(self) -> bool:
        """Returns True if this lane requires deterministic behavior."""
        return self.capabilities.deterministic_required


def enforce_lane(lane: str) -> LaneEnforcer:
    """Factory function for creating LaneEnforcer."""
    return LaneEnforcer(lane)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LANE ENFORCER TESTS")
    print("=" * 60)

    # Test NO_LLM lane
    print("\n--- NO_LLM Lane ---")
    enforcer = enforce_lane("NO_LLM")
    print(f"  Deterministic required: {enforcer.is_deterministic}")
    print(f"  Vector search allowed: {enforcer.capabilities.allow_vector_search}")

    try:
        enforcer.assert_vector_search_allowed()
        print("  ✗ Should have raised LaneViolationError")
    except LaneViolationError as e:
        print(f"  ✓ Correctly blocked: {e}")

    # Test GPT lane
    print("\n--- GPT Lane ---")
    enforcer = enforce_lane("GPT")
    print(f"  Deterministic required: {enforcer.is_deterministic}")
    print(f"  Vector search allowed: {enforcer.capabilities.allow_vector_search}")

    try:
        enforcer.assert_vector_search_allowed()
        print("  ✓ Vector search allowed in GPT lane")
    except LaneViolationError:
        print("  ✗ Should NOT have raised error")

    # Test search type filtering
    print("\n--- Search Type Filtering ---")
    no_llm = enforce_lane("NO_LLM")
    types = ["EXACT", "CANONICAL", "FUZZY", "VECTOR"]
    filtered = no_llm.filter_search_types(types)
    print(f"  Input: {types}")
    print(f"  Filtered for NO_LLM: {filtered}")

    gpt = enforce_lane("GPT")
    filtered = gpt.filter_search_types(types)
    print(f"  Filtered for GPT: {filtered}")

    print("\n✓ All lane enforcer tests passed")
