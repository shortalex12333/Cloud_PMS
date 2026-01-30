#!/usr/bin/env python3
"""
Part Lens - Live Data Testing
==============================

Tests Part Lens capabilities against live Supabase tenant with real test data.

Usage:
    python3 test_part_lens_live.py

Tests:
1. Entity extraction from natural language
2. Capability mapping
3. Search execution with live data
4. Edge cases and variance
"""

import os
import sys
sys.path.insert(0, '.')

from supabase import create_client, Client
from typing import List, Dict, Any

# Supabase credentials
TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # MY Pandora

# Test queries covering different entity types and natural language variations
TEST_QUERIES = [
    # Exact matches
    {
        "query": "TEST-PART-001",
        "expected_entity_type": "PART_NUMBER",
        "expected_results": 1,
        "description": "Exact part number match",
    },
    {
        "query": "Engine Oil Filter",
        "expected_entity_type": "PART_NAME",
        "expected_results": 1,
        "description": "Exact part name match",
    },

    # Generic searches (free-text fallback)
    {
        "query": "oil filter",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Generic part search (lowercase)",
    },
    {
        "query": "filter",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Partial part search",
    },
    {
        "query": "hydraulic pump",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Multi-word part search",
    },

    # Location-based
    {
        "query": "Engine Room - Shelf A",
        "expected_entity_type": "LOCATION",
        "expected_results": ">0",
        "description": "Exact storage location",
    },
    {
        "query": "engine room",
        "expected_entity_type": "PART",  # May extract as PART or LOCATION
        "expected_results": ">0",
        "description": "Partial location search",
    },

    # Category searches
    {
        "query": "Filters",
        "expected_entity_type": "PART_CATEGORY",
        "expected_results": ">0",
        "description": "Category search",
    },
    {
        "query": "Hydraulics",
        "expected_entity_type": "PART_CATEGORY",
        "expected_results": ">0",
        "description": "Category search (Hydraulics)",
    },

    # Natural language variations
    {
        "query": "show me all filters",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Natural language: show me",
    },
    {
        "query": "where is the oil filter",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Natural language: where is",
    },
    {
        "query": "parts in workshop",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Natural language: parts in location",
    },

    # Edge cases
    {
        "query": "OIL FILTER",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Edge case: all caps",
    },
    {
        "query": "oil  filter",  # Double space
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Edge case: extra whitespace",
    },
    {
        "query": "seal kit",
        "expected_entity_type": "PART",
        "expected_results": ">0",
        "description": "Edge case: partial match in name",
    },
]

print("="*80)
print("PART LENS - LIVE DATA TESTING")
print("="*80)
print()
print(f"Tenant: {TENANT_1_URL}")
print(f"Yacht ID: {YACHT_ID}")
print()

# Initialize Supabase client
print("Initializing Supabase client...")
try:
    supabase: Client = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)
    print("✓ Supabase client initialized")
except Exception as e:
    print(f"✗ Failed to initialize Supabase: {e}")
    sys.exit(1)

print()

# Verify test data exists
print("Verifying test data...")
print("-" * 80)
try:
    response = supabase.table('pms_parts')\
        .select('id, name, part_number, category, location')\
        .eq('yacht_id', YACHT_ID)\
        .ilike('part_number', 'TEST-PART-%')\
        .execute()

    test_parts = response.data
    print(f"✓ Found {len(test_parts)} test parts:")
    for part in test_parts:
        print(f"  - {part['part_number']}: {part['name']} ({part['category']}) @ {part.get('location', 'N/A')}")

    if len(test_parts) < 5:
        print()
        print("⚠ WARNING: Expected 5 test parts, found", len(test_parts))
        print("  Run: supabase/migrations/20260130_108_seed_test_parts_e2e.sql")
        print()
