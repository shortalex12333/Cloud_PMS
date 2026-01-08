"""
Module C: Canonicalization & Weighting
=======================================

Normalizes entities and assigns importance weights.

Functions:
- Normalize abbreviations (ME1 → MAIN_ENGINE_1)
- Assign entity weights based on importance
- Merge duplicate entities
- Provide canonical mappings

STRICT RULES:
- Preserves all entity detections from Module B
- Only normalizes, does not add/remove
- Weights reflect business importance
"""

from typing import List, Dict
from module_b_entity_extractor import EntityDetection
from dataclasses import replace


class Canonicalizer:
    """
    Canonicalizes and weights entities for unified output.
    """

    def __init__(self):
        # Abbreviation mappings
        self.abbreviation_map = {
            # Equipment abbreviations
            "ME": "MAIN_ENGINE",
            "ME1": "MAIN_ENGINE_1",
            "ME2": "MAIN_ENGINE_2",
            "AE": "AUXILIARY_ENGINE",
            "AE1": "AUXILIARY_ENGINE_1",
            "AE2": "AUXILIARY_ENGINE_2",
            "GEN": "GENERATOR",
            "GEN1": "GENERATOR_1",
            "GEN2": "GENERATOR_2",
            "SWP": "SEA_WATER_PUMP",
            "FWP": "FRESH_WATER_PUMP",
            "HX": "HEAT_EXCHANGER",

            # Voltage normalization
            "24V": "24_VDC",
            "110V": "110_VAC",
            "220V": "220_VAC",
            "440V": "440_VAC",

            # Common abbreviations
            "TEMP": "TEMPERATURE",
            "PRES": "PRESSURE",
            "RPM": "REVOLUTIONS_PER_MINUTE",
        }

        # Entity type weights (business importance)
        self.entity_weights = {
            "fault_code": 1.0,      # Highest priority
            "equipment": 0.95,      # Critical
            "system": 0.90,         # Important
            "measurement": 0.85,    # Context
            "part": 0.80,           # Specific
            "maritime_term": 0.75,  # Descriptive
        }

        # Entity category weights (for search ranking)
        self.category_weights = {
            "main_engine": 1.0,
            "auxiliary_engine": 0.95,
            "generator": 0.95,
            "pump": 0.90,
            "filter": 0.80,
            "sensor": 0.75,
            "leak": 0.90,
            "failure": 0.95,
            "alarm": 0.93,
        }

    def canonicalize(self, entities: List[EntityDetection]) -> List[EntityDetection]:
        """
        Canonicalize entity values and update confidence weights.

        Returns new list of EntityDetection with canonical forms.
        """
        if not entities:
            return []

        canonical_entities = []

        for entity in entities:
            # Apply abbreviation mapping if exists
            canonical = entity.canonical
            if canonical in self.abbreviation_map:
                canonical = self.abbreviation_map[canonical]

            # Adjust confidence based on entity type weight
            type_weight = self.entity_weights.get(entity.type, 0.70)
            adjusted_confidence = entity.confidence * type_weight

            # Create new entity with canonical form
            canonical_entity = replace(
                entity,
                canonical=canonical,
                confidence=adjusted_confidence
            )

            canonical_entities.append(canonical_entity)

        return canonical_entities

    def get_entity_weight(self, entity: EntityDetection) -> float:
        """
        Get importance weight for entity (for search ranking).

        Returns weight between 0.0 and 1.0.
        """
        # Base weight from entity type
        base_weight = self.entity_weights.get(entity.type, 0.70)

        # Boost weight for critical terms
        canonical_lower = entity.canonical.lower()
        for keyword, boost in self.category_weights.items():
            if keyword in canonical_lower:
                return min(base_weight * boost, 1.0)

        return base_weight

    def merge_duplicates(self, entities: List[EntityDetection]) -> List[EntityDetection]:
        """
        Merge entities with same canonical form, keeping highest confidence.
        """
        if not entities:
            return []

        # Group by canonical form
        entity_map: Dict[str, EntityDetection] = {}

        for entity in entities:
            key = f"{entity.type}:{entity.canonical}"

            if key not in entity_map:
                entity_map[key] = entity
            else:
                # Keep entity with higher confidence
                if entity.confidence > entity_map[key].confidence:
                    entity_map[key] = entity

        return list(entity_map.values())

    def get_summary_weights(self, entities: List[EntityDetection]) -> Dict[str, float]:
        """
        Get summary of entity type weights for the query.

        Returns dict with average confidence per entity type.
        """
        if not entities:
            return {}

        type_confidences: Dict[str, List[float]] = {}

        for entity in entities:
            if entity.type not in type_confidences:
                type_confidences[entity.type] = []
            type_confidences[entity.type].append(entity.confidence)

        # Calculate averages
        summary = {}
        for entity_type, confidences in type_confidences.items():
            summary[entity_type] = sum(confidences) / len(confidences)

        return summary


# Singleton instance
_canonicalizer_instance = None

def get_canonicalizer() -> Canonicalizer:
    """Get or create singleton canonicalizer instance"""
    global _canonicalizer_instance
    if _canonicalizer_instance is None:
        _canonicalizer_instance = Canonicalizer()
    return _canonicalizer_instance


if __name__ == "__main__":
    # Quick tests
    from module_b_entity_extractor import get_extractor as get_entity_extractor

    extractor = get_entity_extractor()
    canonicalizer = Canonicalizer()

    test_queries = [
        "ME1 coolant leak",
        "24V generator failure",
        "SWP E047",
    ]

    print("Module C: Canonicalizer - Quick Tests")
    print("=" * 60)

    for query in test_queries:
        # Extract entities
        entities = extractor.extract_entities(query)

        # Canonicalize
        canonical_entities = canonicalizer.canonicalize(entities)

        # Merge duplicates
        merged = canonicalizer.merge_duplicates(canonical_entities)

        # Get weights
        weights = canonicalizer.get_summary_weights(merged)

        print(f"\nQuery: '{query}'")
        print(f"Original entities: {len(entities)}")
        print(f"Canonical entities:")
        for entity in merged:
            weight = canonicalizer.get_entity_weight(entity)
            print(f"  - {entity.type}: {entity.value} → {entity.canonical}")
            print(f"    Confidence: {entity.confidence:.2f}, Weight: {weight:.2f}")

        print(f"Summary weights: {weights}")
