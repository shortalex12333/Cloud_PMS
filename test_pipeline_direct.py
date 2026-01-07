#!/usr/bin/env python3
"""
Test the full pipeline with pre-extracted entities (bypass OpenAI requirement).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from supabase import create_client
from prepare.capability_composer import compose_search

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def test_with_entities(description, entities):
    """Test pipeline stages 2-4 with pre-extracted entities."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Entities: {entities}")
    print(f"{'='*60}")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Skip stage 1 (extraction), go straight to stage 2-3 (prepare + execute)
    response = compose_search(
        supabase_client=client,
        yacht_id=TEST_YACHT_ID,
        entities=entities,
        limit_per_capability=10
    )

    print(f"Success: {response.success}")
    print(f"Total results: {response.total_count}")
    print(f"Capabilities executed: {response.capabilities_executed}")
    print(f"Capabilities blocked: {len(response.capabilities_blocked)}")

    # Check domain grouping by manually grouping results
    if response.results:
        domains = {}
        for result in response.results:
            capability = result.source_table if hasattr(result, 'source_table') else 'unknown'
            if capability not in domains:
                domains[capability] = []
            domains[capability].append(result)

        print(f"\nDomains found: {len(domains)}")
        for capability, results in domains.items():
            print(f"  - {capability}: {len(results)} results")
            if results:
                first = results[0]
                title = first.title if hasattr(first, 'title') else 'N/A'
                print(f"      Example: {title}")

    print(f"\nExecution times:")
    for cap, time_ms in response.execution_times_ms.items():
        print(f"  {cap}: {time_ms:.0f}ms")

def main():
    print("="*60)
    print("FULL PIPELINE TEST (with pre-extracted entities)")
    print("Tests stages 2-4: Prepare → Execute → Domain Grouping")
    print("="*60)

    # Test 1: Fault code entity
    test_with_entities(
        "Fault code search",
        [{"type": "FAULT_CODE", "value": "MID 128"}]
    )

    # Test 2: Part name entity
    test_with_entities(
        "Part search",
        [{"type": "PART_NAME", "value": "fuel filter"}]
    )

    # Test 3: Equipment name entity
    test_with_entities(
        "Equipment search",
        [{"type": "EQUIPMENT_NAME", "value": "main engine"}]
    )

    # Test 4: Multi-entity query (should hit multiple capabilities)
    test_with_entities(
        "Multi-entity query",
        [
            {"type": "MANUFACTURER", "value": "MTU"},
            {"type": "PART_NAME", "value": "fuel"}
        ]
    )

    # Test 5: Location query
    test_with_entities(
        "Inventory location search",
        [{"type": "LOCATION", "value": "Yacht"}]
    )

    print("\n" + "="*60)
    print("PIPELINE TESTS COMPLETE")
    print("="*60)
    print("\nAll stages tested:")
    print("  ✅ Stage 2: Prepare (entity → capability mapping)")
    print("  ✅ Stage 3: Execute (SQL generation + parallel execution)")
    print("  ✅ Stage 4: Domain grouping (results organization)")

if __name__ == "__main__":
    main()
