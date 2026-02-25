#!/usr/bin/env python3
"""
Fix learned_keywords format: Convert from JSONB arrays to TEXT strings.

The learned_keywords column should be TEXT (space-separated), not JSONB.
This script converts all JSONB arrays to space-separated TEXT format.

Usage:
    python3 scripts/fix_learned_keywords_format.py --yacht-id <yacht_id>
"""

import argparse
import json
import logging
import os
import sys

from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_supabase_client(url: str, service_key: str) -> Client:
    """Create Supabase client with service role key."""
    try:
        client = create_client(url, service_key)
        logger.info("✅ Connected to Supabase")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)


def fix_learned_keywords_format(client: Client, yacht_id: str) -> dict:
    """
    Convert learned_keywords from JSONB arrays to TEXT strings.

    Args:
        client: Supabase client
        yacht_id: UUID of yacht to fix

    Returns:
        Statistics dict
    """
    stats = {
        'rows_checked': 0,
        'rows_updated': 0,
        'rows_skipped': 0,
    }

    logger.info("=" * 80)
    logger.info("FIXING LEARNED_KEYWORDS FORMAT")
    logger.info("=" * 80)
    logger.info(f"Yacht ID: {yacht_id}")
    logger.info("")

    # Get all rows with non-null learned_keywords
    try:
        result = client.table('search_index').select('id, learned_keywords').eq('yacht_id', yacht_id).execute()

        all_rows = result.data
        stats['rows_checked'] = len(all_rows)

        logger.info(f"Found {len(all_rows)} rows to check")

        for row in all_rows:
            entity_id = row['id']
            learned_keywords = row.get('learned_keywords')

            if not learned_keywords:
                stats['rows_skipped'] += 1
                continue

            # Check if it's a JSONB array (list)
            if isinstance(learned_keywords, list):
                # Convert array to space-separated string
                keywords_text = ' '.join(learned_keywords)

                # Update the row
                client.table('search_index').update({
                    'learned_keywords': keywords_text
                }).eq('id', entity_id).execute()

                stats['rows_updated'] += 1

                if stats['rows_updated'] % 100 == 0:
                    logger.info(f"  Updated {stats['rows_updated']} rows...")
            else:
                # Already TEXT format
                stats['rows_skipped'] += 1

        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Rows checked:  {stats['rows_checked']}")
        logger.info(f"Rows updated:  {stats['rows_updated']}")
        logger.info(f"Rows skipped:  {stats['rows_skipped']}")
        logger.info("")
        logger.info("✅ Format conversion complete!")

        return stats

    except Exception as e:
        logger.error(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Fix learned_keywords format from JSONB to TEXT"
    )
    parser.add_argument(
        "--yacht-id",
        required=True,
        help="UUID of the yacht to fix"
    )

    args = parser.parse_args()

    # Get Supabase credentials from environment
    supabase_url = os.environ.get("TENANT_SUPABASE_URL")
    service_key = os.environ.get("TENANT_SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        logger.error("❌ TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_KEY environment variables are required")
        sys.exit(1)

    # Create Supabase client
    client = get_supabase_client(supabase_url, service_key)

    # Run the conversion
    fix_learned_keywords_format(client, args.yacht_id)


if __name__ == "__main__":
    main()
