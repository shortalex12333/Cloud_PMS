"""
Unified Extraction Pipeline
============================

Single source of truth for ALL NLP extraction logic.

Combines:
- Module A: Micro-action & intent detection
- Module B: Maritime entity extraction (regex)
- Module C: Canonicalization & weighting
- GPT Fallback: When regex coverage < 85%, use GPT-4o-mini

Returns unified structured output for:
- Search Engine
- Action Router
- n8n workflows
- Predictive Engine

ARCHITECTURE:
┌─────────────────────┐
│   User Query        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module A           │  Detect actions & intent
│  (Action Detector)  │  (STRICT verb-based)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module B           │  Extract maritime entities
│  (Entity Extractor) │  (regex patterns)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Coverage Check     │  If < 85% tokens covered
│  (Fallback Gate)    │  → trigger GPT extraction
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │  < 85%?   │
     └─────┬─────┘
           │ YES
           ▼
┌─────────────────────┐
│  GPT-4o-mini        │  AI fallback extraction
│  (gpt_extractor)    │  + text-embedding-3-small
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Module C           │  Canonicalize & weight
│  (Canonicalizer)    │  (normalize, merge)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Unified Output     │  Single structured JSON
└─────────────────────┘
"""

from typing import Dict, List, Optional, Set
from dataclasses import asdict
import time
import re
import logging

# Import modules
from module_a_action_detector import get_detector, ActionDetection
from module_b_entity_extractor import get_extractor, EntityDetection
from module_c_canonicalizer import get_canonicalizer

# Import GPT fallback
try:
    from gpt_extractor import get_gpt_extractor, GPTExtractor
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False
    logging.warning("GPT extractor not available - running regex-only mode")

# Coverage threshold for GPT fallback
COVERAGE_THRESHOLD = 0.85  # If less than 85% of tokens covered, use GPT


