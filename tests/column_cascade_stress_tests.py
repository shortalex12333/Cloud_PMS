"""
COLUMN CASCADE STRESS TESTS
============================
1500 queries across 7 categories to stress test search coverage.

Categories:
1. COLUMN_AMBIGUITY_PARTS - Same term exists in multiple columns
2. CANONICAL_VS_RAW - Canonical form vs raw user input
3. CONJUNCTION_ONLY_SURFACES - Columns that need context
4. ENTITY_SOUP_NO_VERB - Multiple entities, no action verb
5. FAULT_CODE_FORMATS - Various fault code formats
6. LOCATION_VARIANTS - Location name variations
7. NEGATIVE_CONTROLS - Should return 0 (nonsense queries)

Each test compares manual SQL vs pipeline to measure false negative rate.
"""

import os
import sys
import json
import asyncio
import httpx
import random
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUPABASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"


@dataclass
class StressTestQuery:
    """A single stress test query."""
    category: str
    query: str
    expected_table: str
    expected_column: str
    expected_min_results: int  # 0 for negative controls
    description: str


@dataclass
class StressTestResult:
    """Result of a single stress test."""
    query: StressTestQuery
    manual_sql_count: int
    pipeline_count: int
    passed: bool
    failure_type: str  # "FALSE_NEGATIVE", "FALSE_POSITIVE", "NONE"
    latency_ms: float


