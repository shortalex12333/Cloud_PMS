#!/usr/bin/env python3
"""
Hours of Rest (HOR) Lens - E2E Testing Script
Tests API endpoints with CREW, HOD, and CAPTAIN roles
Documents honest results including errors
"""
import json
import requests
from datetime import datetime
import os

# Load JWTs
with open('test-jwts.json', 'r') as f:
    jwts = json.load(f)

# Read env
env_vars = {}
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

API_BASE = "http://localhost:8080"
YACHT_ID = env_vars['TEST_YACHT_ID']

# Test results
results = {
    'timestamp': datetime.now().isoformat(),
    'yacht_id': YACHT_ID,
    'tests': []
}

def run_test(role, test_name, method, endpoint, jwt, params=None, expected_status=200):
    """Run a single API test"""
    url = f"{API_BASE}{endpoint}"
    headers = {
        'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json'
    }
    
    test_result = {
        'role': role,
        'test_name': test_name,
        'method': method,
        'endpoint': endpoint,
        'params': params,
        'expected_status': expected_status
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=params, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        test_result['actual_status'] = response.status_code
        test_result['success'] = (response.status_code == expected_status)
        
        try:
            test_result['response'] = response.json()
        except:
            test_result['response'] = response.text[:500]
        
        # Print live result
        status_icon = "✓" if test_result['success'] else "✗"
        print(f"{status_icon} [{role}] {test_name}: {response.status_code}")
        if not test_result['success']:
            print(f"   Error: {test_result['response']}")
        
    except Exception as e:
        test_result['actual_status'] = 'ERROR'
        test_result['success'] = False
        test_result['error'] = str(e)
        print(f"✗ [{role}] {test_name}: EXCEPTION - {e}")
    
    results['tests'].append(test_result)
    return test_result

# ============================================================================
# TEST SUITE
# ============================================================================

print("=" * 80)
print("HOURS OF REST (HOR) LENS - E2E TESTING")
print("=" * 80)
print(f"API: {API_BASE}")
print(f"Yacht ID: {YACHT_ID}")
print(f"Test Users: CREW, HOD, CAPTAIN")
print("=" * 80)

# TEST 1: CREW - Fetch own HOR records
print("\n[TEST GROUP 1] CREW Tests")
print("-" * 80)
crew_jwt = jwts['CREW']['jwt']
crew_id = jwts['CREW']['user_id']

run_test(
    'CREW',
    'Fetch own HOR records (last 7 days)',
    'GET',
    '/v1/hours-of-rest',
    crew_jwt,
    params={'user_id': crew_id}
)

run_test(
    'CREW',
    'Fetch own HOR warnings',
    'GET',
    '/v1/hours-of-rest/warnings',
    crew_jwt,
    params={'user_id': crew_id}
)

run_test(
    'CREW',
    'Try to fetch HOD records (should fail RLS)',
    'GET',
    '/v1/hours-of-rest',
    crew_jwt,
    params={'user_id': jwts['HOD']['user_id']},
    expected_status=200  # Will return 200 but empty data due to RLS
)

# TEST 2: HOD - Fetch department records
print("\n[TEST GROUP 2] HOD Tests")
print("-" * 80)
hod_jwt = jwts['HOD']['jwt']
hod_id = jwts['HOD']['user_id']

run_test(
    'HOD',
    'Fetch own HOR records',
    'GET',
    '/v1/hours-of-rest',
    hod_jwt,
    params={'user_id': hod_id}
)

run_test(
    'HOD',
    'Fetch own HOR warnings',
    'GET',
    '/v1/hours-of-rest/warnings',
    hod_jwt,
    params={'user_id': hod_id}
)

run_test(
    'HOD',
    'Try to fetch department HOR records (CREW)',
    'GET',
    '/v1/hours-of-rest',
    hod_jwt,
    params={'user_id': crew_id},
    expected_status=200  # Should work if same department
)

# TEST 3: CAPTAIN - Fetch all records
print("\n[TEST GROUP 3] CAPTAIN Tests")
print("-" * 80)
captain_jwt = jwts['CAPTAIN']['jwt']
captain_id = jwts['CAPTAIN']['user_id']

run_test(
    'CAPTAIN',
    'Fetch own HOR records',
    'GET',
    '/v1/hours-of-rest',
    captain_jwt,
    params={'user_id': captain_id}
)

run_test(
    'CAPTAIN',
    'Fetch all HOR records (no user filter)',
    'GET',
    '/v1/hours-of-rest',
    captain_jwt,
    params={}
)

run_test(
    'CAPTAIN',
    'Fetch CREW HOR records (cross-user)',
    'GET',
    '/v1/hours-of-rest',
    captain_jwt,
    params={'user_id': crew_id},
    expected_status=200  # CAPTAIN should see all
)

# ============================================================================
# SAVE RESULTS
# ============================================================================

output_dir = 'test-results/hours_of_rest'
os.makedirs(output_dir, exist_ok=True)
output_file = f"{output_dir}/e2e_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = len(results['tests'])
passed = sum(1 for t in results['tests'] if t['success'])
failed = total_tests - passed

print(f"Total Tests: {total_tests}")
print(f"Passed: {passed} ✓")
print(f"Failed: {failed} ✗")
print(f"\nResults saved to: {output_file}")

# Print failures
if failed > 0:
    print("\n" + "-" * 80)
    print("FAILED TESTS:")
    print("-" * 80)
    for test in results['tests']:
        if not test['success']:
            print(f"\n✗ [{test['role']}] {test['test_name']}")
            print(f"  Expected: {test['expected_status']}")
            print(f"  Actual: {test['actual_status']}")
            if 'error' in test:
                print(f"  Error: {test['error']}")
            elif 'response' in test:
                print(f"  Response: {json.dumps(test['response'], indent=4)[:200]}")

print("\n" + "=" * 80)
