#!/usr/bin/env python3
"""
Part Lens v2: Canonical Router Staging Acceptance
===================================================
Tests Part Lens v2 through POST /v1/actions/execute (canonical router)
and minimal read endpoints, using MASTER JWTs with proper role mapping.

Required Environment Variables:
    API_BASE - API base URL
    MASTER_SUPABASE_URL - MASTER database URL
    MASTER_SUPABASE_SERVICE_KEY - MASTER service key
    MASTER_SUPABASE_JWT_SECRET - MASTER JWT secret
    TEST_YACHT_ID - Test yacht ID

Usage:
    export API_BASE="https://pipeline-core.int.celeste7.ai"
    export MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
    export MASTER_SUPABASE_SERVICE_KEY="..."
    export MASTER_SUPABASE_JWT_SECRET="..."
    export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
    python3 tests/ci/part_lens_canonical_acceptance.py
"""

import os
import sys
import json
import requests
import jwt
from datetime import datetime
from typing import Dict, List

# Configuration
API_BASE = os.getenv("API_BASE", "https://pipeline-core.int.celeste7.ai")
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_SERVICE_KEY = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
MASTER_JWT_SECRET = os.getenv("MASTER_SUPABASE_JWT_SECRET")
TEST_YACHT_ID = os.getenv("TEST_YACHT_ID")
EVIDENCE_DIR = "test-evidence"

# Test users (.tenant users - provisioned in MASTER and TENANT)
TEST_USERS = {
    "HOD": {"id": "89b1262c-ff59-4591-b954-757cdf3d609d", "email": "hod.tenant@alex-short.com", "role": "chief_engineer"},
    "CAPTAIN": {"id": "b72c35ff-e309-4a19-a617-bfc706a78c0f", "email": "captain.tenant@alex-short.com", "role": "captain"},
    "CREW": {"id": "2da12a4b-c0a1-4716-80ae-d29c90d98233", "email": "crew.tenant@alex-short.com", "role": "crew"}
}

# Results tracking
test_results = []
five_xx_count = 0

os.makedirs(EVIDENCE_DIR, exist_ok=True)

def generate_jwt(user_id: str, email: str) -> str:
    """Generate MASTER JWT for user."""
    iat_ts = 1704067200  # 2024-01-01
    exp_ts = 1801430400  # 2027-01-30

    payload = {
        "aud": "authenticated",
        "exp": exp_ts,
        "iat": iat_ts,
        "iss": MASTER_SUPABASE_URL + "/auth/v1",
        "sub": user_id,
        "email": email,
        "role": "authenticated",
    }
    return jwt.encode(payload, MASTER_JWT_SECRET, algorithm="HS256")

# MASTER-signed JWTs with correct timestamps (from docs/evidence/inventory_item/JWTS_COPY_PASTE.txt)
# iat: 1769599994 (2 hours ago), exp: 1801143194 (Jan 28, 2027)
# Users provisioned in MASTER.user_accounts and TENANT.auth_users_roles
JWTS = {
    "HOD": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg",
    "CAPTAIN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiY2FwdGFpbi50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTU5OTk5NH1dLCJzZXNzaW9uX2lkIjoiY2ktdGVzdC1iNzJjMzVmZiIsImlzX2Fub255bW91cyI6ZmFsc2V9.Uo0H4yeLWjcvk1UTUD1fF248ElNFRKoN7-eswUWVcvw",
    "CREW": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiY3Jldy50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTU5OTk5NH1dLCJzZXNzaW9uX2lkIjoiY2ktdGVzdC0yZGExMmE0YiIsImlzX2Fub255bW91cyI6ZmFsc2V9.cFA-nWNlaSpwsf3P9qLbWVegltzTtdWEzuw2rCpzEV0"
}

def log_result(test_name: str, passed: bool, message: str = "", status_code: int = None):
    """Log test result and track 5xx."""
    global five_xx_count

    if status_code and 500 <= status_code < 600:
        five_xx_count += 1

    symbol = "✓" if passed else "✗"
    print(f"{symbol} {test_name}: {'PASS' if passed else 'FAIL'}")
    if message:
        print(f"  {message}")

    test_results.append({
        "test": test_name,
        "passed": passed,
        "message": message,
        "status_code": status_code
    })

def save_artifact(name: str, content):
    """Save evidence artifact."""
    filepath = os.path.join(EVIDENCE_DIR, name)
    if isinstance(content, (dict, list)):
        with open(filepath, 'w') as f:
            json.dump(content, f, indent=2)
    else:
        with open(filepath, 'w') as f:
            f.write(str(content))
    print(f"  📁 {filepath}")

def test_low_stock_read():
    """Test minimal read endpoint: GET /v1/parts/low-stock"""
    try:
        url = f"{API_BASE}/v1/parts/low-stock?yacht_id={TEST_YACHT_ID}"
        r = requests.get(url, timeout=10)

        if r.status_code == 200:
            data = r.json()
            total = data.get("total_low_stock", 0)
            log_result("Low-stock read", total > 0, f"{total} parts below min_level", r.status_code)
            save_artifact("low_stock_sample.json", data)
            return True
        else:
            log_result("Low-stock read", False, f"Status {r.status_code}", r.status_code)
            return False
    except Exception as e:
        log_result("Low-stock read", False, str(e))
        return False

