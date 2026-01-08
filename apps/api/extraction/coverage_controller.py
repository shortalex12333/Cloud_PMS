#!/usr/bin/env python3
"""
Stage 2: Coverage Controller
Decides whether AI extraction is needed based on coverage and patterns
"""

import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass


@dataclass
class CoverageDecision:
    """Decision on whether AI extraction is needed."""
    needs_ai: bool
    coverage: float
    uncovered_spans: List[Tuple[int, int]]
    reason: str
    unknown_ratio: float
    has_negation: bool
    has_instruction: bool
    has_conflicts: bool


class CoverageController:
    """Controls when to invoke AI extraction."""

    # Thresholds for AI invocation (Balanced: Precision over Recall)
    # CRITICAL FIX: Lowered from 0.95 to prevent forcing contaminated AI
    # 85% allows legitimate queries like "main engine 3512C" (75% coverage) to skip AI
    COVERAGE_THRESHOLD = 0.85  # Balanced threshold - high quality regex should be trusted
    UNKNOWN_RATIO_THRESHOLD = 0.10  # Balanced - allow some unknowns before AI trigger

    # Patterns that trigger AI
    NEGATION_PATTERNS = [
        r'\bdo\s+not\b',
        r'\bdon\'t\b',
        r'\bnever\b',
        r'\bavoid\b',
        r'\bno\s+\w+ing\b',  # "no resetting", "no starting"
        r'\bwithout\b',
        r'\bunless\b'
    ]

    INSTRUCTION_PATTERNS = [
        r'\bplease\b',
        r'\bcheck\b',
        r'\brefer\s+to\b',
        r'\bsee\b',
        r'\bensure\b',
        r'\bmake\s+sure\b',
        r'\bverify\b',
        r'\bconfirm\b'
    ]

    def __init__(self):
        self.negation_regex = re.compile('|'.join(self.NEGATION_PATTERNS), re.IGNORECASE)
        self.instruction_regex = re.compile('|'.join(self.INSTRUCTION_PATTERNS), re.IGNORECASE)

    def decide(self, cleaned_text: Dict, entities: List,
               original_text: str = None) -> CoverageDecision:
        """
        Decide whether AI extraction is needed.

        Args:
            cleaned_text: Output from TextCleaner
            entities: List of Entity objects from regex extraction
            original_text: Original input text (for semantic analysis)

        Returns:
            CoverageDecision with needs_ai flag and metadata
        """
        text = cleaned_text['normalized']
        tokens = cleaned_text['tokens']
        token_spans = cleaned_text['token_spans']

        # Compute coverage
        covered_spans = [(e.span[0], e.span[1]) for e in entities if e.span]
        coverage = self._compute_coverage(tokens, token_spans, covered_spans, text)

        # Find uncovered spans
        uncovered_spans = self._find_uncovered_spans(text, covered_spans)

        # Check for unknown terms
        unknown_ratio = self._compute_unknown_ratio(text, tokens, covered_spans)

        # Check for semantic patterns
        has_negation = bool(self.negation_regex.search(text))
        has_instruction = bool(self.instruction_regex.search(text))

        # Check for conflicts
        has_conflicts = self._detect_conflicts(entities)

        # Decision logic
        needs_ai = False
        reason = "coverage_sufficient"

        # Rule 1: Low coverage
        if coverage < self.COVERAGE_THRESHOLD:
            needs_ai = True
            reason = f"low_coverage_{coverage:.2f}"

        # Rule 2: High unknown ratio
        elif unknown_ratio >= self.UNKNOWN_RATIO_THRESHOLD:
            needs_ai = True
            reason = f"high_unknown_ratio_{unknown_ratio:.2f}"

        # Rule 3: Semantic patterns (negation/instruction)
        elif has_negation or has_instruction:
            needs_ai = True
            reason = "semantic_pattern"
            if has_negation:
                reason += "_negation"
            if has_instruction:
                reason += "_instruction"

        # Rule 4: Entity conflicts
        elif has_conflicts:
            needs_ai = True
            reason = "entity_conflicts"

        # Rule 5: Special cases (very short text with meaning)
        elif len(tokens) <= 3 and len(tokens) > 0:
            # Short but potentially meaningful text
            if coverage < 0.9:  # Higher threshold for short text
                needs_ai = True
                reason = "short_text_incomplete"

        return CoverageDecision(
            needs_ai=needs_ai,
            coverage=coverage,
            uncovered_spans=uncovered_spans,
            reason=reason,
            unknown_ratio=unknown_ratio,
            has_negation=has_negation,
            has_instruction=has_instruction,
            has_conflicts=has_conflicts
        )

    def _compute_coverage(self, tokens: List[str], token_spans: List[Tuple[int, int]],
                         covered_spans: List[Tuple[int, int]], text: str) -> float:
        """
        Compute coverage as ratio of covered tokens to total meaningful tokens.
        """
        if not tokens:
            return 1.0  # Empty text is fully covered

        # Create coverage mask
        text_len = len(text)
        covered = [False] * text_len

        # Mark extracted spans as covered
        for start, end in covered_spans:
            for i in range(max(0, start), min(text_len, end)):
                covered[i] = True

        # Count covered tokens
        covered_tokens = 0
        for token, (start, end) in zip(tokens, token_spans):
            # Token is covered if >50% of its characters are covered
            chars_covered = sum(covered[start:end])
            if chars_covered > (end - start) / 2:
                covered_tokens += 1

        return covered_tokens / len(tokens) if tokens else 1.0

    def _find_uncovered_spans(self, text: str, covered_spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Find continuous spans of text not covered by extraction.
        """
        if not text:
            return []

        text_len = len(text)
        covered = [False] * text_len

        # Mark covered regions
        for start, end in covered_spans:
            for i in range(max(0, start), min(text_len, end)):
                covered[i] = True

        # Find uncovered spans
        uncovered = []
        span_start = None

        for i, is_covered in enumerate(covered):
            if not is_covered:
                if span_start is None:
                    span_start = i
            else:
                if span_start is not None:
                    # Only include meaningful uncovered spans (not just whitespace)
                    span_text = text[span_start:i].strip()
                    if span_text and len(span_text) >= 3:
                        uncovered.append((span_start, i))
                    span_start = None

        # Handle trailing uncovered text
        if span_start is not None:
            span_text = text[span_start:].strip()
            if span_text and len(span_text) >= 3:
                uncovered.append((span_start, text_len))

        # Merge adjacent spans with small gaps
        merged = []
        for start, end in uncovered:
            if merged and start - merged[-1][1] <= 5:
                # Merge with previous span
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))

        return merged

    def _compute_unknown_ratio(self, text: str, tokens: List[str],
                               covered_spans: List[Tuple[int, int]]) -> float:
        """
        Compute ratio of potentially important unknown terms.
        """
        if not tokens:
            return 0.0

        # Find tokens that might be important but aren't extracted
        uncovered_important = 0

        for token in tokens:
            # Check if token looks important (capitalized, has numbers, etc.)
            is_important = (
                token[0].isupper() or  # Capitalized
                any(c.isdigit() for c in token) or  # Contains numbers
                len(token) >= 6 or  # Longer words
                '-' in token or '_' in token  # Compound terms
            )

            if is_important:
                # Check if this token is covered
                token_lower = token.lower()
                is_covered = any(
                    token_lower in text[start:end].lower()
                    for start, end in covered_spans
                )

                if not is_covered:
                    uncovered_important += 1

        return uncovered_important / len(tokens) if tokens else 0.0

    def _detect_conflicts(self, entities: List) -> bool:
        """
        Detect conflicting entities that might need AI resolution.
        """
        # Group entities by type
        by_type = {}
        for entity in entities:
            if entity.type not in by_type:
                by_type[entity.type] = []
            by_type[entity.type].append(entity)

        # Check for conflicts
        # Example: Multiple different measurements of same type close together
        if 'measurement' in by_type:
            measurements = by_type['measurement']
            if len(measurements) >= 2:
                # Check if measurements are close but different
                for i, m1 in enumerate(measurements):
                    for m2 in measurements[i+1:]:
                        if m1.span and m2.span:
                            distance = abs(m1.span[0] - m2.span[0])
                            if distance < 50:  # Close proximity
                                # Check if they're different values
                                if m1.text != m2.text:
                                    # Could be conflicting readings
                                    return True

        # Check for overlapping entities of different types
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                if e1.span and e2.span and e1.type != e2.type:
                    # Check for overlap
                    if (e1.span[0] < e2.span[1] and e2.span[0] < e1.span[1]):
                        return True

        return False