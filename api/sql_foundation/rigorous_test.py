#!/usr/bin/env python3
"""
RIGOROUS SQL FOUNDATION TEST
============================
Honest, thorough testing. Find all gaps before production.
"""
import sys
import json
import time
import requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.sql_foundation import (
    Operator, probe_single, probe_or_multicolumn, probe_and_conjunction,
    create_entity, compile_probes, TABLES, Variant, VariantType,
    get_columns_for_entity
)

SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

ISSUES = []
PASSES = []

def log_issue(category, description, details=None):
    """Log an issue found during testing."""
    ISSUES.append({"category": category, "description": description, "details": details})
    print(f"  ❌ ISSUE: {description}")

def log_pass(test_name):
    """Log a passing test."""
    PASSES.append(test_name)
    print(f"  ✓ {test_name}")

def query_rest(table, filters, select_cols):
    """Execute query via REST API."""
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }

    select = ",".join(select_cols)
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}&yacht_id=eq.{YACHT_ID}"

    for col, op, val in filters:
        if op == "eq":
            url += f"&{col}=eq.{val}"
        elif op == "ilike":
            url += f"&{col}=ilike.{val}"
        elif op == "in":
            url += f"&{col}=in.({val})"

    url += "&limit=20"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "rows": resp.json()}
        else:
            return {"success": False, "error": resp.text[:300], "status": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}

