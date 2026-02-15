#!/usr/bin/env python3
"""Test image upload with a part that has NO image yet."""

import requests
import os
import base64

API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Try different part (Fuel Filter Generator)
FRESH_PART = "f7913ad1-6832-4169-b816-4538c8b7a417"

SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")

def sign_in():
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=headers,
        json={"email": "x@alex-short.com", "password": "Password2!"},
        timeout=10,
    )
    return response.json()["access_token"]

jwt = sign_in()
print(f"Testing with fresh part: {FRESH_PART}")

png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
png_bytes = base64.b64decode(png_base64)

files = {"file": ("test.png", png_bytes, "image/png")}
data = {
    "yacht_id": YACHT_ID,
    "part_id": FRESH_PART,
    "description": "Fresh part test upload",
}

response = requests.post(
    f"{API_BASE}/v1/parts/upload-image",
    headers={"Authorization": f"Bearer {jwt}"},
    files=files,
    data=data,
    timeout=30
)

print(f"\nStatus: {response.status_code}")
if response.status_code == 200:
    print("✅✅✅ EVERYTHING WORKS! ✅✅✅")
    print(f"Response: {response.json()}")
elif response.status_code == 500 and "duplicate key" in response.text:
    print("❌ This part also has image already (DB trigger issue)")
else:
    print(f"Response: {response.text}")

