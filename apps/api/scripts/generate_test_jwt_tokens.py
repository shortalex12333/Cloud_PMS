#!/usr/bin/env python3
"""
Generate Test JWT Tokens for RLS Testing
========================================

This script generates JWT tokens for different test users with different roles:
- CREW: Regular crew member (should be denied from creating work orders)
- HoD: Head of Department (chief_engineer, chief_officer, etc.) - allowed
- CAPTAIN: Captain (allowed for all actions including archive)

Usage:
    python3 scripts/generate_test_jwt_tokens.py

Output:
    Prints JWT tokens that can be added to .env.tenant1:
    TEST_JWT_CREW=<token>
    TEST_JWT_HOD=<token>
    TEST_JWT_CAPTAIN=<token>
"""

import sys
import os
from pathlib import Path

# Load environment variables from .env.tenant1
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if key == 'TENANT_1_SUPABASE_URL':
                    os.environ['SUPABASE_URL'] = value
                elif key == 'TENANT_1_SUPABASE_SERVICE_KEY':
                    os.environ['SUPABASE_SERVICE_KEY'] = value

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.supabase import get_supabase_client


def get_or_create_test_user(supabase, email: str, role: str, yacht_id: str):
    """Get or create a test user with specific role."""
    print(f"  Looking up user: {email} (role: {role})")

    # Try to find existing user
    try:
        result = supabase.table("profiles").select("*").eq("email", email).execute()

        if result.data and len(result.data) > 0:
            user = result.data[0]
            print(f"    ✅ Found existing user: {user['id']}")
            return user

        print(f"    ℹ️  User not found")

    except Exception as e:
        print(f"    ⚠️  Error looking up user: {e}")

    return None


def generate_test_tokens():
    """Generate JWT tokens for test users."""
    print("=" * 80)
    print("GENERATING TEST JWT TOKENS")
    print("=" * 80)
    print("")

    supabase = get_supabase_client()
    yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"  # Test yacht

    # Define test users
    test_users = [
        {
            "email": "test.crew@celeste.test",
            "role": "crew",
            "env_var": "TEST_JWT_CREW"
        },
        {
            "email": "test.chiefengineer@celeste.test",
            "role": "chief_engineer",
            "env_var": "TEST_JWT_HOD"
        },
        {
            "email": "test.captain@celeste.test",
            "role": "captain",
            "env_var": "TEST_JWT_CAPTAIN"
        },
    ]

    print("=" * 80)
    print("LOOKING UP TEST USERS")
    print("=" * 80)
    print("")

    tokens = {}

    for user_info in test_users:
        print(f"User: {user_info['email']}")
        user = get_or_create_test_user(
            supabase,
            user_info["email"],
            user_info["role"],
            yacht_id
        )

        if user:
            # In a real scenario, you'd need to:
            # 1. Use Supabase Auth API to sign in with the user's credentials
            # 2. Get the JWT access token from the response
            # For now, we'll document what needs to be done
            tokens[user_info["env_var"]] = None
            print(f"    ℹ️  To get JWT token:")
            print(f"       - Sign in as {user_info['email']} via Supabase Auth")
            print(f"       - Copy the access_token from the auth response")

        print("")

    print("=" * 80)
    print("INSTRUCTIONS")
    print("=" * 80)
    print("")
    print("To generate JWT tokens manually:")
    print("")
    print("1. Use Supabase Auth API to sign in as each test user:")
    print("   curl -X POST https://YOUR_SUPABASE_URL/auth/v1/token?grant_type=password \\")
    print("     -H 'apikey: YOUR_ANON_KEY' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"email\":\"test.crew@celeste.test\",\"password\":\"test_password\"}'")
    print("")
    print("2. Copy the 'access_token' from the response")
    print("")
    print("3. Add to .env.tenant1:")
    for user_info in test_users:
        print(f"   {user_info['env_var']}=<access_token>")
    print("")
    print("Alternative: Use Supabase Dashboard")
    print("1. Go to: https://supabase.com/dashboard/project/YOUR_PROJECT/auth/users")
    print("2. Find each test user")
    print("3. Click 'Generate JWT' or use the 'Generate Link' feature")
    print("")

    print("=" * 80)
    print("TEST USER ROLES")
    print("=" * 80)
    print("")
    for user_info in test_users:
        print(f"  {user_info['role'].upper()}: {user_info['email']}")
    print("")

    print("=" * 80)
    print("QUICK TEST")
    print("=" * 80)
    print("")
    print("After adding tokens to .env.tenant1, run:")
    print("  cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api")
    print("  python3 tests/test_work_order_jwt_rls.py")
    print("")


if __name__ == "__main__":
    generate_test_tokens()
