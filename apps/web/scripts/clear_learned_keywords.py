#!/usr/bin/env python3
"""
Clear all learned_keywords for a yacht.

Usage:
    python3 scripts/clear_learned_keywords.py --yacht-id <yacht_id>
"""

import argparse
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


def clear_learned_keywords(client: Client, yacht_id: str) -> int:
    """Clear all learned_keywords for a yacht."""
    logger.info(f"Clearing learned_keywords for yacht {yacht_id}...")

    # Update all rows to empty string
    result = client.table('search_index').update({
        'learned_keywords': '',
        'learned_at': None
    }).eq('yacht_id', yacht_id).execute()

    logger.info(f"✅ Cleared learned_keywords for yacht {yacht_id}")
    return len(result.data) if result.data else 0


def main():
    parser = argparse.ArgumentParser(description="Clear learned_keywords for a yacht")
    parser.add_argument("--yacht-id", required=True, help="UUID of the yacht")
    args = parser.parse_args()

    supabase_url = os.environ.get("TENANT_SUPABASE_URL")
    service_key = os.environ.get("TENANT_SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        logger.error("❌ TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    client = create_client(supabase_url, service_key)
    count = clear_learned_keywords(client, args.yacht_id)
    logger.info(f"✅ Complete! Cleared {count} rows")


if __name__ == "__main__":
    main()
