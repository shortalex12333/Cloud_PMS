"""
Micro-Action Extraction Pipeline
=================================

4-Stage Pipeline Architecture (parallel to maritime entity extractor):
1. Stage 1: Regex Extraction (deterministic patterns)
2. Stage 2: Gazetteer Lookup (synonym/abbreviation mapping)
3. Stage 3: AI Extraction (fallback for complex/ambiguous queries)
4. Stage 4: Merging & Deduplication (combine results, remove duplicates)

This extractor detects MULTIPLE micro-actions in a single user query.
Examples:
  - "create work order" → ["create_work_order"]
  - "add to handover and create wo" → ["add_to_handover", "create_work_order"]
  - "show all open wos" → ["list_work_orders"]
"""

import re
import json
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MicroActionMatch:
    """Represents a detected micro-action with metadata"""
    action_name: str
    confidence: float
    source: str  # 'regex', 'gazetteer', 'ai'
    match_text: str
    start_pos: int
    end_pos: int

    def to_dict(self):
        return {
            'action_name': self.action_name,
            'confidence': self.confidence,
            'source': self.source,
            'match_text': self.match_text,
            'span': [self.start_pos, self.end_pos]
        }


class MicroActionExtractor:
    """
    Main extractor class following 4-stage pipeline architecture.
    Loads patterns once at initialization for performance.
    """

    def __init__(self, patterns_path: Optional[str] = None):
        """Initialize extractor and load patterns"""
        if patterns_path is None:
            # Default to api/microaction_patterns.json
            base_dir = Path(__file__).parent
            patterns_path = base_dir / 'microaction_patterns.json'

        self.patterns = self._load_patterns(patterns_path)
        self.compiled_patterns = self._compile_patterns()
        self.gazetteer = self._build_gazetteer()

        # Source multipliers (same as maritime extractor)
        self.source_multipliers = {
            'regex': 1.0,
            'gazetteer': 0.95,
            'ai': 0.70
        }

        # Confidence threshold for AI fallback
        self.regex_confidence_threshold = 0.80

    def _load_patterns(self, patterns_path: Path) -> Dict:
        """Load micro-action patterns from JSON"""
        with open(patterns_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _compile_patterns(self) -> Dict[str, List[Tuple[re.Pattern, float]]]:
        """Compile regex patterns for each action"""
        compiled = {}

        # Get actions from the 'actions' key in the JSON
        actions = self.patterns.get('actions', {})

        for action_name, action_data in actions.items():
            patterns_list = []
            weight = action_data.get('weight', 1.0)

            for pattern_str in action_data.get('patterns', []):
                try:
                    # Compile with IGNORECASE for robustness
                    compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                    patterns_list.append((compiled_pattern, weight))
                except re.error as e:
                    print(f"Warning: Failed to compile pattern for {action_name}: {pattern_str} - {e}")

            if patterns_list:
                compiled[action_name] = patterns_list

        return compiled

    def _build_gazetteer(self) -> Dict[str, str]:
        """
        Build gazetteer mapping synonyms/abbreviations to canonical action names.
        Similar to maritime extractor's canonical term mapping.
        """
        gazetteer = {}

        # Get actions from the 'actions' key in the JSON
        actions = self.patterns.get('actions', {})

        for action_name, action_data in actions.items():
            # Map synonyms
            for synonym in action_data.get('synonyms', []):
                gazetteer[synonym.lower()] = action_name

            # Map abbreviations
            for abbrev in action_data.get('abbreviations', []):
                gazetteer[abbrev.lower()] = action_name

            # Map verbs combined with key terms
            verbs = action_data.get('verbs', [])
            category = action_data.get('category', '')

            # Example: "create" + "work order" → "create_work_order"
            if category == 'work_orders' and verbs:
                for verb in verbs:
                    gazetteer[f"{verb} work order"] = action_name
                    gazetteer[f"{verb} wo"] = action_name

            if category == 'handover' and verbs:
                for verb in verbs:
                    gazetteer[f"{verb} handover"] = action_name
                    gazetteer[f"{verb} hor"] = action_name

        return gazetteer

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning (similar to maritime text_cleaner)"""
        # Convert to lowercase
        text = text.lower()

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep alphanumeric, spaces, and basic punctuation
        text = re.sub(r'[^\w\s\-/]', ' ', text)

        return text.strip()

    def _detect_conjunctions(self, text: str) -> List[int]:
        """
        Detect conjunction positions to split multi-action queries.
        Returns list of positions where conjunctions occur.
        """
        conjunction_patterns = self.patterns.get('conjunctions', {}).get('patterns', [])
        positions = []

        for pattern_str in conjunction_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(text):
                positions.append(match.start())

        return sorted(positions)

    def _stage1_regex_extraction(self, text: str) -> List[MicroActionMatch]:
        """
        Stage 1: Regex-based extraction (deterministic, fast, 85% accuracy target)
        Detects multiple actions in single query.
        """
        matches = []
        cleaned_text = self._clean_text(text)

        for action_name, pattern_weight_list in self.compiled_patterns.items():
            for pattern, weight in pattern_weight_list:
                for match in pattern.finditer(cleaned_text):
                    # Base confidence from weight
                    confidence = min(weight / 5.0, 1.0)  # Normalize to 0-1 scale

                    # Boost confidence for exact matches
                    match_text = match.group(0)
                    if len(match_text) > 15:  # Longer matches are more specific
                        confidence = min(confidence * 1.1, 1.0)

                    matches.append(MicroActionMatch(
                        action_name=action_name,
                        confidence=confidence * self.source_multipliers['regex'],
                        source='regex',
                        match_text=match_text,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))

        return matches

    def _stage2_gazetteer_lookup(self, text: str) -> List[MicroActionMatch]:
        """
        Stage 2: Gazetteer lookup for synonyms and abbreviations
        Maps common phrases to canonical action names.
        """
        matches = []
        cleaned_text = self._clean_text(text)

        # Check for multi-word phrases first (longer matches take priority)
        sorted_terms = sorted(self.gazetteer.keys(), key=len, reverse=True)

        # Track already matched spans to avoid duplicates
        matched_spans = set()

        for term in sorted_terms:
            # Use word boundary regex to avoid substring matches
            # e.g., "po" won't match in "report"
            pattern = r'\b' + re.escape(term) + r'\b'
            for match in re.finditer(pattern, cleaned_text, re.IGNORECASE):
                action_name = self.gazetteer[term]
                start_pos = match.start()
                end_pos = match.end()

                # Skip if this span overlaps with already matched span
                span = (start_pos, end_pos)
                if span not in matched_spans:
                    matches.append(MicroActionMatch(
                        action_name=action_name,
                        confidence=0.85 * self.source_multipliers['gazetteer'],
                        source='gazetteer',
                        match_text=match.group(0),
                        start_pos=start_pos,
                        end_pos=end_pos
                    ))
                    matched_spans.add(span)

        return matches

    def _stage3_ai_extraction(self, text: str) -> List[MicroActionMatch]:
        """
        Stage 3: AI-based extraction fallback for complex/ambiguous queries.

        NOTE: This is a placeholder. In production, this would call:
        - OpenAI/Claude API with few-shot examples
        - Custom fine-tuned classifier
        - Embedding-based similarity search

        For MVP, we return empty list (regex + gazetteer cover 85%+ cases).
        """
        # TODO: Implement AI fallback using OpenAI/Claude API
        # For now, return empty list
        return []

    def _stage4_merge_and_deduplicate(self, matches: List[MicroActionMatch]) -> List[str]:
        """
        Stage 4: Merge overlapping matches and deduplicate.
        Returns list of unique canonical action names.

        Deduplication strategy:
        1. Group matches by action_name
        2. For each group, keep the highest confidence match
        3. Handle overlapping spans (choose higher confidence)
        4. Return sorted list of unique action names
        """
        if not matches:
            return []

        # Sort by confidence (descending)
        matches = sorted(matches, key=lambda m: m.confidence, reverse=True)

        # Remove overlapping matches (keep higher confidence)
        filtered_matches = []
        occupied_spans = []

        for match in matches:
            # Check if this match overlaps with any already selected match
            overlaps = False
            for start, end in occupied_spans:
                # Check for overlap
                if not (match.end_pos <= start or match.start_pos >= end):
                    overlaps = True
                    break

            if not overlaps:
                filtered_matches.append(match)
                occupied_spans.append((match.start_pos, match.end_pos))

        # Deduplicate by action_name (keep first occurrence = highest confidence)
        seen_actions = set()
        unique_actions = []

        for match in filtered_matches:
            if match.action_name not in seen_actions:
                unique_actions.append(match.action_name)
                seen_actions.add(match.action_name)

        return unique_actions

    def extract_microactions(self, user_input: str) -> List[str]:
        """
        Main extraction method. Runs 4-stage pipeline and returns
        list of detected micro-action names.

        Args:
            user_input: Raw user query string

        Returns:
            List of canonical micro-action names (e.g., ["create_work_order", "add_to_handover"])
        """
        if not user_input or not user_input.strip():
            return []

        # Run all stages
        all_matches = []

        # Stage 1: Regex extraction
        regex_matches = self._stage1_regex_extraction(user_input)
        all_matches.extend(regex_matches)

        # Stage 2: Gazetteer lookup
        gazetteer_matches = self._stage2_gazetteer_lookup(user_input)
        all_matches.extend(gazetteer_matches)

        # Stage 3: AI extraction (only if regex + gazetteer found nothing)
        if not all_matches or max([m.confidence for m in all_matches]) < self.regex_confidence_threshold:
            ai_matches = self._stage3_ai_extraction(user_input)
            all_matches.extend(ai_matches)

        # Stage 4: Merge and deduplicate
        unique_actions = self._stage4_merge_and_deduplicate(all_matches)

        return unique_actions

    def extract_with_details(self, user_input: str) -> Dict:
        """
        Extended extraction method that returns detailed results including
        confidence scores, match positions, and source information.

        Useful for debugging and confidence thresholds.
        """
        if not user_input or not user_input.strip():
            return {
                'micro_actions': [],
                'matches': [],
                'has_unsupported': False
            }

        # Run all stages
        all_matches = []

        regex_matches = self._stage1_regex_extraction(user_input)
        all_matches.extend(regex_matches)

        gazetteer_matches = self._stage2_gazetteer_lookup(user_input)
        all_matches.extend(gazetteer_matches)

        if not all_matches or max([m.confidence for m in all_matches]) < self.regex_confidence_threshold:
            ai_matches = self._stage3_ai_extraction(user_input)
            all_matches.extend(ai_matches)

        # Check for unsupported indicators
        unsupported_patterns = self.patterns.get('unsupported_indicators', {}).get('patterns', [])
        has_unsupported = any(
            re.search(pattern, user_input, re.IGNORECASE)
            for pattern in unsupported_patterns
        )

        # Merge and deduplicate
        unique_actions = self._stage4_merge_and_deduplicate(all_matches)

        return {
            'micro_actions': unique_actions,
            'matches': [m.to_dict() for m in all_matches],
            'has_unsupported': has_unsupported,
            'total_matches': len(all_matches),
            'unique_actions': len(unique_actions)
        }


# Convenience function for n8n wrapper
def extract_for_n8n(user_input: str, patterns_path: Optional[str] = None) -> Dict:
    """
    Simple wrapper for n8n HTTP request node.

    Usage in n8n:
    - HTTP Request node → POST /extract_microactions
    - Body: {"query": "create work order and add to handover"}
    - Response: {"micro_actions": ["create_work_order", "add_to_handover"]}
    """
    extractor = MicroActionExtractor(patterns_path)
    actions = extractor.extract_microactions(user_input)

    return {
        'micro_actions': actions,
        'count': len(actions)
    }


# Singleton instance for FastAPI (load patterns once at startup)
_extractor_instance = None

def get_extractor() -> MicroActionExtractor:
    """Get or create singleton extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = MicroActionExtractor()
    return _extractor_instance


if __name__ == '__main__':
    # Test cases for development
    extractor = MicroActionExtractor()

    test_queries = [
        "create work order",
        "add to handover and create wo",
        "show all open work orders",
        "create purchase request for main engine oil",
        "export handover report",
        "log my hours of rest",
        "upload maintenance manual",
        "show crew list",
        "what's the weather tomorrow",  # Should detect nothing (unsupported)
        "create wo and add to hor"  # Abbreviations
    ]

    print("Micro-Action Extraction Test Results")
    print("=" * 60)

    for query in test_queries:
        result = extractor.extract_with_details(query)
        print(f"\nQuery: '{query}'")
        print(f"Actions: {result['micro_actions']}")
        print(f"Matches: {result['total_matches']}, Unique: {result['unique_actions']}")
        if result['has_unsupported']:
            print("⚠️  Contains unsupported action indicators")
