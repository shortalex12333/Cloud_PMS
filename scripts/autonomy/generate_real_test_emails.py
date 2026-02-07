#!/usr/bin/env python3
"""
Generate test emails using REAL data from yTEST_YACHT_001.

This ensures L1/L2.5 linking can actually match against existing objects.
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
EMAIL_FROM = 'x@alex-short.com'
EMAIL_TO = 'x@alex-short.com'

print("="*60)
print("GENERATING REAL TEST EMAILS FOR L2.5 VALIDATION")
print("="*60)
print()

# Fetch real work orders
print("Fetching work orders...")
wos = supabase.table('pms_work_orders').select(
    'id, wo_number, title, description, status'
).eq('yacht_id', YACHT_ID).order('updated_at', desc=True).limit(30).execute()
print(f"  ✓ Retrieved {len(wos.data)} work orders")

# Fetch real parts
print("Fetching parts...")
parts = supabase.table('pms_parts').select(
    'id, part_number, name, manufacturer'
).eq('yacht_id', YACHT_ID).limit(30).execute()
print(f"  ✓ Retrieved {len(parts.data)} parts")

# Fetch real equipment
print("Fetching equipment...")
equipment = supabase.table('equipment').select(
    'id, name, serial_number, model, manufacturer'
).eq('yacht_id', YACHT_ID).limit(30).execute()
print(f"  ✓ Retrieved {len(equipment.data)} equipment")

# Generate test emails
test_emails = []
index = 1

# L1: Work order explicit IDs (20 emails)
print("\nGenerating L1 (WO explicit) emails...")
for wo in wos.data[:20]:
    wo_num = wo.get('wo_number', 'Unknown')
    title = wo.get('title', 'No title')

    test_emails.append({
        'Index': index,
        'Subject': f"WO-{wo_num}: {title}",
        'Body': f"Update on work order WO-{wo_num}. {wo.get('description', 'Status update required.')}",
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'wo_explicit',
        'Expected_Object_Type': 'work_order',
        'Expected_Object_ID': wo['id'],
        'Expected_WO_Number': wo_num,
        'Attachments_Count': 0
    })
    index += 1

# L2.5: Part number mentions (20 emails)
print("Generating L2.5 (Part) emails...")
for part in parts.data[:20]:
    part_num = part.get('part_number', 'Unknown')
    name = part.get('name', 'Part')

    test_emails.append({
        'Index': index,
        'Subject': f"Part {part_num} - Availability Question",
        'Body': f"Do you have {name} (P/N: {part_num}) in stock? Manufacturer: {part.get('manufacturer', 'Unknown')}",
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'part_number',
        'Expected_Object_Type': 'part',
        'Expected_Object_ID': part['id'],
        'Expected_Part_Number': part_num,
        'Attachments_Count': 0
    })
    index += 1

# L2.5: Equipment serial number (20 emails)
print("Generating L2.5 (Equipment) emails...")
for equip in equipment.data[:20]:
    serial = equip.get('serial_number', 'Unknown')
    name = equip.get('name', 'Equipment')

    test_emails.append({
        'Index': index,
        'Subject': f"Service Request for {name} (S/N: {serial})",
        'Body': f"Equipment {name} with serial number {serial} needs maintenance. Model: {equip.get('model', 'Unknown')}",
        'From': EMAIL_FROM,
        'To': EMAIL_TO,
        'Scenario': 'equipment_serial',
        'Expected_Object_Type': 'equipment',
        'Expected_Object_ID': equip['id'],
        'Expected_Serial_Number': serial,
        'Attachments_Count': 0
    })
    index += 1

# Create DataFrame and save
df = pd.DataFrame(test_emails)
output_path = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test-results/autonomy/test_emails_real_60.xlsx'
df.to_excel(output_path, index=False, sheet_name='Test Emails')

print(f"\n✓ Generated {len(test_emails)} test emails")
print(f"✓ Saved to: {output_path}")
print()
print("Breakdown:")
print(f"  L1 (WO explicit): 20")
print(f"  L2.5 (Parts): 20")
print(f"  L2.5 (Equipment): 20")
print("="*60)
