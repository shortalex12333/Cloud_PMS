#!/usr/bin/env python3
"""
Certificate RLS Test Suite for Docker
=====================================
Comprehensive tests for role-based access control and RLS isolation.

Run with: docker-compose -f docker-compose.test.yml up --build
"""
import os
import sys
import json
import time
import requests
from typing import Optional, Dict, Any, Tuple

# Configuration from environment
API_BASE = os.getenv("API_BASE", "http://api:8000")
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")
# Tenant REST (service key only for read-only invariants + doc_metadata insert)
TENANT_SUPABASE_URL = os.getenv("TENANT_SUPABASE_URL")
TENANT_SUPABASE_SERVICE_KEY = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
YACHT_ID = os.getenv("YACHT_ID")
OTHER_YACHT_ID = os.getenv("OTHER_YACHT_ID", "00000000-0000-0000-0000-000000000000")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "Password2!")

# Test users
USERS = {
    "crew": os.getenv("CREW_EMAIL", "crew.test@alex-short.com"),
    "hod": os.getenv("HOD_EMAIL", "hod.test@alex-short.com"),
    "captain": os.getenv("CAPTAIN_EMAIL", "captain.test@alex-short.com"),
}

# Test results
results = []


def log(msg: str, level: str = "INFO"):
    """Print formatted log message."""
    icon = {"INFO": "ℹ️", "PASS": "✓", "FAIL": "✗", "WARN": "⚠️"}.get(level, "")
    print(f"  {icon} {msg}")


def get_jwt(email: str, password: str) -> Optional[str]:
    """Get JWT token from MASTER Supabase."""
    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, json={"email": email, "password": password}, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        log(f"Auth failed for {email}: {response.status_code}", "WARN")
        return None
    except Exception as e:
        log(f"Auth error: {e}", "WARN")
        return None


def api_call(method: str, endpoint: str, jwt: str, payload: dict = None) -> Tuple[int, dict]:
    """Make API call and return (status_code, body)."""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }
    try:
        if method == "POST":
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        else:
            resp = requests.get(url, headers=headers, timeout=30)
        try:
            body = resp.json()
        except:
            body = {"raw": resp.text[:500]}
        return resp.status_code, body
    except Exception as e:
        return 0, {"error": str(e)}


def tenant_rest(method: str, path: str, params: Dict[str, Any] = None, body: Dict[str, Any] = None,
                anon: bool = False) -> Tuple[int, dict]:
    """Call Supabase REST on the tenant project."""
    url = f"{TENANT_SUPABASE_URL}{path}"
    key = TENANT_SUPABASE_SERVICE_KEY if not anon else MASTER_SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, params=params or {}, json=body or {}, timeout=30)
        else:
            resp = requests.request(method, url, headers=headers, params=params or {}, json=body or {}, timeout=30)
        try:
            data = resp.json()
        except:
            data = {"raw": resp.text[:500]}
        return resp.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}


def test_role_denial(jwt_crew: str, jwt_hod: str) -> bool:
    """Test that CREW cannot create/supersede certificates."""
    print("\n=== TEST: Role-Based Access Control ===")
    all_pass = True

    # CREW cannot create
    log("Testing CREW cannot create certificate...")
    code, body = api_call("POST", "/v1/actions/execute", jwt_crew, {
        "action": "create_vessel_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_type": "FLAG",
            "certificate_name": "CREW Test",
            "certificate_number": f"CREW-DENY-{int(time.time())}",
            "issuing_authority": "Test",
            "expiry_date": "2030-01-01"
        }
    })
    if code == 403:
        log("CREW create denied: PASS", "PASS")
        results.append(("CREW cannot create", True))
    else:
        log(f"CREW create: expected 403, got {code}", "FAIL")
        results.append(("CREW cannot create", False))
        all_pass = False

    # HOD can create
    log("Testing HOD can create certificate...")
    code, body = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "create_vessel_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_type": "FLAG",
            "certificate_name": "HOD Test",
            "certificate_number": f"HOD-OK-{int(time.time())}",
            "issuing_authority": "Test",
            "expiry_date": "2030-01-01"
        }
    })
    if code == 200:
        log("HOD create allowed: PASS", "PASS")
        results.append(("HOD can create", True))
        # Store cert_id for later tests
        return all_pass, body.get("certificate_id")
    else:
        log(f"HOD create: expected 200, got {code}", "FAIL")
        results.append(("HOD can create", False))
        return False, None


