#!/usr/bin/env python3
"""
STRESS TEST: Waves 0-1 (EXACT + ILIKE)
======================================
Deep testing of production-ready operators.
"""
import sys
import time
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.sql_foundation import (
    Operator, probe_single, compile_probes, TABLES, Variant
)

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def execute_rest(table: str, column: str, operator: str, value: str) -> dict:
    """Execute via REST API."""
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }

    select = ",".join(TABLES[table].default_select) if table in TABLES else "id"
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}&yacht_id=eq.{YACHT_ID}"

    if operator == "EXACT":
        url += f"&{column}=eq.{value}"
    elif operator == "ILIKE":
        url += f"&{column}=ilike.{value}"
    elif operator == "IN":
        url += f"&{column}=in.({value})"

    url += "&limit=20"

    try:
        start = time.time()
        resp = requests.get(url, headers=headers, timeout=10)
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            return {"success": True, "count": len(resp.json()), "time_ms": round(elapsed, 1)}
        else:
            return {"success": False, "error": resp.text[:100], "status": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def stress_test():
    """Comprehensive Wave 0-1 stress test."""
    print("=" * 70)
    print("STRESS TEST: Waves 0-1 (EXACT + ILIKE)")
    print("=" * 70)

    # Test cases: (name, table, column, operator, value, expect_min)
    tests = [
        # Wave 0: EXACT - IDs and codes
        ("part_number exact", "pms_parts", "part_number", "EXACT", "ENG-0008-103", 1),
        ("equipment code exact", "pms_equipment", "code", "EXACT", "ME-P-001", 1),
        ("fault code exact", "pms_faults", "fault_code", "EXACT", "E047", 1),
        ("PO number exact", "pms_purchase_orders", "po_number", "EXACT", "PO-2025-001", 1),
        ("symptom code exact", "symptom_aliases", "symptom_code", "EXACT", "VIBRATION", 1),
        ("system type exact", "pms_equipment", "system_type", "EXACT", "propulsion", 2),
        ("status exact", "pms_work_orders", "status", "EXACT", "open", 1),
        ("priority exact", "pms_work_orders", "priority", "EXACT", "high", 1),

        # Wave 1: ILIKE - Pattern matching
        ("part name ilike", "pms_parts", "name", "ILIKE", "%Fuel%", 3),
        ("equipment name ilike", "pms_equipment", "name", "ILIKE", "%Generator%", 2),
        ("fault title ilike", "pms_faults", "title", "ILIKE", "%Engine%", 1),
        ("supplier name ilike", "pms_suppliers", "name", "ILIKE", "%Marine%", 2),
        ("work order title ilike", "pms_work_orders", "title", "ILIKE", "%Service%", 2),
        ("graph node label ilike", "graph_nodes", "label", "ILIKE", "%system%", 5),
        ("symptom alias ilike", "symptom_aliases", "alias", "ILIKE", "%leak%", 2),
        ("location ilike", "pms_equipment", "location", "ILIKE", "%Engine Room%", 5),

        # Edge cases
        ("lowercase part", "pms_parts", "name", "ILIKE", "%fuel%", 3),
        ("uppercase equipment", "pms_equipment", "name", "ILIKE", "%MAIN%", 2),
        ("mixed case fault", "pms_faults", "title", "ILIKE", "%OVerheating%", 1),
        ("partial part number", "pms_parts", "part_number", "ILIKE", "%ENG-%", 10),
        ("single word", "pms_equipment", "name", "ILIKE", "%Port%", 2),

        # Real user queries (simulated)
        ("user: main engine", "pms_equipment", "name", "ILIKE", "%main engine%", 2),
        ("user: fuel filter", "pms_parts", "name", "ILIKE", "%fuel filter%", 1),
        ("user: oil", "pms_parts", "name", "ILIKE", "%oil%", 3),
        ("user: generator 1", "pms_equipment", "name", "ILIKE", "%generator 1%", 1),
        ("user: vibration", "symptom_aliases", "alias", "ILIKE", "%vibration%", 1),
        ("user: leaking", "symptom_aliases", "alias", "ILIKE", "%leak%", 2),

        # Negative tests (should return 0)
        ("nonexistent part", "pms_parts", "part_number", "EXACT", "ZZZZZ-9999", 0),
        ("nonexistent fault", "pms_faults", "fault_code", "EXACT", "X999", 0),
        ("gibberish search", "pms_equipment", "name", "ILIKE", "%xyzzy12345%", 0),
    ]

    passed = 0
    failed = 0
    total_time = 0

    for name, table, column, operator, value, expect_min in tests:
        result = execute_rest(table, column, operator, value)

        if result.get("success"):
            actual = result["count"]
            total_time += result["time_ms"]

            if expect_min == 0:
                ok = actual == 0
            else:
                ok = actual >= expect_min

            status = "✓" if ok else "✗"
            if ok:
                passed += 1
            else:
                failed += 1

            print(f"{status} {name}: {actual} rows ({result['time_ms']}ms) [expected >= {expect_min}]")
        else:
            failed += 1
            print(f"✗ {name}: ERROR - {result.get('error', 'Unknown')}")

        time.sleep(0.2)  # Rate limit

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} passed")
    print(f"Total query time: {round(total_time)}ms")
    print(f"Avg query time: {round(total_time/len(tests), 1)}ms")
    print("=" * 70)

    return passed, failed

