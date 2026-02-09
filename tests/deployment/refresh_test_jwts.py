"""
Refresh test JWTs by logging in with username/password.

This logs into MASTER Supabase and gets fresh access tokens.
"""

import os
import json
import requests

# MASTER Supabase credentials
MASTER_URL = os.getenv("MASTER_SUPABASE_URL", "https://qvzmkaamzaqxpzbewjxe.supabase.co")
MASTER_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")

if not MASTER_ANON_KEY:
    print("❌ MASTER_SUPABASE_ANON_KEY not set")
    print("   Set it in your environment")
    exit(1)

# Test users with passwords
TEST_USERS = {
    "CREW": {
        "email": "crew.tenant@alex-short.com",
        "password": os.getenv("CREW_PASSWORD"),
        "role": "crew"
    },
    "HOD": {
        "email": "hod.tenant@alex-short.com",
        "password": os.getenv("HOD_PASSWORD"),
        "role": "hod"
    },
    "CAPTAIN": {
        "email": "captain.tenant@alex-short.com",
        "password": os.getenv("CAPTAIN_PASSWORD"),
        "role": "captain"
    }
}

print("="*80)
print("REFRESHING TEST JWTS")
print("="*80)
print(f"\nMASTER URL: {MASTER_URL}")
print()

tokens = {}

for role, user in TEST_USERS.items():
    email = user["email"]
    password = user["password"]

    if not password:
        print(f"{role} ({email}): ⚠️  Password not set (env: {role}_PASSWORD)")
        continue

    print(f"{role} ({email}): Logging in...")

    # Login to MASTER Supabase
    response = requests.post(
        f"{MASTER_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": MASTER_ANON_KEY,
            "Content-Type": "application/json"
        },
        json={
            "email": email,
            "password": password
        }
    )

    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access_token")
        user_id = data.get("user", {}).get("id")

        tokens[role] = {
            "email": email,
            "user_id": user_id,
            "role": user["role"],
            "jwt": access_token
        }

        print(f"  ✅ Success")
        print(f"     User ID: {user_id}")
        print(f"     JWT: {access_token[:50]}...")
    else:
        print(f"  ❌ Failed: {response.status_code}")
        print(f"     {response.text}")

print("\n" + "="*80)

if tokens:
    # Write to file
    with open("test-jwts.json", "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"\n✅ Updated test-jwts.json with {len(tokens)} users")
    print("\nYou can now run:")
    print("  python3 tests/deployment/verify_deployment_quick.py")
else:
    print("\n❌ No tokens generated")
    print("\nSet passwords:")
    print("  export CREW_PASSWORD='...'")
    print("  export HOD_PASSWORD='...'")
    print("  export CAPTAIN_PASSWORD='...'")

print("="*80)
