#!/usr/bin/env python3
"""
Hours of Rest Lens v3 - API Integration Tests
==============================================

Tests for Hours of Rest (HOR) endpoints (Crew Compliance Domain):
- GET /v1/hours-of-rest - View HOR records (READ)
- POST /v1/hours-of-rest/upsert - Upsert HOR record (MUTATE)
- POST /v1/hours-of-rest/export - Export HOR data (READ)
- GET /v1/hours-of-rest/signoffs - List monthly sign-offs (READ)
- GET /v1/hours-of-rest/signoffs/details - Get sign-off details (READ)
- POST /v1/hours-of-rest/signoffs/create - Create sign-off (MUTATE)
- POST /v1/hours-of-rest/signoffs/sign - Sign sign-off (MUTATE)
- GET /v1/hours-of-rest/templates - List templates (READ)
- POST /v1/hours-of-rest/templates/create - Create template (MUTATE)
- POST /v1/hours-of-rest/templates/apply - Apply template (MUTATE)
- GET /v1/hours-of-rest/warnings - List warnings (READ)
- POST /v1/hours-of-rest/warnings/acknowledge - Acknowledge warning (MUTATE)
- POST /v1/hours-of-rest/warnings/dismiss - Dismiss warning (MUTATE, HOD+)

Evidence Location: tests/test_results/hours_of_rest_lens_v3/
"""

import sys
import os
import json
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta

# Load environment variables
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("TENANT_1_SUPABASE_URL", "").replace("/database", "")
SUPABASE_ANON_KEY = os.getenv("TENANT_1_SUPABASE_ANON_KEY", "")
YACHT_ID = os.getenv("YACHT_ID", "85fe1119-b04c-41ac-80f1-829d23322598")

# Test users
TEST_USERS = {
    "crew": {
        "email": "crew.test@alex-short.com",
        "password": "Password2!",
        "role": "crew",
    },
    "hod": {
        "email": "hod.test@alex-short.com",
        "password": "Password2!",
        "role": "chief_engineer",
    },
    "captain": {
        "email": "captain.test@alex-short.com",
        "password": "Password2!",
        "role": "captain",
    },
}

# Test output directory
TEST_OUTPUT_DIR = Path(__file__).parent / "test_results" / "hours_of_rest_lens_v3"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


