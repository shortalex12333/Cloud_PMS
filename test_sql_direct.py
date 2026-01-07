#!/usr/bin/env python3
"""
Direct SQL test - bypasses entity extraction to test SQL improvements.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from supabase import create_client
from execute.capability_executor import CapabilityExecutor

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def main():
    print("="*60)
    print("DIRECT SQL TEST - Smart Pattern Matching")
    print("="*60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    executor = CapabilityExecutor(client, TEST_YACHT_ID)

    # Test 1: Multi-token pattern matching on fault codes
    print("\n[TEST 1] Fault code: 'MID 128'")
    result = executor.execute(
        "fault_by_fault_code",
        {"code": "MID 128"},
        limit=5
    )
    print(f"Success: {result.success}")
    print(f"Query: {result.generated_query}")
    print(f"Results: {result.row_count}")
    if result.rows:
        print(f"First match: {result.rows[0].get('code')} - {result.rows[0].get('name')}")
        # Check metadata
        if '_capability' in result.rows[0]:
            print(f"✓ Metadata tagged: _capability = {result.rows[0]['_capability']}")
    print()

    # Test 2: Multi-word part search
    print("[TEST 2] Part search: 'fuel filter'")
    result = executor.execute(
        "part_by_part_number_or_name",
        {"name": "fuel filter"},
        limit=5
    )
    print(f"Success: {result.success}")
    print(f"Query: {result.generated_query}")
    print(f"Results: {result.row_count}")
    if result.rows:
        for i, row in enumerate(result.rows[:3]):
            print(f"  {i+1}. {row.get('name')} ({row.get('part_number')})")
    print()

    # Test 3: Multi-word equipment search
    print("[TEST 3] Equipment: 'main engine'")
    result = executor.execute(
        "equipment_by_name_or_model",
        {"name": "main engine"},
        limit=5
    )
    print(f"Success: {result.success}")
    print(f"Query: {result.generated_query}")
    print(f"Results: {result.row_count}")
    if result.rows:
        for i, row in enumerate(result.rows[:3]):
            print(f"  {i+1}. {row.get('name')} - {row.get('manufacturer')} {row.get('model')}")
    print()

    # Test 4: Check pattern generation
    print("[TEST 4] Pattern Generation Test")
    pattern = executor._generate_smart_pattern("MID 128")
    print(f"Input: 'MID 128'")
    print(f"Pattern: {pattern}")
    print(f"Expected: %MID%128%")
    print(f"✓ Match!" if pattern == "%MID%128%" else "✗ No match")
    print()

    pattern = executor._generate_smart_pattern("turbo gasket")
    print(f"Input: 'turbo gasket'")
    print(f"Pattern: {pattern}")
    print(f"Expected: %turbo%gasket%")
    print(f"✓ Match!" if pattern == "%turbo%gasket%" else "✗ No match")

    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
