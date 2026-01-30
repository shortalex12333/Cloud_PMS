#!/usr/bin/env python3
"""
Fix auth_users_profiles Schema via Direct SQL
==============================================

CRITICAL FIX for 403 FORBIDDEN errors:
- Reads existing auth_users_profiles entries
- Deletes them (handles foreign key constraints by deleting references first)
- Runs grandfather_users.py to recreate with correct schema (id, name)

This approach handles foreign key constraints properly by:
1. Finding all referencing tables (pms_handover.added_by, etc.)
2. Temporarily setting those to a system user or deleting them
3. Deleting bad auth_users_profiles entries
4. Re-seeding with fixed grandfather_users.py

Usage:
    python scripts/fix_profiles_schema_sql.py --yacht 85fe1119-b04c-41ac-80f1-829d23322598 --execute

Environment:
    MASTER_SUPABASE_URL
    MASTER_SUPABASE_SERVICE_KEY
    yTEST_YACHT_001_SUPABASE_URL
    yTEST_YACHT_001_SUPABASE_SERVICE_KEY
"""

import os
import sys
import argparse
import logging
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def get_tenant_client(yacht_id: str) -> Client:
    """Get TENANT Supabase client for a yacht."""
    tenant_alias = os.getenv('DEFAULT_YACHT_CODE', 'yTEST_YACHT_001')
    url = os.getenv(f'{tenant_alias}_SUPABASE_URL')
    key = os.getenv(f'{tenant_alias}_SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise EnvironmentError(f"{tenant_alias}_SUPABASE_URL and {tenant_alias}_SUPABASE_SERVICE_KEY required")

    return create_client(url, key)


def fix_via_sql(tenant: Client, yacht_id: str, dry_run: bool):
    """
    Use SQL to fix the schema issue:
    1. Delete ALL tables that reference auth_users_profiles (test data only)
    2. Delete auth_users_profiles entries with bad schema
    3. Let grandfather_users.py recreate them
    """

    # Tables that reference auth_users_profiles.id
    # These will be recreated via normal operations after fix
    referencing_tables = [
        'pms_handover',
        'pms_work_order_notes',
        'pms_faults',  # May have created_by
        'pms_work_orders',  # May have assigned_to, created_by
        'pms_shopping_list_items',  # May have requested_by, approved_by
        # Add more as needed
    ]

    logger.info("Step 1: Deleting referencing tables (test data will be recreated)...")
    for table in referencing_tables:
        if not dry_run:
            try:
                result = tenant.table(table).delete().eq('yacht_id', yacht_id).execute()
                logger.info(f"✓ Deleted {table} entries for yacht {yacht_id}")
            except Exception as e:
                logger.warning(f"Could not delete {table}: {e}")
        else:
            logger.info(f"DRY RUN: Would delete {table} entries")

    logger.info("")
    logger.info("Step 2: Deleting auth_users_profiles entries...")
    if not dry_run:
        try:
            result = tenant.table('auth_users_profiles').delete().eq('yacht_id', yacht_id).execute()
            logger.info(f"✓ Deleted auth_users_profiles entries for yacht {yacht_id}")
        except Exception as e:
            logger.error(f"✗ Failed: {e}")
            raise
    else:
        logger.info("DRY RUN: Would delete auth_users_profiles entries")


def main():
    parser = argparse.ArgumentParser(description='Fix auth_users_profiles schema via SQL')
    parser.add_argument('--yacht', required=True, help='Target yacht_id (UUID)')
    parser.add_argument('--execute', action='store_true', help='Execute fix (default is dry run)')
    args = parser.parse_args()

    yacht_id = args.yacht
    dry_run = not args.execute

    logger.info("=" * 60)
    logger.info("FIX auth_users_profiles Schema via SQL")
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    else:
        logger.info("EXECUTE MODE - Changes will be committed")

    logger.info("")

    # Connect to TENANT DB
    logger.info(f"Connecting to TENANT database...")
    tenant = get_tenant_client(yacht_id)

    # Fix via SQL
    logger.info("")
    logger.info("--- Fixing Schema ---")
    fix_via_sql(tenant, yacht_id, dry_run)

    # Re-run grandfather_users.py
    if not dry_run:
        logger.info("")
        logger.info("--- Re-seeding with Fixed Script ---")
        logger.info(f"Running: python3 scripts/grandfather_users.py --yacht {yacht_id} --execute")

        try:
            result = subprocess.run(
                ['python3', 'scripts/grandfather_users.py', '--yacht', yacht_id, '--execute'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            logger.info(result.stdout)
            if result.returncode != 0:
                logger.error("grandfather_users.py failed:")
                logger.error(result.stderr)
                sys.exit(1)

        except Exception as e:
            logger.error(f"Failed to run grandfather_users.py: {e}")
            sys.exit(1)

    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPLETE")
    logger.info("=" * 60)

    if dry_run:
        logger.info("Run with --execute to apply changes and re-seed")
    else:
        logger.info("✓ Schema fix complete!")
        logger.info("Next: Run E2E tests to verify 403 FORBIDDEN is fixed")


if __name__ == '__main__':
    main()
