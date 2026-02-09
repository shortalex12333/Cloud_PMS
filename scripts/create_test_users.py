#!/usr/bin/env python3
"""
Create Test Users in Supabase Auth
===================================
Creates CREW and HOD users in Supabase auth.users table.

This must be run BEFORE provision_test_user_mappings.py.

Requirements:
- MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY
- TEST_CREW_USER_EMAIL, TEST_HOD_USER_EMAIL, ALL_TEST_USER_PASSWORD
- TEST_YACHT_ID

Creates:
1. auth.users entries for CREW and HOD
2. Sets user_metadata with role and yacht_id

Usage:
    python3 scripts/create_test_users.py
"""

import os
import sys
import requests
from datetime import datetime

# Configuration from environment
MASTER_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SERVICE_KEY = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
YACHT_ID = os.getenv("TEST_YACHT_ID")

TEST_USERS = [
    {
        "email": os.getenv("TEST_CREW_USER_EMAIL", "crew.test@alex-short.com"),
        "role": "crew",
        "display_name": "Test Crew Member"
    },
    {
        "email": os.getenv("TEST_HOD_USER_EMAIL", "hod.test@alex-short.com"),
        "role": "chief_engineer",  # HOD in this system
        "display_name": "Test Head of Department"
    }
]

PASSWORD = os.getenv("ALL_TEST_USER_PASSWORD", "Password2!")

def validate_env():
    """Validate required environment variables"""
    required = [
        ("MASTER_SUPABASE_URL", MASTER_URL),
        ("MASTER_SUPABASE_SERVICE_KEY", MASTER_SERVICE_KEY),
        ("TEST_YACHT_ID", YACHT_ID),
    ]

    missing = [name for name, value in required if not value]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("✅ All required environment variables present")

def create_user_via_admin_api(user_config):
    """Create user using Supabase Admin API"""
    email = user_config["email"]
    role = user_config["role"]

    print(f"\n{'='*70}")
    print(f"Creating user: {email}")
    print(f"{'='*70}")

    # Use Supabase Admin API to create user
    url = f"{MASTER_URL}/auth/v1/admin/users"
    headers = {
        "apikey": MASTER_SERVICE_KEY,
        "Authorization": f"Bearer {MASTER_SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "email": email,
        "password": PASSWORD,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "role": role,
            "yacht_id": YACHT_ID,
            "display_name": user_config["display_name"],
            "email_verified": True
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200 or response.status_code == 201:
            user_data = response.json()
            user_id = user_data.get("id")
            print(f"✅ User created successfully")
            print(f"   User ID: {user_id}")
            print(f"   Email: {email}")
            print(f"   Role: {role}")
            print(f"   Yacht ID: {YACHT_ID}")
            return user_id
        elif response.status_code == 422:
            # User already exists
            error_data = response.json()
            if "already been registered" in str(error_data):
                print(f"✅ User already exists: {email}")
                # Try to get user ID by signing in
                auth_url = f"{MASTER_URL}/auth/v1/token?grant_type=password"
                auth_headers = {
                    "apikey": MASTER_SERVICE_KEY,
                    "Content-Type": "application/json"
                }
                auth_payload = {
                    "email": email,
                    "password": PASSWORD
                }
                auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    user_id = auth_data.get("user", {}).get("id")
                    print(f"   User ID: {user_id}")
                    return user_id
                else:
                    print(f"   ⚠️  Could not get user ID (auth failed)")
                    return None
            else:
                print(f"❌ Unexpected 422 error: {error_data}")
                return None
        else:
            print(f"❌ Failed to create user: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception creating user: {e}")
        return None

def verify_user_login(email):
    """Verify user can log in"""
    print(f"\n  Verifying login for {email}...")

    url = f"{MASTER_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_SERVICE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": PASSWORD
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            jwt = data.get("access_token")
            print(f"  ✅ Login successful")
            print(f"     JWT: {jwt[:50]}...")
            return jwt
        else:
            print(f"  ❌ Login failed: {response.status_code}")
            print(f"     Response: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Login exception: {e}")
        return None

def main():
    print("=" * 70)
    print("CREATE TEST USERS IN SUPABASE AUTH")
    print("=" * 70)
    print(f"MASTER DB: {MASTER_URL}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Users to create: {len(TEST_USERS)}")
    print()

    # Validate environment
    validate_env()

    # Create each user
    created_users = []
    for user_config in TEST_USERS:
        user_id = create_user_via_admin_api(user_config)
        if user_id:
            created_users.append({
                "email": user_config["email"],
                "user_id": user_id,
                "role": user_config["role"]
            })

    # Verify logins
    print("\n" + "=" * 70)
    print("VERIFYING USER LOGINS")
    print("=" * 70)

    for user in created_users:
        verify_user_login(user["email"])

    # Summary
    print("\n" + "=" * 70)
    print("USER CREATION COMPLETE")
    print("=" * 70)
    print(f"✅ {len(created_users)} users created/verified")
    print()
    print("Users created:")
    for user in created_users:
        print(f"  - {user['email']} ({user['role']}) - ID: {user['user_id']}")
    print()
    print("Next steps:")
    print("  1. Run: python3 scripts/provision_test_user_mappings.py")
    print("  2. Verify with: python3 scripts/verify_user_mappings.py")

if __name__ == "__main__":
    main()
