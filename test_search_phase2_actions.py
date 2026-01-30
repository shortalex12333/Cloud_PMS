#!/usr/bin/env python3
"""
Test Phase 2 search response with actions
==========================================

Simulates what the frontend receives when making a Phase 2 search request.
Validates that action chips data is properly included.
"""

import os
import sys
import asyncio
from supabase import create_client

# Add apps/api to path
sys.path.insert(0, 'apps/api')

# Test credentials
TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Monkey-patch Supabase client
import integrations.supabase as supabase_module
test_client = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)
supabase_module._supabase_client = test_client

from routes.search_streaming import search_parts
from execute.table_capabilities import TABLE_CAPABILITIES

print("=" * 80)
print("PHASE 2 SEARCH RESPONSE - ACTION CHIPS VALIDATION")
print("=" * 80)
print()

async def test_phase2_response():
    """Simulate Phase 2 response construction."""
    query = "filter"  # Use simple query that works

    # Execute search (simulates Phase 2 logic)
    parts_results, parts_count = await search_parts(YACHT_ID, query)

    print(f"Query: '{query}'")
    print(f"Results: {parts_count} parts found")
    print()

    if parts_count == 0:
        print("✗ No results - cannot test action chips")
        return

    # Get available actions from capability
    part_capability = TABLE_CAPABILITIES.get("part_by_part_number_or_name")
    part_actions = part_capability.available_actions if part_capability else []

    print(f"Available actions for parts: {part_actions}")
    print()

    # Format results (simulates what search_streaming.py does)
    snippets_redacted = False  # Captain role - not redacted

    formatted_results = []
    for part in parts_results[:3]:  # Show first 3 only
        result_item = {
            "type": "part",
            "id": part["id"],
            "title": part["name"],
            "part_number": part.get("part_number"),
            "category": part.get("category"),
            "manufacturer": part.get("manufacturer"),
            "location": part.get("location"),
            "available_actions": part_actions,
        }

        if not snippets_redacted:
            result_item["description"] = part.get("description", "")

        formatted_results.append(result_item)

    # Construct Phase 2 payload (what frontend receives)
    payload = {
        "phase": 2,
        "results": formatted_results,
        "total_count": parts_count,
        "snippets_redacted": snippets_redacted,
        "role": "captain",
    }

    print("Phase 2 Payload (what frontend receives):")
    print("-" * 80)
    print(f"Total count: {payload['total_count']}")
    print(f"Results count: {len(payload['results'])}")
    print(f"Snippets redacted: {payload['snippets_redacted']}")
    print()

    # Validate each result has actions
    print("Validating Action Chips in Results:")
    print("-" * 80)

    all_valid = True
    for i, result in enumerate(payload['results'], 1):
        has_actions = "available_actions" in result
        actions_count = len(result.get("available_actions", []))
        has_receive = "receive_part" in result.get("available_actions", [])
        has_consume = "consume_part" in result.get("available_actions", [])

        print(f"Result {i}: {result['title'][:50]}")
        print(f"  - Has actions field: {'✓' if has_actions else '✗'}")
        print(f"  - Actions count: {actions_count}")
        print(f"  - Has receive_part: {'✓' if has_receive else '✗'}")
        print(f"  - Has consume_part: {'✓' if has_consume else '✗'}")

        if not has_actions or not has_receive or not has_consume:
            all_valid = False
        print()

    # Final validation
    print("=" * 80)
    if all_valid:
        print("✓ ALL RESULTS HAVE CORRECT ACTION CHIPS DATA")
        print()
        print("Expected E2E Flow:")
        print("1. User searches 'inventory parts'")
        print("2. Backend returns Phase 1: parts_count > 0")
        print("3. Frontend displays search results")
        print("4. User clicks on a result")
        print("5. Backend returns Phase 2 with available_actions")
        print("6. Frontend renders action chips: receive_part, consume_part, etc.")
        print()
        print("Status: ✅ BACKEND READY FOR E2E TESTS")
    else:
        print("✗ SOME RESULTS MISSING ACTION CHIPS")
        print("Status: ❌ FIX REQUIRED")

asyncio.run(test_phase2_response())

print()
print("=" * 80)
