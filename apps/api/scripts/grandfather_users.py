#!/usr/bin/env python3
"""
Grandfather Existing Users Migration Script
============================================

Migrates existing users from MASTER DB to TENANT DB by creating:
- auth_users_roles entries (yacht-specific role)
- auth_users_profiles entries (profile mirror)

Usage:
    # Dry run (default)
    python scripts/grandfather_users.py --yacht 85fe1119-b04c-41ac-80f1-829d23322598

    # Execute migration
    python scripts/grandfather_users.py --yacht 85fe1119-b04c-41ac-80f1-829d23322598 --execute

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
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def get_master_client() -> Client:
    """Get MASTER Supabase client."""
    url = os.getenv('MASTER_SUPABASE_URL')
    key = os.getenv('MASTER_SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise EnvironmentError("MASTER_SUPABASE_URL and MASTER_SUPABASE_SERVICE_KEY required")

    return create_client(url, key)


def get_tenant_client(yacht_id: str) -> Client:
    """Get TENANT Supabase client for a yacht."""
    # Map yacht_id to tenant key alias
    # For staging, we use yTEST_YACHT_001
    tenant_alias = os.getenv('DEFAULT_YACHT_CODE', 'yTEST_YACHT_001')

    url = os.getenv(f'{tenant_alias}_SUPABASE_URL')
    key = os.getenv(f'{tenant_alias}_SUPABASE_SERVICE_KEY')

    if not url or not key:
        raise EnvironmentError(f"{tenant_alias}_SUPABASE_URL and {tenant_alias}_SUPABASE_SERVICE_KEY required")

    return create_client(url, key)


def fetch_master_users(master: Client, yacht_id: str) -> List[Dict]:
    """Fetch users from MASTER.user_accounts for a yacht."""
    result = master.table('user_accounts').select(
        'id, yacht_id, role, status, created_at'
    ).eq('yacht_id', yacht_id).eq('status', 'active').execute()

    return result.data or []


def fetch_user_emails(master: Client, user_ids: List[str]) -> Dict[str, str]:
    """Fetch email addresses from MASTER.auth.users."""
    # Note: This requires service role access to auth.users
    try:
        emails = {}
        for user_id in user_ids:
            result = master.auth.admin.get_user_by_id(user_id)
            if result and result.user:
                emails[user_id] = result.user.email
        return emails
    except Exception as e:
        logger.warning(f"Could not fetch emails from auth.users: {e}")
        return {}


def check_existing_roles(tenant: Client, yacht_id: str, user_ids: List[str]) -> set:
    """Check which users already have auth_users_roles entries."""
    result = tenant.table('auth_users_roles').select('user_id').eq(
        'yacht_id', yacht_id
    ).in_('user_id', user_ids).execute()

    return {r['user_id'] for r in (result.data or [])}


def check_existing_profiles(tenant: Client, yacht_id: str, user_ids: List[str]) -> set:
    """Check which users already have auth_users_profiles entries."""
    result = tenant.table('auth_users_profiles').select('user_id').eq(
        'yacht_id', yacht_id
    ).in_('user_id', user_ids).execute()

    return {r['user_id'] for r in (result.data or [])}


def migrate_user_roles(
    tenant: Client,
    users: List[Dict],
    yacht_id: str,
    existing_roles: set,
    dry_run: bool
) -> int:
    """Create auth_users_roles entries for users."""
    migrated = 0
    now = datetime.now(timezone.utc).isoformat()

    for user in users:
        user_id = user['id']
        role = user.get('role', 'crew')

        if user_id in existing_roles:
            logger.info(f"SKIP: auth_users_roles exists for {user_id[:8]}...")
            continue

        if dry_run:
            logger.info(f"DRY RUN: Would create auth_users_roles: user={user_id[:8]}... role={role}")
        else:
            try:
                tenant.table('auth_users_roles').insert({
                    'user_id': user_id,
                    'yacht_id': yacht_id,
                    'role': role,
                    'is_active': True,
                    'valid_from': now,
                    'created_at': now,
                    'updated_at': now,
                    'notes': f'Grandfathered from MASTER - {datetime.now().date()}',
                }).execute()
                logger.info(f"CREATED: auth_users_roles for {user_id[:8]}... role={role}")
                migrated += 1
            except Exception as e:
                logger.error(f"FAILED: auth_users_roles for {user_id[:8]}...: {e}")

    return migrated


def migrate_user_profiles(
    tenant: Client,
    users: List[Dict],
    emails: Dict[str, str],
    yacht_id: str,
    existing_profiles: set,
    dry_run: bool
) -> int:
    """Create auth_users_profiles entries for users."""
    migrated = 0
    now = datetime.now(timezone.utc).isoformat()

    for user in users:
        user_id = user['id']
        email = emails.get(user_id, f"user-{user_id[:8]}@unknown.com")

        if user_id in existing_profiles:
            logger.info(f"SKIP: auth_users_profiles exists for {user_id[:8]}...")
            continue

        display_name = email.split('@')[0] if email else f"User {user_id[:8]}"

        if dry_run:
            logger.info(f"DRY RUN: Would create auth_users_profiles: user={user_id[:8]}... email={email}")
        else:
            try:
                tenant.table('auth_users_profiles').insert({
                    'user_id': user_id,
                    'yacht_id': yacht_id,
                    'email': email,
                    'display_name': display_name,
                    'created_at': now,
                }).execute()
                logger.info(f"CREATED: auth_users_profiles for {user_id[:8]}... email={email}")
                migrated += 1
            except Exception as e:
                logger.error(f"FAILED: auth_users_profiles for {user_id[:8]}...: {e}")

    return migrated


def main():
    parser = argparse.ArgumentParser(description='Grandfather existing users to TENANT DB')
    parser.add_argument('--yacht', required=True, help='Target yacht_id (UUID)')
    parser.add_argument('--execute', action='store_true', help='Execute migration (default is dry run)')
    args = parser.parse_args()

    yacht_id = args.yacht
    dry_run = not args.execute

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("EXECUTE MODE - Changes will be committed")
        logger.info("=" * 60)

    # Connect to databases
    logger.info(f"Connecting to MASTER and TENANT databases...")
    master = get_master_client()
    tenant = get_tenant_client(yacht_id)

    # Fetch users from MASTER
    logger.info(f"Fetching users for yacht {yacht_id}...")
    users = fetch_master_users(master, yacht_id)
    logger.info(f"Found {len(users)} active users in MASTER.user_accounts")

    if not users:
        logger.warning("No users found - nothing to migrate")
        return

    user_ids = [u['id'] for u in users]

    # Fetch emails
    logger.info("Fetching user emails from MASTER.auth.users...")
    emails = fetch_user_emails(master, user_ids)
    logger.info(f"Retrieved {len(emails)} email addresses")

    # Check existing TENANT entries
    logger.info("Checking existing TENANT entries...")
    existing_roles = check_existing_roles(tenant, yacht_id, user_ids)
    existing_profiles = check_existing_profiles(tenant, yacht_id, user_ids)
    logger.info(f"Existing: {len(existing_roles)} roles, {len(existing_profiles)} profiles")

    # Migrate roles
    logger.info("")
    logger.info("--- Migrating auth_users_roles ---")
    roles_migrated = migrate_user_roles(tenant, users, yacht_id, existing_roles, dry_run)

    # Migrate profiles
    logger.info("")
    logger.info("--- Migrating auth_users_profiles ---")
    profiles_migrated = migrate_user_profiles(tenant, users, emails, yacht_id, existing_profiles, dry_run)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total users found:       {len(users)}")
    logger.info(f"Roles already exist:     {len(existing_roles)}")
    logger.info(f"Profiles already exist:  {len(existing_profiles)}")
    if dry_run:
        logger.info(f"Roles to create:         {len(users) - len(existing_roles)}")
        logger.info(f"Profiles to create:      {len(users) - len(existing_profiles)}")
        logger.info("")
        logger.info("Run with --execute to apply changes")
    else:
        logger.info(f"Roles created:           {roles_migrated}")
        logger.info(f"Profiles created:        {profiles_migrated}")


if __name__ == '__main__':
    main()
