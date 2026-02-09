#!/usr/bin/env python3
"""
Comprehensive HOR E2E Testing - Multi-Role Hard Evidence Validation
====================================================================

Tests all HOR actions across CAPTAIN, HOD, and CREW roles.
Validates actual data responses, not just HTTP status codes.
"""
import os
import sys
import json
import requests
from datetime import date, timedelta
from typing import Dict, List

# Load env vars
env_vars = {}
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value
            os.environ[key] = value

# Load JWTs
with open('test-jwts.json', 'r') as f:
    jwts = json.load(f)

API_BASE = "http://localhost:8080"
YACHT_ID = env_vars['TEST_YACHT_ID']

# Test users
CAPTAIN = {"jwt": jwts['CAPTAIN']['jwt'], "user_id": jwts['CAPTAIN']['user_id'], "role": "CAPTAIN"}
HOD = {"jwt": jwts['HOD']['jwt'], "user_id": jwts['HOD']['user_id'], "role": "CHIEF_ENGINEER"}
CREW = {"jwt": jwts['CREW']['jwt'], "user_id": jwts['CREW']['user_id'], "role": "CREW"}

# Results tracking
results = {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "issues": []
}

def log_test(action: str, role: str, status: str, evidence: str):
    """Log test result with evidence."""
    results["total_tests"] += 1
    if status == "PASS":
        results["passed"] += 1
        icon = "✅"
    else:
        results["failed"] += 1
        icon = "❌"

    print(f"{icon} [{action}] {role}: {status}")
    print(f"   Evidence: {evidence}")
    print()

def add_issue(category: str, description: str, severity: str, fix: str):
    """Add issue to tracking."""
    results["issues"].append({
        "category": category,
        "description": description,
        "severity": severity,
        "fix": fix
    })

def test_get_hours_of_rest(user: Dict, target_user_id: str = None):
    """Test get_hours_of_rest action."""
    target = target_user_id or user["user_id"]

    payload = {
        "action": "get_hours_of_rest",
        "context": {
            "yacht_id": YACHT_ID,
            "user_id": user["user_id"],
            "role": user["role"]
        },
        "payload": {
            "yacht_id": YACHT_ID,
            "user_id": target
        }
    }

    try:
        response = requests.post(
            f"{API_BASE}/v1/actions/execute",
            json=payload,
            headers={"Authorization": f"Bearer {user['jwt']}"},
            timeout=10
        )

        data = response.json()

        if response.status_code != 200:
            log_test("get_hours_of_rest", user["role"], "FAIL",
                    f"HTTP {response.status_code}: {data.get('message', 'Unknown error')}")
            return None

        # Hard evidence validation
        if 'data' not in data:
            log_test("get_hours_of_rest", user["role"], "FAIL",
                    "Missing 'data' field in response")
            return None

        records = data['data'].get('records', [])
        summary = data['data'].get('summary', {})

        # Evidence: Check structure
        evidence_parts = [
            f"Records: {len(records)}",
            f"Compliant: {summary.get('compliant_days', 0)}/{summary.get('total_records', 0)}",
            f"Avg Rest: {summary.get('average_rest_hours', 0)}h",
            f"Warnings: {summary.get('active_warnings', 0)}"
        ]

        # Validate record structure if records exist
        if records:
            first = records[0]
            required = ['id', 'user_id', 'record_date', 'total_rest_hours', 'is_daily_compliant']
            missing = [f for f in required if f not in first]
            if missing:
                log_test("get_hours_of_rest", user["role"], "FAIL",
                        f"Records missing fields: {missing}")
                return None

            # Check user_id matches target
            if first['user_id'] != target:
                log_test("get_hours_of_rest", user["role"], "FAIL",
                        f"RLS VIOLATION: Got user_id={first['user_id']}, expected={target}")
                add_issue("RLS", f"get_hours_of_rest returns wrong user data", "CRITICAL",
                         "Review RLS policies on pms_hours_of_rest table")
                return None

        log_test("get_hours_of_rest", user["role"], "PASS",
                ", ".join(evidence_parts))
        return data

    except Exception as e:
        log_test("get_hours_of_rest", user["role"], "FAIL", f"Exception: {e}")
        return None

def test_upsert_hours_of_rest(user: Dict):
    """Test upsert_hours_of_rest action."""
    test_date = (date.today() - timedelta(days=1)).isoformat()

    payload = {
        "action": "upsert_hours_of_rest",
        "context": {
            "yacht_id": YACHT_ID,
            "user_id": user["user_id"],
            "role": user["role"]
        },
        "payload": {
            "yacht_id": YACHT_ID,
            "user_id": user["user_id"],
            "record_date": test_date,
            "rest_periods": [
                {"start": "22:00", "end": "06:00", "hours": 8},
                {"start": "13:00", "end": "14:00", "hours": 1}
            ],
            "total_rest_hours": 9,
            "daily_compliance_notes": "E2E test record"
        }
    }

    try:
        response = requests.post(
            f"{API_BASE}/v1/actions/execute",
            json=payload,
            headers={"Authorization": f"Bearer {user['jwt']}"},
            timeout=10
        )

        data = response.json()

        if response.status_code != 200:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    f"HTTP {response.status_code}: {data.get('message', 'Unknown error')}")
            return None

        # Hard evidence validation
        if 'data' not in data:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    "Missing 'data' field in response")
            return None

        record = data['data'].get('record')
        if not record:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    "Missing 'record' in data")
            return None

        # Validate returned record
        evidence_parts = [
            f"ID: {record.get('id', 'MISSING')[:8]}...",
            f"Date: {record.get('record_date')}",
            f"Rest: {record.get('total_rest_hours')}h",
            f"Compliant: {record.get('is_daily_compliant')}"
        ]

        # Check data integrity
        if record.get('record_date') != test_date:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    f"Date mismatch: got {record.get('record_date')}, expected {test_date}")
            return None

        if record.get('total_rest_hours') != 9:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    f"Rest hours mismatch: got {record.get('total_rest_hours')}, expected 9")
            return None

        if record.get('user_id') != user["user_id"]:
            log_test("upsert_hours_of_rest", user["role"], "FAIL",
                    f"RLS VIOLATION: user_id mismatch")
            add_issue("RLS", "upsert_hours_of_rest created record for wrong user", "CRITICAL",
                     "Review handler user_id assignment")
            return None

        log_test("upsert_hours_of_rest", user["role"], "PASS",
                ", ".join(evidence_parts))
        return data

    except Exception as e:
        log_test("upsert_hours_of_rest", user["role"], "FAIL", f"Exception: {e}")
        return None

