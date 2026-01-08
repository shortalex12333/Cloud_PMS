#!/usr/bin/env python3
"""
Apply migration to Supabase Identity project.
Usage: python3 apply_migration.py <service_role_key>
"""

import sys
import requests
from pathlib import Path

# Supabase project details
PROJECT_REF = "qvzmkaamzaqxpzbewjxe"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"

def apply_migration(service_role_key: str):
    """Apply migration using Supabase SQL endpoint."""

    # Read migration file
    migration_path = Path(__file__).parent / "supabase/migrations/20241124000001_identity_schema.sql"

    if not migration_path.exists():
        print(f"Error: Migration file not found: {migration_path}")
        sys.exit(1)

    sql = migration_path.read_text()
    print(f"Loaded migration: {len(sql)} bytes")

    # Execute via Supabase RPC endpoint
    # Note: For DDL we need to use the postgres connection or Management API
    # The REST API doesn't support DDL directly

    # Try the PostgREST rpc endpoint for functions
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # First, let's check if we can reach the API
    print("Testing connection...")
    resp = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10)
    print(f"Connection test: {resp.status_code}")

    if resp.status_code != 200:
        print(f"Error: {resp.text}")
        sys.exit(1)

    print("\nConnection successful!")
    print("\nTo apply this migration, you need to:")
    print("1. Go to Supabase Dashboard → SQL Editor")
    print("2. Paste the contents of:")
    print(f"   {migration_path}")
    print("3. Click 'Run'")
    print("\nOr use psql:")
    print(f"   PGPASSWORD='<password>' psql -h db.{PROJECT_REF}.supabase.co -U postgres -d postgres -f {migration_path}")

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 apply_migration.py <service_role_key>")
        print("\nGet your service_role key from:")
        print("Supabase Dashboard → Settings → API → service_role key")
        sys.exit(1)

    service_role_key = sys.argv[1]
    apply_migration(service_role_key)

if __name__ == "__main__":
    main()