except Exception as e:
    print(f"✗ Failed to verify test data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Import Part Lens components
print("Loading Part Lens components...")
print("-" * 80)

try:
    from apps.api.prepare.capabilities.part_capabilities import PartLensCapability
    from apps.api.prepare.capability_registry import CapabilityRegistry
    print("✓ Part Lens components loaded")
except ImportError as e:
    print(f"✗ Failed to import Part Lens: {e}")
    sys.exit(1)

# Initialize registry
try:
    registry = CapabilityRegistry(supabase)
    registry.discover_and_register()
    print(f"✓ Registry initialized: {len(registry.lenses)} lens(es), {len(registry.entity_mappings)} entity types")
except Exception as e:
    print(f"✗ Failed to initialize registry: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Mock entity extraction (simplified for testing)
def mock_entity_extraction(query: str) -> List[Dict[str, Any]]:
    """
    Simplified entity extraction for testing.
    In production, this is done by module_b_entity_extractor.py
    """
    query_lower = query.lower()
    entities = []

    # Check for part numbers (TEST-PART-XXX)
    if "test-part-" in query_lower:
        entities.append({"type": "PART_NUMBER", "value": query.upper()})

    # Check for exact part names
    part_names = ["engine oil filter", "hydraulic pump seal kit", "spare fuel filter",
                  "navigation light bulb", "stainless steel fasteners"]
    for name in part_names:
        if name in query_lower:
            entities.append({"type": "PART_NAME", "value": name.title()})

    # Check for categories
    categories = ["filters", "hydraulics", "electrical", "hardware"]
    for cat in categories:
        if cat in query_lower:
            entities.append({"type": "PART_CATEGORY", "value": cat.capitalize()})

    # Check for locations
    if "engine room" in query_lower or "workshop" in query_lower or "bridge" in query_lower:
        location_match = None
        if "engine room" in query_lower:
            location_match = "Engine Room"
        elif "workshop" in query_lower:
            location_match = "Workshop"
        elif "bridge" in query_lower:
            location_match = "Bridge"
        if location_match:
            entities.append({"type": "LOCATION", "value": location_match})

    # Generic part search (fallback)
    if not entities:
        # Extract potential part keywords
        keywords = ["filter", "pump", "seal", "bulb", "fastener", "oil", "fuel",
                    "hydraulic", "navigation", "light", "stainless", "steel"]
        for keyword in keywords:
            if keyword in query_lower:
                entities.append({"type": "PART", "value": query})
                break

    return entities


# Test each query
print("Running test queries...")
print("=" * 80)
print()

passed = 0
failed = 0
results_summary = []

for i, test in enumerate(TEST_QUERIES, 1):
    query = test["query"]
    expected_entity = test["expected_entity_type"]
    expected_count = test["expected_results"]
    description = test["description"]

    print(f"Test {i}/{len(TEST_QUERIES)}: {description}")
    print(f"Query: \"{query}\"")
    print("-" * 80)

    # Step 1: Entity extraction
    entities = mock_entity_extraction(query)
    print(f"Entities extracted: {entities}")

    if not entities:
        print("✗ FAIL: No entities extracted")
        failed += 1
        results_summary.append({
            "test": description,
            "status": "FAIL",
            "reason": "No entities extracted"
        })
        print()
        continue

    # Step 2: Check entity mapping
    entity_type = entities[0]["type"]
    entity_value = entities[0]["value"]

    if entity_type not in registry.entity_mappings:
        print(f"✗ FAIL: Entity type '{entity_type}' not mapped in registry")
        failed += 1
        results_summary.append({
            "test": description,
            "status": "FAIL",
            "reason": f"Entity type '{entity_type}' not mapped"
        })
        print()
        continue

    mapping = registry.entity_mappings[entity_type]
    print(f"Mapped to: {mapping.capability_name} (column: {mapping.search_column})")

    # Step 3: Execute search
    try:
        # Get lens instance
        lens = registry.lenses["part_lens"]
        capability_method = getattr(lens, mapping.capability_name)

        # Execute capability
        results = capability_method(
            yacht_id=YACHT_ID,
            search_term=entity_value,
            column_name=mapping.search_column,
            limit=20
        )

        result_count = len(results)
        print(f"Results: {result_count} item(s)")

        # Show first 3 results
        for j, result in enumerate(results[:3], 1):
            title = result.get('title', result.get('name', 'N/A'))
            result_type = result.get('type', 'unknown')
            print(f"  {j}. [{result_type}] {title}")

        # Validate result count
        if expected_count == ">0":
            if result_count > 0:
                print(f"✓ PASS: Found {result_count} result(s)")
                passed += 1
                results_summary.append({
                    "test": description,
                    "status": "PASS",
                    "results": result_count
                })
            else:
                print(f"✗ FAIL: Expected >0 results, got {result_count}")
                failed += 1
                results_summary.append({
                    "test": description,
                    "status": "FAIL",
                    "reason": f"Expected >0 results, got {result_count}"
                })
        else:
            if result_count == expected_count:
                print(f"✓ PASS: Found exactly {result_count} result(s)")
                passed += 1
                results_summary.append({
                    "test": description,
                    "status": "PASS",
                    "results": result_count
                })
            else:
                print(f"✗ FAIL: Expected {expected_count} results, got {result_count}")
                failed += 1
                results_summary.append({
                    "test": description,
                    "status": "FAIL",
                    "reason": f"Expected {expected_count} results, got {result_count}"
                })

    except Exception as e:
        print(f"✗ FAIL: Search execution error: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
        results_summary.append({
            "test": description,
            "status": "FAIL",
            "reason": f"Search error: {str(e)}"
        })

    print()

# Summary
print("="*80)
print("TEST SUMMARY")
print("="*80)
print(f"Total: {len(TEST_QUERIES)} tests")
print(f"Passed: {passed} ✓")
print(f"Failed: {failed} ✗")
print(f"Success Rate: {(passed/len(TEST_QUERIES)*100):.1f}%")
print()

if failed > 0:
    print("Failed Tests:")
    print("-" * 80)
    for result in results_summary:
        if result["status"] == "FAIL":
            print(f"✗ {result['test']}")
            print(f"  Reason: {result['reason']}")
    print()

print("="*80)

# Exit code
sys.exit(0 if failed == 0 else 1)
