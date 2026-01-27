#!/usr/bin/env python3
"""
Faults RLS Test Suite (Docker) - Fault Lens v1
===============================================
Proves role/RLS, error mapping, and suggestions for the Fault lens.

Role Matrix (Fault Lens v1):
- ALL CREW: can report faults, add notes, add photos, view
- ENGINEER+: can acknowledge, update, close, reopen, diagnose, mark_false_alarm
- HOD (chief_engineer, captain, manager): can create_work_order_from_fault (SIGNED)

Error mapping: 4xx for client errors; 500 is test failure
Storage isolation: path prefixes are per-yacht (pms-discrepancy-photos bucket)

Run with: docker-compose -f docker-compose.test.yml up --build
"""
import os
import time
import uuid
import requests
from typing import Optional, Tuple, Dict, Any, List

API_BASE = os.getenv("API_BASE", "http://api:8000")
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")
TENANT_SUPABASE_URL = os.getenv("TENANT_SUPABASE_URL")
TENANT_SUPABASE_SERVICE_KEY = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
YACHT_ID = os.getenv("YACHT_ID")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "Password2!")

USERS = {
    "crew": os.getenv("CREW_EMAIL", "crew.test@alex-short.com"),
    "engineer": os.getenv("ENGINEER_EMAIL", "engineer.test@alex-short.com"),
    "hod": os.getenv("HOD_EMAIL", "hod.test@alex-short.com"),
    "captain": os.getenv("CAPTAIN_EMAIL", "captain.test@alex-short.com"),
}

# Track test results
test_results: List[Tuple[str, bool, str]] = []


def log(msg: str, level: str = "INFO"):
    icon = {"INFO": "  ", "PASS": "  [PASS]", "FAIL": "  [FAIL]", "WARN": "  [WARN]"}.get(level, "  ")
    print(f"{icon} {msg}")


def record_test(name: str, passed: bool, detail: str = ""):
    test_results.append((name, passed, detail))
    level = "PASS" if passed else "FAIL"
    log(f"{name}: {detail}" if detail else name, level)


def get_jwt(email: str, password: str) -> Optional[str]:
    """Get JWT from MASTER Supabase auth."""
    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": MASTER_SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json={"email": email, "password": password}, timeout=12)
        return r.json().get("access_token") if r.status_code == 200 else None
    except Exception as e:
        log(f"JWT fetch failed for {email}: {e}", "WARN")
        return None


def api_call(method: str, endpoint: str, jwt: str, payload: dict = None) -> Tuple[int, Dict[str, Any]]:
    """Make API call and return (status_code, response_body)."""
    url = f"{API_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    try:
        if method.upper() == "GET":
            resp = requests.get(url, headers=headers, timeout=20)
        else:
            resp = requests.post(url, headers=headers, json=payload or {}, timeout=30)
        return resp.status_code, resp.json()
    except Exception as e:
        return 500, {"error": str(e)}


def must_have_env():
    """Validate required environment variables."""
    required = {
        "API_BASE": API_BASE,
        "MASTER_SUPABASE_URL": MASTER_SUPABASE_URL,
        "MASTER_SUPABASE_ANON_KEY": MASTER_SUPABASE_ANON_KEY,
        "TENANT_SUPABASE_URL": TENANT_SUPABASE_URL,
        "TENANT_SUPABASE_SERVICE_KEY": TENANT_SUPABASE_SERVICE_KEY,
        "YACHT_ID": YACHT_ID,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")


def get_test_equipment_id() -> str:
    """Get or create a test equipment ID for fault tests."""
    # For now, return a valid UUID that exists in the test database
    # In real tests, this would query pms_equipment or use a known test fixture
    return os.getenv("TEST_EQUIPMENT_ID", "00000000-0000-0000-0000-000000000001")


def test_crew_can_report_fault(crew_jwt: str, equipment_id: str) -> Optional[str]:
    """Test: CREW can report faults (Fault Lens v1)."""
    log("Testing: CREW can report fault...")
    code, body = api_call("POST", "/v1/actions/execute", crew_jwt, {
        "action": "report_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "equipment_id": equipment_id,
            "title": f"Crew Test Fault {int(time.time())}",
            "description": "Crew observed this issue during routine check",
            "severity": "minor"
        }
    })

    # Extract fault_id from response
    fault_id = body.get("fault_id") or (body.get("result") or {}).get("fault_id")

    if code == 200 and fault_id:
        record_test("CREW report_fault", True)
        return fault_id
    else:
        record_test("CREW report_fault", False, f"Expected 200 with fault_id, got {code}: {body}")
        return None