def test_supersede_requires_signature(jwt_hod: str, cert_id: str) -> bool:
    """Test that supersede requires signature."""
    print("\n=== TEST: Supersede Requires Signature ===")

    log("Testing supersede without signature...")
    code, body = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "supersede_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "reason": "Test without signature"
        }
    })
    if code == 400:
        log("Supersede without signature rejected: PASS", "PASS")
        results.append(("Supersede requires signature", True))
        return True
    else:
        log(f"Expected 400, got {code}", "FAIL")
        results.append(("Supersede requires signature", False))
        return False


def test_hod_cannot_supersede(jwt_hod: str, cert_id: str) -> bool:
    """HOD should not be allowed to supersede even with signature (403)."""
    print("\n=== TEST: HOD Cannot Supersede ===")
    code, body = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "supersede_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "reason": "HOD should be denied",
            "signature": "HOD-FAKE-SIG"
        }
    })
    if code == 403:
        log("HOD supersede denied: PASS", "PASS")
        results.append(("HOD cannot supersede", True))
        return True
    log(f"Expected 403, got {code}", "FAIL")
    results.append(("HOD cannot supersede", False))
    return False


def test_crew_cannot_supersede(jwt_crew: str, cert_id: str) -> bool:
    """Test that CREW cannot supersede even with signature."""
    print("\n=== TEST: CREW Cannot Supersede ===")

    log("Testing CREW cannot supersede...")
    code, body = api_call("POST", "/v1/actions/execute", jwt_crew, {
        "action": "supersede_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "reason": "CREW should not supersede",
            "signature": "CREW-FAKE-SIG"
        }
    })
    if code == 403:
        log("CREW supersede denied: PASS", "PASS")
        results.append(("CREW cannot supersede", True))
        return True
    else:
        log(f"Expected 403, got {code}", "FAIL")
        results.append(("CREW cannot supersede", False))
        return False


def test_captain_supersede(jwt_captain: str, cert_id: str) -> bool:
    """Captain/Manager can supersede with signature (200)."""
    print("\n=== TEST: Captain Supersede (Signed) ===")
    code, body = api_call("POST", "/v1/actions/execute", jwt_captain, {
        "action": "supersede_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "reason": "Captain signed supersede",
            "signature": json.dumps({
                "signature_type": "supersede_certificate",
                "role_at_signing": "captain",
                "signed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "signature_hash": "test-hash"
            })
        }
    })
    if code == 200:
        log("Captain supersede allowed: PASS", "PASS")
        results.append(("Captain supersede", True))
        return True
    log(f"Expected 200, got {code}", "FAIL")
    results.append(("Captain supersede", False))
    return False


def test_duplicate_certificate_number(jwt_hod: str) -> bool:
    """Test that duplicate certificate_number is rejected."""
    print("\n=== TEST: Duplicate Certificate Number ===")

    dup_num = f"DUP-{int(time.time())}"

    # First create
    log(f"Creating first certificate with number {dup_num}...")
    code1, body1 = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "create_vessel_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_type": "FLAG",
            "certificate_name": "Dup Test 1",
            "certificate_number": dup_num,
            "issuing_authority": "Test",
            "expiry_date": "2030-01-01"
        }
    })

    if code1 != 200:
        log(f"First create failed: {code1}", "FAIL")
        results.append(("Duplicate rejection", False))
        return False

    cert_id = body1.get("certificate_id")
    log(f"First certificate created: {cert_id}")

    # Second create with same number
    log("Creating second certificate with same number...")
    code2, body2 = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "create_vessel_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_type": "CLASS",
            "certificate_name": "Dup Test 2",
            "certificate_number": dup_num,
            "issuing_authority": "Test",
            "expiry_date": "2030-01-01"
        }
    })

    if code2 in (409, 400, 500):
        log(f"Duplicate rejected with {code2}: PASS", "PASS")
        results.append(("Duplicate rejection", True))
        return True
    else:
        log(f"Expected 409/400/500, got {code2}", "FAIL")
        results.append(("Duplicate rejection", False))
        return False


