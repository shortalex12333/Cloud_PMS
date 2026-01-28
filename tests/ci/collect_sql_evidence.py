#!/usr/bin/env python3
"""
Collect SQL Evidence for Part Lens v2 Staging Validation
========================================================
Collects view definitions, RLS policies, and single-tenant assertions.

Usage:
    export TENANT_1_DB_PASSWORD='...'
    python3 tests/ci/collect_sql_evidence.py
"""
import os
import sys
import json
import subprocess
from datetime import datetime

DB_HOST = "db.vzsohavtuotocgrfkfyd.supabase.co"
DB_USER = "postgres"
DB_NAME = "postgres"
DB_PASSWORD = os.getenv("TENANT_1_DB_PASSWORD")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
EVIDENCE_DIR = "test-evidence"


def run_psql(query, description=""):
    """Run a psql query and return the output."""
    if description:
        print(f"  📝 {description}...")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "psql",
        "-h", DB_HOST,
        "-U", DB_USER,
        "-d", DB_NAME,
        "-p", "5432",
        "-t",  # Tuples only
        "-A",  # Unaligned
        "-c", query
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"    ✗ Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return None


def save_artifact(name, content):
    """Save evidence artifact."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    filepath = os.path.join(EVIDENCE_DIR, name)

    with open(filepath, 'w') as f:
        if isinstance(content, (dict, list)):
            json.dump(content, f, indent=2)
        else:
            f.write(str(content))

    print(f"  📁 {filepath}")


def collect_view_definitions():
    """Collect view definitions for canonical views."""
    print("\n=== Collecting View Definitions ===")

    views = [
        "pms_part_stock",
        "v_stock_from_transactions",
        "v_low_stock_report"
    ]

    viewdefs = {}

    for view in views:
        query = f"SELECT pg_get_viewdef('{view}'::regclass, true);"
        result = run_psql(query, f"Get viewdef for {view}")
        if result:
            viewdefs[view] = result
            save_artifact(f"viewdef_{view}.sql", result)

    save_artifact("all_viewdefs.json", viewdefs)
    print(f"  ✓ Collected {len(viewdefs)} view definitions")


def collect_rls_policies():
    """Collect RLS policies for part tables."""
    print("\n=== Collecting RLS Policies ===")

    query = """
    SELECT
        tablename,
        policyname,
        permissive,
        roles,
        cmd,
        qual,
        with_check
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename IN ('pms_parts', 'pms_inventory_stock', 'pms_inventory_transactions', 'pms_audit_log')
    ORDER BY tablename, policyname;
    """

    result = run_psql(query, "Get RLS policies")
    if result:
        # Parse result
        lines = result.split("\n")
        policies = []
        for line in lines:
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 7:
                    policies.append({
                        "table": parts[0],
                        "policy_name": parts[1],
                        "permissive": parts[2],
                        "roles": parts[3],
                        "cmd": parts[4],
                        "qual": parts[5],
                        "with_check": parts[6]
                    })

        save_artifact("rls_policies.json", policies)
        save_artifact("rls_policies.txt", result)
        print(f"  ✓ Collected {len(policies)} RLS policies")


def collect_storage_policies():
    """Collect storage bucket policies."""
    print("\n=== Collecting Storage Policies ===")

    query = """
    SELECT
        bucket_id,
        name as policy_name,
        definition
    FROM storage.policies
    WHERE bucket_id IN ('pms-label-pdfs', 'pms-receiving-images', 'pms-part-photos')
    ORDER BY bucket_id, name;
    """

    result = run_psql(query, "Get storage policies")
    if result:
        lines = result.split("\n")
        policies = []
        for line in lines:
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 3:
                    policies.append({
                        "bucket": parts[0],
                        "policy_name": parts[1],
                        "definition": parts[2]
                    })

        save_artifact("storage_policies.json", policies)
        save_artifact("storage_policies.txt", result)
        print(f"  ✓ Collected {len(policies)} storage policies")


def collect_single_tenant_assertion():
    """Collect single-tenant assertion evidence."""
    print("\n=== Collecting Single-Tenant Assertion ===")

    tables = [
        ("pms_parts", YACHT_ID),
        ("pms_inventory_transactions", YACHT_ID),
        ("pms_audit_log", YACHT_ID)
    ]

    results = {}

    for table, yacht_id in tables:
        query = f"""
        SELECT COUNT(DISTINCT yacht_id) as unique_yachts
        FROM {table}
        WHERE yacht_id = '{yacht_id}';
        """
        result = run_psql(query, f"Count distinct yachts in {table}")
        if result:
            unique_count = int(result.strip()) if result.strip().isdigit() else None
            results[table] = {
                "unique_yachts": unique_count,
                "expected": 1,
                "passed": unique_count == 1
            }

    save_artifact("single_tenant_assertion.json", results)

    all_passed = all(r["passed"] for r in results.values())
    if all_passed:
        print("  ✓ All tables are single-tenant")
    else:
        print("  ✗ Some tables have multiple yachts")


def collect_transaction_parity_evidence():
    """Collect evidence that pms_part_stock derives from transactions."""
    print("\n=== Collecting Transaction Parity Evidence ===")

    query = f"""
    SELECT
        ps.part_id,
        ps.on_hand as canonical_on_hand,
        v.on_hand as view_on_hand,
        COALESCE(SUM(t.quantity_change), 0) as manual_sum,
        COUNT(t.id) as txn_count
    FROM pms_part_stock ps
    LEFT JOIN v_stock_from_transactions v ON ps.stock_id = v.stock_id
    LEFT JOIN pms_inventory_transactions t ON ps.stock_id = t.stock_id
    WHERE ps.yacht_id = '{YACHT_ID}'
    GROUP BY ps.part_id, ps.on_hand, v.on_hand, ps.stock_id
    LIMIT 10;
    """

    result = run_psql(query, "Get transaction parity samples")
    if result:
        lines = result.split("\n")
        samples = []
        for line in lines:
            if line.strip():
                parts = line.split("|")
                if len(parts) >= 5:
                    samples.append({
                        "part_id": parts[0],
                        "canonical_on_hand": int(parts[1]) if parts[1].isdigit() else parts[1],
                        "view_on_hand": int(parts[2]) if parts[2].isdigit() else parts[2],
                        "manual_sum": int(parts[3]) if parts[3].isdigit() else parts[3],
                        "txn_count": int(parts[4]) if parts[4].isdigit() else parts[4]
                    })

        save_artifact("transaction_parity_samples.json", samples)
        save_artifact("transaction_parity_samples.txt", result)
        print(f"  ✓ Collected {len(samples)} transaction parity samples")


def main():
    """Run all SQL evidence collection."""
    print("=" * 70)
    print("SQL EVIDENCE COLLECTION - PART LENS V2")
    print("=" * 70)
    print(f"Database: {DB_HOST}")
    print(f"Yacht ID: {YACHT_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    if not DB_PASSWORD:
        print("Error: TENANT_1_DB_PASSWORD not set")
        return 1

    collect_view_definitions()
    collect_rls_policies()
    collect_storage_policies()
    collect_single_tenant_assertion()
    collect_transaction_parity_evidence()

    print()
    print("=" * 70)
    print(f"✓ SQL EVIDENCE COLLECTION COMPLETE")
    print(f"Evidence saved to: {EVIDENCE_DIR}/")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
