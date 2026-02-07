#!/usr/bin/env python3
"""
Create embedding_jobs for search_index entries that lack embeddings.

This unblocks L2.5 semantic matching by ensuring target objects have
embeddings for vector similarity computation.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
import argparse

def main(yacht_id: str, object_type: str = None, limit: int = 500):
    """
    Create embedding_jobs for search_index entries without embeddings.

    Args:
        yacht_id: Yacht ID to process
        object_type: Optional filter ('work_order', 'part', 'equipment')
        limit: Max jobs to create
    """
    print()
    print('='*80)
    print('CREATE EMBEDDING JOBS FOR search_index')
    print('='*80)
    print()

    supabase = get_supabase_client()

    # Find search_index entries without embeddings
    query = supabase.table('search_index').select(
        'object_type, object_id'
    ).eq('yacht_id', yacht_id).is_('embedding', 'null')

    if object_type:
        query = query.eq('object_type', object_type)

    result = query.limit(limit).execute()

    entries = result.data or []

    print(f'Found {len(entries)} search_index entries needing embeddings')

    if object_type:
        print(f'  Filter: object_type={object_type}')
    print()

    if not entries:
        print('✓ All entries already have embeddings')
        print()
        return

    # Show breakdown by object_type
    type_counts = {}
    for entry in entries:
        obj_type = entry['object_type']
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    print('Breakdown by object_type:')
    for obj_type, count in sorted(type_counts.items()):
        print(f'  {obj_type:15s}: {count}')
    print()

    # Create embedding_jobs
    print(f'Creating {len(entries)} embedding_jobs...')
    print()

    jobs = []
    for entry in entries:
        jobs.append({
            'object_type': entry['object_type'],
            'object_id': entry['object_id'],
            'status': 'queued'
        })

    # Insert in batches of 100
    batch_size = 100
    created = 0
    failed = 0

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i+batch_size]
        try:
            supabase.table('embedding_jobs').insert(batch).execute()
            created += len(batch)
            if created % 100 == 0:
                print(f'  Progress: {created}/{len(jobs)} jobs created...')
        except Exception as e:
            failed += len(batch)
            print(f'  ✗ Batch failed: {e}')

    print()
    print('='*80)
    print('COMPLETE')
    print('='*80)
    print(f'  Created: {created}')
    print(f'  Failed: {failed}')
    print(f'  Total: {len(jobs)}')
    print()

    if created > 0:
        print('Next steps:')
        print('  1. Run embedding worker:')
        print('     OPENAI_API_KEY="sk-..." python3 apps/api/workers/embedding_worker.py')
        print()
        print('  2. Reprocess links:')
        print('     python3 scripts/autonomy/manual_link_generation_v2.py')
        print()
        print('  3. Analyze results:')
        print('     python3 scripts/autonomy/analyze_l25_results.py')
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create embedding jobs for search_index entries'
    )
    parser.add_argument('--yacht-id', required=True, help='Yacht ID')
    parser.add_argument('--object-type', choices=['work_order', 'part', 'equipment'],
                       help='Filter by object_type')
    parser.add_argument('--limit', type=int, default=500,
                       help='Max jobs to create (default: 500)')

    args = parser.parse_args()

    main(args.yacht_id, args.object_type, args.limit)