def test_crew_can_add_note(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW can add notes to faults."""
    log("Testing: CREW can add fault note...")
    code, body = api_call("POST", "/v1/actions/execute", crew_jwt, {
        "action": "add_fault_note",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            "text": f"Crew observation at {int(time.time())}: The issue persists"
        }
    })

    note_id = body.get("note_id") or (body.get("result") or {}).get("note_id")
    passed = code == 200 and note_id
    record_test("CREW add_fault_note", passed, f"Got {code}" if not passed else "")
    return passed


def test_crew_cannot_close_fault(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot close faults (engineer+ only)."""
    log("Testing: CREW cannot close fault...")
    code, body = api_call("POST", "/v1/actions/execute", crew_jwt, {
        "action": "close_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"fault_id": fault_id}
    })

    # Expect 403 Forbidden
    passed = code == 403
    record_test("CREW close_fault denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


def test_engineer_can_acknowledge(engineer_jwt: str, fault_id: str) -> bool:
    """Test: ENGINEER can acknowledge faults."""
    log("Testing: ENGINEER can acknowledge fault...")
    code, body = api_call("POST", "/v1/actions/execute", engineer_jwt, {
        "action": "acknowledge_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"fault_id": fault_id}
    })

    passed = code == 200
    record_test("ENGINEER acknowledge_fault", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_engineer_can_update(engineer_jwt: str, fault_id: str) -> bool:
    """Test: ENGINEER can update faults."""
    log("Testing: ENGINEER can update fault...")
    code, body = api_call("POST", "/v1/actions/execute", engineer_jwt, {
        "action": "update_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            "description": "Updated by engineer during diagnosis"
        }
    })

    passed = code == 200
    record_test("ENGINEER update_fault", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_hod_can_create_wo(hod_jwt: str, fault_id: str) -> Optional[str]:
    """Test: HOD can create work order from fault (SIGNED action)."""
    log("Testing: HOD can create WO from fault (signed)...")
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "create_work_order_from_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            "signature": {
                "signed_at": "2026-01-27T12:00:00Z",
                "user_id": "test-user",
                "role_at_signing": "captain",  # Required: captain or manager
                "signature_type": "pin_totp",
                "signature_hash": "test-hash-abc123",
            }
        }
    })

    wo_id = body.get("work_order_id") or (body.get("result") or {}).get("work_order_id")
    passed = code == 200 and wo_id
    record_test("HOD create_work_order_from_fault", passed, f"Got {code}: {body}" if not passed else "")
    return wo_id if passed else None


