#!/usr/bin/env python3
"""
Backfill embeddings for test emails to enable L2.5 semantic matching.

This script generates meta_embedding for emails missing them, which is
required for the vector similarity component of hybrid search.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
from services.email_embedding_service import EmailEmbeddingUpdater
from datetime import datetime, timedelta
import asyncio
import argparse

async def main(yacht_id: str, hours: int, limit: int):
    """
    Backfill embeddings for recent test emails.

    Args:
        yacht_id: Yacht ID to process
        hours: Only process emails from last N hours
        limit: Max emails to process
    """
    print()
    print('='*80)
    print('EMAIL EMBEDDING BACKFILL')
    print('='*80)
    print()

    supabase = get_supabase_client()

    # Find emails needing embeddings (from last N hours)
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    result = supabase.table('email_messages').select(
        'id, subject, from_display_name, attachments, thread_id, created_at'
    ).eq('yacht_id', yacht_id).gte('created_at', cutoff).is_(
        'meta_embedding', 'null'
    ).limit(limit).execute()

    emails = result.data or []

    print(f'Found {len(emails)} emails needing embeddings (last {hours} hours)')

    if not emails:
        print('✓ All recent emails already have embeddings')
        print()
        return

    # Show sample
    print()
    print('Sample emails to process:')
    for email in emails[:5]:
        subject = email.get('subject', 'No subject')[:60]
        print(f'  - {subject}')
    if len(emails) > 5:
        print(f'  ... and {len(emails) - 5} more')
    print()

    # Create updater and backfill
    updater = EmailEmbeddingUpdater(supabase, yacht_id)

    print('Generating embeddings (this may take 1-2 minutes)...')
    print()

    stats = {'processed': 0, 'success': 0, 'failed': 0}

    for i, email in enumerate(emails, 1):
        email_id = email['id']
        subject = email.get('subject', '')
        sender_name = email.get('from_display_name', '')
        attachments = email.get('attachments') or []

        if isinstance(attachments, str):
            import json
            try:
                attachments = json.loads(attachments)
            except:
                attachments = []

        try:
            success = await updater.update_email_embeddings(
                email_id=email_id,
                subject=subject,
                sender_name=sender_name,
                attachments=attachments,
            )

            stats['processed'] += 1
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

            if i % 10 == 0:
                print(f'  Progress: {i}/{len(emails)} emails processed...')

        except Exception as e:
            stats['processed'] += 1
            stats['failed'] += 1
            print(f'  ✗ Failed: {email_id[:8]}: {e}')

    print()
    print('='*80)
    print('BACKFILL COMPLETE')
    print('='*80)
    print(f'  Processed: {stats["processed"]}')
    print(f'  Success:   {stats["success"]}')
    print(f'  Failed:    {stats["failed"]}')
    print()

    if stats['success'] > 0:
        print('✓ Embeddings generated successfully')
        print()
        print('Next steps:')
        print('  1. Reprocess links: python3 scripts/autonomy/manual_link_generation_v2.py')
        print('  2. Analyze results: python3 scripts/autonomy/analyze_l25_results.py')
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backfill email embeddings for L2.5')
    parser.add_argument('--yacht-id', required=True, help='Yacht ID')
    parser.add_argument('--hours', type=int, default=24, help='Process emails from last N hours')
    parser.add_argument('--limit', type=int, default=100, help='Max emails to process')

    args = parser.parse_args()

    asyncio.run(main(args.yacht_id, args.hours, args.limit))
