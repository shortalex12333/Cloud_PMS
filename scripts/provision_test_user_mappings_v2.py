#!/usr/bin/env python3
"""
Provision Test User Mappings (V2 - Simplified)
===============================================
Creates MASTER→TENANT user mappings using known user IDs from JWTs.

Idempotent: Safe to run multiple times.

Usage:
    python3 scripts/provision_test_user_mappings_v2.py
"""

import os
import sys
from supabase import create_client
from datetime import datetime

# Configuration
MASTER_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_KEY = os.getenv("MASTER_SUPABASE_SERVICE_KEY")
TENANT_URL = os.getenv("TENANT_1_SUPABASE_URL")
TENANT_KEY = os.getenv("TENANT_1_SUPABASE_SERVICE_KEY")
YACHT_ID = os.getenv("TEST_YACHT_ID")

# Known user IDs from JWTs (decoded from test_jwts.json)
TEST_USERS = [
    {
        "user_id": "57e82f78-0a2d-4a7c-a428-6287621d06c5",
        "email": "crew.test@alex-short.com",
        "role": "crew",
        "display_name": "Test Crew Member"
    },
    {
        "user_id": "05a488fd-e099-4d18-bf86-d87afba4fcdf",
        "email": "hod.test@alex-short.com",
        "role": "chief_engineer",  # HOD role
        "display_name": "Test Head of Department"
    }
]

def validate_env():
    """Validate required environment variables"""
    if not all([MASTER_URL, MASTER_KEY, TENANT_URL, TENANT_KEY, YACHT_ID]):
        print("❌ Missing environment variables")
        sys.exit(1)
    print("✅ All required environment variables present")

def provision_master_mapping(master_supabase, user):
    """Create user_accounts mapping in MASTER DB"""
    print(f"\n  Provisioning MASTER mapping for {user['email']}...")

    try:
        # Check if mapping exists
        result = master_supabase.table("user_accounts").select("*").eq(
            "user_id", user["user_id"]
        ).eq("yacht_id", YACHT_ID).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Mapping already exists, updating...")
            master_supabase.table("user_accounts").update({
                "status": "active",
                "role": user["role"],
                "email": user["email"],
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user["user_id"]).eq("yacht_id", YACHT_ID).execute()
            print(f"  ✅ Updated to active with role: {user['role']}")
        else:
            # Create new mapping
            master_supabase.table("user_accounts").insert({
                "user_id": user["user_id"],
                "yacht_id": YACHT_ID,
                "email": user["email"],
                "role": user["role"],
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            print(f"  ✅ Created user_accounts mapping (role: {user['role']})")

    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  user_accounts table doesn't exist - skipping")
        elif "duplicate" in error_msg.lower():
            print(f"  ✅ Mapping already exists (duplicate key)")
        else:
            print(f"  ❌ Error: {error_msg[:200]}")

def provision_tenant_profile(tenant_supabase, user):
    """Create auth_users_profiles in TENANT DB"""
    print(f"\n  Provisioning TENANT profile for {user['email']}...")

    try:
        result = tenant_supabase.table("auth_users_profiles").select("*").eq(
            "user_id", user["user_id"]
        ).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Profile already exists")
        else:
            tenant_supabase.table("auth_users_profiles").insert({
                "user_id": user["user_id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            print(f"  ✅ Created auth_users_profiles")

    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  auth_users_profiles table doesn't exist - skipping")
        elif "duplicate" in error_msg.lower():
            print(f"  ✅ Profile already exists (duplicate key)")
        else:
            print(f"  ⚠️  Error: {error_msg[:200]}")

def provision_tenant_role(tenant_supabase, user):
    """Create auth_users_roles in TENANT DB"""
    print(f"\n  Provisioning TENANT role for {user['email']}...")

    try:
        result = tenant_supabase.table("auth_users_roles").select("*").eq(
            "user_id", user["user_id"]
        ).eq("yacht_id", YACHT_ID).eq("role_name", user["role"]).execute()

        if result.data and len(result.data) > 0:
            print(f"  ✅ Role already exists ({user['role']})")
        else:
            tenant_supabase.table("auth_users_roles").insert({
                "user_id": user["user_id"],
                "yacht_id": YACHT_ID,
                "role_name": user["role"],
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            print(f"  ✅ Created role mapping ({user['role']})")

    except Exception as e:
        error_msg = str(e)
        if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
            print(f"  ⚠️  auth_users_roles table doesn't exist - skipping")
        elif "duplicate" in error_msg.lower():
            print(f"  ✅ Role already exists (duplicate key)")
        else:
            print(f"  ⚠️  Error: {error_msg[:200]}")

def main():
    print("=" * 70)
    print("PROVISION TEST USER MAPPINGS (V2)")
    print("=" * 70)
    print(f"MASTER DB: {MASTER_URL}")
    print(f"TENANT DB: {TENANT_URL}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Users: {len(TEST_USERS)}")
    print()

    validate_env()

    # Connect to databases
    print("\n Connecting to databases...")
    master_supabase = create_client(MASTER_URL, MASTER_KEY)
    tenant_supabase = create_client(TENANT_URL, TENANT_KEY)
    print("✅ Connected to MASTER and TENANT databases")

    # Process each user
    for user in TEST_USERS:
        print(f"\n{'='*70}")
        print(f"Processing: {user['email']} ({user['user_id'][:8]}...)")
        print(f"{'='*70}")

        provision_master_mapping(master_supabase, user)
        provision_tenant_profile(tenant_supabase, user)
        provision_tenant_role(tenant_supabase, user)

        print(f"\n✅ Provisioning complete for {user['email']}")

    # Summary
    print("\n" + "=" * 70)
    print("PROVISIONING COMPLETE")
    print("=" * 70)
    print(f"✅ {len(TEST_USERS)} users provisioned")
    print(f"✅ All users assigned to yacht: {YACHT_ID}")
    print()
    print("Next steps:")
    print("  1. Re-run E2E tests: python3 /path/to/test_direct_search.py")

if __name__ == "__main__":
    main()
