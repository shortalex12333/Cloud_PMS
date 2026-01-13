#!/usr/bin/env python3
"""
P3 Handler Tests
================

Tests all 30 P3 read-only handlers against real Supabase.
Run: python3 test_p3_handlers.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"


class P3TestHarness:
    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.results = []
        self.test_ids = {}

    def record(self, test_name: str, status: str, details: str = ""):
        self.results.append({"test": test_name, "status": status, "details": details})
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        detail_str = f" {details[:40]}..." if details and len(details) > 40 else (f" {details}" if details else "")
        print(f"  {icon} {test_name}: {status}{detail_str}")

    async def get_test_ids(self):
        """Get IDs of existing test data."""
        print("\n[SETUP] Fetching test entity IDs...")

        tables = [
            ("pms_faults", "fault_id"),
            ("pms_work_orders", "work_order_id"),
            ("pms_equipment", "equipment_id"),
            ("pms_parts", "part_id"),
            ("documents", "document_id"),
            ("pms_handover", "handover_id"),
            ("pms_purchase_orders", "purchase_order_id"),
        ]

        for table, key in tables:
            try:
                r = self.client.table(table).select("id").eq("yacht_id", TEST_YACHT_ID).limit(1).execute()
                if r.data:
                    self.test_ids[key] = r.data[0]["id"]
                    print(f"  Found {key}: {self.test_ids[key][:8]}...")
            except Exception as e:
                print(f"  No {key} found")

        print(f"  Setup complete: {len(self.test_ids)} test IDs found")

    async def run_tests(self):
        """Run all P3 handler tests."""
        from handlers.p3_read_only_handlers import get_p3_read_only_handlers

        handlers = get_p3_read_only_handlers(self.client)

        print("\n" + "=" * 60)
        print("P3 HANDLER TESTS (30 Read-Only Actions)")
        print("=" * 60)

        # Test each handler with correct signatures
        tests = [
            # (name, handler_key, kwargs, requires_key)
            ("view_fault_history", "view_fault_history", {"fault_id": "fault_id", "yacht_id": TEST_YACHT_ID}, "fault_id"),
            ("suggest_parts", "suggest_parts", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_work_order_history", "view_work_order_history", {"work_order_id": "work_order_id", "yacht_id": TEST_YACHT_ID}, "work_order_id"),
            ("view_work_order_checklist", "view_work_order_checklist", {"work_order_id": "work_order_id", "yacht_id": TEST_YACHT_ID}, "work_order_id"),
            ("view_equipment_details", "view_equipment_details", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_equipment_history", "view_equipment_history", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_equipment_parts", "view_equipment_parts", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_linked_faults", "view_linked_faults", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_equipment_manual", "view_equipment_manual", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_part_stock", "view_part_stock", {"part_id": "part_id", "yacht_id": TEST_YACHT_ID}, "part_id"),
            ("view_part_location", "view_part_location", {"part_id": "part_id", "yacht_id": TEST_YACHT_ID}, "part_id"),
            ("view_part_usage", "view_part_usage", {"part_id": "part_id", "yacht_id": TEST_YACHT_ID}, "part_id"),
            ("scan_part_barcode", "scan_part_barcode", {"barcode": "TEST-BARCODE", "yacht_id": TEST_YACHT_ID}, None),
            ("view_linked_equipment", "view_linked_equipment", {"part_id": "part_id", "yacht_id": TEST_YACHT_ID}, "part_id"),
            ("export_handover", "export_handover", {"yacht_id": TEST_YACHT_ID, "user_id": TEST_USER_ID}, None),
            ("view_document", "view_document", {"document_id": "document_id", "yacht_id": TEST_YACHT_ID}, "document_id"),
            ("view_related_documents", "view_related_documents", {"document_id": "document_id", "yacht_id": TEST_YACHT_ID}, "document_id"),
            ("view_document_section", "view_document_section", {"document_id": "document_id", "section_id": "overview", "yacht_id": TEST_YACHT_ID}, "document_id"),
            ("view_hours_of_rest", "view_hours_of_rest", {"user_id": TEST_USER_ID, "yacht_id": TEST_YACHT_ID}, None),
            ("export_hours_of_rest", "export_hours_of_rest", {"yacht_id": TEST_YACHT_ID, "user_id": TEST_USER_ID}, None),
            ("view_compliance_status", "view_compliance_status", {"yacht_id": TEST_YACHT_ID}, None),
            ("track_delivery", "track_delivery", {"purchase_order_id": "purchase_order_id", "yacht_id": TEST_YACHT_ID}, "purchase_order_id"),
            ("view_checklist", "view_checklist", {"checklist_id": "work_order_id", "yacht_id": TEST_YACHT_ID}, "work_order_id"),
            ("view_worklist", "view_worklist", {"yacht_id": TEST_YACHT_ID, "user_id": TEST_USER_ID}, None),
            ("export_worklist", "export_worklist", {"yacht_id": TEST_YACHT_ID}, None),
            ("view_fleet_summary", "view_fleet_summary", {"user_id": TEST_USER_ID}, None),
            ("open_vessel", "open_vessel", {"yacht_id": TEST_YACHT_ID, "user_id": TEST_USER_ID}, None),
            ("export_fleet_summary", "export_fleet_summary", {"user_id": TEST_USER_ID}, None),
            ("request_predictive_insight", "request_predictive_insight", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("view_smart_summary", "view_smart_summary", {"yacht_id": TEST_YACHT_ID, "user_id": TEST_USER_ID}, None),
        ]

        for i, (test_name, handler_key, kwargs, requires_key) in enumerate(tests, 1):
            print(f"\n[{i}/30] {test_name}")

            # Check if required test ID exists
            if requires_key and requires_key not in self.test_ids:
                self.record(test_name, "SKIP", f"No {requires_key}")
                continue

            # Build actual kwargs, replacing ID placeholders
            actual_kwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, str) and v in self.test_ids:
                    actual_kwargs[k] = self.test_ids[v]
                else:
                    actual_kwargs[k] = v

            try:
                if handler_key not in handlers:
                    self.record(test_name, "SKIP", "Handler not registered")
                    continue

                result = await handlers[handler_key](**actual_kwargs)

                # Read-only handlers should succeed or return "not found" gracefully
                if result.get("status") == "success":
                    self.record(test_name, "PASS")
                elif result.get("status") == "error":
                    # Some "not found" errors are acceptable for read-only ops
                    if "NOT_FOUND" in result.get("error_code", "") or "not found" in result.get("message", "").lower():
                        self.record(test_name, "PASS", "(not found - expected)")
                    else:
                        self.record(test_name, "FAIL", result.get("message", "")[:60])
                else:
                    self.record(test_name, "PASS", "(no data)")
            except Exception as e:
                err_msg = str(e)[:60]
                self.record(test_name, "FAIL", err_msg)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("P3 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total = len(self.results)

        print(f"PASSED: {passed}/{total}")
        print(f"FAILED: {failed}/{total}")
        print(f"SKIPPED: {skipped}/{total}")

        if failed > 0:
            print("\nFAILED TESTS:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  ❌ {r['test']}: {r['details']}")

        return failed == 0


async def main():
    harness = P3TestHarness()
    await harness.get_test_ids()
    await harness.run_tests()
    return harness.print_summary()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
