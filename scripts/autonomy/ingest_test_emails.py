#!/usr/bin/env python3
"""
Ingest test emails directly into database for L2.5 validation.

Faster than sending via Graph API - directly creates email_threads and email_messages.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
import pandas as pd
from datetime import datetime
import uuid
import hashlib

supabase = get_supabase_client()
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'

print("="*60)
print("INGESTING 60 REAL TEST EMAILS")
print("="*60)
print()

# Load test emails
excel_path = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test-results/autonomy/test_emails_real_60.xlsx'
df = pd.read_excel(excel_path)

print(f"Loaded {len(df)} test emails from Excel")
print()

ingested = 0
skipped = 0

for _, row in df.iterrows():
    subject = row['Subject']
    body = row['Body']
    from_addr = row['From']
    to_addr = row['To']
    scenario = row['Scenario']

    # Create unique conversation ID
    conv_id = hashlib.sha256(f"{subject}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:24]
    msg_id = hashlib.sha256(f"{conv_id}{body}".encode()).hexdigest()[:24]

    # Create email thread
    thread_data = {
        'id': str(uuid.uuid4()),
        'yacht_id': YACHT_ID,
        'provider_conversation_id': conv_id,
        'latest_subject': subject,
        'participants': [from_addr, to_addr],
        'participant_hashes': [
            hashlib.sha256(from_addr.encode()).hexdigest(),
            hashlib.sha256(to_addr.encode()).hexdigest()
        ],
        'message_count': 1,
        'is_read': False,
        'has_attachments': False,
        'last_activity_at': datetime.utcnow().isoformat(),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    try:
        # Insert thread
        thread_result = supabase.table('email_threads').insert(thread_data).execute()

        if not thread_result.data:
            print(f"  ✗ Failed to create thread for: {subject[:50]}")
            skipped += 1
            continue

        thread_id = thread_result.data[0]['id']

        # Create email message
        message_data = {
            'id': str(uuid.uuid4()),
            'yacht_id': YACHT_ID,
            'thread_id': thread_id,
            'provider_message_id': msg_id,
            'subject': subject,
            'body_text': body,
            'from_address': from_addr,
            'from_name': 'Test Sender',
            'to_addresses': [to_addr],
            'sent_at': datetime.utcnow().isoformat(),
            'received_at': datetime.utcnow().isoformat(),
            'is_read': False,
            'has_attachments': False,
            'created_at': datetime.utcnow().isoformat()
        }

        supabase.table('email_messages').insert(message_data).execute()

        ingested += 1

        if ingested % 10 == 0:
            print(f"  Ingested {ingested}/{len(df)}...")

    except Exception as e:
        if 'duplicate' in str(e).lower():
            skipped += 1
        else:
            print(f"  Error ingesting '{subject[:40]}': {str(e)[:60]}")
            skipped += 1

print()
print("="*60)
print(f"✓ Ingestion complete:")
print(f"  Ingested: {ingested}")
print(f"  Skipped: {skipped}")
print(f"  Total: {len(df)}")
print("="*60)
print()
print("Next: Wait for background workers to:")
print("  1. Extract tokens (email_extraction_worker)")
print("  2. Generate link suggestions (link_suggester)")
print("="*60)
