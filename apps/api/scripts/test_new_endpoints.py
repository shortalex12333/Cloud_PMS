#!/usr/bin/env python3
"""
Test the new email endpoints directly (bypassing HTTP/auth layer).

Run: python scripts/test_new_endpoints.py
"""

import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Production test credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

# Test user/yacht
TEST_USER_ID = None  # Will be looked up
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


def test_worker_status():
    """Test the worker/status endpoint logic."""
    print("\n=== Testing worker/status endpoint logic ===")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # First, get a user_id from the yacht
    print("Looking up test user...")
    user_result = supabase.table('email_watchers').select('user_id').eq(
        'yacht_id', TEST_YACHT_ID
    ).limit(1).execute()

    if not user_result.data:
        print("ERROR: No email_watchers found for yacht")
        return False

    user_id = user_result.data[0]['user_id']
    print(f"Found user_id: {user_id[:8]}...")

    # Now test the actual query - use limit(1) instead of maybe_single()
    print("\nRunning worker/status query...")
    try:
        watcher_result = supabase.table('email_watchers').select(
            'sync_status, last_sync_at, subscription_expires_at, last_sync_error, delta_link_inbox, updated_at'
        ).eq('user_id', user_id).eq('yacht_id', TEST_YACHT_ID).eq(
            'provider', 'microsoft_graph'
        ).limit(1).execute()

        if not watcher_result.data or len(watcher_result.data) == 0:
            print("No watcher found (this is OK - returns disconnected status)")
            return True

        watcher = watcher_result.data[0]
        print(f"SUCCESS! Watcher data:")
        print(f"  sync_status: {watcher.get('sync_status')}")
        print(f"  last_sync_at: {watcher.get('last_sync_at')}")
        print(f"  last_sync_error: {watcher.get('last_sync_error')}")
        print(f"  has_delta_link: {bool(watcher.get('delta_link_inbox'))}")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thread_links():
    """Test the thread/links endpoint logic."""
    print("\n=== Testing thread/links endpoint logic ===")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # First, get a thread_id from the yacht
    print("Looking up test thread...")
    thread_result = supabase.table('email_threads').select('id').eq(
        'yacht_id', TEST_YACHT_ID
    ).limit(1).execute()

    if not thread_result.data:
        print("ERROR: No email_threads found for yacht")
        return False

    thread_id = thread_result.data[0]['id']
    print(f"Found thread_id: {thread_id}")

    # Test thread verification query
    print("\nVerifying thread belongs to yacht...")
    try:
        verify_result = supabase.table('email_threads').select('id').eq(
            'id', thread_id
        ).eq('yacht_id', TEST_YACHT_ID).maybe_single().execute()

        if not verify_result or not verify_result.data:
            print("ERROR: Thread verification failed")
            return False

        print("Thread verified OK")

    except Exception as e:
        print(f"ERROR in thread verification: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test links query - correct table is email_links
    print("\nQuerying email_links...")
    try:
        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, accepted_at, is_active, score'
        ).eq('thread_id', thread_id).eq('yacht_id', TEST_YACHT_ID).eq('is_active', True).execute()

        links = links_result.data or []
        print(f"SUCCESS! Found {len(links)} links for thread")

        if links:
            for link in links[:3]:  # Show first 3
                print(f"  - {link.get('object_type')}: {link.get('object_id')}")

        return True

    except Exception as e:
        print(f"ERROR in links query: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_table_exists():
    """Check if required tables exist."""
    print("\n=== Checking required tables ===")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    tables = ['email_watchers', 'email_threads', 'email_links']

    for table in tables:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            print(f"  {table}: EXISTS ({len(result.data)} sample rows)")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")
            return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing new email endpoint database queries")
    print("=" * 60)

    # Run tests
    results = []

    results.append(("Table check", test_table_exists()))
    results.append(("worker/status", test_worker_status()))
    results.append(("thread/links", test_thread_links()))

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)

    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("All tests PASSED - endpoint logic is correct")
    else:
        print("Some tests FAILED - check errors above")

    sys.exit(0 if all_pass else 1)
