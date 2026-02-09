#!/usr/bin/env python3
"""
Inventory RLS Test Suite for Docker
===================================
Purpose: Exercise role/RLS guarantees and error mapping for Inventory lens actions.

Run with: docker compose -f docker-compose.test.yml up --build
"""
import os
import time
import requests
from typing import Optional, Dict, Any, Tuple

API_BASE = os.getenv("API_BASE", "http://api:8000")
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")
TENANT_SUPABASE_URL = os.getenv("TENANT_SUPABASE_URL")
TENANT_SUPABASE_SERVICE_KEY = os.getenv("TENANT_SUPABASE_SERVICE_KEY")
YACHT_ID = os.getenv("YACHT_ID")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "Password2!")

USERS = {
    "crew": os.getenv("CREW_EMAIL", "crew.test@alex-short.com"),
    "hod": os.getenv("HOD_EMAIL", "hod.test@alex-short.com"),
}

def log(msg: str, level: str = "INFO"):
    icon = {"INFO": "ℹ️", "PASS": "✓", "FAIL": "✗", "WARN": "⚠️"}.get(level, "")
    print(f"  {icon} {msg}")

def get_jwt(email: str, password: str) -> Optional[str]:
    url = f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": MASTER_SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json={"email": email, "password": password}, timeout=10)
        if r.status_code == 200:
            return r.json().get("access_token")
        log(f"Auth failed for {email}: {r.status_code}", "WARN")
        return None
    except Exception as e:
        log(f"Auth error: {e}", "WARN")
        return None

def api_call(method: str, path: str, jwt: str, payload: Dict[str, Any] | None = None) -> Tuple[int, Dict[str, Any]]:
    url = f"{API_BASE}{path}"
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=30)
    else:
        r = requests.post(url, headers=headers, json=payload or {}, timeout=30)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:500]}
    return r.status_code, body

def tenant_rest(method: str, path: str, params: Dict[str, Any] | None = None, body: Dict[str, Any] | None = None):
    url = f"{TENANT_SUPABASE_URL}{path}"
    headers = {
        "apikey": TENANT_SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {TENANT_SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if method == "GET":
        return requests.get(url, headers=headers, params=params or {}, timeout=30)
    return requests.post(url, headers=headers, params=params or {}, json=body or {}, timeout=30)

def main():
    print("\n=== Inventory RLS Tests ===")
    crew_jwt = get_jwt(USERS["crew"], TEST_PASSWORD)
    hod_jwt = get_jwt(USERS["hod"], TEST_PASSWORD)
    if not (crew_jwt and hod_jwt and YACHT_ID):
        log("Missing JWTs or YACHT_ID", "FAIL"); exit(1)

    # Action list: HOD sees inventory actions
    code, body = api_call("GET", f"/v1/actions/list?q=check+stock&domain=parts", hod_jwt)
    if code != 200:
        log(f"Action list (HOD) failed: {code}", "FAIL"); exit(1)
    ids = [a.get("action_id") for a in body.get("actions", [])]
    if "check_stock_level" in ids:
        log("HOD sees check_stock_level in action list", "PASS")
    else:
        log(f"HOD action list missing check_stock_level: {ids}", "FAIL"); exit(1)

    # Action list: CREW must not see MUTATE log_part_usage
    code, body = api_call("GET", f"/v1/actions/list?q=log+part&domain=parts", crew_jwt)
    if code != 200:
        log(f"Action list (CREW) failed: {code}", "FAIL"); exit(1)
    ids = [a.get("action_id") for a in body.get("actions", [])]
    if "log_part_usage" in ids:
        # If present, ensure variant is not MUTATE (should be gated out entirely)
        mut = [a for a in body.get("actions", []) if a.get("action_id") == "log_part_usage" and a.get("variant") in ("MUTATE","SIGNED")]
        if mut:
            log("CREW should not see log_part_usage mutation", "FAIL"); exit(1)
    log("CREW sees no mutation action log_part_usage", "PASS")

    # Invalid part_id → 404 (check_stock_level)
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "check_stock_level",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"part_id": "00000000-0000-0000-0000-000000000000"}
    })
    if code in (400, 404):
        log("Invalid part_id rejected for check_stock_level", "PASS")
    else:
        log(f"Invalid part expected 400/404, got {code}", "FAIL"); exit(1)

    # Insert a test part via tenant REST with quantity_on_hand = 5
    part_number = f"TEST-INV-{int(time.time())}"
    r = tenant_rest("POST", "/rest/v1/pms_parts", body={
        "yacht_id": YACHT_ID,
        "name": "Test Part",
        "part_number": part_number,
        "unit": "ea",
        "quantity_on_hand": 5,
        "minimum_quantity": 1,
    })
    if r.status_code not in (200, 201):
        log(f"Failed to insert part via REST: {r.status_code} {r.text}", "FAIL"); exit(1)
    part_id = (r.json()[0] if isinstance(r.json(), list) else r.json()).get("id")

    # HOD can log_part_usage (OK path)
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "log_part_usage",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"part_id": part_id, "quantity": 1, "usage_reason": "maintenance"}
    })
    if code == 200 and body.get("status") == "success":
        log("HOD log_part_usage allowed", "PASS")
    else:
        log(f"HOD log_part_usage expected 200, got {code} {body}", "FAIL"); exit(1)

    # Insufficient stock → 400 (INSUFFICIENT_STOCK)
    code, body = api_call("POST", "/v1/actions/execute", hod_jwt, {
        "action": "log_part_usage",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"part_id": part_id, "quantity": 9999, "usage_reason": "maintenance"}
    })
    if code == 400 and (body.get("error_code") == "INSUFFICIENT_STOCK" or body.get("error", {}).get("error_code") == "INSUFFICIENT_STOCK"):
        log("Insufficient stock rejected with 400", "PASS")
    else:
        log(f"Expected 400/INSUFFICIENT_STOCK, got {code} {body}", "FAIL"); exit(1)

    # CREW cannot mutate (log_part_usage) → 403
    code, body = api_call("POST", "/v1/actions/execute", crew_jwt, {
        "action": "log_part_usage",
        "context": {"yacht_id": YACHT_ID},
        "payload": {"part_id": part_id, "quantity": 1, "usage_reason": "maintenance"}
    })
    if code == 403:
        log("CREW mutation denied (log_part_usage)", "PASS")
    else:
        log(f"CREW mutation expected 403, got {code}", "FAIL"); exit(1)

    # Anon vs Service REST invariant on pms_parts
    r_svc = tenant_rest("GET", "/rest/v1/pms_parts", params={"select": "id", "limit": 1})
    r_anon = requests.get(f"{TENANT_SUPABASE_URL}/rest/v1/pms_parts", headers={"apikey": MASTER_SUPABASE_ANON_KEY}, params={"select": "id", "limit": 1})
    if r_svc.status_code == 200 and ((r_anon.status_code in (401,403)) or (r_anon.status_code == 200 and r_anon.json() == [])):
        log("Anon vs Service REST invariant holds", "PASS")
    else:
        log(f"Anon/Service REST failed svc:{r_svc.status_code} anon:{r_anon.status_code}", "FAIL"); exit(1)

    print("\nAll inventory RLS tests passed.")

if __name__ == "__main__":
    main()

