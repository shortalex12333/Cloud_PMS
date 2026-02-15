#!/usr/bin/env python3
"""Test which key type allows seeing threads."""

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

url = os.environ.get('TENANT_SUPABASE_URL') or os.environ.get('yTEST_YACHT_001_SUPABASE_URL')
service_key = os.environ.get('TENANT_SUPABASE_SERVICE_KEY') or os.environ.get('yTEST_YACHT_001_SUPABASE_SERVICE_KEY')
anon_key = os.environ.get('TENANT_SUPABASE_ANON_KEY') or os.environ.get('yTEST_YACHT_001_SUPABASE_ANON_KEY')

print("=" * 60)
print("TESTING KEY TYPES")
print("=" * 60)

# Test with SERVICE key
print("\n1. Testing with SERVICE key (should bypass RLS):")
try:
    client = create_client(url, service_key)
    result = client.table('email_threads').select('id, yacht_id, watcher_id').eq(
        'id', THREAD_ID
    ).eq('yacht_id', YACHT_ID).execute()
    if result.data:
        print(f"   ✓ SUCCESS - Thread found: {result.data[0]['id'][:8]}...")
    else:
        print("   ✗ FAILED - Thread NOT found (empty result)")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

# Test with ANON key
print("\n2. Testing with ANON key (RLS will be applied):")
try:
    client = create_client(url, anon_key)
    result = client.table('email_threads').select('id, yacht_id, watcher_id').eq(
        'id', THREAD_ID
    ).eq('yacht_id', YACHT_ID).execute()
    if result.data:
        print(f"   ✓ SUCCESS - Thread found: {result.data[0]['id'][:8]}...")
        print("   (RLS allowed access - watcher_id matches or is NULL)")
    else:
        print("   ✗ FAILED - Thread NOT found (RLS filtered it out)")
        print("   This is what causes the 404 errors!")
except Exception as e:
    print(f"   ✗ ERROR: {e}")

print("\n" + "=" * 60)
print("DIAGNOSIS:")
print("=" * 60)
print("""
If SERVICE key works but ANON key doesn't, the issue is:
  → Render has ANON key in yTEST_YACHT_001_SUPABASE_SERVICE_KEY

FIX: In Render dashboard, update the secret to use the SERVICE key.

The SERVICE key starts with: eyJhbGc... (longer, has "service_role")
The ANON key starts with:    eyJhbGc... (shorter, has "anon")
""")
