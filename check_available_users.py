#!/usr/bin/env python3
"""
Check Available Users - MASTER vs TENANT
=========================================
Find users that exist in both auth.users (MASTER) and pms_crew_profiles (TENANT)
"""
import os
from supabase import create_client

# Read env file
env_vars = {}
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

# Connect to MASTER (auth.users)
master_url = env_vars['MASTER_SUPABASE_URL']
master_key = env_vars['MASTER_SUPABASE_SERVICE_KEY']
master_db = create_client(master_url, master_key)

# Connect to TENANT (pms_crew_profiles)
tenant_url = env_vars.get('TENANT_SUPABASE_URL') or env_vars.get('TENANT_1_SUPABASE_URL')
tenant_key = env_vars.get('TENANT_SUPABASE_SERVICE_KEY') or env_vars.get('TENANT_1_SUPABASE_SERVICE_KEY')
tenant_db = create_client(tenant_url, tenant_key)

TEST_YACHT_ID = env_vars.get('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')

print("=" * 80)
print("CHECKING AVAILABLE USERS")
print("=" * 80)
print(f"MASTER DB: {master_url}")
print(f"TENANT DB: {tenant_url}")
print(f"TEST YACHT: {TEST_YACHT_ID}")
print()

# Get all users from MASTER auth.users
print("[1] Fetching auth.users from MASTER...")
try:
    # Use admin API to list users
    auth_users = master_db.auth.admin.list_users()
    print(f"✓ Found {len(auth_users)} users in auth.users")
    print()
except Exception as e:
    print(f"✗ Error fetching auth.users: {e}")
    print("Trying alternative method...")
    # Alternative: query directly if admin API doesn't work
    auth_users = []

# Get all crew profiles from TENANT
print("[2] Fetching pms_crew_profiles from TENANT...")
try:
    crew_profiles = tenant_db.table("pms_crew_profiles").select("*").execute()
    print(f"✓ Found {len(crew_profiles.data)} crew profiles")
    print()
except Exception as e:
    print(f"✗ Error fetching crew profiles: {e}")
    crew_profiles = None

# Get profiles for test yacht specifically
print(f"[3] Fetching crew profiles for yacht {TEST_YACHT_ID}...")
try:
    yacht_crew = tenant_db.table("pms_crew_profiles").select("*").eq(
        "yacht_id", TEST_YACHT_ID
    ).execute()
    print(f"✓ Found {len(yacht_crew.data)} crew members on test yacht")
    print()
except Exception as e:
    print(f"✗ Error fetching yacht crew: {e}")
    yacht_crew = None

# Display yacht crew details
if yacht_crew and yacht_crew.data:
    print("=" * 80)
    print("CREW ON TEST YACHT")
    print("=" * 80)
    for crew in yacht_crew.data:
        print(f"Name: {crew.get('name', 'N/A')}")
        print(f"  User ID: {crew.get('user_id')}")
        print(f"  Email: {crew.get('email', 'N/A')}")
        print(f"  Role: {crew.get('role', 'N/A')}")
        print(f"  Department: {crew.get('department', 'N/A')}")
        print(f"  Status: {crew.get('status', 'N/A')}")
        print()

# Try to find matching users
if auth_users and yacht_crew and yacht_crew.data:
    print("=" * 80)
    print("MATCHING USERS (Auth + Crew Profile)")
    print("=" * 80)

    # Build set of user IDs from auth
    auth_user_ids = set()
    auth_user_map = {}

    if hasattr(auth_users, '__iter__'):
        for user in auth_users:
            if hasattr(user, 'id'):
                auth_user_ids.add(user.id)
                auth_user_map[user.id] = user.email

    matched = 0
    for crew in yacht_crew.data:
        user_id = crew.get('user_id')
        if user_id in auth_user_ids:
            matched += 1
            print(f"✓ MATCH: {crew.get('name', 'N/A')}")
            print(f"  User ID: {user_id}")
            print(f"  Email: {auth_user_map.get(user_id, 'N/A')}")
            print(f"  Role: {crew.get('role', 'N/A')}")
            print(f"  Department: {crew.get('department', 'N/A')}")
            print()

    print(f"Total matched: {matched}/{len(yacht_crew.data)}")

# Check for specific test users
print("=" * 80)
print("CHECKING SPECIFIC TEST USERS")
print("=" * 80)

test_users = [
    ("b72c35ff-e309-4a19-a617-bfc706a78c0f", "captain.tenant@alex-short.com"),
    ("05a488fd-e099-4d18-bf86-d87afba4fcdf", "hod.test@alex-short.com"),
    ("57e82f78-0a2d-4a7c-a428-6287621d06c5", "crew.test@alex-short.com"),
]

for user_id, email in test_users:
    print(f"\nChecking {email} ({user_id})...")

    # Check in crew profiles
    try:
        profile = tenant_db.table("pms_crew_profiles").select("*").eq(
            "user_id", user_id
        ).execute()

        if profile.data:
            print(f"  ✓ Found in pms_crew_profiles")
            for p in profile.data:
                print(f"    Yacht: {p.get('yacht_id')}")
                print(f"    Role: {p.get('role')}")
                print(f"    Department: {p.get('department')}")
        else:
            print(f"  ✗ NOT in pms_crew_profiles")
    except Exception as e:
        print(f"  ✗ Error checking profile: {e}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total crew on yacht: {len(yacht_crew.data) if yacht_crew else 0}")
print(f"Usable for testing: Check MATCHING USERS section above")
