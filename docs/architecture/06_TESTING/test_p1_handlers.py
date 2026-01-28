#!/usr/bin/env python3
"""
P1 Handler Tests
================

Tests P1 actions against real Supabase:
- create_work_order
- create_purchase_request
- order_part
- approve_purchase

Run: python -m apps.api.test_p1_handlers
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Test configuration
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-3e0e-4ee8-95d3-19b7c25e0df9"


def get_test_signature():
    """Generate test signature."""
    return {
        "user_id": TEST_USER_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "test_p1_handlers"
    }


async def test_create_work_order(handlers):
    """Test create_work_order action."""
    print("\n" + "=" * 60)
    print("TEST: create_work_order")
    print("=" * 60)

    result = await handlers.create_work_order_execute(
        title="P1 Test Work Order - Routine Maintenance",
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        description="Test work order created by P1 handler test",
        equipment_id=None,  # No equipment for this test
        priority="routine",
        signature=get_test_signature()
    )

    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        wo = result.get("result", {}).get("work_order", {})
        print(f"  WO Number: {wo.get('number')}")
        print(f"  WO ID: {wo.get('id')}")
        print(f"  Status: {wo.get('status')}")
        print(f"  Audit Log ID: {result.get('result', {}).get('audit_log_id')}")
        return wo.get("id")
    else:
        print(f"  Error: {result.get('error_code')}: {result.get('message')}")
        return None


async def test_create_purchase_request(handlers):
    """Test create_purchase_request action."""
    print("\n" + "=" * 60)
    print("TEST: create_purchase_request")
    print("=" * 60)

    result = await handlers.create_purchase_request_execute(
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        supplier_id=None,  # No supplier for this test
        notes="P1 Test Purchase Request",
        items=None,  # No items for this test
        signature=get_test_signature()
    )

    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        po = result.get("result", {}).get("purchase_order", {})
        print(f"  PO Number: {po.get('po_number')}")
        print(f"  PO ID: {po.get('id')}")
        print(f"  Status: {po.get('status')}")
        print(f"  Audit Log ID: {result.get('result', {}).get('audit_log_id')}")
        return po.get("id")
    else:
        print(f"  Error: {result.get('error_code')}: {result.get('message')}")
        return None


async def test_order_part(handlers, po_id):
    """Test order_part action."""
    print("\n" + "=" * 60)
    print("TEST: order_part")
    print("=" * 60)

    if not po_id:
        print("  SKIPPED: No PO ID from previous test")
        return None

    # First get a part ID from the database
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    part_result = client.table("pms_parts").select("id, name, part_number").eq(
        "yacht_id", TEST_YACHT_ID
    ).limit(1).execute()

    if not part_result.data:
        print("  SKIPPED: No parts found in database")
        return None

    part = part_result.data[0]
    print(f"  Using part: {part.get('name')} ({part.get('part_number')})")

    result = await handlers.order_part_execute(
        purchase_order_id=po_id,
        part_id=part["id"],
        quantity=2,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        unit_price=99.99,
        notes="P1 Test Order Part",
        signature=get_test_signature()
    )

    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        item = result.get("result", {}).get("line_item", {})
        print(f"  Line Item ID: {item.get('id')}")
        print(f"  Quantity: {item.get('quantity_ordered')}")
        print(f"  Audit Log ID: {result.get('result', {}).get('audit_log_id')}")
        return item.get("id")
    else:
        print(f"  Error: {result.get('error_code')}: {result.get('message')}")
        return None


async def test_approve_purchase(handlers, po_id):
    """Test approve_purchase action."""
    print("\n" + "=" * 60)
    print("TEST: approve_purchase")
    print("=" * 60)

    if not po_id:
        print("  SKIPPED: No PO ID from previous test")
        return None

    result = await handlers.approve_purchase_execute(
        purchase_order_id=po_id,
        yacht_id=TEST_YACHT_ID,
        user_id=TEST_USER_ID,
        user_role="captain",  # Approved role
        approval_notes="P1 Test Approval",
        signature=get_test_signature()
    )

    print(f"Status: {result.get('status')}")
    if result.get("status") == "success":
        po = result.get("result", {}).get("purchase_order", {})
        print(f"  PO Number: {po.get('po_number')}")
        print(f"  New Status: {po.get('status')}")
        print(f"  Approved At: {po.get('approved_at')}")
        print(f"  Audit Log ID: {result.get('result', {}).get('audit_log_id')}")
        return po.get("id")
    else:
        print(f"  Error: {result.get('error_code')}: {result.get('message')}")
        return None


async def verify_audit_logs(client, yacht_id):
    """Verify audit log entries were created."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Audit Logs")
    print("=" * 60)

    result = client.table("pms_audit_log").select(
        "id, action, entity_type, created_at"
    ).eq("yacht_id", yacht_id).order(
        "created_at", desc=True
    ).limit(10).execute()

    if result.data:
        print(f"  Found {len(result.data)} recent audit entries:")
        for entry in result.data[:5]:
            print(f"    - {entry['action']} ({entry['entity_type']}) at {entry['created_at']}")
    else:
        print("  No audit entries found")


async def main():
    """Run all P1 tests."""
    print("=" * 60)
    print("P1 HANDLER TESTS")
    print("=" * 60)
    print(f"Yacht ID: {TEST_YACHT_ID}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Supabase URL: {SUPABASE_URL}")

    if not SUPABASE_KEY:
        print("\nERROR: SUPABASE_SERVICE_KEY not set")
        print("Run: export SUPABASE_SERVICE_KEY=your_key")
        return

    # Initialize
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Import handlers
    from handlers.p1_purchasing_handlers import P1PurchasingHandlers
    handlers = P1PurchasingHandlers(client)

    # Run tests
    wo_id = await test_create_work_order(handlers)
    po_id = await test_create_purchase_request(handlers)
    item_id = await test_order_part(handlers, po_id)
    await test_approve_purchase(handlers, po_id)

    # Verify audit logs
    await verify_audit_logs(client, TEST_YACHT_ID)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  create_work_order: {'PASSED' if wo_id else 'FAILED'}")
    print(f"  create_purchase_request: {'PASSED' if po_id else 'FAILED'}")
    print(f"  order_part: {'PASSED' if item_id else 'SKIPPED/FAILED'}")
    print(f"  approve_purchase: {'Check above for result'}")


if __name__ == "__main__":
    asyncio.run(main())
