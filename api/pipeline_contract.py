"""
Pipeline Contract
=================

This file defines the CONTRACT that all pipeline components must follow.
It ensures consistent behavior across all 34 files in the query pipeline.

PHILOSOPHY: RECEPTIONIST MODEL
    - Surface EXACTLY what the user asks for
    - Minimal assumption - never invent entities
    - "2c AND 2b" = BOTH locations (explicit conjunction)
    - Humans are chaotic but purposeful - always assume there's a reason
    - If query has signal, return results + surface what couldn't be matched

SUCCESS CRITERION: TOP-3
    - If correct answer is in top 3 results, it's a SUCCESS
    - Ranking optimization will move it to position 1 later
    - Position 3 is NOT a failure for edge cases

4-OUTCOME MODEL:
    - FOUND: All constraints satisfied, high confidence
    - SALVAGED: Partial match, uncertainty surfaced (unmatched_tokens visible)
    - UNKNOWN: No strong anchors, needs clarification
    - EMPTY: Strong anchors present, genuinely no records in DB

CONJUNCTION SEMANTICS:
    - Default: AND (multi-token = all must match)
    - Explicit "or": OR semantics
    - Explicit "and" between locations: IN semantics (both)
    - "not", "except", "excluding": NOT semantics

NEVER:
    - Never assume missing entities
    - Never return FOUND for partial matches
    - Never silently drop unmatched tokens
    - Never treat position > 1 as automatic failure

ALWAYS:
    - Always surface unmatched_tokens in response metadata
    - Always include anchor_strength and coverage_ratio
    - Always preserve original query for debugging
    - Always track which module contributed each entity
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum


# =============================================================================
# OUTCOME MODEL
# =============================================================================

class QueryOutcome(str, Enum):
    """The 4 possible query outcomes"""
    FOUND = "found"         # All constraints satisfied
    SALVAGED = "salvaged"   # Partial match, uncertainty surfaced
    UNKNOWN = "unknown"     # No anchors, needs clarification
    EMPTY = "empty"         # Anchors present, no DB records


# =============================================================================
# CONJUNCTION SEMANTICS
# =============================================================================

class ConjunctionType(str, Enum):
    """How multiple tokens/entities combine"""
    AND = "and"             # All must match (default for multi-token)
    OR = "or"               # Any can match (explicit "or")
    IN = "in"               # Set membership (locations: "2a and 2b")
    NOT = "not"             # Exclusion (explicit "not", "except")


@dataclass
class ConjunctionRule:
    """Parsed conjunction from query"""
    conjunction_type: ConjunctionType
    operands: List[str]
    raw_text: str           # Original text that triggered this rule


# =============================================================================
# PIPELINE RESULT CONTRACT
# =============================================================================

@dataclass
class PipelineResult:
    """
    The contract that ALL pipeline stages must return.

    This ensures consistent handling across all 34 files.
    Every handler MUST populate these fields.
    """
    # Core outcome
    outcome: QueryOutcome

    # What was matched
    matched_entities: List[Dict] = field(default_factory=list)
    matched_tokens: List[str] = field(default_factory=list)

    # What WASN'T matched (MUST be surfaced to user)
    unmatched_tokens: List[str] = field(default_factory=list)
    unmatched_entities: List[str] = field(default_factory=list)

    # Scoring (for ranking)
    anchor_strength: float = 0.0      # 0.0 - 1.0
    coverage_ratio: float = 0.0       # matched / meaningful
    confidence: float = 0.0           # overall confidence

    # Conjunction handling
    conjunctions: List[ConjunctionRule] = field(default_factory=list)

    # Results (position matters for top-3 criterion)
    results: List[Dict] = field(default_factory=list)
    total_count: int = 0

    # Debug/audit trail
    original_query: str = ""
    modules_used: List[str] = field(default_factory=list)
    stage_timings: Dict[str, float] = field(default_factory=dict)

    # Human-readable explanation
    reasoning: str = ""

    def is_success(self, expected_entity_id: Optional[str] = None) -> bool:
        """
        TOP-3 SUCCESS CRITERION

        Returns True if:
        1. outcome is FOUND or SALVAGED (we returned something)
        2. If expected_entity_id provided, it's in top 3 results

        Position 3 is NOT a failure - ranking will optimize later.
        """
        if self.outcome in (QueryOutcome.UNKNOWN, QueryOutcome.EMPTY):
            return False

        if expected_entity_id is None:
            # No specific expectation - just having results is success
            return len(self.results) > 0

        # Check if expected entity is in top 3
        for i, result in enumerate(self.results[:3]):
            result_id = result.get("id") or result.get("entity_id") or result.get("code")
            if result_id == expected_entity_id:
                return True
            # Also check nested data
            if "data" in result:
                data_id = result["data"].get("id") or result["data"].get("code")
                if data_id == expected_entity_id:
                    return True

        return False

    def get_position(self, entity_id: str) -> Optional[int]:
        """Get 1-indexed position of entity in results, or None if not found."""
        for i, result in enumerate(self.results):
            result_id = result.get("id") or result.get("entity_id") or result.get("code")
            if result_id == entity_id:
                return i + 1
            if "data" in result:
                data_id = result["data"].get("id") or result["data"].get("code")
                if data_id == entity_id:
                    return i + 1
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response / logging."""
        return {
            "outcome": self.outcome.value,
            "matched_entities": self.matched_entities,
            "matched_tokens": self.matched_tokens,
            "unmatched_tokens": self.unmatched_tokens,  # MUST be surfaced
            "unmatched_entities": self.unmatched_entities,
            "anchor_strength": round(self.anchor_strength, 3),
            "coverage_ratio": round(self.coverage_ratio, 3),
            "confidence": round(self.confidence, 3),
            "conjunctions": [
                {
                    "type": c.conjunction_type.value,
                    "operands": c.operands,
                    "raw": c.raw_text
                }
                for c in self.conjunctions
            ],
            "result_count": len(self.results),
            "total_count": self.total_count,
            "reasoning": self.reasoning,
            "modules_used": self.modules_used,
        }


