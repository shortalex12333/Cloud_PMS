"""
PROVE TABLE INVENTORY
=====================
Discovers ALL tables and validates yacht_id presence.
Outputs hard evidence to docs/DB_TABLE_INVENTORY.json

NO ASSUMPTIONS - queries database directly.
"""

import json
import urllib.request
import urllib.error
import ssl
import os
from datetime import datetime

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_openapi_schema():
    """Fetch OpenAPI schema to discover all tables."""
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())


def fetch_table_columns(table_name):
    """Fetch column info for a table via OpenAPI."""
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            schema = json.loads(resp.read().decode())
            definitions = schema.get("definitions", {})
            if table_name in definitions:
                props = definitions[table_name].get("properties", {})
                return props
    except:
        pass
    return {}


def get_row_count(table_name, has_yacht_id):
    """Get actual row count for a table."""
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=id&limit=1"
    if has_yacht_id:
        url += f"&yacht_id=eq.{TEST_YACHT_ID}"

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Prefer": "count=exact",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            content_range = resp.headers.get("Content-Range", "")
            if "/" in content_range:
                total = content_range.split("/")[1]
                if total != "*":
                    return int(total)
            return 0
    except urllib.error.HTTPError as e:
        # Try without id column
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=*&limit=1"
            if has_yacht_id:
                url += f"&yacht_id=eq.{TEST_YACHT_ID}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx) as resp:
                content_range = resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    total = content_range.split("/")[1]
                    if total != "*":
                        return int(total)
        except:
            pass
        return -1  # Error
    except:
        return -1


def check_yacht_id_column(columns):
    """Check if yacht_id column exists and get its type."""
    if "yacht_id" in columns:
        col_type = columns["yacht_id"].get("type", "unknown")
        col_format = columns["yacht_id"].get("format", "")
        return True, f"{col_type}" + (f"({col_format})" if col_format else "")
    return False, None


def determine_searchable(table_name, columns, row_count):
    """Determine if table is searchable and why not if not."""
    reasons = []

    # Check row count
    if row_count == 0:
        reasons.append("EMPTY (0 rows)")
    elif row_count == -1:
        reasons.append("ERROR getting row count")

    # Check for text columns
    text_cols = [c for c, spec in columns.items()
                 if spec.get("type") == "string" or spec.get("format") == "text"]
    if not text_cols:
        reasons.append("NO_TEXT_COLUMNS")

    # Check for yacht_id
    if "yacht_id" not in columns:
        reasons.append("NO_YACHT_ID (not tenant-scoped)")

    if reasons:
        return False, "; ".join(reasons)
    return True, None


def find_primary_key(columns):
    """Find primary key column."""
    if "id" in columns:
        return "id"
    for col_name, spec in columns.items():
        if spec.get("format") == "uuid" and "id" in col_name.lower():
            return col_name
    return "unknown"


def main():
    print("=" * 70)
    print("TABLE INVENTORY DISCOVERY - HARD EVIDENCE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Test yacht_id: {TEST_YACHT_ID}")
    print()

    # Fetch OpenAPI schema
    print("Fetching OpenAPI schema...")
    schema = fetch_openapi_schema()
    definitions = schema.get("definitions", {})

    print(f"Found {len(definitions)} table definitions in OpenAPI schema")
    print()

    # Process each table
    inventory = []
    tables_with_yacht_id = 0
    tables_searchable = 0
    total_rows = 0

    for table_name in sorted(definitions.keys()):
        props = definitions[table_name].get("properties", {})

        # Check yacht_id
        has_yacht_id, yacht_id_type = check_yacht_id_column(props)
        if has_yacht_id:
            tables_with_yacht_id += 1

        # Get row count
        row_count = get_row_count(table_name, has_yacht_id)
        if row_count > 0:
            total_rows += row_count

        # Find PK
        pk = find_primary_key(props)

        # Determine searchable
        searchable, reason = determine_searchable(table_name, props, row_count)
        if searchable:
            tables_searchable += 1

        entry = {
            "table_name": table_name,
            "has_yacht_id": has_yacht_id,
            "yacht_id_type": yacht_id_type,
            "pk": pk,
            "row_count": row_count,
            "column_count": len(props),
            "searchable": searchable,
            "reason_if_not": reason,
        }
        inventory.append(entry)

        status = "✓" if searchable else "✗"
        yacht_status = "Y" if has_yacht_id else "N"
        print(f"  {status} {table_name}: yacht_id={yacht_status}, rows={row_count}, cols={len(props)}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tables discovered: {len(inventory)}")
    print(f"Tables with yacht_id: {tables_with_yacht_id}")
    print(f"Tables without yacht_id: {len(inventory) - tables_with_yacht_id}")
    print(f"Tables searchable: {tables_searchable}")
    print(f"Total rows (across searchable tables): {total_rows}")

    # Output JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "supabase_url": SUPABASE_URL,
        "test_yacht_id": TEST_YACHT_ID,
        "summary": {
            "total_tables": len(inventory),
            "tables_with_yacht_id": tables_with_yacht_id,
            "tables_without_yacht_id": len(inventory) - tables_with_yacht_id,
            "tables_searchable": tables_searchable,
            "total_rows": total_rows,
        },
        "discovery_method": "OpenAPI schema from /rest/v1/ + row count via Prefer: count=exact header",
        "tables": inventory,
    }

    output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/DB_TABLE_INVENTORY.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Output written to: {output_path}")

    # List tables without yacht_id
    no_yacht = [t for t in inventory if not t["has_yacht_id"]]
    print()
    print(f"Tables WITHOUT yacht_id ({len(no_yacht)}):")
    for t in no_yacht:
        print(f"  - {t['table_name']}")


if __name__ == "__main__":
    main()
