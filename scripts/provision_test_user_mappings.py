#!/usr/bin/env python3
"""
Provision Test User Mappings
=============================
Creates MASTER→TENANT user mappings for E2E testing.

Idempotent: Safe to run multiple times.

Requirements:
- MASTER_SUPABASE_URL, MASTER_SUPABASE_SERVICE_KEY
- TENANT_1_SUPABASE_URL, TENANT_1_SUPABASE_SERVICE_KEY
- TEST_YACHT_ID, TEST_CREW_USER_EMAIL, TEST_HOD_USER_EMAIL, ALL_TEST_USER_PASSWORD

Creates:
1. MASTER DB: user_accounts rows (user_id → yacht_id + role)
2. TENANT DB: auth_users_profiles, auth_users_roles

Usage:
    python3 scripts/provision_test_user_mappings.py
"""

import os
import sys
from supabase import create_client
from datetime import datetime

# Configuration from environment
MASTER_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SERVICE_KEY = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
MASTER_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")
TENANT_URL = os.getenv("TENANT_1_SUPABASE_URL")
TENANT_SERVICE_KEY = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")
TENANT_ANON_KEY = os.getenv("TENANT_SUPABASE_ANON_KEY")
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
        ("MASTER_SUPABASE_ANON_KEY", MASTER_ANON_KEY),
        ("TENANT_1_SUPABASE_URL", TENANT_URL),
        ("TENANT_1_SUPABASE_SERVICE_KEY", TENANT_SERVICE_KEY),
        ("TENANT_SUPABASE_ANON_KEY", TENANT_ANON_KEY),
        ("TEST_YACHT_ID", YACHT_ID),
    ]

    missing = [name for name, value in required if not value]
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nLoad from env vars.md:")
        print("  export MASTER_SUPABASE_URL=...")
        print("  export MASTER_SUPABASE_SERVICE_KEY=...")
        print("  export MASTER_SUPABASE_ANON_KEY=...")
        print("  export TENANT_1_SUPABASE_URL=...")
        print("  export TENANT_1_SUPABASE_SERVICE_KEY=...")
        print("  export TENANT_SUPABASE_ANON_KEY=...")
        print("  export TEST_YACHT_ID=...")
        sys.exit(1)

    print("✅ All required environment variables present")

def ensure_user_exists(master_supabase, user_config):
    """Ensure user exists in Supabase Auth - get user ID by signing in"""
    email = user_config["email"]

    print(f"\n{'='*70}")
    print(f"Processing: {email}")
    print(f"{'='*70}")

    # Sign in to get user ID (assumes user already exists from previous setup)
    print(f"  Authenticating as {email}...")
    try:
        auth_response = master_supabase.auth.sign_in_with_password({
            "email": email,
            "password": PASSWORD
        })
        user_id = auth_response.user.id
        print(f"✅ Authenticated successfully: {user_id}")
        return user_id
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Authentication failed: {error_msg[:200]}")
        print(f"  User may not exist or password is incorrect")
        print(f"  Email: {email}")
        print(f"  Expected password: {PASSWORD}")
        sys.exit(1)

