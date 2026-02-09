#!/usr/bin/env python3
"""
Apply RLS Security Migrations to Production Database
====================================================

Applies critical RLS security fixes (B1, B2, B3) to the TENANT database.

Migrations:
- B1: 20260125_fix_cross_yacht_notes.sql
- B2: 20260125_fix_cross_yacht_parts.sql
- B3: 20260125_fix_cross_yacht_part_usage.sql
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql

# Migration files to apply
MIGRATIONS = [
    {
        "file": "20260125_fix_cross_yacht_notes.sql",
        "blocker": "B1",
        "description": "Fix pms_work_order_notes cross-yacht leakage"
    },
    {
        "file": "20260125_fix_cross_yacht_parts.sql",
        "blocker": "B2",
        "description": "Fix pms_work_order_parts cross-yacht leakage"
    },
    {
        "file": "20260125_fix_cross_yacht_part_usage.sql",
        "blocker": "B3",
        "description": "Fix pms_part_usage cross-yacht leakage"
    }
]

def get_connection_string():
    """Build PostgreSQL connection string from environment."""
    tenant_url = os.getenv("TENANT_1_SUPABASE_URL", "")
    tenant_password = os.getenv("TENANT_1_DB_PASSWORD", "")

    if not tenant_url or not tenant_password:
        raise ValueError("Missing TENANT_1_SUPABASE_URL or TENANT_1_DB_PASSWORD")

    # Extract project ref from URL (e.g., vzsohavtuotocgrfkfyd from https://vzsohavtuotocgrfkfyd.supabase.co)
    project_ref = tenant_url.replace("https://", "").replace(".supabase.co", "")

    # Build connection string for direct PostgreSQL connection
    # Supabase uses port 6543 for direct PostgreSQL connections with pooler
    conn_string = f"postgresql://postgres.{project_ref}:{tenant_password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

    return conn_string

def check_migration_applied(cursor, migration_file):
    """Check if a migration has already been applied."""
    migration_name = migration_file.replace(".sql", "")

    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM supabase_migrations.schema_migrations
                WHERE version LIKE %s
            )
        """, (f"{migration_name}%",))

        result = cursor.fetchone()
        return result[0] if result else False
    except Exception as e:
        print(f"  ⚠️  Could not check migration status: {e}")
        return False

def apply_migration(cursor, migration_path):
    """Apply a migration file to the database."""
    try:
        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        # Execute the migration
        cursor.execute(migration_sql)

        return True
    except Exception as e:
        print(f"  ❌ Error applying migration: {e}")
        return False

def main():
    """Main migration application function."""
    print("=" * 80)
    print("APPLYING RLS SECURITY MIGRATIONS TO TENANT DATABASE")
    print("=" * 80)
    print("")

    # Get migrations directory
    migrations_dir = Path(__file__).parent.parent.parent / "supabase" / "migrations"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    print(f"Migrations directory: {migrations_dir}")
    print("")

    # Get database connection
    try:
        conn_string = get_connection_string()
        print("Connecting to TENANT database...")
        conn = psycopg2.connect(conn_string)
        conn.autocommit = False  # Use transactions
        cursor = conn.cursor()
        print("✅ Connected to database")
        print("")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("")
        print("Alternative: Use Supabase SQL Editor")
        print("1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql")
        print("2. Copy and paste each migration file")
        print("3. Execute each migration")
        print("")
        return

    # Apply each migration
    applied_count = 0
    skipped_count = 0
    failed_count = 0

    for migration_info in MIGRATIONS:
        migration_file = migration_info["file"]
        blocker = migration_info["blocker"]
        description = migration_info["description"]

        print(f"Migration: {migration_file}")
        print(f"  Blocker: {blocker}")
        print(f"  Description: {description}")

        migration_path = migrations_dir / migration_file

        if not migration_path.exists():
            print(f"  ❌ Migration file not found: {migration_path}")
            failed_count += 1
            print("")
            continue

        # Check if already applied
        if check_migration_applied(cursor, migration_file):
            print(f"  ⏭️  Already applied - skipping")
            skipped_count += 1
            print("")
            continue

        # Apply migration
        print(f"  📝 Applying migration...")

        try:
            if apply_migration(cursor, migration_path):
                conn.commit()
                print(f"  ✅ Migration applied successfully")
                applied_count += 1
            else:
                conn.rollback()
                print(f"  ❌ Migration failed")
                failed_count += 1
        except Exception as e:
            conn.rollback()
            print(f"  ❌ Migration failed: {e}")
            failed_count += 1

        print("")

    # Close connection
    cursor.close()
    conn.close()

    # Summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"  Applied: {applied_count}")
    print(f"  Skipped (already applied): {skipped_count}")
    print(f"  Failed: {failed_count}")
    print("")

    if failed_count > 0:
        print("⚠️  Some migrations failed. Review errors above.")
        print("")
        print("Manual Application Steps:")
        print("1. Go to Supabase SQL Editor:")
        print("   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql")
        print("")
        print("2. Copy and paste each migration file content:")
        for migration_info in MIGRATIONS:
            migration_path = migrations_dir / migration_info["file"]
            print(f"   - {migration_path}")
        print("")
        print("3. Execute each migration in the SQL editor")
        print("")
    elif applied_count > 0:
        print("✅ All migrations applied successfully!")
        print("")
        print("Next steps:")
        print("1. Run RLS security tests to verify: python3 tests/test_work_order_rls_security.py")
        print("2. Check yacht isolation is working correctly")
        print("")
    else:
        print("✅ All migrations already applied - no action needed")
        print("")

if __name__ == "__main__":
    main()
