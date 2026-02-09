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

# Connect to TENANT database (where user profiles are)
supabase_url = env_vars['TENANT_1_SUPABASE_URL']
supabase_key = env_vars['TENANT_1_SUPABASE_SERVICE_KEY']
supabase = create_client(supabase_url, supabase_key)

# Query user profiles with yacht filter
yacht_id = env_vars['TEST_YACHT_ID']

print(f"Querying user profiles for yacht: {yacht_id}\n")

try:
    result = supabase.table('auth_users_profiles').select('id, name, email, metadata').eq('yacht_id', yacht_id).execute()
    
    print(f"Found {len(result.data)} users:\n")
    
    for user in result.data:
        role = user.get('metadata', {}).get('role', 'NO_ROLE') if isinstance(user.get('metadata'), dict) else 'NO_METADATA'
        print(f"Name: {user.get('name')}")
        print(f"  Email: {user.get('email')}")
        print(f"  ID: {user.get('id')}")
        print(f"  Role: {role}")
        print()
        
except Exception as e:
    print(f"Error: {e}")