def provision_master_mapping(master_supabase, user_id, user_config):
    """Create user_accounts mapping in MASTER DB"""
    email = user_config["email"]
    role = user_config["role"]

    print(f"\n  Provisioning MASTER mapping...")

    # Check if mapping exists
    try:
        result = master_supabase.table("user_accounts").select("*").eq(
            "user_id", user_id
        ).eq("yacht_id", YACHT_ID).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Mapping already exists")
            # Update to ensure active
            master_supabase.table("user_accounts").update({
                "status": "active",
                "role": role,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).eq("yacht_id", YACHT_ID).execute()
            print(f"  ✅ Updated status to active")
            return
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  user_accounts table doesn't exist in MASTER - skipping")
            return
        print(f"  ⚠️  Could not check existing mapping: {str(e)[:200]}")

    # Create mapping
    try:
        master_supabase.table("user_accounts").insert({
            "user_id": user_id,
            "yacht_id": YACHT_ID,
            "email": email,
            "role": role,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        print(f"  ✅ Created user_accounts mapping (role: {role})")
    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
            print(f"  ✅ Mapping already exists (duplicate key)")
        else:
            print(f"  ❌ Failed to create mapping: {error_msg[:200]}")

def provision_tenant_profile(tenant_supabase, user_id, user_config):
    """Create auth_users_profiles in TENANT DB"""
    email = user_config["email"]
    display_name = user_config["display_name"]

    print(f"\n  Provisioning TENANT profile...")

    # Check if table exists
    try:
        result = tenant_supabase.table("auth_users_profiles").select("*").eq(
            "user_id", user_id
        ).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Profile already exists")
            return
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  auth_users_profiles table doesn't exist - skipping")
            return

    # Create profile
    try:
        tenant_supabase.table("auth_users_profiles").insert({
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        print(f"  ✅ Created auth_users_profiles")
    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower():
            print(f"  ✅ Profile already exists (duplicate key)")
        else:
            print(f"  ⚠️  Could not create profile: {error_msg[:200]}")

def provision_tenant_role(tenant_supabase, user_id, user_config):
    """Create auth_users_roles in TENANT DB"""
    role = user_config["role"]

    print(f"\n  Provisioning TENANT role...")

    # Check if table exists and role exists
    try:
        result = tenant_supabase.table("auth_users_roles").select("*").eq(
            "user_id", user_id
        ).eq("yacht_id", YACHT_ID).eq("role_name", role).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Role already exists ({role})")
            return
    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  auth_users_roles table doesn't exist - skipping")
            return

    # Create role
    try:
        tenant_supabase.table("auth_users_roles").insert({
            "user_id": user_id,
            "yacht_id": YACHT_ID,
            "role_name": role,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        print(f"  ✅ Created role mapping ({role})")
    except Exception as e:
        error_msg = str(e)
        if "duplicate" in error_msg.lower():
            print(f"  ✅ Role already exists (duplicate key)")
        else:
            print(f"  ⚠️  Could not create role: {error_msg[:200]}")

def main():
    print("=" * 70)
    print("PROVISION TEST USER MAPPINGS")
    print("=" * 70)
    print(f"MASTER DB: {MASTER_URL}")
    print(f"TENANT DB: {TENANT_URL}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Users to provision: {len(TEST_USERS)}")
    print()

    # Validate environment
    validate_env()

    # Connect to databases
    print("\n Connecting to databases...")
    # Auth client (uses anon key for sign-in)
    master_auth = create_client(MASTER_URL, MASTER_ANON_KEY)
    # Service clients (use service keys for database operations)
    master_supabase = create_client(MASTER_URL, MASTER_SERVICE_KEY)
    tenant_supabase = create_client(TENANT_URL, TENANT_SERVICE_KEY)
    print("✅ Connected to MASTER and TENANT databases")

    # Process each user
    for user_config in TEST_USERS:
        # 1. Ensure user exists in auth.users (use anon client)
        user_id = ensure_user_exists(master_auth, user_config)

        # 2. Create MASTER mapping (use service client)
        provision_master_mapping(master_supabase, user_id, user_config)

        # 3. Create TENANT profile (use service client)
        provision_tenant_profile(tenant_supabase, user_id, user_config)

        # 4. Create TENANT role (use service client)
        provision_tenant_role(tenant_supabase, user_id, user_config)

        print(f"\n✅ Provisioning complete for {user_config['email']}")

    # Summary
    print("\n" + "=" * 70)
    print("PROVISIONING COMPLETE")
    print("=" * 70)
    print(f"✅ {len(TEST_USERS)} users provisioned")
    print(f"✅ All users assigned to yacht: {YACHT_ID}")
    print()
    print("Next steps:")
    print("  1. Verify with: python3 scripts/verify_user_mappings.py")
    print("  2. Run E2E tests: docker-compose -f docker-compose.test.yml up")

if __name__ == "__main__":
    main()
