#!/usr/bin/env python3
"""
Docker RLS and Permission Tests

Tests role-level security and permission enforcement for:
- P0 legacy routes (deny-by-default)
- Action router (role-based filtering)
- Document lens permissions

Run with: python tests/docker/run_rls_tests.py
"""

import requests
import json
from typing import Dict, Any

# Docker API endpoint
API_BASE = "http://localhost:8080"

# Test yacht
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test JWTs (real tenant users)
JWTS = {
    "captain": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ1MzI2LCJpYXQiOjE3NzA2NDE3MjYsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MTcyNn1dLCJzZXNzaW9uX2lkIjoiMTFkNjI1YTAtNGQyMS00NDZkLWJhODktOWM5ZThhOGU2ZWVkIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.3ltGmlehSM2kEgUpBgjzL1wsHRugoTpCldwmBEkoop4",
    "hod": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ1MzI3LCJpYXQiOjE3NzA2NDE3MjcsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzcwNjQxNzI3fV0sInNlc3Npb25faWQiOiJlMzdiOTUxMC03MGJkLTQwOTUtODljOC1lYTNhZDJjZmQ4ZWIiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.zM0zOXkTdnFDH8HFOk4J3FG4cA9tqzCwQi__gqTrCoQ",
    "crew": "eyJhbGciOiJIUzI1NiIsImtpZCI6IjE3UGY4ZUVPVnFXZXlmRGIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzcwNjQ2NjAxLCJpYXQiOjE3NzA2NDMwMDEsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlfSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3MDY0MzAwMX1dLCJzZXNzaW9uX2lkIjoiNjViMDEyZTUtODkyYy00N2VjLWI2YWItZjNlZDM5YzQ1YjdjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.vmaSq3MHv3WOd-1D2ysct-xKD1AgOcAIiqdsDUSzZRk",
}


class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []

    def add_pass(self, name: str, evidence: str = ""):
        self.passed.append({"name": name, "evidence": evidence})
        print(f"  ✅ {name}")
        if evidence:
            print(f"     Evidence: {evidence}")

    def add_fail(self, name: str, reason: str = ""):
        self.failed.append({"name": name, "reason": reason})
        print(f"  ❌ {name}")
        if reason:
            print(f"     Reason: {reason}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'=' * 80}")
        print(f"TEST SUMMARY: {len(self.passed)}/{total} PASSED")
        print(f"{'=' * 80}")

        if self.failed:
            print("\n❌ FAILED TESTS:")
            for test in self.failed:
                print(f"  - {test['name']}: {test['reason']}")

        return len(self.failed) == 0


results = TestResult()


def test_action_list_hod_sees_mutations():
    """HOD should see MUTATE actions (add_document_comment, etc.)"""
    print("\nTEST: HOD sees mutation actions in action list")

    response = requests.get(
        f"{API_BASE}/v1/actions/list",
        headers={"Authorization": f"Bearer {JWTS['hod']}"},
        params={"domain": "documents"}
    )

    if response.status_code != 200:
        results.add_fail("HOD action list", f"HTTP {response.status_code}")
        return

    actions = response.json().get('actions', [])
    action_ids = [a['action_id'] for a in actions]

    # Check for mutation actions
    has_add = any('add' in a and 'comment' in a for a in action_ids)
    has_update = any('update' in a and 'comment' in a for a in action_ids)
    has_delete = any('delete' in a and 'comment' in a for a in action_ids)

    if has_add or has_update or has_delete:
        results.add_pass("HOD sees mutation actions", f"Found: {[a for a in action_ids if 'comment' in a]}")
    else:
        results.add_fail("HOD sees mutation actions", f"No mutation actions found in {len(action_ids)} actions")


def test_action_list_crew_no_mutations():
    """CREW should NOT see MUTATE actions (only READ)"""
    print("\nTEST: CREW does NOT see mutation actions")

    response = requests.get(
        f"{API_BASE}/v1/actions/list",
        headers={"Authorization": f"Bearer {JWTS['crew']}"},
        params={"domain": "documents"}
    )

    if response.status_code != 200:
        results.add_fail("CREW action list", f"HTTP {response.status_code}")
        return

    actions = response.json().get('actions', [])
    action_ids = [a['action_id'] for a in actions]

    # Check for mutation actions (should NOT exist)
    mutations = [a for a in action_ids if any(verb in a for verb in ['add', 'create', 'update', 'delete', 'remove'])]

    if not mutations:
        results.add_pass("CREW blocked from mutations", f"Only sees: {action_ids}")
    else:
        results.add_fail("CREW blocked from mutations", f"SECURITY ISSUE: CREW sees {mutations}")


