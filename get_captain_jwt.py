#!/usr/bin/env python3
import os
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

# Try captain.tenant@alex-short.com
try:
    print(f"Trying captain.tenant@alex-short.com...")
    response = supabase.auth.sign_in_with_password({
        "email": "captain.tenant@alex-short.com",
        "password": env_vars['ALL_TEST_USER_PASSWORD']
    })
    
    if response.session:
        print(f"✓ JWT obtained for captain.tenant@alex-short.com")
        print(f"  User ID: {response.user.id}")
        print(f"  JWT: {response.session.access_token[:50]}...")
    else:
        print("✗ No session")
except Exception as e:
    print(f"✗ Error: {e}")
