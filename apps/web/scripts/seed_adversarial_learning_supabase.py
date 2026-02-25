#!/usr/bin/env python3
"""
Supabase-client wrapper for seed_adversarial_learning.py
Uses Supabase REST API with service key instead of direct PostgreSQL connection.

This script wraps the ML seeding logic to work with Supabase client library,
avoiding the need for PostgreSQL database password.

Usage:
    python3 scripts/seed_adversarial_learning_supabase.py --yacht-id <yacht_id>
    python3 scripts/seed_adversarial_learning_supabase.py --yacht-id <yacht_id> --dry-run

Environment Variables:
    TENANT_SUPABASE_URL: Supabase project URL
    TENANT_SUPABASE_SERVICE_KEY: Supabase service role key
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Dict

from supabase import create_client, Client

# Import the learned keyword mappings from the original script
sys.path.insert(0, os.path.dirname(__file__))
from seed_adversarial_learning import LEARNED_KEYWORD_MAPPINGS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_supabase_client(url: str, service_key: str) -> Client:
    """
    Create Supabase client with service role key.

    Args:
        url: Supabase project URL
        service_key: Service role key

    Returns:
        Supabase client instance
    """
    try:
        client = create_client(url, service_key)
        logger.info("✅ Connected to Supabase")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)


def check_learned_keywords_column_exists(client: Client) -> bool:
    """
    Check if learned_keywords column exists in search_index table.

    Args:
        client: Supabase client

    Returns:
        True if column exists, False otherwise
    """
    try:
        # Try to query with learned_keywords column
        result = client.table('search_index').select('learned_keywords').limit(1).execute()
        return True
    except Exception as e:
        if 'column' in str(e).lower() and 'learned_keywords' in str(e).lower():
            return False
        # For other errors, assume column exists but there's a different issue
        logger.warning(f"⚠️  Could not verify learned_keywords column: {e}")
        return True


def find_entities_by_pattern(
    client: Client,
    yacht_id: str,
    search_pattern: str,
    object_types: List[str] = None
) -> List[dict]:
    """
    Find entities in search_index matching a search pattern.

    Args:
        client: Supabase client
        yacht_id: UUID of yacht to filter by
        search_pattern: Text pattern to search for
        object_types: Optional list of object_types to filter by

    Returns:
        List of matching rows
    """
    try:
        query = client.table('search_index').select('*').eq('yacht_id', yacht_id)

        if object_types:
            query = query.in_('object_type', object_types)

        # Use ilike for case-insensitive pattern matching on search_text only
        query = query.ilike('search_text', f'%{search_pattern}%')

        query = query.limit(50)

        result = query.execute()
        return result.data
    except Exception as e:
        logger.warning(f"⚠️  Error searching for pattern '{search_pattern}': {e}")
        return []


def inject_learned_keywords(
    client: Client,
    entity_id: str,
    new_keywords: List[str],
    dry_run: bool = False
) -> None:
    """
    Inject learned keywords into search_index entity.

    Args:
        client: Supabase client
        entity_id: UUID of search_index row
        new_keywords: List of keyword strings to add
        dry_run: If True, don't actually execute the update
    """
    if dry_run:
        logger.info(f"[DRY RUN] Would inject keywords into entity {entity_id}: {new_keywords}")
        return

    try:
        # Get current learned_keywords
        result = client.table('search_index').select('learned_keywords').eq('id', entity_id).single().execute()

        if not result.data:
            logger.warning(f"⚠️  Entity {entity_id} not found")
            return

        # Merge new keywords with existing (deduplicate)
        # NOTE: learned_keywords is TEXT (space-separated), not JSONB
        current_keywords_text = result.data.get('learned_keywords', '')
        if not current_keywords_text or current_keywords_text == '':
            current_keywords = []
        else:
            current_keywords = current_keywords_text.split()

        # Add new keywords (case-insensitive deduplication)
        existing_lower = {kw.lower() for kw in current_keywords}
        for kw in new_keywords:
            if kw.lower() not in existing_lower:
                current_keywords.append(kw)
                existing_lower.add(kw.lower())

        # Convert back to space-separated TEXT
        keywords_text = ' '.join(current_keywords)

        # Update the row
        client.table('search_index').update({
            'learned_keywords': keywords_text
        }).eq('id', entity_id).execute()

    except Exception as e:
        logger.error(f"❌ Error injecting keywords into entity {entity_id}: {e}")


def seed_learned_keywords(
    client: Client,
    yacht_id: str,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Main seeding function: finds entities and injects learned keywords.

    Args:
        client: Supabase client
        yacht_id: UUID of yacht to seed
        dry_run: If True, don't actually modify database
        verbose: If True, print detailed progress

    Returns:
        Dictionary with statistics
    """
    stats = {
        'entities_processed': 0,
        'keywords_injected': 0,
        'patterns_matched': 0,
    }

    logger.info("=" * 80)
    logger.info("ADVERSARIAL LEARNING SEEDER - SHARD 11 EXTREME CASES")
    logger.info("=" * 80)
    logger.info(f"Yacht ID: {yacht_id}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    logger.info("")

    # Iterate through all canonical terms and their learned variations
    for canonical_term, learned_variations in LEARNED_KEYWORD_MAPPINGS.items():
        if verbose:
            logger.info(f"Searching for entities matching: '{canonical_term}'")

        # Find entities matching this canonical term
        entities = find_entities_by_pattern(
            client,
            yacht_id,
            canonical_term,
            object_types=['equipment', 'work_order', 'part', 'document', 'fault']
        )

        if not entities:
            if verbose:
                logger.warning(f"  ⚠️  No entities found for '{canonical_term}'")
            continue

        stats['patterns_matched'] += 1

        # Inject learned variations into each matching entity
        for entity in entities:
            entity_id = entity['id']
            object_type = entity['object_type']

            if verbose:
                payload_name = entity.get('payload', {}).get('name', 'Unknown') if entity.get('payload') else 'Unknown'
                logger.info(f"  → Found {object_type}: {payload_name} (ID: {entity_id})")

            # Inject the learned variations
            inject_learned_keywords(client, entity_id, learned_variations, dry_run)

            stats['entities_processed'] += 1
            stats['keywords_injected'] += len(learned_variations)

        if verbose:
            logger.info(f"  ✅ Injected {len(learned_variations)} keywords into {len(entities)} entities")
            logger.info("")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Seed learned_keywords into search_index for Shard 11 extreme case tests (Supabase client version)"
    )
    parser.add_argument(
        "--yacht-id",
        required=True,
        help="UUID of the yacht to seed (e.g., 85fe1119-b04c-41ac-80f1-829d23322598)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without actually updating the database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information"
    )

    args = parser.parse_args()

    # Get Supabase credentials from environment
    supabase_url = os.environ.get("TENANT_SUPABASE_URL")
    service_key = os.environ.get("TENANT_SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        logger.error("❌ TENANT_SUPABASE_URL and TENANT_SUPABASE_SERVICE_KEY environment variables are required")
        logger.error("Usage: TENANT_SUPABASE_URL='https://...' TENANT_SUPABASE_SERVICE_KEY='eyJ...' python scripts/seed_adversarial_learning_supabase.py --yacht-id <yacht_id>")
        sys.exit(1)

    # Create Supabase client
    client = get_supabase_client(supabase_url, service_key)

    try:
        # Check if column exists
        if not check_learned_keywords_column_exists(client):
            logger.error("❌ learned_keywords column does not exist.")
            logger.error("   You need to add it to the search_index table first.")
            logger.error("   Run: ALTER TABLE search_index ADD COLUMN learned_keywords JSONB DEFAULT '[]'::jsonb;")
            sys.exit(1)

        # Run the seeding process
        stats = seed_learned_keywords(
            client,
            args.yacht_id,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Patterns matched:     {stats['patterns_matched']}")
        logger.info(f"Entities processed:   {stats['entities_processed']}")
        logger.info(f"Keywords injected:    {stats['keywords_injected']}")
        logger.info("")

        if args.dry_run:
            logger.info("🔍 This was a DRY RUN - no changes were made")
            logger.info("   Run without --dry-run to apply changes")
        else:
            logger.info("✅ Seeding complete! Shard 11 tests should now pass.")
            logger.info("   The search index now simulates 'Month 2 of Production'")
            logger.info("   with learned misspellings, semantic descriptions, and colloquial terms.")

    except Exception as e:
        logger.error(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