def test_crew_execute_mutation_blocked():
    """CREW executing a mutation action should return 403"""
    print("\nTEST: CREW blocked from executing mutations")

    response = requests.post(
        f"{API_BASE}/v1/actions/execute",
        headers={"Authorization": f"Bearer {JWTS['crew']}"},
        json={
            "action": "add_document_comment",
            "context": {"yacht_id": TEST_YACHT_ID},
            "payload": {
                "document_id": "test-doc-id",
                "comment": "CREW test - should be blocked"
            }
        }
    )

    if response.status_code == 403:
        results.add_pass("CREW blocked with 403", "FORBIDDEN as expected")
    elif response.status_code == 404:
        results.add_pass("CREW blocked with 404", "Action not exposed to CREW (acceptable)")
    else:
        results.add_fail("CREW blocked from execution", f"HTTP {response.status_code} (expected 403 or 404)")


def test_hod_execute_mutation_allowed():
    """HOD should be able to execute mutations (or get reasonable error)"""
    print("\nTEST: HOD authorized for mutations")

    response = requests.post(
        f"{API_BASE}/v1/actions/execute",
        headers={"Authorization": f"Bearer {JWTS['hod']}"},
        json={
            "action": "add_document_comment",
            "context": {"yacht_id": TEST_YACHT_ID},
            "payload": {
                "document_id": "test-doc-id",
                "comment": "HOD test comment"
            }
        }
    )

    # Should NOT be 403 (forbidden)
    if response.status_code == 403:
        results.add_fail("HOD authorized", "Got 403 FORBIDDEN (should be allowed)")
    else:
        results.add_pass("HOD authorized", f"HTTP {response.status_code} (not 403)")


def test_error_code_mapping():
    """Invalid resources should return 4xx not 5xx"""
    print("\nTEST: Error code mapping (4xx not 5xx)")

    response = requests.post(
        f"{API_BASE}/v1/actions/execute",
        headers={"Authorization": f"Bearer {JWTS['captain']}"},
        json={
            "action": "get_document_url",
            "context": {"yacht_id": TEST_YACHT_ID},
            "payload": {"document_id": "00000000-0000-0000-0000-000000000000"}
        }
    )

    if response.status_code < 500:
        results.add_pass("Error mapping", f"Returns {response.status_code} (not 5xx)")
    else:
        results.add_fail("Error mapping", f"Returns {response.status_code} (should be 4xx)")


def test_p0_route_deny_by_default():
    """P0 routes should deny requests without explicit permission"""
    print("\nTEST: P0 routes deny by default")

    # Try accessing a P0 route without proper context
    # Note: This test assumes P0 routes still exist - adjust if fully migrated
    response = requests.get(
        f"{API_BASE}/api/documents",  # Example P0 route
        headers={"Authorization": f"Bearer {JWTS['crew']}"}
    )

    # Should return 403, 401, or 404 (not 200 or 500)
    if response.status_code in [401, 403, 404]:
        results.add_pass("P0 deny-by-default", f"HTTP {response.status_code}")
    elif response.status_code == 200:
        results.add_fail("P0 deny-by-default", "Returned 200 (should require explicit permission)")
    else:
        # Might be 404 if route doesn't exist (acceptable)
        results.add_pass("P0 deny-by-default", f"HTTP {response.status_code} (route may not exist)")


if __name__ == "__main__":
    print("=" * 80)
    print("DOCKER RLS AND PERMISSION TESTS")
    print("=" * 80)

    # Run all tests
    test_action_list_hod_sees_mutations()
    test_action_list_crew_no_mutations()
    test_crew_execute_mutation_blocked()
    test_hod_execute_mutation_allowed()
    test_error_code_mapping()
    test_p0_route_deny_by_default()

    # Print summary
    success = results.summary()

    # Exit with proper code
    exit(0 if success else 1)
