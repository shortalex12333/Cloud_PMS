#!/usr/bin/env python3
"""
Schema Introspection Script
Dumps production Supabase schema to JSON for validation.

Usage:
    python scripts/dump_schema.py

Output:
    docs/schema_snapshot.json
"""

import json
import os
import sys
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase not installed. Run: pip install supabase")
    sys.exit(1)

# Production Supabase credentials
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Tables we care about for PMS search
TARGET_TABLES = [
    # Core PMS
    "pms_parts",
    "pms_inventory_stock",
    "pms_equipment",
    "pms_work_orders",
    "pms_faults",
    "pms_suppliers",
    "pms_notes",
    "pms_handover_notes",
    "pms_vessel_certificates",
    "pms_crew_certificates",
    "pms_purchase_orders",
    "pms_purchase_order_items",

    # Search/Graph
    "search_fault_code_catalog",
    "search_symptom_catalog",
    "search_graph_nodes",
    "search_graph_edges",

    # Documents
    "doc_yacht_library",
    "doc_metadata",
    "doc_sop_procedures",
    "search_ocred_pages",
    "search_document_chunks",

    # Inventory locations
    "inventory",
    "locations",
]

# SQL to get table schema
SCHEMA_SQL = """
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    c.is_nullable,
    c.column_default,
    c.character_maximum_length,
    c.numeric_precision,
    c.ordinal_position
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name = ANY($1)
ORDER BY c.table_name, c.ordinal_position;
"""

# SQL to get indexes
INDEX_SQL = """
SELECT
    t.relname AS table_name,
    i.relname AS index_name,
    a.attname AS column_name,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE t.relkind = 'r'
  AND t.relname = ANY($1)
ORDER BY t.relname, i.relname, a.attnum;
"""

# SQL to check RLS status
RLS_SQL = """
SELECT
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = ANY($1);
"""

# SQL to get foreign keys
FK_SQL = """
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = ANY($1);
"""


def main():
    print("=" * 60)
    print("SUPABASE SCHEMA DUMP")
    print("=" * 60)
    print(f"URL: {SUPABASE_URL}")
    print(f"Target tables: {len(TARGET_TABLES)}")
    print()

    # Connect to Supabase
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    schema = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "supabase_url": SUPABASE_URL,
            "target_tables": TARGET_TABLES,
        },
        "tables": {},
        "missing_tables": [],
        "indexes": {},
        "foreign_keys": {},
        "rls_status": {},
    }

    # Get columns
    print("Fetching column information...")
    try:
        result = client.rpc('get_schema_columns', {'table_names': TARGET_TABLES}).execute()
        columns_data = result.data
    except Exception as e:
        # Fallback: query information_schema directly via postgres
        print(f"RPC failed ({e}), trying direct query...")
        # Use raw SQL via postgrest
        columns_data = []
        for table in TARGET_TABLES:
            try:
                # Try to select 0 rows to get column info
                r = client.table(table).select("*").limit(0).execute()
                # This doesn't give us types, so we'll infer from a real row
                r2 = client.table(table).select("*").limit(1).execute()
                if r2.data:
                    row = r2.data[0]
                    for col_name, col_val in row.items():
                        col_type = type(col_val).__name__ if col_val is not None else "unknown"
                        columns_data.append({
                            "table_name": table,
                            "column_name": col_name,
                            "data_type": col_type,
                            "is_nullable": "YES",
                        })
                else:
                    # Table exists but empty, just get column names
                    pass
            except Exception as table_err:
                print(f"  Table {table}: {table_err}")
                schema["missing_tables"].append(table)

    # Organize by table
    print("Processing columns...")
    for col in columns_data:
        table = col.get("table_name")
        if table not in schema["tables"]:
            schema["tables"][table] = {
                "columns": {},
                "has_yacht_id": False,
                "yacht_id_column": None,
                "primary_key": None,
            }

        col_name = col.get("column_name")
        schema["tables"][table]["columns"][col_name] = {
            "type": col.get("data_type") or col.get("udt_name", "unknown"),
            "nullable": col.get("is_nullable") == "YES",
            "default": col.get("column_default"),
            "max_length": col.get("character_maximum_length"),
        }

        # Check for yacht_id
        if col_name in ["yacht_id", "vessel_id"]:
            schema["tables"][table]["has_yacht_id"] = True
            schema["tables"][table]["yacht_id_column"] = col_name

        # Check for primary key (usually 'id')
        if col_name == "id":
            schema["tables"][table]["primary_key"] = "id"

    # Summary
    print()
    print("=" * 60)
    print("SCHEMA SUMMARY")
    print("=" * 60)

    found_tables = list(schema["tables"].keys())
    print(f"Tables found: {len(found_tables)}")
    print(f"Tables missing: {len(schema['missing_tables'])}")

    if schema["missing_tables"]:
        print(f"  Missing: {schema['missing_tables']}")

    print()
    print("Per-table summary:")
    for table, info in sorted(schema["tables"].items()):
        col_count = len(info["columns"])
        yacht = "✓" if info["has_yacht_id"] else "✗"
        print(f"  {table}: {col_count} columns, yacht_id={yacht}")

    # Write output
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "schema_snapshot.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2, default=str)

    print()
    print(f"Schema written to: {output_path}")
    print()

    return schema


if __name__ == "__main__":
    main()