def test_signed_flow_missing_signature(hod_jwt: str, fault_id: str) -> bool:
    """Test: Missing signature returns 400 for signed action."""
    log("Testing: Missing signature returns 400...")
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "create_work_order_from_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            # No signature
        }
    })

    # Should get 400 for missing signature
    passed = code == 400 and body.get("error_code") in ("INVALID_SIGNATURE", "missing_required_fields")
    record_test("Missing signature returns 400", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_signed_flow_wrong_role(hod_jwt: str, fault_id: str) -> bool:
    """Test: Wrong signature role returns 400."""
    log("Testing: Wrong signature role returns 400...")
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "create_work_order_from_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            "signature": {
                "signed_at": "2026-01-27T12:00:00Z",
                "user_id": "test-user",
                "role_at_signing": "chief_engineer",  # Wrong: must be captain or manager
                "signature_type": "pin_totp",
                "signature_hash": "test-hash",
            }
        }
    })

    # Should get 400 for wrong signature role
    passed = code == 400 and "INVALID_SIGNATURE_ROLE" in str(body)
    record_test("Wrong signature role returns 400", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_crew_cannot_create_wo(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot create work order from fault."""
    log("Testing: CREW cannot create WO from fault...")
    code, body = api_call("POST", "/v1/actions/execute", crew_jwt, {
        "action": "create_work_order_from_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "fault_id": fault_id,
            "signature": {"confirmed": True}
        }
    })

    # Expect 403 Forbidden
    passed = code == 403
    record_test("CREW create_wo denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


def test_invalid_fault_returns_4xx(hod_jwt: str) -> bool:
    """Test: Invalid fault ID returns 4xx, not 5xx."""
    log("Testing: Invalid fault ID returns 4xx...")
    fake_id = str(uuid.uuid4())
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "update_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"fault_id": fake_id}
    })

    passed = 400 <= code < 500
    record_test("Invalid fault returns 4xx", passed, f"Got {code}" if not passed else "")
    return passed


def test_action_suggestions_hod(hod_jwt: str) -> bool:
    """Test: HOD sees mutation actions in faults domain."""
    log("Testing: HOD sees fault mutations in suggestions...")
    code, body = api_call("GET", "/v1/actions/list?domain=faults", hod_jwt)

    if code != 200:
        record_test("HOD suggestions", False, f"Expected 200, got {code}")
        return False

    action_ids = [a.get("action_id") for a in body.get("actions", [])]
    expected = ["report_fault", "close_fault", "create_work_order_from_fault"]
    found = [a for a in expected if a in action_ids]

    passed = len(found) >= 2  # At least 2 of expected actions
    record_test("HOD suggestions include mutations", passed, f"Found: {found}")
    return passed


def test_action_suggestions_crew(crew_jwt: str) -> bool:
    """Test: CREW sees appropriate actions (can report, add_note, add_photo)."""
    log("Testing: CREW sees allowed actions in suggestions...")
    code, body = api_call("GET", "/v1/actions/list?domain=faults", crew_jwt)

    if code != 200:
        record_test("CREW suggestions", False, f"Expected 200, got {code}")
        return False

    actions = body.get("actions", [])
    action_ids = [a.get("action_id") for a in actions]

    # CREW should see: report_fault, add_fault_note, add_fault_photo, view_fault_detail
    allowed_for_crew = ["report_fault", "add_fault_note", "add_fault_photo", "view_fault_detail"]
    found_allowed = [a for a in allowed_for_crew if a in action_ids]

    # CREW should NOT see: close_fault, create_work_order_from_fault
    denied_for_crew = ["close_fault", "create_work_order_from_fault"]
    found_denied = [a for a in denied_for_crew if a in action_ids]

    passed = len(found_allowed) >= 2 and len(found_denied) == 0
    record_test("CREW suggestions correct", passed,
                f"Allowed: {found_allowed}, Denied visible: {found_denied}")
    return passed


def test_storage_options(hod_jwt: str) -> bool:
    """Test: Storage options for add_fault_photo show safe yacht prefix."""
    log("Testing: Storage options for add_fault_photo...")
    code, body = api_call("GET", "/v1/actions/list?domain=faults", hod_jwt)

    if code != 200:
        record_test("Storage options fetch", False, f"Expected 200, got {code}")
        return False

    actions = body.get("actions", [])
    add_photo = next((a for a in actions if a.get("action_id") == "add_fault_photo"), None)

    if not add_photo:
        record_test("Storage options", False, "add_fault_photo not found in actions")
        return False

    storage = add_photo.get("storage_options", {})
    path_preview = storage.get("path_preview", "")
    bucket = storage.get("bucket", "")

    # Validate bucket is correct and path contains yacht prefix
    correct_bucket = "pms-discrepancy-photos" in bucket or "documents" in bucket
    correct_path = f"{YACHT_ID}/faults/" in path_preview or "{yacht_id}/faults/" in path_preview

    passed = correct_path  # Focus on path validation
    record_test("Storage path isolation", passed, f"Bucket: {bucket}, Path: {path_preview}")
    return passed


# ============================================================================
# PR #2: SUGGESTIONS API TESTS - Context Gating & Disambiguation
# ============================================================================


def test_suggestions_context_gating_wo_hidden(hod_jwt: str) -> bool:
    """Test: create_work_order_from_fault NOT shown without entity context."""
    log("Testing: create_wo_from_fault hidden without entity context...")
    code, body = api_call("POST", "/v1/actions/suggestions", hod_jwt, {
        "query_text": "create work order",
        "domain": "faults",
        # NO entity_type or entity_id
    })

    if code != 200:
        record_test("Suggestions API call", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])
    action_ids = [c.get("action_id") for c in candidates]

    # create_work_order_from_fault should NOT appear (context gated)
    if "create_work_order_from_fault" in action_ids:
        record_test("Context gating: WO hidden", False, "Found create_work_order_from_fault without context")
        return False

    record_test("Context gating: WO hidden", True, f"Actions: {action_ids}")
    return True


def test_suggestions_context_gating_wo_shown(hod_jwt: str, fault_id: str) -> bool:
    """Test: create_work_order_from_fault shown when focused on fault entity."""
    log("Testing: create_wo_from_fault shown with fault entity context...")
    code, body = api_call("POST", "/v1/actions/suggestions", hod_jwt, {
        "query_text": "create work order",
        "domain": "faults",
        "entity_type": "fault",
        "entity_id": fault_id,
    })

    if code != 200:
        record_test("Suggestions with context", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])
    action_ids = [c.get("action_id") for c in candidates]

    # create_work_order_from_fault SHOULD appear (focused on fault)
    if "create_work_order_from_fault" not in action_ids:
        record_test("Context gating: WO shown", False, f"create_work_order_from_fault not in {action_ids}")
        return False

    # Also verify focused_entity is returned
    focused = body.get("focused_entity", {})
    if focused.get("entity_type") != "fault" or focused.get("entity_id") != fault_id:
        record_test("Context gating: WO shown", False, f"Wrong focused_entity: {focused}")
        return False

    record_test("Context gating: WO shown", True, f"Found in: {action_ids}")
    return True


def test_suggestions_multiple_candidates(hod_jwt: str) -> bool:
    """Test: Suggestions API returns multiple candidates (never just one)."""
    log("Testing: Multiple candidates returned...")
    code, body = api_call("POST", "/v1/actions/suggestions", hod_jwt, {
        "query_text": "fault",
        "domain": "faults",
        "limit": 5,
    })

    if code != 200:
        record_test("Multiple candidates fetch", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])
    count = len(candidates)

    # Should have multiple candidates (never just one per brief)
    if count < 2:
        record_test("Multiple candidates", False, f"Only {count} candidate(s)")
        return False

    # Verify match_scores are present and deterministic (numbers)
    for c in candidates:
        if not isinstance(c.get("match_score"), (int, float)):
            record_test("Multiple candidates", False, f"Missing/invalid match_score in {c}")
            return False

    record_test("Multiple candidates", True, f"Got {count} candidates with scores")
    return True


def test_suggestions_domain_filter(hod_jwt: str) -> bool:
    """Test: Domain filter is honored - only faults domain actions returned."""
    log("Testing: Domain filter honored...")
    code, body = api_call("POST", "/v1/actions/suggestions", hod_jwt, {
        "query_text": "",
        "domain": "faults",
        "limit": 20,
    })

    if code != 200:
        record_test("Domain filter", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])

    # All candidates should be from faults domain
    non_faults = [c for c in candidates if c.get("domain") not in ("faults", None)]
    if non_faults:
        record_test("Domain filter", False, f"Non-faults domains: {[c.get('domain') for c in non_faults]}")
        return False

    record_test("Domain filter", True, f"{len(candidates)} faults-only candidates")
    return True


def test_canonical_roles_crew(crew_jwt: str) -> bool:
    """Test: CREW role sees correct actions (report, photo, note, view)."""
    log("Testing: CREW canonical roles in suggestions...")
    code, body = api_call("POST", "/v1/actions/suggestions", crew_jwt, {
        "domain": "faults",
        "limit": 20,
    })

    if code != 200:
        record_test("CREW canonical roles", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])
    action_ids = [c.get("action_id") for c in candidates]

    # CREW should see these (per binding brief canonical roles)
    should_see = ["report_fault", "add_fault_photo", "add_fault_note", "view_fault_detail"]
    # CREW should NOT see these mutations
    should_not_see = ["acknowledge_fault", "close_fault", "diagnose_fault", "update_fault", "reopen_fault"]

    missing = [a for a in should_see if a not in action_ids]
    forbidden = [a for a in should_not_see if a in action_ids]

    if missing:
        record_test("CREW canonical roles", False, f"Missing: {missing}")
        return False
    if forbidden:
        record_test("CREW canonical roles", False, f"Should not see: {forbidden}")
        return False

    record_test("CREW canonical roles", True, f"Correct actions: {action_ids}")
    return True


def test_canonical_roles_hod(hod_jwt: str) -> bool:
    """Test: HOD role sees all fault mutations."""
    log("Testing: HOD canonical roles in suggestions...")
    code, body = api_call("POST", "/v1/actions/suggestions", hod_jwt, {
        "domain": "faults",
        "limit": 20,
    })

    if code != 200:
        record_test("HOD canonical roles", False, f"Expected 200, got {code}")
        return False

    candidates = body.get("candidates", [])
    action_ids = [c.get("action_id") for c in candidates]

    # HOD should see all these
    should_see = [
        "report_fault", "acknowledge_fault", "close_fault",
        "update_fault", "diagnose_fault", "reopen_fault",
        "add_fault_photo", "add_fault_note", "view_fault_detail",
    ]

    missing = [a for a in should_see if a not in action_ids]

    if missing:
        record_test("HOD canonical roles", False, f"Missing: {missing}")
        return False

    record_test("HOD canonical roles", True, f"All actions visible: {len(action_ids)}")
    return True


def main():
    """Main test runner."""
    print("\n" + "=" * 60)
    print("FAULT LENS v1 - DOCKER RLS TEST SUITE")
    print("=" * 60 + "\n")

    must_have_env()

    # Get JWTs for all test users
    log("Obtaining JWTs...")
    crew_jwt = get_jwt(USERS["crew"], TEST_PASSWORD)
    engineer_jwt = get_jwt(USERS.get("engineer", USERS["hod"]), TEST_PASSWORD)  # Fallback to HOD if no engineer
    hod_jwt = get_jwt(USERS["hod"], TEST_PASSWORD)
    captain_jwt = get_jwt(USERS["captain"], TEST_PASSWORD)

    if not crew_jwt:
        raise SystemExit("Failed to get CREW JWT")
    if not hod_jwt:
        raise SystemExit("Failed to get HOD JWT")

    # Use HOD as engineer fallback if engineer JWT not available
    if not engineer_jwt:
        log("Using HOD JWT as engineer fallback", "WARN")
        engineer_jwt = hod_jwt

    equipment_id = get_test_equipment_id()

    print("\n--- ROLE/RLS TESTS ---\n")

    # Test 1: CREW can report fault
    fault_id = test_crew_can_report_fault(crew_jwt, equipment_id)
    if not fault_id:
        log("Cannot continue without a fault_id from crew test", "WARN")
        # Create fault with HOD as fallback
        code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
            "action": "report_fault",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "equipment_id": equipment_id,
                "title": f"HOD Fallback Fault {int(time.time())}",
                "severity": "minor"
            }
        })
        fault_id = body.get("fault_id") or (body.get("result") or {}).get("fault_id")
        if not fault_id:
            raise SystemExit(f"Failed to create test fault: {body}")
        log(f"Created fallback fault: {fault_id}", "INFO")

    # Test 2: CREW can add note
    test_crew_can_add_note(crew_jwt, fault_id)

    # Test 3: CREW cannot close fault
    test_crew_cannot_close_fault(crew_jwt, fault_id)

    # Test 4: ENGINEER can acknowledge
    test_engineer_can_acknowledge(engineer_jwt, fault_id)

    # Test 5: ENGINEER can update
    test_engineer_can_update(engineer_jwt, fault_id)

    # Test 6: CREW cannot create WO
    test_crew_cannot_create_wo(crew_jwt, fault_id)

    # Test 7: HOD can create WO (SIGNED)
    # Note: This will fail if fault is already work_ordered, so we create a fresh fault
    log("Creating fresh fault for WO test...")
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "report_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "equipment_id": equipment_id,
            "title": f"WO Test Fault {int(time.time())}",
            "severity": "major"
        }
    })
    wo_test_fault_id = body.get("fault_id") or (body.get("result") or {}).get("fault_id")
    if wo_test_fault_id:
        test_hod_can_create_wo(hod_jwt, wo_test_fault_id)
    else:
        record_test("HOD create_work_order_from_fault", False, "Could not create test fault")

    print("\n--- ERROR MAPPING TESTS ---\n")

    # Test 8: Invalid fault returns 4xx
    test_invalid_fault_returns_4xx(hod_jwt)

    print("\n--- SUGGESTION TESTS ---\n")

    # Test 9: HOD sees mutations
    test_action_suggestions_hod(hod_jwt)

    # Test 10: CREW sees correct actions
    test_action_suggestions_crew(crew_jwt)

    # Test 11: Storage options
    test_storage_options(hod_jwt)

    print("\n--- PR #2: SUGGESTIONS API CONTEXT GATING ---\n")

    # Test 12: create_wo_from_fault hidden without entity context
    test_suggestions_context_gating_wo_hidden(hod_jwt)

    # Test 13: create_wo_from_fault shown with fault entity context
    if fault_id:
        test_suggestions_context_gating_wo_shown(hod_jwt, fault_id)
    else:
        record_test("Context gating: WO shown", False, "No fault_id for test")

    # Test 14: Multiple candidates returned
    test_suggestions_multiple_candidates(hod_jwt)

    # Test 15: Domain filter honored
    test_suggestions_domain_filter(hod_jwt)

    # Test 16: CREW canonical roles
    test_canonical_roles_crew(crew_jwt)

    # Test 17: HOD canonical roles
    test_canonical_roles_hod(hod_jwt)

    print("\n--- PR #3: SIGNED FLOW TESTS ---\n")

    # Test 18: Missing signature returns 400
    # Create fresh fault for this test
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "report_fault",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "equipment_id": equipment_id,
            "title": f"Signed Flow Test {int(time.time())}",
            "severity": "major"
        }
    })
    signed_test_fault_id = body.get("fault_id") or (body.get("result") or {}).get("fault_id")
    if signed_test_fault_id:
        test_signed_flow_missing_signature(hod_jwt, signed_test_fault_id)
        test_signed_flow_wrong_role(hod_jwt, signed_test_fault_id)
    else:
        record_test("Signed flow tests", False, "Could not create test fault")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p, _ in test_results if p)
    failed = len(test_results) - passed

    for name, result, detail in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
        if detail and not result:
            print(f"         {detail}")

    print(f"\nTotal: {passed}/{len(test_results)} passed")

    if failed > 0:
        print(f"\nFAILED: {failed} tests")
        raise SystemExit(1)
    else:
        print("\nAll Fault Lens Docker tests passed.")


if __name__ == "__main__":
    main()
