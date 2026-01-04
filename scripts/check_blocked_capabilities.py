#!/usr/bin/env python3
"""
Blocked Capability Monitor
==========================

Checks if blocked capability tables have been populated.
Run periodically or before releases to identify capabilities ready to unblock.

Usage:
    python scripts/check_blocked_capabilities.py

Output:
    - Row counts for blocked tables
    - Recommendation: UNBLOCK or KEEP_BLOCKED
    - Next steps if ready to unblock
"""

import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.table_capabilities import TABLE_CAPABILITIES, CapabilityStatus

# Supabase config
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Minimum rows required to consider unblocking
MIN_ROWS_TO_UNBLOCK = 10


def check_blocked_capabilities():
    """Check row counts for all blocked capability tables."""
    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: supabase not installed")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("=" * 60)
    print("BLOCKED CAPABILITY STATUS CHECK")
    print("=" * 60)
    print(f"Minimum rows to unblock: {MIN_ROWS_TO_UNBLOCK}")
    print()

    blocked_caps = [
        (name, cap) for name, cap in TABLE_CAPABILITIES.items()
        if cap.status == CapabilityStatus.EMPTY
    ]

    if not blocked_caps:
        print("No blocked capabilities found.")
        return

    ready_to_unblock = []

    for cap_name, cap in blocked_caps:
        print(f"--- {cap_name} ---")
        print(f"Blocked reason: {cap.blocked_reason}")

        for table_spec in cap.tables:
            table_name = table_spec.name
            try:
                result = client.table(table_name).select("id").limit(100).execute()
                row_count = len(result.data)

                if row_count >= MIN_ROWS_TO_UNBLOCK:
                    print(f"  {table_name}: {row_count} rows ✓ READY TO UNBLOCK")
                    ready_to_unblock.append((cap_name, table_name, row_count))
                elif row_count > 0:
                    print(f"  {table_name}: {row_count} rows (need {MIN_ROWS_TO_UNBLOCK}+)")
                else:
                    print(f"  {table_name}: 0 rows - KEEP BLOCKED")

            except Exception as e:
                print(f"  {table_name}: ERROR - {e}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if ready_to_unblock:
        print("\n✓ CAPABILITIES READY TO UNBLOCK:")
        for cap_name, table_name, row_count in ready_to_unblock:
            print(f"  - {cap_name} ({table_name}: {row_count} rows)")

        print("\nTO UNBLOCK:")
        print("1. Run: python scripts/dump_schema.py  # Re-validate schema")
        print("2. Run: python -m api.table_capabilities --validate")
        print("3. Update api/table_capabilities.py:")
        print("   - Change status from CapabilityStatus.EMPTY to CapabilityStatus.ACTIVE")
        print("   - Remove blocked_reason")
        print("4. Add integration tests for the capability")
        print("5. Run: python tests/stress_campaign/capability_test_runner.py")
    else:
        print("\nNo capabilities ready to unblock.")
        print("Tables remain empty - this is expected.")
        print("Capabilities will be unblocked when real data is populated.")


if __name__ == "__main__":
    check_blocked_capabilities()
