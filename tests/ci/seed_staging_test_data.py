#!/usr/bin/env python3
"""
Seed staging database with test data for inventory acceptance tests.

Creates test parts, stock records, and categories for CI testing.
Idempotent - safe to run multiple times.
"""
import os
import sys
from supabase import create_client

# Staging credentials
MASTER_URL = os.getenv("MASTER_SUPABASE_URL", "https://qvzmkaamzaqxpzbewjxe.supabase.co")
MASTER_SERVICE_KEY = os.getenv("MASTER_SUPABASE_SERVICE_ROLE_KEY")
TEST_YACHT_ID = os.getenv("TEST_YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")

if not MASTER_SERVICE_KEY:
    print("❌ MASTER_SUPABASE_SERVICE_ROLE_KEY not set", file=sys.stderr)
    sys.exit(1)

# Test parts with fixed UUIDs for CI
TEST_PARTS = [
    {
        "part_id": "00000000-0000-4000-8000-000000000001",
        "part_number": "TEST-PART-001",
        "part_name": "Test Part - Consumable",
        "category": "test_category",
        "manufacturer": "Test Manufacturer",
        "initial_stock": 100,
        "location": "test_location_A"
    },
    {
        "part_id": "00000000-0000-4000-8000-000000000002",
        "part_number": "TEST-PART-002",
        "part_name": "Test Part - Adjustable",
        "category": "test_category",
        "manufacturer": "Test Manufacturer",
        "initial_stock": 50,
        "location": "test_location_B"
    },
    {
        "part_id": "00000000-0000-4000-8000-000000000003",
        "part_number": "TEST-PART-003",
        "part_name": "Test Part - Receivable",
        "category": "test_category",
        "manufacturer": "Test Manufacturer",
        "initial_stock": 0,
        "location": "test_location_A"
    },
    {
        "part_id": "00000000-0000-4000-8000-000000000004",
        "part_number": "TEST-PART-004",
        "part_name": "Test Part - Insufficient Stock",
        "category": "test_category",
        "manufacturer": "Test Manufacturer",
        "initial_stock": 2,  # Low stock for insufficient stock tests
        "location": "test_location_A"
    },
    {
        "part_id": "00000000-0000-4000-8000-000000000005",
        "part_number": "TEST-PART-005",
        "part_name": "Test Part - Transferable",
        "category": "test_category",
        "manufacturer": "Test Manufacturer",
        "initial_stock": 25,
        "location": "test_location_A"
    }
]


def seed_test_data():
    """Seed test parts and stock records."""
    print("=" * 80)
    print("SEEDING STAGING TEST DATA")
    print("=" * 80)
    print()
    print(f"Master URL: {MASTER_URL}")
    print(f"Test Yacht: {TEST_YACHT_ID}")
    print()

    db = create_client(MASTER_URL, MASTER_SERVICE_KEY)

    # Check yacht exists
    yacht_result = db.table("fleet_registry").select("yacht_id, yacht_name").eq("yacht_id", TEST_YACHT_ID).maybe_single().execute()
    if not yacht_result or not yacht_result.data:
        print(f"❌ Yacht {TEST_YACHT_ID} not found in fleet_registry")
        sys.exit(1)

    print(f"✅ Yacht found: {yacht_result.data.get('yacht_name')}")
    print()

    # Seed each test part
    for part in TEST_PARTS:
        print(f"Processing: {part['part_number']} ({part['part_name']})")

        # 1. Upsert part in pms_parts_catalog (yacht-specific)
        try:
            part_data = {
                "part_id": part["part_id"],
                "yacht_id": TEST_YACHT_ID,
                "part_number": part["part_number"],
                "part_name": part["part_name"],
                "category": part["category"],
                "manufacturer": part["manufacturer"],
                "is_active": True,
                "reorder_level": 10,
                "reorder_quantity": 20,
                "unit_cost": 100.00,
                "currency": "USD"
            }

            # Use upsert() to insert or update based on primary key
            db.table("pms_parts_catalog").upsert(part_data, on_conflict="part_id,yacht_id").execute()
            print(f"  ✅ Upserted part in catalog")

        except Exception as e:
            print(f"  ⚠️  Part catalog error: {e}")

        # 2. Upsert stock record in pms_inventory_stock
        try:
            stock_data = {
                "yacht_id": TEST_YACHT_ID,
                "part_id": part["part_id"],
                "location": part["location"],
                "quantity": part["initial_stock"],
                "is_active": True
            }

            # Use upsert() - Supabase will handle insert-or-update based on unique constraints
            # The unique constraint is likely on (yacht_id, part_id, location)
            db.table("pms_inventory_stock").upsert(stock_data, on_conflict="yacht_id,part_id,location").execute()
            print(f"  ✅ Upserted stock record ({part['initial_stock']} units at {part['location']})")

        except Exception as e:
            print(f"  ⚠️  Stock record error: {e}")

        print()

    print("=" * 80)
    print("SEEDING COMPLETE")
    print("=" * 80)
    print()
    print("Test Part IDs for use in tests:")
    for part in TEST_PARTS:
        print(f"  {part['part_number']}: {part['part_id']}")
    print()

    # Write part IDs to environment for tests
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as f:
            f.write(f"TEST_PART_CONSUMABLE={TEST_PARTS[0]['part_id']}\n")
            f.write(f"TEST_PART_ADJUSTABLE={TEST_PARTS[1]['part_id']}\n")
            f.write(f"TEST_PART_RECEIVABLE={TEST_PARTS[2]['part_id']}\n")
            f.write(f"TEST_PART_LOW_STOCK={TEST_PARTS[3]['part_id']}\n")
            f.write(f"TEST_PART_TRANSFERABLE={TEST_PARTS[4]['part_id']}\n")
        print("✅ Part IDs exported to GITHUB_ENV")
    else:
        print("💡 Export commands for local testing:")
        print(f"export TEST_PART_CONSUMABLE={TEST_PARTS[0]['part_id']}")
        print(f"export TEST_PART_ADJUSTABLE={TEST_PARTS[1]['part_id']}")
        print(f"export TEST_PART_RECEIVABLE={TEST_PARTS[2]['part_id']}")
        print(f"export TEST_PART_LOW_STOCK={TEST_PARTS[3]['part_id']}")
        print(f"export TEST_PART_TRANSFERABLE={TEST_PARTS[4]['part_id']}")


if __name__ == "__main__":
    seed_test_data()
