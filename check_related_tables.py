#!/usr/bin/env python3
"""
Check if related tables exist and have any data at all.
"""

import requests

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def check_table(table: str):
    """Check if table exists and has data."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.get(url, headers=HEADERS, params={"select": "*", "limit": 5})

    if response.status_code == 200:
        data = response.json()
        return {"exists": True, "count": len(data), "sample": data[:2] if data else []}
    elif response.status_code == 404:
        return {"exists": False, "error": "Table not found"}
    else:
        return {"exists": "unknown", "error": f"{response.status_code}: {response.text[:100]}"}


def main():
    print("=" * 80)
    print("CHECKING WORK ORDER RELATED TABLES")
    print("=" * 80)

    tables = [
        "pms_work_orders",
        "pms_work_order_notes",
        "pms_work_order_parts",
        "pms_work_order_checklist",
        "pms_audit_log",
        "checklist_items",  # Alternative table name
        "work_order_parts",  # Alternative table name
    ]

    for table in tables:
        print(f"\n📋 {table}")
        result = check_table(table)

        if result["exists"] == True:
            print(f"   ✅ EXISTS - {result['count']} rows returned (limit 5)")
            if result["sample"]:
                print(f"   Sample columns: {list(result['sample'][0].keys())[:8]}")
        elif result["exists"] == False:
            print(f"   ❌ NOT FOUND")
        else:
            print(f"   ⚠️  Error: {result['error']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
