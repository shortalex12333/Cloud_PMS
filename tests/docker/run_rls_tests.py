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
YACHT_ID = os.getenv("YACHT_ID")
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
        test_crew_cannot_supersede(jwt_crew, cert_id)
        test_date_validation(jwt_hod, cert_id)

    test_duplicate_certificate_number(jwt_hod)

    # Summary
    all_pass = print_summary()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
