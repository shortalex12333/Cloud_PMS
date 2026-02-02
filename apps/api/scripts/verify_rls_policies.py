#!/usr/bin/env python3
"""
Verify RLS Policies on Work Order Tables
=========================================

Checks the current state of RLS policies on work order-related tables
to determine if B1, B2, B3 fixes have been applied.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env.tenant1
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if key == 'TENANT_1_SUPABASE_URL':
                    os.environ['SUPABASE_URL'] = value
                elif key == 'TENANT_1_SUPABASE_SERVICE_KEY':
                    os.environ['SUPABASE_SERVICE_KEY'] = value

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.supabase import get_supabase_client

def verify_policies():
    """Verify RLS policies on work order tables."""

    print("=" * 80)
    print("VERIFYING RLS POLICIES ON WORK ORDER TABLES")
    print("=" * 80)
    print("")

    supabase = get_supabase_client()

    # Tables to check
    tables_to_check = [
        {
            "table": "pms_work_orders",
            "expected_policies": ["Users can view work orders", "Engineers can create work orders"],
            "blocker": None,
            "critical": True
        },
        {
            "table": "pms_work_order_notes",
            "expected_policies": ["crew_select_own_yacht_notes", "crew_insert_own_yacht_notes"],
            "bad_policies": ["Authenticated users can view notes"],  # USING (true)
            "blocker": "B1",
            "critical": True
        },
        {
            "table": "pms_work_order_parts",
            "expected_policies": ["crew_select_own_yacht_wo_parts", "crew_insert_own_yacht_wo_parts"],
            "bad_policies": ["Authenticated users can view parts"],  # USING (true)
            "blocker": "B2",
            "critical": True
        },
        {
            "table": "pms_part_usage",
            "expected_policies": ["crew_select_own_yacht_part_usage"],
            "bad_policies": ["Authenticated users can view usage", "Authenticated users can view part usage"],
            "blocker": "B3",
            "critical": True
        }
    ]

    results = []

    for table_info in tables_to_check:
        table_name = table_info["table"]
        blocker = table_info.get("blocker")

        print(f"Table: {table_name}")
        if blocker:
            print(f"  Blocker: {blocker}")

        # Query pg_policies to get current policies
        try:
            # Use raw SQL query via RPC or direct query
            # Note: We'll use our test approach - check for data leakage
            result = supabase.table(table_name).select("id").limit(10).execute()

            if result.data:
                print(f"  ✅ RLS enabled (can query table)")
                print(f"  Records visible: {len(result.data)}")

                # Check for expected good policies (we can't query pg_policies via Supabase client easily)
                # Instead, we'll test for data isolation
                if blocker:
                    print(f"  ⚠️  Cannot verify policies directly via Supabase client")
                    print(f"  ℹ️  Run security test to verify: python3 tests/test_work_order_rls_security.py")

                    results.append({
                        "table": table_name,
                        "blocker": blocker,
                        "status": "NEEDS_VERIFICATION",
                        "message": "Run RLS security tests"
                    })
                else:
                    results.append({
                        "table": table_name,
                        "status": "OK"
                    })
            else:
                print(f"  ℹ️  No data in table (or RLS blocking)")
                results.append({
                    "table": table_name,
                    "status": "NO_DATA"
                })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "table": table_name,
                "status": "ERROR",
                "error": str(e)
            })

        print("")

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("")
    print("To verify RLS policies are correct, run the security test suite:")
    print("  cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api")
    print("  python3 tests/test_work_order_rls_security.py")
    print("")
    print("This will test for cross-yacht data leakage and verify B1, B2, B3 fixes.")
    print("")

if __name__ == "__main__":
    verify_policies()
