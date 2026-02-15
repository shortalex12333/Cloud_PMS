#!/usr/bin/env python3
"""Test the exact query the backend runs."""

import os
from pathlib import Path

env_local = Path(__file__).parent.parent.parent.parent / ".env.local"
if env_local.exists():
    with open(env_local) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from supabase import create_client

THREAD_ID = "a0e5b26b-e791-4896-8f15-c7da5a692f00"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
OUTLOOK_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"  # x@alex-short.com
HOD_USER_ID = "05a488fd-e099-4d18-bf86-d87afba4fcdf"  # hod.test@alex-short.com

url = os.environ.get('TENANT_SUPABASE_URL')
key = os.environ.get('TENANT_SUPABASE_SERVICE_KEY')

print(f"Connecting to: {url[:50]}...")
supabase = create_client(url, key)

print("\n" + "=" * 70)
print("SIMULATING BACKEND QUERIES")
print("=" * 70)

def test_user(user_id, user_name):
    print(f"\n--- Testing as {user_name} (user_id: {user_id[:8]}...) ---")

    # Step 1: Get watcher_id (same as backend)
    watcher_result = supabase.table('email_watchers').select('id').eq(
        'user_id', user_id
    ).eq('yacht_id', YACHT_ID).eq('sync_status', 'active').limit(1).execute()

    watcher_id = watcher_result.data[0]['id'] if watcher_result.data else None
    print(f"  1. Watcher lookup: {watcher_id or 'None (no watcher)'}")

    # Step 2: Build thread query (same as backend)
    thread_query = supabase.table('email_threads').select('id, watcher_id, latest_subject').eq(
        'id', THREAD_ID
    ).eq('yacht_id', YACHT_ID)

    # Step 3: Apply watcher_id filter if present
    if watcher_id:
        thread_query = thread_query.or_(f"watcher_id.eq.{watcher_id},watcher_id.is.null")
        print(f"  2. Added watcher_id filter: watcher_id={watcher_id} OR watcher_id IS NULL")
    else:
        print(f"  2. No watcher_id filter (user has no watcher)")

    # Step 4: Execute query
    thread_result = thread_query.limit(1).execute()

    if thread_result.data:
        t = thread_result.data[0]
        print(f"  3. ✓ FOUND: {t['latest_subject'][:50]}")
    else:
        print(f"  3. ✗ NOT FOUND (404)")

        # Check if thread exists at all
        check = supabase.table('email_threads').select('id, watcher_id').eq('id', THREAD_ID).execute()
        if check.data:
            print(f"     Thread exists with watcher_id: {check.data[0]['watcher_id']}")
            print(f"     But filter excluded it!")

# Test as the outlook user
test_user(OUTLOOK_USER_ID, "x@alex-short.com (Outlook connected)")

# Test as HOD user (no outlook connection)
test_user(HOD_USER_ID, "hod.test@alex-short.com (No Outlook)")

print("\n" + "=" * 70)