class HoursOfRestLensTester:
    """API integration tester for Hours of Rest Lens v3."""

    def __init__(self):
        self.test_results = {
            "test_run_id": TEST_RUN_ID,
            "start_time": datetime.now().isoformat(),
            "scope": "Hours of Rest Lens v3 API Integration",
            "tests": [],
            "passed": 0,
            "failed": 0,
            "tokens": {},
            "errors": [],
        }
        self.tokens = {}
        self.client = httpx.AsyncClient(timeout=30.0)

    async def cleanup(self):
        """Clean up resources."""
        await self.client.aclose()

    def _record_test(self, test_name: str, passed: bool, details: Dict):
        """Record test result."""
        result = {
            "test_name": test_name,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.test_results["tests"].append(result)
        if passed:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1
        print(f"{'✅' if passed else '❌'} {test_name}")

    async def login_user(self, role: str) -> Optional[str]:
        """Login a test user and get JWT token."""
        user = TEST_USERS.get(role)
        if not user:
            print(f"Unknown role: {role}")
            return None

        try:
            auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
            response = await self.client.post(
                auth_url,
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "email": user["email"],
                    "password": user["password"],
                },
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                self.tokens[role] = token
                return token
            else:
                print(f"Login failed for {role}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Login error for {role}: {e}")
            return None

    async def test_get_hours_of_rest(self, role: str) -> bool:
        """Test GET /v1/hours-of-rest endpoint."""
        token = self.tokens.get(role) or await self.login_user(role)
        if not token:
            self._record_test(f"get_hours_of_rest_{role}", False, {"error": "No token"})
            return False

        try:
            response = await self.client.get(
                f"{API_BASE_URL}/v1/hours-of-rest",
                params={"yacht_id": YACHT_ID},
                headers={"Authorization": f"Bearer {token}"},
            )
            passed = response.status_code == 200
            self._record_test(
                f"get_hours_of_rest_{role}",
                passed,
                {"status_code": response.status_code, "response": response.json() if passed else response.text}
            )
            return passed
        except Exception as e:
            self._record_test(f"get_hours_of_rest_{role}", False, {"error": str(e)})
            return False

    async def test_upsert_hours_of_rest(self, role: str) -> bool:
        """Test POST /v1/hours-of-rest/upsert endpoint."""
        token = self.tokens.get(role) or await self.login_user(role)
        if not token:
            self._record_test(f"upsert_hours_of_rest_{role}", False, {"error": "No token"})
            return False

        try:
            today = date.today().isoformat()
            payload = {
                "yacht_id": YACHT_ID,
                "record_date": today,
                "rest_periods": [
                    {"start": "22:00", "end": "06:00", "hours": 8.0},
                    {"start": "13:00", "end": "15:00", "hours": 2.0}
                ],
            }
            response = await self.client.post(
                f"{API_BASE_URL}/v1/hours-of-rest/upsert",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            # Accept 200 (success) or 409 (duplicate) as valid
            passed = response.status_code in [200, 201, 409]
            self._record_test(
                f"upsert_hours_of_rest_{role}",
                passed,
                {"status_code": response.status_code, "response": response.json() if passed else response.text}
            )
            return passed
        except Exception as e:
            self._record_test(f"upsert_hours_of_rest_{role}", False, {"error": str(e)})
            return False

    async def test_list_signoffs(self, role: str) -> bool:
        """Test GET /v1/hours-of-rest/signoffs endpoint."""
        token = self.tokens.get(role) or await self.login_user(role)
        if not token:
            self._record_test(f"list_signoffs_{role}", False, {"error": "No token"})
            return False

        try:
            response = await self.client.get(
                f"{API_BASE_URL}/v1/hours-of-rest/signoffs",
                params={"yacht_id": YACHT_ID},
                headers={"Authorization": f"Bearer {token}"},
            )
            passed = response.status_code == 200
            self._record_test(
                f"list_signoffs_{role}",
                passed,
                {"status_code": response.status_code, "response": response.json() if passed else response.text}
            )
            return passed
        except Exception as e:
            self._record_test(f"list_signoffs_{role}", False, {"error": str(e)})
            return False

    async def test_list_templates(self, role: str) -> bool:
        """Test GET /v1/hours-of-rest/templates endpoint."""
        token = self.tokens.get(role) or await self.login_user(role)
        if not token:
            self._record_test(f"list_templates_{role}", False, {"error": "No token"})
            return False

        try:
            response = await self.client.get(
                f"{API_BASE_URL}/v1/hours-of-rest/templates",
                params={"yacht_id": YACHT_ID},
                headers={"Authorization": f"Bearer {token}"},
            )
            passed = response.status_code == 200
            self._record_test(
                f"list_templates_{role}",
                passed,
                {"status_code": response.status_code, "response": response.json() if passed else response.text}
            )
            return passed
        except Exception as e:
            self._record_test(f"list_templates_{role}", False, {"error": str(e)})
            return False

    async def test_list_warnings(self, role: str) -> bool:
        """Test GET /v1/hours-of-rest/warnings endpoint."""
        token = self.tokens.get(role) or await self.login_user(role)
        if not token:
            self._record_test(f"list_warnings_{role}", False, {"error": "No token"})
            return False

        try:
            response = await self.client.get(
                f"{API_BASE_URL}/v1/hours-of-rest/warnings",
                params={"yacht_id": YACHT_ID},
                headers={"Authorization": f"Bearer {token}"},
            )
            passed = response.status_code == 200
            self._record_test(
                f"list_warnings_{role}",
                passed,
                {"status_code": response.status_code, "response": response.json() if passed else response.text}
            )
            return passed
        except Exception as e:
            self._record_test(f"list_warnings_{role}", False, {"error": str(e)})
            return False

    async def test_dismiss_warning_role_gate(self) -> bool:
        """Test that crew cannot dismiss warnings (HOD+ only)."""
        token = self.tokens.get("crew") or await self.login_user("crew")
        if not token:
            self._record_test("dismiss_warning_crew_denied", False, {"error": "No token"})
            return False

        try:
            payload = {
                "yacht_id": YACHT_ID,
                "warning_id": "00000000-0000-0000-0000-000000000000",  # Fake ID
                "hod_justification": "Test justification",
                "dismissed_by_role": "hod",
            }
            response = await self.client.post(
                f"{API_BASE_URL}/v1/hours-of-rest/warnings/dismiss",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            # Crew should get 403 Forbidden
            passed = response.status_code == 403
            self._record_test(
                "dismiss_warning_crew_denied",
                passed,
                {"status_code": response.status_code, "expected": 403, "response": response.text[:500]}
            )
            return passed
        except Exception as e:
            self._record_test("dismiss_warning_crew_denied", False, {"error": str(e)})
            return False

    async def run_all_tests(self):
        """Run all HOR lens tests."""
        print(f"\n{'='*60}")
        print("Hours of Rest Lens v3 - API Integration Tests")
        print(f"{'='*60}\n")

        # Login all users first
        for role in TEST_USERS.keys():
            await self.login_user(role)

        # Test READ endpoints for all roles
        for role in ["crew", "hod", "captain"]:
            await self.test_get_hours_of_rest(role)
            await self.test_list_signoffs(role)
            await self.test_list_templates(role)
            await self.test_list_warnings(role)

        # Test MUTATE endpoints
        await self.test_upsert_hours_of_rest("crew")

        # Test role gates
        await self.test_dismiss_warning_role_gate()

        # Save results
        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["summary"] = {
            "total": self.test_results["passed"] + self.test_results["failed"],
            "passed": self.test_results["passed"],
            "failed": self.test_results["failed"],
            "pass_rate": f"{(self.test_results['passed'] / max(1, self.test_results['passed'] + self.test_results['failed'])) * 100:.1f}%"
        }

        # Write results to file
        output_file = TEST_OUTPUT_DIR / f"test_run_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"Results: {self.test_results['passed']} passed, {self.test_results['failed']} failed")
        print(f"Evidence saved to: {output_file}")
        print(f"{'='*60}\n")

        return self.test_results["failed"] == 0


async def main():
    """Main entry point."""
    tester = HoursOfRestLensTester()
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
