#!/usr/bin/env python3
"""Check what parts exist in the database."""

import os
from supabase import create_client

TENANT_URL = os.getenv("TENANT_SUPABASE_URL")
TENANT_KEY = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test part IDs
TEST_PARTS = {
    "TEAK_COMPOUND": "5dd34337-c4c4-41dd-9c6b-adf84af349a8",
    "WATER_PUMP": "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",
    "CYLINDER_RING": "5543266b-2d8c-46a0-88e2-74a7ab403cdd",
}

db = create_client(TENANT_URL, TENANT_KEY)

print("=" * 70)
print("CHECKING PARTS IN DATABASE")
print("=" * 70)

# Check if test parts exist
print("\nTest parts:")
for name, part_id in TEST_PARTS.items():
    result = db.table("pms_parts").select("id, name, part_number").eq("id", part_id).eq("yacht_id", YACHT_ID).execute()
    
    if result.data:
        print(f"✅ {name}: FOUND - {result.data[0].get('name')}")
    else:
        print(f"❌ {name}: NOT FOUND ({part_id})")

# Get actual parts in database for this yacht
print(f"\nActual parts in database for yacht {YACHT_ID[:8]}...:")
result = db.table("pms_parts").select("id, name, part_number").eq("yacht_id", YACHT_ID).limit(10).execute()

if result.data:
    print(f"Found {len(result.data)} parts:")
    for part in result.data[:5]:
        print(f"  - {part.get('name')} | ID: {part.get('id')}")
else:
    print("  No parts found in database!")

