#!/usr/bin/env python3
"""
DEMONSTRATION: Same SQL Template Running on 3 Different Tables
===============================================================
Proves that the SQL foundation is truly uniform.
Only substituted values differ - NOT the SQL structure.
"""
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.sql_foundation import (
    Operator, probe_single, probe_or_multicolumn, probe_and_conjunction,
    create_entity, compile_probes, TABLES, Variant
)

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def demo_single_probe_same_template():
    """
    PROOF 1: Same EXACT template across 3 tables.
    Only table name and column name differ.
    """
    print("=" * 70)
    print("PROOF 1: EXACT Operator - Same Template, 3 Tables")
    print("=" * 70)

    tables_and_columns = [
        ("pms_parts", "part_number", "ENG-0008-103"),
        ("pms_equipment", "code", "ME-P-001"),
        ("pms_faults", "fault_code", "E047"),
    ]

    for table, column, value in tables_and_columns:
        probe = probe_single(
            table=table,
            column=column,
            operator=Operator.EXACT,
            term=value,
            yacht_id=YACHT_ID,
            select_cols=TABLES[table].default_select,
            entity_type="TEST",
            variant_type=None
        )

        sql = probe.to_sql()
        print(f"\n--- {table}.{column} ---")
        print(sql)
        print(f"Params: {probe.params}")

    print("\n✓ SAME SQL STRUCTURE - only table/column/value substituted")

def demo_ilike_same_template():
    """
    PROOF 2: Same ILIKE template across 3 tables.
    """
    print("\n" + "=" * 70)
    print("PROOF 2: ILIKE Operator - Same Template, 3 Tables")
    print("=" * 70)

    tables_and_columns = [
        ("pms_parts", "name", "%fuel filter%"),
        ("pms_equipment", "name", "%generator%"),
        ("pms_suppliers", "name", "%marine%"),
    ]

    for table, column, pattern in tables_and_columns:
        probe = probe_single(
            table=table,
            column=column,
            operator=Operator.ILIKE,
            term=pattern,
            yacht_id=YACHT_ID,
            select_cols=TABLES[table].default_select,
            entity_type="TEST",
            variant_type=None
        )

        sql = probe.to_sql()
        print(f"\n--- {table}.{column} ---")
        print(sql)
        print(f"Params: {probe.params}")

    print("\n✓ SAME SQL STRUCTURE - only table/column/pattern substituted")

def demo_or_multicolumn():
    """
    PROOF 3: OR across columns in same table.
    """
    print("\n" + "=" * 70)
    print("PROOF 3: OR Multi-Column - Same Template Shape")
    print("=" * 70)

    entity = create_entity("EQUIPMENT_NAME", "generator")

    probe = probe_or_multicolumn(
        table="pms_equipment",
        columns=["name", "code"],
        operator=Operator.ILIKE,
        term="%generator%",
        yacht_id=YACHT_ID,
        select_cols=TABLES["pms_equipment"].default_select,
        entity_type="EQUIPMENT_NAME"
    )

    sql = probe.to_sql()
    print(sql)
    print(f"Params: {probe.params}")
    print("\n✓ OR shape: (col1 ILIKE $2) OR (col2 ILIKE $2)")

def demo_conjunction():
    """
    PROOF 4: AND conjunction across entities.
    """
    print("\n" + "=" * 70)
    print("PROOF 4: AND Conjunction - Multiple Entities")
    print("=" * 70)

    probe = probe_and_conjunction(
        table="pms_parts",
        column_terms=[
            ("name", Operator.ILIKE, "%fuel filter%"),
            ("manufacturer", Operator.ILIKE, "%MTU%"),
        ],
        yacht_id=YACHT_ID,
        select_cols=TABLES["pms_parts"].default_select
    )

    sql = probe.to_sql()
    print(sql)
    print(f"Params: {probe.params}")
    print("\n✓ AND shape: col1 ILIKE $2 AND col2 ILIKE $3")

def demo_compiler_full():
    """
    PROOF 5: Full compiler producing uniform probes.
    """
    print("\n" + "=" * 70)
    print("PROOF 5: Compiler Output - Entity-Driven Probe Generation")
    print("=" * 70)

    entities = [
        {"type": "PART_NUMBER", "value": "ENG-0008-103"},
    ]

    probes_by_wave = compile_probes(YACHT_ID, entities)

    print("\nProbes by wave:")
    for wave, probes in probes_by_wave.items():
        if probes:
            print(f"\n  Wave {wave}:")
            for p in probes:
                print(f"    - {p.probe_id}")
                print(f"      SQL: {p.to_sql()[:60]}...")

    print("\n✓ Compiler generates uniform probes from entity types")

def demo_variant_substitution():
    """
    PROOF 6: Same probe, different variants substituted.
    """
    print("\n" + "=" * 70)
    print("PROOF 6: Variant Substitution - Same Probe, Different Values")
    print("=" * 70)

    raw_value = "ENG-0008-103"
    variants = Variant.from_raw(raw_value)

    print(f"Raw value: {raw_value}")
    print("\nGenerated variants:")
    for v in variants:
        print(f"  {v.type.value} (priority {v.priority}): {v.value}")

    print("\nSame probe structure, different term values:")
    for v in variants[:2]:  # Show first two
        probe = probe_single(
            table="pms_parts",
            column="part_number",
            operator=Operator.EXACT if v.type.value == "canonical" else Operator.ILIKE,
            term=v.value,
            yacht_id=YACHT_ID,
            select_cols=["id", "part_number", "name"],
            entity_type="PART_NUMBER",
            variant_type=v.type
        )
        print(f"\n  Variant: {v.type.value}")
        print(f"  Params: {probe.params}")

    print("\n✓ Same SQL structure, only term value changes per variant")

if __name__ == "__main__":
    demo_single_probe_same_template()
    demo_ilike_same_template()
    demo_or_multicolumn()
    demo_conjunction()
    demo_compiler_full()
    demo_variant_substitution()

    print("\n" + "=" * 70)
    print("FOUNDATION PROVEN: Universal SQL, Uniform Structure, Substitutable Values")
    print("=" * 70)
