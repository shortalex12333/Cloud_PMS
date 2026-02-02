#!/usr/bin/env python3
"""
Comprehensive validation test for all lens entity type mappings.

Tests that all entity types from all 5 lenses have proper capability mappings.
"""

import sys
sys.path.insert(0, 'apps/api')

from prepare.capability_composer import ENTITY_TO_SEARCH_COLUMN

# Define all expected entity types per lens
EXPECTED_MAPPINGS = {
    # Parts Lens (6 types)
    'PART_NUMBER': 'part_by_part_number_or_name',
    'PART_NAME': 'part_by_part_number_or_name',
    'MANUFACTURER': 'part_by_part_number_or_name',
    'BRAND': 'part_by_part_number_or_name',              # NEW - PR #69
    'EQUIPMENT_BRAND': 'part_by_part_number_or_name',    # NEW - PR #69
    'ORG': 'part_by_part_number_or_name',                # NEW - PR #69

    # Inventory Lens (5 types)
    'LOCATION': 'inventory_by_location',
    'STOCK_QUERY': 'inventory_by_location',
    'STOCK_STATUS': 'inventory_by_location',
    'LOW_STOCK': 'inventory_by_location',
    'OUT_OF_STOCK': 'inventory_by_location',
    'REORDER_NEEDED': 'inventory_by_location',

    # Shopping List Lens (7 types)
    'SHOPPING_LIST_ITEM': 'shopping_list_by_item_or_status',
    'SHOPPING_LIST_TERM': 'shopping_list_by_item_or_status',    # NEW
    'REQUESTED_PART': 'shopping_list_by_item_or_status',
    'REQUESTER_NAME': 'shopping_list_by_item_or_status',
    'URGENCY_LEVEL': 'shopping_list_by_item_or_status',
    'APPROVAL_STATUS': 'shopping_list_by_item_or_status',
    'SOURCE_TYPE': 'shopping_list_by_item_or_status',

    # Receiving Lens (7 types)
    'PO_NUMBER': 'receiving_by_po_or_supplier',
    'RECEIVING_ID': 'receiving_by_po_or_supplier',
    'SUPPLIER_NAME': 'receiving_by_po_or_supplier',
    'INVOICE_NUMBER': 'receiving_by_po_or_supplier',
    'DELIVERY_DATE': 'receiving_by_po_or_supplier',
    'RECEIVER_NAME': 'receiving_by_po_or_supplier',
    'RECEIVING_STATUS': 'receiving_by_po_or_supplier',

    # Crew Lens (3 types)
    'REST_COMPLIANCE': 'crew_hours_of_rest_search',
    'WARNING_SEVERITY': 'crew_warnings_search',
    'WARNING_STATUS': 'crew_warnings_search',
}

# Organize by lens for reporting
LENS_GROUPS = {
    'Parts Lens': ['PART_NUMBER', 'PART_NAME', 'MANUFACTURER', 'BRAND', 'EQUIPMENT_BRAND', 'ORG'],
    'Inventory Lens': ['LOCATION', 'STOCK_QUERY', 'STOCK_STATUS', 'LOW_STOCK', 'OUT_OF_STOCK', 'REORDER_NEEDED'],
    'Shopping List Lens': ['SHOPPING_LIST_ITEM', 'SHOPPING_LIST_TERM', 'REQUESTED_PART', 'REQUESTER_NAME', 'URGENCY_LEVEL', 'APPROVAL_STATUS', 'SOURCE_TYPE'],
    'Receiving Lens': ['PO_NUMBER', 'RECEIVING_ID', 'SUPPLIER_NAME', 'INVOICE_NUMBER', 'DELIVERY_DATE', 'RECEIVER_NAME', 'RECEIVING_STATUS'],
    'Crew Lens': ['REST_COMPLIANCE', 'WARNING_SEVERITY', 'WARNING_STATUS'],
}

def test_entity_mappings():
    """Test all entity type mappings are present and correct."""
    print("=" * 80)
    print("ALL LENS ENTITY TYPE MAPPING VALIDATION")
    print("=" * 80)
    print()

    total_passed = 0
    total_failed = 0
    failed_mappings = []

    for lens_name, entity_types in LENS_GROUPS.items():
        print(f"\n{'=' * 80}")
        print(f"  {lens_name}")
        print(f"{'=' * 80}")

        lens_passed = 0
        lens_failed = 0

        for entity_type in entity_types:
            expected_capability = EXPECTED_MAPPINGS[entity_type]

            # Check if mapping exists
            if entity_type not in ENTITY_TO_SEARCH_COLUMN:
                print(f"  ❌ FAIL: {entity_type} - NOT MAPPED")
                lens_failed += 1
                total_failed += 1
                failed_mappings.append((lens_name, entity_type, "NOT_MAPPED"))
                continue

            # Check if capability is correct
            actual_capability, _ = ENTITY_TO_SEARCH_COLUMN[entity_type]
            if actual_capability != expected_capability:
                print(f"  ❌ FAIL: {entity_type}")
                print(f"      Expected: {expected_capability}")
                print(f"      Actual: {actual_capability}")
                lens_failed += 1
                total_failed += 1
                failed_mappings.append((lens_name, entity_type, "WRONG_CAPABILITY"))
            else:
                print(f"  ✅ PASS: {entity_type} → {actual_capability}")
                lens_passed += 1
                total_passed += 1

        # Lens summary
        print(f"\n  {lens_name} Results: {lens_passed}/{len(entity_types)} passed")

    # Overall summary
    print(f"\n{'=' * 80}")
    print(f"OVERALL RESULTS")
    print(f"{'=' * 80}")
    print(f"Total Entity Types Tested: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print()

    if total_failed == 0:
        print("✅ ALL ENTITY TYPE MAPPINGS VALIDATED SUCCESSFULLY")
        print()
        print("All 5 lenses have complete and correct entity type mappings:")
        print("  • Parts Lens: 6 types")
        print("  • Inventory Lens: 6 types")
        print("  • Shopping List Lens: 7 types")
        print("  • Receiving Lens: 7 types")
        print("  • Crew Lens: 3 types")
        print()
        print("Total: 29 entity types mapped to capabilities")
        return 0
    else:
        print(f"❌ {total_failed} ENTITY TYPE MAPPINGS FAILED")
        print()
        print("Failed Mappings:")
        for lens_name, entity_type, reason in failed_mappings:
            print(f"  • {lens_name}: {entity_type} ({reason})")
        return 1

    print("=" * 80)

if __name__ == "__main__":
    exit_code = test_entity_mappings()
    sys.exit(exit_code)
