#!/usr/bin/env python3
"""
Direct test of plan_capabilities function to debug why it returns empty list
"""

import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

from prepare.capability_composer import plan_capabilities, ENTITY_TO_SEARCH_COLUMN
from execute.table_capabilities import get_active_capabilities, TABLE_CAPABILITIES

# Test entities (same structure as returned by extraction)
test_entities = [
    {
        "type": "STOCK_STATUS",
        "value": "low stock",
        "confidence": 0.8
    },
    {
        "type": "LOW_STOCK",
        "value": "low stock",
        "confidence": 0.8,
        "source": "inventory_lens_transformation"
    }
]

print("=" * 80)
print("DEBUGGING plan_capabilities()")
print("=" * 80)

print("\n1. Test Entities:")
for e in test_entities:
    print(f"   {e}")

print("\n2. Checking ENTITY_TO_SEARCH_COLUMN mappings:")
for entity in test_entities:
    entity_type = entity.get("type")
    mapping = ENTITY_TO_SEARCH_COLUMN.get(entity_type)
    print(f"   {entity_type}: {mapping}")

print("\n3. Checking active capabilities:")
active_caps = get_active_capabilities()
print(f"   Total active: {len(active_caps)}")
if "inventory_by_location" in active_caps:
    cap = active_caps["inventory_by_location"]
    print(f"   ✓ inventory_by_location IS ACTIVE")
    print(f"     Entity triggers: {cap.entity_triggers}")
else:
    print(f"   ✗ inventory_by_location NOT ACTIVE")

print("\n4. Calling plan_capabilities()...")
try:
    plans = plan_capabilities(test_entities)
    print(f"   Plans returned: {len(plans)}")
    for i, plan in enumerate(plans, 1):
        print(f"   Plan {i}:")
        print(f"     Capability: {plan.capability_name}")
        print(f"     Entity type: {plan.entity_type}")
        print(f"     Entity value: {plan.entity_value}")
        print(f"     Search column: {plan.search_column}")
        print(f"     Blocked: {plan.blocked}")
        if plan.blocked:
            print(f"     Blocked reason: {plan.blocked_reason}")
except Exception as e:
    print(f"   ✗ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("END DEBUG")
print("=" * 80)