def test_date_validation(jwt_hod: str, cert_id: str) -> bool:
    """Test that expiry < issue date is rejected."""
    print("\n=== TEST: Date Validation ===")

    log("Testing expiry before issue date...")
    code, body = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "update_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "issue_date": "2030-01-01",
            "expiry_date": "2025-01-01"
        }
    })

    if code in (400, 500):
        log(f"Invalid dates rejected with {code}: PASS", "PASS")
        results.append(("Date validation", True))
        return True
    else:
        log(f"Expected 400/500, got {code}", "FAIL")
        results.append(("Date validation", False))
        return False


def test_update_ok(jwt_hod: str, cert_id: str) -> bool:
    """HOD can update certificate (200)."""
    print("\n=== TEST: Update Certificate (OK) ===")
    code, body = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "update_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "certificate_name": "Updated Name",
            "expiry_date": "2031-01-01"
        }
    })
    if code == 200:
        log("Update allowed: PASS", "PASS")
        results.append(("HOD update", True))
        return True
    log(f"Expected 200, got {code}", "FAIL")
    results.append(("HOD update", False))
    return False


def test_reads(jwt_hod: str, cert_id: str) -> bool:
    """Read endpoints (list, expiring, get, history) return 200."""
    print("\n=== TEST: Read Endpoints ===")
    ok = True
    for ep in [
        "/api/v1/certificates/vessel",
        "/api/v1/certificates/crew",
        "/api/v1/certificates/expiring?days_ahead=60&domain=all",
        f"/api/v1/certificates/{cert_id}",
        f"/api/v1/certificates/{cert_id}/history"
    ]:
        code, _ = api_call("GET", ep, jwt_hod)
        if code != 200:
            log(f"GET {ep}: expected 200, got {code}", "FAIL")
            ok = False
        else:
            log(f"GET {ep}: PASS", "PASS")
    results.append(("Read endpoints", ok))
    return ok


def test_link_document(jwt_hod: str, cert_id: str) -> bool:
    """Insert doc_metadata and link to certificate."""
    print("\n=== TEST: Link Document ===")
    # Insert doc_metadata row via tenant REST
    body = {
        "yacht_id": YACHT_ID,
        "source": "test",
        "filename": "test.pdf",
        "content_type": "application/pdf",
        "storage_path": f"{YACHT_ID}/certificates/{cert_id}/test.pdf"
    }
    code_dm, dm = tenant_rest("POST", "/rest/v1/doc_metadata", body=body)
    if code_dm not in (200, 201):
        log(f"doc_metadata insert failed: {code_dm}", "FAIL")
        results.append(("Link document", False))
        return False
    doc_id = dm[0].get("id") if isinstance(dm, list) and dm else dm.get("id")
    # Link via action
    code, resp = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "link_document_to_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "document_id": doc_id
        }
    })
    if code == 200:
        log("Link document: PASS", "PASS")
        results.append(("Link document", True))
        return True
    log(f"Link document expected 200, got {code}", "FAIL")
    results.append(("Link document", False))
    return False


def test_link_document_invalid(jwt_hod: str, cert_id: str) -> bool:
    print("\n=== TEST: Link Document Invalid ID ===")
    code, resp = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "link_document_to_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "certificate_id": cert_id,
            "domain": "vessel",
            "document_id": "00000000-0000-0000-0000-000000000000"
        }
    })
    if code in (400, 404):
        log("Invalid document rejected: PASS", "PASS")
        results.append(("Link invalid doc", True))
        return True
    log(f"Expected 400/404, got {code}", "FAIL")
    results.append(("Link invalid doc", False))
    return False


