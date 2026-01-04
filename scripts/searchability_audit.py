"""
SEARCHABILITY AUDIT
===================
For EVERY table/column, classify WHY it's not searchable.

Categories:
A) EMPTY BY DATA - would work if data existed
B) NON-SEARCHABLE BY DESIGN - would create junk
C) BLOCKED BY SECURITY/RLS - access denied
D) UNSUPPORTED DATATYPE - need special operator
E) WRONG VALUES BEING PASSED (BUG) - data exists but search returns 0
F) MISSING INDEX / PERFORMANCE BLOCK - too slow

CATEGORY E IS THE CRITICAL ONE - these are bugs.
"""

import json
import urllib.request
import urllib.error
import ssl
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def api_request(endpoint: str, params: str = "") -> Tuple[Optional[Any], Optional[str], int]:
    """Make API request and return (data, error, row_count)."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += f"?{params}"

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Prefer": "count=exact",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            content_range = resp.headers.get("Content-Range", "")
            total = 0
            if "/" in content_range:
                total_str = content_range.split("/")[1]
                if total_str != "*":
                    total = int(total_str)
            return data, None, total
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}", 0
    except Exception as e:
        return None, str(e), 0


def get_sample_values(table: str, column: str, has_yacht_id: bool) -> List[str]:
    """Get actual sample values from a column."""
    params = f"select={column}&limit=5"
    if has_yacht_id:
        params += f"&yacht_id=eq.{TEST_YACHT_ID}"

    data, error, _ = api_request(table, params)
    if error or not data:
        return []

    values = []
    for row in data:
        val = row.get(column)
        if val and isinstance(val, str) and len(val) > 2:
            values.append(val)
    return values[:3]


def test_manual_search(table: str, column: str, value: str, has_yacht_id: bool) -> Tuple[int, str]:
    """Test manual ILIKE search and return row count."""
    # URL encode the value
    import urllib.parse
    encoded_value = urllib.parse.quote(f"*{value}*")

    params = f"select=*&{column}=ilike.{encoded_value}&limit=10"
    if has_yacht_id:
        params += f"&yacht_id=eq.{TEST_YACHT_ID}"

    data, error, total = api_request(table, params)
    if error:
        return -1, f"QUERY_ERROR: {error}"

    return len(data) if data else 0, f"ilike.{encoded_value}"


def test_pipeline_search(table: str, column: str, value: str) -> Tuple[int, str]:
    """Test search via pipeline (SearchPlanner)."""
    try:
        from supabase import create_client
        from api.search_planner import SearchPlanner, ENTITY_SOURCE_MAP

        client = create_client(SUPABASE_URL, SERVICE_KEY)
        planner = SearchPlanner(client, TEST_YACHT_ID)

        # Find entity type that routes to this table/column
        entity_type = None
        for etype, sources in ENTITY_SOURCE_MAP.items():
            for src in sources:
                if src.table == table and src.column == column:
                    entity_type = etype
                    break
            if entity_type:
                break

        if not entity_type:
            return -2, "NO_ENTITY_TYPE_ROUTES_HERE"

        entities = [{"type": entity_type, "value": value}]
        plan = planner.create_plan(entities)
        result = planner.execute_plan(plan)

        # Count rows from this specific table
        table_rows = 0
        for sr in result.results:
            if sr.source.table == table:
                table_rows += sr.row_count

        return table_rows, f"entity_type={entity_type}"

    except Exception as e:
        return -1, f"PIPELINE_ERROR: {e}"


def classify_column(
    table: str,
    column: str,
    datatype: str,
    row_count: int,
    has_yacht_id: bool,
    sample_values: List[str],
) -> Dict:
    """Classify a column's searchability status."""

    result = {
        "table": table,
        "column": column,
        "datatype": datatype,
        "row_count": row_count,
        "has_yacht_id": has_yacht_id,
        "sample_values": sample_values,
        "searchable_expected": True,
        "actual_status": None,
        "evidence": {},
    }

    # Category A: EMPTY BY DATA
    if row_count == 0:
        result["actual_status"] = "A"
        result["searchable_expected"] = True
        result["evidence"] = {
            "reason": "Table has 0 rows",
            "query": f"SELECT count(*) FROM {table} WHERE yacht_id='{TEST_YACHT_ID}'",
            "would_work": True,
        }
        return result

    # Category B: NON-SEARCHABLE BY DESIGN
    non_searchable_columns = {
        "id": "Primary key - use EXACT lookup only",
        "yacht_id": "Tenant filter - never searched directly",
        "created_at": "Timestamp - use date range filter",
        "updated_at": "Timestamp - use date range filter",
        "metadata": "JSONB blob - too unstructured for text search",
        "properties": "JSONB blob - too unstructured for text search",
        "embedding": "Vector - requires similarity search operator",
        "search_embedding": "Vector - requires similarity search operator",
    }

    if column in non_searchable_columns:
        result["actual_status"] = "B"
        result["searchable_expected"] = False
        result["evidence"] = {
            "reason": non_searchable_columns[column],
            "design_decision": True,
        }
        return result

    # Category D: UNSUPPORTED DATATYPE
    unsupported_types = {
        "vector": "Requires pgvector <=> operator",
        "jsonb": "Requires @> or ->> operators",
        "json": "Requires ->> operator",
        "bytea": "Binary data not searchable",
    }

    dtype_lower = datatype.lower()
    for utype, reason in unsupported_types.items():
        if utype in dtype_lower:
            result["actual_status"] = "D"
            result["searchable_expected"] = False
            result["evidence"] = {
                "datatype": datatype,
                "reason": reason,
                "required_operator": reason.split("Requires ")[1] if "Requires" in reason else "unknown",
            }
            return result

    # If no sample values, column might be all NULL
    if not sample_values:
        result["actual_status"] = "A"
        result["searchable_expected"] = True
        result["evidence"] = {
            "reason": "Column has no non-null text values",
            "query": f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT 1",
            "note": "Table has rows but this column is empty",
        }
        return result

    # Now test actual search: compare manual vs pipeline
    test_value = sample_values[0][:20]  # Use first 20 chars of first sample

    manual_count, manual_query = test_manual_search(table, column, test_value, has_yacht_id)
    pipeline_count, pipeline_info = test_pipeline_search(table, column, test_value)

    result["evidence"]["test_value"] = test_value
    result["evidence"]["manual_search"] = {"count": manual_count, "query": manual_query}
    result["evidence"]["pipeline_search"] = {"count": pipeline_count, "info": pipeline_info}

    # Category C: BLOCKED BY SECURITY/RLS
    if manual_count == -1 and "403" in str(manual_query):
        result["actual_status"] = "C"
        result["searchable_expected"] = False
        result["evidence"]["reason"] = "RLS policy blocks access"
        return result

    # Category E: WRONG VALUES BEING PASSED (BUG!)
    # Manual search returns rows but pipeline doesn't
    if manual_count > 0 and pipeline_count == 0:
        result["actual_status"] = "E"
        result["searchable_expected"] = True
        result["evidence"]["reason"] = "BUG: Manual search works but pipeline returns 0"
        result["evidence"]["is_bug"] = True
        return result

    # Pipeline doesn't route to this column at all
    if pipeline_count == -2:
        result["actual_status"] = "E"
        result["searchable_expected"] = True
        result["evidence"]["reason"] = "BUG: No entity type routes to this column"
        result["evidence"]["is_bug"] = True
        result["evidence"]["fix"] = f"Add routing for {table}.{column} in ENTITY_SOURCE_MAP"
        return result

    # Both work - column is searchable
    if manual_count > 0 and pipeline_count > 0:
        result["actual_status"] = "OK"
        result["searchable_expected"] = True
        result["evidence"]["reason"] = "Searchable and working"
        return result

    # Both return 0 - data doesn't match test value (edge case)
    if manual_count == 0 and pipeline_count == 0:
        result["actual_status"] = "A"
        result["searchable_expected"] = True
        result["evidence"]["reason"] = "No matches for test value (data exists but not this pattern)"
        return result

    # Unknown case
    result["actual_status"] = "UNKNOWN"
    result["evidence"]["reason"] = "Could not determine status"
    return result


