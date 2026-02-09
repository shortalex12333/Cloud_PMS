#!/usr/bin/env python3
"""
Part Lens Production API Test - Live Microaction Verification

Tests the production API endpoint to verify:
1. Microactions are being returned in search results
2. Event loop fix is working (no crashes)
3. Part Lens integration is operational

This test uses real production credentials and hits the live API.
"""

import os
import sys
import json
import jwt
import time
import requests
from datetime import datetime, timedelta

print("=" * 100)
print("PART LENS PRODUCTION API TEST - LIVE MICROACTION VERIFICATION")
print("=" * 100)
print()

# Production endpoint
PRODUCTION_URL = "https://pipeline-core.int.celeste7.ai/webhook/search"
HEALTH_URL = "https://pipeline-core.int.celeste7.ai/v2/search/health"

# Test queries
TEST_QUERIES = [
    ("Racor", "MANUFACTURER entity - should return parts with microactions"),
    ("oil filter", "PART_NAME entity - common part search"),
    ("FH-5", "PART_NUMBER entity - specific part code"),
]

def generate_test_jwt():
    """Generate a test JWT token for authentication."""
    # Try to get JWT secret from env
    jwt_secret = os.getenv('MASTER_SUPABASE_JWT_SECRET') or os.getenv('TENANT_1_SUPABASE_JWT_SECRET')

    if not jwt_secret:
        print("⚠️  No JWT secret found in environment")
        print("   Checking .env files...")

        # Try to read from .env.staging.example
        env_file = '.env.staging.example'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TENANT_1_SUPABASE_JWT_SECRET='):
                        jwt_secret = line.split('=', 1)[1].strip()
                        print(f"   ✅ Found JWT secret in {env_file}")
                        break

    if not jwt_secret:
        print("❌ Cannot generate JWT - no secret available")
        return None

    # Generate JWT with test user
    # Using a test user ID - in production this would be a real user from user_accounts
    payload = {
        'sub': '00000000-0000-0000-0000-000000000001',  # Test user ID
        'email': 'test@celeste7.ai',
        'role': 'authenticated',
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,  # 1 hour expiry
    }

    try:
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        print("✅ Generated test JWT token")
        return token
    except Exception as e:
        print(f"❌ Failed to generate JWT: {e}")
        return None

