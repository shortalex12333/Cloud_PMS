#!/usr/bin/env python3
"""
Simulate Self Email - Test Data Generator

Generates test emails and inserts directly into email_threads/email_messages
for autonomous linking validation.

Test Scenarios:
- L1: Explicit WO IDs (baseline)
- L2.5: Part numbers, equipment names, warranty claims
- Vendor context

Usage:
    python scripts/autonomy/simulate_self_email.py --count 50
"""

import os
import sys
import json
import uuid
import random
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from integrations.supabase import get_supabase_client


# Test email templates
TEMPLATES = {
    'wo_explicit': [
        "Re: {wo_number} - Status Update",
        "Work Order {wo_number} - Parts Arrived",
        "{wo_number}: Completion Estimate",
        "FW: {wo_number} Vendor Quote",
    ],
    'part_number': [
        "Part {part_number} - Availability Question",
        "Re: Ordering {part_number} for {equipment_name}",
        "Quote Request: {part_number} ({manufacturer})",
        "{part_number} - Installation Manual Needed",
    ],
    'equipment_serial': [
        "Service Request for {equipment_name} (S/N: {serial_number})",
        "{equipment_name} Maintenance - Serial {serial_number}",
        "Re: {equipment_name} ({model}) - Troubleshooting",
        "{manufacturer} {model} - Service History Request",
    ],
    'warranty_claim': [
        "Warranty Claim: {equipment_name} Failure",
        "Re: Warranty Status for {equipment_name}",
        "Claim Documentation for {equipment_name} (S/N: {serial_number})",
        "Warranty Service Request - {manufacturer} {model}",
    ],
    'vendor_generic': [
        "Quote Request for Upcoming Service",
        "Re: Parts Pricing Discussion",
        "Follow-up: Service Proposal",
        "Availability Check",
    ],
}


def load_sampled_data() -> Dict[str, Any]:
    """Load sampled real data from JSON."""
    sample_path = 'test-results/autonomy/sampled_data.json'

    if not os.path.exists(sample_path):
        print(f"⚠ Sampled data not found at {sample_path}. Run sample_real_data.py first.")
        return {
            'yacht_id': '00000000-0000-0000-0000-000000000001',
            'parts': [],
            'equipment': [],
            'work_orders': [],
            'vendors': [],
        }

    with open(sample_path, 'r') as f:
        return json.load(f)


def generate_test_email(
    scenario: str,
    sampled_data: Dict[str, Any],
    from_email: str = 'x@alex-short.com',
    to_email: str = 'x@alex-short.com'
) -> Optional[Dict[str, Any]]:
    """
    Generate a test email for given scenario.

    Args:
        scenario: Test scenario type
        sampled_data: Real data from database
        from_email: Sender email
        to_email: Recipient email

    Returns:
        Email dict with thread and message data, plus ground truth
    """
    yacht_id = sampled_data['yacht_id']
    thread_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    provider_message_id = f"AAMkAGE{uuid.uuid4().hex[:32]}"

    now = datetime.now(timezone.utc)

    # Ground truth for validation
    ground_truth = {
        'scenario': scenario,
        'expected_level': None,
        'expected_object_type': None,
        'expected_object_id': None,
    }

    # Generate based on scenario
    if scenario == 'wo_explicit' and sampled_data.get('work_orders'):
        wo = random.choice(sampled_data['work_orders'])
        template = random.choice(TEMPLATES['wo_explicit'])
        subject = template.format(wo_number=wo['wo_number'])
        body = f"This email discusses work order {wo['wo_number']}. The title is: {wo['title']}."

        ground_truth['expected_level'] = 'L1'
        ground_truth['expected_object_type'] = 'work_order'
        ground_truth['expected_object_id'] = wo['id']

    elif scenario == 'part_number' and sampled_data.get('parts'):
        part = random.choice(sampled_data['parts'])
        template = random.choice(TEMPLATES['part_number'])

        # Randomly pick equipment for context
        equipment_name = ''
        if sampled_data.get('equipment'):
            eq = random.choice(sampled_data['equipment'])
            equipment_name = eq['name']

        subject = template.format(
            part_number=part['part_number'],
            equipment_name=equipment_name,
            manufacturer=part.get('manufacturer', 'OEM')
        )
        body = f"We need part number {part['part_number']} ({part['name']}) for {equipment_name}. Please provide pricing and availability."

        ground_truth['expected_level'] = 'L2.5'
        ground_truth['expected_object_type'] = 'part'
        ground_truth['expected_object_id'] = part['id']

    elif scenario == 'equipment_serial' and sampled_data.get('equipment'):
        eq = random.choice(sampled_data['equipment'])
        template = random.choice(TEMPLATES['equipment_serial'])
        subject = template.format(
            equipment_name=eq['name'],
            serial_number=eq['serial_number'],
            model=eq.get('model', 'N/A'),
            manufacturer=eq.get('manufacturer', 'OEM')
        )
        body = f"Service inquiry for {eq['name']} with serial number {eq['serial_number']}. Model: {eq.get('model', 'N/A')}."

        ground_truth['expected_level'] = 'L2.5'
        ground_truth['expected_object_type'] = 'equipment'
        ground_truth['expected_object_id'] = eq['id']

    elif scenario == 'warranty_claim' and sampled_data.get('equipment'):
        eq = random.choice(sampled_data['equipment'])
        template = random.choice(TEMPLATES['warranty_claim'])
        subject = template.format(
            equipment_name=eq['name'],
            serial_number=eq['serial_number'],
            model=eq.get('model', 'N/A'),
            manufacturer=eq.get('manufacturer', 'OEM')
        )
        body = f"Warranty claim for {eq['name']} (S/N: {eq['serial_number']}). Equipment failure occurred. Please review warranty coverage and next steps."

        ground_truth['expected_level'] = 'L2.5'
        ground_truth['expected_object_type'] = 'equipment'
        ground_truth['expected_object_id'] = eq['id']

    elif scenario == 'vendor_generic' and sampled_data.get('vendors'):
        vendor = random.choice(sampled_data['vendors'])
        template = random.choice(TEMPLATES['vendor_generic'])
        subject = template
        body = f"This is a general inquiry to {vendor['name']}. Looking for service options."

        # Override from_email to vendor
        from_email = vendor['email']

        ground_truth['expected_level'] = 'L4'  # Vendor match
        ground_truth['expected_object_type'] = 'vendor'
        ground_truth['expected_object_id'] = vendor['id']

    else:
        # No valid data for this scenario
        return None

    # Build email data
    email_data = {
        'thread': {
            'id': thread_id,
            'yacht_id': yacht_id,
            'provider_thread_id': f"AAQkAGE{uuid.uuid4().hex[:30]}",
            'latest_subject': subject,
            'latest_from_address': from_email,
            'latest_from_name': 'Test Sender',
            'participant_hashes': [from_email, to_email],
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        },
        'message': {
            'id': message_id,
            'thread_id': thread_id,
            'yacht_id': yacht_id,
            'provider_message_id': provider_message_id,
            'subject': subject,
            'from_address': from_email,
            'from_name': 'Test Sender',
            'to_recipients': [to_email],
            'body_preview': body[:200],
            'body_content': body,
            'sent_at': now.isoformat(),
            'received_at': now.isoformat(),
            'is_read': False,
            'has_attachments': False,
            'importance': 'normal',
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        },
        'ground_truth': ground_truth,
    }

    return email_data


