#!/usr/bin/env python3
"""
Analyze L2.5 validation results from real-data batch.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
from datetime import datetime, timedelta
import json

supabase = get_supabase_client()
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'

cutoff = (datetime.utcnow() - timedelta(hours=2)).isoformat()

# Get threads from last 2 hours (our test batch)
threads = supabase.table('email_threads').select(
    'id, latest_subject, source, extracted_tokens'
).eq('yacht_id', YACHT_ID).gte('created_at', cutoff).eq('source', 'external').execute()

print()
print('='*80)
print('L2.5 VALIDATION REPORT - REAL DATA BATCH')
print('='*80)
print()

print(f'Test Emails Analyzed: {len(threads.data)}')

# Get links
links = supabase.table('email_links').select(
    'thread_id, object_type, object_id, confidence, score, suggested_reason, score_breakdown'
).eq('yacht_id', YACHT_ID).is_('is_primary', 'true').execute()

link_map = {link['thread_id']: link for link in links.data}

# Categorize by scenario
l1_wo = []
l3_parts = []
l3_equipment = []
l25_semantic = []
no_match = []

for thread in threads.data:
    subject = thread['latest_subject']
    tokens = thread.get('extracted_tokens', {})

    has_wo_id = bool(tokens.get('ids', {}).get('wo_id'))
    has_part_num = bool(tokens.get('parts', {}).get('part_number'))
    has_serial = bool(tokens.get('parts', {}).get('serial_number'))

    thread_info = {
        'subject': subject,
        'thread_id': thread['id'],
        'linked': thread['id'] in link_map,
        'link': link_map.get(thread['id'])
    }

    if has_wo_id:
        l1_wo.append(thread_info)
    elif has_part_num:
        l3_parts.append(thread_info)
    elif has_serial:
        l3_equipment.append(thread_info)
    else:
        l25_semantic.append(thread_info)

    if thread['id'] not in link_map:
        no_match.append(thread_info)

print()
print('BREAKDOWN BY SCENARIO:')
print('-'*80)
l1_linked = sum(1 for t in l1_wo if t['linked'])
l3p_linked = sum(1 for t in l3_parts if t['linked'])
l3e_linked = sum(1 for t in l3_equipment if t['linked'])
l25_linked = sum(1 for t in l25_semantic if t['linked'])

l1_pct = 100*l1_linked/len(l1_wo) if l1_wo else 0
l3p_pct = 100*l3p_linked/len(l3_parts) if l3_parts else 0
l3e_pct = 100*l3e_linked/len(l3_equipment) if l3_equipment else 0
l25_pct = 100*l25_linked/len(l25_semantic) if l25_semantic else 0

print(f'L1 (WO explicit):        {len(l1_wo)} emails, {l1_linked} linked ({l1_pct:.1f}%)')
print(f'L3 (Parts):              {len(l3_parts)} emails, {l3p_linked} linked ({l3p_pct:.1f}%)')
print(f'L3 (Equipment):          {len(l3_equipment)} emails, {l3e_linked} linked ({l3e_pct:.1f}%)')
print(f'L2.5 (Semantic):         {len(l25_semantic)} emails, {l25_linked} linked ({l25_pct:.1f}%)')

# Calculate overall coverage
total_test = len(threads.data)
total_linked = len([t for t in threads.data if t['id'] in link_map])
coverage_pct = 100*total_linked/total_test if total_test else 0

print()
print(f'Overall Coverage: {total_linked}/{total_test} = {coverage_pct:.1f}%')

print()
print()
print('CONFIDENCE LEVELS:')
print('-'*80)
conf_counts = {}
for link in links.data:
    conf = link['confidence']
    conf_counts[conf] = conf_counts.get(conf, 0) + 1

for conf in sorted(conf_counts.keys()):
    print(f'{conf:20s}: {conf_counts[conf]}')

print()
print()
print('SCORE DISTRIBUTION:')
print('-'*80)
scores = [link['score'] for link in links.data if link['score']]
if scores:
    print(f'Mean: {sum(scores)/len(scores):.1f}')
    print(f'Min:  {min(scores)}')
    print(f'Max:  {max(scores)}')
    print(f'≥130 (auto-confirm): {sum(1 for s in scores if s >= 130)}')
    print(f'100-129 (strong):    {sum(1 for s in scores if 100 <= s < 130)}')
    print(f'70-99 (weak):        {sum(1 for s in scores if 70 <= s < 100)}')

print()
print()
print(f'UNMATCHED EMAILS ({len(no_match)}):')
print('-'*80)
for t in no_match[:10]:
    subj = t['subject'][:70]
    print(f'  ✗ {subj}')

print()
print('='*80)
print()

# Save detailed results to JSON
output = {
    'summary': {
        'total_test_emails': total_test,
        'total_linked': total_linked,
        'coverage_pct': coverage_pct,
        'l1_precision': l1_pct,
        'l3_parts_accuracy': l3p_pct,
        'l3_equipment_accuracy': l3e_pct,
        'l25_semantic_accuracy': l25_pct
    },
    'confidence_distribution': conf_counts,
    'score_stats': {
        'mean': sum(scores)/len(scores) if scores else 0,
        'min': min(scores) if scores else 0,
        'max': max(scores) if scores else 0,
        'auto_confirm_count': sum(1 for s in scores if s >= 130),
        'strong_count': sum(1 for s in scores if 100 <= s < 130),
        'weak_count': sum(1 for s in scores if 70 <= s < 100)
    },
    'unmatched_count': len(no_match)
}

import json
output_path = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test-results/autonomy/report_real_batch.json'
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f'✓ Saved detailed results to: {output_path}')
print()
