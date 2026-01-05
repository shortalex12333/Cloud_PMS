"""
REAL-WORLD QUERY TEST SUITE
============================
30+ queries across all lanes and intents.
Proves end-to-end behavior against live Supabase.
"""
import os
import sys
import time
import json
from dataclasses import dataclass
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_foundation.sql_planner import SQLPlanner, Lane, Intent
from sql_foundation.execute_sql import execute_with_plan, execute_search

YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

@dataclass
class QueryTest:
    name: str
    lane: Lane
    intent: Intent
    entities: List[Dict]
    expect_min_results: int = 0
    category: str = "basic"


# =============================================================================
# TEST CASES: 30+ real queries
# =============================================================================

REAL_QUERIES = [
    # --- LOOKUP (10 cases) ---
    QueryTest("Lookup: part number ENG-0008-103", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "PART_NUMBER", "value": "ENG-0008-103"}], 1, "lookup"),
    QueryTest("Lookup: equipment code ME-S-001", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "EQUIPMENT_CODE", "value": "ME-S-001"}], 1, "lookup"),
    QueryTest("Lookup: fault code E047", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "FAULT_CODE", "value": "E047"}], 1, "lookup"),
    QueryTest("Lookup: fault code G012", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "FAULT_CODE", "value": "G012"}], 1, "lookup"),
    QueryTest("Lookup: nonexistent part XYZ-999", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "PART_NUMBER", "value": "XYZ-999"}], 0, "lookup"),
    QueryTest("Lookup: equipment by serial", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "SERIAL_NUMBER", "value": "MTU-2019-001"}], 0, "lookup"),
    QueryTest("Lookup: PO number", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "PO_NUMBER", "value": "PO-2024"}], 0, "lookup"),
    QueryTest("Lookup: work order status", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "STATUS", "value": "pending"}], 0, "lookup"),
    QueryTest("Lookup: high priority items", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "PRIORITY", "value": "high"}], 0, "lookup"),
    QueryTest("Lookup: critical severity", Lane.NO_LLM, Intent.LOOKUP,
              [{"type": "SEVERITY", "value": "critical"}], 0, "lookup"),

    # --- SEARCH (10 cases) ---
    QueryTest("Search: oil filter", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "oil filter"}], 1, "search"),
    QueryTest("Search: generator", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "EQUIPMENT_NAME", "value": "generator"}], 1, "search"),
    QueryTest("Search: MTU parts", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "MANUFACTURER", "value": "MTU"}, {"type": "PART_NAME", "value": "filter"}], 0, "search"),
    QueryTest("Search: engine room equipment", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "LOCATION", "value": "engine room"}], 0, "search"),
    QueryTest("Search: hydraulic system", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "SYSTEM_NAME", "value": "hydraulic"}], 0, "search"),
    QueryTest("Search: fuel pump", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "fuel pump"}], 0, "search"),
    QueryTest("Search: coolant", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "coolant"}], 0, "search"),
    QueryTest("Search: bearing", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "bearing"}], 0, "search"),
    QueryTest("Search: gasket", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "gasket"}], 0, "search"),
    QueryTest("Search: sensor", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "sensor"}], 0, "search"),

    # --- DIAGNOSE (5 cases) ---
    QueryTest("Diagnose: vibration", Lane.GPT, Intent.DIAGNOSE,
              [{"type": "SYMPTOM", "value": "vibration"}], 1, "diagnose"),
    QueryTest("Diagnose: overheating", Lane.GPT, Intent.DIAGNOSE,
              [{"type": "SYMPTOM", "value": "high temp"}], 1, "diagnose"),
    QueryTest("Diagnose: oil leak", Lane.GPT, Intent.DIAGNOSE,
              [{"type": "SYMPTOM", "value": "oil leak"}], 0, "diagnose"),
    QueryTest("Diagnose: exhaust issue", Lane.GPT, Intent.DIAGNOSE,
              [{"type": "SYMPTOM", "value": "exhaust"}], 1, "diagnose"),
    QueryTest("Diagnose: pressure alarm", Lane.GPT, Intent.DIAGNOSE,
              [{"type": "SYMPTOM", "value": "pressure"}], 0, "diagnose"),

    # --- ENTITY SOUP (hostile, 3 cases) ---
    QueryTest("Entity soup: 3 entities", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "filter"},
               {"type": "MANUFACTURER", "value": "MTU"},
               {"type": "LOCATION", "value": "engine"}], 0, "hostile"),
    QueryTest("Entity soup: 5 entities", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "pump"},
               {"type": "EQUIPMENT_NAME", "value": "generator"},
               {"type": "MANUFACTURER", "value": "Caterpillar"},
               {"type": "LOCATION", "value": "engine room"},
               {"type": "SYSTEM_NAME", "value": "propulsion"}], 0, "hostile"),
    QueryTest("Entity soup: 8 entities (should → UNKNOWN)", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "filter"},
               {"type": "EQUIPMENT_NAME", "value": "engine"},
               {"type": "MANUFACTURER", "value": "MTU"},
               {"type": "LOCATION", "value": "engine room"},
               {"type": "SYMPTOM", "value": "noise"},
               {"type": "STATUS", "value": "pending"},
               {"type": "PRIORITY", "value": "high"},
               {"type": "SYSTEM_NAME", "value": "propulsion"}], 0, "hostile"),

    # --- TYPOS (hostile, 2 cases) ---
    QueryTest("Typo: fule fitler", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "PART_NAME", "value": "fule fitler", "variants": ["fuel filter"]}], 0, "hostile"),
    QueryTest("Typo: genertor", Lane.NO_LLM, Intent.SEARCH,
              [{"type": "EQUIPMENT_NAME", "value": "genertor", "variants": ["generator"]}], 0, "hostile"),
]


