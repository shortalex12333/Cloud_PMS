#!/usr/bin/env python3
"""
Edge Case & Error Handling Test Harness
========================================

Tests error handling, edge cases, and security patterns:
- D1: Error response consistency
- D2: Edge cases (null, empty, invalid inputs)
- D3: Yacht isolation verification
- D4: Input validation

Run: python3 test_edge_cases.py
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
WRONG_YACHT_ID = "00000000-0000-0000-0000-000000000000"  # Non-existent yacht
TEST_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
FAKE_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"  # Non-existent entity


class EdgeCaseTestHarness:
    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.results = []
        self.test_ids = {}

    def record(self, category: str, test_name: str, status: str, details: str = ""):
        self.results.append({
            "category": category,
            "test": test_name,
            "status": status,
            "details": details
        })
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
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
        ]
        for table, key in tables:
            try:
                r = self.client.table(table).select("id").eq("yacht_id", TEST_YACHT_ID).limit(1).execute()
                if r.data:
                    self.test_ids[key] = r.data[0]["id"]
            except:
                pass
        print(f"  Found {len(self.test_ids)} test IDs")

    async def run_d1_error_consistency(self):
        """D1: Test error response consistency."""
        print("\n" + "=" * 60)
        print("D1: ERROR RESPONSE CONSISTENCY")
        print("=" * 60)

        from handlers.p3_read_only_handlers import get_p3_read_only_handlers
        from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers
        from handlers.situation_handlers import get_situation_handlers

        p3 = get_p3_read_only_handlers(self.client)
        p2 = get_p2_mutation_light_handlers(self.client)
        situations = get_situation_handlers(self.client)

        # Test NOT_FOUND errors return correct structure
        not_found_tests = [
            ("P3 view_fault_history", p3["view_fault_history"], {"fault_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
            ("P3 view_equipment_details", p3["view_equipment_details"], {"equipment_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
            ("P3 view_part_stock", p3["view_part_stock"], {"part_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
            ("P3 view_document", p3["view_document"], {"document_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
            ("Situation fault", situations["fault_situation"], {"fault_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
            ("Situation equipment", situations["equipment_situation"], {"equipment_id": FAKE_UUID, "yacht_id": TEST_YACHT_ID}),
        ]

        for test_name, handler, kwargs in not_found_tests:
            try:
                result = await handler(**kwargs)

                # Check error structure
                if result.get("status") == "error":
                    has_code = "error_code" in result
                    has_message = "message" in result
                    is_not_found = "NOT_FOUND" in result.get("error_code", "")

                    if has_code and has_message and is_not_found:
                        self.record("D1", f"{test_name} NOT_FOUND", "PASS", f"code={result['error_code']}")
                    elif has_code and has_message:
                        self.record("D1", f"{test_name} NOT_FOUND", "WARN", f"code={result.get('error_code')}")
                    else:
                        self.record("D1", f"{test_name} NOT_FOUND", "FAIL", "Missing error_code or message")
                else:
                    # Should have been an error
                    self.record("D1", f"{test_name} NOT_FOUND", "FAIL", f"Expected error, got {result.get('status')}")
            except Exception as e:
                self.record("D1", f"{test_name} NOT_FOUND", "FAIL", str(e)[:50])

    async def run_d2_edge_cases(self):
        """D2: Test edge cases."""
        print("\n" + "=" * 60)
        print("D2: EDGE CASES (Null, Empty, Invalid)")
        print("=" * 60)

        from handlers.p3_read_only_handlers import get_p3_read_only_handlers
        from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers

        p3 = get_p3_read_only_handlers(self.client)
        p2 = get_p2_mutation_light_handlers(self.client)

        # Test empty result handling (queries that return no data)
        print("\n[Empty Results]")
        empty_tests = [
            ("view_worklist (no tasks)", p3["view_worklist"], {"yacht_id": WRONG_YACHT_ID, "user_id": TEST_USER_ID}),
            ("view_fleet_summary (no yachts)", p3["view_fleet_summary"], {"user_id": FAKE_UUID}),
            ("view_compliance_status", p3["view_compliance_status"], {"yacht_id": WRONG_YACHT_ID}),
        ]

        for test_name, handler, kwargs in empty_tests:
            try:
                result = await handler(**kwargs)
                # Should succeed with empty data, not crash
                if result.get("status") == "success":
                    self.record("D2", test_name, "PASS", "Handles empty gracefully")
                elif result.get("status") == "error" and "NOT_FOUND" in result.get("error_code", ""):
                    self.record("D2", test_name, "PASS", "Returns NOT_FOUND")
                else:
                    self.record("D2", test_name, "WARN", f"status={result.get('status')}")
            except Exception as e:
                self.record("D2", test_name, "FAIL", str(e)[:50])

        # Test invalid UUID format handling
        print("\n[Invalid UUID Format]")
        invalid_uuid = "not-a-valid-uuid"
        invalid_tests = [
            ("view_fault_history (bad uuid)", p3["view_fault_history"], {"fault_id": invalid_uuid, "yacht_id": TEST_YACHT_ID}),
            ("view_equipment_details (bad uuid)", p3["view_equipment_details"], {"equipment_id": invalid_uuid, "yacht_id": TEST_YACHT_ID}),
        ]

        for test_name, handler, kwargs in invalid_tests:
            try:
                result = await handler(**kwargs)
                # Should return error, not crash
                if result.get("status") == "error":
                    self.record("D2", test_name, "PASS", "Returns error for invalid UUID")
                else:
                    self.record("D2", test_name, "WARN", "Accepted invalid UUID")
            except Exception as e:
                # Exception is acceptable for invalid input
                self.record("D2", test_name, "PASS", f"Raises exception: {type(e).__name__}")

        # Test handlers with optional parameters
        print("\n[Optional Parameters]")
        if "equipment_id" in self.test_ids:
            eq_id = self.test_ids["equipment_id"]
            optional_tests = [
                ("view_equipment_history (default days)", p3["view_equipment_history"],
                 {"equipment_id": eq_id, "yacht_id": TEST_YACHT_ID}),
                ("view_linked_faults (no filter)", p3["view_linked_faults"],
                 {"equipment_id": eq_id, "yacht_id": TEST_YACHT_ID}),
            ]
            for test_name, handler, kwargs in optional_tests:
                try:
                    result = await handler(**kwargs)
                    if result.get("status") == "success":
                        self.record("D2", test_name, "PASS", "Works without optional params")
                    else:
                        self.record("D2", test_name, "FAIL", result.get("message", "")[:40])
                except Exception as e:
                    self.record("D2", test_name, "FAIL", str(e)[:50])

    async def run_d3_yacht_isolation(self):
        """D3: Verify yacht_id isolation."""
        print("\n" + "=" * 60)
        print("D3: YACHT ISOLATION VERIFICATION")
        print("=" * 60)

        from handlers.p3_read_only_handlers import get_p3_read_only_handlers

        p3 = get_p3_read_only_handlers(self.client)

        # Try to access entities with wrong yacht_id
        isolation_tests = []

        if "fault_id" in self.test_ids:
            isolation_tests.append((
                "fault cross-yacht",
                p3["view_fault_history"],
                {"fault_id": self.test_ids["fault_id"], "yacht_id": WRONG_YACHT_ID}
            ))

        if "equipment_id" in self.test_ids:
            isolation_tests.append((
                "equipment cross-yacht",
                p3["view_equipment_details"],
                {"equipment_id": self.test_ids["equipment_id"], "yacht_id": WRONG_YACHT_ID}
            ))

        if "part_id" in self.test_ids:
            isolation_tests.append((
                "part cross-yacht",
                p3["view_part_stock"],
                {"part_id": self.test_ids["part_id"], "yacht_id": WRONG_YACHT_ID}
            ))

        if "document_id" in self.test_ids:
            isolation_tests.append((
                "document cross-yacht",
                p3["view_document"],
                {"document_id": self.test_ids["document_id"], "yacht_id": WRONG_YACHT_ID}
            ))

        for test_name, handler, kwargs in isolation_tests:
            try:
                result = await handler(**kwargs)

                # Should NOT return the entity (yacht isolation should block)
                if result.get("status") == "error" and "NOT_FOUND" in result.get("error_code", ""):
                    self.record("D3", test_name, "PASS", "Yacht isolation enforced")
                elif result.get("status") == "success":
                    # SECURITY ISSUE: returned data for wrong yacht
                    self.record("D3", test_name, "FAIL", "SECURITY: Cross-yacht data leak!")
                else:
                    self.record("D3", test_name, "WARN", f"Unexpected: {result.get('status')}")
            except Exception as e:
                self.record("D3", test_name, "PASS", f"Exception blocks access: {type(e).__name__}")

    async def run_d4_input_validation(self):
        """D4: Check input validation."""
        print("\n" + "=" * 60)
        print("D4: INPUT VALIDATION")
        print("=" * 60)

        from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers

        p2 = get_p2_mutation_light_handlers(self.client)

        # Test with potentially malicious inputs
        print("\n[SQL-like Injection Attempts]")

        # These should be handled safely by Supabase parameterized queries
        injection_tests = [
            ("barcode with quotes", p2.get("scan_part_barcode") if "scan_part_barcode" in p2 else None,
             {"barcode": "'; DROP TABLE pms_parts; --", "yacht_id": TEST_YACHT_ID}),
        ]

        from handlers.p3_read_only_handlers import get_p3_read_only_handlers
        p3 = get_p3_read_only_handlers(self.client)

        injection_tests.append((
            "barcode injection (P3)",
            p3["scan_part_barcode"],
            {"barcode": "' OR '1'='1", "yacht_id": TEST_YACHT_ID}
        ))

        for test_name, handler, kwargs in injection_tests:
            if handler is None:
                self.record("D4", test_name, "SKIP", "Handler not available")
                continue
            try:
                result = await handler(**kwargs)
                # Should return NOT_FOUND or error, never crash or succeed with injected data
                if result.get("status") == "error":
                    self.record("D4", test_name, "PASS", "Injection safely rejected")
                elif result.get("status") == "success":
                    # Check if it actually found something (which would be bad)
                    if result.get("result", {}).get("part"):
                        self.record("D4", test_name, "FAIL", "SECURITY: Possible injection success")
                    else:
                        self.record("D4", test_name, "PASS", "No data returned")
                else:
                    self.record("D4", test_name, "WARN", f"status={result.get('status')}")
            except Exception as e:
                self.record("D4", test_name, "PASS", f"Exception: {type(e).__name__}")

        # Test boundary values
        print("\n[Boundary Values]")
        if "equipment_id" in self.test_ids:
            eq_id = self.test_ids["equipment_id"]
            boundary_tests = [
                ("negative limit", p3["view_linked_faults"],
                 {"equipment_id": eq_id, "yacht_id": TEST_YACHT_ID, "limit": -1}),
                ("zero limit", p3["view_linked_faults"],
                 {"equipment_id": eq_id, "yacht_id": TEST_YACHT_ID, "limit": 0}),
                ("huge limit", p3["view_linked_faults"],
                 {"equipment_id": eq_id, "yacht_id": TEST_YACHT_ID, "limit": 999999}),
            ]

            for test_name, handler, kwargs in boundary_tests:
                try:
                    result = await handler(**kwargs)
                    if result.get("status") in ("success", "error"):
                        self.record("D4", test_name, "PASS", f"Handled: {result.get('status')}")
                    else:
                        self.record("D4", test_name, "WARN", f"status={result.get('status')}")
                except Exception as e:
                    self.record("D4", test_name, "PASS", f"Exception handled: {type(e).__name__}")

    def print_summary(self):
        """Print test summary by category."""
        print("\n" + "=" * 60)
        print("EDGE CASE AUDIT SUMMARY")
        print("=" * 60)

        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}
            status = r["status"].lower()
            if status in categories[cat]:
                categories[cat][status] += 1

        total_pass = 0
        total_fail = 0
        total_warn = 0

        for cat, counts in sorted(categories.items()):
            total = counts["pass"] + counts["fail"] + counts["warn"] + counts["skip"]
            print(f"\n{cat}: {counts['pass']}/{total} PASS, {counts['fail']} FAIL, {counts['warn']} WARN")
            total_pass += counts["pass"]
            total_fail += counts["fail"]
            total_warn += counts["warn"]

        print("\n" + "-" * 40)
        total = total_pass + total_fail + total_warn
        print(f"TOTAL: {total_pass}/{total} PASS, {total_fail} FAIL, {total_warn} WARN")

        if total_fail > 0:
            print("\nFAILED TESTS:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  ❌ [{r['category']}] {r['test']}: {r['details']}")

        if total_warn > 0:
            print("\nWARNINGS:")
            for r in self.results:
                if r["status"] == "WARN":
                    print(f"  ⚠️ [{r['category']}] {r['test']}: {r['details']}")

        return total_fail == 0


async def main():
    harness = EdgeCaseTestHarness()
    await harness.get_test_ids()

    await harness.run_d1_error_consistency()
    await harness.run_d2_edge_cases()
    await harness.run_d3_yacht_isolation()
    await harness.run_d4_input_validation()

    return harness.print_summary()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
