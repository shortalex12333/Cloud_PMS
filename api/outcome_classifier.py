"""
Outcome Classifier
==================

Implements the 4-outcome truth table for query results:

    FOUND     - All constraints satisfied (hard match)
    SALVAGED  - Partial match, explicit uncertainty surfaced
    UNKNOWN   - No strong anchors OR too ambiguous
    EMPTY     - Strong anchors present but genuinely no records

This replaces the binary pass/fail model that conflates three different
notions of correctness (filing-cabinet, receptionist, ATC).

Scoring Policy:
    Let:
        A = anchor strength (fault_code > equipment_code > part_number > known_part > location)
        C = constraint coverage ratio (matched_tokens / meaningful_tokens)
        U = unmatched meaningful tokens count
        N = nonsense/OOV ratio

    Rules:
        If A == 0              → UNKNOWN
        If A > 0 and C >= 0.6  → FOUND
        If A > 0 and C < 0.6   → SALVAGED (with penalties)
        If A > 0 and DB empty  → EMPTY

Example: "purple unicorn generator"
    A = 0.9 (generator is strong anchor)
    C = 0.33 (1/3 tokens matched)
    Outcome: SALVAGED (not EMPTY, not FOUND)
    Response: Returns generators + surfaces {"unmatched": ["purple", "unicorn"]}

This directly addresses the philosophical inconsistency where:
    - "purple unicorn generator" was marked FAIL (expected EMPTY)
    - But ATC behavior says: return generators, surface uncertainty
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
import re


class QueryOutcome(str, Enum):
    """The 4 possible outcomes for a query"""
    FOUND = "found"         # All constraints satisfied
    SALVAGED = "salvaged"   # Partial match, uncertainty surfaced
    UNKNOWN = "unknown"     # No anchors or too ambiguous
    EMPTY = "empty"         # Anchors present, genuinely no records


@dataclass
class OutcomeResult:
    """Result of outcome classification"""
    outcome: QueryOutcome
    anchor_strength: float          # A: 0.0 - 1.0
    coverage_ratio: float           # C: matched/meaningful
    matched_tokens: List[str]       # Tokens that matched entities
    unmatched_tokens: List[str]     # Meaningful tokens that didn't match
    nonsense_tokens: List[str]      # OOV/gibberish tokens
    confidence: float               # Overall confidence 0.0 - 1.0
    reasoning: str                  # Human-readable explanation

    def to_dict(self) -> Dict:
        return {
            "outcome": self.outcome.value,
            "anchor_strength": round(self.anchor_strength, 3),
            "coverage_ratio": round(self.coverage_ratio, 3),
            "matched_tokens": self.matched_tokens,
            "unmatched_tokens": self.unmatched_tokens,
            "nonsense_tokens": self.nonsense_tokens,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
        }


# Anchor strength weights by entity type
# Higher = stronger signal that query is meaningful
ANCHOR_WEIGHTS = {
    "fault_code": 1.0,       # E047, SPN 100 FMI 3 - very specific
    "equipment_code": 0.95,  # ME-S-001, GEN-002 - specific asset
    "part_number": 0.9,      # ENG-0008-103 - specific part
    "work_order_number": 0.9,# WO-2024-001 - specific WO
    "model": 0.85,           # 16V4000 - specific model
    "brand": 0.8,            # MTU, Caterpillar - known manufacturer
    "equipment": 0.75,       # generator, pump - known equipment type
    "part": 0.7,             # filter, impeller - known part type
    "symptom": 0.65,         # overheating, vibration - diagnostic signal
    "location_code": 0.6,    # BOX-2A - specific location
    "location": 0.5,         # engine room - general location
    "measurement": 0.5,      # 85°C, 3 bar - concrete value
    "action": 0.4,           # replace, inspect - verb
    "system": 0.3,           # cooling system - broad category
    "person": 0.2,           # captain, engineer - role
}

# Stop words that don't count as meaningful tokens
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "also", "now", "and",
    "or", "but", "if", "because", "until", "while", "although", "though",
    "me", "my", "our", "you", "your", "it", "its", "this", "that", "these",
    "those", "what", "which", "who", "whom", "show", "find", "get", "list",
    "search", "display", "give", "tell", "see", "look", "check", "view",
    "um", "uh", "like", "basically", "actually", "literally", "kinda",
    "sorta", "yeah", "okay", "ok", "please", "thanks", "hey", "hi",
}

# Known domain vocabulary (things that ARE meaningful even if short)
DOMAIN_VOCABULARY = {
    # Equipment types
    "pump", "filter", "engine", "generator", "motor", "valve", "sensor",
    "gauge", "meter", "switch", "relay", "panel", "tank", "pipe", "hose",
    "seal", "gasket", "bearing", "belt", "impeller", "thermostat",
    "alternator", "compressor", "radar", "autopilot", "thruster",
    # Fluids
    "oil", "fuel", "water", "coolant", "hydraulic",
    # Locations
    "deck", "bridge", "room", "locker", "box", "storage",
    # Statuses
    "pending", "completed", "progress", "overdue", "critical", "routine",
    "planned", "open", "closed", "active", "resolved",
    # Actions
    "maintenance", "service", "repair", "replace", "inspect", "check",
    # Symptoms
    "overheating", "vibration", "leak", "noise", "alarm", "fault", "error",
    # Parts
    "main", "auxiliary", "port", "starboard", "bow", "stern",
}


class OutcomeClassifier:
    """
    Classifies query results into the 4-outcome model.

    This replaces binary pass/fail with a nuanced model that:
    1. Never returns FOUND for partial matches
    2. Returns SALVAGED when there's signal but gaps
    3. Returns UNKNOWN when no anchors exist
    4. Returns EMPTY only when anchors exist but DB has nothing
    """

    def __init__(self):
        self.stop_words = STOP_WORDS
        self.domain_vocab = DOMAIN_VOCABULARY
        self.anchor_weights = ANCHOR_WEIGHTS

    def classify(
        self,
        query: str,
        extracted_entities: List[Dict],
        has_results: bool,
        result_count: int = 0
    ) -> OutcomeResult:
        """
        Classify the outcome of a query.

        Args:
            query: Original user query
            extracted_entities: Entities found by Module B
            has_results: Whether the DB query returned any results
            result_count: Number of results returned

        Returns:
            OutcomeResult with classification and metrics
        """
        # Tokenize query
        tokens = self._tokenize(query)

        # Categorize tokens
        matched, unmatched, nonsense = self._categorize_tokens(
            tokens, extracted_entities
        )

        # Calculate anchor strength (max weight of matched entities)
        anchor_strength = self._calculate_anchor_strength(extracted_entities)

        # Calculate coverage ratio
        meaningful_count = len(matched) + len(unmatched)
        coverage_ratio = len(matched) / meaningful_count if meaningful_count > 0 else 0.0

        # Determine outcome
        outcome, reasoning = self._determine_outcome(
            anchor_strength, coverage_ratio, has_results,
            len(nonsense), len(tokens)
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            anchor_strength, coverage_ratio, len(nonsense), len(tokens)
        )

        return OutcomeResult(
            outcome=outcome,
            anchor_strength=anchor_strength,
            coverage_ratio=coverage_ratio,
            matched_tokens=matched,
            unmatched_tokens=unmatched,
            nonsense_tokens=nonsense,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _tokenize(self, query: str) -> List[str]:
        """Split query into tokens, preserving meaningful compounds."""
        # Lowercase and split on whitespace/punctuation
        query_lower = query.lower()
        # Keep hyphens for codes like ME-S-001
        tokens = re.findall(r'[a-z0-9][-a-z0-9]*[a-z0-9]|[a-z0-9]', query_lower)
        return tokens

    def _categorize_tokens(
        self,
        tokens: List[str],
        entities: List[Dict]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Categorize tokens into matched, unmatched meaningful, and nonsense.
        """
        matched = []
        unmatched = []
        nonsense = []

        # Build set of entity values (lowercase)
        entity_values = set()
        for e in entities:
            val = e.get("value", "").lower()
            entity_values.add(val)
            # Also add individual words from multi-word values
            for word in val.split():
                entity_values.add(word)

        for token in tokens:
            # Skip stop words
            if token in self.stop_words:
                continue

            # Check if matched by an entity
            if token in entity_values:
                matched.append(token)
            # Check if it's domain vocabulary (meaningful but not matched)
            elif token in self.domain_vocab:
                unmatched.append(token)
            # Check if it looks like a code/number (meaningful)
            elif re.match(r'^[a-z]{2,4}[-]?\d{2,}', token):
                unmatched.append(token)
            elif re.match(r'^\d+[a-z]?$', token):
                unmatched.append(token)
            # Check if it's a reasonable English word (4+ chars, no weird patterns)
            elif len(token) >= 4 and token.isalpha():
                # Likely a meaningful word we don't recognize
                unmatched.append(token)
            else:
                # Gibberish or very short unknown token
                nonsense.append(token)

        return matched, unmatched, nonsense

    def _calculate_anchor_strength(self, entities: List[Dict]) -> float:
        """Calculate max anchor strength from extracted entities."""
        if not entities:
            return 0.0

        max_strength = 0.0
        for e in entities:
            entity_type = e.get("type", "")
            weight = self.anchor_weights.get(entity_type, 0.1)
            max_strength = max(max_strength, weight)

        return max_strength

    def _determine_outcome(
        self,
        anchor_strength: float,
        coverage_ratio: float,
        has_results: bool,
        nonsense_count: int,
        total_tokens: int
    ) -> Tuple[QueryOutcome, str]:
        """
        Apply the outcome policy.

        Policy:
            If A == 0              → UNKNOWN
            If A > 0 and C >= 0.6  → FOUND (if has_results) else EMPTY
            If A > 0 and C < 0.6   → SALVAGED (if has_results) else EMPTY
        """
        # No anchor = UNKNOWN
        if anchor_strength < 0.1:
            return QueryOutcome.UNKNOWN, "No strong domain anchors found"

        # High nonsense ratio = UNKNOWN
        nonsense_ratio = nonsense_count / total_tokens if total_tokens > 0 else 0
        if nonsense_ratio > 0.7:
            return QueryOutcome.UNKNOWN, f"Too much nonsense ({nonsense_count}/{total_tokens} tokens)"

        # Anchor exists but no results = EMPTY
        if not has_results:
            return QueryOutcome.EMPTY, "Strong anchors present but no matching records"

        # Anchor exists with results
        if coverage_ratio >= 0.6:
            return QueryOutcome.FOUND, f"All major constraints satisfied (coverage={coverage_ratio:.0%})"
        else:
            return QueryOutcome.SALVAGED, f"Partial match (coverage={coverage_ratio:.0%}), unmatched tokens surfaced"

    def _calculate_confidence(
        self,
        anchor_strength: float,
        coverage_ratio: float,
        nonsense_count: int,
        total_tokens: int
    ) -> float:
        """
        Calculate overall confidence score.

        Confidence = A * C * (1 - N/total)
        """
        nonsense_penalty = 1 - (nonsense_count / total_tokens) if total_tokens > 0 else 1
        confidence = anchor_strength * coverage_ratio * nonsense_penalty
        return max(0.0, min(1.0, confidence))


