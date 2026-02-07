#!/usr/bin/env python3
"""
Manual link generation for 101 test emails (v2 - corrected).

Uses correct LinkingLadder API: determine_primary() + create_link_suggestion()
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
from services.linking_ladder import LinkingLadder
from datetime import datetime, timedelta
import asyncio

supabase = get_supabase_client()
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'

print("="*60)
print("MANUAL LINK GENERATION V2")
print("="*60)

# Get threads that need suggestions
cutoff = (datetime.utcnow() - timedelta(hours=12)).isoformat()

threads = supabase.table('email_threads').select(
    'id, latest_subject, yacht_id'
).eq('yacht_id', YACHT_ID).gte(
    'created_at', cutoff
).is_('suggestions_generated_at', 'null').limit(101).execute()

print(f"\nFound {len(threads.data)} threads needing suggestions")

async def process_threads():
    ladder = LinkingLadder(supabase)

    processed = 0
    suggestions_created = 0
    errors = 0

    by_level = {}

    for thread in threads.data:
        thread_id = thread['id']
        yacht_id = thread['yacht_id']
        subject = thread.get('latest_subject', 'No subject')

        try:
            # Run linking ladder
            result = await ladder.determine_primary(
                yacht_id=yacht_id,
                thread_id=thread_id,
                subject=subject,
                from_address='unknown@example.com',  # Not critical for existing tokens
                attachments=None,
                participant_hashes=None,
                context=None
            )

            # Create suggestions if actionable
            if result and result.get('action') in ('auto_link', 'suggest', 'weak_suggest'):
                created = await ladder.create_link_suggestion(
                    yacht_id=yacht_id,
                    thread_id=thread_id,
                    selection=result,
                    max_suggestions=3
                )
                suggestions_created += len(created)

                level = result.get('level', 'unknown')
                by_level[level] = by_level.get(level, 0) + 1

            # Mark as processed
            supabase.table('email_threads').update({
                'suggestions_generated_at': datetime.utcnow().isoformat()
            }).eq('id', thread_id).execute()

            processed += 1

            if processed % 10 == 0:
                print(f"  Processed {processed}/{len(threads.data)}...")

        except Exception as e:
            errors += 1
            print(f"  Error processing '{subject[:40]}': {str(e)[:80]}")

    print(f"\n✓ Link generation complete:")
    print(f"  Processed: {processed}")
    print(f"  Suggestions created: {suggestions_created}")
    print(f"  Errors: {errors}")

    if by_level:
        print(f"\n  Breakdown by level:")
        for level in sorted(by_level.keys()):
            print(f"    {level}: {by_level[level]}")

# Run async processing
asyncio.run(process_threads())

print("\n" + "="*60)
print("Checking email_links table...")

links = supabase.table('email_links').select('*', count='exact').eq(
    'yacht_id', YACHT_ID
).gte('suggested_at', cutoff).execute()

print(f"  email_links created: {links.count}")

if links.data:
    by_confidence = {}
    for link in links.data:
        conf = link.get('confidence', 'unknown')
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

    print(f"\n  Breakdown by confidence:")
    for conf in sorted(by_confidence.keys()):
        print(f"    {conf}: {by_confidence[conf]}")

print("="*60)