def test_anon_vs_service_rest() -> bool:
    """Anon returns [], service role shows rows."""
    print("\n=== TEST: Anon vs Service REST ===")
    # Service role count
    code_svc, data_svc = tenant_rest("GET", "/rest/v1/pms_vessel_certificates", params={"select": "id", "limit": 1})
    svc_ok = code_svc == 200 and isinstance(data_svc, list)
    # Anon (using master anon key as a proxy for anon) - expected to be blocked or empty
    code_anon, data_anon = tenant_rest("GET", "/rest/v1/pms_vessel_certificates", params={"select": "id", "limit": 1}, anon=True)
    anon_ok = (code_anon == 200 and data_anon == []) or code_anon in (401, 403)
    if svc_ok and anon_ok:
        log("Anon vs Service REST: PASS", "PASS")
        results.append(("Anon vs Service REST", True))
        return True
    log(f"Anon/Service REST failed svc:{code_svc} anon:{code_anon}", "FAIL")
    results.append(("Anon vs Service REST", False))
    return False


def test_double_supersede(jwt_captain: str, cert_id: str) -> bool:
    print("\n=== TEST: Double Supersede ===")
    code, _ = api_call("POST", "/v1/actions/execute", jwt_captain, {
        "action": "supersede_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"certificate_id": cert_id, "domain": "vessel", "signature": "again"}
    })
    if code in (400, 409):
        log("Double supersede rejected: PASS", "PASS")
        results.append(("Double supersede", True))
        return True
    log(f"Expected 400/409, got {code}", "FAIL")
    results.append(("Double supersede", False))
    return False


def test_update_nonexistent(jwt_hod: str) -> bool:
    print("\n=== TEST: Update Non-Existent ===")
    code, _ = api_call("POST", "/v1/actions/execute", jwt_hod, {
        "action": "update_certificate",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"certificate_id": "00000000-0000-0000-0000-000000000000", "domain": "vessel", "certificate_name": "Nope"}
    })
    if code == 404:
        log("Update non-existent: PASS", "PASS")
        results.append(("Update non-existent", True))
        return True
    log(f"Expected 404, got {code}", "FAIL")
    results.append(("Update non-existent", False))
    return False


def test_audit_content(cert_id: str) -> bool:
    print("\n=== TEST: Audit Content ===")
    params = {"select": "action,signature", "entity_id": f"eq.{cert_id}", "order": "created_at.desc"}
    code, data = tenant_rest("GET", "/rest/v1/pms_audit_log", params=params)
    if code != 200 or not isinstance(data, list) or not data:
        log(f"Audit fetch failed: {code}", "FAIL")
        results.append(("Audit content", False))
        return False
    ok_unsigned = any(row.get("action") in ("create_vessel_certificate", "update_certificate", "link_document") and row.get("signature") == {} for row in data)
    ok_signed = any(row.get("action") == "supersede_certificate" and isinstance(row.get("signature"), dict) and row.get("signature") != {} for row in data)
    if ok_unsigned and ok_signed:
        log("Audit signature content: PASS", "PASS")
        results.append(("Audit content", True))
        return True
    log("Audit signature content missing/incorrect", "FAIL")
    results.append(("Audit content", False))
    return False


def test_action_list_hod_sees_create(jwt_hod: str) -> bool:
    """HOD should see create_vessel_certificate in action list."""
    print("\n=== TEST: Action List - HOD Sees Create ===")
    code, body = api_call("GET", "/v1/actions/list?q=add+certificate&domain=certificates", jwt_hod)
    if code != 200:
        log(f"Action list failed: {code}", "FAIL")
        results.append(("HOD sees create action", False))
        return False
    actions = body.get("actions", [])
    action_ids = [a.get("action_id") for a in actions]
    if "create_vessel_certificate" in action_ids:
        log("HOD sees create_vessel_certificate: PASS", "PASS")
        results.append(("HOD sees create action", True))
        return True
    log(f"create_vessel_certificate not in actions: {action_ids}", "FAIL")
    results.append(("HOD sees create action", False))
    return False


def test_action_list_crew_no_mutations(jwt_crew: str) -> bool:
    """CREW should not see any MUTATE/SIGNED actions."""
    print("\n=== TEST: Action List - CREW No Mutations ===")
    code, body = api_call("GET", "/v1/actions/list?domain=certificates", jwt_crew)
    if code != 200:
        log(f"Action list failed: {code}", "FAIL")
        results.append(("CREW no mutations", False))
        return False
    actions = body.get("actions", [])
    mutations = [a for a in actions if a.get("variant") in ("MUTATE", "SIGNED")]
    if len(mutations) == 0:
        log("CREW sees no MUTATE actions: PASS", "PASS")
        results.append(("CREW no mutations", True))
        return True
    log(f"CREW saw {len(mutations)} mutation actions: {[a['action_id'] for a in mutations]}", "FAIL")
    results.append(("CREW no mutations", False))
    return False


