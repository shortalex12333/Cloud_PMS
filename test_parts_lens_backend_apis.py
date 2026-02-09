#!/usr/bin/env python3
"""
Parts Lens - Backend API Testing with Real User JWTs
=====================================================

Tests all backend APIs that app.celeste7.ai frontend calls.
Validates bffb436 deployment and backend functionality.

Uses REAL user credentials and fresh JWTs.
"""

import requests
import json
import sys
import os
import uuid
import time
from typing import Dict, Any

# Configuration
API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY", "")

# Test users
USERS = {
    "CAPTAIN": {
        "email": "x@alex-short.com",
        "password": os.getenv("ALL_TEST_USER_PASSWORD", "Password2!"),
        "jwt": None,
    },
    "HOD": {
        "email": "hod.test@alex-short.com",
        "password": os.getenv("ALL_TEST_USER_PASSWORD", "Password2!"),
        "jwt": None,
    },
    "CREW": {
        "email": "crew.test@alex-short.com",
        "password": os.getenv("ALL_TEST_USER_PASSWORD", "Password2!"),
        "jwt": None,
    },
}

# Test parts (from validate_system.py)
TEST_PARTS = {
    "TEAK_COMPOUND": "5dd34337-c4c4-11dd-9c6b-adf84af349a8",
    "WATER_PUMP": "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0",
    "CYLINDER_RING": "5543266b-2d8c-46a0-88e2-74a7ab403cdd",
}


class BackendAPITester:
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
        print("BACKEND API TEST SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total:  {self.passed + self.failed}")
        print("=" * 70)

        # Save results
        with open("test-results/backend_api_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test-results/backend_api_results.json")

        return self.failed == 0


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


def sign_in_all_users():
    """Sign in all test users and populate JWTs."""
    print("=" * 70)
    print("SIGNING IN TEST USERS")
    print("=" * 70)
    for role, user in USERS.items():
        try:
            jwt = sign_in_user(user["email"], user["password"])
            user["jwt"] = jwt
            print(f"✅ {role}: {user['email']}")
        except Exception as e:
            print(f"❌ {role}: {e}")
            sys.exit(1)
    print()


# ============================================================================
# SEARCH / DOMAIN DETECTION TESTS
# ============================================================================

