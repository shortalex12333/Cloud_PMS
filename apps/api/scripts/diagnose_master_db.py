#!/usr/bin/env python3
"""
Diagnose MASTER DB User/Yacht Mapping
=====================================

Checks user_accounts and fleet_registry to understand yacht_id routing.
"""

import os
import sys
from pathlib import Path

# Load environment variables
env_local = Path(__file__).parent.parent.parent.parent / ".env.local"
if env_local.exists():
    with open(env_local) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from supabase import create_client

# Expected yacht_id from email threads
EXPECTED_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def diagnose():
    """Check MASTER DB user/yacht mapping."""

    # MASTER DB credentials
    url = os.environ.get('MASTER_SUPABASE_URL')
    key = os.environ.get('MASTER_SUPABASE_SERVICE_KEY')

    if not url or not key:
        print("ERROR: Missing MASTER Supabase credentials")
        sys.exit(1)

    print(f"Connecting to MASTER DB: {url[:50]}...")
    supabase = create_client(url, key)

    print("\n" + "=" * 80)
    print("MASTER DB DIAGNOSIS - USER/YACHT MAPPING")
    print("=" * 80)

    # Check user_accounts
    print("\n1. All user_accounts:")
    users = supabase.table('user_accounts').select('*').execute()

    if users.data:
        for user in users.data:
            yacht_match = "✓" if user.get('yacht_id') == EXPECTED_YACHT_ID else "✗ MISMATCH"
            print(f"\n   User ID: {user['id'][:8]}...")
            print(f"   - email: {user.get('email', 'N/A')}")
            print(f"   - yacht_id: {user.get('yacht_id')} {yacht_match}")
            print(f"   - status: {user.get('status')}")
            print(f"   - role: {user.get('role')}")
    else:
        print("   No user_accounts found!")

    # Check fleet_registry
    print("\n2. Fleet registry:")
    fleet = supabase.table('fleet_registry').select('*').execute()

    if fleet.data:
        for vessel in fleet.data:
            print(f"\n   Yacht: {vessel.get('yacht_name', 'N/A')}")
            print(f"   - yacht_id: {vessel.get('yacht_id')}")
            print(f"   - tenant_key_alias: {vessel.get('tenant_key_alias')}")
            print(f"   - active: {vessel.get('active')}")
    else:
        print("   No fleet_registry entries found!")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nExpected yacht_id (from email threads): {EXPECTED_YACHT_ID}")

    mismatched_users = [u for u in users.data if u.get('yacht_id') != EXPECTED_YACHT_ID]
    if mismatched_users:
        print(f"\n⚠️  Found {len(mismatched_users)} user(s) with DIFFERENT yacht_id:")
        for u in mismatched_users:
            print(f"   - {u.get('email', u['id'][:8])}: yacht_id = {u.get('yacht_id')}")
        print("\nThis explains the 404 errors - user is authenticated with different yacht_id")
        print("than the yacht_id on the email threads.")
    else:
        print("\n✓ All users have correct yacht_id")


if __name__ == "__main__":
    diagnose()
