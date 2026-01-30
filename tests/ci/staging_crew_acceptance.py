#!/usr/bin/env python3
"""
Staging Crew Acceptance - Crew Lens v2
=======================================
Purpose: Minimal, fast checks in staging (real JWTs) to gate merges.

This workflow proves:
- Staging uses the same role/RLS semantics as Docker
- Client error mapping is correct (e.g., invalid user_id → 404, not 500)
- Simple positive flows succeed (e.g., assign_role → 200)
- Audit trail is correctly written for mutations
- JWT-derived context (yacht_id, role) works

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

def tenant_rest(method, path, params=None, body=None):
    headers = {"apikey": TENANT_SVC, "Content-Type":"application/json", "Prefer":"return=representation", "Authorization": f"Bearer {TENANT_SVC}"}
    url = f"{TENANT_URL}{path}"
    if method == 'GET':
        return SESSION.get(url, headers=headers, params=params or {})
    return SESSION.post(url, headers=headers, params=params or {}, json=body or {})

def get_user_id_from_jwt(jwt):
    """Extract user_id from JWT by calling view_my_profile."""
    r = call_api(jwt, 'POST', '/v1/actions/execute', {
        'action': 'view_my_profile',
        'context': {'yacht_id': YACHT_ID},
        'payload': {}
    }, expect=200)
    # ResponseBuilder format: {"success": true, "data": {"profile": {...}}, ...}
    data = r.json().get('data', {})
    profile = data.get('profile', {})
    return profile.get('id')

def get_audit_count_for_action(action_name):
    """Query audit log for specific action count."""
    r = tenant_rest('GET', '/rest/v1/pms_audit_log', params={
        'yacht_id': f'eq.{YACHT_ID}',
        'action': f'eq.{action_name}',
        'select': 'id'
    })
    if r.status_code == 200:
        return len(r.json())
    return 0

def main():
    print("=" * 80)
    print("Staging Crew Acceptance - Crew Lens v2")
    print("=" * 80)

    if not all([API_BASE, MASTER_URL, MASTER_ANON, MASTER_SVC, TENANT_URL, TENANT_SVC, YACHT_ID, PASSWORD]):
        fail("Missing required env vars for staging acceptance")

    # Prepare users or create if needed
    emails = {}
    jwts = {}
    user_ids = {}

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
        user_ids = ids
    else:
        emails = {'crew': CREW_EMAIL, 'hod': HOD_EMAIL, 'captain': CAPTAIN_EMAIL}

    # Authenticate
    jwts['crew'] = login(emails['crew'], PASSWORD); ok("CREW JWT obtained")
    jwts['hod'] = login(emails['hod'], PASSWORD); ok("HOD JWT obtained")
    jwts['captain'] = login(emails['captain'], PASSWORD); ok("CAPTAIN JWT obtained")

    # Get user IDs from JWTs
    if not CREATE_USERS:
        user_ids['crew'] = get_user_id_from_jwt(jwts['crew'])
        user_ids['hod'] = get_user_id_from_jwt(jwts['hod'])
        user_ids['captain'] = get_user_id_from_jwt(jwts['captain'])

    ok(f"Crew user_id: {user_ids['crew']}")
    ok(f"HOD user_id: {user_ids['hod']}")

    # ==========================================================================
    # TEST 1: Invalid profile id returns 404
    # ==========================================================================
    fake_user_id = '00000000-0000-0000-0000-000000000000'
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'view_crew_member_details',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'user_id': fake_user_id}
    }, expect=[400, 404])
    ok("Invalid user_id rejected (404)")

    # ==========================================================================
    # TEST 2: Crew can view own profile (200)
    # ==========================================================================
    resp = call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
        'action': 'view_my_profile',
        'context': {'yacht_id': YACHT_ID},
        'payload': {}
    }, expect=200)
    # ResponseBuilder format: {"success": true, "data": {"profile": {...}}, ...}
    data = resp.json().get('data', {})
    profile = data.get('profile')
    if not profile:
        fail("view_my_profile did not return profile")
    ok("CREW can view own profile (200)")

    # ==========================================================================
    # TEST 3: Crew cannot list all crew members (403)
    # ==========================================================================
    call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
        'action': 'list_crew_members',
        'context': {'yacht_id': YACHT_ID},
        'payload': {}
    }, expect=403)
    ok("CREW cannot list_crew_members (403)")

    # ==========================================================================
    # TEST 4: HOD can list all crew members (200)
    # ==========================================================================
    resp = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'list_crew_members',
        'context': {'yacht_id': YACHT_ID},
        'payload': {}
    }, expect=200)
    # ResponseBuilder format: {"success": true, "data": {"crew_members": [...]}, ...}
    data = resp.json().get('data', {})
    crew_members = data.get('crew_members', [])
    if len(crew_members) == 0:
        fail("HOD should see crew members in list")
    ok(f"HOD can list_crew_members (found {len(crew_members)} crew)")

    # ==========================================================================
    # TEST 5: HOD can assign role (200 or 409 if user already has role)
    # ==========================================================================
    audit_before = get_audit_count_for_action('assign_role')

    # First, try to revoke any existing roles
    resp_details = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'view_crew_member_details',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'user_id': user_ids['crew']}
    }, expect=200)
    data_details = resp_details.json().get('data', {})
    existing_roles = data_details.get('roles', [])
    for role in existing_roles:
        if role.get('is_active'):
            call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
                'action': 'revoke_role',
                'context': {'yacht_id': YACHT_ID},
                'payload': {
                    'role_id': role['id'],
                    'reason': 'CI test setup - clearing existing role'
                }
            }, expect=200)

    # Now assign the role
    resp = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'assign_role',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'user_id': user_ids['crew'],
            'role': 'eto'
        }
    }, expect=200)
    # ResponseBuilder format: {"success": true, "data": {"role_id": "..."}, ...}
    data = resp.json().get('data', {})
    role_id = data.get('role_id')
    if not role_id:
        fail(f"assign_role did not return role_id: {resp.text}")
    ok(f"HOD assign_role returned 200 (role_id={role_id})")

    # ==========================================================================
    # TEST 6: Verify audit log write for assign_role
    # ==========================================================================
    audit_after = get_audit_count_for_action('assign_role')
    if audit_after <= audit_before:
        fail(f"Audit log not written for assign_role (before={audit_before}, after={audit_after})")
    ok("Audit log written for assign_role")

    # ==========================================================================
    # TEST 7: HOD cannot assign duplicate role (409)
    # ==========================================================================
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'assign_role',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'user_id': user_ids['crew'],
            'role': 'eto'  # Already assigned
        }
    }, expect=409)
    ok("Duplicate assign_role rejected (409)")

    # ==========================================================================
    # TEST 8: HOD can revoke role (200)
    # ==========================================================================
    audit_before = get_audit_count_for_action('revoke_role')

    resp = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'revoke_role',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'role_id': role_id,
            'reason': 'CI test cleanup'
        }
    }, expect=200)
    ok("HOD revoke_role returned 200")

    # Verify audit log write
    audit_after = get_audit_count_for_action('revoke_role')
    if audit_after <= audit_before:
        fail(f"Audit log not written for revoke_role (before={audit_before}, after={audit_after})")
    ok("Audit log written for revoke_role")

    # ==========================================================================
    # TEST 9: Verify soft delete (is_active=false, not deleted)
    # ==========================================================================
    r = tenant_rest('GET', '/rest/v1/auth_users_roles', params={
        'id': f'eq.{role_id}',
        'select': 'id,is_active,valid_until'
    })
    if r.status_code != 200:
        fail(f"Could not query role: {r.status_code}")
    roles = r.json()
    if len(roles) == 0:
        fail("Revoked role was deleted (should be soft-deleted with is_active=false)")
    if roles[0].get('is_active') != False:
        fail(f"Revoked role is_active should be false, got {roles[0].get('is_active')}")
    ok("Revoke uses soft delete (is_active=false)")

    # ==========================================================================
    # TEST 10: Action list - HOD sees mutation actions
    # ==========================================================================
    resp = call_api(jwts['hod'], 'GET', '/v1/actions/list?domain=crew', expect=200)
    actions = resp.json().get('actions', [])
    action_ids = [a.get('action_id') for a in actions]
    expected_hod_actions = ['list_crew_members', 'assign_role', 'revoke_role']
    found = [a for a in expected_hod_actions if a in action_ids]
    if len(found) != len(expected_hod_actions):
        fail(f"HOD should see {expected_hod_actions}, found {found}")
    ok("HOD sees mutation actions in crew domain")

    # ==========================================================================
    # TEST 11: Action list - CREW sees no HOD actions
    # ==========================================================================
    resp = call_api(jwts['crew'], 'GET', '/v1/actions/list?domain=crew', expect=200)
    actions = resp.json().get('actions', [])
    hod_only_actions = ['list_crew_members', 'assign_role', 'revoke_role', 'update_crew_member_status']
    found_hod_actions = [a.get('action_id') for a in actions if a.get('action_id') in hod_only_actions]
    if len(found_hod_actions) > 0:
        fail(f"CREW should not see HOD actions: {found_hod_actions}")
    ok("CREW sees no HOD/Captain actions in crew domain")

    # ==========================================================================
    # TEST 12: Captain can update crew status (200)
    # ==========================================================================
    resp = call_api(jwts['captain'], 'POST', '/v1/actions/execute', {
        'action': 'update_crew_member_status',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'user_id': user_ids['crew'],
            'is_active': False,
            'reason': 'CI test'
        }
    }, expect=200)
    ok("CAPTAIN can update_crew_member_status (200)")

    # Restore status
    call_api(jwts['captain'], 'POST', '/v1/actions/execute', {
        'action': 'update_crew_member_status',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'user_id': user_ids['crew'],
            'is_active': True
        }
    }, expect=200)
    ok("Crew status restored")

    print("\n" + "=" * 80)
    print("✓ All Crew Lens v2 Staging Acceptance Tests Passed")
    print("=" * 80)

if __name__ == '__main__':
    main()