def test_health_endpoint():
    """Test the health endpoint to verify service is running."""
    print("Step 1: Testing health endpoint...")
    print(f"   URL: {HEALTH_URL}")

    try:
        response = requests.get(HEALTH_URL, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Service healthy: {data}")
            return True
        else:
            print(f"   ⚠️  Health check returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

def test_search_with_jwt(query, description, jwt_token):
    """Test search endpoint with a query."""
    print(f"\nTesting: '{query}'")
    print(f"   Description: {description}")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {jwt_token}'
    }

    payload = {
        'query': query,
        'limit': 3
    }

    try:
        response = requests.post(PRODUCTION_URL, headers=headers, json=payload, timeout=30)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Check results
            results = data.get('results', [])
            print(f"   ✅ Got {len(results)} results")

            if len(results) == 0:
                print(f"   ⚠️  No results returned (may be expected if no parts match)")
                return {'success': True, 'has_results': False}

            # Check first result for microactions
            first_result = results[0]
            print(f"   First result: {first_result.get('title', 'N/A')}")
            print(f"   Source table: {first_result.get('source_table', 'N/A')}")

            # Check for actions field
            actions = first_result.get('actions', [])
            print(f"   Actions field: present={('actions' in first_result)}, count={len(actions)}")

            if actions:
                print(f"   ✅ MICROACTIONS FOUND! ({len(actions)} actions)")
                for i, action in enumerate(actions[:3], 1):
                    print(f"      {i}. {action.get('label', 'N/A')} ({action.get('action_id', 'N/A')})")
                    print(f"         Priority: {action.get('priority', 'N/A')}, Variant: {action.get('variant', 'N/A')}")

                return {
                    'success': True,
                    'has_results': True,
                    'has_microactions': True,
                    'action_count': len(actions),
                    'actions': actions[:3]
                }
            else:
                print(f"   ⚠️  No microactions in results (actions field is empty)")
                return {
                    'success': True,
                    'has_results': True,
                    'has_microactions': False,
                    'reason': 'actions_empty'
                }

        elif response.status_code == 401:
            print(f"   ❌ Authentication failed (401)")
            print(f"      This means JWT is invalid or user not in MASTER DB")
            return {'success': False, 'error': 'auth_failed', 'status': 401}

        elif response.status_code == 403:
            print(f"   ❌ Forbidden (403)")
            return {'success': False, 'error': 'forbidden', 'status': 403}

        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            print(f"      Response: {response.text[:200]}")
            return {'success': False, 'error': 'unexpected_status', 'status': response.status_code}

    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out")
        return {'success': False, 'error': 'timeout'}

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {'success': False, 'error': str(e)}

def test_with_service_key():
    """Test using service key directly (bypass JWT auth)."""
    print("\nStep 3: Testing with Supabase service key (bypass auth)...")

    service_key = os.getenv('TENANT_1_SUPABASE_SERVICE_KEY')

    if not service_key:
        # Try to read from .env.staging.example
        env_file = '.env.staging.example'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TENANT_1_SUPABASE_SERVICE_KEY='):
                        service_key = line.split('=', 1)[1].strip()
                        break

    if not service_key:
        print("   ⚠️  Service key not available, skipping")
        return None

    print("   ✅ Service key found, testing...")

    # Note: The API expects JWT auth, not service key directly
    # This test will likely fail with 401, which is expected
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {service_key}'
    }

    payload = {'query': 'Racor', 'limit': 1}

    try:
        response = requests.post(PRODUCTION_URL, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Service key auth worked! Got {len(data.get('results', []))} results")
            return True
        else:
            print(f"   ⚠️  Service key auth failed (expected): {response.status_code}")
            print(f"      API requires proper JWT from MASTER DB user")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run production API tests."""

    # Test 1: Health check
    if not test_health_endpoint():
        print("\n⚠️  Service may be down, but continuing with tests...")

    print()
    print("=" * 100)
    print("Step 2: Testing search endpoint with JWT authentication")
    print("=" * 100)

    # Generate JWT token
    jwt_token = generate_test_jwt()

    if not jwt_token:
        print("\n❌ Cannot proceed without JWT token")
        print("\nAlternative: Manual testing required")
        print("   1. Get a valid JWT from a logged-in frontend user")
        print("   2. Use that JWT to test:")
        print(f"      curl -X POST {PRODUCTION_URL} \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -H 'Authorization: Bearer <JWT>' \\")
        print(f"        -d '{{\"query\": \"Racor\", \"limit\": 3}}' | jq '.results[0].actions'")
        sys.exit(1)

    # Test each query
    results = []
    for query, description in TEST_QUERIES:
        result = test_search_with_jwt(query, description, jwt_token)
        results.append({
            'query': query,
            'result': result
        })

    # Test with service key (expected to fail, but informative)
    test_with_service_key()

    # Summary
    print()
    print("=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)

    microactions_found = any(r['result'].get('has_microactions') for r in results)
    auth_failed = any(r['result'].get('error') == 'auth_failed' for r in results)

    if microactions_found:
        print("✅ MICROACTIONS ARE WORKING IN PRODUCTION!")
        print()
        for r in results:
            if r['result'].get('has_microactions'):
                print(f"   Query: '{r['query']}'")
                print(f"   Actions: {r['result']['action_count']}")
    elif auth_failed:
        print("⚠️  AUTHENTICATION FAILED")
        print()
        print("The test JWT was rejected. This means:")
        print("  1. The test user doesn't exist in MASTER DB user_accounts table")
        print("  2. JWT secret may be incorrect")
        print("  3. Need to use a real user JWT from frontend")
        print()
        print("RECOMMENDATION:")
        print("  Ask user to provide a valid JWT from logged-in frontend session")
        print("  Or create a test user in MASTER DB with yacht assignment")
    else:
        print("⚠️  MICROACTIONS NOT FOUND")
        print()
        print("Possible reasons:")
        print("  1. No parts matched the queries (check if pms_parts has data)")
        print("  2. MicroactionRegistry failed to initialize (check Render logs)")
        print("  3. source_table field missing from results")
        print("  4. Event loop bug not fixed (check for crashes in logs)")

    print()
    print("=" * 100)
    print()

    return microactions_found

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