def query_rpc(function_name, params):
    """Execute RPC function."""
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"

    try:
        resp = requests.post(url, json=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            return {"success": True, "data": resp.json()}
        else:
            return {"success": False, "error": resp.text[:300], "status": resp.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# TEST 1: OPERATOR COVERAGE
# =============================================================================
def test_operator_coverage():
    """Test which operators actually work via REST/RPC."""
    print("\n" + "=" * 70)
    print("TEST 1: OPERATOR COVERAGE")
    print("=" * 70)

    # EXACT
    print("\n[EXACT operator]")
    result = query_rest("pms_parts", [("part_number", "eq", "ENG-0008-103")], ["id", "part_number"])
    if result["success"] and len(result["rows"]) == 1:
        log_pass("EXACT via REST eq filter")
    else:
        log_issue("OPERATOR", "EXACT failed", result)

    # ILIKE
    print("\n[ILIKE operator]")
    result = query_rest("pms_parts", [("name", "ilike", "%Fuel%")], ["id", "name"])
    if result["success"] and len(result["rows"]) > 0:
        log_pass(f"ILIKE via REST ilike filter ({len(result['rows'])} rows)")
    else:
        log_issue("OPERATOR", "ILIKE failed", result)

    # IN operator
    print("\n[IN operator]")
    result = query_rest("pms_equipment", [("system_type", "in", "propulsion,electrical")], ["id", "name", "system_type"])
    if result["success"] and len(result["rows"]) > 0:
        log_pass(f"IN via REST in filter ({len(result['rows'])} rows)")
    else:
        log_issue("OPERATOR", "IN failed", result)

    # TRIGRAM - requires pg_trgm extension
    print("\n[TRIGRAM operator]")
    # Check if similarity function exists
    result = query_rpc("test_trigram", {"search_term": "genrator"})  # Intentional typo
    if result["success"]:
        log_pass("TRIGRAM via RPC")
    else:
        log_issue("OPERATOR", "TRIGRAM not available - need RPC function", result.get("error"))

    # ARRAY operators
    print("\n[ARRAY operators]")
    # Check if array columns exist and work
    result = query_rest("search_fault_code_catalog", [], ["id", "code", "symptoms"])
    if result["success"]:
        if result["rows"] and result["rows"][0].get("symptoms"):
            log_pass("ARRAY column exists (symptoms)")
            # Now test array contains
            # PostgREST uses cs. for contains
        else:
            log_issue("OPERATOR", "ARRAY column empty or missing", result)
    else:
        log_issue("OPERATOR", "ARRAY query failed", result)

    # JSONB operators
    print("\n[JSONB operators]")
    result = query_rest("graph_nodes", [], ["id", "label", "properties"])
    if result["success"]:
        if result["rows"] and any(r.get("properties") for r in result["rows"]):
            log_pass("JSONB column exists (properties)")
        else:
            log_issue("DATA", "JSONB column empty in graph_nodes.properties")
    else:
        log_issue("OPERATOR", "JSONB query failed", result)


# =============================================================================
# TEST 2: CONJUNCTION ENFORCEMENT
# =============================================================================
def test_conjunction_enforcement():
    """Test that conjunction_only columns are properly blocked when isolated."""
    print("\n" + "=" * 70)
    print("TEST 2: CONJUNCTION ENFORCEMENT")
    print("=" * 70)

    # These should produce NO isolated probes
    conjunction_only_entities = [
        ("MANUFACTURER", "MTU"),
        ("DESCRIPTION", "fuel injector"),
        ("CONTACT", "Carlos"),
    ]

    for entity_type, value in conjunction_only_entities:
        print(f"\n[{entity_type} = '{value}']")

        probes = compile_probes(YACHT_ID, [{"type": entity_type, "value": value}])
        total = sum(len(p) for p in probes.values())

        # Check what columns this maps to
        columns = get_columns_for_entity(entity_type)
        isolated_cols = [(t, c) for t, c, ops, iso, conj in columns if iso and not conj]
        conj_only_cols = [(t, c) for t, c, ops, iso, conj in columns if conj]

        print(f"  Columns found: {len(columns)}")
        print(f"  Isolated OK: {isolated_cols}")
        print(f"  Conjunction only: {conj_only_cols}")
        print(f"  Probes compiled: {total}")

        if total == 0 and len(conj_only_cols) > 0 and len(isolated_cols) == 0:
            log_pass(f"{entity_type} correctly blocked (conjunction_only)")
        elif total > 0 and len(isolated_cols) > 0:
            log_pass(f"{entity_type} allowed via isolated column")
        else:
            log_issue("CONJUNCTION", f"{entity_type} enforcement unclear",
                     {"probes": total, "isolated": isolated_cols, "conj": conj_only_cols})


# =============================================================================
# TEST 3: VARIANT GENERATION & MATCHING
# =============================================================================
def test_variant_matching():
    """Test that variants are generated correctly and match data."""
    print("\n" + "=" * 70)
    print("TEST 3: VARIANT GENERATION & MATCHING")
    print("=" * 70)

    test_values = [
        ("ENG-0008-103", "part_number"),  # With hyphens
        ("Main Engine Port", "equipment name"),
        ("E047", "fault code"),
        ("PO-2025-001", "PO number"),
    ]

    for raw, description in test_values:
        print(f"\n[{description}: '{raw}']")
        variants = Variant.from_raw(raw)

        print("  Variants generated:")
        for v in variants:
            print(f"    {v.type.value} (p{v.priority}): '{v.value}'")

        # Check if canonical matches database format
        # This is a key issue - our canonical strips hyphens but DB has hyphens
        canonical = next((v for v in variants if v.type == VariantType.CANONICAL), None)
        if canonical:
            # Test if canonical would actually match
            if "-" in raw and "-" not in canonical.value:
                log_issue("VARIANT", f"Canonical strips hyphens but DB has hyphens: {raw} → {canonical.value}",
                         "EXACT match will fail, need ILIKE fallback")
            else:
                log_pass(f"Canonical format OK for {description}")


# =============================================================================
# TEST 4: CROSS-TABLE ENTITY ROUTING
# =============================================================================
def test_entity_routing():
    """Test that entities route to correct tables."""
    print("\n" + "=" * 70)
    print("TEST 4: ENTITY ROUTING")
    print("=" * 70)

    expected_routing = {
        "PART_NUMBER": ["pms_parts"],
        "EQUIPMENT_NAME": ["pms_equipment", "graph_nodes"],
        "EQUIPMENT_CODE": ["pms_equipment"],
        "FAULT_CODE": ["pms_faults", "search_fault_code_catalog"],
        "SERIAL_NUMBER": ["pms_equipment"],
        "MANUFACTURER": ["pms_equipment", "pms_parts", "pms_suppliers"],
        "SUPPLIER_NAME": ["pms_suppliers"],
        "PO_NUMBER": ["pms_purchase_orders"],
        "SYMPTOM": ["pms_faults", "symptom_aliases", "search_fault_code_catalog"],
        "LOCATION": ["pms_equipment", "pms_parts"],
        "SYSTEM_NAME": ["pms_equipment", "pms_parts", "graph_nodes"],
        "STATUS": ["pms_work_orders", "pms_purchase_orders"],
        "PRIORITY": ["pms_work_orders", "pms_equipment"],
        "HOURS": ["pms_work_orders"],
    }

    for entity_type, expected_tables in expected_routing.items():
        print(f"\n[{entity_type}]")
        columns = get_columns_for_entity(entity_type)
        actual_tables = list(set(t for t, c, ops, iso, conj in columns))

        missing = set(expected_tables) - set(actual_tables)
        extra = set(actual_tables) - set(expected_tables)

        if missing:
            log_issue("ROUTING", f"{entity_type} missing tables: {missing}")
        if extra:
            print(f"  Note: Extra tables found: {extra}")
        if not missing:
            log_pass(f"{entity_type} → {actual_tables}")


# =============================================================================
# TEST 5: DATA EXISTENCE
# =============================================================================
def test_data_existence():
    """Verify data exists in all configured tables."""
    print("\n" + "=" * 70)
    print("TEST 5: DATA EXISTENCE")
    print("=" * 70)

    for table_name, table_cfg in TABLES.items():
        print(f"\n[{table_name}]")

        result = query_rest(table_name, [], ["id"])

        if result["success"]:
            count = len(result["rows"])
            if count > 0:
                log_pass(f"{count} rows")
            else:
                log_issue("DATA", f"{table_name} is EMPTY")
        else:
            log_issue("DATA", f"{table_name} query failed", result.get("error"))


# =============================================================================
# TEST 6: COLUMN DATA QUALITY
# =============================================================================
def test_column_data_quality():
    """Check if searchable columns actually have data."""
    print("\n" + "=" * 70)
    print("TEST 6: COLUMN DATA QUALITY")
    print("=" * 70)

    critical_columns = [
        ("pms_parts", "part_number"),
        ("pms_parts", "name"),
        ("pms_parts", "manufacturer"),
        ("pms_equipment", "name"),
        ("pms_equipment", "code"),
        ("pms_equipment", "manufacturer"),
        ("pms_faults", "fault_code"),
        ("pms_faults", "title"),
        ("graph_nodes", "label"),
        ("symptom_aliases", "alias"),
    ]

    for table, column in critical_columns:
        result = query_rest(table, [], [column])

        if result["success"]:
            non_null = [r for r in result["rows"] if r.get(column)]
            null_count = len(result["rows"]) - len(non_null)

            if null_count > 0:
                log_issue("DATA_QUALITY", f"{table}.{column} has {null_count} NULL values")
            else:
                log_pass(f"{table}.{column} - {len(non_null)} non-null")
        else:
            log_issue("DATA_QUALITY", f"{table}.{column} query failed")


# =============================================================================
# TEST 7: EDGE CASES
# =============================================================================
def test_edge_cases():
    """Test edge cases and potential failure modes."""
    print("\n" + "=" * 70)
    print("TEST 7: EDGE CASES")
    print("=" * 70)

    # Empty string
    print("\n[Empty string query]")
    probes = compile_probes(YACHT_ID, [{"type": "PART_NAME", "value": ""}])
    total = sum(len(p) for p in probes.values())
    if total > 0:
        log_issue("EDGE_CASE", "Empty string generated probes - should be blocked")
    else:
        log_pass("Empty string blocked")

    # Single character
    print("\n[Single character query]")
    probes = compile_probes(YACHT_ID, [{"type": "PART_NAME", "value": "a"}])
    total = sum(len(p) for p in probes.values())
    print(f"  Single char 'a' generated {total} probes")
    if total > 5:
        log_issue("EDGE_CASE", "Single character generates too many probes - should limit")

    # SQL injection attempt
    print("\n[SQL injection attempt]")
    malicious = "'; DROP TABLE pms_parts; --"
    probes = compile_probes(YACHT_ID, [{"type": "PART_NAME", "value": malicious}])
    # The probe should be safe because we use parameterization
    all_probes = []
    for wave_probes in probes.values():
        all_probes.extend(wave_probes)

    if all_probes:
        probe = all_probes[0]
        sql = probe.to_sql()
        if "DROP" in sql:
            log_issue("SECURITY", "SQL injection in generated SQL!", sql)
        else:
            log_pass("SQL injection blocked by parameterization")
    else:
        log_pass("SQL injection attempt generated no probes")

    # Very long string
    print("\n[Very long string]")
    long_string = "a" * 500
    probes = compile_probes(YACHT_ID, [{"type": "PART_NAME", "value": long_string}])
    total = sum(len(p) for p in probes.values())
    print(f"  500-char string generated {total} probes")
    # Should still work but may want to truncate

    # Unicode/emoji
    print("\n[Unicode/emoji]")
    unicode_val = "🔧 engine"
    probes = compile_probes(YACHT_ID, [{"type": "PART_NAME", "value": unicode_val}])
    total = sum(len(p) for p in probes.values())
    if total > 0:
        log_pass(f"Unicode handled ({total} probes)")
    else:
        log_issue("EDGE_CASE", "Unicode input blocked entirely")


# =============================================================================
# TEST 8: WAVE DISTRIBUTION
# =============================================================================
def test_wave_distribution():
    """Check that probes are distributed across waves correctly."""
    print("\n" + "=" * 70)
    print("TEST 8: WAVE DISTRIBUTION")
    print("=" * 70)

    test_entities = [
        {"type": "PART_NUMBER", "value": "ENG-0008-103"},
        {"type": "EQUIPMENT_NAME", "value": "Generator"},
        {"type": "SYMPTOM", "value": "vibration"},
    ]

    for entity in test_entities:
        print(f"\n[{entity['type']} = '{entity['value']}']")
        probes = compile_probes(YACHT_ID, [entity])

        for wave in range(4):
            wave_probes = probes.get(wave, [])
            if wave_probes:
                ops = [p.where_clauses[0].operator.value for p in wave_probes]
                print(f"  Wave {wave}: {len(wave_probes)} probes - {set(ops)}")

        # Check wave 0 has EXACT only
        wave0 = probes.get(0, [])
        non_exact = [p for p in wave0 if p.where_clauses[0].operator != Operator.EXACT]
        if non_exact:
            log_issue("WAVE", f"Wave 0 has non-EXACT operators for {entity['type']}")
        else:
            log_pass(f"Wave distribution correct for {entity['type']}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 70)
    print("RIGOROUS SQL FOUNDATION TEST")
    print("Finding all gaps before production")
    print("=" * 70)

    test_operator_coverage()
    time.sleep(0.5)

    test_conjunction_enforcement()
    time.sleep(0.5)

    test_variant_matching()
    time.sleep(0.5)

    test_entity_routing()
    time.sleep(0.5)

    test_data_existence()
    time.sleep(0.5)

    test_column_data_quality()
    time.sleep(0.5)

    test_edge_cases()
    time.sleep(0.5)

    test_wave_distribution()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n✓ PASSED: {len(PASSES)}")
    print(f"❌ ISSUES: {len(ISSUES)}")

    if ISSUES:
        print("\n--- ISSUES TO FIX ---")
        by_category = {}
        for issue in ISSUES:
            cat = issue["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(issue)

        for cat, issues in by_category.items():
            print(f"\n[{cat}] ({len(issues)} issues)")
            for issue in issues:
                print(f"  - {issue['description']}")
                if issue.get("details"):
                    print(f"    Details: {str(issue['details'])[:100]}")

    print("\n" + "=" * 70)
    if len(ISSUES) == 0:
        print("ALL TESTS PASSED - READY FOR PRODUCTION")
    else:
        print(f"FIX {len(ISSUES)} ISSUES BEFORE PRODUCTION")
    print("=" * 70)

    return ISSUES

if __name__ == "__main__":
    issues = main()