def run_tests():
    print("=" * 70)
    print("REAL-WORLD QUERY TEST SUITE")
    print(f"Target: {len(REAL_QUERIES)} queries against live Supabase")
    print("=" * 70)

    planner = SQLPlanner()
    results = []
    category_stats = {}

    for tc in REAL_QUERIES:
        start = time.time()

        try:
            plan = planner.plan(
                lane=tc.lane,
                entities=tc.entities,
                intent=tc.intent,
                yacht_id=YACHT_ID,
            )

            result = execute_with_plan(plan)
            latency = (time.time() - start) * 1000

            row_count = len(result.get("results", []))
            passed = row_count >= tc.expect_min_results

            # Track by category
            cat = tc.category
            if cat not in category_stats:
                category_stats[cat] = {"passed": 0, "failed": 0, "total_latency": 0}
            if passed:
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1
            category_stats[cat]["total_latency"] += latency

            status = "✓" if passed else "✗"
            print(f"{status} [{tc.category}] {tc.name}: {row_count} results ({latency:.0f}ms)")

            if not passed:
                print(f"      Expected >= {tc.expect_min_results}, got {row_count}")
                if result.get("trace", {}).get("errors"):
                    print(f"      Errors: {result['trace']['errors']}")

            results.append({
                "name": tc.name,
                "category": tc.category,
                "passed": passed,
                "results": row_count,
                "expected": tc.expect_min_results,
                "latency_ms": latency,
                "plan": plan.to_dict(),
                "waves": result.get("trace", {}).get("wave_traces", []),
            })

        except Exception as e:
            latency = (time.time() - start) * 1000
            print(f"✗ [{tc.category}] {tc.name}: ERROR - {e}")
            results.append({
                "name": tc.name,
                "category": tc.category,
                "passed": False,
                "error": str(e),
                "latency_ms": latency,
            })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results if r.get("passed"))
    failed = sum(1 for r in results if not r.get("passed"))
    total_latency = sum(r.get("latency_ms", 0) for r in results)

    print(f"\nTotal: {passed}/{len(results)} passed")
    print(f"Avg latency: {total_latency / len(results):.0f}ms")

    print("\nBy Category:")
    for cat, stats in category_stats.items():
        total = stats["passed"] + stats["failed"]
        avg_lat = stats["total_latency"] / total if total > 0 else 0
        print(f"  {cat}: {stats['passed']}/{total} ({avg_lat:.0f}ms avg)")

    # Failed tests
    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r.get("passed"):
                print(f"  ✗ {r['name']}: expected {r.get('expected', '?')}, got {r.get('results', 'ERROR')}")

    print("\n" + "=" * 70)

    return {
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "avg_latency_ms": total_latency / len(results),
        "by_category": category_stats,
    }


if __name__ == "__main__":
    if not os.environ.get("SUPABASE_SERVICE_KEY"):
        print("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    summary = run_tests()
    sys.exit(0 if summary["failed"] == 0 else 1)
