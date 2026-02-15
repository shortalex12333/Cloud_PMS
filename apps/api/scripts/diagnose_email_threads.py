#!/usr/bin/env python3
"""
Diagnose Email Thread 404 Errors
================================

Checks yacht_id assignment for threads that return 404.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env.tenant1
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    print(f"Loading env from: {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Also try .env.local for additional vars
env_local = Path(__file__).parent.parent.parent.parent / ".env.local"
if env_local.exists():
    print(f"Loading env from: {env_local}")
    with open(env_local) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value

from supabase import create_client

# Thread IDs that are returning 404
FAILING_THREAD_IDS = [
    "a0e5b26b-e791-4896-8f15-c7da5a692f00",
    "b1711439-7409-442d-b4b5-3fe16bcef379",
    "beb4bb89-b250-4279-ab5a-f06eca9a303b",
    "edfe0943-0921-4546-b824-43957535e3d1",
]

def diagnose():
    """Check yacht_id for failing threads."""

    # Get Supabase credentials
    url = os.environ.get('TENANT_1_SUPABASE_URL') or os.environ.get('yTEST_YACHT_001_SUPABASE_URL') or os.environ.get('SUPABASE_URL')
    key = os.environ.get('TENANT_1_SUPABASE_SERVICE_KEY') or os.environ.get('yTEST_YACHT_001_SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_SERVICE_KEY')

    if not url or not key:
        print("ERROR: Missing Supabase credentials")
        print(f"  URL: {'set' if url else 'MISSING'}")
        print(f"  KEY: {'set' if key else 'MISSING'}")
        sys.exit(1)

    print(f"\nConnecting to: {url[:50]}...")
    supabase = create_client(url, key)

    print("\n" + "=" * 80)
    print("DIAGNOSING EMAIL THREAD 404 ERRORS")
    print("=" * 80)

    # First, get all distinct yacht_ids in email_threads
    print("\n1. Checking all yacht_ids in email_threads table...")
    yacht_result = supabase.table('email_threads').select('yacht_id').execute()
    unique_yachts = set(t['yacht_id'] for t in yacht_result.data if t.get('yacht_id'))
    print(f"   Found {len(yacht_result.data)} threads across {len(unique_yachts)} yacht(s):")
    for yacht in unique_yachts:
        count = sum(1 for t in yacht_result.data if t.get('yacht_id') == yacht)
        print(f"   - {yacht}: {count} threads")

    # Check the specific failing threads
    print("\n2. Checking failing thread IDs...")
    for thread_id in FAILING_THREAD_IDS:
        result = supabase.table('email_threads').select(
            'id, yacht_id, latest_subject, created_at, source'
        ).eq('id', thread_id).execute()

        if result.data:
            thread = result.data[0]
            print(f"\n   Thread: {thread_id}")
            print(f"   - EXISTS: YES")
            print(f"   - yacht_id: {thread.get('yacht_id')}")
            print(f"   - subject: {thread.get('latest_subject', 'N/A')[:60]}")
            print(f"   - source: {thread.get('source')}")
            print(f"   - created: {thread.get('created_at')}")
        else:
            print(f"\n   Thread: {thread_id}")
            print(f"   - EXISTS: NO - Thread not found in database!")

    # Check email_watchers to see what yacht_id emails should be syncing with
    print("\n3. Checking email_watchers configuration...")
    watcher_result = supabase.table('email_watchers').select(
        'id, user_id, yacht_id, sync_status, last_sync_at'
    ).execute()

    if watcher_result.data:
        for watcher in watcher_result.data:
            print(f"\n   Watcher: {watcher['id'][:8]}...")
            print(f"   - user_id: {watcher['user_id'][:8]}...")
            print(f"   - yacht_id: {watcher['yacht_id']}")
            print(f"   - status: {watcher.get('sync_status')}")
            print(f"   - last_sync: {watcher.get('last_sync_at')}")
    else:
        print("   No email watchers found!")

    # Check user_accounts to see expected yacht_id
    print("\n4. Checking user_accounts for expected yacht_id...")
    # Note: This requires MASTER DB, not tenant DB
    # We'll skip this for now since we're connected to tenant

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nIf threads exist with a yacht_id that doesn't match user session,")
    print("run the fix script to update yacht_ids.")


if __name__ == "__main__":
    diagnose()