def test_action_list_storage_options(jwt_hod: str) -> bool:
    """File-related actions should include storage_options."""
    print("\n=== TEST: Action List - Storage Options ===")
    code, body = api_call("GET", "/v1/actions/list?q=link+document&domain=certificates", jwt_hod)
    if code != 200:
        log(f"Action list failed: {code}", "FAIL")
        results.append(("Storage options", False))
        return False
    actions = body.get("actions", [])
    link_action = next((a for a in actions if a.get("action_id") == "link_document_to_certificate"), None)
    if not link_action:
        log("link_document_to_certificate not found", "FAIL")
        results.append(("Storage options", False))
        return False
    storage = link_action.get("storage_options")
    if storage and storage.get("bucket") == "documents" and storage.get("confirmation_required"):
        log("storage_options present and correct: PASS", "PASS")
        results.append(("Storage options", True))
        return True
    log(f"storage_options missing or incorrect: {storage}", "FAIL")
    results.append(("Storage options", False))
    return False


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p in results if p)
    failed = sum(1 for _, p in results if not p)

    for name, passed_test in results:
        icon = "✓" if passed_test else "✗"
        status = "PASS" if passed_test else "FAIL"
        print(f"  {icon} {name}: {status}")

    print("=" * 60)
    print(f"TOTAL: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


def main():
    print("=" * 60)
    print("CERTIFICATE RLS TEST SUITE")
    print("=" * 60)
    print(f"API_BASE: {API_BASE}")
    print(f"YACHT_ID: {YACHT_ID}")

    # Wait for API to be ready
    print("\nWaiting for API...")
    for i in range(30):
        try:
            resp = requests.get(f"{API_BASE}/health", timeout=5)
            if resp.status_code == 200:
                log("API healthy", "PASS")
                break
        except:
            pass
        time.sleep(1)
    else:
        log("API not ready after 30s", "FAIL")
        return 1

    # Get JWTs
    print("\n=== Authenticating Users ===")
    jwt_crew = get_jwt(USERS["crew"], TEST_PASSWORD)
    jwt_hod = get_jwt(USERS["hod"], TEST_PASSWORD)
    jwt_captain = get_jwt(USERS["captain"], TEST_PASSWORD)

    if not jwt_crew:
        log("Failed to get CREW JWT", "FAIL")
        return 1
    log("CREW JWT obtained", "PASS")

    if not jwt_hod:
        log("Failed to get HOD JWT", "FAIL")
        return 1
    log("HOD JWT obtained", "PASS")

    if not jwt_captain:
        log("Failed to get CAPTAIN JWT", "FAIL")
        return 1
    log("CAPTAIN JWT obtained", "PASS")

    # Run tests
    role_pass, cert_id = test_role_denial(jwt_crew, jwt_hod)

    if cert_id:
        test_supersede_requires_signature(jwt_hod, cert_id)
        test_hod_cannot_supersede(jwt_hod, cert_id)
        test_crew_cannot_supersede(jwt_crew, cert_id)
        test_update_ok(jwt_hod, cert_id)
        test_reads(jwt_hod, cert_id)
        test_link_document(jwt_hod, cert_id)
        test_link_document_invalid(jwt_hod, cert_id)
        test_date_validation(jwt_hod, cert_id)
        # Captain supersede signed
        if test_captain_supersede(jwt_captain, cert_id):
            test_double_supersede(jwt_captain, cert_id)
        test_audit_content(cert_id)

    test_duplicate_certificate_number(jwt_hod)
    test_anon_vs_service_rest()

    # Action list tests
    test_action_list_hod_sees_create(jwt_hod)
    test_action_list_crew_no_mutations(jwt_crew)
    test_action_list_storage_options(jwt_hod)

    # Summary
    all_pass = print_summary()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
