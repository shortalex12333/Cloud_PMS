#!/usr/bin/env python3
"""
Test: Image Update Endpoint - Tenant Key Extraction Fix

This test verifies that the tenant key extraction fix (PR #225) works
for the update-image endpoint. We test with a part that has NO image,
so we expect a 400 error "no image to update" - which proves the
tenant key fix is working (otherwise we'd get "Missing tenant credentials").
"""

import requests
import os
import sys

API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY", "")

# Part that likely has NO image (different from TEAK_COMPOUND)
TEST_PART_NO_IMAGE = "2f452e3b-bf3e-464e-82d5-7d0bc849e6c0"  # WATER_PUMP


def sign_in_user(email: str, password: str) -> str:
    """Sign in user and get JWT."""
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
        raise Exception(f"Sign in failed: {response.status_code} - {response.text}")
    return response.json()["access_token"]


def test_update_image_tenant_key_fix():
    """Test update-image endpoint with tenant key fix."""
    print("=" * 70)
    print("TEST: Image Update - Tenant Key Extraction Fix (PR #225)")
    print("=" * 70)

    # Sign in as HOD
    print("\n1. Signing in as HOD...")
    jwt = sign_in_user("hod.test@alex-short.com", "Password2!")
    print("   ✅ Signed in successfully")

    # Call update-image endpoint
    print(f"\n2. Calling update-image for part: {TEST_PART_NO_IMAGE}")
    print("   (This part likely has NO image)")

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    payload = {
        "yacht_id": YACHT_ID,
        "image_id": TEST_PART_NO_IMAGE,
        "description": "Test update - should fail (no image exists)",
    }

    response = requests.post(
        f"{API_BASE}/v1/parts/update-image",
        headers=headers,
        json=payload,
        timeout=10
    )

    print(f"\n3. Response: HTTP {response.status_code}")

    # Analyze result
    print("\n" + "=" * 70)
    print("RESULT ANALYSIS")
    print("=" * 70)

    if response.status_code == 400:
        error = response.json().get("error", "")
        if "not found" in error or "no image" in error.lower():
            print("✅ SUCCESS: Tenant key fix is WORKING!")
            print(f"   Error message: {error}")
            print("\n   Why this proves the fix works:")
            print("   - Code successfully extracted tenant_key_alias from dict")
            print("   - Code successfully connected to tenant database")
            print("   - Code successfully queried for part")
            print("   - Error is about missing image (expected), not tenant credentials")
            return True
        elif "Missing tenant credentials" in error:
            print("❌ FAILURE: Tenant key fix NOT working!")
            print(f"   Error: {error}")
            print("\n   This means:")
            print("   - Dict is still being passed where string expected")
            print("   - PR #225 not deployed or was overwritten")
            return False
        else:
            print(f"⚠️  UNEXPECTED 400 error: {error}")
            return False

    elif response.status_code == 200:
        print("✅ SUCCESS: Update worked (part had an image)")
        print("   Tenant key fix is WORKING!")
        return True

    elif response.status_code == 500:
        error_text = response.text[:300]
        if "Missing tenant credentials" in error_text:
            print("❌ FAILURE: Tenant key fix NOT working!")
            print(f"   Error: {error_text}")
            return False
        else:
            print(f"⚠️  UNEXPECTED 500 error: {error_text}")
            return False

    else:
        print(f"⚠️  UNEXPECTED status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False


if __name__ == "__main__":
    try:
        success = test_update_image_tenant_key_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)
