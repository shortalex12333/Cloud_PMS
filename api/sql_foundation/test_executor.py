#!/usr/bin/env python3
"""
TEST: Full Executor Flow
========================
Tests entity → compile → execute → results
"""
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Config
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def test_full_flow():
    """Test entity → search → results."""
    print("=" * 60)
    print("SQL FOUNDATION: FULL EXECUTOR TEST")
    print("=" * 60)

    # Create Supabase client
    client = create_client(SUPABASE_URL, SERVICE_KEY)

    from api.sql_foundation import search

    # Test cases
    test_cases = [
        {
            "name": "Part number lookup",
            "entities": [{"type": "PART_NUMBER", "value": "ENG-0008-103"}],
            "expect_min": 1
        },
        {
            "name": "Equipment name search",
            "entities": [{"type": "EQUIPMENT_NAME", "value": "Generator"}],
            "expect_min": 2
        },
        {
            "name": "Fault code lookup",
            "entities": [{"type": "FAULT_CODE", "value": "E047"}],
            "expect_min": 1
        },
        {
            "name": "Supplier search",
            "entities": [{"type": "SUPPLIER_NAME", "value": "Marine"}],
            "expect_min": 1
        },
        {
            "name": "Multi-entity (part + manufacturer)",
            "entities": [
                {"type": "PART_NAME", "value": "fuel"},
                {"type": "MANUFACTURER", "value": "MTU"}
            ],
            "expect_min": 1
        },
        {
            "name": "Symptom search",
            "entities": [{"type": "SYMPTOM", "value": "shaking"}],
            "expect_min": 1
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        print(f"Entities: {test['entities']}")

        result = search(
            supabase_client=client,
            yacht_id=YACHT_ID,
            entities=test['entities'],
            max_results=10
        )

        print(f"Results: {result.total_count} rows")
        print(f"Waves: {result.waves_executed}, Probes: {result.probes_executed}")
        print(f"Time: {result.execution_time_ms}ms")

        if result.wave_details:
            for wd in result.wave_details:
                print(f"  Wave {wd['wave']}: {wd['probes']} probes, {wd['rows']} rows, {wd['time_ms']}ms")

        if result.errors:
            print(f"Errors: {result.errors[:2]}")

        # Check result
        if result.total_count >= test['expect_min']:
            print(f"✓ PASS (expected >= {test['expect_min']})")
            passed += 1
        else:
            print(f"✗ FAIL (expected >= {test['expect_min']}, got {result.total_count})")
            failed += 1

        # Show sample results
        if result.rows:
            for row in result.rows[:2]:
                # Get first few fields
                fields = list(row.items())[:3]
                print(f"  → {dict(fields)}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(test_cases)} passed")
    print("=" * 60)

    return passed, failed

if __name__ == "__main__":
    test_full_flow()