class UnifiedExtractionPipeline:
    """
    Unified extraction pipeline combining all NLP logic.

    Single entry point for all extraction needs.
    Now includes GPT fallback when regex coverage < 85%.
    """

    # Stop words that don't count toward coverage
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "and", "or", "but", "if", "because", "until", "while", "me", "my",
        "our", "you", "your", "it", "its", "this", "that", "these", "those",
        "what", "which", "who", "show", "find", "get", "list", "search",
        "display", "give", "tell", "see", "look", "check", "view", "all",
    }

    def __init__(self):
        # Load all modules (singletons)
        self.action_detector = get_detector()
        self.entity_extractor = get_extractor()
        self.canonicalizer = get_canonicalizer()

        # Load GPT fallback (if available)
        self.gpt_extractor = None
        if GPT_AVAILABLE:
            try:
                self.gpt_extractor = get_gpt_extractor()
            except Exception as e:
                logging.warning(f"Failed to initialize GPT extractor: {e}")

    def extract(self, query: str, min_action_confidence: float = 0.4) -> Dict:
        """
        Run complete extraction pipeline on query.

        Returns unified structured output:
        {
            "intent": "...",
            "microactions": [{"action": "...", "confidence": 0.92}],
            "entities": [...],
            "canonical_entities": [...],
            "scores": {
                "intent_confidence": 0.85,
                "entity_confidence": 0.91
            },
            "metadata": {
                "latency_ms": 45,
                "modules_run": ["action", "entity", "canonical"]
            }
        }

        Args:
            query: User query string
            min_action_confidence: Minimum confidence for action detection

        Returns:
            Unified extraction results dict
        """
        start_time = time.time()

        if not query or not query.strip():
            return self._empty_response(0)

        # STAGE 1: Module A - Detect micro-actions and intent
        action_detections = self.action_detector.detect_actions(query)

        # Filter by confidence threshold
        filtered_actions = [
            action for action in action_detections
            if action.confidence >= min_action_confidence
        ]

        # Get best action for intent
        best_action = None
        if filtered_actions:
            filtered_actions.sort(key=lambda x: x.confidence, reverse=True)
            best_action = filtered_actions[0]

        intent = self.action_detector.detect_intent(query)
        intent_confidence = best_action.confidence if best_action else 0.0

        # STAGE 2: Module B - Extract maritime entities (regex)
        raw_entities = self.entity_extractor.extract_entities(query)

        # STAGE 2.5: Coverage check - decide if GPT fallback needed
        coverage = self._calculate_coverage(query, raw_entities)
        used_gpt_fallback = False

        if coverage < COVERAGE_THRESHOLD and self.gpt_extractor:
            # GPT FALLBACK: Coverage too low, use AI extraction
            try:
                gpt_result = self.gpt_extractor.extract(query)
                if gpt_result and gpt_result.entities:
                    # Convert GPT entities to EntityDetection format and merge
                    gpt_entities = self._convert_gpt_entities(gpt_result.entities)
                    raw_entities = self._merge_entities(raw_entities, gpt_entities)
                    used_gpt_fallback = True
            except Exception as e:
                logging.warning(f"GPT fallback failed: {e}")

        # STAGE 3: Module C - Canonicalize and weight entities
        canonical_entities = self.canonicalizer.canonicalize(raw_entities)
        merged_entities = self.canonicalizer.merge_duplicates(canonical_entities)

        # Calculate entity confidence (average)
        entity_confidence = 0.0
        if merged_entities:
            entity_confidence = sum(e.confidence for e in merged_entities) / len(merged_entities)

        # Get summary weights
        entity_weights = self.canonicalizer.get_summary_weights(merged_entities)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Build unified output
        return {
            "intent": intent,
            "microactions": [
                {
                    "action": action.action,
                    "confidence": action.confidence,
                    "verb": action.verb,
                    "matched_text": action.matched_text
                }
                for action in filtered_actions
            ],
            "entities": [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence
                }
                for entity in raw_entities
            ],
            "canonical_entities": [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "canonical": entity.canonical,
                    "confidence": entity.confidence,
                    "weight": self.canonicalizer.get_entity_weight(entity)
                }
                for entity in merged_entities
            ],
            "scores": {
                "intent_confidence": intent_confidence,
                "entity_confidence": entity_confidence,
                "entity_weights": entity_weights
            },
            "metadata": {
                "query": query,
                "latency_ms": latency_ms,
                "modules_run": ["action_detector", "entity_extractor", "canonicalizer"] +
                               (["gpt_fallback"] if used_gpt_fallback else []),
                "action_count": len(filtered_actions),
                "entity_count": len(merged_entities),
                "coverage": round(coverage, 3),
                "used_gpt_fallback": used_gpt_fallback
            }
        }

    def _empty_response(self, latency_ms: int) -> Dict:
        """Return empty response for invalid queries"""
        return {
            "intent": None,
            "microactions": [],
            "entities": [],
            "canonical_entities": [],
            "scores": {
                "intent_confidence": 0.0,
                "entity_confidence": 0.0,
                "entity_weights": {}
            },
            "metadata": {
                "query": "",
                "latency_ms": latency_ms,
                "modules_run": [],
                "action_count": 0,
                "entity_count": 0,
                "coverage": 0.0,
                "used_gpt_fallback": False
            }
        }

    def _calculate_coverage(self, query: str, entities: List[EntityDetection]) -> float:
        """
        Calculate what percentage of meaningful tokens are covered by entities.

        Returns: float between 0.0 and 1.0
        """
        # Tokenize query
        tokens = re.findall(r'[a-z0-9][-a-z0-9]*[a-z0-9]|[a-z0-9]', query.lower())

        # Filter out stop words
        meaningful_tokens = [t for t in tokens if t not in self.STOP_WORDS]

        if not meaningful_tokens:
            return 1.0  # Empty query is "fully covered"

        # Build set of entity values (lowercase, tokenized)
        entity_tokens: Set[str] = set()
        for e in entities:
            val = (e.value or "").lower()
            # Add whole value and individual words
            entity_tokens.add(val)
            for word in re.findall(r'[a-z0-9]+', val):
                entity_tokens.add(word)

        # Count covered tokens
        covered = sum(1 for t in meaningful_tokens if t in entity_tokens)

        return covered / len(meaningful_tokens)

    def _convert_gpt_entities(self, gpt_entities: List) -> List[EntityDetection]:
        """
        Convert GPT extraction entities to EntityDetection format.

        GPT ExtractedEntity has: type, value, confidence, evidence, start_char, end_char
        EntityDetection needs: type, value, canonical, confidence, span, metadata, weight
        """
        converted = []
        for e in gpt_entities:
            # Extract fields from GPT entity
            entity_type = getattr(e, 'type', None) or getattr(e, 'entity_type', 'unknown')
            value = getattr(e, 'value', None) or getattr(e, 'text', '')
            confidence = getattr(e, 'confidence', 0.85)
            start_char = getattr(e, 'start_char', None)
            end_char = getattr(e, 'end_char', None)

            if value:
                # Build span tuple (required by EntityDetection)
                span = (start_char, end_char) if start_char is not None and end_char is not None else (0, len(value))

                converted.append(EntityDetection(
                    type=entity_type,
                    value=value,
                    canonical=value,  # Module C will normalize
                    confidence=confidence,
                    span=span,
                    metadata={"source": "gpt"},
                ))
        return converted

    def _merge_entities(
        self,
        regex_entities: List[EntityDetection],
        gpt_entities: List[EntityDetection]
    ) -> List[EntityDetection]:
        """
        Merge regex and GPT entities, preferring regex when overlapping.
        """
        # Start with regex entities (higher trust)
        merged = list(regex_entities)

        # Get existing values (lowercase)
        existing_values = {e.value.lower() for e in regex_entities if e.value}

        # Add GPT entities that don't overlap
        for gpt_e in gpt_entities:
            if gpt_e.value and gpt_e.value.lower() not in existing_values:
                merged.append(gpt_e)
                existing_values.add(gpt_e.value.lower())

        return merged

    def extract_actions_only(self, query: str) -> List[Dict]:
        """
        Extract only micro-actions (for fast routing).

        Returns list of actions with confidence.
        """
        detections = self.action_detector.detect_actions(query)
        return [
            {
                "action": d.action,
                "confidence": d.confidence,
                "verb": d.verb
            }
            for d in detections
            if d.confidence >= 0.4
        ]

    def extract_entities_only(self, query: str) -> List[Dict]:
        """
        Extract only maritime entities (for search).

        Returns list of canonical entities.
        """
        raw_entities = self.entity_extractor.extract_entities(query)
        canonical_entities = self.canonicalizer.canonicalize(raw_entities)
        merged = self.canonicalizer.merge_duplicates(canonical_entities)

        return [
            {
                "type": entity.type,
                "canonical": entity.canonical,
                "confidence": entity.confidence
            }
            for entity in merged
        ]


