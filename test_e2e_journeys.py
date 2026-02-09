#!/usr/bin/env python3
"""
E2E Journey Tests - Backend API Validation
===========================================

Tests full user journeys for:
1. PR #194: RBAC fix (crew can create work orders)
2. PR #195: Image upload MVP (all roles)

Uses real user JWTs and real parts from production.
"""

import requests
import json
import sys
import os
from typing import Dict, Any

# Configuration
API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL", "https://qvzmkaamzaqxpzbewjxe.supabase.co")
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY", "")

# Real test parts (no images yet)
TEST_PARTS = {
    "TEAK_COMPOUND": "5dd34337-c4c4-41dd-9c6b-adf84af349a8",
    "WATER_PUMP": "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",
    "CYLINDER_RING": "5543266b-2d8c-46a0-88e2-74a7ab403cdd",
}

# Test users - passwords from environment
USERS = {
    "CAPTAIN": {
        "email": "captain.tenant@alex-short.com",
        "password": os.getenv("CAPTAIN_PASSWORD", ""),
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "role": "captain",
        "jwt": None,  # Will be populated by sign_in_users()
    },
    "HOD": {
        "email": "hod.tenant@alex-short.com",
        "password": os.getenv("HOD_PASSWORD", ""),
        "user_id": "89b1262c-ff59-4591-b954-757cdf3d609d",
        "role": "chief_engineer",
        "jwt": None,
    },
    "CREW": {
        "email": "crew.tenant@alex-short.com",
        "password": os.getenv("CREW_PASSWORD", ""),
        "user_id": "2da12a4b-c0a1-4716-80ae-d29c90d98233",
        "role": "crew",
        "jwt": None,
    },
}


def sign_in_user(email: str, password: str) -> str:
    """Sign in user and get fresh JWT token."""
    if not SUPABASE_ANON_KEY:
        raise ValueError("MASTER_SUPABASE_ANON_KEY not set")

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }

    payload = {"email": email, "password": password}

    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=headers,
        json=payload,
        timeout=10,
    )

    if response.status_code != 200:
        raise Exception(f"Sign in failed for {email}: HTTP {response.status_code} - {response.text}")

    data = response.json()
    return data["access_token"]


def sign_in_users():
    """Sign in all test users and populate JWTs."""
    print("\n🔐 Signing in test users...")
    for role, user in USERS.items():
        if not user["password"]:
            print(f"   ⚠️  {role}: No password set (set {role}_PASSWORD env var)")
            continue

        try:
            jwt = sign_in_user(user["email"], user["password"])
            user["jwt"] = jwt
            print(f"   ✅ {role}: Signed in ({user['email']})")
        except Exception as e:
            print(f"   ❌ {role}: Sign in failed - {e}")
            sys.exit(1)

    print()