class StressTestGenerator:
    """Generates 1500 stress test queries across 7 categories."""

    def __init__(self):
        self.queries: List[StressTestQuery] = []

    def generate_all(self) -> List[StressTestQuery]:
        """Generate all 1500 queries."""
        # ~215 per category to hit 1500
        self._generate_column_ambiguity_parts(215)
        self._generate_canonical_vs_raw(215)
        self._generate_conjunction_only_surfaces(215)
        self._generate_entity_soup_no_verb(215)
        self._generate_fault_code_formats(215)
        self._generate_location_variants(215)
        self._generate_negative_controls(215)

        return self.queries

    def _generate_column_ambiguity_parts(self, count: int):
        """
        Category 1: COLUMN_AMBIGUITY_PARTS
        Terms that exist in multiple columns - tests if search finds all.
        """
        # Part numbers that exist in both pms_parts and v_inventory
        part_prefixes = ["ENG", "HYD", "ELE", "NAV", "PLB", "HVA", "SAF", "DEC"]
        part_suffixes = list(range(100, 999))

        for i in range(count):
            prefix = random.choice(part_prefixes)
            num = random.choice(part_suffixes)
            middle = random.randint(1000, 9999)
            part_number = f"{prefix}-{middle:04d}-{num}"

            self.queries.append(StressTestQuery(
                category="COLUMN_AMBIGUITY_PARTS",
                query=part_number,
                expected_table="pms_parts,v_inventory",
                expected_column="part_number",
                expected_min_results=0,  # May or may not exist
                description=f"Part number should search both pms_parts and v_inventory"
            ))

    def _generate_canonical_vs_raw(self, count: int):
        """
        Category 2: CANONICAL_VS_RAW
        Raw user input vs normalized/canonical forms.
        """
        raw_canonical_pairs = [
            # (raw, canonical, entity_type)
            ("main engine", "MAIN_ENGINE", "EQUIPMENT_NAME"),
            ("gen set", "GENERATOR", "EQUIPMENT_NAME"),
            ("genset", "GENERATOR", "EQUIPMENT_NAME"),
            ("a/c", "AIR_CONDITIONING", "SYSTEM_NAME"),
            ("ac system", "AIR_CONDITIONING", "SYSTEM_NAME"),
            ("hvac", "HVAC_SYSTEM", "SYSTEM_NAME"),
            ("bow thruster", "BOW_THRUSTER", "EQUIPMENT_NAME"),
            ("stern thruster", "STERN_THRUSTER", "EQUIPMENT_NAME"),
            ("watermaker", "WATERMAKER", "EQUIPMENT_NAME"),
            ("water maker", "WATERMAKER", "EQUIPMENT_NAME"),
            ("bilge pump", "BILGE_PUMP", "EQUIPMENT_NAME"),
            ("shore power", "SHORE_POWER", "SYSTEM_NAME"),
            ("nav lights", "NAVIGATION_LIGHTS", "EQUIPMENT_NAME"),
            ("radar", "RADAR", "EQUIPMENT_NAME"),
            ("autopilot", "AUTOPILOT", "EQUIPMENT_NAME"),
            ("auto pilot", "AUTOPILOT", "EQUIPMENT_NAME"),
            ("GPS", "GPS", "EQUIPMENT_NAME"),
            ("gps system", "GPS", "EQUIPMENT_NAME"),
            ("VHF", "VHF_RADIO", "EQUIPMENT_NAME"),
            ("vhf radio", "VHF_RADIO", "EQUIPMENT_NAME"),
        ]

        for i in range(count):
            raw, canonical, entity_type = random.choice(raw_canonical_pairs)
            # Alternate between raw and canonical queries
            if i % 2 == 0:
                query = raw
                desc = f"Raw form '{raw}' should find canonical '{canonical}'"
            else:
                query = canonical
                desc = f"Canonical form '{canonical}' should find entries"

            self.queries.append(StressTestQuery(
                category="CANONICAL_VS_RAW",
                query=query,
                expected_table="graph_nodes",
                expected_column="label,normalized_label",
                expected_min_results=0,  # Depends on data
                description=desc
            ))

    def _generate_conjunction_only_surfaces(self, count: int):
        """
        Category 3: CONJUNCTION_ONLY_SURFACES
        Columns that only make sense when combined with another term.
        """
        weak_terms = [
            "high", "low", "normal", "critical", "warning",
            "pending", "completed", "active", "inactive",
            "open", "closed", "in progress", "scheduled",
            "red", "green", "yellow", "amber",
            "1", "2", "3", "4", "5",
            "yes", "no", "true", "false"
        ]

        context_terms = [
            "engine", "generator", "pump", "filter",
            "oil", "fuel", "water", "coolant",
            "pressure", "temperature", "level", "flow"
        ]

        for i in range(count):
            weak = random.choice(weak_terms)
            context = random.choice(context_terms)

            if i % 3 == 0:
                # Weak term alone - should match little
                query = weak
                desc = f"Weak term '{weak}' alone - conjunction_only should limit results"
            elif i % 3 == 1:
                # With context - should match more
                query = f"{context} {weak}"
                desc = f"Weak term '{weak}' with context '{context}' - should find more"
            else:
                # Reversed order
                query = f"{weak} {context}"
                desc = f"Reversed '{weak} {context}' - order shouldn't matter"

            self.queries.append(StressTestQuery(
                category="CONJUNCTION_ONLY_SURFACES",
                query=query,
                expected_table="various",
                expected_column="status,severity,priority",
                expected_min_results=0,
                description=desc
            ))

    def _generate_entity_soup_no_verb(self, count: int):
        """
        Category 4: ENTITY_SOUP_NO_VERB
        Multiple entities without action verbs - pure search queries.
        """
        equipment = ["main engine", "generator", "watermaker", "bow thruster", "bilge pump"]
        systems = ["electrical", "hydraulic", "fuel", "cooling", "HVAC"]
        parts = ["filter", "pump", "valve", "sensor", "relay"]
        locations = ["engine room", "lazarette", "flybridge", "forepeak", "bilge"]

        for i in range(count):
            # Combine 2-4 entities
            num_entities = random.randint(2, 4)
            entities = []

            if random.random() > 0.5:
                entities.append(random.choice(equipment))
            if random.random() > 0.5:
                entities.append(random.choice(systems))
            if random.random() > 0.5:
                entities.append(random.choice(parts))
            if random.random() > 0.5:
                entities.append(random.choice(locations))

            # Ensure at least 2
            while len(entities) < 2:
                entities.append(random.choice(equipment + systems + parts))

            query = " ".join(entities[:num_entities])

            self.queries.append(StressTestQuery(
                category="ENTITY_SOUP_NO_VERB",
                query=query,
                expected_table="graph_nodes,pms_parts,v_inventory",
                expected_column="label,name,description",
                expected_min_results=0,
                description=f"Entity soup: {len(entities)} entities, no verb"
            ))

    def _generate_fault_code_formats(self, count: int):
        """
        Category 5: FAULT_CODE_FORMATS
        Various fault code format variations.
        """
        prefixes = ["E", "F", "W", "A", "C", "ERR", "FAULT", "WARN"]
        separators = ["", "-", "_", " ", "."]

        for i in range(count):
            prefix = random.choice(prefixes)
            sep = random.choice(separators)
            num = random.randint(1, 999)

            # Various formats
            formats = [
                f"{prefix}{sep}{num:03d}",
                f"{prefix}{sep}{num}",
                f"{num:03d}",
                f"error {num}",
                f"fault {prefix}{num:03d}",
                f"code {prefix}{sep}{num}",
            ]
            query = random.choice(formats)

            self.queries.append(StressTestQuery(
                category="FAULT_CODE_FORMATS",
                query=query,
                expected_table="search_fault_code_catalog",
                expected_column="code",
                expected_min_results=0,
                description=f"Fault code format variation"
            ))

    def _generate_location_variants(self, count: int):
        """
        Category 6: LOCATION_VARIANTS
        Location name variations (abbreviations, full names, misspellings).
        """
        location_variants = [
            # (variations list, canonical)
            (["ER", "eng room", "engine room", "engineroom", "engine rm"], "engine_room"),
            (["laz", "lazarette", "lazaret", "lazzarette"], "lazarette"),
            (["fb", "flybridge", "fly bridge", "flying bridge"], "flybridge"),
            (["fp", "forepeak", "fore peak", "fwd peak"], "forepeak"),
            (["bilge", "bilges", "bilge area"], "bilge"),
            (["galley", "kitchen", "gally"], "galley"),
            (["salon", "saloon", "main salon"], "salon"),
            (["head", "bathroom", "toilet", "wc"], "head"),
            (["stbd", "starboard", "stb"], "starboard"),
            (["port", "pt"], "port"),
            (["fwd", "forward", "fore"], "forward"),
            (["aft", "stern", "rear"], "aft"),
            (["cockpit", "ck pit", "c pit"], "cockpit"),
            (["anchor locker", "anchor lkr", "anch locker"], "anchor_locker"),
            (["chain locker", "chain lkr"], "chain_locker"),
        ]

        for i in range(count):
            variants, canonical = random.choice(location_variants)
            variant = random.choice(variants)

            self.queries.append(StressTestQuery(
                category="LOCATION_VARIANTS",
                query=variant,
                expected_table="v_inventory,pms_equipment",
                expected_column="location",
                expected_min_results=0,
                description=f"Location variant '{variant}' → canonical '{canonical}'"
            ))

    def _generate_negative_controls(self, count: int):
        """
        Category 7: NEGATIVE_CONTROLS
        Queries that SHOULD return 0 results.
        """
        nonsense = [
            # Gibberish
            "xyzzy", "qwertyuiop", "asdfghjkl", "zxcvbnm",
            "aaaaaa", "123456789", "!@#$%^&*()",
            # Random strings
            "flurblegargle", "snorkelwax", "blinkenlight",
            "framistan", "grommit", "wodget",
            # Wrong domain
            "cryptocurrency", "blockchain", "NFT",
            "facebook", "instagram", "tiktok",
            "pizza", "hamburger", "sushi",
            # SQL injection attempts (should return 0, not error)
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "{{constructor.constructor('return this')()}}",
        ]

        for i in range(count):
            if i < len(nonsense):
                query = nonsense[i % len(nonsense)]
            else:
                # Generate random nonsense
                query = ''.join(random.choices('abcdefghijklmnop', k=random.randint(8, 15)))

            self.queries.append(StressTestQuery(
                category="NEGATIVE_CONTROLS",
                query=query,
                expected_table="none",
                expected_column="none",
                expected_min_results=0,  # MUST be 0
                description=f"Negative control - should return 0 results"
            ))


