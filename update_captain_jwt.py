#!/usr/bin/env python3
import os
import json
from supabase import create_client

# Read env file
env_vars = {}
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

# Connect to MASTER Supabase
supabase_url = env_vars['MASTER_SUPABASE_URL']
supabase_key = env_vars['MASTER_SUPABASE_SERVICE_KEY']
supabase = create_client(supabase_url, supabase_key)

# Get captain JWT
print(f"Authenticating captain.tenant@alex-short.com...")
response = supabase.auth.sign_in_with_password({
    "email": "captain.tenant@alex-short.com",
    "password": env_vars['ALL_TEST_USER_PASSWORD']
})

if not response.session:
    print("✗ Failed to get captain JWT")
    exit(1)

captain_jwt = response.session.access_token
captain_user_id = response.user.id

print(f"✓ Captain JWT obtained")
print(f"  User ID: {captain_user_id}")

# Load existing JWTs
with open('test-jwts.json', 'r') as f:
    jwts = json.load(f)

# Add captain
jwts['CAPTAIN'] = {
    "email": "captain.tenant@alex-short.com",
    "user_id": captain_user_id,
    "jwt": captain_jwt,
    "jwt_preview": captain_jwt[:50] + "..."
}

# Save
with open('test-jwts.json', 'w') as f:
    json.dump(jwts, f, indent=2)

print("✓ test-jwts.json updated with CAPTAIN JWT")
