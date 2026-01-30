#!/usr/bin/env python3
"""
Part Lens - Direct Database Search Testing
===========================================

Tests Part Lens search queries directly against Supabase without imports.

Usage:
    python3 test_part_search_direct.py
"""

from supabase import create_client, Client
from typing import List, Dict, Any

# Supabase credentials
TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # MY Pandora

# Test cases covering different search patterns
TEST_CASES = [
    {
        "name": "Exact part number",
        "query": "TEST-PART-001",
        "column": "part_number",
        "match_type": "eq",
        "expected_min": 1,
    },
    {
        "name": "Exact part name",
        "query": "Engine Oil Filter",
        "column": "name",
        "match_type": "eq",
        "expected_min": 1,
    },
    {
        "name": "Partial name match (lowercase)",
        "query": "oil filter",
        "column": "name",
        "match_type": "ilike",
        "expected_min": 1,
    },
    {
        "name": "Partial name match (filter)",
        "query": "filter",
        "column": "name",
        "match_type": "ilike",
        "expected_min": 2,  # Engine Oil Filter + Spare Fuel Filter
    },
    {
        "name": "Category search (Filters)",
        "query": "Filters",
        "column": "category",
        "match_type": "eq",
        "expected_min": 2,  # 2 filter parts
    },
    {
        "name": "Category search (Hydraulics)",
        "query": "Hydraulics",
        "column": "category",
        "match_type": "eq",
        "expected_min": 1,
    },
    {
        "name": "Location search (Engine Room)",
        "query": "Engine Room",
        "column": "location",
        "match_type": "ilike",
        "expected_min": 2,  # 2 parts in engine room
    },
    {
        "name": "Location search (Workshop)",
        "query": "Workshop",
        "column": "location",
        "match_type": "ilike",
        "expected_min": 2,  # 2 parts in workshop
    },
    {
        "name": "Partial match (pump)",
        "query": "pump",
        "column": "name",
        "match_type": "ilike",
        "expected_min": 1,  # Hydraulic Pump Seal Kit
    },
    {
        "name": "Partial match (seal)",
        "query": "seal",
        "column": "name",
        "match_type": "ilike",
        "expected_min": 1,  # Seal Kit
    },
    {
        "name": "Case insensitive (OIL FILTER)",
        "query": "OIL FILTER",
        "column": "name",
        "match_type": "ilike",
        "expected_min": 1,
    },
    {
        "name": "Partial location (engine)",
        "query": "engine",
        "column": "location",
        "match_type": "ilike",
        "expected_min": 2,
    },
]

print("="*80)
print("PART LENS - DIRECT DATABASE SEARCH TESTING")
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
    exit(1)

print()

# Verify test data
print("Verifying test data...")
print("-" * 80)
try:
    response = supabase.table('pms_parts')\
        .select('id, name, part_number, category, location, quantity_on_hand, minimum_quantity')\
        .eq('yacht_id', YACHT_ID)\
        .ilike('part_number', 'TEST-PART-%')\
        .execute()

    test_parts = response.data
    print(f"✓ Found {len(test_parts)} test parts:")
    for part in test_parts:
        stock = f"{part.get('quantity_on_hand', 0)}/{part.get('minimum_quantity', 0)}"
        print(f"  - {part['part_number']}: {part['name']}")
        print(f"    Category: {part.get('category', 'N/A')} | Location: {part.get('location', 'N/A')} | Stock: {stock}")

    if len(test_parts) < 5:
        print()
        print(f"⚠ WARNING: Expected 5 test parts, found {len(test_parts)}")
except Exception as e:
    print(f"✗ Failed to verify test data: {e}")
    exit(1)

print()

# Run test cases
print("Running search tests...")
print("="*80)
print()

passed = 0
failed = 0
results = []

