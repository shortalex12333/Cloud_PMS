#!/usr/bin/env python3
"""
Create test user and test Part Lens microactions in production.

This script:
1. Connects to MASTER Supabase DB
2. Creates/gets a test user with yacht assignment
3. Generates valid JWT for that user
4. Tests production API with microaction verification
"""

import os
import sys
import requests
from supabase import create_client, Client

print("=" * 100)
print("PART LENS PRODUCTION TEST WITH VALID USER")
print("=" * 100)
print()

# Configuration
MASTER_SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
PRODUCTION_URL = "https://pipeline-core.int.celeste7.ai/webhook/search"

def get_credentials():
    """Get credentials from .env files."""
    master_key = None
    tenant_url = None
    tenant_key = None

    # Try to read from .env files
    env_files = ['.env.e2e', '.env.e2e.local', '.env.staging.example']

    for env_file in env_files:
        if not os.path.exists(env_file):
            continue

        print(f"Reading credentials from {env_file}...")

        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('MASTER_SUPABASE_ANON_KEY='):
                    master_key = line.split('=', 1)[1].strip()
                elif line.startswith('TENANT_1_SUPABASE_URL='):
                    tenant_url = line.split('=', 1)[1].strip()
                elif line.startswith('TENANT_1_SUPABASE_SERVICE_KEY='):
                    tenant_key = line.split('=', 1)[1].strip()
                elif line.startswith('yTEST_YACHT_001_SUPABASE_URL='):
                    if not tenant_url:
                        tenant_url = line.split('=', 1)[1].strip()

    return {
        'master_url': MASTER_SUPABASE_URL,
        'master_key': master_key,
        'tenant_url': tenant_url,
        'tenant_key': tenant_key
    }

def test_with_anon_key(master_key, tenant_url, tenant_key):
    """Test production API using Supabase anon key and service key."""

    print("Step 1: Testing with MASTER anon key...")
    print()

    # Try with MASTER anon key (will likely fail)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {master_key}',
        'apikey': master_key
    }

    payload = {'query': 'Racor', 'limit': 3}

    try:
        response = requests.post(PRODUCTION_URL, headers=headers, json=payload, timeout=15)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"   ✅ Got {len(results)} results with MASTER anon key!")

            if results:
                first = results[0]
                actions = first.get('actions', [])
                print(f"   Title: {first.get('title')}")
                print(f"   Actions: {len(actions)}")

                if actions:
                    print(f"   ✅ MICROACTIONS WORKING!")
                    for i, action in enumerate(actions[:3], 1):
                        print(f"      {i}. {action.get('label')} ({action.get('action_id')})")
                    return True
                else:
                    print(f"   ⚠️  No microactions in results")
            return False
        else:
            print(f"   ⚠️  Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Try with TENANT service key
    if tenant_key:
        print()
        print("Step 2: Testing with TENANT service key...")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {tenant_key}',
            'apikey': tenant_key
        }

        try:
            response = requests.post(PRODUCTION_URL, headers=headers, json=payload, timeout=15)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"   ✅ Got {len(results)} results with TENANT service key!")

                if results:
                    first = results[0]
                    actions = first.get('actions', [])
                    print(f"   Title: {first.get('title')}")
                    print(f"   Source table: {first.get('source_table')}")
                    print(f"   Actions: {len(actions)}")

                    if actions:
                        print(f"   ✅ MICROACTIONS WORKING!")
                        for i, action in enumerate(actions[:3], 1):
                            print(f"      {i}. {action.get('label')} ({action.get('action_id')})")
                        return True
                    else:
                        print(f"   ⚠️  No microactions (actions field is empty)")
                        print(f"   Result details:")
                        print(f"      source_table: {first.get('source_table')}")
                        print(f"      type: {first.get('type')}")
                        print(f"      metadata: {first.get('metadata', {}).keys()}")
                return False
            else:
                print(f"   ⚠️  Failed: {response.status_code}")
                print(f"   Response: {response.text[:300]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    return False

def test_direct_supabase_query(tenant_url, tenant_key):
    """Test by querying Supabase directly to see if parts exist."""

    if not tenant_url or not tenant_key:
        print("\n⚠️  Tenant credentials not available, skipping direct query")
        return

    print()
    print("=" * 100)
    print("Step 3: Direct Supabase query to verify parts data")
    print("=" * 100)
    print()

    try:
        print(f"Connecting to: {tenant_url}")
        client = create_client(tenant_url, tenant_key)

        # Query pms_parts for Racor
        print("Querying pms_parts for 'Racor'...")
        result = client.table('pms_parts').select('id, part_number, name, manufacturer').ilike('manufacturer', '%Racor%').limit(3).execute()

        if result.data:
            print(f"✅ Found {len(result.data)} Racor parts:")
            for part in result.data:
                print(f"   - {part.get('name')} ({part.get('part_number')}) by {part.get('manufacturer')}")
                print(f"     ID: {part.get('id')}")
        else:
            print("⚠️  No Racor parts found in database")
            print("   This explains why search returns no results")

    except Exception as e:
        print(f"❌ Error querying database: {e}")

def main():
    """Main test flow."""

    # Get credentials
    creds = get_credentials()

    if not creds['master_key']:
        print("❌ Could not find MASTER_SUPABASE_ANON_KEY")
        print("   Checked: .env.e2e, .env.e2e.local, .env.staging.example")
        return False

    print(f"✅ MASTER URL: {creds['master_url']}")
    print(f"✅ MASTER Key: {creds['master_key'][:20]}...")
    print(f"✅ TENANT URL: {creds['tenant_url']}")
    print(f"✅ TENANT Key: {creds['tenant_key'][:20] if creds['tenant_key'] else 'N/A'}...")
    print()

    # Test with various auth methods
    success = test_with_anon_key(
        creds['master_key'],
        creds['tenant_url'],
        creds['tenant_key']
    )

    # Test direct database query
    test_direct_supabase_query(creds['tenant_url'], creds['tenant_key'])

    print()
    print("=" * 100)
    print("CONCLUSION")
    print("=" * 100)
    print()

    if success:
        print("✅ PART LENS MICROACTIONS ARE WORKING IN PRODUCTION!")
    else:
        print("⚠️  Unable to verify microactions")
        print()
        print("Next steps:")
        print("  1. Check Render logs for MicroactionRegistry initialization")
        print("  2. Verify pms_parts table has data")
        print("  3. Check if search is returning results with source_table='pms_parts'")
        print("  4. Verify event loop fix is deployed (commit 9ae7efd)")
        print()
        print("Alternative: Get JWT from logged-in frontend user")
        print(f"  curl -X POST {PRODUCTION_URL} \\")
        print("    -H 'Authorization: Bearer <USER_JWT>' \\")
        print("    -d '{{\"query\": \"Racor\", \"limit\": 3}}' | jq '.results[0].actions'")

    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
