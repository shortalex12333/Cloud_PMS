#!/usr/bin/env python3
# security-audit: exempt-ops-tool (schema introspection only, no user data)
"""
Preflight Schema Check: doc_metadata

Purpose:
- Verify doc_metadata table has required columns for Document Lens v2
- Print missing columns and propose ALTER statements
- Can be run against multiple tenants

Usage:
    export TENANT_SUPABASE_URL="https://..."
    export SUPABASE_SERVICE_KEY="..."
    python scripts/preflight/check_doc_metadata_schema.py

    # Check multiple tenants
    python scripts/preflight/check_doc_metadata_schema.py --tenants tenant1,tenant2
"""

import os
import sys
import argparse
import requests
from typing import Dict, List, Optional

# Required columns for Document Lens v2
REQUIRED_COLUMNS = {
    "id": "uuid",
    "yacht_id": "uuid",
    "filename": "text",
    "content_type": "text",
    "storage_path": "text",
    "created_at": "timestamp with time zone",
    # Soft delete columns (added by migration)
    "deleted_at": "timestamp with time zone",
    "deleted_by": "uuid",
    "deleted_reason": "text",
    # Extended columns
    "system_path": "text",
    "tags": "text[]",
}

# Optional columns (nice to have but not blocking)
OPTIONAL_COLUMNS = {
    "doc_type": "text",
    "title": "text",
    "description": "text",
    "oem": "text",
    "equipment_ids": "uuid[]",
}


def check_schema(tenant_url: str, service_key: str) -> Dict:
    """Check doc_metadata schema against required columns."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    # Use PostgREST to get column info via RPC or direct query
    # We'll use a simple approach: try to select each column
    result = {
        "tenant_url": tenant_url,
        "table_exists": False,
        "present_columns": [],
        "missing_required": [],
        "missing_optional": [],
        "alter_statements": [],
    }

    # First check if table exists
    try:
        r = requests.get(
            f"{tenant_url}/rest/v1/doc_metadata?limit=0",
            headers=headers,
            timeout=10
        )
        if r.status_code == 200:
            result["table_exists"] = True
        elif r.status_code == 404 or "does not exist" in r.text:
            result["table_exists"] = False
            return result
        else:
            print(f"  Warning: Unexpected response {r.status_code}: {r.text[:200]}")
            return result
    except Exception as e:
        print(f"  Error checking table: {e}")
        return result

    # Check each column by selecting it
    all_columns = {**REQUIRED_COLUMNS, **OPTIONAL_COLUMNS}
    for col, col_type in all_columns.items():
        try:
            r = requests.get(
                f"{tenant_url}/rest/v1/doc_metadata?select={col}&limit=0",
                headers=headers,
                timeout=10
            )
            if r.status_code == 200:
                result["present_columns"].append(col)
            elif "does not exist" in r.text or r.status_code == 400:
                if col in REQUIRED_COLUMNS:
                    result["missing_required"].append(col)
                    result["alter_statements"].append(
                        f"ALTER TABLE doc_metadata ADD COLUMN IF NOT EXISTS {col} {col_type};"
                    )
                else:
                    result["missing_optional"].append(col)
        except Exception as e:
            print(f"  Error checking column {col}: {e}")

    return result


def print_results(results: List[Dict]):
    """Print results in a readable format."""
    print("\n" + "=" * 70)
    print("DOC_METADATA SCHEMA PREFLIGHT CHECK")
    print("=" * 70)

    for r in results:
        print(f"\n--- {r['tenant_url']} ---")

        if not r["table_exists"]:
            print("  ❌ Table doc_metadata does not exist!")
            print("  → Run baseline migration to create table")
            continue

        print(f"  ✅ Table exists")
        print(f"  Present columns: {len(r['present_columns'])}")

        if r["missing_required"]:
            print(f"  ❌ Missing required columns: {', '.join(r['missing_required'])}")
        else:
            print(f"  ✅ All required columns present")

        if r["missing_optional"]:
            print(f"  ⚠️  Missing optional columns: {', '.join(r['missing_optional'])}")

        if r["alter_statements"]:
            print("\n  Proposed ALTER statements:")
            for stmt in r["alter_statements"]:
                print(f"    {stmt}")

    print("\n" + "=" * 70)

    # Summary
    total = len(results)
    tables_exist = sum(1 for r in results if r["table_exists"])
    fully_compliant = sum(1 for r in results if r["table_exists"] and not r["missing_required"])

    print(f"Summary: {fully_compliant}/{total} tenants fully compliant")
    if fully_compliant < total:
        print("Run the soft delete migration on non-compliant tenants:")
        print("  psql < supabase/migrations/20260128_doc_metadata_soft_delete.sql")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Check doc_metadata schema")
    parser.add_argument(
        "--tenants",
        help="Comma-separated tenant names (uses ENV vars: {name}_SUPABASE_URL, {name}_SUPABASE_SERVICE_KEY)"
    )
    args = parser.parse_args()

    results = []

    if args.tenants:
        # Check multiple tenants
        for tenant in args.tenants.split(","):
            tenant = tenant.strip().upper()
            url = os.getenv(f"{tenant}_SUPABASE_URL")
            key = os.getenv(f"{tenant}_SUPABASE_SERVICE_KEY")
            if url and key:
                print(f"Checking {tenant}...")
                results.append(check_schema(url, key))
            else:
                print(f"Skipping {tenant}: missing URL or key in environment")
    else:
        # Check single tenant from default env vars
        url = os.getenv("TENANT_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            print("Error: TENANT_SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
            sys.exit(1)
        print("Checking default tenant...")
        results.append(check_schema(url, key))

    print_results(results)


if __name__ == "__main__":
    main()
