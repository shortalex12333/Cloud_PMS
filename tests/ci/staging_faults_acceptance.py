#!/usr/bin/env python3
"""
Staging Faults Acceptance - Fault Lens v1
==========================================
Real-JWT checks for the Fault lens with staging environment.

Role Matrix (Fault Lens v1):
- ALL CREW: can report faults, add notes, add photos, view
- ENGINEER+: can acknowledge, update, close, reopen, diagnose
- HOD (chief_engineer, captain, manager): can create_work_order_from_fault (SIGNED)

Asserts:
- CREW can report_fault (200)
- CREW can add_fault_note (200)
- CREW cannot close_fault (403)
- ENGINEER can update_fault (200)
- HOD can create_work_order_from_fault (200, SIGNED)
- Invalid fault update returns 4xx (never 500)
- Action list returns correct actions for each role
"""
import os
import sys
import time
import uuid
import requests
from typing import Optional, Tuple, Dict, Any, List

# Environment variables
API_BASE = os.environ.get('API_BASE')
MASTER_URL = os.environ.get('MASTER_SUPABASE_URL')
MASTER_ANON = os.environ.get('MASTER_SUPABASE_ANON_KEY')
TENANT_URL = os.environ.get('TENANT_SUPABASE_URL')
TENANT_SVC = os.environ.get('TENANT_SUPABASE_SERVICE_KEY')
YACHT_ID = os.environ.get('YACHT_ID')

CREW_EMAIL = os.environ.get('STAGING_CREW_EMAIL')
ENGINEER_EMAIL = os.environ.get('STAGING_ENGINEER_EMAIL')
HOD_EMAIL = os.environ.get('STAGING_HOD_EMAIL')
CAPTAIN_EMAIL = os.environ.get('STAGING_CAPTAIN_EMAIL')
PASSWORD = os.environ.get('STAGING_USER_PASSWORD')
TEST_EQUIPMENT_ID = os.environ.get('TEST_EQUIPMENT_ID', '00000000-0000-0000-0000-000000000001')

# Session for requests
S = requests.Session()
test_results: List[Tuple[str, bool, str]] = []


def fail(msg: str):
    """Record failure and exit."""
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    """Record success."""
    print(f"[PASS] {msg}")


def record(name: str, passed: bool, detail: str = ""):
    """Record test result."""
    test_results.append((name, passed, detail))
    if passed:
        ok(f"{name}: {detail}" if detail else name)
    else:
        print(f"[FAIL] {name}: {detail}" if detail else f"[FAIL] {name}")


def login(email: str, password: str) -> Optional[str]:
    """Obtain JWT from MASTER Supabase auth."""
    try:
        r = S.post(
            f"{MASTER_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": MASTER_ANON, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=15
        )
        if r.status_code != 200:
            return None
        return r.json().get('access_token')
    except Exception as e:
        print(f"[WARN] Login failed for {email}: {e}")
        return None


def call(jwt: str, method: str, path: str, payload: dict = None,
         expect: int = None) -> Tuple[int, Dict[str, Any]]:
    """Make API call and return (status_code, response_body)."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    try:
        if method.upper() == 'GET':
            r = S.get(url, headers=headers, timeout=30)
        else:
            r = S.post(url, headers=headers, json=payload or {}, timeout=30)

        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}

        return r.status_code, body
    except Exception as e:
        return 500, {"error": str(e)}


def test_crew_report_fault(crew_jwt: str) -> Optional[str]:
    """Test: CREW can report fault (Fault Lens v1)."""
    code, body = call(crew_jwt, 'POST', '/v1/actions/execute', {
        'action': 'report_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'equipment_id': TEST_EQUIPMENT_ID,
            'title': f'Staging CI Fault {int(time.time())}',
            'description': 'Crew observed issue during CI test',
            'severity': 'minor'
        }
    })

    fault_id = body.get('fault_id') or (body.get('result') or {}).get('fault_id')
    passed = code == 200 and fault_id
    record("CREW report_fault", passed, f"Got {code}" if not passed else "")
    return fault_id if passed else None


def test_crew_add_note(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW can add note to fault."""
    code, body = call(crew_jwt, 'POST', '/v1/actions/execute', {
        'action': 'add_fault_note',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'fault_id': fault_id,
            'text': f'Staging CI note at {int(time.time())}'
        }
    })

    note_id = body.get('note_id') or (body.get('result') or {}).get('note_id')
    passed = code == 200 and note_id
    record("CREW add_fault_note", passed, f"Got {code}" if not passed else "")
    return passed


