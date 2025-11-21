"""
Unified Extraction Pipeline
============================

Single source of truth for ALL NLP extraction logic.

Combines:
- Module A: Micro-action & intent detection
- Module B: Maritime entity extraction
- Module C: Canonicalization & weighting

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
│  (Entity Extractor) │  (equipment, faults, etc.)
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

from typing import Dict, List, Optional
from dataclasses import asdict
import time

# Import modules
from module_a_action_detector import get_detector, ActionDetection
from module_b_entity_extractor import get_extractor, EntityDetection
from module_c_canonicalizer import get_canonicalizer


class UnifiedExtractionPipeline:
    """
    Unified extraction pipeline combining all NLP logic.

    Single entry point for all extraction needs.
    """

    def __init__(self):
        # Load all modules (singletons)
        self.action_detector = get_detector()
        self.entity_extractor = get_extractor()
        self.canonicalizer = get_canonicalizer()

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

        # STAGE 2: Module B - Extract maritime entities
        raw_entities = self.entity_extractor.extract_entities(query)

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
                "modules_run": ["action_detector", "entity_extractor", "canonicalizer"],
                "action_count": len(filtered_actions),
                "entity_count": len(merged_entities)
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
                "entity_count": 0
            }
        }

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
