#!/usr/bin/env python3
"""
Deploy CelesteOS schema to Supabase
"""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    os.system("pip install psycopg2-binary")
    import psycopg2

# Supabase connection details
SUPABASE_PROJECT_REF = "vzsohavtuotocgrfkfyd"
SUPABASE_HOST = f"db.{SUPABASE_PROJECT_REF}.supabase.co"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres"

# Try with the secret key as password
SUPABASE_PASSWORD = "sb_secret_PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw"

# Alternative: try with the service role key
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

def execute_sql_file(filepath):
    """Execute SQL file against Supabase database"""

    # Read SQL file
    with open(filepath, 'r') as f:
        sql = f.read()

    # Try different connection approaches
    connection_attempts = [
        # Direct connection
        {
            'host': SUPABASE_HOST,
            'database': SUPABASE_DB,
            'user': SUPABASE_USER,
            'password': SUPABASE_PASSWORD,
            'port': 5432
        },
        # Pooler connection (transaction mode)
        {
            'host': f"aws-0-us-east-1.pooler.supabase.com",
            'database': SUPABASE_DB,
            'user': f"postgres.{SUPABASE_PROJECT_REF}",
            'password': SUPABASE_PASSWORD,
            'port': 6543
        }
    ]

    last_error = None

    for i, conn_params in enumerate(connection_attempts, 1):
        try:
            print(f"\nAttempt {i}: Connecting to {conn_params['host']}...")

            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            cursor = conn.cursor()

            print("✓ Connected successfully!")
            print("Executing SQL schema...")

            cursor.execute(sql)

            print("✓ Schema deployed successfully!")

            # Get list of tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            tables = cursor.fetchall()
            print(f"\n✓ Created {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")

            cursor.close()
            conn.close()
            return True

        except Exception as e:
            last_error = e
            print(f"✗ Attempt {i} failed: {e}")
            continue

    print(f"\n✗ All connection attempts failed.")
    print(f"\nLast error: {last_error}")
    print("\n" + "="*80)
    print("MANUAL DEPLOYMENT REQUIRED")
    print("="*80)
    print("\nThe schema could not be deployed automatically.")
    print("\nPlease deploy manually using ONE of these methods:")
    print("\n1. Supabase Dashboard SQL Editor:")
    print("   - Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql")
    print("   - Copy the contents of: supabase_schema.sql")
    print("   - Paste into the SQL editor")
    print("   - Click 'Run'")
    print("\n2. Get Database Password:")
    print("   - Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/settings/database")
    print("   - Copy the database password")
    print("   - Run: PGPASSWORD='your_password' psql -h db.vzsohavtuotocgrfkfyd.supabase.co -p 5432 -U postgres -d postgres -f supabase_schema.sql")
    print("\n3. Install Supabase CLI:")
    print("   - Follow: https://supabase.com/docs/guides/cli")
    print("   - Run: supabase db push")
    print("="*80)

    return False

if __name__ == "__main__":
    sql_file = "/home/user/Cloud_PMS/supabase_schema.sql"

    if not os.path.exists(sql_file):
        print(f"Error: SQL file not found: {sql_file}")
        sys.exit(1)

    success = execute_sql_file(sql_file)
    sys.exit(0 if success else 1)
