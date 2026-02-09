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

# Get JWT for captain
response = supabase.auth.sign_in_with_password({
    "email": "captain.tenant@alex-short.com",
    "password": env_vars['ALL_TEST_USER_PASSWORD']
})

# Load existing JWTs
with open('test-jwts.json', 'r') as f:
    jwts = json.load(f)

# Add captain
jwts['CAPTAIN'] = {
    'email': 'captain.tenant@alex-short.com',
    'user_id': response.user.id,
    'jwt': response.session.access_token,
    'jwt_preview': response.session.access_token[:50] + '...'
}

# Update crew and hod emails to match profiles
jwts['CREW']['profile_note'] = 'Uses crew.test@alex-short.com for auth'
jwts['HOD']['profile_note'] = 'Uses hod.test@alex-short.com for auth'

# Save
with open('test-jwts.json', 'w') as f:
    json.dump(jwts, f, indent=2)

print("✓ Updated test-jwts.json with all 3 users")
print(f"  CREW: {jwts['CREW']['user_id']}")
print(f"  HOD: {jwts['HOD']['user_id']}")
print(f"  CAPTAIN: {jwts['CAPTAIN']['user_id']}")
