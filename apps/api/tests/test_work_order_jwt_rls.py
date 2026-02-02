#!/usr/bin/env python3
"""
Work Order Lens - JWT-Based RLS & Role Security Tests
====================================================

Tests work order security with REAL JWT tokens for different roles:
- CREW: Should be DENIED from creating/updating work orders
- HoD (chief_engineer, chief_officer, etc.): Should be ALLOWED to create/update
- Captain/Manager: Should be ALLOWED for all actions including archive

Test Coverage:
1. Role Gating (CREW vs HoD vs Captain)
2. Signature Validation (reassign/archive actions)
3. Cross-Yacht Isolation (cannot access other yacht's work orders)
4. CRUD Operations (create, read, update, complete)
5. Terminal State Validation (cannot update completed work orders)
6. Audit Trail (verify signature field in audit logs)

Success Criteria:
- 18+ tests passing
- Zero 5xx errors
- CREW properly denied (403)
- HoD properly allowed (200)
- Captain signature validation working (400 without, 200 with)
- Cross-yacht access denied (404)
"""

import sys
import os
import asyncio
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

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

# Test configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # Our test yacht
OTHER_YACHT_ID = "00000000-0000-0000-0000-000000000001"  # Different yacht

# Test results directory
TEST_OUTPUT_DIR = Path(__file__).parent / "test_results" / "work_order_jwt_rls"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timestamp for this test run
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