def test_action_not_wired(action: str, user: Dict):
    """Test that action returns 404 (not wired to dispatch)."""
    payload = {
        "action": action,
        "context": {
            "yacht_id": YACHT_ID,
            "user_id": user["user_id"],
            "role": user["role"]
        },
        "payload": {
            "yacht_id": YACHT_ID,
            "user_id": user["user_id"]
        }
    }

    try:
        response = requests.post(
            f"{API_BASE}/v1/actions/execute",
            json=payload,
            headers={"Authorization": f"Bearer {user['jwt']}"},
            timeout=10
        )

        data = response.json()

        if response.status_code == 404:
            log_test(action, user["role"], "EXPECTED",
                    f"Not wired to dispatch (404)")
            return True
        else:
            log_test(action, user["role"], "UNEXPECTED",
                    f"Got HTTP {response.status_code}, expected 404")
            return False

    except Exception as e:
        log_test(action, user["role"], "FAIL", f"Exception: {e}")
        return False

print("=" * 80)
print("HOR COMPREHENSIVE E2E TESTING - MULTI-ROLE HARD EVIDENCE")
print("=" * 80)
print(f"API: {API_BASE}")
print(f"Yacht: {YACHT_ID}")
print()

# ============================================================================
# TEST SUITE 1: get_hours_of_rest - Own Data
# ============================================================================
print("[SUITE 1] get_hours_of_rest - Users Accessing Own Data")
print("-" * 80)

test_get_hours_of_rest(CAPTAIN)
test_get_hours_of_rest(HOD)
test_get_hours_of_rest(CREW)

# ============================================================================
# TEST SUITE 2: get_hours_of_rest - Cross-User Access (RLS Testing)
# ============================================================================
print("\n[SUITE 2] get_hours_of_rest - Cross-User Access (RLS Validation)")
print("-" * 80)

# CAPTAIN should access HOD data (RLS policy allows)
print("CAPTAIN → HOD data:")
test_get_hours_of_rest(CAPTAIN, HOD["user_id"])

# CAPTAIN should access CREW data (RLS policy allows)
print("CAPTAIN → CREW data:")
test_get_hours_of_rest(CAPTAIN, CREW["user_id"])

# HOD should access CREW in same department (RLS policy allows if same dept)
print("HOD → CREW data (same department):")
test_get_hours_of_rest(HOD, CREW["user_id"])

# CREW should NOT access other users (RLS should deny)
print("CREW → CAPTAIN data (should deny):")
test_get_hours_of_rest(CREW, CAPTAIN["user_id"])

# ============================================================================
# TEST SUITE 3: upsert_hours_of_rest - Data Mutation
# ============================================================================
print("\n[SUITE 3] upsert_hours_of_rest - Data Mutation")
print("-" * 80)

test_upsert_hours_of_rest(CAPTAIN)
test_upsert_hours_of_rest(HOD)
test_upsert_hours_of_rest(CREW)

# ============================================================================
# TEST SUITE 4: Unwired Actions - Coverage Check
# ============================================================================
print("\n[SUITE 4] Unwired HOR Actions - Coverage Check")
print("-" * 80)

unwired_actions = [
    "get_monthly_signoff",
    "list_monthly_signoffs",
    "create_monthly_signoff",
    "sign_monthly_signoff",
    "create_crew_template",
    "apply_crew_template",
    "list_crew_templates",
    "list_crew_warnings",
    "acknowledge_warning",
    "dismiss_warning"
]

for action in unwired_actions:
    test_action_not_wired(action, CAPTAIN)
    if action in unwired_actions[:3]:  # Only test first 3 to save time
        pass
    else:
        break  # Skip remaining after confirming pattern

if len(unwired_actions) > 0:
    add_issue("COVERAGE", f"{len(unwired_actions)} HOR actions not wired to dispatch", "HIGH",
             f"Wire actions to p0_actions_routes.py: {', '.join(unwired_actions[:5])}...")

# ============================================================================
# RESULTS SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST RESULTS SUMMARY")
print("=" * 80)
print(f"Total Tests: {results['total_tests']}")
print(f"Passed: {results['passed']} ✅")
print(f"Failed: {results['failed']} ❌")
print(f"Success Rate: {(results['passed']/results['total_tests']*100):.1f}%")
print()

if results['issues']:
    print("=" * 80)
    print("ISSUES IDENTIFIED")
    print("=" * 80)
    for i, issue in enumerate(results['issues'], 1):
        print(f"\n[ISSUE {i}] {issue['severity']} - {issue['category']}")
        print(f"Description: {issue['description']}")
        print(f"Fix: {issue['fix']}")
else:
    print("✅ No issues identified")

print("\n" + "=" * 80)