# =============================================================================
# CONJUNCTION PARSER
# =============================================================================

import re

class ConjunctionParser:
    """
    Parses explicit conjunctions from user queries.

    RULES:
    - "X and Y" between locations → IN (both)
    - "X or Y" → OR (either)
    - "not X", "except X", "excluding X" → NOT
    - Multiple tokens without conjunction → AND (all must match)

    NEVER assume implicit OR for multi-token phrases.
    "fuel filter" = fuel AND filter, not fuel OR filter.
    """

    # Patterns for explicit conjunctions
    LOCATION_AND_PATTERN = re.compile(
        r'\b(box|locker|deck|storage)\s*(\w+)\s+and\s+(box|locker|deck|storage)?\s*(\w+)',
        re.IGNORECASE
    )

    OR_PATTERN = re.compile(
        r'\b(\w+)\s+or\s+(\w+)\b',
        re.IGNORECASE
    )

    NOT_PATTERNS = [
        re.compile(r'\bnot\s+(?:in\s+)?(\w+)', re.IGNORECASE),
        re.compile(r'\bexcept\s+(\w+)', re.IGNORECASE),
        re.compile(r'\bexcluding\s+(\w+)', re.IGNORECASE),
        re.compile(r'\bother\s+than\s+(\w+)', re.IGNORECASE),
    ]

    def parse(self, query: str) -> List[ConjunctionRule]:
        """
        Extract all conjunction rules from query.

        Example:
            "inventory in box 2a and 2b"
            → [ConjunctionRule(IN, ["box 2a", "box 2b"], "box 2a and 2b")]

            "filter or pump"
            → [ConjunctionRule(OR, ["filter", "pump"], "filter or pump")]

            "parts not in locker"
            → [ConjunctionRule(NOT, ["locker"], "not in locker")]
        """
        rules = []

        # Check for location AND (IN semantics)
        for match in self.LOCATION_AND_PATTERN.finditer(query):
            loc1_type = match.group(1)
            loc1_id = match.group(2)
            loc2_type = match.group(3) or loc1_type  # Inherit type if not specified
            loc2_id = match.group(4)

            rules.append(ConjunctionRule(
                conjunction_type=ConjunctionType.IN,
                operands=[f"{loc1_type} {loc1_id}", f"{loc2_type} {loc2_id}"],
                raw_text=match.group(0)
            ))

        # Check for explicit OR
        for match in self.OR_PATTERN.finditer(query):
            # Skip if this is part of a location AND we already captured
            if any(match.group(0) in r.raw_text for r in rules):
                continue

            rules.append(ConjunctionRule(
                conjunction_type=ConjunctionType.OR,
                operands=[match.group(1), match.group(2)],
                raw_text=match.group(0)
            ))

        # Check for NOT patterns
        for pattern in self.NOT_PATTERNS:
            for match in pattern.finditer(query):
                rules.append(ConjunctionRule(
                    conjunction_type=ConjunctionType.NOT,
                    operands=[match.group(1)],
                    raw_text=match.group(0)
                ))

        return rules


