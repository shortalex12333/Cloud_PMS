#!/usr/bin/env python3
"""
One-time migration script: Apply is_hod() fix to test database

This script applies the 20260129_fix_is_hod_use_auth_users_roles migration
to fix the is_hod() function to query auth_users_roles instead of auth_users_profiles.

Usage:
    cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
    python3 supabase/apply_is_hod_fix.py

Requirements:
    - .env file with SUPABASE_URL and SUPABASE_SERVICE_KEY
    - psycopg2 Python package
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

print("=" * 80)
print("MIGRATION: Fix is_hod() to use auth_users_roles table")
print("=" * 80)
print()

# Load environment from .env file
env_path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'api', '.env')
if not os.path.exists(env_path):
    print(f"ERROR: .env file not found at {env_path}")
    sys.exit(1)

print(f"Loading environment from: {env_path}")
env_vars = {}
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key] = value
            os.environ[key] = value

# Get Supabase credentials
tenant_url = env_vars.get('yTEST_YACHT_001_SUPABASE_URL') or env_vars.get('SUPABASE_URL')
service_key = env_vars.get('yTEST_YACHT_001_SUPABASE_SERVICE_KEY') or env_vars.get('SUPABASE_SERVICE_KEY')

if not tenant_url or not service_key:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

print(f"Target database: {tenant_url}")
print()

# Migration SQL
migration_sql = """
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role text;
BEGIN
    -- Query auth_users_roles (NOT auth_users_profiles) for active role
    SELECT role INTO v_role
    FROM public.auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    -- HOD roles: chief_engineer, chief_officer, captain, chief_steward, purser, manager
    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'chief_steward',
        'purser',
        'manager'
    );
END;
$$;

COMMENT ON FUNCTION public.is_hod(uuid, uuid) IS
    'Check if user is Head of Department (includes purser). Queries auth_users_roles NOT auth_users_profiles.';
"""

# Try using Supabase client to execute SQL via RPC
print("Attempting to apply migration via Supabase client...")
try:
    from supabase import create_client

    client = create_client(tenant_url, service_key)

    # Supabase Python client doesn't have direct SQL execution
    # We need to use psycopg2 or manual application
    print("Supabase client created, but direct SQL execution not supported.")
    print("Falling back to psycopg2...")
    raise NotImplementedError("Need psycopg2")

except Exception as e:
    # Try psycopg2
    print(f"Trying psycopg2 with direct database connection...")

    try:
        import psycopg2

        # Extract project ref from URL
        project_ref = tenant_url.replace('https://', '').replace('.supabase.co', '')
        print(f"Project reference: {project_ref}")

        # Check if DATABASE_URL is available
        db_url = env_vars.get('yTEST_YACHT_001_DATABASE_URL') or env_vars.get('DATABASE_URL')

        if not db_url:
            print()
            print("=" * 80)
            print("DATABASE_URL not found - Manual application required")
            print("=" * 80)
            print()
            print("Please apply this migration manually via one of these methods:")
            print()
            print("METHOD 1: Supabase SQL Editor (Recommended)")
            print(f"   1. Go to: https://supabase.com/dashboard/project/{project_ref}")
            print("   2. Navigate to: SQL Editor")
            print("   3. Click 'New Query'")
            print("   4. Copy and paste the SQL below")
            print("   5. Click 'Run'")
            print()
            print("METHOD 2: Add DATABASE_URL to .env and re-run this script")
            print(f"   1. Get connection string from: https://supabase.com/dashboard/project/{project_ref}/settings/database")
            print("   2. Add to apps/api/.env: DATABASE_URL=postgresql://...")
            print("   3. Re-run: python3 supabase/apply_is_hod_fix.py")
            print()
            print("=" * 80)
            print("MIGRATION SQL:")
            print("=" * 80)
            print()
            print(migration_sql)
            print()
            print("=" * 80)
            sys.exit(1)

        # Connect and execute
        print(f"Connecting to database...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        print("Executing migration SQL...")
        cur.execute(migration_sql)
        conn.commit()

        cur.close()
        conn.close()

        print()
        print("=" * 80)
        print("✅ MIGRATION APPLIED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("The is_hod() function has been fixed to query auth_users_roles.")
        print("Next step: Run acceptance tests to verify the fix")
        print()
        print("  bash tests/run_receiving_tests_simple.sh")
        print()
        sys.exit(0)

    except ImportError:
        print()
        print("ERROR: psycopg2 not installed")
        print("Install with: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e2:
        print()
        print(f"ERROR: Failed to apply migration: {e2}")
        print()
        print("Please apply manually via Supabase SQL Editor (see instructions above)")
        sys.exit(1)
