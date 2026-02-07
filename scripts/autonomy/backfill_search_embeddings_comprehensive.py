#!/usr/bin/env python3
"""
Comprehensive one-time backfill of missing search_index embeddings.

Creates embedding_jobs for all search_index entries without embeddings,
then monitors embedding_worker progress toward 95% coverage SLO.

Usage:
    python3 scripts/autonomy/backfill_search_embeddings_comprehensive.py \
        --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
        --monitor
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
import argparse
import time
from datetime import datetime

def get_coverage_stats(supabase, yacht_id):
    """Get embedding coverage by object_type."""
    # Query all entries by object_type
    coverage_stats = []

    for obj_type in ['work_order', 'equipment', 'part']:
        total = supabase.table('search_index').select(
            'id', count='exact'
        ).eq('yacht_id', yacht_id).eq('object_type', obj_type).execute()

        embedded = supabase.table('search_index').select(
            'id', count='exact'
        ).eq('yacht_id', yacht_id).eq('object_type', obj_type).not_.is_('embedding', 'null').execute()

        total_count = total.count or 0
        embedded_count = embedded.count or 0
        coverage_pct = (embedded_count * 100.0 / total_count) if total_count > 0 else 0.0

        coverage_stats.append({
            'object_type': obj_type,
            'total': total_count,
            'embedded': embedded_count,
            'coverage_pct': round(coverage_pct, 1)
        })

    return coverage_stats

def get_queue_stats(supabase, yacht_id):
    """Get embedding_jobs queue status."""
    result = supabase.table('embedding_jobs').select(
        'status', count='exact'
    ).eq('yacht_id', yacht_id).execute()

    status_counts = {}
    for row in result.data or []:
        status = row.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    return status_counts, result.count

def backfill_missing_jobs(supabase, yacht_id, dry_run=False):
    """
    Create embedding_jobs for all search_index entries without embeddings.

    Uses idempotent INSERT ON CONFLICT DO NOTHING to prevent duplicates.
    """
    print()
    print('='*80)
    print('COMPREHENSIVE EMBEDDING JOBS BACKFILL')
    print('='*80)
    print()

    # Get current coverage
    print('Current embedding coverage:')
    print('-'*80)
    coverage = get_coverage_stats(supabase, yacht_id)

    if coverage:
        for row in coverage:
            obj_type = row['object_type']
            total = row['total']
            embedded = row['embedded']
            pct = row['coverage_pct']
            status = '✅' if pct >= 95 else '⚠️' if pct >= 80 else '❌'
            print(f'{status} {obj_type:15s}: {embedded:4d}/{total:4d} ({pct:5.1f}%)')
    print()

    # Find entries needing jobs
    print('Finding search_index entries without embeddings...')

    # Get entries without embeddings
    entries = supabase.table('search_index').select(
        'yacht_id, object_type, object_id, org_id'
    ).eq('yacht_id', yacht_id).in_(
        'object_type', ['work_order', 'equipment', 'part']
    ).is_('embedding', 'null').execute()

    missing_entries = entries.data or []
    print(f'Found {len(missing_entries)} entries needing embeddings')
    print()

    if not missing_entries:
        print('✓ All entries already have embeddings or jobs queued')
        return 0

    # Check which already have jobs
    existing_jobs = supabase.table('embedding_jobs').select(
        'object_type, object_id'
    ).eq('yacht_id', yacht_id).execute()

    existing_keys = {
        (job['object_type'], job['object_id'])
        for job in (existing_jobs.data or [])
    }

    # Filter to only entries without jobs
    entries_needing_jobs = [
        entry for entry in missing_entries
        if (entry['object_type'], entry['object_id']) not in existing_keys
    ]

    print(f'Entries needing new jobs: {len(entries_needing_jobs)}')

    if not entries_needing_jobs:
        print('✓ All entries already have embedding_jobs (waiting for worker)')
        return 0

    # Show breakdown
    type_counts = {}
    for entry in entries_needing_jobs:
        obj_type = entry['object_type']
        type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

    print()
    print('Jobs to create by object_type:')
    for obj_type, count in sorted(type_counts.items()):
        print(f'  {obj_type:15s}: {count}')
    print()

    if dry_run:
        print('🔍 DRY RUN - No jobs created')
        return len(entries_needing_jobs)

    # Create jobs in batches
    print('Creating embedding_jobs...')
    batch_size = 100
    created = 0
    failed = 0

    for i in range(0, len(entries_needing_jobs), batch_size):
        batch = entries_needing_jobs[i:i+batch_size]

        jobs = [{
            'yacht_id': entry['yacht_id'],
            'org_id': entry['org_id'],
            'object_type': entry['object_type'],
            'object_id': entry['object_id'],
            'status': 'queued',
            'queued_at': datetime.utcnow().isoformat()
        } for entry in batch]

        try:
            # Use upsert with onConflict to handle any race conditions
            supabase.table('embedding_jobs').upsert(
                jobs,
                on_conflict='yacht_id,object_type,object_id'
            ).execute()
            created += len(batch)
            if created % 500 == 0:
                print(f'  Progress: {created}/{len(entries_needing_jobs)} jobs created...')
        except Exception as e:
            failed += len(batch)
            print(f'  ✗ Batch failed: {e}')

    print()
    print('='*80)
    print('BACKFILL COMPLETE')
    print('='*80)
    print(f'  Created: {created}')
    print(f'  Failed: {failed}')
    print(f'  Total: {len(entries_needing_jobs)}')
    print()

    return created

def monitor_progress(supabase, yacht_id, target_coverage=95, check_interval=30):
    """
    Monitor embedding worker progress until target coverage reached.

    Args:
        supabase: Supabase client
        yacht_id: Yacht ID
        target_coverage: Target coverage percentage (default 95%)
        check_interval: Seconds between checks (default 30)
    """
    print()
    print('='*80)
    print(f'MONITORING EMBEDDING PROGRESS (Target: {target_coverage}%)')
    print('='*80)
    print()
    print('Press Ctrl+C to stop monitoring')
    print()

    start_time = time.time()
    checks = 0

    try:
        while True:
            checks += 1
            elapsed = time.time() - start_time

            # Get coverage
            coverage = get_coverage_stats(supabase, yacht_id)
            queue_stats, queue_total = get_queue_stats(supabase, yacht_id)

            print(f'\n[Check #{checks} @ {elapsed/60:.1f}min]')
            print('-'*80)

            # Coverage by type
            all_met_target = True
            for row in coverage:
                obj_type = row['object_type']
                total = row['total']
                embedded = row['embedded']
                pct = row['coverage_pct']

                if pct < target_coverage:
                    all_met_target = False
                    status = '⏳'
                else:
                    status = '✅'

                print(f'{status} {obj_type:15s}: {embedded:4d}/{total:4d} ({pct:5.1f}%)')

            # Queue status
            print()
            print('Queue status:')
            for status, count in sorted(queue_stats.items()):
                print(f'  {status:15s}: {count}')

            if all_met_target:
                print()
                print('='*80)
                print(f'✓ TARGET REACHED: All object types at ≥{target_coverage}% coverage!')
                print(f'  Total time: {elapsed/60:.1f} minutes')
                print('='*80)
                break

            # Wait for next check
            time.sleep(check_interval)

    except KeyboardInterrupt:
        print()
        print()
        print('Monitoring stopped by user')
        print(f'Total monitoring time: {(time.time() - start_time)/60:.1f} minutes')

def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive backfill of search_index embeddings'
    )
    parser.add_argument('--yacht-id', required=True, help='Yacht ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without creating')
    parser.add_argument('--monitor', action='store_true', help='Monitor progress after backfill')
    parser.add_argument('--target-coverage', type=float, default=95.0, help='Target coverage %% (default: 95)')
    parser.add_argument('--check-interval', type=int, default=30, help='Seconds between checks (default: 30)')

    args = parser.parse_args()

    supabase = get_supabase_client()

    # Backfill missing jobs
    created = backfill_missing_jobs(supabase, args.yacht_id, args.dry_run)

    if created > 0 and not args.dry_run:
        print()
        print('Next steps:')
        print('  1. Start embedding worker:')
        print('     OPENAI_API_KEY="sk-..." python3 apps/api/workers/embedding_worker.py')
        print()
        print('  2. Monitor progress (or use --monitor flag):')
        print(f'     python3 {sys.argv[0]} --yacht-id {args.yacht_id} --monitor')
        print()

        if args.monitor:
            input('Press Enter to start monitoring (or Ctrl+C to exit)...')
            monitor_progress(supabase, args.yacht_id, args.target_coverage, args.check_interval)
    elif args.monitor:
        monitor_progress(supabase, args.yacht_id, args.target_coverage, args.check_interval)

if __name__ == '__main__':
    main()
