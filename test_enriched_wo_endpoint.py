#!/usr/bin/env python3
"""
Test the enriched /v1/entity/work_order/{id} endpoint.
Verifies it returns notes, parts, checklist, and audit history.
"""

import requests
import json

# Use a work order we know has related data
# From our earlier search: "CI Test WO 1769563473" has notes + audit
TEST_WORK_ORDER_ID = "1543b482-dfe4-431a-85b6-46659edffa1f"

# Alternative: "Hydraulic System Oil Change" has parts
ALT_WORK_ORDER_ID = "10000001-0001-4001-8001-000000000009"

# API endpoint (local or staging)
API_URL = "https://pipeline-core.int.celeste7.ai"

# We need an auth token - let's get one by logging in
SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
TEST_EMAIL = "x@alex-short.com"
TEST_PASSWORD = "Password2!"


def get_auth_token():
    """Get auth token by logging in."""
    print("[1] Getting auth token...")

    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw",
            "Content-Type": "application/json",
        },
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        }
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print(f"    ✅ Got token: {token[:20]}...")
        return token
    else:
        print(f"    ❌ Login failed: {response.status_code}")
        print(f"    {response.text[:200]}")
        return None


def test_work_order_endpoint(token: str, wo_id: str):
    """Test the enriched work order endpoint."""
    print(f"\n[2] Testing /v1/entity/work_order/{wo_id[:8]}...")

    response = requests.get(
        f"{API_URL}/v1/entity/work_order/{wo_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"    ✅ Success!")
        print(f"\n    Work Order: {data.get('title')}")
        print(f"    Status: {data.get('status')}")
        print(f"    Priority: {data.get('priority')}")

        # Check for enriched data
        print(f"\n    === ENRICHED DATA ===")

        notes = data.get('notes', [])
        print(f"    Notes: {len(notes)} items")
        if notes:
            for note in notes[:2]:
                print(f"      - {note.get('note_text', '')[:50]}...")

        parts = data.get('parts', [])
        print(f"    Parts: {len(parts)} items")
        if parts:
            for part in parts[:2]:
                part_info = part.get('pms_parts', {})
                print(f"      - {part_info.get('name', 'Unknown')} (qty: {part.get('quantity')})")

        checklist = data.get('checklist', [])
        print(f"    Checklist: {len(checklist)} items")
        if checklist:
            for item in checklist[:2]:
                status = "✓" if item.get('is_completed') else "○"
                print(f"      {status} {item.get('title', '')[:40]}")

        audit = data.get('audit_history', [])
        print(f"    Audit History: {len(audit)} entries")
        if audit:
            for entry in audit[:2]:
                print(f"      - {entry.get('action')} at {entry.get('created_at')}")

        # Summary
        print(f"\n    === COUNTS ===")
        print(f"    notes_count: {data.get('notes_count', 0)}")
        print(f"    parts_count: {data.get('parts_count', 0)}")
        print(f"    checklist_count: {data.get('checklist_count', 0)}")
        print(f"    checklist_completed: {data.get('checklist_completed', 0)}")

        return data
    else:
        print(f"    ❌ Failed: {response.status_code}")
        print(f"    {response.text[:300]}")
        return None


def main():
    print("=" * 70)
    print("TESTING ENRICHED WORK ORDER ENDPOINT")
    print("=" * 70)

    token = get_auth_token()
    if not token:
        print("\n❌ Cannot proceed without auth token")
        return

    # Test with work order that has notes + audit
    print("\n" + "-" * 70)
    print("Test 1: Work order with NOTES + AUDIT")
    print("-" * 70)
    test_work_order_endpoint(token, TEST_WORK_ORDER_ID)

    # Test with work order that has parts
    print("\n" + "-" * 70)
    print("Test 2: Work order with PARTS")
    print("-" * 70)
    test_work_order_endpoint(token, ALT_WORK_ORDER_ID)

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
