#!/usr/bin/env python3
"""
Test HOR via /v1/actions/execute endpoint
Uses action registry dispatch pattern (intended architecture)
"""
import os
import sys
import json
import requests

# Load env vars
env_vars = {}
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value
            os.environ[key] = value

# Load JWTs
with open('test-jwts.json', 'r') as f:
    jwts = json.load(f)

API_BASE = "http://localhost:8080"
YACHT_ID = env_vars['TEST_YACHT_ID']

print("=" * 80)
print("HOR Testing via /v1/actions/execute (Action Registry Dispatch)")
print("=" * 80)
print(f"API: {API_BASE}")
print(f"Yacht: {YACHT_ID}")
print()

# Test 1: Execute get_hours_of_rest action
print("[TEST 1] CAPTAIN executes get_hours_of_rest action")
print("-" * 80)

captain_jwt = jwts['CAPTAIN']['jwt']
captain_id = jwts['CAPTAIN']['user_id']

payload = {
    "action": "get_hours_of_rest",
    "context": {
        "yacht_id": YACHT_ID,
        "user_id": captain_id,
        "role": "captain"
    },
    "payload": {
        "yacht_id": YACHT_ID,
        "user_id": captain_id
    }
}

try:
    response = requests.post(
        f"{API_BASE}/v1/actions/execute",
        json=payload,
        headers={"Authorization": f"Bearer {captain_jwt}"},
        timeout=10
    )

    print(f"Status: {response.status_code}")
    print(f"Response:")
    resp_json = response.json()
    if response.status_code == 200 and 'data' in resp_json:
        # Show summary and first 3 records for successful response
        print(json.dumps({
            'success': resp_json.get('success'),
            'action_id': resp_json.get('action_id'),
            'data': {
                'records_count': len(resp_json['data'].get('records', [])),
                'records_sample': resp_json['data'].get('records', [])[:3],
                'summary': resp_json['data'].get('summary'),
                'date_range': resp_json['data'].get('date_range')
            }
        }, indent=2))
    else:
        print(json.dumps(resp_json, indent=2)[:800])

except Exception as e:
    print(f"ERROR: {e}")

print()
print("=" * 80)
print("To start API:")
print("  cd apps/api")
print("  export $(grep -v '^#' ../../env/.env.local | xargs)")
print("  uvicorn pipeline_service:app --reload --port 8080")
