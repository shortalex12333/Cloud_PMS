#!/usr/bin/env python3
"""
Backfill webLink for existing email messages.

Fetches webLink from Microsoft Graph API for each message
that doesn't have a web_link value in the database.

Usage:
  python backfill_weblink.py --user-id <USER_ID> --yacht-id <YACHT_ID>

Environment:
  TENANT_SUPABASE_URL - Supabase tenant database URL
  TENANT_SUPABASE_KEY - Service role key
"""

import asyncio
import argparse
import os
import sys
import logging
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# MASTER database (for auth tokens)
MASTER_SUPABASE_URL = os.getenv('MASTER_SUPABASE_URL', 'https://qvzmkaamzaqxpzbewjxe.supabase.co')
MASTER_SUPABASE_KEY = os.getenv('MASTER_SUPABASE_KEY', '')

# Tenant database (for email messages)
TENANT_SUPABASE_URL = os.getenv('TENANT_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
TENANT_SUPABASE_KEY = os.getenv('TENANT_SUPABASE_KEY', os.getenv('SUPABASE_SERVICE_ROLE_KEY', ''))


async def get_graph_token(master_supabase, user_id: str, yacht_id: str) -> Optional[str]:
    """Get Microsoft Graph access token for user from MASTER database."""
    result = master_supabase.table('auth_microsoft_tokens').select(
        'microsoft_access_token, token_expires_at'
    ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
        'provider', 'microsoft_graph'
    ).eq('token_purpose', 'read').eq('is_revoked', 'false').maybe_single().execute()

    if not result.data:
        logger.error("No read token found for user")
        return None

    # Check if expired
    expires_at_str = result.data.get('token_expires_at', '')
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at < datetime.now(expires_at.tzinfo):
                logger.warning("Token is expired - need refresh")
                # For now, return it anyway and let Graph API fail
        except Exception as e:
            logger.warning(f"Could not parse expiry: {e}")

    return result.data.get('microsoft_access_token')


async def fetch_weblink(client: httpx.AsyncClient, token: str, provider_message_id: str) -> Optional[str]:
    """Fetch webLink for a single message from Graph API."""
    url = f"{GRAPH_BASE_URL}/me/messages/{provider_message_id}?$select=id,webLink"

    try:
        response = await client.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
            timeout=15.0
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('webLink')
        elif response.status_code == 404:
            logger.debug(f"Message not found in Graph: {provider_message_id[:20]}...")
            return None
        else:
            logger.warning(f"Graph API error {response.status_code} for {provider_message_id[:20]}...")
            return None

    except Exception as e:
        logger.error(f"Error fetching webLink: {e}")
        return None


async def backfill_messages(user_id: str, yacht_id: str, batch_size: int = 50, dry_run: bool = False):
    """
    Backfill webLink for all messages without it.
    """
    if not TENANT_SUPABASE_KEY:
        logger.error("TENANT_SUPABASE_KEY not set")
        return

    # TENANT database has both tokens and messages
    tenant_supabase = create_client(TENANT_SUPABASE_URL, TENANT_SUPABASE_KEY)

    # Get Graph token from TENANT (auth_microsoft_tokens is in tenant DB)
    token = await get_graph_token(tenant_supabase, user_id, yacht_id)
    if not token:
        logger.error("Could not get Graph token")
        return

    # Get messages without web_link from TENANT
    logger.info("Fetching messages without web_link...")
    result = tenant_supabase.table('email_messages').select(
        'id, provider_message_id'
    ).eq('yacht_id', yacht_id).is_('web_link', 'null').limit(1000).execute()

    messages = result.data or []
    logger.info(f"Found {len(messages)} messages without web_link")

    if not messages:
        logger.info("Nothing to backfill!")
        return

    if dry_run:
        logger.info("[DRY RUN] Would backfill these messages:")
        for msg in messages[:10]:
            logger.info(f"  - {msg['id']}: {msg['provider_message_id'][:30]}...")
        if len(messages) > 10:
            logger.info(f"  ... and {len(messages) - 10} more")
        return

    # Process in batches
    updated = 0
    failed = 0
    skipped = 0

    async with httpx.AsyncClient() as client:
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} messages)...")

            for msg in batch:
                weblink = await fetch_weblink(client, token, msg['provider_message_id'])

                if weblink:
                    # Update TENANT database
                    try:
                        tenant_supabase.table('email_messages').update({
                            'web_link': weblink
                        }).eq('id', msg['id']).execute()
                        updated += 1
                        logger.debug(f"Updated {msg['id'][:8]}... with webLink")
                    except Exception as e:
                        logger.error(f"Failed to update {msg['id']}: {e}")
                        failed += 1
                else:
                    skipped += 1

            # Small delay between batches to respect rate limits
            await asyncio.sleep(0.5)

    logger.info(f"\n=== BACKFILL COMPLETE ===")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped (no webLink): {skipped}")
    logger.info(f"Failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description='Backfill webLink for email messages')
    parser.add_argument('--user-id', required=True, help='User ID')
    parser.add_argument('--yacht-id', required=True, help='Yacht ID')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    asyncio.run(backfill_messages(
        user_id=args.user_id,
        yacht_id=args.yacht_id,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))


if __name__ == '__main__':
    main()
