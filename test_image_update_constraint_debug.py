#!/usr/bin/env python3
"""
Debug: Image Update Constraint Violation

Tests the TEAK_COMPOUND part that has an image to see the exact
constraint violation error.
"""

import requests
import os

API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY", "")

TEAK_COMPOUND = "5dd34337-c4c4-41dd-9c6b-adf84af349a8"


def sign_in_user(email: str, password: str) -> str:
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=headers,
        json=payload,
        timeout=10,
    )
    return response.json()["access_token"]


print("=" * 70)
print("DEBUG: Image Update Constraint Violation")
print("=" * 70)

jwt = sign_in_user("hod.test@alex-short.com", "Password2!")
print("\n✅ Signed in as HOD")

headers = {
    "Authorization": f"Bearer {jwt}",
    "Content-Type": "application/json",
}

payload = {
    "yacht_id": YACHT_ID,
    "image_id": TEAK_COMPOUND,
    "description": "Test update - part has image from previous test",
}

print(f"\nCalling update-image for TEAK_COMPOUND: {TEAK_COMPOUND}")
response = requests.post(
    f"{API_BASE}/v1/parts/update-image",
    headers=headers,
    json=payload,
    timeout=10
)

print(f"\nHTTP {response.status_code}")
print(f"\nFull response:\n{response.text}\n")

if response.status_code == 500:
    import json
    try:
        error_data = response.json()
        print("=" * 70)
        print("ERROR DETAILS:")
        print("=" * 70)
        print(json.dumps(error_data, indent=2))
    except:
        pass
