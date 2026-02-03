#!/usr/bin/env python3
"""
Test entity extraction for manufacturer searches.

Validates that manufacturer names like "Racor", "Caterpillar", "Volvo Penta"
correctly extract as BRAND/EQUIPMENT_BRAND/ORG and route to Parts Lens.
"""

import sys
import asyncio
sys.path.insert(0, 'apps/api')

from extraction.orchestrator import ExtractionOrchestrator
from prepare.capability_composer import plan_capabilities, ENTITY_TO_SEARCH_COLUMN

# Test queries for manufacturer searches
TEST_QUERIES = [
    "Racor",
    "Caterpillar",
    "Volvo Penta",
    "Volvo",
    "MTU",
    "Yanmar",
]

async def test_manufacturer_extraction():
    """Test manufacturer entity extraction."""
    print("=" * 80)
    print("MANUFACTURER ENTITY EXTRACTION TEST")
    print("=" * 80)
    print()

    orchestrator = ExtractionOrchestrator()

    total_passed = 0
    total_failed = 0
    failed_tests = []

    for query in TEST_QUERIES:
        print(f"\n{'=' * 80}")
        print(f"Query: \"{query}\"")
        print(f"{'=' * 80}")

        # Extract entities
        result = await orchestrator.extract(query)
        entities_dict = result.get('entities', {})

        print(f"Raw extraction result:")
        print(f"  Entities: {entities_dict}")
        print(f"  Source mix: {result.get('source_mix', {})}")

        # Check if any relevant entity types were extracted
        relevant_types = ['BRAND', 'EQUIPMENT_BRAND', 'ORG', 'MANUFACTURER']
        found_types = []

        for entity_type, values in entities_dict.items():
            normalized_type = entity_type.upper().replace(' ', '_')
            if normalized_type in relevant_types:
                found_types.append(normalized_type)
                print(f"\n  ✅ Extracted {normalized_type}: {values}")

                # Check capability mapping
                mapping = ENTITY_TO_SEARCH_COLUMN.get(normalized_type)
                if mapping:
                    capability, search_col = mapping
                    print(f"     → Maps to capability: {capability} (column: {search_col})")
                    if capability == 'part_by_part_number_or_name':
                        print(f"     ✅ CORRECT: Routes to Parts Lens")
                        total_passed += 1
                    else:
                        print(f"     ❌ WRONG: Routes to {capability} instead of Parts Lens")
                        total_failed += 1
                        failed_tests.append((query, normalized_type, capability))
                else:
                    print(f"     ❌ NO MAPPING FOUND for {normalized_type}")
                    total_failed += 1
                    failed_tests.append((query, normalized_type, "NO_MAPPING"))

        if not found_types:
            print(f"\n  ❌ FAIL: No manufacturer entities extracted")
            total_failed += 1
            failed_tests.append((query, "NO_ENTITIES", "N/A"))

    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Queries: {len(TEST_QUERIES)}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print()

    if total_failed == 0:
        print("✅ ALL MANUFACTURER EXTRACTION TESTS PASSED")
        print()
        print("Manufacturer searches correctly:")
        print("  • Extract as BRAND/EQUIPMENT_BRAND/ORG entity types")
        print("  • Map to part_by_part_number_or_name capability")
        print("  • Route to Parts Lens for search")
        return 0
    else:
        print(f"❌ {total_failed} TESTS FAILED")
        print()
        print("Failed Tests:")
        for query, entity_type, issue in failed_tests:
            print(f"  • Query: \"{query}\" - {entity_type} - {issue}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_manufacturer_extraction())
    sys.exit(exit_code)
