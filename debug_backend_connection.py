#!/usr/bin/env python3
"""Debug: Why is backend API not finding parts that exist?"""

import requests
import os

API_BASE = "https://pipeline-core.int.celeste7.ai"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEAK_COMPOUND = "5dd34337-c4c4-41dd-9c6b-adf84af349a8"
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
print("✅ Signed in")

# Try to upload image
print(f"\nUploading image for part {TEAK_COMPOUND}...")

import base64
png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
png_bytes = base64.b64decode(png_base64)

files = {"file": ("test.png", png_bytes, "image/png")}
data = {
    "yacht_id": YACHT_ID,
    "part_id": TEAK_COMPOUND,
    "description": "Test upload",
}

response = requests.post(
    f"{API_BASE}/v1/parts/upload-image",
    headers={"Authorization": f"Bearer {jwt}"},
    files=files,
    data=data,
    timeout=30
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}\n")

if response.status_code == 400:
    print("❌ Part not found - but it EXISTS in database!")
    print("\nPossible causes:")
    print("1. Backend connecting to WRONG database")
    print("2. Backend using wrong tenant credentials")
    print("3. Backend yacht_id mismatch in query")
    print("4. Backend missing environment variables")
elif response.status_code == 200:
    print("✅ Upload successful - everything works!")

