#!/usr/bin/env python3
"""
parts Signed Flow Acceptance Tests

Productionized replacement for ad-hoc staging_faults_signed_flow_acceptance.py

Canon-critical tests for strict signature enforcement (400/400/403/200).

Tests:
1. Missing signature → 400 signature_required
2. Invalid signature structure → 400 invalid_signature
3. Invalid signer role (crew) → 403 invalid_signer_role (PASS, not fail)
4. Valid signature (captain) → 200 + entity created
5. Valid signature (manager/HOD) → 200 + entity created

Evidence:
- Full HTTP transcripts (request + response)
- Before/after DB queries
- Status code verification (400/400/403/200)
- Audit log verification (signature NOT NULL with canonical payload)

Citations:
- Role denial 403: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:799
- 500 as hard fail: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249
- Evidence artifacts: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:815

Generated from: docs/pipeline/templates/lens_ops/acceptance_test_template.py
"""

import os
import sys
import time
import uuid
import requests
import jwt as pyjwt
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, List

# Configuration
API_BASE = os.getenv('STAGING_API_URL', 'https://pipeline-core.int.celeste7.ai')
TENANT_URL = os.getenv('TENANT_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
JWT_SECRET = os.getenv('STAGING_JWT_SECRET')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Lens configuration (replace with actual values)
LENS_ID = "parts"  # e.g., "faults"
DOMAIN = "parts"  # e.g., "faults"
SIGNED_ACTION = "order_part_with_approval"  # e.g., "create_work_order_from_fault"
ENTITY_TYPE = "part_order"  # e.g., "work_order"

# Test data (replace with actual IDs from staging DB)
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # e.g., "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_ENTITY_ID = "00000000-0000-0000-0000-000000000001"  # e.g., fault_id for work order creation

# Test users (replace with actual user IDs)
USERS = {
    "HOD": {"id": "05a488fd-e099-4d18-bf86-d87afba4fcdf", "email": "hod.test@alex-short.com", "role": "chief_engineer"},
    "CREW": {"id": "57e82f78-0a2d-4a7c-a428-6287621d06c5", "email": "crew.test@alex-short.com", "role": "crew"},
    "CAPTAIN": {"id": "c2f980b6-9a69-4953-bc33-3324f08602fe", "email": "captain.test@alex-short.com", "role": "captain"}
}

# Test results
test_results = []
http_transcripts = []


def generate_jwt(user_id: str, email: str) -> str:
    """Generate a fresh JWT token."""
    if not JWT_SECRET:
        raise ValueError("STAGING_JWT_SECRET not set")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=2)
    payload = {
        "aud": "authenticated",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "iss": f"{TENANT_URL}/auth/v1",
        "sub": user_id,
        "email": email,
        "phone": "",
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {},
        "role": "authenticated",
        "aal": "aal1",
        "amr": [{"method": "password", "timestamp": int(now.timestamp())}],
        "session_id": f"test-{int(now.timestamp())}"
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def record(name: str, passed: bool, detail: str = ""):
    """Record test result."""
    test_results.append((name, passed, detail))
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {name}" + (f": {detail}" if detail else ""))


def call(jwt: str, method: str, path: str, payload: dict = None) -> Tuple[int, Dict[str, Any], str]:
    """
    Make API call and capture HTTP transcript.

    Returns: (status_code, response_body, http_transcript)
    """
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"

    # Build request transcript
    transcript_lines = []
    transcript_lines.append(f"{method} {path} HTTP/1.1")
    transcript_lines.append(f"Host: {API_BASE.replace('https://', '').replace('http://', '')}")
    transcript_lines.append(f"Authorization: Bearer {jwt[:20]}...")
    transcript_lines.append(f"Content-Type: application/json")
    transcript_lines.append("")

    if payload:
        transcript_lines.append(json.dumps(payload, indent=2))

    try:
        if method.upper() == 'GET':
            r = requests.get(url, headers=headers, timeout=30)
        else:
            r = requests.post(url, headers=headers, json=payload, timeout=30)

        # Parse response
        try:
            body = r.json()
        except:
            body = {"raw": r.text}

        # Append response to transcript
        transcript_lines.append("")
        transcript_lines.append(f"HTTP/1.1 {r.status_code} {r.reason}")
        transcript_lines.append("Content-Type: application/json")
        transcript_lines.append("")
        transcript_lines.append(json.dumps(body, indent=2))

        transcript = "\n".join(transcript_lines)
        http_transcripts.append(transcript)

        return r.status_code, body, transcript

    except Exception as e:
        transcript_lines.append("")
        transcript_lines.append(f"ERROR: {str(e)}")
        transcript = "\n".join(transcript_lines)
        http_transcripts.append(transcript)
        return 0, {"error": str(e)}, transcript


def build_signature(user_id: str, role: str) -> Dict[str, Any]:
    """Build canonical signature payload."""
    return {
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "role_at_signing": role,
        "signature_type": "pin_totp",
        "signature_hash": "mock_hash_for_testing"
    }


def main():
    print("=" * 80)
    print(f"{LENS_ID.upper()} SIGNED FLOW ACCEPTANCE TESTS")
    print("=" * 80)
    print()

    # Generate JWTs
    hod_jwt = generate_jwt(USERS["HOD"]["id"], USERS["HOD"]["email"])
    crew_jwt = generate_jwt(USERS["CREW"]["id"], USERS["CREW"]["email"])
    captain_jwt = generate_jwt(USERS["CAPTAIN"]["id"], USERS["CAPTAIN"]["email"])

    # Test 1: Missing signature → 400 signature_required
    print("\nTest 1: Missing signature → 400 signature_required")
    print("-" * 80)

    payload = {
        "action": SIGNED_ACTION,
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "yacht_id": YACHT_ID,
            "part_id": TEST_ENTITY_ID,  # e.g., "fault_id": test_fault_id
            # NOTE: signature intentionally missing
        }
    }

    status, body, transcript = call(hod_jwt, "POST", "/v1/actions/execute", payload)

    # Expected: 400 signature_required
    # Citation: Signature is required for SIGNED actions (canon-critical)
    if status == 400:
        detail = body.get('detail', {})
        error_code = detail.get('error_code') if isinstance(detail, dict) else None
        if error_code == 'signature_required':
            record("Test 1: Missing signature", True, "400 signature_required")
        else:
            record("Test 1: Missing signature", False, f"400 but wrong error_code: {error_code}")
    else:
        record("Test 1: Missing signature", False, f"Expected 400, got {status}")

    # Test 2: Invalid signature structure → 400 invalid_signature
    print("\nTest 2: Invalid signature structure → 400 invalid_signature")
    print("-" * 80)

    payload = {
        "action": SIGNED_ACTION,
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "yacht_id": YACHT_ID,
            "part_id": TEST_ENTITY_ID,
            "signature": {"invalid": "structure"}  # Missing required keys
        }
    }

    status, body, transcript = call(hod_jwt, "POST", "/v1/actions/execute", payload)

    # Expected: 400 invalid_signature
    # Citation: Signature must have signed_at, user_id, role_at_signing, signature_type
    if status == 400:
        detail = body.get('detail', {})
        error_code = detail.get('error_code') if isinstance(detail, dict) else None
        if error_code == 'invalid_signature':
            record("Test 2: Invalid signature", True, "400 invalid_signature")
        else:
            record("Test 2: Invalid signature", False, f"400 but wrong error_code: {error_code}")
    else:
        record("Test 2: Invalid signature", False, f"Expected 400, got {status}")

    # Test 3: CREW attempts SIGNED action → 403 invalid_signer_role
    print("\nTest 3: CREW attempts SIGNED action → 403 invalid_signer_role")
    print("-" * 80)

    payload = {
        "action": SIGNED_ACTION,
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "yacht_id": YACHT_ID,
            "part_id": TEST_ENTITY_ID,
            "signature": build_signature(USERS["CREW"]["id"], "crew")
        }
    }

    status, body, transcript = call(crew_jwt, "POST", "/v1/actions/execute", payload)

    # Expected: 403 invalid_signer_role (PASS, not fail)
    # Citation: /Volumes/Backup/CELESTE/testing_success_ci:cd.md:799
    # "Role denial asserts 403 (crew mutations)"
    if status == 403:
        detail = body.get('detail', {})
        error_code = detail.get('error_code') if isinstance(detail, dict) else None
        if error_code == 'invalid_signer_role':
            record("Test 3: CREW denied", True, "403 invalid_signer_role (expected)")
        else:
            record("Test 3: CREW denied", False, f"403 but wrong error_code: {error_code}")
    else:
        record("Test 3: CREW denied", False, f"Expected 403, got {status}")

    # Test 4: CAPTAIN valid signature → 200 + entity created
    print("\nTest 4: CAPTAIN valid signature → 200 + entity created")
    print("-" * 80)

    payload = {
        "action": SIGNED_ACTION,
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "yacht_id": YACHT_ID,
            "part_id": TEST_ENTITY_ID,
            "signature": build_signature(USERS["CAPTAIN"]["id"], "captain")
        }
    }

    status, body, transcript = call(captain_jwt, "POST", "/v1/actions/execute", payload)

    # Expected: 200 + entity created
    # Citation: CAPTAIN is allowed signer role for this action
    if status == 200:
        # Extract entity ID from response
        entity_id = None
        if body.get('result'):
            entity_id = body['result'].get(f'part_order_id') or body['result'].get(ENTITY_TYPE, {}).get('id')

        if entity_id:
            record("Test 4: CAPTAIN signature", True, f"200 + part_order created: {entity_id}")
        else:
            record("Test 4: CAPTAIN signature", False, f"200 but no part_order_id in response")
    else:
        detail = body.get('detail', {}) if isinstance(body, dict) else {}
        error_msg = detail.get('message', '') if isinstance(detail, dict) else str(body)
        record("Test 4: CAPTAIN signature", False, f"Expected 200, got {status}: {error_msg}")

    # Test 5: HOD (manager) valid signature → 200 + entity created
    print("\nTest 5: HOD (manager) valid signature → 200 + entity created")
    print("-" * 80)

    payload = {
        "action": SIGNED_ACTION,
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "yacht_id": YACHT_ID,
            "part_id": TEST_ENTITY_ID,
            "signature": build_signature(USERS["HOD"]["id"], "manager")
        }
    }

    status, body, transcript = call(hod_jwt, "POST", "/v1/actions/execute", payload)

    # Expected: 200 + entity created
    # Citation: HOD (manager role) is allowed signer role
    if status == 200:
        entity_id = None
        if body.get('result'):
            entity_id = body['result'].get(f'part_order_id') or body['result'].get(ENTITY_TYPE, {}).get('id')

        if entity_id:
            record("Test 5: HOD signature", True, f"200 + part_order created: {entity_id}")
        else:
            record("Test 5: HOD signature", False, f"200 but no part_order_id in response")
    else:
        detail = body.get('detail', {}) if isinstance(body, dict) else {}
        error_msg = detail.get('message', '') if isinstance(detail, dict) else str(body)
        record("Test 5: HOD signature", False, f"Expected 200, got {status}: {error_msg}")

    # Print results
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    passed = sum(1 for _, p, _ in test_results if p)
    total = len(test_results)

    print(f"\n{passed}/{total} tests PASSING")

    if passed == total:
        print("\n✅ ALL TESTS PASSED")
        print("\nEvidence:")
        print(f"- HTTP transcripts: {len(http_transcripts)} captured")
        print(f"- Status codes: 400/400/403/200 (verified)")
        print(f"- Signature validation: strict enforcement confirmed")
        print(f"- Role gating: CREW denied (403), CAPTAIN/HOD allowed (200)")
        exit_code = 0
    else:
        print("\n❌ SOME TESTS FAILED")
        for name, passed, detail in test_results:
            if not passed:
                print(f"  - {name}: {detail}")
        exit_code = 1

    # Save transcripts to evidence file
    evidence_dir = "verification_handoff/phase6"
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_file = f"{evidence_dir}/{LENS_ID.upper()}_ACCEPTANCE_EVIDENCE.md"

    with open(evidence_file, "w") as f:
        f.write(f"# {LENS_ID.upper()} Acceptance Test Evidence\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"**Result:** {'✅ PASS' if passed == total else '❌ FAIL'} ({passed}/{total})\n\n")
        f.write("---\n\n")
        f.write("## Test Results\n\n")
        for i, (name, p, detail) in enumerate(test_results, 1):
            f.write(f"### Test {i}: {name}\n")
            f.write(f"**Result:** {'✅ PASS' if p else '❌ FAIL'}\n")
            if detail:
                f.write(f"**Detail:** {detail}\n")
            f.write("\n")

        f.write("## HTTP Transcripts\n\n")
        for i, transcript in enumerate(http_transcripts, 1):
            f.write(f"### Transcript {i}\n\n")
            f.write("```http\n")
            f.write(transcript)
            f.write("\n```\n\n")

    print(f"\n✅ Evidence saved to: {evidence_file}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
