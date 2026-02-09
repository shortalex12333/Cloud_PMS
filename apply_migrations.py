import os
from supabase import create_client

# Read env file
with open('env/.env.local', 'r') as f:
    for line in f:
        if line.strip() and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

# Connect to TENANT database
supabase_url = os.environ['TENANT_1_SUPABASE_URL']
supabase_key = os.environ['TENANT_1_SUPABASE_SERVICE_KEY']
supabase = create_client(supabase_url, supabase_key)

# Read migration files
with open('migrations/010_hor_missing_rpc_functions.sql', 'r') as f:
    migration_010 = f.read()

with open('migrations/011_hor_rls_policy_fixes.sql', 'r') as f:
    migration_011 = f.read()

# Execute migrations using rpc
try:
    print("Applying migration 010 (RPC functions)...")
    result = supabase.rpc('exec_sql', {'sql': migration_010}).execute()
    print(f"✓ Migration 010 applied successfully")
except Exception as e:
    print(f"Migration 010 error: {e}")
    # Try raw SQL execution
    print("Trying direct execution...")

try:
    print("\nApplying migration 011 (RLS policies)...")
    result = supabase.rpc('exec_sql', {'sql': migration_011}).execute()
    print(f"✓ Migration 011 applied successfully")
except Exception as e:
    print(f"Migration 011 error: {e}")

# Verify functions exist
print("\nVerifying RPC functions...")
try:
    result = supabase.rpc('check_hor_violations', {'p_hor_id': '00000000-0000-0000-0000-000000000000'}).execute()
    print("✓ check_hor_violations exists")
except Exception as e:
    print(f"✗ check_hor_violations: {e}")

print("\nVerifying RLS policies...")
result = supabase.table('pg_policies').select('tablename, policyname').eq('tablename', 'pms_hours_of_rest').execute()
print(f"Policies on pms_hours_of_rest: {len(result.data) if result.data else 0}")
for policy in (result.data or []):
    print(f"  - {policy['policyname']}")