def test_crew_cannot_close(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot close fault (engineer+ only)."""
    code, body = call(crew_jwt, 'POST', '/v1/actions/execute', {
        'action': 'close_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'fault_id': fault_id}
    })

    passed = code == 403
    record("CREW close_fault denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


def test_engineer_update(engineer_jwt: str, fault_id: str) -> bool:
    """Test: ENGINEER can update fault."""
    code, body = call(engineer_jwt, 'POST', '/v1/actions/execute', {
        'action': 'update_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'fault_id': fault_id,
            'description': 'Updated by engineer in CI test'
        }
    })

    passed = code == 200
    record("ENGINEER update_fault", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_hod_create_wo(hod_jwt: str) -> bool:
    """Test: HOD can create work order from fault (SIGNED)."""
    # First create a fresh fault for this test
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'report_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'equipment_id': TEST_EQUIPMENT_ID,
            'title': f'WO Test Fault {int(time.time())}',
            'severity': 'major'
        }
    })

    fault_id = body.get('fault_id') or (body.get('result') or {}).get('fault_id')
    if not fault_id:
        record("HOD create_work_order_from_fault", False, "Could not create test fault")
        return False

    # Now test create_work_order_from_fault (SIGNED)
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'create_work_order_from_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'fault_id': fault_id,
            'signature': {
                'role_at_signing': 'chief_engineer',
                'confirmed': True
            }
        }
    })

    wo_id = body.get('work_order_id') or (body.get('result') or {}).get('work_order_id')
    passed = code == 200 and wo_id
    record("HOD create_work_order_from_fault", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_crew_cannot_create_wo(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot create work order from fault."""
    code, body = call(crew_jwt, 'POST', '/v1/actions/execute', {
        'action': 'create_work_order_from_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'fault_id': fault_id,
            'signature': {'confirmed': True}
        }
    })

    passed = code == 403
    record("CREW create_wo denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


def test_invalid_fault_4xx(hod_jwt: str) -> bool:
    """Test: Invalid fault ID returns 4xx, not 5xx."""
    fake_id = str(uuid.uuid4())
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'update_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'fault_id': fake_id}
    })

    passed = 400 <= code < 500
    record("Invalid fault returns 4xx", passed, f"Got {code}" if not passed else "")
    return passed


def test_suggestions_hod(hod_jwt: str) -> bool:
    """Test: HOD sees mutation actions in suggestions."""
    code, body = call(hod_jwt, 'GET', '/v1/actions/list?domain=faults')

    if code != 200:
        record("HOD suggestions", False, f"Expected 200, got {code}")
        return False

    action_ids = [a.get('action_id') for a in body.get('actions', [])]
    expected = ['report_fault', 'close_fault', 'create_work_order_from_fault']
    found = [a for a in expected if a in action_ids]

    passed = len(found) >= 2
    record("HOD suggestions include mutations", passed, f"Found: {found}")
    return passed


def test_suggestions_crew(crew_jwt: str) -> bool:
    """Test: CREW sees appropriate actions (can report, add_note, add_photo)."""
    code, body = call(crew_jwt, 'GET', '/v1/actions/list?domain=faults')

    if code != 200:
        record("CREW suggestions", False, f"Expected 200, got {code}")
        return False

    actions = body.get('actions', [])
    action_ids = [a.get('action_id') for a in actions]

    # CREW should see: report_fault, add_fault_note, add_fault_photo, view_fault_detail
    allowed = ['report_fault', 'add_fault_note', 'add_fault_photo', 'view_fault_detail']
    found_allowed = [a for a in allowed if a in action_ids]

    # CREW should NOT see: close_fault, create_work_order_from_fault
    denied = ['close_fault', 'create_work_order_from_fault']
    found_denied = [a for a in denied if a in action_ids]

    passed = len(found_allowed) >= 2 and len(found_denied) == 0
    record("CREW suggestions correct", passed,
           f"Allowed: {found_allowed}, Denied visible: {found_denied}")
    return passed


# ==============================================================================
# FAULT LENS v1 - NEW TESTS (Entity Extraction, Severity Mapping, Show Related)
# ==============================================================================