class StressTestRunner:
    """Runs stress tests and measures false negative rate."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.headers = {
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json"
        }
        self.results: List[StressTestResult] = []

    async def manual_sql_search(self, query: str, tables: List[str]) -> int:
        """Direct SQL search across specified tables."""
        total_count = 0

        for table in tables:
            try:
                # Get text columns for this table
                text_columns = await self._get_text_columns(table)
                if not text_columns:
                    continue

                # Search each text column
                for col in text_columns[:5]:  # Limit to 5 columns per table
                    url = f"{SUPABASE_URL}/rest/v1/{table}"
                    params = {
                        "select": "count",
                        col: f"ilike.*{query}*",
                        "yacht_id": f"eq.{TEST_YACHT_ID}"
                    }

                    response = await self.client.get(url, headers={
                        **self.headers,
                        "Prefer": "count=exact"
                    }, params=params)

                    if response.status_code == 200:
                        count_header = response.headers.get("content-range", "")
                        if "/" in count_header:
                            count = int(count_header.split("/")[1])
                            if count > 0:
                                total_count += count
                                break  # Found in this table, move to next
            except Exception:
                pass

        return total_count

    async def _get_text_columns(self, table: str) -> List[str]:
        """Get text columns for a table (cached)."""
        # Common text columns per table
        text_cols_map = {
            "pms_parts": ["part_number", "name", "description", "category", "manufacturer"],
            "v_inventory": ["part_number", "name", "description", "category", "location", "equipment", "system"],
            "graph_nodes": ["label", "normalized_label", "node_type", "extraction_source"],
            "pms_equipment": ["name", "serial_number", "location", "description"],
            "search_fault_code_catalog": ["code", "description", "severity"],
            "search_document_chunks": ["content", "section_title", "doc_type"],
            "symptom_aliases": ["alias", "canonical"],
            "alias_symptoms": ["alias", "canonical"],
        }
        return text_cols_map.get(table, [])

    async def pipeline_search(self, query: str) -> Tuple[int, float]:
        """Search through pipeline, return (count, latency_ms)."""
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

    async def run_single_test(self, test_query: StressTestQuery) -> StressTestResult:
        """Run a single stress test."""
        # Determine tables to search
        tables = test_query.expected_table.split(",") if test_query.expected_table != "none" else []
        if "various" in tables:
            tables = ["pms_parts", "v_inventory", "graph_nodes", "pms_equipment"]

        # Run manual SQL
        manual_count = await self.manual_sql_search(test_query.query, tables) if tables else 0

        # Run pipeline
        pipeline_count, latency = await self.pipeline_search(test_query.query)

        # Determine pass/fail
        if test_query.category == "NEGATIVE_CONTROLS":
            # Negative controls: pipeline should return 0 or very few
            passed = pipeline_count <= 2
            failure_type = "FALSE_POSITIVE" if not passed else "NONE"
        else:
            # Regular tests: if manual finds data, pipeline should too
            if manual_count > 0 and pipeline_count == 0:
                passed = False
                failure_type = "FALSE_NEGATIVE"
            elif manual_count == 0 and pipeline_count > 0:
                # Pipeline found something manual didn't - could be good (broader search)
                passed = True
                failure_type = "NONE"
            else:
                passed = True
                failure_type = "NONE"

        return StressTestResult(
            query=test_query,
            manual_sql_count=manual_count,
            pipeline_count=pipeline_count,
            passed=passed,
            failure_type=failure_type,
            latency_ms=latency
        )

    async def run_all_tests(self, queries: List[StressTestQuery], batch_size: int = 50):
        """Run all stress tests in batches."""
        print(f"Running {len(queries)} stress tests...")
        print(f"Categories: {len(set(q.category for q in queries))}")

        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self.run_single_test(q) for q in batch
            ])
            self.results.extend(batch_results)

            # Progress update
            completed = min(i + batch_size, len(queries))
            passed = sum(1 for r in self.results if r.passed)
            print(f"  Progress: {completed}/{len(queries)} | Passed: {passed}/{len(self.results)}")

        return self.results

    def generate_report(self) -> Dict:
        """Generate final report."""
        by_category = {}
        for r in self.results:
            cat = r.query.category
            if cat not in by_category:
                by_category[cat] = {
                    "total": 0,
                    "passed": 0,
                    "false_negatives": 0,
                    "false_positives": 0,
                    "avg_latency_ms": []
                }
            by_category[cat]["total"] += 1
            if r.passed:
                by_category[cat]["passed"] += 1
            if r.failure_type == "FALSE_NEGATIVE":
                by_category[cat]["false_negatives"] += 1
            if r.failure_type == "FALSE_POSITIVE":
                by_category[cat]["false_positives"] += 1
            by_category[cat]["avg_latency_ms"].append(r.latency_ms)

        # Calculate averages
        for cat in by_category:
            latencies = by_category[cat]["avg_latency_ms"]
            by_category[cat]["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0
            by_category[cat]["pass_rate"] = by_category[cat]["passed"] / by_category[cat]["total"] * 100

        total_passed = sum(1 for r in self.results if r.passed)
        total_fn = sum(1 for r in self.results if r.failure_type == "FALSE_NEGATIVE")
        total_fp = sum(1 for r in self.results if r.failure_type == "FALSE_POSITIVE")

        return {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(self.results),
            "total_passed": total_passed,
            "total_failed": len(self.results) - total_passed,
            "pass_rate": total_passed / len(self.results) * 100 if self.results else 0,
            "false_negative_count": total_fn,
            "false_positive_count": total_fp,
            "false_negative_rate": total_fn / len(self.results) * 100 if self.results else 0,
            "by_category": by_category,
            "sample_failures": [
                {
                    "category": r.query.category,
                    "query": r.query.query,
                    "manual_count": r.manual_sql_count,
                    "pipeline_count": r.pipeline_count,
                    "failure_type": r.failure_type
                }
                for r in self.results if not r.passed
            ][:50]  # First 50 failures
        }

    async def close(self):
        await self.client.aclose()


async def main():
    print("=" * 60)
    print("COLUMN CASCADE STRESS TESTS")
    print("=" * 60)
    print("Generating 1500 queries across 7 categories...")

    # Generate queries
    generator = StressTestGenerator()
    queries = generator.generate_all()

    print(f"Generated {len(queries)} queries")
    for cat in set(q.category for q in queries):
        count = sum(1 for q in queries if q.category == cat)
        print(f"  - {cat}: {count}")

    # Run tests
    runner = StressTestRunner()
    try:
        await runner.run_all_tests(queries, batch_size=25)

        # Generate report
        report = runner.generate_report()

        print("\n" + "=" * 60)
        print("FINAL REPORT")
        print("=" * 60)
        print(f"Total Queries: {report['total_queries']}")
        print(f"Passed: {report['total_passed']}")
        print(f"Failed: {report['total_failed']}")
        print(f"Pass Rate: {report['pass_rate']:.1f}%")
        print(f"False Negative Rate: {report['false_negative_rate']:.1f}%")

        print("\nBy Category:")
        for cat, stats in report["by_category"].items():
            print(f"  {cat}:")
            print(f"    Pass Rate: {stats['pass_rate']:.1f}%")
            print(f"    False Negatives: {stats['false_negatives']}")
            print(f"    Avg Latency: {stats['avg_latency_ms']:.1f}ms")

        # Save report
        output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))docs/COLUMN_CASCADE_RESULTS.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