def main():
    print("=" * 70)
    print("SEARCHABILITY AUDIT")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Test yacht_id: {TEST_YACHT_ID}")
    print()

    # Load table inventory
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/DB_TABLE_INVENTORY.json") as f:
        inventory = json.load(f)

    # Load search surface map
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/SEARCH_SURFACE_MAP.json") as f:
        surface_map = json.load(f)

    # Build table -> columns map
    table_columns = {}
    for col in surface_map["columns"]:
        t = col["table"]
        if t not in table_columns:
            table_columns[t] = []
        table_columns[t].append(col)

    # Build table -> row_count map
    table_rows = {t["table_name"]: t["row_count"] for t in inventory["tables"]}
    table_yacht = {t["table_name"]: t["has_yacht_id"] for t in inventory["tables"]}

    audit_results = []
    status_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "OK": 0, "UNKNOWN": 0}
    category_e_bugs = []

    # Process tables with data first (these are where bugs matter)
    tables_with_data = [t for t in inventory["tables"] if t["row_count"] > 0]

    print(f"Auditing {len(tables_with_data)} tables with data...")
    print()

    for table_info in tables_with_data:
        table = table_info["table_name"]
        row_count = table_info["row_count"]
        has_yacht_id = table_info["has_yacht_id"]

        if table not in table_columns:
            print(f"  SKIP: {table} - no column info in surface map")
            continue

        print(f"  Auditing {table} ({row_count} rows)...")

        # Get text columns only
        text_columns = [
            c for c in table_columns[table]
            if "ILIKE" in c.get("match_modes", []) or "TRIGRAM" in c.get("match_modes", [])
        ]

        for col_info in text_columns:
            column = col_info["column"]
            datatype = col_info["datatype"]

            # Get sample values
            sample_values = get_sample_values(table, column, has_yacht_id)

            # Classify
            result = classify_column(
                table, column, datatype, row_count, has_yacht_id, sample_values
            )
            audit_results.append(result)

            status = result["actual_status"]
            status_counts[status] = status_counts.get(status, 0) + 1

            if status == "E":
                category_e_bugs.append(result)
                print(f"    !! BUG: {column} - {result['evidence'].get('reason', '')}")
            elif status == "OK":
                print(f"    ✓ {column}")
            else:
                print(f"    [{status}] {column}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = sum(status_counts.values())
    print(f"\nTotal columns audited: {total}")
    print()
    print("Status breakdown:")
    print(f"  A) EMPTY BY DATA:           {status_counts['A']:3d} ({100*status_counts['A']/total:.1f}%)")
    print(f"  B) NON-SEARCHABLE BY DESIGN:{status_counts['B']:3d} ({100*status_counts['B']/total:.1f}%)")
    print(f"  C) BLOCKED BY SECURITY:     {status_counts['C']:3d} ({100*status_counts['C']/total:.1f}%)")
    print(f"  D) UNSUPPORTED DATATYPE:    {status_counts['D']:3d} ({100*status_counts['D']/total:.1f}%)")
    print(f"  E) WRONG VALUES (BUG):      {status_counts['E']:3d} ({100*status_counts['E']/total:.1f}%)")
    print(f"  F) PERFORMANCE BLOCK:       {status_counts['F']:3d} ({100*status_counts['F']/total:.1f}%)")
    print(f"  OK) WORKING:                {status_counts['OK']:3d} ({100*status_counts['OK']/total:.1f}%)")
    print(f"  UNKNOWN:                    {status_counts.get('UNKNOWN', 0):3d}")

    print()
    print("=" * 70)
    print("CATEGORY E BUGS (CORRECTNESS ISSUES)")
    print("=" * 70)

    if category_e_bugs:
        print(f"\n{len(category_e_bugs)} columns have BUGS where data exists but search fails:\n")
        for bug in category_e_bugs:
            print(f"  Table: {bug['table']}")
            print(f"  Column: {bug['column']}")
            print(f"  Sample values: {bug['sample_values'][:2]}")
            print(f"  Manual search: {bug['evidence'].get('manual_search', {})}")
            print(f"  Pipeline search: {bug['evidence'].get('pipeline_search', {})}")
            print(f"  Fix: {bug['evidence'].get('fix', 'Add routing in ENTITY_SOURCE_MAP')}")
            print()
    else:
        print("\nNo Category E bugs found.")

    # Output JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "test_yacht_id": TEST_YACHT_ID,
        "summary": {
            "total_columns_audited": total,
            "status_counts": status_counts,
            "category_e_bug_count": len(category_e_bugs),
            "percentages": {
                "empty_by_data": round(100 * status_counts["A"] / total, 1) if total > 0 else 0,
                "non_searchable_by_design": round(100 * status_counts["B"] / total, 1) if total > 0 else 0,
                "blocked_by_security": round(100 * status_counts["C"] / total, 1) if total > 0 else 0,
                "unsupported_datatype": round(100 * status_counts["D"] / total, 1) if total > 0 else 0,
                "wrong_values_bug": round(100 * status_counts["E"] / total, 1) if total > 0 else 0,
                "working": round(100 * status_counts["OK"] / total, 1) if total > 0 else 0,
            },
        },
        "category_e_bugs": category_e_bugs,
        "audit_results": audit_results,
    }

    output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/SEARCHABILITY_AUDIT.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput written to: {output_path}")

    # Return exit code based on bugs
    if category_e_bugs:
        print(f"\n⚠️  {len(category_e_bugs)} CORRECTNESS BUGS FOUND")
        return 1
    else:
        print("\n✓ No correctness bugs found")
        return 0


if __name__ == "__main__":
    sys.exit(main())
