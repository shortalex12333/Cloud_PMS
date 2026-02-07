#!/usr/bin/env python3
"""
Generate real-data test batch for L2.5 validation.

Uses actual WO numbers, part numbers, and serial numbers from yTEST_YACHT_001.
"""

import os
import sys
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

os.environ['SUPABASE_URL'] = 'https://vzsohavtuotocgrfkfyd.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'

from integrations.supabase import get_supabase_client
import pandas as pd
from datetime import datetime

supabase = get_supabase_client()
YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598'
EMAIL_FROM = 'realtest@alex-short.com'
EMAIL_TO = 'x@alex-short.com'

print("="*80)
print("GENERATING REAL-DATA TEST BATCH FOR L2.5 VALIDATION")
print("="*80)
print()

# Fetch real work orders
print("Fetching work orders...")
wos = supabase.table('pms_work_orders').select(
    'id, wo_number, title, description, status'
).eq('yacht_id', YACHT_ID).not_.is_('wo_number', 'null').order('updated_at', desc=True).limit(20).execute()
print(f"  ✓ Retrieved {len(wos.data)} work orders with wo_number")

# Fetch real parts
print("Fetching parts...")
parts = supabase.table('pms_parts').select(
    'id, part_number, name, manufacturer'
).eq('yacht_id', YACHT_ID).not_.is_('part_number', 'null').limit(15).execute()
print(f"  ✓ Retrieved {len(parts.data)} parts with part_number")

# Fetch real equipment
print("Fetching equipment...")
equipment = supabase.table('equipment').select(
    'id, name, serial_number, model, manufacturer'
).eq('yacht_id', YACHT_ID).not_.is_('serial_number', 'null').limit(15).execute()
print(f"  ✓ Retrieved {len(equipment.data)} equipment with serial_number")

# Generate test emails
test_emails = []
index = 1

# L1: Work order explicit IDs (15 emails) - for L1 precision validation
print("\nGenerating L1 (WO explicit) emails...")
for i, wo in enumerate(wos.data[:15]):
    wo_num = wo.get('wo_number', 'Unknown')
    title = wo.get('title', 'No title')

    # Vary the subject line format
    if i % 3 == 0:
        subject = f"WO-{wo_num}: {title}"
    elif i % 3 == 1:
        subject = f"Re: {wo_num} - Status Update"
    else:
        subject = f"Work Order {wo_num} - Question"

    test_emails.append({
        'Index': index,
        'Subject': subject,
        'Body': f"Update on work order {wo_num}. {wo.get('description', 'Status update required.')[:200]}",
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'l1_wo_explicit',
        'Expected_Level': 'L1',
        'Expected_Object_Type': 'work_order',
        'Expected_Object_ID': wo['id'],
        'Expected_WO_Number': wo_num,
        'Attachments_Count': 0
    })
    index += 1

# L2.5: Part number mentions (10 emails) - for L2.5/L3 validation
print("Generating L2.5 (Part) emails...")
for i, part in enumerate(parts.data[:10]):
    part_num = part.get('part_number', 'Unknown')
    name = part.get('name', 'Part')

    # Vary format - some with explicit P/N: prefix, some natural
    if i % 2 == 0:
        subject = f"Part {part_num} - Availability Question"
        body = f"Do you have {name} (P/N: {part_num}) in stock?"
    else:
        subject = f"Question about {name}"
        body = f"I need to order part number {part_num} - {name}. Manufacturer: {part.get('manufacturer', 'Unknown')}"

    test_emails.append({
        'Index': index,
        'Subject': subject,
        'Body': body,
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'l25_part_number',
        'Expected_Level': 'L2.5 or L3',
        'Expected_Object_Type': 'part',
        'Expected_Object_ID': part['id'],
        'Expected_Part_Number': part_num,
        'Attachments_Count': 0
    })
    index += 1

# L2.5: Equipment serial number (10 emails) - for L2.5/L3 validation
print("Generating L2.5 (Equipment) emails...")
for i, equip in enumerate(equipment.data[:10]):
    serial = equip.get('serial_number', 'Unknown')
    name = equip.get('name', 'Equipment')

    # Vary format
    if i % 2 == 0:
        subject = f"Service Request for {name} (S/N: {serial})"
        body = f"Equipment {name} with serial number {serial} needs maintenance."
    else:
        subject = f"Maintenance needed: {name}"
        body = f"Please schedule service for serial {serial}. Model: {equip.get('model', 'Unknown')}"

    test_emails.append({
        'Index': index,
        'Subject': subject,
        'Body': body,
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'l25_equipment_serial',
        'Expected_Level': 'L2.5 or L3',
        'Expected_Object_Type': 'equipment',
        'Expected_Object_ID': equip['id'],
        'Expected_Serial_Number': serial,
        'Attachments_Count': 0
    })
    index += 1

# L2.5: Semantic/contextual (5 emails) - pure L2.5 hybrid search
print("Generating L2.5 (Semantic) emails...")
for i, wo in enumerate(wos.data[15:20]):
    title = wo.get('title', 'No title')
    desc = wo.get('description', '')

    # No explicit IDs - only semantic content
    subject = f"Question about {title.split('-')[0] if '-' in title else title}"
    body = f"I have a question regarding {desc[:150] if desc else title}. Can you help?"

    test_emails.append({
        'Index': index,
        'Subject': subject,
        'Body': body,
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'l25_semantic',
        'Expected_Level': 'L2.5',
        'Expected_Object_Type': 'work_order',
        'Expected_Object_ID': wo['id'],
        'Expected_WO_Number': wo.get('wo_number'),
        'Attachments_Count': 0
    })
    index += 1

# Create DataFrame and save
df = pd.DataFrame(test_emails)
output_path = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test-results/autonomy/test_emails_real_batch.xlsx'
df.to_excel(output_path, index=False, sheet_name='Real Test Emails')

print(f"\n✓ Generated {len(test_emails)} test emails")
print(f"✓ Saved to: {output_path}")
print()
print("Breakdown:")
print(f"  L1 (WO explicit): 15")
print(f"  L2.5/L3 (Parts): 10")
print(f"  L2.5/L3 (Equipment): 10")
print(f"  L2.5 (Semantic): 5")
print(f"  Total: {len(test_emails)}")
print("="*80)
