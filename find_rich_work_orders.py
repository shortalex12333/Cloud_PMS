#!/usr/bin/env python3
"""
Find work orders that have related data (notes, parts, checklist, history).
This helps us test with real data instead of empty placeholders.
"""

import requests

# Tenant DB credentials (PMS data)
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

# Test yacht
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def query_table(table: str, params: dict = None):
    """Query Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error querying {table}: {response.status_code} - {response.text[:200]}")
        return []


def main():
    print("=" * 80)
    print("FINDING WORK ORDERS WITH RELATED DATA")
    print("=" * 80)

    # 1. Get all work orders for test yacht
    print("\n[1] Fetching work orders...")
    work_orders = query_table("pms_work_orders", {
        "select": "id,wo_number,title,status,priority,created_at",
        "yacht_id": f"eq.{TEST_YACHT_ID}",
        "order": "created_at.desc",
        "limit": 50,
    })

    print(f"    Found {len(work_orders)} work orders")

    if not work_orders:
        print("    No work orders found!")
        return

    # 2. Check related tables
    print("\n[2] Checking related tables for each work order...\n")

    rich_work_orders = []

    for wo in work_orders:
        wo_id = wo["id"]
        wo_title = wo.get("title", "Untitled")[:50]

        # Check notes
        notes = query_table("pms_work_order_notes", {
            "select": "id",
            "work_order_id": f"eq.{wo_id}",
        })
        notes_count = len(notes)

        # Check parts
        parts = query_table("pms_work_order_parts", {
            "select": "id",
            "work_order_id": f"eq.{wo_id}",
        })
        parts_count = len(parts)

        # Check checklist
        try:
            checklist = query_table("pms_work_order_checklist", {
                "select": "id",
                "work_order_id": f"eq.{wo_id}",
            })
            checklist_count = len(checklist)
        except:
            checklist_count = 0

        # Check audit log
        audit = query_table("pms_audit_log", {
            "select": "id",
            "entity_type": "eq.work_order",
            "entity_id": f"eq.{wo_id}",
        })
        audit_count = len(audit)

        # Calculate richness
        has_data = notes_count > 0 or parts_count > 0 or checklist_count > 0 or audit_count > 0

        if has_data:
            rich_work_orders.append({
                "id": wo_id,
                "title": wo_title,
                "wo_number": wo.get("wo_number"),
                "status": wo.get("status"),
                "notes": notes_count,
                "parts": parts_count,
                "checklist": checklist_count,
                "audit": audit_count,
            })
            print(f"  ✅ {wo_title[:40]}")
            print(f"     ID: {wo_id}")
            print(f"     Notes: {notes_count} | Parts: {parts_count} | Checklist: {checklist_count} | Audit: {audit_count}")
            print()

    # 3. Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal work orders: {len(work_orders)}")
    print(f"Work orders with related data: {len(rich_work_orders)}")

    if rich_work_orders:
        print("\n🎯 RECOMMENDED WORK ORDERS FOR TESTING:")
        print("-" * 60)
        for wo in rich_work_orders[:5]:  # Top 5
            total = wo["notes"] + wo["parts"] + wo["checklist"] + wo["audit"]
            print(f"\n  Title: {wo['title']}")
            print(f"  ID: {wo['id']}")
            print(f"  Status: {wo['status']}")
            print(f"  Related data: {total} items")
            print(f"    - Notes: {wo['notes']}")
            print(f"    - Parts: {wo['parts']}")
            print(f"    - Checklist: {wo['checklist']}")
            print(f"    - Audit history: {wo['audit']}")
    else:
        print("\n⚠️  NO WORK ORDERS HAVE RELATED DATA!")
        print("   All work orders are empty placeholders.")
        print("   Need to seed test data with notes, parts, checklists.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
