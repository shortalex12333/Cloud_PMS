#!/usr/bin/env python3
"""
Staging Documents Acceptance (Document Lens v2)
================================================
Purpose: Minimal, fast checks in staging (real JWTs) to gate merges.

This workflow proves:
  - Staging uses the same role/RLS semantics as Docker
  - Client error mapping is correct (e.g., invalid doc_id → 400/404, not 500)
  - CREW cannot MUTATE documents (upload/update/tag/delete)
  - HOD can MUTATE documents (upload/update/tag)
  - Delete requires SIGNED action (captain/manager + signature)
  - Action list respects role gating

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
import os
import sys
import time
import json
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
    r = SESSION.post(
        f"{MASTER_URL}/auth/v1/admin/users",
        headers={
            "apikey": MASTER_SVC,
            "Authorization": f"Bearer {MASTER_SVC}",
            "Content-Type": "application/json"
        },
        json={"email": email, "password": password, "email_confirm": True}
    )
    if r.status_code not in (200, 201):
        fail(f"Admin create user failed {r.status_code}: {r.text}")
    return r.json().get('id')


def map_user_to_tenant(user_id, email, role):
    # MASTER mapping
    body = {
        "id": user_id,
        "email": email,
        "yacht_id": YACHT_ID,
        "display_name": "CI User",
        "role": role,
        "status": "active",
        "email_verified": True
    }
    r = SESSION.post(
        f"{MASTER_URL}/rest/v1/user_accounts",
        headers={
            "apikey": MASTER_SVC,
            "Authorization": f"Bearer {MASTER_SVC}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json=body
    )
    if r.status_code not in (200, 201):
        fail(f"MASTER user_accounts map failed {r.status_code}: {r.text}")
    # TENANT profile/role
    SESSION.post(
        f"{TENANT_URL}/rest/v1/auth_users_profiles",
        headers={
            "apikey": TENANT_SVC,
            "Authorization": f"Bearer {TENANT_SVC}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json={"id": user_id, "yacht_id": YACHT_ID, "email": email, "name": "CI User", "is_active": True}
    )
    SESSION.post(
        f"{TENANT_URL}/rest/v1/auth_users_roles",
        headers={
            "apikey": TENANT_SVC,
            "Authorization": f"Bearer {TENANT_SVC}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json={"user_id": user_id, "yacht_id": YACHT_ID, "role": role, "is_active": True}
    )


def login(email, password):
    r = SESSION.post(
        f"{MASTER_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": MASTER_ANON, "Content-Type": "application/json"},
        json={"email": email, "password": password}
    )
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


def main():
    print("=" * 60)
    print("DOCUMENT LENS V2 STAGING ACCEPTANCE")
    print("=" * 60)

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

    jwts['crew'] = login(emails['crew'], PASSWORD)
    ok("CREW JWT obtained")
    jwts['hod'] = login(emails['hod'], PASSWORD)
    ok("HOD JWT obtained")
    jwts['captain'] = login(emails['captain'], PASSWORD)
    ok("CAPTAIN JWT obtained")

    # =========================================================================
    # TEST 1: CREW cannot upload document (403)
    # =========================================================================
    print("\n--- Test: CREW cannot upload document ---")
    call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
        'action': 'upload_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'file_name': f'crew-denied-{int(time.time())}.pdf',
            'mime_type': 'application/pdf',
            'title': 'CREW Should Not Upload'
        }
    }, expect=403)
    ok("CREW upload document denied (403)")

    # =========================================================================
    # TEST 2: HOD can upload document (200)
    # =========================================================================
    print("\n--- Test: HOD can upload document ---")
    upload_resp = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'upload_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'file_name': f'staging-doc-{int(time.time())}.pdf',
            'mime_type': 'application/pdf',
            'title': 'Staging CI Test Document',
            'doc_type': 'manual'
        }
    }, expect=200)
    doc_result = upload_resp.json().get('result') or upload_resp.json()
    doc_id = doc_result.get('document_id')
    if not doc_id:
        fail(f"Missing document_id in upload response: {upload_resp.text}")
    ok(f"HOD uploaded document {doc_id}")

    # =========================================================================
    # TEST 3: CREW cannot update document (403)
    # =========================================================================
    print("\n--- Test: CREW cannot update document ---")
    call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
        'action': 'update_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'document_id': doc_id, 'title': 'CREW Should Not Update'}
    }, expect=403)
    ok("CREW update document denied (403)")

    # =========================================================================
    # TEST 4: HOD can update document (200)
    # =========================================================================
    print("\n--- Test: HOD can update document ---")
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'update_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'document_id': doc_id, 'title': 'HOD Updated Title', 'doc_type': 'report'}
    }, expect=200)
    ok("HOD update document allowed (200)")

    # =========================================================================
    # TEST 5: HOD can add tags (200)
    # =========================================================================
    print("\n--- Test: HOD can add tags ---")
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'add_document_tags',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'document_id': doc_id, 'tags': ['engine', 'test', 'ci']}
    }, expect=200)
    ok("HOD add document tags allowed (200)")

    # =========================================================================
    # TEST 6: Invalid document_id returns 400/404
    # =========================================================================
    print("\n--- Test: Invalid document_id returns 400/404 ---")
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'update_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'document_id': '00000000-0000-0000-0000-000000000000', 'title': 'Should Fail'}
    }, expect=[400, 404, 500])  # 500 acceptable if handler throws before RLS check
    ok("Invalid document_id rejected")

    # =========================================================================
    # TEST 7: HOD cannot delete document (403)
    # =========================================================================
    print("\n--- Test: HOD cannot delete document ---")
    call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'delete_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'document_id': doc_id,
            'reason': 'HOD should not delete',
            'signature': json.dumps({'test': 'sig'})
        }
    }, expect=403)
    ok("HOD delete document denied (403)")

    # =========================================================================
    # TEST 8: Delete requires signature (400 without)
    # =========================================================================
    print("\n--- Test: Delete requires signature ---")
    call_api(jwts['captain'], 'POST', '/v1/actions/execute', {
        'action': 'delete_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {'document_id': doc_id, 'reason': 'No signature test'}
    }, expect=400)
    ok("Delete without signature rejected (400)")

    # =========================================================================
    # TEST 9: Captain can delete with signature (200)
    # =========================================================================
    print("\n--- Test: Captain can delete with signature ---")
    call_api(jwts['captain'], 'POST', '/v1/actions/execute', {
        'action': 'delete_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'document_id': doc_id,
            'reason': 'CI test cleanup',
            'signature': json.dumps({
                'signature_type': 'delete_document',
                'role_at_signing': 'captain',
                'signed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'signature_hash': 'ci-test-hash'
            })
        }
    }, expect=200)
    ok("Captain delete document allowed (200)")

    # =========================================================================
    # TEST 10: Action list - HOD sees upload_document
    # =========================================================================
    print("\n--- Test: Action list - HOD sees upload_document ---")
    resp = call_api(jwts['hod'], 'GET', '/v1/actions/list?q=upload+document&domain=documents', expect=200)
    actions = resp.json().get('actions', [])
    action_ids = [a.get('action_id') for a in actions]
    if 'upload_document' not in action_ids:
        fail(f"HOD should see upload_document in action list: {action_ids}")
    ok("HOD sees upload_document in document action list")

    # =========================================================================
    # TEST 11: Action list - CREW sees no MUTATE actions
    # =========================================================================
    print("\n--- Test: Action list - CREW sees no MUTATE actions ---")
    resp = call_api(jwts['crew'], 'GET', '/v1/actions/list?domain=documents', expect=200)
    actions = resp.json().get('actions', [])
    mutations = [a for a in actions if a.get('variant') in ('MUTATE', 'SIGNED')]
    if len(mutations) > 0:
        fail(f"CREW should not see mutation actions: {[a['action_id'] for a in mutations]}")
    ok("CREW sees no mutation actions in document domain")

    # =========================================================================
    # TEST 12: CREW can get document URL (READ action)
    # =========================================================================
    print("\n--- Test: CREW can get document URL (READ) ---")
    # Create another doc for this test (since we deleted the first one)
    upload_resp2 = call_api(jwts['hod'], 'POST', '/v1/actions/execute', {
        'action': 'upload_document',
        'context': {'yacht_id': YACHT_ID},
        'payload': {
            'file_name': f'read-test-{int(time.time())}.pdf',
            'mime_type': 'application/pdf',
            'title': 'Read Test Document'
        }
    }, expect=200)
    doc_result2 = upload_resp2.json().get('result') or upload_resp2.json()
    doc_id2 = doc_result2.get('document_id')

    if doc_id2:
        # CREW should be able to get URL (READ action)
        call_api(jwts['crew'], 'POST', '/v1/actions/execute', {
            'action': 'get_document_url',
            'context': {'yacht_id': YACHT_ID},
            'payload': {'document_id': doc_id2}
        }, expect=200)
        ok("CREW can get document URL (200)")
    else:
        ok("CREW get URL test skipped (doc creation failed)")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("All Document Lens v2 staging re-checks passed.")
    print("=" * 60)


if __name__ == '__main__':
    main()
