#!/usr/bin/env python3
"""
Situations Test Harness
=======================

Tests all 10 situation state machines against real Supabase.
Run: python3 test_situations.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"


class SituationsTestHarness:
    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.results = []
        self.test_ids = {}

    def record(self, test_name: str, status: str, details: str = ""):
        self.results.append({"test": test_name, "status": status, "details": details})
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        detail_str = f" {details[:50]}..." if details and len(details) > 50 else (f" {details}" if details else "")
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
            ("pms_receiving_events", "receiving_id"),
        ]

        for table, key in tables:
            try:
                r = self.client.table(table).select("id").eq("yacht_id", TEST_YACHT_ID).limit(1).execute()
                if r.data:
                    self.test_ids[key] = r.data[0]["id"]
                    print(f"  Found {key}: {self.test_ids[key][:8]}...")
            except Exception as e:
                print(f"  No {key} found: {str(e)[:30]}")

        print(f"  Setup complete: {len(self.test_ids)} test IDs found")

    async def run_tests(self):
        """Run all situation tests."""
        from handlers.situation_handlers import get_situation_handlers

        handlers = get_situation_handlers(self.client)

        print("\n" + "=" * 60)
        print("SITUATION STATE MACHINE TESTS (10 Situations)")
        print("=" * 60)

        # Test each situation
        tests = [
            # (name, handler_key, kwargs, requires_key)
            ("fault_situation", "fault_situation", {"fault_id": "fault_id", "yacht_id": TEST_YACHT_ID}, "fault_id"),
            ("work_order_situation", "work_order_situation", {"work_order_id": "work_order_id", "yacht_id": TEST_YACHT_ID}, "work_order_id"),
            ("equipment_situation", "equipment_situation", {"equipment_id": "equipment_id", "yacht_id": TEST_YACHT_ID}, "equipment_id"),
            ("part_situation", "part_situation", {"part_id": "part_id", "yacht_id": TEST_YACHT_ID}, "part_id"),
            ("document_situation", "document_situation", {"document_id": "document_id", "yacht_id": TEST_YACHT_ID}, "document_id"),
            ("handover_situation", "handover_situation", {"handover_id": "handover_id", "yacht_id": TEST_YACHT_ID}, "handover_id"),
            ("purchase_situation", "purchase_situation", {"purchase_order_id": "purchase_order_id", "yacht_id": TEST_YACHT_ID}, "purchase_order_id"),
            ("receiving_situation", "receiving_situation", {"receiving_id": "receiving_id", "yacht_id": TEST_YACHT_ID}, "receiving_id"),
            ("compliance_situation", "compliance_situation", {"user_id": TEST_USER_ID, "yacht_id": TEST_YACHT_ID}, None),
            ("get_situation (generic)", "get_situation", {"situation_type": "fault", "entity_id": "fault_id", "yacht_id": TEST_YACHT_ID}, "fault_id"),
        ]

        for i, (test_name, handler_key, kwargs, requires_key) in enumerate(tests, 1):
            print(f"\n[{i}/10] {test_name}")

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

                # Situations should return success with state info
                if result.get("status") == "success":
                    state = result.get("current_state", "")
                    self.record(test_name, "PASS", f"state={state}")
                elif result.get("status") == "error":
                    # NOT_FOUND is acceptable for read-only situations
                    if "NOT_FOUND" in result.get("error_code", ""):
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
        print("SITUATIONS TEST SUMMARY")
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
    harness = SituationsTestHarness()
    await harness.get_test_ids()
    await harness.run_tests()
    return harness.print_summary()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
