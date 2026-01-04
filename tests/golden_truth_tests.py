"""
GOLDEN TRUTH TESTS
==================
200 queries using REAL values from the database.

These are NOT random queries - they use actual data that EXISTS.
If pipeline returns 0 for these, it's a confirmed FALSE NEGATIVE.
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


@dataclass
class GoldenTruthQuery:
    """A query where we KNOW the expected result exists."""
    query: str
    table: str
    column: str
    expected_value: str
    expected_min_results: int
    category: str


@dataclass
class GoldenTruthResult:
    """Result of a golden truth test."""
    query: GoldenTruthQuery
    manual_sql_count: int
    pipeline_count: int
    passed: bool
    is_false_negative: bool
    latency_ms: float


class GoldenTruthTester:
    """Tests using real data from the database."""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}"
        }
        self.results: List[GoldenTruthResult] = []

    def get_real_values(self) -> List[GoldenTruthQuery]:
        """Fetch real values from the database to use as test queries."""
        queries = []

        # 1. Get real part_numbers from pms_parts
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/pms_parts?select=part_number,name&yacht_id=eq.{TEST_YACHT_ID}&limit=50",
            headers=self.headers
        )
        if r.status_code == 200:
            for row in r.json():
                if row.get("part_number"):
                    queries.append(GoldenTruthQuery(
                        query=row["part_number"],
                        table="pms_parts",
                        column="part_number",
                        expected_value=row["part_number"],
                        expected_min_results=1,
                        category="PART_NUMBER"
                    ))
                if row.get("name"):
                    queries.append(GoldenTruthQuery(
                        query=row["name"],
                        table="pms_parts",
                        column="name",
                        expected_value=row["name"],
                        expected_min_results=1,
                        category="PART_NAME"
                    ))

        # 2. Get real labels from graph_nodes
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/graph_nodes?select=label,node_type&yacht_id=eq.{TEST_YACHT_ID}&limit=50",
            headers=self.headers
        )
        if r.status_code == 200:
            for row in r.json():
                if row.get("label"):
                    queries.append(GoldenTruthQuery(
                        query=row["label"],
                        table="graph_nodes",
                        column="label",
                        expected_value=row["label"],
                        expected_min_results=1,
                        category="EQUIPMENT_NAME"
                    ))

        # 3. Get real locations from v_inventory
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/v_inventory?select=location,name,part_number&yacht_id=eq.{TEST_YACHT_ID}&limit=50",
            headers=self.headers
        )
        if r.status_code == 200:
            seen_locations = set()
            for row in r.json():
                loc = row.get("location")
                if loc and loc not in seen_locations:
                    seen_locations.add(loc)
                    queries.append(GoldenTruthQuery(
                        query=loc,
                        table="v_inventory",
                        column="location",
                        expected_value=loc,
                        expected_min_results=1,
                        category="STOCK_LOCATION"
                    ))

        # 4. Get real equipment names from pms_equipment
        r = self.client.get(
            f"{SUPABASE_URL}/rest/v1/pms_equipment?select=name,serial_number&yacht_id=eq.{TEST_YACHT_ID}&limit=30",
            headers=self.headers
        )
        if r.status_code == 200:
            for row in r.json():
                if row.get("name"):
                    queries.append(GoldenTruthQuery(
                        query=row["name"],
                        table="pms_equipment",
                        column="name",
                        expected_value=row["name"],
                        expected_min_results=1,
                        category="EQUIPMENT_NAME"
                    ))

        return queries[:200]  # Limit to 200

    def manual_sql_search(self, table: str, column: str, value: str) -> int:
        """Direct SQL search - ground truth."""
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        params = {
            "select": "count",
            column: f"ilike.*{value}*",
            "yacht_id": f"eq.{TEST_YACHT_ID}"
        }

        try:
            response = self.client.get(url, headers={
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

    def pipeline_search(self, query: str) -> Tuple[int, float]:
        """Search through pipeline."""
        import time
        start = time.time()

        try:
            from api.search_planner import SearchPlanner, PlanExecutionResult
            from supabase import create_client, Client

            supabase: Client = create_client(SUPABASE_URL, SERVICE_KEY)
            planner = SearchPlanner(supabase, TEST_YACHT_ID)

            entities = [{"type": "FREE_TEXT", "value": query}]
            plan = planner.create_plan(entities, max_waves=2)
            result: PlanExecutionResult = planner.execute_plan(plan)

            latency = (time.time() - start) * 1000
            return result.total_rows, latency
        except Exception as e:
            latency = (time.time() - start) * 1000
            return 0, latency

    def run_single_test(self, gq: GoldenTruthQuery) -> GoldenTruthResult:
        """Run a single golden truth test."""
        # Manual SQL
        manual_count = self.manual_sql_search(gq.table, gq.column, gq.expected_value)

        # Pipeline
        pipeline_count, latency = self.pipeline_search(gq.query)

        # A false negative = manual finds it but pipeline doesn't
        is_false_negative = manual_count > 0 and pipeline_count == 0
        passed = not is_false_negative

        return GoldenTruthResult(
            query=gq,
            manual_sql_count=manual_count,
            pipeline_count=pipeline_count,
            passed=passed,
            is_false_negative=is_false_negative,
            latency_ms=latency
        )

    def run_all_tests(self) -> Dict:
        """Run all golden truth tests."""
        print("Fetching real values from database...")
        queries = self.get_real_values()
        print(f"Found {len(queries)} golden truth queries")

        print("\nRunning tests...")
        for i, gq in enumerate(queries):
            result = self.run_single_test(gq)
            self.results.append(result)

            if (i + 1) % 20 == 0:
                passed = sum(1 for r in self.results if r.passed)
                fn = sum(1 for r in self.results if r.is_false_negative)
                print(f"  Progress: {i+1}/{len(queries)} | Passed: {passed} | FN: {fn}")

        # Generate report
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        false_negatives = sum(1 for r in self.results if r.is_false_negative)

        by_category = {}
        for r in self.results:
            cat = r.query.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "fn": 0}
            by_category[cat]["total"] += 1
            if r.passed:
                by_category[cat]["passed"] += 1
            if r.is_false_negative:
                by_category[cat]["fn"] += 1

        # Calculate rates
        for cat in by_category:
            stats = by_category[cat]
            stats["pass_rate"] = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            stats["fn_rate"] = stats["fn"] / stats["total"] * 100 if stats["total"] > 0 else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "total_queries": total,
            "passed": passed,
            "failed": total - passed,
            "false_negatives": false_negatives,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "false_negative_rate": false_negatives / total * 100 if total > 0 else 0,
            "by_category": by_category,
            "false_negative_samples": [
                {
                    "query": r.query.query,
                    "table": r.query.table,
                    "column": r.query.column,
                    "category": r.query.category,
                    "manual_count": r.manual_sql_count,
                    "pipeline_count": r.pipeline_count
                }
                for r in self.results if r.is_false_negative
            ][:30]  # First 30 FN examples
        }

    def close(self):
        self.client.close()


def main():
    print("=" * 60)
    print("GOLDEN TRUTH TESTS")
    print("=" * 60)
    print("Testing with REAL values from the database.")
    print("Any failure = confirmed FALSE NEGATIVE bug")
    print()

    tester = GoldenTruthTester()
    try:
        report = tester.run_all_tests()

        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        print(f"Total Queries: {report['total_queries']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Pass Rate: {report['pass_rate']:.1f}%")
        print(f"False Negatives: {report['false_negatives']}")
        print(f"False Negative Rate: {report['false_negative_rate']:.1f}%")

        print("\nBy Category:")
        for cat, stats in report["by_category"].items():
            print(f"  {cat}: {stats['pass_rate']:.0f}% pass, {stats['fn']} FN ({stats['fn_rate']:.0f}%)")

        if report["false_negative_samples"]:
            print("\nSample False Negatives:")
            for fn in report["false_negative_samples"][:10]:
                print(f"  [{fn['category']}] '{fn['query'][:30]}...' in {fn['table']}.{fn['column']}")
                print(f"    Manual: {fn['manual_count']} | Pipeline: {fn['pipeline_count']}")

        # Save report
        output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/GOLDEN_TRUTH_RESULTS.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

        # Exit with failure code if FN rate > 10%
        if report["false_negative_rate"] > 10:
            print(f"\n*** FAILED: False negative rate {report['false_negative_rate']:.1f}% > 10% threshold ***")
            sys.exit(1)
        else:
            print("\n*** PASSED ***")
            sys.exit(0)

    finally:
        tester.close()


if __name__ == "__main__":
    main()
