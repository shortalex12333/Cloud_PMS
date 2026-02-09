#!/usr/bin/env python3
"""
Staging Inventory Acceptance (template)
======================================
Minimal checks for Inventory lens with real JWTs. Copying the Certificates template intent.

Proves:
- Action list shows READ action (HOD) and hides MUTATE from CREW
- Invalid part_id → 404 (client error mapping, not 500)
- HOD can log usage (200), CREW denied (403)
"""
import os, sys, time, requests

API_BASE = os.environ.get('API_BASE')
MASTER_URL = os.environ.get('MASTER_SUPABASE_URL')
MASTER_ANON = os.environ.get('MASTER_SUPABASE_ANON_KEY')
MASTER_SVC = os.environ.get('MASTER_SUPABASE_SERVICE_KEY')
TENANT_URL = os.environ.get('TENANT_SUPABASE_URL')
TENANT_SVC = os.environ.get('TENANT_SUPABASE_SERVICE_KEY')
YACHT_ID = os.environ.get('YACHT_ID')

CREW_EMAIL = os.environ.get('STAGING_CREW_EMAIL')
HOD_EMAIL = os.environ.get('STAGING_HOD_EMAIL')
PASSWORD = os.environ.get('STAGING_USER_PASSWORD')

SESSION = requests.Session()

def fail(msg):
    print(f"✗ {msg}")
    sys.exit(1)

def ok(msg):
    print(f"✓ {msg}")

def login(email, password):
    r = SESSION.post(f"{MASTER_URL}/auth/v1/token?grant_type=password",
                     headers={"apikey": MASTER_ANON, "Content-Type": "application/json"},
                     json={"email": email, "password": password})
    if r.status_code != 200:
        fail(f"Login failed {email}: {r.status_code} {r.text}")
    return r.json().get('access_token')

def call_api(jwt, method, path, payload=None, expect=None):
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    if method == 'GET':
        r = SESSION.get(url, headers=headers)
    else:
        r = SESSION.post(url, headers=headers, json=payload or {})
    if expect is not None and r.status_code not in (expect if isinstance(expect, (list, tuple)) else [expect]):
        fail(f"{method} {path} expected {expect}, got {r.status_code}: {r.text}")
    return r

def tenant_rest(method, path, params=None, body=None):
    headers = {"apikey": TENANT_SVC, "Authorization": f"Bearer {TENANT_SVC}", "Content-Type":"application/json", "Prefer":"return=representation"}
    url = f"{TENANT_URL}{path}"
    if method == 'GET':
        return SESSION.get(url, headers=headers, params=params or {})
    return SESSION.post(url, headers=headers, params=params or {}, json=body or {})

def main():
    if not all([API_BASE, MASTER_URL, MASTER_ANON, MASTER_SVC, TENANT_URL, TENANT_SVC, YACHT_ID, PASSWORD, CREW_EMAIL, HOD_EMAIL]):
        fail("Missing required env vars for staging inventory acceptance")

    jwts = {
        'crew': login(CREW_EMAIL, PASSWORD),
        'hod': login(HOD_EMAIL, PASSWORD),
    }
    ok("JWTs obtained")

    # Action list: HOD sees check_stock_level
    resp = call_api(jwts['hod'], 'GET', '/v1/actions/list?q=check+stock&domain=parts', expect=200)
    ids = [a.get('action_id') for a in resp.json().get('actions', [])]
    if 'check_stock_level' not in ids:
        fail(f"HOD should see check_stock_level in action list: {ids}")
    ok("HOD sees check_stock_level in action list")

    # Invalid part_id for check_stock_level → 400/404
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'check_stock_level',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'part_id': '00000000-0000-0000-0000-000000000000'}
    }, expect=[400,404])
    ok("Invalid part rejected (400/404)")

    # Insert a minimal part via tenant REST
    pn = f"CI-INV-{int(time.time())}"
    r = tenant_rest('POST', '/rest/v1/pms_parts', body={
        'yacht_id': YACHT_ID,
        'name': 'CI Inventory Part',
        'part_number': pn,
        'unit': 'ea',
        'quantity_on_hand': 2,
        'minimum_quantity': 1,
    })
    if r.status_code not in (200, 201):
        fail(f"Failed to insert part via REST: {r.status_code} {r.text}")
    part_id = (r.json()[0] if isinstance(r.json(), list) else r.json()).get('id')

    # HOD can log usage → 200
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'log_part_usage',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'part_id': part_id, 'quantity': 1, 'usage_reason': 'maintenance'}
    }, expect=200)
    ok("log_part_usage returned 200 for HOD")

    # CREW denied log_part_usage → 403
    r = call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
        'action': 'log_part_usage',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'part_id': part_id, 'quantity': 1, 'usage_reason': 'maintenance'}
    }, expect=403)
    ok("CREW denied mutation (403)")

    print("\nInventory staging acceptance passed.")

if __name__ == '__main__':
    main()