def insert_test_email(supabase, email_data: Dict[str, Any]):
    """Insert test email into database."""
    try:
        # Insert thread
        supabase.table('email_threads').insert(email_data['thread']).execute()

        # Insert message
        supabase.table('email_messages').insert(email_data['message']).execute()

        return True
    except Exception as e:
        print(f"⚠ Error inserting email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate test emails for autonomous testing')
    parser.add_argument('--count', type=int, default=50, help='Number of test emails to generate')
    parser.add_argument('--scenarios', nargs='+', help='Specific scenarios to test')
    args = parser.parse_args()

    # Connect to yTEST_YACHT_001
    os.environ['SUPABASE_URL'] = os.getenv('yTEST_YACHT_001_SUPABASE_URL', '')
    os.environ['SUPABASE_SERVICE_KEY'] = os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY', '')

    supabase = get_supabase_client()

    # Load sampled data
    sampled_data = load_sampled_data()

    print("=" * 60)
    print("Simulating Self Emails")
    print("=" * 60)
    print(f"Target count: {args.count}")
    print(f"Yacht ID: {sampled_data['yacht_id']}")
    print()

    # Determine scenario distribution
    if args.scenarios:
        scenarios = args.scenarios
    else:
        scenarios = ['wo_explicit'] * 10 + ['part_number'] * 15 + ['equipment_serial'] * 15 + ['warranty_claim'] * 5 + ['vendor_generic'] * 5

    # Shuffle for randomness
    random.shuffle(scenarios)

    # Generate and insert emails
    inserted = []
    ground_truths = []

    for i in range(args.count):
        scenario = scenarios[i % len(scenarios)]

        email_data = generate_test_email(scenario, sampled_data)

        if not email_data:
            print(f"⚠ Skipping {scenario} - no data available")
            continue

        success = insert_test_email(supabase, email_data)

        if success:
            inserted.append(email_data)
            ground_truths.append({
                'thread_id': email_data['thread']['id'],
                'subject': email_data['thread']['latest_subject'],
                **email_data['ground_truth']
            })

            print(f"✓ [{i+1}/{args.count}] {scenario}: {email_data['thread']['latest_subject']}")
        else:
            print(f"✗ [{i+1}/{args.count}] {scenario}: Failed to insert")

    # Save ground truth
    ground_truth_path = 'test-results/autonomy/ground_truth.json'
    with open(ground_truth_path, 'w') as f:
        json.dump(ground_truths, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Inserted {len(inserted)} test emails")
    print(f"✓ Ground truth saved to {ground_truth_path}")
    print("=" * 60)

    # Print summary
    scenario_counts = {}
    for gt in ground_truths:
        scenario_counts[gt['scenario']] = scenario_counts.get(gt['scenario'], 0) + 1

    print("\nScenario Distribution:")
    for scenario, count in sorted(scenario_counts.items()):
        print(f"  {scenario}: {count}")


if __name__ == '__main__':
    main()
