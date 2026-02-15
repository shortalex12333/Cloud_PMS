#!/usr/bin/env python3
"""Check watcher_id on email threads."""

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

FAILING_THREADS = [
    "a0e5b26b-e791-4896-8f15-c7da5a692f00",
    "b1711439-7409-442d-b4b5-3fe16bcef379",
    "beb4bb89-b250-4279-ab5a-f06eca9a303b",
    "edfe0943-0921-4546-b824-43957535e3d1",
]

url = os.environ.get('TENANT_SUPABASE_URL') or os.environ.get('yTEST_YACHT_001_SUPABASE_URL')
key = os.environ.get('TENANT_SUPABASE_SERVICE_KEY') or os.environ.get('yTEST_YACHT_001_SUPABASE_SERVICE_KEY')

print(f"Connecting to: {url[:50]}...")
supabase = create_client(url, key)

print("\n=== Checking watcher_id on failing threads ===\n")

for thread_id in FAILING_THREADS:
    result = supabase.table('email_threads').select(
        'id, yacht_id, watcher_id, latest_subject'
    ).eq('id', thread_id).execute()

    if result.data:
        t = result.data[0]
        print(f"Thread: {thread_id[:8]}...")
        print(f"  watcher_id: {t.get('watcher_id') or 'NULL'}")
        print(f"  subject: {t.get('latest_subject', 'N/A')[:50]}")
        print()
    else:
        print(f"Thread: {thread_id[:8]}... NOT FOUND")

print("\n=== Checking email_watchers ===\n")
watchers = supabase.table('email_watchers').select('id, user_id, yacht_id, sync_status').execute()
for w in watchers.data:
    print(f"Watcher: {w['id']}")
    print(f"  user_id: {w['user_id'][:8]}...")
    print(f"  yacht_id: {w['yacht_id']}")
    print(f"  status: {w.get('sync_status')}")
    print()