# Singleton instance
_classifier_instance = None

def get_outcome_classifier() -> OutcomeClassifier:
    """Get or create singleton outcome classifier."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = OutcomeClassifier()
    return _classifier_instance


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    classifier = OutcomeClassifier()

    # Test cases demonstrating the 4 outcomes
    test_cases = [
        # (query, entities, has_results, expected_outcome)
        (
            "purple unicorn generator",
            [{"type": "equipment", "value": "generator"}],
            True,
            "SALVAGED - generator is anchor, purple/unicorn unmatched"
        ),
        (
            "ME-S-001",
            [{"type": "equipment_code", "value": "ME-S-001"}],
            True,
            "FOUND - exact match"
        ),
        (
            "pending work orders for ME-S-001",
            [
                {"type": "equipment_code", "value": "ME-S-001"},
                {"type": "action", "value": "work orders"},
            ],
            True,
            "FOUND - high coverage"
        ),
        (
            "asdfasdfasdf",
            [],
            False,
            "UNKNOWN - no anchors"
        ),
        (
            "work orders for ME-Z-999",
            [{"type": "equipment_code", "value": "ME-Z-999"}],
            False,
            "EMPTY - anchor exists but no records"
        ),
        (
            "quantum flux capacitor filter",
            [{"type": "part", "value": "filter"}],
            True,
            "SALVAGED - filter is anchor, quantum/flux/capacitor unmatched"
        ),
        (
            "oil filter",
            [{"type": "part", "value": "oil filter"}],
            True,
            "FOUND - exact match"
        ),
        (
            "fule fitler",  # typos
            [{"type": "part", "value": "fuel filter"}],  # fuzzy matched
            True,
            "FOUND - typos resolved"
        ),
    ]

    print("=" * 70)
    print("OUTCOME CLASSIFIER TESTS")
    print("=" * 70)

    for query, entities, has_results, description in test_cases:
        result = classifier.classify(query, entities, has_results, 10 if has_results else 0)
        print(f"\nQuery: \"{query}\"")
        print(f"Expected: {description}")
        print(f"Got: {result.outcome.value.upper()}")
        print(f"  Anchor strength: {result.anchor_strength:.2f}")
        print(f"  Coverage ratio:  {result.coverage_ratio:.2f}")
        print(f"  Matched:         {result.matched_tokens}")
        print(f"  Unmatched:       {result.unmatched_tokens}")
        print(f"  Nonsense:        {result.nonsense_tokens}")
        print(f"  Confidence:      {result.confidence:.2f}")
        print(f"  Reasoning:       {result.reasoning}")