class JourneyTest:
    """E2E journey test runner"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name: str, fn):
        """Run a test and track results"""
        try:
            print(f"\n🧪 {name}")
            result = fn()
            if result.get("success"):
                print(f"   ✅ PASS: {result.get('message')}")
                self.passed += 1
                self.results.append({"test": name, "status": "PASS", **result})
            else:
                print(f"   ❌ FAIL: {result.get('message')}")
                self.failed += 1
                self.results.append({"test": name, "status": "FAIL", **result})
        except Exception as e:
            print(f"   ❌ FAIL: {str(e)}")
            self.failed += 1
            self.results.append({"test": name, "status": "FAIL", "error": str(e)})

    def summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total:  {self.passed + self.failed}")
        print("=" * 70)

        # Save results
        with open("test-results/e2e_journey_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test-results/e2e_journey_results.json")

        return self.failed == 0


# ============================================================================
# JOURNEY TESTS
# ============================================================================

def journey_1_rbac_fix_crew_work_order():
    """Journey 1: CRITICAL RBAC Fix - Crew creates work order (PR #194)"""
    import time
    headers = {
        "Authorization": f"Bearer {USERS['CREW']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "action": "create_work_order",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "title": f"E2E Test - Crew WO {int(time.time())}",
            "department": "deck",
            "priority": "medium",
            "description": "Testing PR #194 RBAC fix - crew can create work orders",
        },
    }

    response = requests.post(f"{API_BASE}/v1/actions/execute", headers=headers, json=payload)

    # Should succeed (not 403)
    if response.status_code < 400:
        body = response.json()
        return {
            "success": True,
            "message": f"Crew created work order successfully (HTTP {response.status_code})",
            "work_order_id": body.get("result", {}).get("work_order_id"),
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def journey_2_captain_upload_image():
    """Journey 2: Captain uploads part image (PR #195)"""
    headers = {
        "Authorization": f"Bearer {USERS['CAPTAIN']['jwt']}",
    }

    # Use multipart/form-data with actual file upload
    files = {
        "file": ("e2e-test-image.png", open("test-results/test-image.png", "rb"), "image/png")
    }

    data = {
        "yacht_id": YACHT_ID,
        "part_id": TEST_PARTS["TEAK_COMPOUND"],
        "description": "E2E journey test - captain upload",
    }

    response = requests.post(
        f"{API_BASE}/v1/parts/upload-image",
        headers=headers,
        files=files,
        data=data,
        timeout=30
    )

    if response.status_code == 200:
        body = response.json()
        # Verify storage path contains yacht_id (storage isolation)
        storage_path = body.get("storage_path", "")
        image_url = body.get("image_url", "")
        if YACHT_ID in storage_path:
            return {
                "success": True,
                "message": f"Captain uploaded image, storage isolated: {storage_path[:50]}...",
                "storage_path": storage_path,
                "image_url": image_url[:80] + "..." if len(image_url) > 80 else image_url,
            }
        else:
            return {
                "success": False,
                "message": f"Storage path missing yacht_id: {storage_path}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def journey_3_hod_update_image():
    """Journey 3: HOD updates image description (PR #195)"""
    headers = {
        "Authorization": f"Bearer {USERS['HOD']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "yacht_id": YACHT_ID,
        "image_id": TEST_PARTS["TEAK_COMPOUND"],  # MVP: image_id = part_id
        "description": "E2E test - HOD updated description",
    }

    response = requests.post(f"{API_BASE}/v1/parts/update-image", headers=headers, json=payload)

    if response.status_code == 200:
        body = response.json()
        return {
            "success": True,
            "message": f"HOD updated image description successfully",
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def journey_4_nlp_search_parts():
    """Journey 4: NLP search for parts (actionable query-based)"""
    headers = {
        "Authorization": f"Bearer {USERS['HOD']['jwt']}",
        "Content-Type": "application/json",
    }

    # Natural language query for parts
    payload = {
        "query": "teak seam compound for deck maintenance",
        "yacht_id": YACHT_ID,
    }

    response = requests.post(f"{API_BASE}/search", headers=headers, json=payload)

    if response.status_code == 200:
        body = response.json()
        domain = body.get("context", {}).get("domain")
        actions = body.get("actions", [])

        # Verify domain detection and actions surfaced
        if domain == "parts" and len(actions) > 0:
            return {
                "success": True,
                "message": f"NLP search found domain=parts, surfaced {len(actions)} actions",
                "actions": [a["action_id"] for a in actions[:3]],
            }
        else:
            return {
                "success": False,
                "message": f"Domain={domain}, actions={len(actions)} (expected parts domain with actions)",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def journey_5_version_check():
    """Journey 5: Verify deployed version"""
    response = requests.get(f"{API_BASE}/version")

    if response.status_code == 200:
        body = response.json()
        version = body.get("version")
        fixes = body.get("critical_fixes", [])

        if version == "2026.02.09.003" and len(fixes) > 0:
            return {
                "success": True,
                "message": f"Version {version} deployed with {len(fixes)} critical fixes",
                "fixes": fixes,
            }
        else:
            return {
                "success": False,
                "message": f"Version={version} (expected 2026.02.09.003), fixes={len(fixes)}",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}",
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("E2E JOURNEY TESTS - PR #194 (RBAC) + PR #195 (Image Upload)")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print(f"Yacht: {YACHT_ID}")
    print(f"Users: Captain, HOD, Crew")

    # Sign in all users to get fresh JWTs
    sign_in_users()

    runner = JourneyTest()

    # Run journey tests
    runner.test("Journey 1: RBAC Fix - Crew creates work order", journey_1_rbac_fix_crew_work_order)
    runner.test("Journey 2: Captain uploads part image", journey_2_captain_upload_image)
    runner.test("Journey 3: HOD updates image description", journey_3_hod_update_image)
    runner.test("Journey 4: NLP search for parts", journey_4_nlp_search_parts)
    runner.test("Journey 5: Version check", journey_5_version_check)

    # Summary
    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