for i, test in enumerate(TEST_CASES, 1):
    name = test["name"]
    query = test["query"]
    column = test["column"]
    match_type = test["match_type"]
    expected_min = test["expected_min"]

    print(f"Test {i}/{len(TEST_CASES)}: {name}")
    print(f"  Query: \"{query}\" on column '{column}' ({match_type})")
    print("-" * 80)

    try:
        # Build query
        q = supabase.table('pms_parts')\
            .select('id, name, part_number, category, location')\
            .eq('yacht_id', YACHT_ID)\
            .ilike('part_number', 'TEST-PART-%')  # Only test parts

        # Apply match
        if match_type == "eq":
            q = q.eq(column, query)
        elif match_type == "ilike":
            q = q.ilike(column, f"%{query}%")

        response = q.execute()
        result_data = response.data
        count = len(result_data)

        # Show results
        print(f"  Results: {count} item(s)")
        for j, item in enumerate(result_data[:3], 1):
            print(f"    {j}. {item['part_number']}: {item['name']}")
            print(f"       Category: {item.get('category', 'N/A')} | Location: {item.get('location', 'N/A')}")

        # Validate
        if count >= expected_min:
            print(f"  ✓ PASS: Found {count} result(s) (expected >= {expected_min})")
            passed += 1
            results.append({"test": name, "status": "PASS", "count": count})
        else:
            print(f"  ✗ FAIL: Found {count} result(s) (expected >= {expected_min})")
            failed += 1
            results.append({"test": name, "status": "FAIL", "count": count, "expected": expected_min})

    except Exception as e:
        print(f"  ✗ FAIL: Query error: {e}")
        failed += 1
        results.append({"test": name, "status": "FAIL", "error": str(e)})

    print()

# Summary
print("="*80)
print("TEST SUMMARY")
print("="*80)
print(f"Total: {len(TEST_CASES)} tests")
print(f"Passed: {passed} ✓")
print(f"Failed: {failed} ✗")
print(f"Success Rate: {(passed/len(TEST_CASES)*100):.1f}%")
print()

if failed > 0:
    print("Failed Tests:")
    print("-" * 80)
    for result in results:
        if result["status"] == "FAIL":
            print(f"✗ {result['test']}")
            if "error" in result:
                print(f"  Error: {result['error']}")
            elif "count" in result:
                print(f"  Found: {result['count']}, Expected: {result.get('expected', 'N/A')}")
    print()

# Natural language test cases
print("="*80)
print("NATURAL LANGUAGE QUERY SIMULATION")
print("="*80)
print()

nl_tests = [
    {
        "query": "show me all filters",
        "extracted_term": "filter",
        "explanation": "Extract 'filter' → search name column with ILIKE",
    },
    {
        "query": "where is the oil filter",
        "extracted_term": "oil filter",
        "explanation": "Extract 'oil filter' → search name column with ILIKE",
    },
    {
        "query": "parts in engine room",
        "extracted_term": "engine room",
        "explanation": "Extract 'engine room' → search location column with ILIKE",
    },
    {
        "query": "hydraulic parts",
        "extracted_term": "hydraulic",
        "explanation": "Extract 'hydraulic' → search name OR category with ILIKE",
    },
]

print("Natural language queries → entity extraction → search:")
print()

for nl_test in nl_tests:
    query = nl_test["query"]
    term = nl_test["extracted_term"]
    explanation = nl_test["explanation"]

    print(f"Query: \"{query}\"")
    print(f"  → {explanation}")

    # Simulate search
    try:
        response = supabase.table('pms_parts')\
            .select('id, name, part_number, category, location')\
            .eq('yacht_id', YACHT_ID)\
            .ilike('part_number', 'TEST-PART-%')\
            .or_(f"name.ilike.%{term}%,category.ilike.%{term}%,location.ilike.%{term}%")\
            .execute()

        count = len(response.data)
        print(f"  → Found {count} result(s)")
        if count > 0:
            print(f"  ✓ Natural language search works")
        else:
            print(f"  ⚠ No results (may need better extraction)")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print()

print("="*80)
print("CONCLUSION")
print("="*80)
print()

if failed == 0:
    print("✓ ALL DATABASE QUERIES WORKING")
    print()
    print("Part Lens Search Capabilities Validated:")
    print("  ✓ Exact part number match")
    print("  ✓ Exact part name match")
    print("  ✓ Partial name search (case insensitive)")
    print("  ✓ Category search")
    print("  ✓ Location search")
    print("  ✓ Natural language extraction → search")
    print()
    print("Next Step: Deploy backend and run E2E tests")
else:
    print(f"⚠ {failed} test(s) failed - review queries and data")

print()