# =============================================================================
# CONTRADICTION DETECTOR
# =============================================================================

class ContradictionDetector:
    """
    Detects mutually exclusive filter combinations.

    "pending completed" → CONTRADICTION (status can't be both)
    "out of stock with quantity 10" → CONTRADICTION
    """

    # Mutually exclusive groups
    EXCLUSIVE_GROUPS = {
        "status": {"pending", "planned", "in_progress", "in progress", "completed", "closed", "open"},
        "priority": {"critical", "routine", "high", "low", "urgent"},
        "stock": {"out of stock", "in stock", "low stock", "out_of_stock", "in_stock", "low_stock"},
    }

    # Known contradictory patterns
    CONTRADICTIONS = [
        ({"pending", "completed"}, "status"),
        ({"in_progress", "completed"}, "status"),
        ({"in progress", "completed"}, "status"),
        ({"pending", "in_progress"}, "status"),
        ({"pending", "in progress"}, "status"),
        ({"open", "closed"}, "status"),
        ({"critical", "routine"}, "priority"),
        ({"out_of_stock", "in_stock"}, "stock"),
        ({"out of stock", "in stock"}, "stock"),
    ]

    def detect(self, filters: Dict[str, Any]) -> Optional[str]:
        """
        Check if filters contain contradictions.

        Returns None if no contradiction, or a string explaining the contradiction.
        """
        # Collect all filter values
        values = set()
        for key, val in filters.items():
            if isinstance(val, str):
                values.add(val.lower().replace(" ", "_"))
            elif isinstance(val, dict) and "value" in val:
                values.add(str(val["value"]).lower().replace(" ", "_"))

        # Check for known contradictions
        for contradictory_set, group_name in self.CONTRADICTIONS:
            matches = values & contradictory_set
            if len(matches) >= 2:
                return f"Contradictory {group_name}: {matches} are mutually exclusive"

        return None

    def detect_in_query(self, query: str) -> Optional[str]:
        """
        Check if query text contains contradictory keywords.

        This catches cases like "pending completed" where both words appear
        but only one gets extracted as a filter.
        """
        query_lower = query.lower()

        # Check for contradictory status words in query
        for contradictory_set, group_name in self.CONTRADICTIONS:
            matches = set()
            for word in contradictory_set:
                # Use word boundary to avoid false positives
                word_normalized = word.replace("_", " ")
                if re.search(r'\b' + re.escape(word_normalized) + r'\b', query_lower):
                    matches.add(word)
            if len(matches) >= 2:
                return f"Contradictory {group_name}: {matches} are mutually exclusive"

        return None


# =============================================================================
# TEST SUCCESS EVALUATOR
# =============================================================================

