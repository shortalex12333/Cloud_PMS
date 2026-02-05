#!/usr/bin/env python3
"""
Backfill entity extraction for email messages.

Purpose: Populate email_extraction_results for messages lacking entity extraction.

Usage:
    python backfill_entity_extraction.py --yacht-id <yacht_id> --limit 100 --dry-run
    python backfill_entity_extraction.py --yacht-id <yacht_id> --limit 100
"""

import os
import sys
import argparse
import logging
import asyncio
from typing import List, Dict, Any

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client

from email_rag.entity_extractor import EmailEntityExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Tenant database
TENANT_SUPABASE_URL = os.getenv('TENANT_SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
TENANT_SUPABASE_KEY = os.getenv('TENANT_SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY')


def get_supabase_client() -> Client:
    """Get Supabase client."""
    return create_client(TENANT_SUPABASE_URL, TENANT_SUPABASE_KEY)


def get_messages_without_extraction(supabase: Client, yacht_id: str, limit: int) -> List[Dict]:
    """Get messages without extraction results."""

    # Get message IDs that already have extraction
    existing = supabase.table('email_extraction_results').select(
        'message_id'
    ).eq('yacht_id', yacht_id).execute()

    existing_ids = {r['message_id'] for r in (existing.data or [])}

    # Get messages without extraction
    result = supabase.table('email_messages').select(
        'id, subject, preview_text'
    ).eq('yacht_id', yacht_id).order(
        'sent_at', desc=True
    ).limit(limit * 2).execute()  # Fetch more, filter after

    messages = []
    for msg in (result.data or []):
        if msg['id'] not in existing_ids:
            messages.append(msg)
            if len(messages) >= limit:
                break

    return messages


def extract_and_store(
    supabase: Client,
    yacht_id: str,
    message_id: str,
    subject: str,
    preview_text: str,
    dry_run: bool = False
) -> int:
    """
    Extract entities and store results.

    Returns:
        Number of entities extracted
    """
    extractor = EmailEntityExtractor()

    # Combine subject + preview
    full_text = f"{subject or ''}\n\n{preview_text or ''}"

    # Extract entities
    entities = extractor.extract(full_text)

    if not entities:
        return 0

    # Map entity types to DB-compatible types
    type_mapping = {
        'equipment': 'equipment',
        'subcomponent': 'equipment',
        'system': 'equipment',
        'model': 'equipment',
        'marine_brand': 'supplier',
        'part_number': 'part',
        'document_id': 'work_order',
        'fault_code': 'fault',
        'measurement': 'other',
        'location_on_board': 'other',
        'status': 'other',
        'symptom': 'other',
        'action': 'other',
        'marine_protocol': 'other',
        'document_type': 'other',
        'date': 'other',
        'time': 'other',
        'network_id': 'other',
    }

    results_to_insert = []

    for entity_type, values in entities.items():
        mapped_type = type_mapping.get(entity_type, 'other')
        for value in values:
            if value:
                results_to_insert.append({
                    'yacht_id': yacht_id,
                    'message_id': message_id,
                    'entity_type': mapped_type,
                    'entity_value': str(value)[:255],
                    'confidence': 0.8,
                    'found_in': 'body'
                })

    if not results_to_insert:
        return 0

    # Deduplicate
    seen = set()
    unique_results = []
    for r in results_to_insert:
        key = (r['message_id'], r['entity_type'], r['entity_value'].lower())
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    if dry_run:
        logger.info(f"  [DRY RUN] Would insert {len(unique_results)} entities")
        for r in unique_results[:5]:
            logger.info(f"    - {r['entity_type']}: {r['entity_value']}")
        if len(unique_results) > 5:
            logger.info(f"    ... and {len(unique_results) - 5} more")
        return len(unique_results)

    # Insert
    try:
        supabase.table('email_extraction_results').insert(unique_results).execute()
        return len(unique_results)
    except Exception as e:
        logger.error(f"Failed to insert: {e}")
        return 0


def backfill(yacht_id: str, limit: int, dry_run: bool = False):
    """
    Backfill entity extraction for messages.

    Args:
        yacht_id: Target yacht
        limit: Max messages to process
        dry_run: If True, don't write to DB
    """
    supabase = get_supabase_client()

    # Get messages needing extraction
    messages = get_messages_without_extraction(supabase, yacht_id, limit)
    logger.info(f"Found {len(messages)} messages without extraction")

    if not messages:
        return {'processed': 0, 'extracted': 0, 'remaining': 0}

    stats = {
        'processed': 0,
        'extracted': 0,
        'with_entities': 0,
        'remaining': 0
    }

    for msg in messages:
        msg_id = msg['id']
        subject = msg.get('subject', '')
        preview = msg.get('preview_text', '')

        logger.info(f"Processing: {subject[:50]}...")

        entity_count = extract_and_store(
            supabase=supabase,
            yacht_id=yacht_id,
            message_id=msg_id,
            subject=subject,
            preview_text=preview,
            dry_run=dry_run
        )

        stats['processed'] += 1
        stats['extracted'] += entity_count
        if entity_count > 0:
            stats['with_entities'] += 1

    # Check remaining
    remaining = get_messages_without_extraction(supabase, yacht_id, 1)
    stats['remaining'] = len(remaining)

    logger.info(f"Backfill complete: {stats}")
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill entity extraction for emails')
    parser.add_argument('--yacht-id', required=True, help='Yacht UUID')
    parser.add_argument('--limit', type=int, default=100, help='Max messages to process')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')

    args = parser.parse_args()

    logger.info(f"Starting entity extraction backfill for yacht {args.yacht_id}")
    logger.info(f"Limit: {args.limit}, Dry run: {args.dry_run}")

    result = backfill(
        yacht_id=args.yacht_id,
        limit=args.limit,
        dry_run=args.dry_run
    )

    print(f"\nResult: {result}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
