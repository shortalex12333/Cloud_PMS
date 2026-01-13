#!/usr/bin/env python3
"""
Execute HOR Migration
=====================
Pushes 001_pms_hours_of_rest.sql to Supabase and verifies.
"""

import os
from supabase import create_client

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "a35cad0b-3e0e-4ee8-95d3-19b7c25e0df9"


def main():
    print("=" * 60)
    print("HOR MIGRATION EXECUTION")
    print("=" * 60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Step 1: Check if table already exists
    print("\n[1] Checking if pms_hours_of_rest exists...")
    try:
        result = client.table("pms_hours_of_rest").select("id").limit(1).execute()
        print(f"    TABLE EXISTS - {len(result.data)} rows found")
        table_exists = True
    except Exception as e:
        if "does not exist" in str(e) or "42P01" in str(e):
            print("    TABLE DOES NOT EXIST - will create")
            table_exists = False
        else:
            print(f"    ERROR: {e}")
            table_exists = False

    # Step 2: Read migration SQL
    print("\n[2] Reading migration SQL...")
    with open("/private/tmp/celesteos/migrations/001_pms_hours_of_rest.sql", "r") as f:
        migration_sql = f.read()
    print(f"    Read {len(migration_sql)} characters")

    # Step 3: Execute via RPC if table doesn't exist
    if not table_exists:
        print("\n[3] Migration needs to be executed via Supabase Dashboard SQL Editor")
        print("    Cannot execute DDL via Python client")
        print("    Copy the SQL from: /private/tmp/celesteos/migrations/001_pms_hours_of_rest.sql")
        return False

    # Step 4: Verify table structure
    print("\n[4] Verifying table structure...")
    try:
        # Insert test row to verify triggers
        test_data = {
            "yacht_id": TEST_YACHT_ID,
            "user_id": TEST_USER_ID,
            "record_date": "2026-01-12",
            "rest_periods": [
                {"start": "22:00", "end": "06:00", "hours": 8.0},
                {"start": "12:00", "end": "14:00", "hours": 2.0}
            ],
            "status": "draft",
            "location": "At Sea"
        }

        # Check if test record exists
        existing = client.table("pms_hours_of_rest").select("id").eq(
            "yacht_id", TEST_YACHT_ID
        ).eq("user_id", TEST_USER_ID).eq("record_date", "2026-01-12").execute()

        if existing.data:
            print(f"    Test record exists, deleting first...")
            client.table("pms_hours_of_rest").delete().eq("id", existing.data[0]["id"]).execute()

        print("    Inserting test record...")
        result = client.table("pms_hours_of_rest").insert(test_data).execute()

        if result.data:
            row = result.data[0]
            print(f"    INSERT SUCCESS")
            print(f"    - ID: {row['id']}")
            print(f"    - total_rest_hours: {row.get('total_rest_hours')} (expected: 10.0)")
            print(f"    - total_work_hours: {row.get('total_work_hours')} (expected: 14.0)")
            print(f"    - is_daily_compliant: {row.get('is_daily_compliant')} (expected: True)")
            print(f"    - is_weekly_compliant: {row.get('is_weekly_compliant')}")
            print(f"    - is_compliant: {row.get('is_compliant')}")

            # Verify trigger fired
            if row.get('total_rest_hours') == 10.0:
                print("\n    ✅ DAILY TRIGGER FIRED CORRECTLY")
            else:
                print("\n    ❌ DAILY TRIGGER DID NOT FIRE")
                return False

            # Clean up
            client.table("pms_hours_of_rest").delete().eq("id", row["id"]).execute()
            print("    Test record cleaned up")

            return True
        else:
            print("    INSERT FAILED - no data returned")
            return False

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def test_compliance_scenarios():
    """Test various compliance scenarios."""
    print("\n" + "=" * 60)
    print("COMPLIANCE SCENARIO TESTS")
    print("=" * 60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    scenarios = [
        {
            "name": "COMPLIANT - 10 hours, 2 periods, one 6+ hrs",
            "rest_periods": [
                {"start": "22:00", "end": "06:00", "hours": 8.0},
                {"start": "12:00", "end": "14:00", "hours": 2.0}
            ],
            "expected_daily": True,
            "expected_total": 10.0
        },
        {
            "name": "NON-COMPLIANT - only 8 hours",
            "rest_periods": [
                {"start": "22:00", "end": "06:00", "hours": 8.0}
            ],
            "expected_daily": False,
            "expected_total": 8.0
        },
        {
            "name": "NON-COMPLIANT - 10 hours but 3 periods",
            "rest_periods": [
                {"start": "22:00", "end": "02:00", "hours": 4.0},
                {"start": "08:00", "end": "11:00", "hours": 3.0},
                {"start": "14:00", "end": "17:00", "hours": 3.0}
            ],
            "expected_daily": False,
            "expected_total": 10.0
        },
        {
            "name": "NON-COMPLIANT - 10 hours, 2 periods, neither 6+",
            "rest_periods": [
                {"start": "22:00", "end": "03:00", "hours": 5.0},
                {"start": "12:00", "end": "17:00", "hours": 5.0}
            ],
            "expected_daily": False,
            "expected_total": 10.0
        }
    ]

    all_passed = True

    for i, scenario in enumerate(scenarios):
        print(f"\n[{i+1}] {scenario['name']}")

        try:
            # Delete any existing test record for this date
            test_date = f"2026-01-{10+i:02d}"
            existing = client.table("pms_hours_of_rest").select("id").eq(
                "yacht_id", TEST_YACHT_ID
            ).eq("user_id", TEST_USER_ID).eq("record_date", test_date).execute()

            if existing.data:
                client.table("pms_hours_of_rest").delete().eq("id", existing.data[0]["id"]).execute()

            # Insert test record
            result = client.table("pms_hours_of_rest").insert({
                "yacht_id": TEST_YACHT_ID,
                "user_id": TEST_USER_ID,
                "record_date": test_date,
                "rest_periods": scenario["rest_periods"],
                "status": "draft"
            }).execute()

            if result.data:
                row = result.data[0]
                total_ok = row.get("total_rest_hours") == scenario["expected_total"]
                daily_ok = row.get("is_daily_compliant") == scenario["expected_daily"]

                status = "✅ PASS" if (total_ok and daily_ok) else "❌ FAIL"
                print(f"    {status}")
                print(f"    - total_rest_hours: {row.get('total_rest_hours')} (expected: {scenario['expected_total']})")
                print(f"    - is_daily_compliant: {row.get('is_daily_compliant')} (expected: {scenario['expected_daily']})")

                if not (total_ok and daily_ok):
                    all_passed = False
                    if row.get("daily_compliance_notes"):
                        print(f"    - notes: {row.get('daily_compliance_notes')}")

                # Clean up
                client.table("pms_hours_of_rest").delete().eq("id", row["id"]).execute()
            else:
                print(f"    ❌ INSERT FAILED")
                all_passed = False

        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    table_ok = main()

    if table_ok:
        scenarios_ok = test_compliance_scenarios()

        print("\n" + "=" * 60)
        print("PHASE A SUMMARY")
        print("=" * 60)
        if scenarios_ok:
            print("✅ ALL TESTS PASSED")
            print("✅ HOR TABLE VERIFIED")
            print("✅ TRIGGERS FIRING CORRECTLY")
        else:
            print("❌ SOME TESTS FAILED")
    else:
        print("\n❌ TABLE VERIFICATION FAILED")
        print("   Migration may need to be applied via Supabase Dashboard")
