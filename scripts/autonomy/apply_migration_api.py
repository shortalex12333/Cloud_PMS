#!/usr/bin/env python3
"""
Apply migration via Supabase SQL Editor API

Uses the Supabase Management API to execute SQL migrations.
"""

import os
import sys
import requests

# Read migration
migration_file = 'supabase/migrations/20260206000003_match_link_targets_rpc.sql'

with open(migration_file, 'r') as f:
    sql = f.read()

# Get env vars
project_ref = 'vzsohavtuotocgrfkfyd'
service_key = os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY')

if not service_key:
    print("ERROR: yTEST_YACHT_001_SUPABASE_SERVICE_KEY not set")
    sys.exit(1)

# Use Supabase's query endpoint (PostgREST RPC)
# We'll create the function using a direct SQL execution approach

print("Attempting to apply migration via Supabase API...")
print(f"Project: {project_ref}")
print(f"Migration: {migration_file}")
print()

# Try using the SQL endpoint (requires management API access)
url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"

headers = {
    'Authorization': f'Bearer {service_key}',
    'Content-Type': 'application/json',
    'apikey': service_key
}

payload = {
    'query': sql
}

print("Executing SQL...")
response = requests.post(url, headers=headers, json=payload)

if response.status_code == 200:
    print("✓ Migration applied successfully!")
    sys.exit(0)
elif response.status_code == 404:
    print("✗ Management API endpoint not available")
    print()
    print("Please apply migration manually:")
    print(f"1. Go to: https://supabase.com/dashboard/project/{project_ref}/sql/new")
    print(f"2. Paste contents of: {migration_file}")
    print("3. Click 'Run'")
    sys.exit(1)
else:
    print(f"✗ Failed to apply migration: HTTP {response.status_code}")
    print(f"Response: {response.text}")
    print()
    print("Please apply migration manually:")
    print(f"1. Go to: https://supabase.com/dashboard/project/{project_ref}/sql/new")
    print(f"2. Paste contents of: {migration_file}")
    print("3. Click 'Run'")
    sys.exit(1)
