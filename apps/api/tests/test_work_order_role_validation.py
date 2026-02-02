#!/usr/bin/env python3
"""
Work Order Lens - Role Validation Logic Tests
============================================

Tests role validation logic at the action router level WITHOUT requiring JWT tokens.
This validates the core RBAC logic by simulating different user contexts.

Test Coverage:
1. Role validation logic (who can execute which actions)
2. Signature requirement enforcement
3. Required field validation
4. Role membership checks (is user in allowed_roles)

This test suite complements the JWT RLS tests by validating the RBAC
logic layer separately from the full HTTP authentication flow.
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Load environment variables from .env.tenant1
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from action_router.registry import get_action, get_actions_for_domain

# Test results directory
TEST_OUTPUT_DIR = Path(__file__).parent / "test_results" / "work_order_role_validation"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timestamp for this test run
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


class WorkOrderRoleValidationTests:
    """Role validation logic tests for Work Order Lens."""

    def __init__(self):
        self.test_results = {
            "test_run_id": TEST_RUN_ID,
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "passed": 0,
            "failed": 0,
        }

    def _record_test(self, test_name: str, passed: bool, details: Dict):
        """Record test result."""
        result = {
            "test_name": test_name,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }
        self.test_results["tests"].append(result)

        if passed:
            self.test_results["passed"] += 1
            print(f"  ✅ PASS: {test_name}")
        else:
            self.test_results["failed"] += 1
            print(f"  ❌ FAIL: {test_name}")

        return passed

    def _save_test_results(self, test_name: str, results: Any):
        """Save test results to file."""
        output_file = TEST_OUTPUT_DIR / f"{test_name}_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  💾 Results saved to: {output_file.name}")

    def _is_user_allowed_for_action(self, user_role: str, action_name: str) -> bool:
        """Check if user role is allowed for action."""
        try:
            action_id = f"work_orders.{action_name}"
            action_def = get_action(action_id)
            if not action_def:
                return False

            allowed_roles = action_def.allowed_roles or []
            return user_role in allowed_roles
        except Exception as e:
            return False

    def _requires_signature(self, action_name: str) -> bool:
        """Check if action requires signature."""
        try:
            action_id = f"work_orders.{action_name}"
            action_def = get_action(action_id)
            if not action_def:
                return False

            required_fields = action_def.required_fields or []
            return "signature" in required_fields
        except Exception as e:
            return False

    # =========================================================================
    # TEST CATEGORY 1: ROLE MEMBERSHIP
    # =========================================================================

    async def test_action_registry_completeness(self):
        """Test 1.1: Verify all work order actions are registered"""
        print("=" * 80)
        print("TEST 1.1: Action Registry Completeness")
        print("=" * 80)

        work_order_actions = get_actions_for_domain("work_orders")

        print(f"  Found {len(work_order_actions)} work order actions")
        print("")

        expected_actions = [
            "list_work_orders",
            "search_work_orders",
            "create_work_order",
            "update_work_order",
            "complete_work_order",
            "reassign_work_order",
            "add_work_order_note",
            "list_work_order_notes",
            "add_work_order_part",
            "update_work_order_part",
            "remove_work_order_part",
            "list_work_order_parts",
            "archive_work_order",
            "unarchive_work_order",
        ]

        missing_actions = []
        for expected in expected_actions:
            expected_id = f"work_orders.{expected}"
            found = any(action["action_id"] == expected_id for action in work_order_actions)
            if found:
                print(f"    ✅ {expected}")
            else:
                print(f"    ❌ {expected} - MISSING")
                missing_actions.append(expected)

        print("")

        passed = len(missing_actions) == 0

        self._record_test("action_registry_completeness", passed, {
            "expected_actions": len(expected_actions),
            "found_actions": len(work_order_actions),
            "missing_actions": missing_actions
        })

        return passed

    async def test_crew_role_restrictions(self):
        """Test 1.2: CREW should NOT be in allowed_roles for create/update/reassign/archive"""
        print("=" * 80)
        print("TEST 1.2: CREW Role Restrictions")
        print("=" * 80)

        restricted_actions = [
            "create_work_order",
            "update_work_order",
            "reassign_work_order",
            "archive_work_order",
            "add_work_order_note",
            "add_work_order_part",
        ]

        crew_roles = ["crew", "deckhand", "steward", "cook"]

        failures = []

        for action_name in restricted_actions:
            print(f"  Testing: {action_name}")
            for crew_role in crew_roles:
                allowed = self._is_user_allowed_for_action(crew_role, action_name)
                if allowed:
                    print(f"    ❌ {crew_role} - INCORRECTLY ALLOWED")
                    failures.append(f"{crew_role} allowed for {action_name}")
                else:
                    print(f"    ✅ {crew_role} - correctly denied")

        print("")

        passed = len(failures) == 0

        self._record_test("crew_role_restrictions", passed, {
            "failures": failures
        })

        return passed

    async def test_hod_role_permissions(self):
        """Test 1.3: HoD roles should be ALLOWED for create/update (but not archive)"""
        print("=" * 80)
        print("TEST 1.3: HoD Role Permissions")
        print("=" * 80)

        hod_roles = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser"]

        allowed_actions = [
            "create_work_order",
            "update_work_order",
            "reassign_work_order",  # with signature
            "add_work_order_note",
            "add_work_order_part",
        ]

        denied_actions = [
            "archive_work_order",  # captain/manager only
        ]

        failures = []

        # Test allowed actions
        print("  Testing ALLOWED actions for HoD:")
        for action_name in allowed_actions:
            print(f"    {action_name}:")
            for hod_role in hod_roles:
                allowed = self._is_user_allowed_for_action(hod_role, action_name)
                if not allowed:
                    print(f"      ❌ {hod_role} - INCORRECTLY DENIED")
                    failures.append(f"{hod_role} denied for {action_name}")
                else:
                    print(f"      ✅ {hod_role} - correctly allowed")

        print("")

        # Test denied actions
        print("  Testing DENIED actions for HoD:")
        for action_name in denied_actions:
            print(f"    {action_name}:")
            for hod_role in hod_roles:
                allowed = self._is_user_allowed_for_action(hod_role, action_name)
                if allowed:
                    print(f"      ❌ {hod_role} - INCORRECTLY ALLOWED")
                    failures.append(f"{hod_role} allowed for {action_name}")
                else:
                    print(f"      ✅ {hod_role} - correctly denied")

        print("")

        passed = len(failures) == 0

        self._record_test("hod_role_permissions", passed, {
            "failures": failures
        })

        return passed

    async def test_captain_role_permissions(self):
        """Test 1.4: Captain/Manager should be ALLOWED for ALL actions"""
        print("=" * 80)
        print("TEST 1.4: Captain/Manager Role Permissions")
        print("=" * 80)

        captain_roles = ["captain", "manager"]

        all_actions = [
            "create_work_order",
            "update_work_order",
            "reassign_work_order",
            "archive_work_order",  # should be allowed
            "add_work_order_note",
            "add_work_order_part",
        ]

        failures = []

        for action_name in all_actions:
            print(f"  Testing: {action_name}")
            for captain_role in captain_roles:
                allowed = self._is_user_allowed_for_action(captain_role, action_name)
                if not allowed:
                    print(f"    ❌ {captain_role} - INCORRECTLY DENIED")
                    failures.append(f"{captain_role} denied for {action_name}")
                else:
                    print(f"    ✅ {captain_role} - correctly allowed")

        print("")

        passed = len(failures) == 0

        self._record_test("captain_role_permissions", passed, {
            "failures": failures
        })

        return passed

    # =========================================================================
    # TEST CATEGORY 2: SIGNATURE REQUIREMENTS
    # =========================================================================

    async def test_signature_requirements(self):
        """Test 2.1: Verify which actions require signature"""
        print("=" * 80)
        print("TEST 2.1: Signature Requirements")
        print("=" * 80)

        expected_signed_actions = [
            "reassign_work_order",
            "archive_work_order",
        ]

        expected_unsigned_actions = [
            "create_work_order",
            "update_work_order",
            "complete_work_order",
            "add_work_order_note",
            "add_work_order_part",
        ]

        failures = []

        # Test actions that SHOULD require signature
        print("  Actions that SHOULD require signature:")
        for action_name in expected_signed_actions:
            requires_sig = self._requires_signature(action_name)
            if requires_sig:
                print(f"    ✅ {action_name} - correctly requires signature")
            else:
                print(f"    ❌ {action_name} - MISSING signature requirement")
                failures.append(f"{action_name} should require signature")

        print("")

        # Test actions that should NOT require signature
        print("  Actions that should NOT require signature:")
        for action_name in expected_unsigned_actions:
            requires_sig = self._requires_signature(action_name)
            if not requires_sig:
                print(f"    ✅ {action_name} - correctly unsigned")
            else:
                print(f"    ❌ {action_name} - INCORRECTLY requires signature")
                failures.append(f"{action_name} should not require signature")

        print("")

        passed = len(failures) == 0

        self._record_test("signature_requirements", passed, {
            "failures": failures
        })

        return passed

    # =========================================================================
    # TEST CATEGORY 3: REQUIRED FIELDS
    # =========================================================================

    async def test_required_fields(self):
        """Test 3.1: Verify required fields for each action"""
        print("=" * 80)
        print("TEST 3.1: Required Fields Validation")
        print("=" * 80)

        expected_required_fields = {
            "create_work_order": ["title"],  # type and priority have defaults
            "update_work_order": ["work_order_id"],
            "complete_work_order": ["work_order_id"],
            "reassign_work_order": ["work_order_id", "assigned_to", "signature"],
            "archive_work_order": ["work_order_id", "deletion_reason", "signature"],
            "add_work_order_note": ["work_order_id", "note_text"],
            "add_work_order_part": ["work_order_id", "part_id", "quantity"],
        }

        failures = []

        for action_name, expected_fields in expected_required_fields.items():
            try:
                action_id = f"work_orders.{action_name}"
                action_def = get_action(action_id)
                if not action_def:
                    print(f"  ❌ {action_name} - action not found")
                    failures.append(f"{action_name} not found")
                    continue

                actual_required = action_def.required_fields or []
            except Exception as e:
                print(f"  ❌ {action_name} - error: {e}")
                failures.append(f"{action_name} error")
                continue

            print(f"  {action_name}:")
            print(f"    Expected: {expected_fields}")
            print(f"    Actual: {actual_required}")

            # Check if all expected fields are present
            missing = [f for f in expected_fields if f not in actual_required]
            extra = [f for f in actual_required if f not in expected_fields]

            if missing:
                print(f"    ❌ Missing required fields: {missing}")
                failures.append(f"{action_name} missing: {missing}")

            if extra:
                print(f"    ⚠️  Extra required fields: {extra}")
                # Not a failure, just informational

            if not missing and not extra:
                print(f"    ✅ Required fields correct")

            print("")

        passed = len(failures) == 0

        self._record_test("required_fields", passed, {
            "failures": failures
        })

        return passed

    # =========================================================================
    # TEST EXECUTION
    # =========================================================================

    async def run_all_tests(self):
        """Run all role validation tests."""
        print("=" * 80)
        print("WORK ORDER LENS - ROLE VALIDATION LOGIC TESTS")
        print("=" * 80)
        print(f"Test Run ID: {TEST_RUN_ID}")
        print(f"Output Directory: {TEST_OUTPUT_DIR}")
        print("")

        print("=" * 80)
        print("RUNNING ALL TESTS")
        print("=" * 80)
        print("")

        # Category 1: Role Membership
        await self.test_action_registry_completeness()
        await self.test_crew_role_restrictions()
        await self.test_hod_role_permissions()
        await self.test_captain_role_permissions()

        # Category 2: Signature Requirements
        await self.test_signature_requirements()

        # Category 3: Required Fields
        await self.test_required_fields()

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary."""
        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total * 100) if total > 0 else 0

        for test in self.test_results["tests"]:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            print(f"{status}: {test['test_name']}")

        print("")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.test_results['passed']}")
        print(f"Failed: {self.test_results['failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print("")

        # Save final summary
        self.test_results["end_time"] = datetime.now().isoformat()
        summary_file = TEST_OUTPUT_DIR / f"summary_{TEST_RUN_ID}.json"
        with open(summary_file, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print(f"💾 Summary saved to: {summary_file}")
        print("")

        # Verdict
        if self.test_results["failed"] == 0 and self.test_results["passed"] > 0:
            print("=" * 80)
            print("✅ VERDICT: ALL ROLE VALIDATION TESTS PASSED")
            print("=" * 80)
        else:
            print("=" * 80)
            print("❌ VERDICT: SOME TESTS FAILED")
            print("=" * 80)

        print("")


async def main():
    """Main test execution."""
    tests = WorkOrderRoleValidationTests()
    await tests.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
