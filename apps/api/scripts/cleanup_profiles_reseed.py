#!/usr/bin/env python3
"""
Cleanup and Re-seed auth_users_profiles
========================================

CRITICAL FIX for 403 FORBIDDEN errors:
- Old entries used wrong column names (user_id, display_name)
- Handlers expect correct column names (id, name)
- This script deletes bad entries and re-runs grandfather_users.py

Usage:
    # Dry run (shows what would be deleted)
    python scripts/cleanup_profiles_reseed.py --yacht 85fe1119-b04c-41ac-80f1-829d23322598

    # Execute cleanup + re-seed
    python scripts/cleanup_profiles_reseed.py --yacht 85fe1119-b04c-41ac-80f1-829d23322598 --execute

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

# Add parent directory to path
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


def cleanup_profiles(tenant: Client, yacht_id: str, dry_run: bool) -> int:
    """Delete all auth_users_profiles entries for yacht (will be recreated)."""
    # Query existing entries
    result = tenant.table('auth_users_profiles').select('id, yacht_id, email').eq(
        'yacht_id', yacht_id
    ).execute()

    count = len(result.data or [])

    if count == 0:
        logger.info("No existing auth_users_profiles entries found")
        return 0

    logger.info(f"Found {count} auth_users_profiles entries to delete:")
    for entry in result.data:
        logger.info(f"  - {entry.get('id', 'unknown')[:8]}... {entry.get('email', 'no-email')}")

    if dry_run:
        logger.info(f"DRY RUN: Would delete {count} entries")
        return count
    else:
        try:
            tenant.table('auth_users_profiles').delete().eq('yacht_id', yacht_id).execute()
            logger.info(f"✓ Deleted {count} auth_users_profiles entries")
            return count
        except Exception as e:
            logger.error(f"✗ Failed to delete entries: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Cleanup bad auth_users_profiles and re-seed')
    parser.add_argument('--yacht', required=True, help='Target yacht_id (UUID)')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup and re-seed (default is dry run)')
    args = parser.parse_args()

    yacht_id = args.yacht
    dry_run = not args.execute

    logger.info("=" * 60)
    logger.info("CLEANUP & RE-SEED auth_users_profiles")
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    else:
        logger.info("EXECUTE MODE - Changes will be committed")

    logger.info("")

    # Step 1: Connect to TENANT DB
    logger.info(f"Connecting to TENANT database...")
    tenant = get_tenant_client(yacht_id)

    # Step 2: Cleanup bad entries
    logger.info("")
    logger.info("--- STEP 1: Delete Bad Entries ---")
    deleted = cleanup_profiles(tenant, yacht_id, dry_run)

    # Step 3: Re-run grandfather_users.py
    if not dry_run and deleted > 0:
        logger.info("")
        logger.info("--- STEP 2: Re-seed with Fixed Script ---")
        logger.info("Running: python scripts/grandfather_users.py --yacht {} --execute".format(yacht_id))

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

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Entries deleted: {deleted}")

    if dry_run:
        logger.info("")
        logger.info("Run with --execute to apply changes and re-seed")
    else:
        logger.info("✓ Cleanup and re-seed complete!")
        logger.info("")
        logger.info("Next: Run E2E tests to verify 403 FORBIDDEN is fixed")


if __name__ == '__main__':
    main()
