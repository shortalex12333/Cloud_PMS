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

# Test users
test_users = [
    {
        'email': env_vars['TEST_CREW_USER_EMAIL'],
        'password': env_vars['ALL_TEST_USER_PASSWORD'],
        'role': 'CREW'
    },
    {
        'email': env_vars['TEST_HOD_USER_EMAIL'],
        'password': env_vars['ALL_TEST_USER_PASSWORD'],
        'role': 'HOD'
    },
    {
        'email': env_vars['TEST_CAPTAIN_USER_EMAIL'],
        'password': env_vars['ALL_TEST_USER_PASSWORD'],
        'role': 'CAPTAIN'
    }
]

# Connect to MASTER Supabase (auth is on master)
supabase_url = env_vars['MASTER_SUPABASE_URL']
supabase_key = env_vars['MASTER_SUPABASE_SERVICE_KEY']
supabase = create_client(supabase_url, supabase_key)

jwts = {}

for user in test_users:
    try:
        print(f"\nAuthenticating {user['role']}: {user['email']}")
        
        # Sign in
        response = supabase.auth.sign_in_with_password({
            "email": user['email'],
            "password": user['password']
        })
        
        if response.session:
            jwt = response.session.access_token
            user_id = response.user.id
            jwts[user['role']] = {
                'email': user['email'],
                'user_id': user_id,
                'jwt': jwt,
                'jwt_preview': jwt[:50] + '...'
            }
            print(f"✓ {user['role']} JWT obtained")
            print(f"  User ID: {user_id}")
            print(f"  JWT: {jwt[:50]}...")
        else:
            print(f"✗ {user['role']}: No session returned")
            
    except Exception as e:
        print(f"✗ {user['role']} error: {e}")

# Save JWTs to file
with open('test-jwts.json', 'w') as f:
    json.dump(jwts, f, indent=2)

print(f"\n✓ JWTs saved to test-jwts.json")
print(f"\nTotal JWTs obtained: {len(jwts)}/3")
