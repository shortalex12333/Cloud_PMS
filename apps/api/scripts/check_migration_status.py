#!/usr/bin/env python3
"""
Check Migration Status on TENANT Database
==========================================

Checks which migrations have been applied to the database by querying
the supabase_migrations.schema_migrations table.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.supabase import get_supabase_client

def check_migrations():
    """Check which migrations have been applied."""

    print("=" * 80)
    print("CHECKING MIGRATION STATUS ON TENANT DATABASE")
    print("=" * 80)
    print("")

    # Get Supabase client
    supabase = get_supabase_client()

    # Check for RLS security migrations
    critical_migrations = [
        "20260125_fix_cross_yacht_notes",
        "20260125_fix_cross_yacht_parts",
        "20260125_fix_cross_yacht_part_usage",
    ]

    print("Checking critical RLS security migrations:")
    print("")

    for migration in critical_migrations:
        print(f"  Checking: {migration}")

        try:
            # Query schema_migrations table
            result = supabase.table("supabase_migrations.schema_migrations")\
                .select("version, name")\
                .like("version", f"{migration}%")\
                .execute()

            if result.data and len(result.data) > 0:
                print(f"    ✅ APPLIED: {result.data[0].get('version')}")
            else:
                print(f"    ❌ NOT APPLIED")
        except Exception as e:
            print(f"    ⚠️  Could not check: {e}")

        print("")

    print("=" * 80)
    print("")

if __name__ == "__main__":
    check_migrations()
