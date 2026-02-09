#!/usr/bin/env python3
"""Test Part Lens entity extraction BEFORE fix."""

import sys
sys.path.insert(0, 'apps/api')

from extraction.regex_extractor import RegexExtractor

extractor = RegexExtractor()

test_queries = [
    "Racor",
    "oil filter",
    "Air Filter Element",
    "Caterpillar filters",
    "fuel pump",
    "glow plug",
    "zinc anode",
]

print("=" * 80)
print("BEFORE FIX - Part Lens Entity Extraction")
print("=" * 80)

issues_found = 0

for query in test_queries:
    entities, _ = extractor.extract(query)

    print(f"\nQuery: '{query}'")
    print(f"Entities: {len(entities)}")

    for ent in entities:
        print(f"  - {ent.text}: {ent.type} (source={ent.source}, conf={ent.confidence})")

    # Check for issues
    has_org = any(e.type == 'org' for e in entities)
    has_equipment = any(e.type == 'equipment' for e in entities)
    has_manufacturer = any(e.type == 'manufacturer' for e in entities)
    has_part = any(e.type in ['part_number', 'part_name'] for e in entities)

    if has_org and not has_manufacturer:
        print(f"  ❌ ISSUE: Extracted as 'org' instead of 'manufacturer'")
        issues_found += 1

    if has_equipment and not has_part:
        print(f"  ⚠️  WARNING: Extracted as 'equipment', may route to wrong lens")
        issues_found += 1

    if len(entities) == 0:
        print(f"  ⚠️  WARNING: No entities extracted")

print("\n" + "=" * 80)
print(f"Issues found: {issues_found}")
print("=" * 80)