def test_variant_execution():
    """Test that variants execute correctly."""
    print("\n" + "=" * 70)
    print("VARIANT EXECUTION TEST")
    print("=" * 70)

    test_values = [
        ("ENG-0008-103", "pms_parts", "part_number"),
        ("Main Engine Port", "pms_equipment", "name"),
        ("E047", "pms_faults", "fault_code"),
    ]

    for raw_value, table, column in test_values:
        print(f"\n--- {raw_value} ---")
        variants = Variant.from_raw(raw_value)

        for v in variants:
            # Determine operator based on variant type
            if v.type.value == "canonical":
                op = "EXACT"
                val = v.value
            elif v.type.value == "fuzzy":
                op = "ILIKE"
                val = v.value
            else:
                op = "ILIKE"
                val = f"%{v.value}%"

            result = execute_rest(table, column, op, val)
            status = "✓" if result.get("success") and result.get("count", 0) > 0 else "○"
            count = result.get("count", 0) if result.get("success") else "ERR"
            print(f"  {status} {v.type.value} ({op}): {count} rows")

            time.sleep(0.2)

def test_compiler_output():
    """Test that compiler produces executable probes."""
    print("\n" + "=" * 70)
    print("COMPILER → EXECUTION TEST")
    print("=" * 70)

    entities = [
        {"type": "PART_NUMBER", "value": "ENG-0008-103"},
        {"type": "EQUIPMENT_NAME", "value": "Generator"},
        {"type": "FAULT_CODE", "value": "E047"},
        {"type": "SUPPLIER_NAME", "value": "Marine"},
        {"type": "SYMPTOM", "value": "vibration"},
    ]

    for entity in entities:
        print(f"\n--- {entity['type']}: {entity['value']} ---")

        probes_by_wave = compile_probes(YACHT_ID, [entity])

        for wave in [0, 1]:  # Only test Waves 0-1
            probes = probes_by_wave.get(wave, [])
            if not probes:
                continue

            print(f"  Wave {wave}:")
            for probe in probes[:3]:  # Test first 3
                clause = probe.where_clauses[0]
                term = probe.params[1] if len(probe.params) > 1 else ""

                result = execute_rest(
                    probe.table,
                    clause.column,
                    clause.operator.value,
                    term
                )

                status = "✓" if result.get("success") and result.get("count", 0) > 0 else "○"
                count = result.get("count", 0) if result.get("success") else "ERR"
                print(f"    {status} {probe.table}.{clause.column} → {count} rows")

                time.sleep(0.2)

if __name__ == "__main__":
    passed, failed = stress_test()
    test_variant_execution()
    test_compiler_output()

    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL WAVE 0-1 TESTS PASSED ✓")
    else:
        print(f"WAVE 0-1: {passed} passed, {failed} failed")
    print("=" * 70)
