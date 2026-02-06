#!/usr/bin/env python3
"""
Sample Real Data from yTEST_YACHT_001

Queries database for real part numbers, equipment serials, WO numbers
to use in test email generation.

Usage:
    python scripts/autonomy/sample_real_data.py
"""

import os
import sys
import json
from typing import Dict, List, Any

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from integrations.supabase import get_supabase_client


def sample_parts(supabase, yacht_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Sample parts with part numbers."""
    try:
        result = supabase.table('pms_parts').select(
            'id, name, part_number, manufacturer, category'
        ).eq('yacht_id', yacht_id).not_.is_(
            'part_number', 'null'
        ).limit(limit).execute()

        return result.data or []
    except Exception as e:
        print(f"Error sampling parts: {e}")
        return []


def sample_equipment(supabase, yacht_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Sample equipment with serials."""
    try:
        result = supabase.table('equipment').select(
            'id, name, serial_number, model, manufacturer, category'
        ).eq('yacht_id', yacht_id).not_.is_(
            'serial_number', 'null'
        ).limit(limit).execute()

        return result.data or []
    except Exception as e:
        print(f"Error sampling equipment: {e}")
        return []


def sample_work_orders(supabase, yacht_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Sample recent work orders."""
    try:
        result = supabase.table('pms_work_orders').select(
            'id, wo_number, title, status, equipment_id, vendor_contact_hash'
        ).eq('yacht_id', yacht_id).order(
            'created_at', desc=True
        ).limit(limit).execute()

        return result.data or []
    except Exception as e:
        print(f"Error sampling work orders: {e}")
        return []


def sample_vendors(supabase, yacht_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Sample vendors."""
    try:
        result = supabase.table('vendors').select(
            'id, name, email, domain, email_hash, category'
        ).eq('yacht_id', yacht_id).not_.is_(
            'email', 'null'
        ).limit(limit).execute()

        return result.data or []
    except Exception as e:
        print(f"Error sampling vendors: {e}")
        return []


def main():
    # Get yacht ID from env
    yacht_id = os.getenv('TEST_YACHT_ID', '00000000-0000-0000-0000-000000000001')

    # Connect to yTEST_YACHT_001
    os.environ['SUPABASE_URL'] = os.getenv('yTEST_YACHT_001_SUPABASE_URL', '')
    os.environ['SUPABASE_SERVICE_KEY'] = os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY', '')

    supabase = get_supabase_client()

    print("=" * 60)
    print("Sampling Real Data from yTEST_YACHT_001")
    print("=" * 60)

    # Sample data
    parts = sample_parts(supabase, yacht_id, limit=10)
    equipment = sample_equipment(supabase, yacht_id, limit=10)
    work_orders = sample_work_orders(supabase, yacht_id, limit=10)
    vendors = sample_vendors(supabase, yacht_id, limit=10)

    # Build sample set
    sample_data = {
        'yacht_id': yacht_id,
        'parts': parts,
        'equipment': equipment,
        'work_orders': work_orders,
        'vendors': vendors,
        'counts': {
            'parts': len(parts),
            'equipment': len(equipment),
            'work_orders': len(work_orders),
            'vendors': len(vendors),
        }
    }

    # Save to JSON
    output_path = 'test-results/autonomy/sampled_data.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(sample_data, f, indent=2, default=str)

    print(f"\n✓ Sampled {len(parts)} parts, {len(equipment)} equipment, {len(work_orders)} work orders, {len(vendors)} vendors")
    print(f"✓ Saved to {output_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("Sample Summary")
    print("=" * 60)

    if parts:
        print(f"\nParts (first 3):")
        for p in parts[:3]:
            print(f"  - {p['name']} (P/N: {p['part_number']})")

    if equipment:
        print(f"\nEquipment (first 3):")
        for e in equipment[:3]:
            print(f"  - {e['name']} (S/N: {e['serial_number']})")

    if work_orders:
        print(f"\nWork Orders (first 3):")
        for wo in work_orders[:3]:
            print(f"  - WO-{wo['wo_number']}: {wo['title']} ({wo['status']})")

    if vendors:
        print(f"\nVendors (first 3):")
        for v in vendors[:3]:
            print(f"  - {v['name']} ({v['email']})")


if __name__ == '__main__':
    main()