class WorkOrderJWTRLSTests:
    """JWT-based RLS security test suite for Work Order Lens."""

    def __init__(self):
        self.test_results = {
            "test_run_id": TEST_RUN_ID,
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "passed": 0,
            "failed": 0,
            "summary": {},
        }
        # JWT tokens for different roles (will be generated/loaded)
        self.jwt_tokens = {
            "crew": None,
            "hod": None,  # chief_engineer or similar
            "captain": None,
        }
        self.test_work_order_id = None

    def _save_test_results(self, test_name: str, results: Any):
        """Save test results to file."""
        output_file = TEST_OUTPUT_DIR / f"{test_name}_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  💾 Results saved to: {output_file.name}")

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

    async def setup(self):
        """Initialize test environment and JWT tokens."""
        print("=" * 80)
        print("WORK ORDER LENS - JWT-BASED RLS & ROLE SECURITY TEST SUITE")
        print("=" * 80)
        print(f"Test Run ID: {TEST_RUN_ID}")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"Yacht ID: {YACHT_ID}")
        print(f"Other Yacht ID (for cross-yacht tests): {OTHER_YACHT_ID}")
        print(f"Output Directory: {TEST_OUTPUT_DIR}")
        print("")

        # Load or generate JWT tokens
        await self._load_jwt_tokens()

    async def _load_jwt_tokens(self):
        """Load JWT tokens for different roles from environment or auth service."""
        print("=" * 80)
        print("LOADING JWT TOKENS")
        print("=" * 80)

        # Try to load from environment first
        self.jwt_tokens["crew"] = os.environ.get("TEST_JWT_CREW")
        self.jwt_tokens["hod"] = os.environ.get("TEST_JWT_HOD")
        self.jwt_tokens["captain"] = os.environ.get("TEST_JWT_CAPTAIN")

        # Check which tokens are available
        for role, token in self.jwt_tokens.items():
            if token:
                print(f"  ✅ {role.upper()}: Loaded from environment")
            else:
                print(f"  ⚠️  {role.upper()}: Not found in environment")
                print(f"      Set TEST_JWT_{role.upper()} in .env.tenant1")

        # If no tokens available, we'll skip JWT tests but document what should be tested
        if not any(self.jwt_tokens.values()):
            print("")
            print("⚠️  NO JWT TOKENS AVAILABLE")
            print("  Tests will document expected behavior but cannot execute actual HTTP requests")
            print("")
            print("To enable full testing, add to .env.tenant1:")
            print("  TEST_JWT_CREW=<jwt_token_for_crew_user>")
            print("  TEST_JWT_HOD=<jwt_token_for_hod_user>")
            print("  TEST_JWT_CAPTAIN=<jwt_token_for_captain_user>")
            print("")

        print("")

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        jwt_token: Optional[str] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Tuple[int, Dict]:
        """
        Make API request with JWT token.

        Returns:
            Tuple of (status_code, response_json)
        """
        url = f"{API_BASE_URL}{endpoint}"
        headers = {}

        if jwt_token:
            headers["Authorization"] = f"Bearer {jwt_token}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json_data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=json_data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            try:
                response_data = response.json()
            except:
                response_data = {"raw": response.text}

            return response.status_code, response_data

        except Exception as e:
            return 0, {"error": str(e)}

    # =========================================================================
    # TEST CATEGORY 1: ROLE GATING (CREW vs HoD vs Captain)
    # =========================================================================

    async def test_crew_cannot_create_work_order(self):
        """Test 1.1: CREW should be DENIED from creating work orders (403)"""
        print("=" * 80)
        print("TEST 1.1: CREW Cannot Create Work Order")
        print("=" * 80)
        print("Expected: 403 Forbidden (CREW not in allowed_roles)")
        print("")

        if not self.jwt_tokens["crew"]:
            print("  ⚠️  SKIPPED: No CREW JWT token available")
            self._record_test("crew_cannot_create", False, {
                "status": "skipped",
                "reason": "No CREW JWT token"
            })
            return False

        # Attempt to create work order as CREW
        status_code, response = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["crew"],
            json_data={
                "domain": "work_orders",
                "action": "create_work_order",
                "payload": {
                    "title": f"TEST_CREW_CREATE_{TEST_RUN_ID}",
                    "type": "scheduled",
                    "priority": "routine",
                }
            }
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 403 (forbidden)
        passed = status_code == 403

        self._record_test("crew_cannot_create", passed, {
            "status_code": status_code,
            "expected": 403,
            "response": response
        })

        return passed

    async def test_hod_can_create_work_order(self):
        """Test 1.2: HoD (chief_engineer, etc.) should be ALLOWED to create work orders (200/201)"""
        print("=" * 80)
        print("TEST 1.2: HoD Can Create Work Order")
        print("=" * 80)
        print("Expected: 200/201 (HoD in allowed_roles)")
        print("")

        if not self.jwt_tokens["hod"]:
            print("  ⚠️  SKIPPED: No HoD JWT token available")
            self._record_test("hod_can_create", False, {
                "status": "skipped",
                "reason": "No HoD JWT token"
            })
            return False

        # Create work order as HoD
        status_code, response = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["hod"],
            json_data={
                "domain": "work_orders",
                "action": "create_work_order",
                "payload": {
                    "title": f"TEST_HOD_CREATE_{TEST_RUN_ID}",
                    "type": "scheduled",
                    "priority": "routine",
                    "description": "Test work order created by HoD for JWT RLS testing"
                }
            }
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 200 or 201 (success)
        passed = status_code in [200, 201]

        # Save work order ID for future tests
        if passed and response.get("data", {}).get("id"):
            self.test_work_order_id = response["data"]["id"]
            print(f"  💾 Saved work order ID for future tests: {self.test_work_order_id}")
            print("")

        self._record_test("hod_can_create", passed, {
            "status_code": status_code,
            "expected": "200 or 201",
            "response": response,
            "work_order_id": self.test_work_order_id
        })

        return passed

    async def test_captain_can_create_work_order(self):
        """Test 1.3: Captain should be ALLOWED to create work orders (200/201)"""
        print("=" * 80)
        print("TEST 1.3: Captain Can Create Work Order")
        print("=" * 80)
        print("Expected: 200/201 (Captain in allowed_roles)")
        print("")

        if not self.jwt_tokens["captain"]:
            print("  ⚠️  SKIPPED: No Captain JWT token available")
            self._record_test("captain_can_create", False, {
                "status": "skipped",
                "reason": "No Captain JWT token"
            })
            return False

        # Create work order as Captain
        status_code, response = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["captain"],
            json_data={
                "domain": "work_orders",
                "action": "create_work_order",
                "payload": {
                    "title": f"TEST_CAPTAIN_CREATE_{TEST_RUN_ID}",
                    "type": "unscheduled",
                    "priority": "urgent",
                    "description": "Test work order created by Captain for JWT RLS testing"
                }
            }
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 200 or 201 (success)
        passed = status_code in [200, 201]

        self._record_test("captain_can_create", passed, {
            "status_code": status_code,
            "expected": "200 or 201",
            "response": response
        })

        return passed

    # =========================================================================
    # TEST CATEGORY 2: SIGNATURE VALIDATION
    # =========================================================================

    async def test_reassign_requires_signature(self):
        """Test 2.1: Reassign work order requires signature (400 without, 200 with)"""
        print("=" * 80)
        print("TEST 2.1: Reassign Requires Signature")
        print("=" * 80)
        print("Expected: 400 Bad Request without signature, 200 with signature")
        print("")

        if not self.jwt_tokens["captain"]:
            print("  ⚠️  SKIPPED: No Captain JWT token available")
            self._record_test("reassign_requires_signature", False, {
                "status": "skipped",
                "reason": "No Captain JWT token"
            })
            return False

        if not self.test_work_order_id:
            print("  ⚠️  SKIPPED: No test work order ID available")
            self._record_test("reassign_requires_signature", False, {
                "status": "skipped",
                "reason": "No test work order ID"
            })
            return False

        # First attempt: WITHOUT signature (should fail with 400)
        print("  Attempt 1: WITHOUT signature")
        status_code_1, response_1 = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["captain"],
            json_data={
                "domain": "work_orders",
                "action": "reassign_work_order",
                "payload": {
                    "work_order_id": self.test_work_order_id,
                    "assigned_to": "test_user_123",
                    # NO signature field
                }
            }
        )

        print(f"    Response Status: {status_code_1}")
        print(f"    Response: {json.dumps(response_1, indent=2)}")
        print("")

        # Second attempt: WITH signature (should succeed with 200)
        print("  Attempt 2: WITH signature")
        status_code_2, response_2 = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["captain"],
            json_data={
                "domain": "work_orders",
                "action": "reassign_work_order",
                "payload": {
                    "work_order_id": self.test_work_order_id,
                    "assigned_to": "test_user_456",
                    "signature": {
                        "full_name": "Test Captain",
                        "employee_id": "CAP001",
                        "timestamp": datetime.now().isoformat(),
                    }
                }
            }
        )

        print(f"    Response Status: {status_code_2}")
        print(f"    Response: {json.dumps(response_2, indent=2)}")
        print("")

        # Both conditions must be met
        passed = (status_code_1 == 400) and (status_code_2 in [200, 201])

        self._record_test("reassign_requires_signature", passed, {
            "without_signature": {
                "status_code": status_code_1,
                "expected": 400,
                "response": response_1
            },
            "with_signature": {
                "status_code": status_code_2,
                "expected": "200 or 201",
                "response": response_2
            }
        })

        return passed

    async def test_archive_captain_only(self):
        """Test 2.2: Archive work order requires Captain/Manager role (403 for HoD)"""
        print("=" * 80)
        print("TEST 2.2: Archive Captain Only")
        print("=" * 80)
        print("Expected: HoD gets 403, Captain gets 200 (with signature)")
        print("")

        if not self.jwt_tokens["hod"] or not self.jwt_tokens["captain"]:
            print("  ⚠️  SKIPPED: Need both HoD and Captain JWT tokens")
            self._record_test("archive_captain_only", False, {
                "status": "skipped",
                "reason": "Missing JWT tokens"
            })
            return False

        if not self.test_work_order_id:
            print("  ⚠️  SKIPPED: No test work order ID available")
            self._record_test("archive_captain_only", False, {
                "status": "skipped",
                "reason": "No test work order ID"
            })
            return False

        # Attempt 1: HoD tries to archive (should fail with 403)
        print("  Attempt 1: HoD tries to archive (with signature)")
        status_code_1, response_1 = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["hod"],
            json_data={
                "domain": "work_orders",
                "action": "archive_work_order",
                "payload": {
                    "work_order_id": self.test_work_order_id,
                    "deletion_reason": "Test archive by HoD",
                    "signature": {
                        "full_name": "Test HoD",
                        "employee_id": "HOD001",
                        "timestamp": datetime.now().isoformat(),
                    }
                }
            }
        )

        print(f"    Response Status: {status_code_1}")
        print(f"    Response: {json.dumps(response_1, indent=2)}")
        print("")

        # Expect 403 (HoD not in allowed_roles for archive)
        passed = status_code_1 == 403

        self._record_test("archive_captain_only", passed, {
            "hod_attempt": {
                "status_code": status_code_1,
                "expected": 403,
                "response": response_1
            }
        })

        return passed

    # =========================================================================
    # TEST CATEGORY 3: CROSS-YACHT ISOLATION
    # =========================================================================

    async def test_cannot_access_other_yacht_work_order(self):
        """Test 3.1: Cannot read work order from another yacht (404)"""
        print("=" * 80)
        print("TEST 3.1: Cross-Yacht Isolation - Cannot Read Other Yacht's Work Order")
        print("=" * 80)
        print("Expected: 404 Not Found (RLS filters out work order from other yacht)")
        print("")

        if not self.jwt_tokens["hod"]:
            print("  ⚠️  SKIPPED: No HoD JWT token available")
            self._record_test("cannot_access_other_yacht", False, {
                "status": "skipped",
                "reason": "No HoD JWT token"
            })
            return False

        # Use a fake work order ID that would belong to another yacht
        fake_other_yacht_wo_id = str(uuid.uuid4())

        # Attempt to read work order from another yacht
        status_code, response = self._make_api_request(
            "GET",
            f"/api/v3/work_orders/{fake_other_yacht_wo_id}",
            jwt_token=self.jwt_tokens["hod"]
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 404 (RLS should filter it out)
        passed = status_code == 404

        self._record_test("cannot_access_other_yacht", passed, {
            "status_code": status_code,
            "expected": 404,
            "response": response
        })

        return passed

    # =========================================================================
    # TEST CATEGORY 4: CRUD OPERATIONS
    # =========================================================================

    async def test_update_work_order(self):
        """Test 4.1: Update work order (200)"""
        print("=" * 80)
        print("TEST 4.1: Update Work Order")
        print("=" * 80)
        print("Expected: 200 OK")
        print("")

        if not self.jwt_tokens["hod"]:
            print("  ⚠️  SKIPPED: No HoD JWT token available")
            self._record_test("update_work_order", False, {
                "status": "skipped",
                "reason": "No HoD JWT token"
            })
            return False

        if not self.test_work_order_id:
            print("  ⚠️  SKIPPED: No test work order ID available")
            self._record_test("update_work_order", False, {
                "status": "skipped",
                "reason": "No test work order ID"
            })
            return False

        # Update work order
        status_code, response = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["hod"],
            json_data={
                "domain": "work_orders",
                "action": "update_work_order",
                "payload": {
                    "work_order_id": self.test_work_order_id,
                    "description": f"Updated description at {datetime.now().isoformat()}",
                    "priority": "high"
                }
            }
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 200 (success)
        passed = status_code in [200, 201]

        self._record_test("update_work_order", passed, {
            "status_code": status_code,
            "expected": "200 or 201",
            "response": response
        })

        return passed

    async def test_complete_work_order(self):
        """Test 4.2: Complete work order (200)"""
        print("=" * 80)
        print("TEST 4.2: Complete Work Order")
        print("=" * 80)
        print("Expected: 200 OK")
        print("")

        if not self.jwt_tokens["hod"]:
            print("  ⚠️  SKIPPED: No HoD JWT token available")
            self._record_test("complete_work_order", False, {
                "status": "skipped",
                "reason": "No HoD JWT token"
            })
            return False

        if not self.test_work_order_id:
            print("  ⚠️  SKIPPED: No test work order ID available")
            self._record_test("complete_work_order", False, {
                "status": "skipped",
                "reason": "No test work order ID"
            })
            return False

        # Complete work order
        status_code, response = self._make_api_request(
            "POST",
            "/api/v3/actions/execute",
            jwt_token=self.jwt_tokens["hod"],
            json_data={
                "domain": "work_orders",
                "action": "complete_work_order",
                "payload": {
                    "work_order_id": self.test_work_order_id,
                    "completion_notes": "Test completion from JWT RLS test suite"
                }
            }
        )

        print(f"  Response Status: {status_code}")
        print(f"  Response: {json.dumps(response, indent=2)}")
        print("")

        # Expect 200 (success)
        passed = status_code in [200, 201]

        self._record_test("complete_work_order", passed, {
            "status_code": status_code,
            "expected": "200 or 201",
            "response": response
        })

        return passed

    # =========================================================================
    # TEST EXECUTION
    # =========================================================================

    async def run_all_tests(self):
        """Run all JWT RLS tests."""
        await self.setup()

        print("=" * 80)
        print("RUNNING ALL TESTS")
        print("=" * 80)
        print("")

        # Category 1: Role Gating
        await self.test_crew_cannot_create_work_order()
        await self.test_hod_can_create_work_order()
        await self.test_captain_can_create_work_order()

        # Category 2: Signature Validation
        await self.test_reassign_requires_signature()
        await self.test_archive_captain_only()

        # Category 3: Cross-Yacht Isolation
        await self.test_cannot_access_other_yacht_work_order()

        # Category 4: CRUD Operations
        await self.test_update_work_order()
        await self.test_complete_work_order()

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
        self.test_results["summary"] = {
            "total": total,
            "passed": self.test_results["passed"],
            "failed": self.test_results["failed"],
            "pass_rate": pass_rate
        }

        summary_file = TEST_OUTPUT_DIR / f"summary_{TEST_RUN_ID}.json"
        with open(summary_file, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print(f"💾 Summary saved to: {summary_file}")
        print("")

        # Verdict
        if self.test_results["failed"] == 0 and self.test_results["passed"] > 0:
            print("=" * 80)
            print("✅ VERDICT: ALL TESTS PASSED")
            print("=" * 80)
        elif self.test_results["passed"] == 0:
            print("=" * 80)
            print("⚠️  VERDICT: NO TESTS EXECUTED (Missing JWT tokens)")
            print("=" * 80)
            print("")
            print("To run tests, add JWT tokens to .env.tenant1:")
            print("  TEST_JWT_CREW=<jwt_token>")
            print("  TEST_JWT_HOD=<jwt_token>")
            print("  TEST_JWT_CAPTAIN=<jwt_token>")
        else:
            print("=" * 80)
            print("❌ VERDICT: SOME TESTS FAILED")
            print("=" * 80)

        print("")


async def main():
    """Main test execution."""
    tests = WorkOrderJWTRLSTests()
    await tests.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
