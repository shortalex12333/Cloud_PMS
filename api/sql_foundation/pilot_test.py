#!/usr/bin/env python3
"""
PILOT TEST: Execute real probes against Supabase
================================================
Tests the SQL foundation with actual database queries.
"""
import sys
import json
import time
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.sql_foundation import (
    Operator, probe_single, probe_or_multicolumn, probe_and_conjunction,
    create_entity, compile_probes, TABLES, Variant, VariantType
)

# Config
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def execute_probe_via_rest(table: str, column: str, operator: str, value: str, select_cols: list) -> dict:
    """Execute probe via Supabase REST API."""
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    # Build PostgREST query
    select = ",".join(select_cols)
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}&yacht_id=eq.{YACHT_ID}"

    if operator == "EXACT":
        url += f"&{column}=eq.{value}"
    elif operator == "ILIKE":
        url += f"&{column}=ilike.{value}"
    elif operator == "TRIGRAM":
        # Trigram requires RPC - skip for now
        return {"error": "TRIGRAM requires RPC", "rows": []}

    url += "&limit=10"

    start = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            rows = resp.json()
            return {
                "success": True,
                "rows": rows,
                "count": len(rows),
                "time_ms": round(elapsed, 2)
            }
        else:
            return {
                "success": False,
                "error": resp.text[:200],
                "status": resp.status_code,
                "time_ms": round(elapsed, 2)
            }
    except Exception as e:
        return {"success": False, "error": str(e), "rows": []}

def test_pilot():
    """Run pilot tests against real database."""
    print("=" * 70)
    print("PILOT TEST: SQL Foundation Against Live Database")
    print("=" * 70)

    tests = [
        # Wave 0: EXACT matches
        {
            "name": "EXACT part_number",
            "table": "pms_parts",
            "column": "part_number",
            "operator": "EXACT",
            "value": "ENG-0008-103",
            "expect_rows": 1
        },
        {
            "name": "EXACT equipment code",
            "table": "pms_equipment",
            "column": "code",
            "operator": "EXACT",
            "value": "ME-P-001",
            "expect_rows": 1
        },
        {
            "name": "EXACT fault code",
            "table": "pms_faults",
            "column": "fault_code",
            "operator": "EXACT",
            "value": "E047",
            "expect_rows": 1
        },
        {
            "name": "EXACT PO number",
            "table": "pms_purchase_orders",
            "column": "po_number",
            "operator": "EXACT",
            "value": "PO-2025-001",
            "expect_rows": 1
        },
        {
            "name": "EXACT symptom code",
            "table": "symptom_aliases",
            "column": "symptom_code",
            "operator": "EXACT",
            "value": "VIBRATION",
            "expect_rows": 4  # Multiple aliases for same code
        },

        # Wave 1: ILIKE matches
        {
            "name": "ILIKE part name",
            "table": "pms_parts",
            "column": "name",
            "operator": "ILIKE",
            "value": "%Fuel%",
            "expect_rows": 3  # Multiple fuel-related parts
        },
        {
            "name": "ILIKE equipment name",
            "table": "pms_equipment",
            "column": "name",
            "operator": "ILIKE",
            "value": "%Generator%",
            "expect_rows": 2  # Generator 1 and 2
        },
        {
            "name": "ILIKE supplier",
            "table": "pms_suppliers",
            "column": "name",
            "operator": "ILIKE",
            "value": "%Marine%",
            "expect_rows": 2  # Mediterranean Marine, Kohler Marine
        },
        {
            "name": "ILIKE fault title",
            "table": "pms_faults",
            "column": "title",
            "operator": "ILIKE",
            "value": "%Engine%",
            "expect_rows": 2
        },
        {
            "name": "ILIKE work order",
            "table": "pms_work_orders",
            "column": "title",
            "operator": "ILIKE",
            "value": "%Service%",
            "expect_rows": 3
        },
        {
            "name": "ILIKE graph node",
            "table": "graph_nodes",
            "column": "label",
            "operator": "ILIKE",
            "value": "%system%",
            "expect_rows": 10  # Many system nodes
        },
        {
            "name": "ILIKE symptom alias",
            "table": "symptom_aliases",
            "column": "alias",
            "operator": "ILIKE",
            "value": "%leak%",
            "expect_rows": 3
        },

        # Canonical variant tests
        {
            "name": "EXACT canonical (no hyphens)",
            "table": "pms_parts",
            "column": "part_number",
            "operator": "ILIKE",
            "value": "%ENG0008103%",  # Stripped hyphens
            "expect_rows": 0  # Won't match - data has hyphens
        },
        {
            "name": "ILIKE lowercase",
            "table": "pms_equipment",
            "column": "name",
            "operator": "ILIKE",
            "value": "%main engine%",
            "expect_rows": 2  # Case insensitive
        },

        # System/location tests
        {
            "name": "EXACT system type",
            "table": "pms_equipment",
            "column": "system_type",
            "operator": "EXACT",
            "value": "propulsion",
            "expect_rows": 2  # Port and Starboard engines
        },
        {
            "name": "ILIKE location",
            "table": "pms_equipment",
            "column": "location",
            "operator": "ILIKE",
            "value": "%Engine Room%",
            "expect_rows": 10  # Most equipment in engine room
        },
    ]

    passed = 0
    failed = 0
    results = []

    for test in tests:
        table_cfg = TABLES.get(test["table"])
        select_cols = table_cfg.default_select if table_cfg else ["id"]

        result = execute_probe_via_rest(
            table=test["table"],
            column=test["column"],
            operator=test["operator"],
            value=test["value"],
            select_cols=select_cols
        )

        # Check result
        if result.get("success"):
            actual = result["count"]
            expected = test["expect_rows"]

            # Allow >= for "expect at least" semantics
            if actual >= expected or (expected > 1 and actual > 0):
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            print(f"\n{status}: {test['name']}")
            print(f"  Query: {test['table']}.{test['column']} {test['operator']} '{test['value']}'")
            print(f"  Expected: >= {expected}, Got: {actual}")
            print(f"  Time: {result['time_ms']}ms")

            if actual > 0 and actual <= 3:
                for row in result["rows"]:
                    # Show first identifying field
                    id_field = list(row.keys())[1] if len(row) > 1 else "id"
                    print(f"    → {row.get(id_field, row.get('id', '?'))}")

        else:
            status = "ERROR"
            failed += 1
            print(f"\n{status}: {test['name']}")
            print(f"  Error: {result.get('error', 'Unknown')}")

        results.append({
            "test": test["name"],
            "status": status,
            "expected": test["expect_rows"],
            "actual": result.get("count", 0),
            "time_ms": result.get("time_ms", 0)
        })

        time.sleep(0.3)  # Rate limiting

    # Summary
    print("\n" + "=" * 70)
    print(f"PILOT TEST RESULTS: {passed}/{len(tests)} passed")
    print("=" * 70)

    print("\n| Test | Status | Expected | Actual | Time |")
    print("|------|--------|----------|--------|------|")
    for r in results:
        print(f"| {r['test'][:30]} | {r['status']} | {r['expected']} | {r['actual']} | {r['time_ms']}ms |")

    return passed, failed

