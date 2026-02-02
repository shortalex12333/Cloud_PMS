#!/usr/bin/env python3
"""
Debug entity extraction for manufacturer searches.
Tests each stage of the pipeline.
"""

import sys
sys.path.insert(0, 'apps/api')

from extraction.text_cleaner import TextCleaner
from extraction.regex_extractor import RegexExtractor

# Test queries
TEST_QUERIES = ["Racor", "Caterpillar", "Volvo Penta"]

def test_extraction_stages():
    """Test each stage of extraction."""
    print("=" * 80)
    print("EXTRACTION PIPELINE DEBUG TEST")
    print("=" * 80)

    cleaner = TextCleaner()
    regex_extractor = RegexExtractor()

    for query in TEST_QUERIES:
        print(f"\n{'=' * 80}")
        print(f"Query: \"{query}\"")
        print(f"{'=' * 80}")

        # Stage 1: Clean
        cleaned = cleaner.clean(query)
        print(f"\n1. CLEANED TEXT:")
        print(f"   Original: {query}")
        print(f"   Normalized: {cleaned['normalized']}")
        print(f"   Tokens: {cleaned.get('tokens', [])}")

        # Stage 2: Regex extraction
        print(f"\n2. REGEX EXTRACTION:")
        regex_entities, covered_spans = regex_extractor.extract(cleaned['normalized'])
        print(f"   Entities found: {len(regex_entities)}")

        if regex_entities:
            for entity in regex_entities:
                print(f"   - {entity.type}: {entity.text} (source: {entity.source}, confidence: {entity.confidence})")
        else:
            print(f"   ❌ NO ENTITIES EXTRACTED")

            # Debug: Check gazetteer directly
            print(f"\n3. GAZETTEER DEBUG:")
            query_lower = query.lower()

            # Check each entity type in gazetteer
            entity_types_to_check = [
                'BRAND', 'EQUIPMENT_BRAND', 'ORG', 'MANUFACTURER',
                'CORE_BRANDS', 'EQUIPMENT_NAME', 'VESSEL_EQUIPMENT'
            ]

            for entity_type in entity_types_to_check:
                if entity_type in regex_extractor.gazetteer:
                    terms = regex_extractor.gazetteer[entity_type]
                    if query_lower in terms:
                        print(f"   ✅ Found \"{query}\" in gazetteer['{entity_type}']")
                    else:
                        # Check if any partial match exists
                        matches = [t for t in terms if query_lower in t or t in query_lower]
                        if matches:
                            print(f"   ⚠️  Partial matches in {entity_type}: {matches[:5]}")
                        else:
                            print(f"   ❌ NOT in gazetteer['{entity_type}']")
                else:
                    print(f"   ❌ gazetteer['{entity_type}'] does not exist")

        print(f"\n   Covered spans: {covered_spans}")

if __name__ == "__main__":
    test_extraction_stages()