def test_severity_mapping(hod_jwt: str) -> bool:
    """Test: Severity mapping works (medium → minor, high → major)."""
    # Test with legacy "medium" severity - should map to "minor"
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'report_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'equipment_id': TEST_EQUIPMENT_ID,
            'title': f'Severity Map Test {int(time.time())}',
            'description': 'Testing medium → minor mapping',
            'severity': 'medium'  # Legacy value
        }
    })

    fault_data = body.get('result', {}).get('fault', {})
    actual_severity = fault_data.get('severity')

    # Should be mapped to "minor"
    passed = code == 200 and actual_severity == 'minor'
    record("Severity mapping (medium→minor)", passed,
           f"Got {code}, severity={actual_severity}" if not passed else "")
    return passed


def test_show_related_api(hod_jwt: str, fault_id: str) -> bool:
    """Test: Show Related API returns related entities."""
    code, body = call(hod_jwt, 'POST', '/v1/faults/related', {
        'entity_type': 'fault',
        'entity_id': fault_id,
        'limit': 20
    })

    passed = code == 200 and 'related' in body
    record("Show Related API", passed, f"Got {code}: {body}" if not passed else "")
    return passed


def test_add_related_hod(hod_jwt: str, fault_id: str) -> Optional[str]:
    """Test: HOD can add related entity link."""
    # Create a link to the equipment
    code, body = call(hod_jwt, 'POST', '/v1/faults/related/add', {
        'source_entity_type': 'fault',
        'source_entity_id': fault_id,
        'target_entity_type': 'equipment',
        'target_entity_id': TEST_EQUIPMENT_ID,
        'link_type': 'related',
        'note': 'Linked by staging CI test'
    })

    link_id = body.get('link_id')
    passed = code == 200 and link_id
    record("HOD add_related", passed, f"Got {code}: {body}" if not passed else "")
    return link_id if passed else None


