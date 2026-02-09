#!/usr/bin/env python3
"""
Debug script to test stock status extraction locally
"""
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

from extraction.regex_extractor import RegexExtractor
from entity_extraction_loader import load_equipment_gazetteer

# Initialize extractor
extractor = RegexExtractor()

# Test queries
test_queries = [
    "low stock parts",
    "out of stock filters",
    "critically low inventory",
    "need to reorder",
    "below minimum",
]

print("=" * 80)
print("STOCK STATUS EXTRACTION TEST")
print("=" * 80)

# Check if stock_status is in entity_extraction_gazetteer
gazetteer = load_equipment_gazetteer()
if 'stock_status' in gazetteer:
    print(f"\n✅ stock_status found in entity_extraction_gazetteer")
    print(f"   Terms count: {len(gazetteer['stock_status'])}")
    print(f"   Sample terms: {list(gazetteer['stock_status'])[:10]}")

    # Check if specific terms exist
    test_terms = ['critically low', 'critically low inventory', 'critical', 'low stock']
    for term in test_terms:
        exists = term in gazetteer['stock_status']
        print(f"   '{term}': {'✅' if exists else '❌'}")
else:
    print(f"\n❌ stock_status NOT found in entity_extraction_gazetteer")

# Check urgency_level gazetteer
if 'urgency_level' in gazetteer:
    print(f"\n📝 urgency_level found in entity_extraction_gazetteer")
    print(f"   Terms count: {len(gazetteer['urgency_level'])}")
    if 'critical' in gazetteer['urgency_level']:
        print(f"   'critical': ✅ (THIS IS THE CONFLICT)")
    else:
        print(f"   'critical': ❌")

print("\n" + "=" * 80)
print("EXTRACTION TESTS")
print("=" * 80)

for query in test_queries:
    print(f"\nQuery: \"{query}\"")
    entities, spans = extractor.extract(query)

    if entities:
        print(f"  Extracted {len(entities)} entities:")
        for entity in entities:
            print(f"    - {entity.type}: {entity.text} (source: {entity.source})")

        # Check for stock_status
        stock_status_entities = [e for e in entities if e.type == 'stock_status']
        if stock_status_entities:
            print(f"  ✅ STOCK_STATUS found: {stock_status_entities[0].text}")
        else:
            print(f"  ❌ STOCK_STATUS missing")
            print(f"     Found types: {[e.type for e in entities]}")
    else:
        print(f"  ❌ No entities extracted")

print("\n" + "=" * 80)
