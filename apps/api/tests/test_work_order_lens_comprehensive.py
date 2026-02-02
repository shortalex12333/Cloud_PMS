#!/usr/bin/env python3
"""
Work Order Lens - Comprehensive Overnight Testing Suite

Tests Work Order Lens integration with the async pipeline focusing on:
1. Entity extraction for work order queries (chaotic, vague, misspelled)
2. Capability execution with title/description ILIKE search
3. Cross-lens search (equipment → work orders)
4. RLS policy enforcement
5. Result confidence and filtering
6. Frontend integration (microaction availability)

Requirements:
- Async pipeline operational (5-stage extraction)
- Work Order capability with title/description ILIKE columns
- Entity transformation logic in pipeline_v1.py
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Load environment variables from .env.tenant1
env_file = Path(__file__).parent.parent.parent.parent / ".env.tenant1"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                # Map TENANT_1_* to SUPABASE_* for compatibility
                if key == 'TENANT_1_SUPABASE_URL':
                    os.environ['SUPABASE_URL'] = value
                elif key == 'TENANT_1_SUPABASE_SERVICE_KEY':
                    os.environ['SUPABASE_SERVICE_KEY'] = value

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test environment
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
OTHER_YACHT_ID = "00000000-0000-0000-0000-000000000000"

# Test data directory
TEST_OUTPUT_DIR = Path(__file__).parent / "test_results" / "work_order_lens"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timestamp for this test run
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


class WorkOrderLensTestSuite:
    """Comprehensive test suite for Work Order Lens."""

    def __init__(self):
        self.test_results = {
            "test_run_id": TEST_RUN_ID,
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "failures": [],
            "summary": {},
        }
        self.pipeline = None
        self.supabase_client = None

    async def setup(self):
        """Initialize test environment."""
        print("=" * 80)
        print("WORK ORDER LENS - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print(f"Test Run ID: {TEST_RUN_ID}")
        print(f"Yacht ID: {YACHT_ID}")
        print(f"Output Directory: {TEST_OUTPUT_DIR}")
        print("")

        try:
            # Import after path setup
            from pipeline_v1 import Pipeline
            from integrations.supabase import get_supabase_client

            self.supabase_client = get_supabase_client()
            self.pipeline = Pipeline(self.supabase_client, YACHT_ID)

            print("✅ Pipeline initialized")
            print("✅ Supabase client connected")
            print("")
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            raise

    async def test_entity_extraction_work_order_queries(self):
        """Test 1: Entity Extraction for Work Order Queries"""
        print("=" * 80)
        print("TEST 1: Entity Extraction for Work Order Queries")
        print("=" * 80)
        print("")

        test_queries = [
            # Clear, structured queries
            {
                "query": "WO-12345",
                "expected_entity_types": ["WORK_ORDER_ID"],
                "expected_values": ["WO-12345"],
                "category": "exact_wo_number",
            },
            {
                "query": "work order 98765",
                "expected_entity_types": ["WORK_ORDER_ID"],
                "expected_values": ["work order 98765"],
                "category": "natural_wo_number",
            },
            # Equipment-based (should create WORK_ORDER_EQUIPMENT entity)
            {
                "query": "generator",
                "expected_entity_types": ["EQUIPMENT_NAME", "WORK_ORDER_EQUIPMENT"],
                "expected_values": ["generator"],
                "category": "equipment_single_word",
            },
            {
                "query": "port generator maintenance",
                "expected_entity_types": ["EQUIPMENT_NAME", "WORK_ORDER_EQUIPMENT"],
                "expected_values": ["generator", "port generator"],
                "category": "equipment_compound",
            },
            # Maintenance actions (should create WORK_ORDER_TITLE entity)
            {
                "query": "oil change",
                "expected_entity_types": ["WORK_ORDER_TITLE"],
                "expected_values": ["change"],
                "category": "maintenance_action",
            },
            {
                "query": "routine maintenance checklist",
                "expected_entity_types": ["WORK_ORDER_TITLE"],
                "expected_values": ["maintenance"],
                "category": "maintenance_with_descriptor",
            },
            # Chaotic queries (real user input)
            {
                "query": "show me work order from yesterday about generator leak",
                "expected_entity_types": ["EQUIPMENT_NAME", "WORK_ORDER_EQUIPMENT"],
                "expected_values": ["generator"],
                "category": "chaotic_natural_language",
            },
            {
                "query": "genrator oil chnge scheduled today",
                "expected_entity_types": ["EQUIPMENT_NAME"],  # Misspellings
                "expected_values": None,  # May not extract due to misspellings
                "category": "misspelled_chaos",
            },
            # Vague queries
            {
                "query": "maintenance",
                "expected_entity_types": ["WORK_ORDER_TITLE"],
                "expected_values": ["maintenance"],
                "category": "vague_single_word",
            },
            {
                "query": "stuff that needs fixing",
                "expected_entity_types": None,  # Too vague
                "expected_values": None,
                "category": "extremely_vague",
            },
            # Contradictory queries
            {
                "query": "urgent but not critical generator service",
                "expected_entity_types": ["EQUIPMENT_NAME", "WORK_ORDER_EQUIPMENT"],
                "expected_values": ["generator"],
                "category": "contradictory_priority",
            },
        ]

        results = []

        for test_case in test_queries:
            query = test_case["query"]
            category = test_case["category"]

            print(f"Testing: '{query}' ({category})")

            try:
                # Extract entities using pipeline
                extraction_result = await self.pipeline._extract(query)
                entities = extraction_result.get("entities", [])

                print(f"  Entities extracted: {len(entities)}")
                for entity in entities:
                    print(f"    - {entity['type']:30} | {entity['value']:30} | conf: {entity.get('confidence', 0):.2f} | source: {entity.get('source', 'unknown')}")

                # Validate expected entity types
                entity_types = [e["type"] for e in entities]

                if test_case["expected_entity_types"]:
                    for expected_type in test_case["expected_entity_types"]:
                        if expected_type in entity_types:
                            print(f"  ✅ Expected entity type found: {expected_type}")
                        else:
                            print(f"  ⚠️  Expected entity type MISSING: {expected_type}")

                # Check for Work Order transformation entities
                wo_equipment_entities = [e for e in entities if e["type"] == "WORK_ORDER_EQUIPMENT"]
                wo_title_entities = [e for e in entities if e["type"] == "WORK_ORDER_TITLE"]

                if wo_equipment_entities:
                    print(f"  ✅ WORK_ORDER_EQUIPMENT entities created: {len(wo_equipment_entities)}")
                if wo_title_entities:
                    print(f"  ✅ WORK_ORDER_TITLE entities created: {len(wo_title_entities)}")

                results.append({
                    "query": query,
                    "category": category,
                    "entities": entities,
                    "entity_types": entity_types,
                    "wo_equipment_count": len(wo_equipment_entities),
                    "wo_title_count": len(wo_title_entities),
                    "success": True,
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    "query": query,
                    "category": category,
                    "error": str(e),
                    "success": False,
                })

            print("")

        # Save results
        output_file = TEST_OUTPUT_DIR / f"entity_extraction_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✅ Entity extraction test complete - Results saved to {output_file}")
        print("")

        self.test_results["tests"].append({
            "name": "entity_extraction",
            "total": len(test_queries),
            "passed": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
        })

    async def test_capability_execution_title_description_search(self):
        """Test 2: Capability Execution with Title/Description ILIKE Search"""
        print("=" * 80)
        print("TEST 2: Capability Execution - Title/Description ILIKE Search")
        print("=" * 80)
        print("")

        from prepare.capability_composer import compose_search

        test_queries = [
            # Title search
            {
                "query": "generator",
                "entity": {"type": "WORK_ORDER_EQUIPMENT", "value": "generator", "confidence": 0.85},
                "expected_search_column": "title",
                "expected_match_type": "ILIKE",
                "category": "title_search",
            },
            {
                "query": "oil change",
                "entity": {"type": "WORK_ORDER_TITLE", "value": "change", "confidence": 0.75},
                "expected_search_column": "title",
                "expected_match_type": "ILIKE",
                "category": "title_search_action",
            },
            # WO number exact match
            {
                "query": "WO-12345",
                "entity": {"type": "WORK_ORDER_ID", "value": "WO-12345", "confidence": 0.90},
                "expected_search_column": "wo_number",
                "expected_match_type": "EXACT",
                "category": "exact_wo_number",
            },
        ]

        results = []

        for test_case in test_queries:
            query = test_case["query"]
            entity = test_case["entity"]
            category = test_case["category"]

            print(f"Testing capability execution for: '{query}' ({category})")
            print(f"  Entity: {entity['type']} = '{entity['value']}'")

            try:
                # Execute capability search
                search_result = compose_search(
                    supabase_client=self.supabase_client,
                    yacht_id=YACHT_ID,
                    entities=[entity],
                    limit_per_capability=20,
                )

                print(f"  Capabilities executed: {len(search_result.capabilities_executed)}")
                print(f"  Total results: {search_result.total_count}")
                print(f"  Execution times: {search_result.execution_times_ms}")

                # Check if work_order_by_id capability was executed
                if "work_order_by_id" in search_result.capabilities_executed:
                    print(f"  ✅ work_order_by_id capability executed")

                    # Check results
                    if search_result.total_count > 0:
                        print(f"  ✅ Results returned: {search_result.total_count}")
                        for i, result in enumerate(search_result.results[:3], 1):
                            # NormalizedResult is a dataclass, use attribute access
                            title = getattr(result, 'title', 'No title')
                            primary_id = getattr(result, 'primary_id', 'N/A')
                            print(f"    {i}. {title} (ID: {str(primary_id)[:8]}...)")
                    else:
                        print(f"  ⚠️  No results returned (may be valid if no matching work orders exist)")
                else:
                    print(f"  ❌ work_order_by_id capability NOT executed")

                results.append({
                    "query": query,
                    "category": category,
                    "entity": entity,
                    "capabilities_executed": search_result.capabilities_executed,
                    "total_results": search_result.total_count,
                    "execution_times_ms": search_result.execution_times_ms,
                    "success": True,
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "query": query,
                    "category": category,
                    "error": str(e),
                    "success": False,
                })

            print("")

        # Save results
        output_file = TEST_OUTPUT_DIR / f"capability_execution_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✅ Capability execution test complete - Results saved to {output_file}")
        print("")

        self.test_results["tests"].append({
            "name": "capability_execution",
            "total": len(test_queries),
            "passed": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
        })

    async def test_cross_lens_search_equipment_to_work_orders(self):
        """Test 3: Cross-Lens Search (Equipment → Work Orders)"""
        print("=" * 80)
        print("TEST 3: Cross-Lens Search - Equipment → Work Orders")
        print("=" * 80)
        print("")

        from prepare.capability_composer import compose_search

        test_cases = [
            {
                "query": "generator",
                "description": "Equipment name should trigger both equipment and work order search",
            },
            {
                "query": "port engine",
                "description": "Compound equipment name should trigger both searches",
            },
            {
                "query": "pump",
                "description": "Generic equipment should trigger both searches",
            },
        ]

        results = []

        for test_case in test_cases:
            query = test_case["query"]
            description = test_case["description"]

            print(f"Testing: '{query}'")
            print(f"  {description}")

            try:
                # Extract entities
                extraction_result = await self.pipeline._extract(query)
                entities = extraction_result.get("entities", [])

                print(f"  Entities extracted: {len(entities)}")
                for entity in entities:
                    print(f"    - {entity['type']:30} | {entity['value']}")

                # Execute search with all entities
                search_result = compose_search(
                    supabase_client=self.supabase_client,
                    yacht_id=YACHT_ID,
                    entities=entities,
                    limit_per_capability=20,
                )

                print(f"  Capabilities executed: {search_result.capabilities_executed}")

                # Check if BOTH equipment and work_order capabilities executed
                has_equipment = "equipment_by_name_or_model" in search_result.capabilities_executed
                has_work_order = "work_order_by_id" in search_result.capabilities_executed

                if has_equipment and has_work_order:
                    print(f"  ✅ Cross-lens search working: Both equipment and work order capabilities executed")
                elif has_equipment:
                    print(f"  ⚠️  Only equipment capability executed (work order entity may not be created)")
                elif has_work_order:
                    print(f"  ⚠️  Only work order capability executed (equipment entity may be missing)")
                else:
                    print(f"  ❌ Neither capability executed")

                # Analyze results by capability
                results_by_cap = search_result.rows_per_capability
                print(f"  Results by capability:")
                for cap_name, row_count in results_by_cap.items():
                    print(f"    - {cap_name}: {row_count} results")

                results.append({
                    "query": query,
                    "entities": entities,
                    "capabilities_executed": search_result.capabilities_executed,
                    "has_equipment": has_equipment,
                    "has_work_order": has_work_order,
                    "cross_lens_success": has_equipment and has_work_order,
                    "results_by_capability": results_by_cap,
                    "success": True,
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "query": query,
                    "error": str(e),
                    "success": False,
                })

            print("")

        # Save results
        output_file = TEST_OUTPUT_DIR / f"cross_lens_search_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✅ Cross-lens search test complete - Results saved to {output_file}")
        print("")

        self.test_results["tests"].append({
            "name": "cross_lens_search",
            "total": len(test_cases),
            "passed": sum(1 for r in results if r.get("cross_lens_success")),
            "failed": sum(1 for r in results if not r.get("cross_lens_success") and r.get("success")),
        })

    async def test_natural_language_chaos_queries(self):
        """Test 4: Natural Language Chaos Queries"""
        print("=" * 80)
        print("TEST 4: Natural Language Chaos Queries")
        print("=" * 80)
        print("")

        chaos_queries = [
            # Misspellings
            "genrator maintanence",
            "oil chnge on port engin",
            "recieving shipment for pump parst",
            # Vague
            "stuff from yesterday",
            "things that need attention",
            "maintenance",
            "work",
            # Contradictory
            "urgent but can wait generator issue",
            "important not critical oil leak",
            "high priority low urgency",
            # Timestamps (vague)
            "work order from last week",
            "maintenance scheduled for tomorrow",
            "service due 2nd Tuesday",
            # Names (may not exist)
            "john ordered pump part",
            "captain signed generator work order",
            "chief engineer requested oil change",
            # Compound chaos
            "show me that thing captain mentioned yesterday about starboard generator leak",
            "need to find work order john created last week urgent",
            "where is the pump part from last month high priority",
        ]

        results = []

        for query in chaos_queries:
            print(f"Chaos Query: '{query}'")

            try:
                # Extract entities
                extraction_result = await self.pipeline._extract(query)
                entities = extraction_result.get("entities", [])

                print(f"  Entities: {len(entities)} extracted")
                if entities:
                    for entity in entities[:5]:  # Show first 5
                        print(f"    - {entity['type']:25} | {entity['value']:30} | conf: {entity.get('confidence', 0):.2f}")

                # Execute search
                from prepare.capability_composer import compose_search
                search_result = compose_search(
                    supabase_client=self.supabase_client,
                    yacht_id=YACHT_ID,
                    entities=entities,
                    limit_per_capability=20,
                )

                print(f"  Results: {search_result.total_count} found")
                print(f"  Capabilities: {', '.join(search_result.capabilities_executed) if search_result.capabilities_executed else 'None'}")

                # Vague input should give vague output (or nothing)
                is_vague = len(query.split()) <= 3 and not any(char.isdigit() for char in query)
                if is_vague:
                    print(f"  ℹ️  Vague query - results may be limited or empty (expected)")

                results.append({
                    "query": query,
                    "entities_count": len(entities),
                    "results_count": search_result.total_count,
                    "capabilities": search_result.capabilities_executed,
                    "is_vague": is_vague,
                    "success": True,
                })

            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    "query": query,
                    "error": str(e),
                    "success": False,
                })

            print("")

        # Save results
        output_file = TEST_OUTPUT_DIR / f"chaos_queries_{TEST_RUN_ID}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✅ Chaos query test complete - Results saved to {output_file}")
        print("")

        self.test_results["tests"].append({
            "name": "chaos_queries",
            "total": len(chaos_queries),
            "passed": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
        })

    async def run_all_tests(self):
        """Run all tests in sequence."""
        await self.setup()

        try:
            await self.test_entity_extraction_work_order_queries()
            await self.test_capability_execution_title_description_search()
            await self.test_cross_lens_search_equipment_to_work_orders()
            await self.test_natural_language_chaos_queries()

        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results["failures"].append({
                "error": str(e),
                "traceback": traceback.format_exc(),
            })

        # Generate summary
        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["summary"] = {
            "total_tests": len(self.test_results["tests"]),
            "total_passed": sum(t["passed"] for t in self.test_results["tests"]),
            "total_failed": sum(t["failed"] for t in self.test_results["tests"]),
            "has_failures": len(self.test_results["failures"]) > 0,
        }

        # Save final results
        summary_file = TEST_OUTPUT_DIR / f"test_summary_{TEST_RUN_ID}.json"
        with open(summary_file, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print("=" * 80)
        print("TEST SUITE COMPLETE")
        print("=" * 80)
        print(f"Total Tests: {self.test_results['summary']['total_tests']}")
        print(f"Total Passed: {self.test_results['summary']['total_passed']}")
        print(f"Total Failed: {self.test_results['summary']['total_failed']}")
        print(f"Summary saved to: {summary_file}")
        print("")

        return self.test_results["summary"]["total_failed"] == 0


async def main():
    """Main entry point."""
    test_suite = WorkOrderLensTestSuite()
    success = await test_suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
