#!/usr/bin/env python3
"""
Staging Certificates Acceptance

Runs against a live API using real JWTs from MASTER.

STABLE-USER MODE (default, recommended):
  - Set CREATE_USERS='false' in workflow
  - Provide STAGING_CREW_EMAIL, STAGING_HOD_EMAIL, STAGING_CAPTAIN_EMAIL secrets
  - Uses pre-provisioned accounts: crew.test@, hod.test@, captain.test@alex-short.com
  - No DB pollution from timestamped test users

AUTO-PROVISION MODE (first-time setup only):
  - Set CREATE_USERS='true' in workflow
  - Creates timestamped users (crew.ci+{ts}@, hod.ci+{ts}@, captain.ci+{ts}@)
  - Use sparingly; clean up after to avoid DB pollution
"""
import os, sys, time, json, uuid
import requests

API_BASE = os.environ.get('API_BASE')
MASTER_URL = os.environ.get('MASTER_SUPABASE_URL')
MASTER_ANON = os.environ.get('MASTER_SUPABASE_ANON_KEY')
MASTER_SVC = os.environ.get('MASTER_SUPABASE_SERVICE_KEY')
TENANT_URL = os.environ.get('TENANT_SUPABASE_URL')
TENANT_SVC = os.environ.get('TENANT_SUPABASE_SERVICE_KEY')
YACHT_ID = os.environ.get('YACHT_ID')

CREW_EMAIL = os.environ.get('STAGING_CREW_EMAIL')
HOD_EMAIL = os.environ.get('STAGING_HOD_EMAIL')
CAPTAIN_EMAIL = os.environ.get('STAGING_CAPTAIN_EMAIL')
PASSWORD = os.environ.get('STAGING_USER_PASSWORD')
CREATE_USERS = (os.environ.get('CREATE_USERS', 'false').lower() == 'true')

SESSION = requests.Session()

def fail(msg):
    print(f"✗ {msg}")
    sys.exit(1)

def ok(msg):
    print(f"✓ {msg}")

def admin_create_user(email, password):
    r = SESSION.post(f"{MASTER_URL}/auth/v1/admin/users",
                     headers={"apikey": MASTER_SVC, "Authorization": f"Bearer {MASTER_SVC}", "Content-Type":"application/json"},
                     json={"email": email, "password": password, "email_confirm": True})
    if r.status_code not in (200, 201):
        fail(f"Admin create user failed {r.status_code}: {r.text}")
    return r.json().get('id')

def map_user_to_tenant(user_id, email, role):
    # MASTER mapping
    body = {"id": user_id, "email": email, "yacht_id": YACHT_ID, "display_name": "CI User", "role": role, "status": "active", "email_verified": True}
    r = SESSION.post(f"{MASTER_URL}/rest/v1/user_accounts",
                     headers={"apikey": MASTER_SVC, "Authorization": f"Bearer {MASTER_SVC}", "Content-Type":"application/json", "Prefer": "return=representation"},
                     json=body)
    if r.status_code not in (200, 201):
        fail(f"MASTER user_accounts map failed {r.status_code}: {r.text}")
    # TENANT profile/role
    SESSION.post(f"{TENANT_URL}/rest/v1/auth_users_profiles",
                 headers={"apikey": TENANT_SVC, "Authorization": f"Bearer {TENANT_SVC}", "Content-Type":"application/json", "Prefer": "return=representation"},
                 json={"id": user_id, "yacht_id": YACHT_ID, "email": email, "name": "CI User", "is_active": True})
    SESSION.post(f"{TENANT_URL}/rest/v1/auth_users_roles",
                 headers={"apikey": TENANT_SVC, "Authorization": f"Bearer {TENANT_SVC}", "Content-Type":"application/json", "Prefer": "return=representation"},
                 json={"user_id": user_id, "yacht_id": YACHT_ID, "role": role, "is_active": True})

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

def tenant_rest(method, path, params=None, body=None, anon=False):
    headers = {"apikey": (MASTER_ANON if anon else TENANT_SVC), "Content-Type":"application/json", "Prefer":"return=representation"}
    url = f"{TENANT_URL}{path}"
    if method == 'GET':
        return SESSION.get(url, headers=headers, params=params or {})
    return SESSION.post(url, headers=headers, params=params or {}, json=body or {})

def main():
    if not all([API_BASE, MASTER_URL, MASTER_ANON, MASTER_SVC, TENANT_URL, TENANT_SVC, YACHT_ID, PASSWORD]):
        fail("Missing required env vars for staging acceptance")

    # Prepare users or create if needed
    emails = {}
    jwts = {}
    if CREATE_USERS or not all([CREW_EMAIL, HOD_EMAIL, CAPTAIN_EMAIL]):
        ts = int(time.time())
        emails = {
            'crew': f"crew.ci+{ts}@alex-short.com",
            'hod': f"hod.ci+{ts}@alex-short.com",
            'captain': f"captain.ci+{ts}@alex-short.com",
        }
        ids = {
            'crew': admin_create_user(emails['crew'], PASSWORD),
            'hod': admin_create_user(emails['hod'], PASSWORD),
            'captain': admin_create_user(emails['captain'], PASSWORD),
        }
        map_user_to_tenant(ids['crew'], emails['crew'], 'crew')
        map_user_to_tenant(ids['hod'], emails['hod'], 'chief_engineer')
        map_user_to_tenant(ids['captain'], emails['captain'], 'captain')
    else:
        emails = {'crew': CREW_EMAIL, 'hod': HOD_EMAIL, 'captain': CAPTAIN_EMAIL}

    jwts['crew'] = login(emails['crew'], PASSWORD); ok("CREW JWT obtained")
    jwts['hod'] = login(emails['hod'], PASSWORD); ok("HOD JWT obtained")
    jwts['captain'] = login(emails['captain'], PASSWORD); ok("CAPTAIN JWT obtained")

    # HOD create cert
    create = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'create_vessel_certificate',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'certificate_type': 'FLAG',
            'certificate_name': 'CI Cert',
            'certificate_number': f'CI-{int(time.time())}',
            'issuing_authority': 'Test',
            'expiry_date': '2030-01-01'
        }
    }, expect=200)
    cert_id = (create.json().get('result') or {}).get('certificate_id') or create.json().get('certificate_id')
    if not cert_id:
        fail(f"Missing certificate_id in create response: {create.text}")
    ok(f"Created cert {cert_id}")

    # Invalid doc link → 400/404
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'link_document_to_certificate',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'certificate_id': cert_id, 'domain': 'vessel', 'document_id': '00000000-0000-0000-0000-000000000000'}
    }, expect=[400,404])
    ok("Invalid doc link rejected (400/404)")

    # Update cert (audit insert) → 200
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'update_certificate',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'certificate_id': cert_id, 'domain': 'vessel', 'certificate_name': 'CI Update'}
    }, expect=200)
    ok("Update returned 200 (no audit 409)")

    print("\nAll required staging re-checks passed.")

if __name__ == '__main__':
    main()

