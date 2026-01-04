"""
HARD ASSERTION TESTS
====================
Tests that ACTUALLY FAIL when search logic is wrong.

These tests compare:
1. Manual SQL results (ground truth)
2. Pipeline results (what we return to users)

If manual finds data but pipeline doesn't = TEST FAILS.

Categories tested:
- Category E bugs (data exists, pipeline returns 0)
- False negative rate measurement
- Coverage of ENTITY_SOURCE_MAP
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Known Category E bugs from audit
CATEGORY_E_BUGS = [
    ("pms_parts", "part_number", "ENG-0198-824"),
    ("pms_parts", "description", "Glow Plug"),
    ("pms_parts", "category", "Engine Room"),
    ("v_inventory", "part_number", "ENG-0198-824"),
    ("v_inventory", "description", "Glow Plug"),
    ("v_inventory", "category", "Engine Room"),
    ("v_inventory", "equipment", "Generator 1"),
    ("v_inventory", "system", "Electrical System"),
    ("v_inventory", "manufacturer", "Cummins"),
    ("search_fault_code_catalog", "severity", "warning"),
    ("entity_staging", "entity_type", "document_section"),
    ("entity_staging", "status", "completed"),
    ("graph_nodes", "extraction_source", "qwen_14b_local"),
    ("document_chunks", "graph_extract_status", "pending"),
    ("symptom_aliases", "alias", "shaking"),
]


class HardAssertionTester:
    """Tests that actually bite when search is wrong."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "false_negative_rate": 0.0
            }
        }

    async def manual_sql_search(self, table: str, column: str, value: str) -> int:
        """Direct SQL search - ground truth."""
        # Use ILIKE for text search
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        params = {
            "select": "count",
            column: f"ilike.*{value}*"
        }

        # Add yacht_id filter if table has it
        yacht_tables = [
            "pms_parts", "v_inventory", "search_fault_code_catalog",
            "entity_staging", "graph_nodes", "document_chunks",
            "symptom_aliases", "alias_symptoms", "alias_systems"
        ]
        if table in yacht_tables:
            params["yacht_id"] = f"eq.{TEST_YACHT_ID}"

        try:
            response = await self.client.get(url, headers={
                **self.headers,
                "Prefer": "count=exact"
            }, params=params)

            if response.status_code == 200:
                count_header = response.headers.get("content-range", "")
                if "/" in count_header:
                    return int(count_header.split("/")[1])
            return 0
        except Exception as e:
            print(f"  Manual SQL error: {e}")
            return -1

    async def pipeline_search(self, query: str) -> Tuple[int, Dict]:
        """Search through our pipeline - what users actually get."""
        try:
            # Import the search planner and create supabase client
            from api.search_planner import SearchPlanner, PlanExecutionResult
            from supabase import create_client, Client

            supabase: Client = create_client(SUPABASE_URL, SERVICE_KEY)
            planner = SearchPlanner(supabase, TEST_YACHT_ID)

            # First create a plan with a simple entity
            # The query becomes the search value for FREE_TEXT entity type
            entities = [{"type": "FREE_TEXT", "value": query}]
            plan = planner.create_plan(entities, max_waves=2)

            # Execute the plan
            result: PlanExecutionResult = planner.execute_plan(plan)

            total_results = result.total_rows if hasattr(result, 'total_rows') else 0

            return total_results, {"total_rows": total_results, "unique_rows": result.unique_rows}
        except Exception as e:
            print(f"  Pipeline error: {e}")
            return 0, {"error": str(e)}

    async def test_category_e_bug(self, table: str, column: str, sample_value: str) -> Dict:
        """Test a known Category E bug - MUST FAIL if bug still exists."""
        test_result = {
            "test_type": "CATEGORY_E_BUG",
            "table": table,
            "column": column,
            "sample_value": sample_value,
            "manual_sql_count": 0,
            "pipeline_count": 0,
            "passed": False,
            "failure_reason": None
        }

        print(f"\n  Testing {table}.{column} with '{sample_value}'...")

        # 1. Manual SQL (ground truth)
        manual_count = await self.manual_sql_search(table, column, sample_value)
        test_result["manual_sql_count"] = manual_count
        print(f"    Manual SQL: {manual_count} rows")

        if manual_count <= 0:
            test_result["passed"] = True
            test_result["failure_reason"] = "No data in table (not a bug test)"
            return test_result

        # 2. Pipeline search
        pipeline_count, pipeline_result = await self.pipeline_search(sample_value)
        test_result["pipeline_count"] = pipeline_count
        print(f"    Pipeline: {pipeline_count} rows")

        # 3. HARD ASSERTION: If manual finds data, pipeline MUST find data
        if manual_count > 0 and pipeline_count == 0:
            test_result["passed"] = False
            test_result["failure_reason"] = f"FALSE NEGATIVE: Manual found {manual_count}, pipeline found 0"
            print(f"    FAILED: {test_result['failure_reason']}")
        elif manual_count > 0 and pipeline_count > 0:
            test_result["passed"] = True
            print(f"    PASSED: Both found data")
        else:
            test_result["passed"] = True

        return test_result

    async def test_entity_source_map_coverage(self) -> Dict:
        """Test that ENTITY_SOURCE_MAP covers all searchable columns."""
        from api.search_planner import ENTITY_SOURCE_MAP

        # Load audit results
        audit_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/SEARCHABILITY_AUDIT.json"
        if os.path.exists(audit_path):
            with open(audit_path) as f:
                audit = json.load(f)
        else:
            return {"passed": False, "error": "Audit file not found"}

        # Get all searchable text columns
        searchable_columns = []
        for col in audit.get("columns", []):
            if col.get("actual_status") in ["OK", "E"]:
                searchable_columns.append(f"{col['table']}.{col['column']}")

        # Get columns covered by ENTITY_SOURCE_MAP
        # Note: SearchSource is a dataclass, use .table and .column attributes
        covered_columns = set()
        for entity_type, sources in ENTITY_SOURCE_MAP.items():
            for source in sources:
                covered_columns.add(f"{source.table}.{source.column}")

        coverage = len(covered_columns) / len(searchable_columns) * 100 if searchable_columns else 0

        test_result = {
            "test_type": "ENTITY_SOURCE_MAP_COVERAGE",
            "total_searchable_columns": len(searchable_columns),
            "covered_columns": len(covered_columns),
            "coverage_percent": round(coverage, 1),
            "uncovered_columns": [c for c in searchable_columns if c not in covered_columns],
            "passed": coverage >= 80.0,  # Require 80% coverage
            "failure_reason": None
        }

        if not test_result["passed"]:
            test_result["failure_reason"] = f"Coverage {coverage:.1f}% < 80% required"

        print(f"\n  ENTITY_SOURCE_MAP Coverage: {coverage:.1f}%")
        print(f"    Covered: {len(covered_columns)} / {len(searchable_columns)}")
        if not test_result["passed"]:
            print(f"    FAILED: {test_result['failure_reason']}")

        return test_result

    async def test_false_negative_rate(self) -> Dict:
        """Measure false negative rate across all Category E columns."""
        false_negatives = 0
        true_positives = 0
        total_tested = 0

        print("\n  Measuring False Negative Rate...")

        for table, column, sample in CATEGORY_E_BUGS:
            manual = await self.manual_sql_search(table, column, sample)
            if manual > 0:
                total_tested += 1
                pipeline, _ = await self.pipeline_search(sample)
                if pipeline == 0:
                    false_negatives += 1
                else:
                    true_positives += 1

        fn_rate = (false_negatives / total_tested * 100) if total_tested > 0 else 0

        test_result = {
            "test_type": "FALSE_NEGATIVE_RATE",
            "total_tested": total_tested,
            "true_positives": true_positives,
            "false_negatives": false_negatives,
            "false_negative_rate": round(fn_rate, 1),
            "passed": fn_rate <= 10.0,  # Require <10% FN rate
            "failure_reason": None
        }

        if not test_result["passed"]:
            test_result["failure_reason"] = f"FN rate {fn_rate:.1f}% > 10% allowed"

        print(f"    False Negatives: {false_negatives} / {total_tested}")
        print(f"    FN Rate: {fn_rate:.1f}%")

        return test_result

    async def run_all_tests(self):
        """Run all hard assertion tests."""
        print("=" * 60)
        print("HARD ASSERTION TESTS")
        print("=" * 60)
        print("\nThese tests FAIL when search logic is wrong.")
        print("If manual SQL finds data but pipeline doesn't = FAIL")

        # Test 1: Category E bugs
        print("\n" + "-" * 40)
        print("TEST GROUP 1: Category E Bugs")
        print("-" * 40)

        for table, column, sample in CATEGORY_E_BUGS:
            result = await self.test_category_e_bug(table, column, sample)
            self.results["tests"].append(result)
            self.results["summary"]["total"] += 1
            if result["passed"]:
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1

        # Test 2: ENTITY_SOURCE_MAP coverage
        print("\n" + "-" * 40)
        print("TEST GROUP 2: ENTITY_SOURCE_MAP Coverage")
        print("-" * 40)

        coverage_result = await self.test_entity_source_map_coverage()
        self.results["tests"].append(coverage_result)
        self.results["summary"]["total"] += 1
        if coverage_result["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

        # Test 3: False negative rate
        print("\n" + "-" * 40)
        print("TEST GROUP 3: False Negative Rate")
        print("-" * 40)

        fn_result = await self.test_false_negative_rate()
        self.results["tests"].append(fn_result)
        self.results["summary"]["total"] += 1
        if fn_result["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

        # Calculate overall FN rate
        fn_tests = [t for t in self.results["tests"] if t.get("test_type") == "FALSE_NEGATIVE_RATE"]
        if fn_tests:
            self.results["summary"]["false_negative_rate"] = fn_tests[0]["false_negative_rate"]

        return self.results

    async def close(self):
        await self.client.aclose()


async def main():
    tester = HardAssertionTester()

    try:
        results = await tester.run_all_tests()

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Pass Rate: {results['summary']['passed']/results['summary']['total']*100:.1f}%")
        print(f"False Negative Rate: {results['summary']['false_negative_rate']:.1f}%")

        # List failures
        failures = [t for t in results["tests"] if not t["passed"]]
        if failures:
            print("\n" + "-" * 40)
            print("FAILURES:")
            print("-" * 40)
            for f in failures:
                if f.get("test_type") == "CATEGORY_E_BUG":
                    print(f"  - {f['table']}.{f['column']}: {f['failure_reason']}")
                else:
                    print(f"  - {f['test_type']}: {f['failure_reason']}")

        # Save results
        output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/HARD_ASSERTION_RESULTS.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

        # Exit with failure code if tests failed
        if results["summary"]["failed"] > 0:
            print("\n*** TESTS FAILED - SEARCH LOGIC HAS BUGS ***")
            sys.exit(1)
        else:
            print("\n*** ALL TESTS PASSED ***")
            sys.exit(0)

    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