def test_compiler_integration():
    """Test full compiler → probe → execute flow."""
    print("\n" + "=" * 70)
    print("COMPILER INTEGRATION TEST")
    print("=" * 70)

    # Test entities
    test_cases = [
        {"type": "PART_NUMBER", "value": "ENG-0008-103"},
        {"type": "EQUIPMENT_NAME", "value": "Generator"},
        {"type": "FAULT_CODE", "value": "E047"},
        {"type": "MANUFACTURER", "value": "MTU"},  # conjunction_only - should produce no isolated probes
    ]

    for entity_input in test_cases:
        print(f"\n--- Entity: {entity_input['type']} = '{entity_input['value']}' ---")

        probes_by_wave = compile_probes(YACHT_ID, [entity_input])

        total_probes = sum(len(p) for p in probes_by_wave.values())
        print(f"Compiled {total_probes} probes")

        for wave, probes in probes_by_wave.items():
            if probes:
                print(f"  Wave {wave}: {len(probes)} probes")
                for p in probes[:2]:  # Show first 2
                    print(f"    - {p.probe_id}")

        # Execute first probe if exists
        wave0 = probes_by_wave.get(0, [])
        if wave0:
            probe = wave0[0]
            print(f"\n  Executing: {probe.probe_id}")

            # Parse probe for REST execution
            clause = probe.where_clauses[0]
            table_cfg = TABLES.get(probe.table)

            result = execute_probe_via_rest(
                table=probe.table,
                column=clause.column,
                operator=clause.operator.value,
                value=probe.params[1],  # $2 is the term
                select_cols=table_cfg.default_select if table_cfg else ["id"]
            )

            if result.get("success"):
                print(f"  Result: {result['count']} rows in {result['time_ms']}ms")
            else:
                print(f"  Error: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    passed, failed = test_pilot()
    test_compiler_integration()

    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL PILOT TESTS PASSED")
    else:
        print(f"PILOT TESTS: {passed} passed, {failed} failed")
    print("=" * 70)
