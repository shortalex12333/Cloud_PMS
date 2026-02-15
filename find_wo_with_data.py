#!/usr/bin/env python3
"""
Find work orders that have related data (any yacht).
"""

import requests

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def query(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(url, headers=HEADERS, params=params)
    return response.json() if response.status_code == 200 else []


def main():
    print("=" * 80)
    print("FINDING WORK ORDERS WITH RELATED DATA (ALL YACHTS)")
    print("=" * 80)

    # Get work_order_ids from notes
    print("\n[1] Work orders with NOTES:")
    notes = query("pms_work_order_notes", {"select": "work_order_id", "limit": 20})
    note_wo_ids = list(set([n["work_order_id"] for n in notes]))
    print(f"    Found {len(note_wo_ids)} unique work orders with notes")

    # Get work_order_ids from parts
    print("\n[2] Work orders with PARTS:")
    parts = query("pms_work_order_parts", {"select": "work_order_id", "limit": 20})
    parts_wo_ids = list(set([p["work_order_id"] for p in parts]))
    print(f"    Found {len(parts_wo_ids)} unique work orders with parts")

    # Get entity_ids from audit log where entity_type = work_order
    print("\n[3] Work orders with AUDIT HISTORY:")
    audit = query("pms_audit_log", {"select": "entity_id", "entity_type": "eq.work_order", "limit": 20})
    audit_wo_ids = list(set([a["entity_id"] for a in audit]))
    print(f"    Found {len(audit_wo_ids)} unique work orders with audit history")

    # Combine all
    all_wo_ids = list(set(note_wo_ids + parts_wo_ids + audit_wo_ids))
    print(f"\n📊 Total unique work orders with some related data: {len(all_wo_ids)}")

    if all_wo_ids:
        print("\n🎯 WORK ORDERS WITH RELATED DATA:")
        print("-" * 60)

        for wo_id in all_wo_ids[:10]:  # Show first 10
            # Get work order details
            wo_data = query("pms_work_orders", {"select": "*", "id": f"eq.{wo_id}"})
            if wo_data:
                wo = wo_data[0]
                print(f"\n  Title: {wo.get('title', 'Unknown')[:50]}")
                print(f"  ID: {wo_id}")
                print(f"  Yacht ID: {wo.get('yacht_id')}")
                print(f"  Status: {wo.get('status')}")

                # Count related
                has_notes = wo_id in note_wo_ids
                has_parts = wo_id in parts_wo_ids
                has_audit = wo_id in audit_wo_ids
                print(f"  Related: notes={has_notes}, parts={has_parts}, audit={has_audit}")
            else:
                print(f"\n  ⚠️  Work order {wo_id} not found in pms_work_orders")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
