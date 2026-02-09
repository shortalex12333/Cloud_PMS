"""
Quick API JWT test - diagnose exact error from production API
"""

import json
import requests

API_URL = "https://pipeline-core.int.celeste7.ai"

# Load test JWT
with open('test-jwts.json', 'r') as f:
    tokens = json.load(f)
    jwt = tokens['CREW']['jwt']
    user_id = tokens['CREW']['user_id']

print("="*80)
print("TESTING PRODUCTION API JWT VALIDATION")
print("="*80)
print(f"\nAPI: {API_URL}")
print(f"User: {tokens['CREW']['email']}")
print(f"JWT Issuer: qvzmkaamzaqxpzbewjxe.supabase.co")
print("\n" + "="*80)

# Test simple action
print("\nTesting: get_hours_of_rest action...")
response = requests.post(
    f"{API_URL}/v1/actions/execute",
    headers={
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json"
    },
    json={
        "action": "get_hours_of_rest",
        "context": {
            "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
            "user_id": user_id,
            "role": "crew"
        },
        "payload": {
            "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
            "user_id": user_id,
            "start_date": "2026-02-01",
            "end_date": "2026-02-09"
        }
    },
    timeout=10
)

print(f"\nStatus Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print(f"\nResponse Body:")
print(response.text)

if response.status_code == 200:
    print("\n✅ SUCCESS - JWT validation working!")
    data = response.json()
    print(f"Retrieved {len(data.get('records', []))} records")
elif response.status_code == 400:
    print("\n❌ 400 Bad Request - Likely JWT signature issue")
    print("\nDiagnosis:")
    if "invalid JWT" in response.text or "signature" in response.text:
        print("  - MASTER_SUPABASE_JWT_SECRET in Render doesn't match qvzmkaamzaqxpzbewjxe project")
        print("  - OR: yTEST_YACHT_001_SUPABASE_JWT_SECRET has the correct secret instead")
        print("\nTo fix:")
        print("  1. Go to https://supabase.com/dashboard")
        print("  2. Select qvzmkaamzaqxpzbewjxe project")
        print("  3. Settings → API → Copy JWT Secret")
        print("  4. In Render: Set MASTER_SUPABASE_JWT_SECRET to that value")
        print("  5. Redeploy")
elif response.status_code == 401:
    print("\n❌ 401 Unauthorized - JWT expired or invalid")
else:
    print(f"\n⚠️  Unexpected status: {response.status_code}")

print("\n" + "="*80)