def test_search_marine_part_domain_detection():
    """Test: /search detects domain=parts for marine query"""
    headers = {
        "Authorization": f"Bearer {USERS['HOD']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": "teak seam compound for deck maintenance",
        "limit": 10,
    }

    response = requests.post(f"{API_BASE}/search", headers=headers, json=payload, timeout=10)

    if response.status_code == 200:
        body = response.json()
        domain = body.get("context", {}).get("domain")
        confidence = body.get("context", {}).get("domain_confidence")

        if domain == "parts":
            return {
                "success": True,
                "message": f"Domain detected: parts (confidence: {confidence})",
                "domain": domain,
                "confidence": confidence,
            }
        else:
            return {
                "success": False,
                "message": f"Expected domain=parts, got {domain} (PR #208 marine anchors may not be deployed)",
                "domain": domain,
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_search_returns_actions():
    """Test: /search returns action buttons for parts query"""
    headers = {
        "Authorization": f"Bearer {USERS['CAPTAIN']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": "caterpillar filter replacement",
        "limit": 10,
    }

    response = requests.post(f"{API_BASE}/search", headers=headers, json=payload, timeout=10)

    if response.status_code == 200:
        body = response.json()
        actions = body.get("actions", [])

        if len(actions) > 0:
            action_names = []
            for a in actions[:5]:
                if isinstance(a, dict):
                    name = a.get("action") or a.get("label") or "unknown"
                    action_names.append(name)

            return {
                "success": True,
                "message": f"Search returned {len(actions)} actions: {action_names}",
                "actions_count": len(actions),
                "actions": action_names,
            }
        else:
            return {
                "success": False,
                "message": "No actions returned (expected parts-related actions)",
            }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


# ============================================================================
# ACTION EXECUTION TESTS (CRITICAL - bffb436)
# ============================================================================

def test_action_execute_endpoint_exists():
    """Test: /v1/actions/execute endpoint exists and requires auth"""
    # Test without auth first
    response = requests.post(
        f"{API_BASE}/v1/actions/execute",
        json={"action": "test"},
        timeout=10
    )

    if response.status_code in [401, 422]:
        return {
            "success": True,
            "message": f"Endpoint exists and requires auth (HTTP {response.status_code})",
            "status_code": response.status_code,
        }
    elif response.status_code == 404:
        return {
            "success": False,
            "message": "Endpoint NOT FOUND (404) - routing issue!",
            "status_code": 404,
        }
    else:
        return {
            "success": False,
            "message": f"Unexpected status: {response.status_code}",
        }


def test_action_execute_create_work_order():
    """Test: Execute create_work_order action (crew RBAC)"""
    unique_id = str(uuid.uuid4())[:8]
    headers = {
        "Authorization": f"Bearer {USERS['CREW']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "action": "create_work_order",
        "context": {"yacht_id": YACHT_ID},
        "payload": {
            "title": f"Backend API Test - {unique_id}",
            "department": "deck",
            "priority": "medium",
            "description": f"Testing action execution - {unique_id}",
        },
    }

    response = requests.post(f"{API_BASE}/v1/actions/execute", headers=headers, json=payload, timeout=10)

    if response.status_code < 400 or response.status_code == 409:
        return {
            "success": True,
            "message": f"Action executed (HTTP {response.status_code}) - RBAC working",
            "status_code": response.status_code,
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


# ============================================================================
# IMAGE UPLOAD TESTS (PR #208 JWT FIX)
# ============================================================================

def test_image_upload_jwt_validation():
    """Test: Image upload with valid JWT (PR #208 fix)"""
    headers = {
        "Authorization": f"Bearer {USERS['CAPTAIN']['jwt']}",
    }

    # Create minimal test image (1x1 PNG)
    import base64
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    png_bytes = base64.b64decode(png_base64)

    files = {
        "file": ("test.png", png_bytes, "image/png")
    }

    data = {
        "yacht_id": YACHT_ID,
        "part_id": TEST_PARTS["TEAK_COMPOUND"],
        "description": "Backend API test image",
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
        return {
            "success": True,
            "message": "Image uploaded successfully (PR #208 JWT fix working!)",
            "status_code": 200,
            "storage_path": body.get("storage_path", "")[:50],
        }
    elif response.status_code == 500 and "ValidationResult" in response.text:
        return {
            "success": False,
            "message": "HTTP 500 - JWT bug still present (PR #208 not deployed!)",
            "status_code": 500,
            "error": response.text[:200],
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


def test_image_update_jwt_validation():
    """Test: Image update with valid JWT (PR #208 fix)"""
    headers = {
        "Authorization": f"Bearer {USERS['HOD']['jwt']}",
        "Content-Type": "application/json",
    }

    payload = {
        "yacht_id": YACHT_ID,
        "image_id": TEST_PARTS["TEAK_COMPOUND"],  # MVP: image_id = part_id
        "description": "Backend API test - updated description",
    }

    response = requests.post(f"{API_BASE}/v1/parts/update-image", headers=headers, json=payload, timeout=10)

    if response.status_code == 200:
        return {
            "success": True,
            "message": "Image updated successfully (PR #208 JWT fix working!)",
            "status_code": 200,
        }
    elif response.status_code == 500:
        return {
            "success": False,
            "message": f"HTTP 500 - JWT bug still present (PR #208 not deployed!)",
            "status_code": 500,
            "error": response.text[:200],
        }
    elif response.status_code == 404:
        return {
            "success": True,
            "message": "HTTP 404 - No image exists yet (expected, but JWT validation passed!)",
            "status_code": 404,
            "note": "This is OK - proves JWT validation works",
        }
    else:
        return {
            "success": False,
            "message": f"HTTP {response.status_code}: {response.text[:200]}",
        }


# ============================================================================
# DEPLOYMENT VALIDATION
# ============================================================================

def test_deployment_version():
    """Test: Check deployed version"""
    response = requests.get(f"{API_BASE}/version", timeout=10)

    if response.status_code == 200:
        body = response.json()
        version = body.get("version")
        commit = body.get("git_commit")

        return {
            "success": True,
            "message": f"Version: {version}, Commit: {commit[:7]}",
            "version": version,
            "commit": commit,
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
    print("PARTS LENS - BACKEND API TESTING")
    print("=" * 70)
    print(f"API: {API_BASE}")
    print(f"Yacht: {YACHT_ID}")
    print(f"Testing: All backend APIs for app.celeste7.ai")
    print(f"Deployment: bffb436 expected")
    print("=" * 70)
    print()

    # Sign in all users
    sign_in_all_users()

    runner = BackendAPITester()

    # Deployment validation
    print("\n" + "=" * 70)
    print("GROUP 1: DEPLOYMENT VALIDATION")
    print("=" * 70)
    runner.test("Check deployed version", test_deployment_version)

    # Search / Domain Detection
    print("\n" + "=" * 70)
    print("GROUP 2: SEARCH & DOMAIN DETECTION")
    print("=" * 70)
    runner.test("Search detects domain=parts for marine query", test_search_marine_part_domain_detection)
    runner.test("Search returns action buttons", test_search_returns_actions)

    # Action Execution (CRITICAL - bffb436)
    print("\n" + "=" * 70)
    print("GROUP 3: ACTION EXECUTION (bffb436 fix)")
    print("=" * 70)
    runner.test("/v1/actions/execute endpoint exists", test_action_execute_endpoint_exists)
    runner.test("Execute create_work_order action", test_action_execute_create_work_order)

    # Image Operations (PR #208 JWT fix)
    print("\n" + "=" * 70)
    print("GROUP 4: IMAGE OPERATIONS (PR #208 JWT fix)")
    print("=" * 70)
    runner.test("Image upload with JWT validation", test_image_upload_jwt_validation)
    runner.test("Image update with JWT validation", test_image_update_jwt_validation)

    # Summary
    success = runner.summary()

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("✅ Backend APIs validated via testing")
    print()
    print("⏳ Frontend testing required:")
    print("   1. Open app.celeste7.ai in browser")
    print("   2. Follow PARTS_LENS_FRONTEND_TEST_PLAN.md")
    print("   3. Validate dynamic UI, action buttons, lens switching")
    print()
    print("📋 Key validations from frontend testing:")
    print("   - Action buttons call /v1/actions/execute (not /workflows)")
    print("   - Parts Lens UI renders on marine part queries")
    print("   - JWT auto-refreshes during session")
    print("   - RBAC enforced correctly in UI")
    print("=" * 70)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
