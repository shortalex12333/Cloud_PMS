#!/usr/bin/env python3
"""
Generate Fresh JWT Tokens for E2E Testing
==========================================

This script signs in test users to Supabase Auth and retrieves fresh JWTs.

Usage:
    python3 generate_fresh_tokens.py

Requirements:
    - User passwords in environment variables or prompted
    - Supabase Auth URL
"""

import os
import requests
import json
from datetime import datetime
from getpass import getpass

# Supabase Auth Configuration (MASTER DB for auth)
SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL", "https://qvzmkaamzaqxpzbewjxe.supabase.co")
AUTH_URL = f"{SUPABASE_URL}/auth/v1"
ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")  # Public anon key for auth

# Test Users
USERS = {
    "CAPTAIN": {
        "email": "captain.tenant@alex-short.com",
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "role": "captain",
    },
    "HOD": {
        "email": "hod.tenant@alex-short.com",
        "user_id": "89b1262c-ff59-4591-b954-757cdf3d609d",
        "role": "chief_engineer",
    },
    "CREW": {
        "email": "crew.tenant@alex-short.com",
        "user_id": "2da12a4b-c0a1-4716-80ae-d29c90d98233",
        "role": "crew",
    },
}

def sign_in_user(email: str, password: str) -> dict:
    """Sign in a user and get JWT token."""
    headers = {
        "apikey": ANON_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "email": email,
        "password": password
    }

    response = requests.post(
        f"{AUTH_URL}/token?grant_type=password",
        headers=headers,
        json=payload,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data["expires_at"],
            "user": data["user"]
        }
    else:
        raise Exception(f"Sign-in failed: HTTP {response.status_code} - {response.text}")

def main():
    print("=" * 70)
    print("GENERATE FRESH JWT TOKENS FOR E2E TESTING")
    print("=" * 70)

    if not ANON_KEY:
        print("❌ ERROR: SUPABASE_ANON_KEY environment variable not set")
        print("\nTo set it, run:")
        print("  export SUPABASE_ANON_KEY='your-anon-key'")
        return

    print("\nThis script will sign in test users and generate fresh JWTs.")
    print("You'll need the passwords for each test user.\n")

    fresh_tokens = {}

    for role_name, user_info in USERS.items():
        print(f"\n📧 {role_name}: {user_info['email']}")

        # Get password (check env var first, then prompt)
        password_env_var = f"{role_name}_PASSWORD"
        password = os.getenv(password_env_var)

        if not password:
            password = getpass(f"   Enter password for {user_info['email']}: ")

        if not password:
            print(f"   ⏭️  Skipping {role_name} (no password provided)")
            continue

        try:
            result = sign_in_user(user_info['email'], password)
            jwt = result['access_token']
            expires_at = result['expires_at']

            # Decode expiration time
            exp_dt = datetime.fromtimestamp(expires_at)
            mins_until_exp = int((exp_dt - datetime.now()).total_seconds() / 60)

            print(f"   ✅ Signed in successfully!")
            print(f"   ⏰ Expires: {exp_dt} (in {mins_until_exp} minutes)")
            print(f"   🔑 JWT: {jwt[:50]}...")

            fresh_tokens[role_name] = {
                **user_info,
                "jwt": jwt,
                "expires_at": expires_at,
                "expires_at_iso": exp_dt.isoformat(),
            }
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue

    if not fresh_tokens:
        print("\n❌ No tokens generated. Exiting.")
        return

    # Save to JSON file
    output_file = "test-results/fresh_tokens.json"
    with open(output_file, "w") as f:
        json.dump(fresh_tokens, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"✅ Generated {len(fresh_tokens)} fresh tokens")
    print(f"📄 Saved to: {output_file}")
    print(f"{'=' * 70}")

    # Print Python code to update test file
    print("\n📋 Copy this to update your test file:\n")
    print("USERS = {")
    for role_name, token_info in fresh_tokens.items():
        print(f'    "{role_name}": {{')
        print(f'        "email": "{token_info["email"]}",')
        print(f'        "user_id": "{token_info["user_id"]}",')
        print(f'        "jwt": "{token_info["jwt"]}",')
        print(f'        "role": "{token_info["role"]}",')
        print(f'    }},')
    print("}")

if __name__ == "__main__":
    main()