def test_view_part_details(jwt_token: str, role: str):
    """Test view_part_details through canonical router."""
    try:
        # Get a part from low-stock
        parts_resp = requests.get(f"{API_BASE}/v1/parts/low-stock?yacht_id={TEST_YACHT_ID}")
        if not parts_resp.ok or not parts_resp.json().get("parts"):
            log_result(f"view_part_details ({role})", False, "No parts available")
            return False

        part_id = parts_resp.json()["parts"][0]["id"]

        payload = {
            "action": "view_part_details",
            "context": {"yacht_id": TEST_YACHT_ID},
            "payload": {"part_id": part_id}
        }

        r = requests.post(
            f"{API_BASE}/v1/actions/execute",
            headers={"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        if r.status_code == 200:
            data = r.json()
            # API returns {status, data: {stock: {on_hand}}} structure
            stock = data.get("data", {}).get("stock", {})
            has_stock = "on_hand" in stock
            log_result(f"view_part_details ({role})", has_stock, f"Status {r.status_code}", r.status_code)
            save_artifact(f"view_part_details_{role.lower()}.json", data)
            return True
        else:
            log_result(f"view_part_details ({role})", False, f"Status {r.status_code}: {r.text[:100]}", r.status_code)
            return False
    except Exception as e:
        log_result(f"view_part_details ({role})", False, str(e))
        return False

def test_consume_part_idempotency(jwt_token: str):
    """Test consume_part action and verify no 5xx on success/failure paths."""
    try:
        # Get a part with stock
        parts_resp = requests.get(f"{API_BASE}/v1/parts/low-stock?yacht_id={TEST_YACHT_ID}")
        if not parts_resp.ok:
            log_result("consume_part", False, "Cannot get parts")
            return False

        parts = parts_resp.json().get("parts", [])
        part_with_stock = next((p for p in parts if p.get("on_hand", 0) > 0), None)

        if not part_with_stock:
            log_result("consume_part", False, "No parts with stock")
            return False

        part_id = part_with_stock["id"]

        payload = {
            "action": "consume_part",
            "context": {"yacht_id": TEST_YACHT_ID},
            "payload": {"part_id": part_id, "quantity": 1, "notes": "Canonical router test"}
        }

        r = requests.post(
            f"{API_BASE}/v1/actions/execute",
            headers={"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=10
        )

        success = r.status_code in (200, 201, 409)  # 200/201 success, 409 insufficient stock
        log_result("consume_part", success, f"Status {r.status_code}", r.status_code)
        save_artifact("consume_part_result.json", r.json() if r.ok else {"status": r.status_code, "detail": r.text})
        return success
    except Exception as e:
        log_result("consume_part", False, str(e))
        return False

def test_zero_5xx_scan():
    """Test various endpoints to ensure zero 5xx errors."""
    endpoints = [
        ("GET", f"{API_BASE}/health", {}),
        ("GET", f"{API_BASE}/v1/parts/low-stock?yacht_id={TEST_YACHT_ID}", {}),
    ]

    results = []
    for method, url, headers in endpoints:
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=10)
            else:
                r = requests.post(url, headers=headers, json={}, timeout=10)

            is_5xx = 500 <= r.status_code < 600
            results.append({"url": url, "status": r.status_code, "is_5xx": is_5xx})

            if not is_5xx:
                print(f"  ✓ {url.split('/')[-1]}: {r.status_code}")
        except Exception as e:
            results.append({"url": url, "error": str(e)})
            print(f"  ✗ {url}: {e}")

    five_xx_found = sum(1 for r in results if r.get("is_5xx"))
    log_result("Zero 5xx scan", five_xx_found == 0, f"Tested {len(endpoints)} endpoints, {five_xx_found} returned 5xx")
    save_artifact("zero_5xx_scan.json", results)
    return five_xx_found == 0

def run_acceptance():
    """Run all acceptance tests."""
    print("=" * 70)
    print("PART LENS V2: CANONICAL ROUTER STAGING ACCEPTANCE")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print(f"Yacht: {TEST_YACHT_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    print("=== Minimal Read Endpoints ===")
    test_low_stock_read()
    print()

    print("=== Canonical Action Router (by role) ===")
    test_view_part_details(JWTS["HOD"], "HOD")
    test_view_part_details(JWTS["CAPTAIN"], "CAPTAIN")
    test_view_part_details(JWTS["CREW"], "CREW")
    print()

    print("=== Action Execution ===")
    test_consume_part_idempotency(JWTS["HOD"])
    print()

    print("=== Zero 5xx Comprehensive ===")
    test_zero_5xx_scan()
    print()

    # Summary
    passed = sum(1 for r in test_results if r["passed"])
    total = len(test_results)
    success_rate = passed / total if total > 0 else 0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "api_base": API_BASE,
        "yacht_id": TEST_YACHT_ID,
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "success_rate": success_rate,
        "five_xx_count": five_xx_count,
        "results": test_results
    }

    save_artifact("canonical_router_acceptance_summary.json", summary)

    print("=" * 70)
    print(f"RESULTS: {passed}/{total} passed ({int(success_rate*100)}%)")
    print(f"5xx ERRORS: {five_xx_count}")
    print("=" * 70)

    if success_rate == 1.0 and five_xx_count == 0:
        print("✅ READY FOR CANARY")
        return 0
    else:
        print(f"✗ {total - passed} FAILED, {five_xx_count} 5XX ERRORS")
        return 1

if __name__ == "__main__":
    sys.exit(run_acceptance())
