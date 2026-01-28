#!/usr/bin/env python3
"""
Shopping List Lens v1 - Canary Smoke Tests

Validates canary deployment after SHOPPING_LIST_LENS_V1_ENABLED=true.

Tests:
1. Health endpoint - 200 OK
2. CREW create - 200 OK
3. CREW approve - 403 Forbidden
4. CREW reject - 403 Forbidden
5. CREW promote - 403 Forbidden
6. HOD approve - 200 OK
7. HOD reject - 200 OK
8. ENGINEER promote - 200 OK

Canon citations:
- Role denial 403 is PASS: /Volumes/Backup/CELESTE/testing_sucess_ci:cd.md:799
- 500 is always FAIL: /Volumes/Backup/CELESTE/testing_sucess_ci:cd.md:249
- Evidence artifacts: /Volumes/Backup/CELESTE/testing_sucess_ci:cd.md:815
"""

import os
import sys
import time
import uuid
import requests
import jwt as pyjwt
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple

# Configuration
API_BASE = os.getenv('API_BASE', 'https://celeste-pipeline-v1.onrender.com')
TENANT_URL = os.getenv('TENANT_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
JWT_SECRET = os.getenv('TENANT_SUPABASE_JWT_SECRET')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Test data
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'
CREW_USER_ID = '57e82f78-0a2d-4a7c-a428-6287621d06c5'
CREW_EMAIL = 'crew.test@alex-short.com'
HOD_USER_ID = '05a488fd-e099-4d18-bf86-d87afba4fcdf'
HOD_EMAIL = 'hod.test@alex-short.com'
ENGINEER_USER_ID = HOD_USER_ID  # chief_engineer has engineer permissions
ENGINEER_EMAIL = HOD_EMAIL

# Test results
test_results = []
http_transcripts = []

def log(msg: str):
    """Print timestamped log message."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")

def generate_jwt(user_id: str, email: str, yacht_id: str) -> str:
    """Generate JWT token."""
    if not JWT_SECRET:
        raise ValueError("TENANT_SUPABASE_JWT_SECRET not set")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=2)
    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": f"{TENANT_URL}/auth/v1",
        "sub": user_id,
        "email": email,
        "yacht_id": yacht_id,
        "phone": "",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"smoke-{int(now.timestamp())}"
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def api_call(jwt_token: str, method: str, path: str, payload: dict = None) -> Tuple[int, Dict[str, Any], str]:
    """Make API call and capture transcript."""
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE}{path}"

    try:
        if method.upper() == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, headers=headers, json=payload, timeout=10)

        try:
            body = r.json()
        except:
            body = {"raw": r.text}

        # Capture HTTP transcript
        transcript = f"""
{'='*80}
{method} {path}
Authorization: Bearer {jwt_token[:20]}...
Content-Type: application/json

{json.dumps(payload, indent=2) if payload else '(no body)'}

HTTP/1.1 {r.status_code} {r.reason}
Content-Type: application/json

{json.dumps(body, indent=2)}
{'='*80}
"""
        http_transcripts.append(transcript)

        return r.status_code, body, transcript

    except Exception as e:
        error_transcript = f"""
{'='*80}
{method} {path}
ERROR: {str(e)}
{'='*80}
"""
        http_transcripts.append(error_transcript)
        return 0, {"error": str(e)}, error_transcript

def record(name: str, passed: bool, detail: str = ""):
    """Record test result."""
    status = "PASS" if passed else "FAIL"
    test_results.append((name, passed, detail))
    log(f"[{status}] {name}" + (f": {detail}" if detail else ""))

def main():
    log("Starting Shopping List Lens v1 Canary Smoke Tests")
    log(f"API Base: {API_BASE}")
    log(f"Yacht ID: {YACHT_ID}")

    # Generate JWTs
    log("Generating JWT tokens...")
    crew_jwt = generate_jwt(CREW_USER_ID, CREW_EMAIL, YACHT_ID)
    hod_jwt = generate_jwt(HOD_USER_ID, HOD_EMAIL, YACHT_ID)
    engineer_jwt = hod_jwt  # Same user (chief_engineer has both HOD and engineer permissions)

    log(f"CREW JWT: {crew_jwt[:30]}...")
    log(f"HOD JWT: {hod_jwt[:30]}...")

    # Test 1: Health endpoint
    log("\n=== Test 1: Health Endpoint ===")
    status, body, _ = api_call(crew_jwt, "GET", "/health", None)
    if status == 200 and body.get("status") == "healthy":
        record("Health endpoint", True, "200 OK, status=healthy")
    else:
        record("Health endpoint", False, f"Expected 200 + healthy, got {status}: {body}")

    # Test 2: CREW create item (should succeed)
    log("\n=== Test 2: CREW Create Item ===")
    create_payload = {
        "action": "create_shopping_list_item",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "item_name": f"Smoke Test Item {uuid.uuid4().hex[:8]}",
            "quantity": 5,
            "source_type": "manual",
            "is_candidate_part": False,
            "urgency": "routine"
        }
    }
    status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", create_payload)
    if status == 200:
        created_item_id = body.get("data", {}).get("id") or body.get("id")
        record("CREW create item", True, f"200 OK, item_id={created_item_id}")
    else:
        record("CREW create item", False, f"Expected 200, got {status}: {body}")
        created_item_id = None

    # Test 3: CREW approve (should fail with 403)
    log("\n=== Test 3: CREW Approve (Expected 403) ===")
    if created_item_id:
        approve_payload = {
            "action": "approve_shopping_list_item",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": created_item_id,
                "quantity_approved": 5
            }
        }
        status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", approve_payload)
        if status == 403:
            record("CREW approve denied", True, "403 Forbidden (expected)")
        else:
            record("CREW approve denied", False, f"Expected 403, got {status}: {body}")
    else:
        record("CREW approve denied", False, "Skipped (no item created)")

    # Test 4: CREW reject (should fail with 403)
    log("\n=== Test 4: CREW Reject (Expected 403) ===")
    if created_item_id:
        reject_payload = {
            "action": "reject_shopping_list_item",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": created_item_id,
                "rejection_reason": "Test rejection"
            }
        }
        status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", reject_payload)
        if status == 403:
            record("CREW reject denied", True, "403 Forbidden (expected)")
        else:
            record("CREW reject denied", False, f"Expected 403, got {status}: {body}")
    else:
        record("CREW reject denied", False, "Skipped (no item created)")

    # Test 5: CREW promote (should fail with 403)
    log("\n=== Test 5: CREW Promote (Expected 403) ===")
    if created_item_id:
        promote_payload = {
            "action": "promote_candidate_to_part",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": created_item_id,
                "part_name": "Test Part",
                "part_number": f"TEST-{uuid.uuid4().hex[:8]}"
            }
        }
        status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", promote_payload)
        if status == 403:
            record("CREW promote denied", True, "403 Forbidden (expected)")
        else:
            record("CREW promote denied", False, f"Expected 403, got {status}: {body}")
    else:
        record("CREW promote denied", False, "Skipped (no item created)")

    # Test 6: HOD approve (should succeed)
    log("\n=== Test 6: HOD Approve ===")
    if created_item_id:
        approve_payload = {
            "action": "approve_shopping_list_item",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": created_item_id,
                "quantity_approved": 5
            }
        }
        status, body, _ = api_call(hod_jwt, "POST", "/v1/actions/execute", approve_payload)
        if status == 200:
            record("HOD approve item", True, "200 OK")
        else:
            record("HOD approve item", False, f"Expected 200, got {status}: {body}")
    else:
        record("HOD approve item", False, "Skipped (no item created)")

    # Create another item for reject test
    log("\n=== Creating Second Item for Reject Test ===")
    create_payload2 = {
        "action": "create_shopping_list_item",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "item_name": f"Smoke Test Item 2 {uuid.uuid4().hex[:8]}",
            "quantity": 3,
            "source_type": "manual",
            "is_candidate_part": False
        }
    }
    status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", create_payload2)
    if status == 200:
        created_item_id_2 = body.get("data", {}).get("id") or body.get("id")
        log(f"Created second item: {created_item_id_2}")
    else:
        created_item_id_2 = None

    # Test 7: HOD reject (should succeed)
    log("\n=== Test 7: HOD Reject ===")
    if created_item_id_2:
        reject_payload = {
            "action": "reject_shopping_list_item",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": created_item_id_2,
                "rejection_reason": "Smoke test rejection"
            }
        }
        status, body, _ = api_call(hod_jwt, "POST", "/v1/actions/execute", reject_payload)
        if status == 200:
            record("HOD reject item", True, "200 OK")
        else:
            record("HOD reject item", False, f"Expected 200, got {status}: {body}")
    else:
        record("HOD reject item", False, "Skipped (no item created)")

    # Create candidate part for promote test
    log("\n=== Creating Candidate Part for Promote Test ===")
    create_payload3 = {
        "action": "create_shopping_list_item",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "item_name": f"Candidate Part {uuid.uuid4().hex[:8]}",
            "quantity": 2,
            "source_type": "manual",
            "is_candidate_part": True,
            "manufacturer": "Test Mfg",
            "model_number": "TEST-123"
        }
    }
    status, body, _ = api_call(crew_jwt, "POST", "/v1/actions/execute", create_payload3)
    if status == 200:
        candidate_item_id = body.get("data", {}).get("id") or body.get("id")
        log(f"Created candidate part: {candidate_item_id}")

        # Approve it first (required for promote)
        approve_payload = {
            "action": "approve_shopping_list_item",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": candidate_item_id,
                "quantity_approved": 2
            }
        }
        status, body, _ = api_call(hod_jwt, "POST", "/v1/actions/execute", approve_payload)
        if status != 200:
            log(f"WARNING: Failed to approve candidate: {status} {body}")
            candidate_item_id = None
    else:
        candidate_item_id = None

    # Test 8: ENGINEER promote (should succeed)
    log("\n=== Test 8: ENGINEER Promote ===")
    if candidate_item_id:
        promote_payload = {
            "action": "promote_candidate_to_part",
            "context": {"yacht_id": YACHT_ID},
            "payload": {
                "item_id": candidate_item_id,
                "part_name": f"Test Part {uuid.uuid4().hex[:8]}",
                "part_number": f"PART-{uuid.uuid4().hex[:8]}"
            }
        }
        status, body, _ = api_call(engineer_jwt, "POST", "/v1/actions/execute", promote_payload)
        if status == 200:
            record("ENGINEER promote part", True, "200 OK")
        else:
            record("ENGINEER promote part", False, f"Expected 200, got {status}: {body}")
    else:
        record("ENGINEER promote part", False, "Skipped (no candidate created)")

    # Print summary
    log("\n" + "="*80)
    log("SMOKE TEST SUMMARY")
    log("="*80)

    passed = sum(1 for _, p, _ in test_results if p)
    failed = sum(1 for _, p, _ in test_results if not p)

    for name, passed_status, detail in test_results:
        status_str = "✅ PASS" if passed_status else "❌ FAIL"
        log(f"  {status_str}: {name}" + (f" - {detail}" if detail else ""))

    log("")
    log(f"Total: {len(test_results)}")
    log(f"Passed: {passed}")
    log(f"Failed: {failed}")
    log("")

    # Check for 500 errors (0×500 requirement)
    status_5xx_count = sum(1 for t in http_transcripts if "HTTP/1.1 5" in t)
    if status_5xx_count > 0:
        log(f"❌ CRITICAL: {status_5xx_count}×500 errors detected (0×500 requirement violated)")
        log("="*80)
        return 1
    else:
        log(f"✅ 0×500 requirement met (no 5xx errors)")

    log("="*80)

    # Write evidence
    evidence_dir = "verification_handoff/canary"
    os.makedirs(evidence_dir, exist_ok=True)

    evidence_file = f"{evidence_dir}/SHOPPING_LIST_CANARY_SMOKE.md"
    with open(evidence_file, 'w') as f:
        f.write("# Shopping List Lens v1 - Canary Smoke Test Results\n\n")
        f.write(f"**Date**: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"**API Base**: {API_BASE}\n")
        f.write(f"**Yacht ID**: {YACHT_ID}\n\n")
        f.write("## Test Summary\n\n")
        f.write(f"- Total: {len(test_results)}\n")
        f.write(f"- Passed: {passed}\n")
        f.write(f"- Failed: {failed}\n")
        f.write(f"- 5xx Errors: {status_5xx_count}\n\n")
        f.write("## Test Results\n\n")
        for name, passed_status, detail in test_results:
            status_str = "✅ PASS" if passed_status else "❌ FAIL"
            f.write(f"- {status_str} **{name}**" + (f": {detail}" if detail else "") + "\n")
        f.write("\n## HTTP Transcripts\n\n")
        for transcript in http_transcripts:
            f.write(f"```\n{transcript}\n```\n\n")

    log(f"Evidence written to: {evidence_file}")

    if failed > 0:
        return 1
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
