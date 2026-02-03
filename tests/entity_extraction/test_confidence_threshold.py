#!/usr/bin/env python3
"""
Test confidence threshold calculation for brand entities.
"""

import sys
sys.path.insert(0, 'apps/api')

from extraction.extraction_config import config as extraction_config

# Test brand entity filtering
print("=" * 80)
print("CONFIDENCE THRESHOLD ANALYSIS")
print("=" * 80)
print()

# Entity types to test
entity_types = ['brand', 'BRAND', 'EQUIPMENT_BRAND', 'ORG', 'MANUFACTURER', 'equipment']

for entity_type in entity_types:
    threshold = extraction_config.get_threshold(entity_type, 'gazetteer')
    print(f"Entity type: {entity_type:20s} → Threshold: {threshold:.2f}")

print()
print("=" * 80)
print("FILTERING SIMULATION")
print("=" * 80)
print()

# Simulate filtering for actual extracted entities
test_entities = [
    {'type': 'brand', 'text': 'Racor', 'confidence': 0.4, 'source': 'gazetteer'},
    {'type': 'brand', 'text': 'Caterpillar', 'confidence': 0.5, 'source': 'gazetteer'},
    {'type': 'brand', 'text': 'Volvo Penta', 'confidence': 0.5, 'source': 'gazetteer'},
]

for entity in test_entities:
    entity_type = entity['type']
    confidence = entity['confidence']
    source = entity['source']
    text = entity['text']

    # Get source multiplier
    multiplier = extraction_config.get_source_multiplier(source)

    # Calculate adjusted confidence
    adjusted_conf = confidence * multiplier

    # Get threshold
    threshold = extraction_config.get_threshold(entity_type, source)

    # Determine if filtered
    is_kept = adjusted_conf >= threshold
    status = "✅ KEPT" if is_kept else "❌ FILTERED"

    print(f"{status} | {text:15s} | type={entity_type:10s} | "
          f"conf={confidence:.2f} | multiplier={multiplier:.2f} | "
          f"adjusted={adjusted_conf:.2f} | threshold={threshold:.2f}")
