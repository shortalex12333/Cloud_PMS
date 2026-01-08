#!/usr/bin/env python3
"""
Quick diagnostic script to check user yacht assignment
"""
from supabase import create_client
import json
import os

# Supabase credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "YOUR_SERVICE_ROLE_KEY_HERE")

# User from logs
USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
USER_EMAIL = "x@alex-short.com"

def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 60)
    print("CelesteOS User Yacht Assignment Diagnostic")
    print("=" * 60)
    print(f"\nUser ID: {USER_ID}")
    print(f"Email: {USER_EMAIL}\n")

    # Check auth_users table
    print("1️⃣  Checking auth_users table...")
    try:
        user = client.table('auth_users').select('*').eq('id', USER_ID).execute()
        if user.data:
            print(f"   ✅ User found: {user.data[0].get('email')}")
            print(f"   Columns: {list(user.data[0].keys())}")
        else:
            print(f"   ⚠️  User not found in auth_users")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check auth_users_yacht table
    print("\n2️⃣  Checking auth_users_yacht table...")
    try:
        yacht_link = client.table('auth_users_yacht').select('*').eq('user_id', USER_ID).execute()
        if yacht_link.data:
            print(f"   ✅ Yacht assignment found!")
            print(f"   Data: {json.dumps(yacht_link.data[0], indent=4)}")
        else:
            print(f"   ❌ No yacht assigned to this user!")
            print(f"   This is why search returns no results.")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check auth_role_assignments
    print("\n3️⃣  Checking auth_role_assignments table...")
    try:
        roles = client.table('auth_role_assignments').select('*').eq('user_id', USER_ID).execute()
        if roles.data:
            print(f"   ✅ Found {len(roles.data)} role(s)")
            for role in roles.data:
                print(f"   - Role ID: {role.get('role_id')}, Yacht: {role.get('yacht_id')}")
        else:
            print(f"   ⚠️  No roles assigned")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # List available yachts
    print("\n4️⃣  Available yachts...")
    try:
        yachts = client.table('yachts').select('id, name, status').limit(5).execute()
        if yachts.data:
            print(f"   ✅ Found {len(yachts.data)} yacht(s)")
            for yacht in yachts.data:
                print(f"   - {yacht['name']} (ID: {yacht['id']}, Status: {yacht['status']})")
        else:
            print(f"   ⚠️  No yachts found")
    except Exception as e:
        print(f"   ❌ Error checking yachts: {e}")

    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
