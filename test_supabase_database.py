#!/usr/bin/env python3
"""
Supabase Database Pre-Flight Test Script
=========================================

Tests database integrity before frontend testing.
Run this script with network access to Supabase.

Usage:
    python3 test_supabase_database.py

Requirements:
    pip install supabase python-dotenv
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def print_check(check_num, total, name):
    print(f"\n{Colors.BLUE}[CHECK {check_num}/{total}] {name}{Colors.RESET}")
    print("-" * 80)

def print_pass(message):
    print(f"{Colors.GREEN}✅ PASS:{Colors.RESET} {message}")

def print_fail(message):
    print(f"{Colors.RED}❌ FAIL:{Colors.RESET} {message}")

def print_warn(message):
    print(f"{Colors.YELLOW}⚠️  WARN:{Colors.RESET} {message}")

def run_query(client, query, description="Query"):
    """Execute SQL query via RPC"""
    try:
        result = client.rpc('exec_sql', {'query': query}).execute()
        return result.data
    except Exception as e:
        # Fallback: try direct table query if RPC not available
        print_warn(f"RPC not available, using direct queries: {e}")
        return None

def main():
    print_header("SUPABASE DATABASE PRE-FLIGHT CHECKS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Get credentials
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print_fail("Missing Supabase credentials in .env file")
        print("Required variables:")
        print("  - NEXT_PUBLIC_SUPABASE_URL")
        print("  - SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    print(f"Connecting to: {url}")
    print(f"Using service role key: {key[:20]}...\n")

    # Create client
    try:
        client = create_client(url, key)
        print_pass("Connected to Supabase")
    except Exception as e:
        print_fail(f"Failed to connect: {e}")
        sys.exit(1)

    total_checks = 10
    passed = 0
    failed = 0
    warnings = 0

    # =========================================================================
    # CHECK 1: Migration Status - Accountability Columns on pms_parts
    # =========================================================================
    print_check(1, total_checks, "Migration Status - pms_parts columns")

    try:
        result = client.table("pms_parts").select("quantity_on_hand, minimum_quantity, unit, location, last_counted_at, last_counted_by").limit(1).execute()

        # Check if columns exist by examining the response
        if result.data is not None:
            print_pass("pms_parts has new accountability columns")
            passed += 1
        else:
            print_warn("pms_parts table exists but may have no data")
            warnings += 1

    except Exception as e:
        error_msg = str(e)
        if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
            print_fail("Migration 03 not deployed - accountability columns missing")
            failed += 1
        else:
            print_fail(f"Error checking pms_parts: {e}")
            failed += 1

    # =========================================================================
    # CHECK 2: Migration Status - Accountability Columns on pms_work_orders
    # =========================================================================
    print_check(2, total_checks, "Migration Status - pms_work_orders columns")

    try:
        result = client.table("pms_work_orders").select("fault_id, assigned_to, completed_by, completed_at, completion_notes").limit(1).execute()

        if result.data is not None:
            print_pass("pms_work_orders has new accountability columns")
            passed += 1
        else:
            print_warn("pms_work_orders table exists but may have no data")
            warnings += 1

    except Exception as e:
        error_msg = str(e)
        if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
            print_fail("Migration 03 not deployed - accountability columns missing")
            failed += 1
        else:
            print_fail(f"Error checking pms_work_orders: {e}")
            failed += 1

    # =========================================================================
    # CHECK 3: New Trust Tables Exist
    # =========================================================================
    print_check(3, total_checks, "Migration Status - Trust tables")

    trust_tables = {
        "pms_audit_log": False,
        "pms_part_usage": False,
        "pms_work_order_notes": False,
        "pms_handover": False
    }

    for table_name in trust_tables.keys():
        try:
            result = client.table(table_name).select("*").limit(1).execute()
            trust_tables[table_name] = True
            print(f"  ✓ {table_name}")
        except Exception as e:
            print(f"  ✗ {table_name}: {str(e)[:50]}")

    if all(trust_tables.values()):
        print_pass("All 4 trust tables exist")
        passed += 1
    else:
        missing = [t for t, exists in trust_tables.items() if not exists]
        print_fail(f"Missing tables: {', '.join(missing)}")
        print("  → Re-run migration 04")
        failed += 1

    # =========================================================================
    # CHECK 4: Test Data - Yachts
    # =========================================================================
    print_check(4, total_checks, "Test Data - Yachts")

    try:
        # Try yachts table
        result = client.table("yachts").select("id, name").limit(5).execute()
        if result.data and len(result.data) > 0:
            print_pass(f"Found {len(result.data)} yacht(s)")
            for yacht in result.data[:3]:
                print(f"  - {yacht.get('name', 'Unknown')} (ID: {yacht['id'][:8]}...)")
            passed += 1
        else:
            print_warn("No yachts found - create test yacht")
            warnings += 1
    except Exception as e:
        # Try vessels table
        try:
            result = client.table("vessels").select("id, name").limit(5).execute()
            if result.data and len(result.data) > 0:
                print_pass(f"Found {len(result.data)} vessel(s) in 'vessels' table")
                for vessel in result.data[:3]:
                    print(f"  - {vessel.get('name', 'Unknown')} (ID: {vessel['id'][:8]}...)")
                passed += 1
            else:
                print_warn("No vessels found - create test yacht/vessel")
                warnings += 1
        except Exception as e2:
            print_fail(f"Neither yachts nor vessels table accessible: {e2}")
            failed += 1

    # =========================================================================
    # CHECK 5: Test Data - Equipment
    # =========================================================================
    print_check(5, total_checks, "Test Data - Equipment")

    try:
        result = client.table("pms_equipment").select("id, name, equipment_type, location").limit(5).execute()
        if result.data and len(result.data) > 0:
            print_pass(f"Found {len(result.data)} equipment item(s)")
            for eq in result.data[:3]:
                print(f"  - {eq.get('name', 'Unknown')} ({eq.get('equipment_type', 'N/A')}) @ {eq.get('location', 'N/A')}")
            passed += 1
        else:
            print_warn("No equipment found - create test equipment")
            warnings += 1
    except Exception as e:
        print_fail(f"Error accessing equipment: {e}")
        failed += 1

    # =========================================================================
    # CHECK 6: Test Data - Faults
    # =========================================================================
    print_check(6, total_checks, "Test Data - Open Faults")

    try:
        result = client.table("pms_faults").select("id, fault_code, title, severity, status").eq("status", "open").limit(5).execute()
        if result.data and len(result.data) > 0:
            print_pass(f"Found {len(result.data)} open fault(s)")
            for fault in result.data[:3]:
                print(f"  - {fault.get('fault_code', 'N/A')}: {fault.get('title', 'Unknown')[:50]}")
            passed += 1
        else:
            print_warn("No open faults found - create test fault")
            warnings += 1
    except Exception as e:
        print_fail(f"Error accessing faults: {e}")
        failed += 1

    # =========================================================================
    # CHECK 7: Test Data - Parts with Stock
    # =========================================================================
    print_check(7, total_checks, "Test Data - Parts with Stock")

    try:
        result = client.table("pms_parts").select("id, name, part_number, quantity_on_hand, minimum_quantity").gt("quantity_on_hand", 0).limit(5).execute()
        if result.data and len(result.data) > 0:
            print_pass(f"Found {len(result.data)} part(s) with stock")
            for part in result.data[:3]:
                stock = part.get('quantity_on_hand', 0)
                min_qty = part.get('minimum_quantity', 0)
                status = "LOW" if stock <= min_qty else "OK"
                print(f"  - {part.get('name', 'Unknown')} ({part.get('part_number', 'N/A')}): {stock} units ({status})")
            passed += 1
        else:
            print_warn("No parts with stock found - create test parts")
            warnings += 1
    except Exception as e:
        print_fail(f"Error accessing parts: {e}")
        failed += 1

    # =========================================================================
    # CHECK 8: Test Data - Users
    # =========================================================================
    print_check(8, total_checks, "Test Data - Users")

    try:
        result = client.table("user_profiles").select("id, full_name, role, yacht_id").limit(5).execute()
        if result.data and len(result.data) > 0:
            print_pass(f"Found {len(result.data)} user(s)")
            for user in result.data[:3]:
                print(f"  - {user.get('full_name', 'Unknown')} ({user.get('role', 'N/A')})")
            passed += 1
        else:
            print_warn("No user profiles found - create user via Supabase Auth")
            warnings += 1
    except Exception as e:
        print_fail(f"Error accessing users: {e}")
        failed += 1

    # =========================================================================
    # CHECK 9: Data Integrity - No Negative Stock
    # =========================================================================
    print_check(9, total_checks, "Data Integrity - Stock Levels")

    try:
        result = client.table("pms_parts").select("id, name, quantity_on_hand").lt("quantity_on_hand", 0).execute()
        if result.data and len(result.data) > 0:
            print_fail(f"Found {len(result.data)} parts with NEGATIVE stock - data corruption!")
            for part in result.data[:3]:
                print(f"  - {part.get('name', 'Unknown')}: {part.get('quantity_on_hand')} units")
            failed += 1
        else:
            print_pass("No negative stock found")
            passed += 1
    except Exception as e:
        print_warn(f"Could not check stock levels: {e}")
        warnings += 1

    # =========================================================================
    # CHECK 10: Foreign Key Integrity - Orphaned Faults
    # =========================================================================
    print_check(10, total_checks, "Foreign Key Integrity - Faults")

    try:
        # Get all faults
        faults = client.table("pms_faults").select("id, fault_code, equipment_id").limit(100).execute()

        if faults.data and len(faults.data) > 0:
            orphaned = []

            # Check each fault's equipment exists
            for fault in faults.data:
                eq_id = fault.get('equipment_id')
                if eq_id:
                    eq = client.table("pms_equipment").select("id").eq("id", eq_id).execute()
                    if not eq.data or len(eq.data) == 0:
                        orphaned.append(fault.get('fault_code', fault['id'][:8]))

            if len(orphaned) > 0:
                print_warn(f"Found {len(orphaned)} orphaned fault(s) - equipment missing")
                print(f"  Orphaned faults: {', '.join(orphaned[:5])}")
                warnings += 1
            else:
                print_pass("No orphaned faults found")
                passed += 1
        else:
            print_warn("No faults to check")
            warnings += 1

    except Exception as e:
        print_warn(f"Could not check foreign keys: {e}")
        warnings += 1

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_header("TEST SUMMARY")

    total_ran = passed + failed + warnings

    print(f"Total Checks: {total_checks}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"{Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")

    print(f"\n{Colors.BOLD}Result:{Colors.RESET} ", end="")

    if failed == 0 and warnings == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL CHECKS PASSED - READY FOR FRONTEND TESTING{Colors.RESET}")
        print("\nNext steps:")
        print("1. Save test entity IDs (yacht_id, user_id, equipment_id, fault_id, part_id)")
        print("2. Proceed to frontend testing on Vercel")
        return 0
    elif failed == 0:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  PASSED WITH WARNINGS - CAN PROCEED{Colors.RESET}")
        print("\nWarnings are non-critical. You can proceed to frontend testing.")
        print("Consider fixing warnings for better data quality.")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ CRITICAL FAILURES - MUST FIX BEFORE TESTING{Colors.RESET}")
        print("\nFix the failed checks before proceeding to frontend testing.")
        print("See: SUPABASE_PRE_FLIGHT_CHECKS.md for fix instructions")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