def test_crew_cannot_add_related(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot add related entity links (HOD+ only)."""
    code, body = call(crew_jwt, 'POST', '/v1/faults/related/add', {
        'source_entity_type': 'fault',
        'source_entity_id': fault_id,
        'target_entity_type': 'equipment',
        'target_entity_id': TEST_EQUIPMENT_ID,
        'link_type': 'related'
    })

    passed = code == 403
    record("CREW add_related denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


def test_show_related_includes_link(hod_jwt: str, fault_id: str, link_id: str) -> bool:
    """Test: Show Related includes the newly created link."""
    if not link_id:
        record("Show Related includes link", False, "No link_id to check")
        return False

    code, body = call(hod_jwt, 'POST', '/v1/faults/related', {
        'entity_type': 'fault',
        'entity_id': fault_id
    })

    related = body.get('related', [])
    link_ids = [r.get('link_id') for r in related]

    passed = code == 200 and link_id in link_ids
    record("Show Related includes link", passed,
           f"Got {code}, link_id in results: {link_id in link_ids}")
    return passed


def test_acknowledge_fault(hod_jwt: str, fault_id: str) -> bool:
    """Test: HOD can acknowledge fault (open → investigating)."""
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'acknowledge_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'fault_id': fault_id,
            'notes': 'Acknowledged in staging CI test'
        }
    })

    result = body.get('result', {})
    new_status = result.get('new_status')

    passed = code == 200 and new_status == 'investigating'
    record("HOD acknowledge_fault", passed,
           f"Got {code}, status={new_status}" if not passed else "")
    return passed


def test_crew_cannot_acknowledge(crew_jwt: str, fault_id: str) -> bool:
    """Test: CREW cannot acknowledge fault (HOD+ only)."""
    code, body = call(crew_jwt, 'POST', '/v1/actions/execute', {
        'action': 'acknowledge_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'fault_id': fault_id}
    })

    passed = code == 403
    record("CREW acknowledge denied", passed, f"Expected 403, got {code}" if not passed else "")
    return passed


# ==============================================================================
# PR #2: SUGGESTIONS API CONTEXT GATING TESTS
# ==============================================================================


def test_suggestions_context_gating_wo_hidden(hod_jwt: str) -> bool:
    """Test: create_wo_from_fault NOT shown without entity context."""
    code, body = call(hod_jwt, 'POST', '/v1/actions/suggestions', {
        'query_text': 'create work order',
        'domain': 'faults',
        # NO entity_type or entity_id
    })

    if code != 200:
        record("Context gating: WO hidden", False, f"Expected 200, got {code}")
        return False

    candidates = body.get('candidates', [])
    action_ids = [c.get('action_id') for c in candidates]

    # create_work_order_from_fault should NOT appear
    if 'create_work_order_from_fault' in action_ids:
        record("Context gating: WO hidden", False, "create_wo found without context")
        return False

    record("Context gating: WO hidden", True)
    return True


def test_suggestions_context_gating_wo_shown(hod_jwt: str, fault_id: str) -> bool:
    """Test: create_wo_from_fault shown when focused on fault."""
    code, body = call(hod_jwt, 'POST', '/v1/actions/suggestions', {
        'query_text': 'create work order',
        'domain': 'faults',
        'entity_type': 'fault',
        'entity_id': fault_id,
    })

    if code != 200:
        record("Context gating: WO shown", False, f"Expected 200, got {code}")
        return False

    candidates = body.get('candidates', [])
    action_ids = [c.get('action_id') for c in candidates]

    if 'create_work_order_from_fault' not in action_ids:
        record("Context gating: WO shown", False, f"Not found in {action_ids}")
        return False

    # Verify focused_entity is returned
    focused = body.get('focused_entity', {})
    if focused.get('entity_type') != 'fault':
        record("Context gating: WO shown", False, f"Wrong focused_entity: {focused}")
        return False

    record("Context gating: WO shown", True)
    return True


def test_suggestions_multiple_candidates(hod_jwt: str) -> bool:
    """Test: Suggestions returns multiple candidates (never just one)."""
    code, body = call(hod_jwt, 'POST', '/v1/actions/suggestions', {
        'query_text': 'fault',
        'domain': 'faults',
        'limit': 5,
    })

    if code != 200:
        record("Multiple candidates", False, f"Expected 200, got {code}")
        return False

    candidates = body.get('candidates', [])
    count = len(candidates)

    if count < 2:
        record("Multiple candidates", False, f"Only {count} candidate(s)")
        return False

    record("Multiple candidates", True, f"Got {count} candidates")
    return True


def test_canonical_roles_suggestions(hod_jwt: str, crew_jwt: str) -> bool:
    """Test: Canonical roles enforced in Suggestions API."""
    # HOD should see all mutations
    code, body = call(hod_jwt, 'POST', '/v1/actions/suggestions', {
        'domain': 'faults',
        'limit': 20,
    })

    if code != 200:
        record("Canonical roles (HOD)", False, f"Expected 200, got {code}")
        return False

    hod_actions = [c.get('action_id') for c in body.get('candidates', [])]
    hod_should_see = ['acknowledge_fault', 'close_fault', 'diagnose_fault']
    hod_missing = [a for a in hod_should_see if a not in hod_actions]

    if hod_missing:
        record("Canonical roles (HOD)", False, f"Missing: {hod_missing}")
        return False

    # CREW should NOT see mutations
    code, body = call(crew_jwt, 'POST', '/v1/actions/suggestions', {
        'domain': 'faults',
        'limit': 20,
    })

    if code != 200:
        record("Canonical roles (CREW)", False, f"Expected 200, got {code}")
        return False

    crew_actions = [c.get('action_id') for c in body.get('candidates', [])]
    crew_should_not_see = ['acknowledge_fault', 'close_fault', 'diagnose_fault']
    crew_forbidden = [a for a in crew_should_not_see if a in crew_actions]

    if crew_forbidden:
        record("Canonical roles (CREW)", False, f"Should not see: {crew_forbidden}")
        return False

    record("Canonical roles enforced", True)
    return True


def main():
    print("\n" + "=" * 60)
    print("FAULT LENS v1 - STAGING ACCEPTANCE TESTS")
    print("=" * 60 + "\n")

    # Validate environment
    required = {
        'API_BASE': API_BASE,
        'MASTER_SUPABASE_URL': MASTER_URL,
        'MASTER_SUPABASE_ANON_KEY': MASTER_ANON,
        'TENANT_SUPABASE_URL': TENANT_URL,
        'TENANT_SUPABASE_SERVICE_KEY': TENANT_SVC,
        'YACHT_ID': YACHT_ID,
        'STAGING_USER_PASSWORD': PASSWORD,
        'STAGING_CREW_EMAIL': CREW_EMAIL,
        'STAGING_HOD_EMAIL': HOD_EMAIL,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        fail(f"Missing required env vars: {', '.join(missing)}")

    # Obtain JWTs
    print("Obtaining JWTs...")
    crew_jwt = login(CREW_EMAIL, PASSWORD)
    engineer_jwt = login(ENGINEER_EMAIL, PASSWORD) if ENGINEER_EMAIL else None
    hod_jwt = login(HOD_EMAIL, PASSWORD)
    captain_jwt = login(CAPTAIN_EMAIL, PASSWORD) if CAPTAIN_EMAIL else None

    if not crew_jwt:
        fail("Failed to get CREW JWT")
    if not hod_jwt:
        fail("Failed to get HOD JWT")

    # Use HOD as engineer fallback if no engineer email
    if not engineer_jwt:
        print("[INFO] Using HOD JWT as engineer fallback")
        engineer_jwt = hod_jwt

    print()
    print("--- ROLE/RLS TESTS ---")
    print()

    # Test 1: CREW can report fault
    fault_id = test_crew_report_fault(crew_jwt)
    if not fault_id:
        # Fallback: create fault with HOD
        code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
            'action': 'report_fault',
            'context': {'yacht_id': YACHT_ID},
            'payload': {
                'equipment_id': TEST_EQUIPMENT_ID,
                'title': f'HOD Fallback Fault {int(time.time())}',
                'severity': 'minor'
            }
        })
        fault_id = body.get('fault_id') or (body.get('result') or {}).get('fault_id')
        if not fault_id:
            fail(f"Failed to create test fault: {body}")
        print(f"[INFO] Created fallback fault: {fault_id}")

    # Test 2: CREW can add note
    test_crew_add_note(crew_jwt, fault_id)

    # Test 3: CREW cannot close fault
    test_crew_cannot_close(crew_jwt, fault_id)

    # Test 4: ENGINEER can update
    test_engineer_update(engineer_jwt, fault_id)

    # Test 5: CREW cannot create WO
    test_crew_cannot_create_wo(crew_jwt, fault_id)

    # Test 6: HOD can create WO (SIGNED)
    test_hod_create_wo(hod_jwt)

    print()
    print("--- ERROR MAPPING TESTS ---")
    print()

    # Test 7: Invalid fault returns 4xx
    test_invalid_fault_4xx(hod_jwt)

    print()
    print("--- SUGGESTION TESTS ---")
    print()

    # Test 8: HOD suggestions
    test_suggestions_hod(hod_jwt)

    # Test 9: CREW suggestions
    test_suggestions_crew(crew_jwt)

    print()
    print("--- FAULT LENS v1 NEW TESTS ---")
    print()

    # Test 10: Severity mapping
    test_severity_mapping(hod_jwt)

    # Test 11: Acknowledge fault (HOD only)
    # Create fresh fault for acknowledge test
    code, body = call(hod_jwt, 'POST', '/v1/actions/execute', {
        'action': 'report_fault',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'equipment_id': TEST_EQUIPMENT_ID,
            'title': f'Ack Test Fault {int(time.time())}',
            'severity': 'minor'
        }
    })
    ack_fault_id = body.get('fault_id') or (body.get('result') or {}).get('fault', {}).get('id')
    if ack_fault_id:
        test_crew_cannot_acknowledge(crew_jwt, ack_fault_id)
        test_acknowledge_fault(hod_jwt, ack_fault_id)

    # Test 12-15: Show Related + Add Related
    test_show_related_api(hod_jwt, fault_id)
    test_crew_cannot_add_related(crew_jwt, fault_id)
    link_id = test_add_related_hod(hod_jwt, fault_id)
    if link_id:
        test_show_related_includes_link(hod_jwt, fault_id, link_id)

    print()
    print("--- PR #2: SUGGESTIONS API CONTEXT GATING ---")
    print()

    # Test 16: create_wo_from_fault hidden without context
    test_suggestions_context_gating_wo_hidden(hod_jwt)

    # Test 17: create_wo_from_fault shown with fault context
    test_suggestions_context_gating_wo_shown(hod_jwt, fault_id)

    # Test 18: Multiple candidates returned
    test_suggestions_multiple_candidates(hod_jwt)

    # Test 19: Canonical roles enforced
    test_canonical_roles_suggestions(hod_jwt, crew_jwt)

    # Summary
    print()
    print("=" * 60)
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
        sys.exit(1)
    else:
        print("\nAll staging Fault Lens checks passed.")


if __name__ == '__main__':
    main()
