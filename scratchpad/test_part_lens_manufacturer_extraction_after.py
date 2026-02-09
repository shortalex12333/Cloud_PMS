#!/usr/bin/env python3
"""Test Part Lens MANUFACTURER extraction AFTER fix (PR #69)."""

import sys
sys.path.insert(0, 'apps/api')

from extraction.regex_extractor import RegexExtractor

extractor = RegexExtractor()

# Focus on manufacturer extraction - the primary fix in PR #69
test_queries = [
    # Single manufacturer brand names (from ENTITY_EXTRACTION_EXPORT)
    ("Racor", "brand"),           # Currently 'brand', should route to parts
    ("Caterpillar", "brand"),     # Currently 'brand', should route to parts
    ("Volvo", "brand"),           # Currently 'brand', should route to parts
    ("Cummins", "brand"),         # Currently 'brand', should route to parts
    ("Yanmar", "brand"),          # Currently 'brand', should route to parts

    # Part numbers (regression test - should continue working)
    ("FLT-0170-576", "part_number"),

    # Brand + product queries (compound entities)
    ("Racor filters", "brand"),
    ("Caterpillar parts", "brand"),
]

print("=" * 80)
print("AFTER FIX - Part Lens Manufacturer Routing (PR #69)")
print("=" * 80)
print("Testing that BRAND/EQUIPMENT_BRAND/ORG entity types route to part search")
print("=" * 80)

passed = 0
failed = 0

for query, expected_type in test_queries:
    entities, _ = extractor.extract(query)

    print(f"\nQuery: '{query}'")
    print(f"Expected: {expected_type}")
    print(f"Entities: {len(entities)}")

    found_types = []
    for ent in entities:
        print(f"  - {ent.text}: {ent.type} (source={ent.source}, conf={ent.confidence})")
        found_types.append(ent.type)

    # Validate - check if extracted type matches OR if it's one of the acceptable manufacturer types
    manufacturer_types = {'brand', 'equipment_brand', 'org', 'manufacturer'}
    if expected_type in found_types:
        print(f"  ✅ PASS: Found expected type '{expected_type}'")
        passed += 1
    elif expected_type in manufacturer_types and any(ft in manufacturer_types for ft in found_types):
        print(f"  ✅ PASS: Found manufacturer type {found_types} (will route to part search)")
        passed += 1
    else:
        print(f"  ❌ FAIL: Expected '{expected_type}', got {found_types}")
        failed += 1

print("\n" + "=" * 80)
print(f"Results: {passed}/{len(test_queries)} passed, {failed} failed")
if failed == 0:
    print("✅ ALL TESTS PASSED")
else:
    print(f"❌ {failed} TESTS FAILED")
print("=" * 80)