# Singleton instance
_pipeline_instance = None

def get_pipeline() -> UnifiedExtractionPipeline:
    """Get or create singleton pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = UnifiedExtractionPipeline()
    return _pipeline_instance


if __name__ == "__main__":
    # Comprehensive tests matching requirements
    pipeline = UnifiedExtractionPipeline()

    test_cases = [
        # Test 1: Action only
        "create work order for bilge pump",

        # Test 2: Maritime only
        "bilge manifold",

        # Test 3: Mixed
        "diagnose E047 on ME1",

        # Test 4: Noise
        "tell me bilge pump",

        # Test 5: Edge
        "find coolant temp",

        # Additional tests
        "sea water pump pressure low",
        "24V generator failure",
        "open work order for main engine coolant leak",
    ]

    print("=" * 70)
    print("UNIFIED EXTRACTION PIPELINE - COMPREHENSIVE TESTS")
    print("=" * 70)

    for query in test_cases:
        result = pipeline.extract(query)

        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print(f"{'='*70}")

        print(f"\n📋 INTENT: {result['intent']}")

        print(f"\n⚡ MICRO-ACTIONS ({len(result['microactions'])}):")
        if result['microactions']:
            for action in result['microactions']:
                print(f"  - {action['action']}")
                print(f"    Confidence: {action['confidence']:.2f}, Verb: {action['verb']}")
        else:
            print("  None detected")

        print(f"\n🔧 ENTITIES ({len(result['canonical_entities'])}):")
        if result['canonical_entities']:
            for entity in result['canonical_entities']:
                print(f"  - {entity['type']}: {entity['value']} → {entity['canonical']}")
                print(f"    Confidence: {entity['confidence']:.2f}, Weight: {entity['weight']:.2f}")
        else:
            print("  None detected")

        print(f"\n📊 SCORES:")
        print(f"  Intent confidence: {result['scores']['intent_confidence']:.2f}")
        print(f"  Entity confidence: {result['scores']['entity_confidence']:.2f}")

        print(f"\n⏱️  METADATA:")
        print(f"  Latency: {result['metadata']['latency_ms']}ms")
        print(f"  Actions: {result['metadata']['action_count']}, Entities: {result['metadata']['entity_count']}")

    print(f"\n{'='*70}")
    print("✅ All tests complete")
    print(f"{'='*70}")