class TestEvaluator:
    """
    Evaluates test success using the TOP-3 CRITERION.

    A test is successful if:
    1. For FOUND/SALVAGED outcomes: expected answer is in top 3 results
    2. For EMPTY outcomes: we expected empty AND query had strong anchors
    3. For UNKNOWN outcomes: query genuinely had no anchors

    Position 3 is NOT a failure - ranking optimization will fix later.
    """

    def evaluate(
        self,
        result: PipelineResult,
        expected_outcome: QueryOutcome,
        expected_entity_id: Optional[str] = None,
        expected_empty: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate a test case.

        Returns:
            {
                "success": bool,
                "reason": str,
                "position": int or None,
                "outcome_match": bool,
            }
        """
        # Check outcome match
        outcome_match = result.outcome == expected_outcome

        # Special case: SALVAGED is acceptable when FOUND was expected
        # (because ranking isn't optimized yet)
        if expected_outcome == QueryOutcome.FOUND and result.outcome == QueryOutcome.SALVAGED:
            outcome_match = True  # Acceptable

        # For EMPTY/UNKNOWN, just check outcome
        if expected_outcome in (QueryOutcome.EMPTY, QueryOutcome.UNKNOWN):
            return {
                "success": outcome_match,
                "reason": f"Expected {expected_outcome.value}, got {result.outcome.value}",
                "position": None,
                "outcome_match": outcome_match,
            }

        # For FOUND/SALVAGED, check top-3 criterion
        if expected_entity_id:
            position = result.get_position(expected_entity_id)
            in_top_3 = position is not None and position <= 3

            if in_top_3:
                return {
                    "success": True,
                    "reason": f"Found at position {position} (top-3 success)",
                    "position": position,
                    "outcome_match": outcome_match,
                }
            else:
                return {
                    "success": False,
                    "reason": f"Expected entity not in top 3 (position: {position})",
                    "position": position,
                    "outcome_match": outcome_match,
                }

        # No specific entity expected, just check we have results
        has_results = len(result.results) > 0
        return {
            "success": has_results and result.outcome != QueryOutcome.EMPTY,
            "reason": f"Has {len(result.results)} results" if has_results else "No results",
            "position": None,
            "outcome_match": outcome_match,
        }


# =============================================================================
# SINGLETON INSTANCES
# =============================================================================

_conjunction_parser = None
_contradiction_detector = None
_test_evaluator = None

def get_conjunction_parser() -> ConjunctionParser:
    global _conjunction_parser
    if _conjunction_parser is None:
        _conjunction_parser = ConjunctionParser()
    return _conjunction_parser

def get_contradiction_detector() -> ContradictionDetector:
    global _contradiction_detector
    if _contradiction_detector is None:
        _contradiction_detector = ContradictionDetector()
    return _contradiction_detector

def get_test_evaluator() -> TestEvaluator:
    global _test_evaluator
    if _test_evaluator is None:
        _test_evaluator = TestEvaluator()
    return _test_evaluator


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PIPELINE CONTRACT TESTS")
    print("=" * 70)

    # Test conjunction parsing
    print("\n1. CONJUNCTION PARSING")
    print("-" * 50)

    parser = ConjunctionParser()

    conjunction_tests = [
        "inventory in box 2a and 2b",
        "inventory in box 2a and box 2c",
        "parts in deck 1 or deck 2",
        "filter or pump",
        "inventory not in locker",
        "parts except filters",
        "equipment excluding generators",
        "items other than pumps",
    ]

    for query in conjunction_tests:
        rules = parser.parse(query)
        print(f"\nQuery: \"{query}\"")
        for rule in rules:
            print(f"  → {rule.conjunction_type.value}: {rule.operands}")

    # Test contradiction detection
    print("\n\n2. CONTRADICTION DETECTION")
    print("-" * 50)

    detector = ContradictionDetector()

    contradiction_tests = [
        {"status": "pending", "priority": "critical"},  # OK
        {"status": "pending", "status2": "completed"},  # Not detected (different keys)
        {"filters": ["pending", "completed"]},  # Not detected (list)
    ]

    # Test with actual filter structure
    test_filters = {
        "status": {"value": "pending"},
        "other_status": {"value": "completed"},
    }
    result = detector.detect(test_filters)
    print(f"Filters: {test_filters}")
    print(f"Contradiction: {result}")

    # Test top-3 success criterion
    print("\n\n3. TOP-3 SUCCESS CRITERION")
    print("-" * 50)

    evaluator = TestEvaluator()

    # Create test result with entity at position 3
    test_result = PipelineResult(
        outcome=QueryOutcome.SALVAGED,
        results=[
            {"id": "wrong-1"},
            {"id": "wrong-2"},
            {"id": "correct-answer"},  # Position 3
            {"id": "wrong-4"},
        ],
        anchor_strength=0.7,
        coverage_ratio=0.5,
    )

    eval_result = evaluator.evaluate(
        test_result,
        expected_outcome=QueryOutcome.FOUND,
        expected_entity_id="correct-answer"
    )

    print(f"Result has correct answer at position 3")
    print(f"Success: {eval_result['success']}")
    print(f"Reason: {eval_result['reason']}")

    # Test with entity at position 4 (should fail)
    test_result_4 = PipelineResult(
        outcome=QueryOutcome.SALVAGED,
        results=[
            {"id": "wrong-1"},
            {"id": "wrong-2"},
            {"id": "wrong-3"},
            {"id": "correct-answer"},  # Position 4
        ],
    )

    eval_result_4 = evaluator.evaluate(
        test_result_4,
        expected_outcome=QueryOutcome.FOUND,
        expected_entity_id="correct-answer"
    )

    print(f"\nResult has correct answer at position 4")
    print(f"Success: {eval_result_4['success']}")
    print(f"Reason: {eval_result_4['reason']}")

    print("\n" + "=" * 70)
    print("CONTRACT TESTS COMPLETE")
    print("=" * 70)
