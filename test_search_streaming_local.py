#!/usr/bin/env python3
"""
Local test for search streaming with preprocessing
==================================================

Validates that the integrated preprocessing works correctly
with the actual backend search implementation.
"""

import os
import sys
import asyncio
from supabase import create_client

# Add apps/api to path
sys.path.insert(0, 'apps/api')

from routes.search_streaming import preprocess_search_query, search_parts

# Test credentials
TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Set environment for supabase integration
os.environ['SUPABASE_URL'] = TENANT_1_URL
os.environ['SUPABASE_SERVICE_KEY'] = TENANT_1_SERVICE_KEY

print("=" * 80)
print("SEARCH STREAMING - LOCAL INTEGRATION TEST")
print("=" * 80)
print()

# Test preprocessing
test_queries = [
    ("show me filters", "filters"),
    ("where is oil filter", "oil filter"),
    ("  filter  ", "filter"),
    ("the pump", "pump"),
    ("that filter thing", "filter"),
    ("I need seal", "seal"),
]

print("Testing Query Preprocessing:")
print("-" * 80)
for original, expected in test_queries:
    processed = preprocess_search_query(original)
    status = "✓" if processed == expected else "✗"
    print(f"{status} '{original}' → '{processed}' (expected: '{expected}')")

print()

# Test actual search (using direct Supabase client)
print("Testing Integrated Search:")
print("-" * 80)

# Monkey-patch the get_supabase_client function to use our test client
import integrations.supabase as supabase_module
test_client = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)
supabase_module._supabase_client = test_client

async def test_search():
    test_cases = [
        "filters",
        "oil filter",
        "pump",
        "seal",
        "volvo",
        "engine room",
    ]

    for query in test_cases:
        try:
            results, count = await search_parts(YACHT_ID, query)
            status = "✓" if count > 0 else "✗"
            sample = results[0]['name'][:50] if results else "N/A"
            print(f"{status} '{query}': {count} results - Sample: {sample}")
        except Exception as e:
            print(f"✗ '{query}': ERROR - {str(e)[:60]}")

    # Test that results include available_actions
    print()
    print("Testing Actions Inclusion:")
    print("-" * 80)

    from execute.table_capabilities import TABLE_CAPABILITIES
    part_capability = TABLE_CAPABILITIES.get("part_by_part_number_or_name")

    if part_capability:
        actions = part_capability.available_actions
        print(f"✓ Part capability has {len(actions)} actions: {actions}")

        # Check if receive_part and consume_part are included
        if "receive_part" in actions:
            print("✓ receive_part action is available")
        else:
            print("✗ receive_part action is MISSING")

        if "consume_part" in actions:
            print("✓ consume_part action is available")
        else:
            print("✗ consume_part action is MISSING")
    else:
        print("✗ Part capability not found in TABLE_CAPABILITIES")

asyncio.run(test_search())

print()
print("=" * 80)
print("Test complete!")
print("=" * 80)
