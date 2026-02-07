#!/usr/bin/env python3
"""
Backfill missing email_links for threads with extracted tokens.

This script finds threads that have extracted_tokens but no email_links,
and runs the linking ladder to create the missing links.

Usage:
    python scripts/autonomy/backfill_email_links.py [--limit N] [--dry-run]

Options:
    --limit N    Maximum number of threads to process (default: 100)
    --dry-run    Don't actually create links, just log what would be done
"""

import os
import sys
import asyncio
import argparse
import logging

# Add path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../apps/api/.env'))

from supabase import create_client
from services.linking_ladder import LinkingLadder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('backfill_email_links')

# Init clients
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')


async def get_threads_needing_links(supabase, limit: int) -> list:
    """
    Find threads that have extracted_tokens but no email_links.
    """
    # Get threads with tokens
    result = supabase.table('email_threads').select(
        'id, yacht_id, latest_subject, extracted_tokens, suggestions_generated_at'
    ).not_.is_(
        'extracted_tokens', 'null'
    ).not_.is_(
        'suggestions_generated_at', 'null'
    ).order('created_at', desc=True).limit(limit * 2).execute()

    if not result.data:
        return []

    # Filter to those without links
    threads_needing_links = []
    for thread in result.data:
        # Check if this thread has any links
        links = supabase.table('email_links').select('id').eq(
            'thread_id', thread['id']
        ).limit(1).execute()

        if not links.data:
            threads_needing_links.append(thread)
            if len(threads_needing_links) >= limit:
                break

    return threads_needing_links


async def backfill_thread(ladder: LinkingLadder, thread: dict, dry_run: bool) -> dict:
    """
    Run linking ladder for a single thread and create links.
    """
    thread_id = thread['id']
    yacht_id = thread['yacht_id']
    subject = thread.get('latest_subject', '')
    tokens = thread.get('extracted_tokens', {})

    logger.info(f"Processing thread {thread_id[:8]}... subject='{subject[:50]}'")

    result = {
        'thread_id': thread_id,
        'subject': subject,
        'tokens': tokens,
        'selection': None,
        'links_created': 0,
        'error': None
    }

    try:
        # Run linking ladder
        selection = await ladder.determine_primary(
            yacht_id=yacht_id,
            thread_id=thread_id,
            subject=subject,
            from_address='',
            attachments=None,
            participant_hashes=tokens.get('vendor', {}).get('participant_hashes', []),
            context=None
        )

        result['selection'] = selection

        if not selection:
            logger.debug(f"  -> No selection returned (L5)")
            return result

        logger.info(f"  -> {selection.get('level')} match: {selection.get('candidate', {}).get('label')}")

        if dry_run:
            logger.info(f"  -> [DRY RUN] Would create link")
            result['links_created'] = 1
            return result

        # Create links
        created_ids = await ladder.create_link_suggestion(
            yacht_id=yacht_id,
            thread_id=thread_id,
            selection=selection,
            max_suggestions=3
        )

        result['links_created'] = len(created_ids)
        logger.info(f"  -> Created {len(created_ids)} link(s)")

    except Exception as e:
        result['error'] = str(e)
        logger.error(f"  -> ERROR: {e}")

    return result


async def main():
    parser = argparse.ArgumentParser(description='Backfill missing email_links')
    parser.add_argument('--limit', type=int, default=100, help='Maximum threads to process')
    parser.add_argument('--dry-run', action='store_true', help='Do not create links')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("EMAIL LINKS BACKFILL")
    logger.info("=" * 60)
    logger.info(f"Limit: {args.limit}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 60)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    ladder = LinkingLadder(supabase)

    # Find threads needing links
    logger.info("\n1. Finding threads with tokens but no links...")
    threads = await get_threads_needing_links(supabase, args.limit)
    logger.info(f"   Found {len(threads)} thread(s) needing links")

    if not threads:
        logger.info("\n   No threads to process!")
        return

    # Process each thread
    logger.info(f"\n2. Processing threads...")
    stats = {
        'processed': 0,
        'links_created': 0,
        'l1_matches': 0,
        'l2_matches': 0,
        'l25_matches': 0,
        'l3_matches': 0,
        'l4_matches': 0,
        'l5_no_match': 0,
        'errors': 0,
    }

    for thread in threads:
        result = await backfill_thread(ladder, thread, args.dry_run)
        stats['processed'] += 1
        stats['links_created'] += result['links_created']

        if result['error']:
            stats['errors'] += 1
        elif result['selection']:
            level = result['selection'].get('level', 'L5')
            if level == 'L1':
                stats['l1_matches'] += 1
            elif level == 'L2':
                stats['l2_matches'] += 1
            elif level == 'L2.5':
                stats['l25_matches'] += 1
            elif level == 'L3':
                stats['l3_matches'] += 1
            elif level == 'L4':
                stats['l4_matches'] += 1
            else:
                stats['l5_no_match'] += 1
        else:
            stats['l5_no_match'] += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Processed:    {stats['processed']}")
    logger.info(f"Links created: {stats['links_created']}")
    logger.info(f"L1 matches:   {stats['l1_matches']}")
    logger.info(f"L2 matches:   {stats['l2_matches']}")
    logger.info(f"L2.5 matches: {stats['l25_matches']}")
    logger.info(f"L3 matches:   {stats['l3_matches']}")
    logger.info(f"L4 matches:   {stats['l4_matches']}")
    logger.info(f"L5 no match:  {stats['l5_no_match']}")
    logger.info(f"Errors:       {stats['errors']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
