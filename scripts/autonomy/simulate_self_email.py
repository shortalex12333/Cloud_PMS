#!/usr/bin/env python3
"""
Schema-safe email simulator for testing.

Uses production email_messages schema (hashes, preview_text, content_hash).
Matches actual email_watcher ingestion structure.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
from services.token_extractor import TokenExtractor
from datetime import datetime
import uuid
import hashlib
import argparse

supabase = get_supabase_client()
token_extractor = TokenExtractor()

def send_email(
    yacht_id: str,
    from_address: str,
    to_address: str,
    subject: str,
    body: str,
    attachments: list = None,
    scenario: str = 'test'
):
    """
    Send a test email using production schema (hashes + preview_text + content_hash).

    Returns:
        thread_id if successful, None otherwise
    """
    # Generate unique IDs
    conv_id = hashlib.sha256(f"sim-{subject}-{datetime.utcnow().isoformat()}".encode()).hexdigest()[:24]
    msg_id = f"sim-{uuid.uuid4()}"
    thread_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    attachments = attachments or []

    # Extract tokens
    tokens = token_extractor.extract_all(
        subject=subject,
        from_address=from_address,
        attachments=attachments
    )

    # Create thread - production schema
    thread_data = {
        'id': thread_id,
        'yacht_id': yacht_id,
        'provider_conversation_id': conv_id,
        'latest_subject': subject,
        'participant_hashes': [
            hashlib.sha256(from_address.lower().encode()).hexdigest(),
            hashlib.sha256(to_address.lower().encode()).hexdigest()
        ],
        'message_count': 1,
        'active_message_count': 1,
        'has_attachments': len(attachments) > 0,
        'last_activity_at': datetime.utcnow().isoformat(),
        'first_message_at': datetime.utcnow().isoformat(),
        'last_inbound_at': datetime.utcnow().isoformat(),
        'source': 'external',  # Valid enum: celeste_originated, external, mixed
        'extracted_tokens': tokens
    }

    try:
        # Insert thread
        thread_result = supabase.table('email_threads').insert(thread_data).execute()

        if not thread_result.data:
            print(f"  ✗ Failed to create thread: {subject[:50]}")
            return None

        # Create message - production schema with hashes
        preview = body[:200] if body else subject
        attachment_names = [att.get('name', 'attachment') for att in attachments]
        content_for_hash = f"{subject}|{body}|{'|'.join(attachment_names)}"

        message_data = {
            'id': message_id,
            'yacht_id': yacht_id,
            'thread_id': thread_id,
            'provider_message_id': msg_id,
            'subject': subject,
            'preview_text': preview,
            'content_hash': hashlib.sha256(content_for_hash.encode()).hexdigest(),
            'from_address_hash': hashlib.sha256(from_address.lower().encode()).hexdigest(),
            'from_display_name': 'Test Simulator',
            'to_addresses_hash': [hashlib.sha256(to_address.lower().encode()).hexdigest()],
            'sent_at': datetime.utcnow().isoformat(),
            'received_at': datetime.utcnow().isoformat(),
            'has_attachments': len(attachments) > 0,
            'attachments': attachments if attachments else None,
            'direction': 'inbound',
            'folder': 'inbox'
        }

        supabase.table('email_messages').insert(message_data).execute()

        return thread_id

    except Exception as e:
        print(f"  ✗ Error: {subject[:40]}: {e}")
        return None


def seed_from_excel(excel_path: str, yacht_id: str, from_address: str, to_address: str):
    """
    Seed emails from Excel file using production-schema simulator.
    """
    import pandas as pd

    df = pd.read_excel(excel_path)

    print(f"\n{'='*80}")
    print(f"SEEDING {len(df)} EMAILS VIA PRODUCTION-SCHEMA SIMULATOR")
    print(f"{'='*80}\n")

    success = 0
    failed = 0

    for idx, row in df.iterrows():
        subject = row['Subject']
        body = row['Body']
        scenario = row.get('Scenario', 'test')

        # Generate attachment based on scenario
        attachments = []
        if 'wo_explicit' in scenario or 'part' in scenario:
            attachments = [{
                'name': 'quote_Q-2026-001.pdf' if 'part' in scenario else 'completion_report.pdf',
                'size': 1024,
                'contentType': 'application/pdf'
            }]

        thread_id = send_email(
            yacht_id=yacht_id,
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
            attachments=attachments,
            scenario=scenario
        )

        if thread_id:
            success += 1
            if success % 10 == 0:
                print(f"  Seeded {success}/{len(df)}...")
        else:
            failed += 1

    print(f"\n{'='*80}")
    print(f"✓ Seeding complete:")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(df)}")
    print(f"{'='*80}\n")

    return success, failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulate self-emails for testing')
    parser.add_argument('--excel', required=True, help='Path to Excel file with test emails')
    parser.add_argument('--yacht-id', required=True, help='Yacht ID')
    parser.add_argument('--from', dest='from_addr', default='simulator@alex-short.com', help='From address')
    parser.add_argument('--to', default='x@alex-short.com', help='To address')

    args = parser.parse_args()

    success, failed = seed_from_excel(
        excel_path=args.excel,
        yacht_id=args.yacht_id,
        from_address=args.from_addr,
        to_address=args.to
    )

    exit_code = 0 if failed == 0 else 1
    sys.exit(exit_code)
