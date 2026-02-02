#!/usr/bin/env python3
"""
Work Order Lens - Stress & Performance Tests
============================================

Tests Work Order Lens under load:
1. High-volume concurrent queries (100+ simultaneous)
2. Response time validation (P95 < 500ms)
3. Success rate validation (>99%)
4. Memory/resource stability
5. Error handling under pressure

Success Criteria:
- P95 response time < 500ms
- P99 response time < 1000ms
- Success rate > 99%
- Zero memory leaks
- Zero crashes under load
"""

import sys
import os
import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics
import concurrent.futures

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test configuration
CONCURRENT_USERS = 50  # Simulate 50 concurrent users
QUERIES_PER_USER = 10  # Each user makes 10 queries
TOTAL_QUERIES = CONCURRENT_USERS * QUERIES_PER_USER

# Success thresholds
TARGET_P95_MS = 500
TARGET_P99_MS = 1000
TARGET_SUCCESS_RATE = 0.99

# Test results directory
TEST_OUTPUT_DIR = Path(__file__).parent / "test_results" / "work_order_stress"
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timestamp for this test run
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


class WorkOrderStressTests:
    """Stress test suite for Work Order Lens."""

    def __init__(self):
        self.test_results = {
            "test_run_id": TEST_RUN_ID,
            "start_time": datetime.now().isoformat(),
            "config": {
                "concurrent_users": CONCURRENT_USERS,
                "queries_per_user": QUERIES_PER_USER,
                "total_queries": TOTAL_QUERIES,
            },
            "timings": [],
            "errors": [],
            "summary": {},
        }
        self.pipeline = None
        self.supabase_client = None

    async def setup(self):
        """Initialize test environment."""
        print("=" * 80)
        print("WORK ORDER LENS - STRESS & PERFORMANCE TEST SUITE")
        print("=" * 80)
        print(f"Test Run ID: {TEST_RUN_ID}")
        print(f"Concurrent Users: {CONCURRENT_USERS}")
        print(f"Queries Per User: {QUERIES_PER_USER}")
        print(f"Total Queries: {TOTAL_QUERIES}")
        print(f"Target P95: < {TARGET_P95_MS}ms")
        print(f"Target P99: < {TARGET_P99_MS}ms")
        print(f"Target Success Rate: > {TARGET_SUCCESS_RATE * 100}%")
        print(f"Output Directory: {TEST_OUTPUT_DIR}")
        print("")

        # Initialize pipeline
        from pipeline_v1 import Pipeline
        from handlers.db_client import get_supabase_client

        print("Initializing pipeline...")
        self.pipeline = Pipeline(yacht_id="85fe1119-b04c-41ac-80f1-829d23322598")
        self.supabase_client = get_supabase_client("85fe1119-b04c-41ac-80f1-829d23322598")
        print("✅ Pipeline initialized")
        print("")

    # Test queries covering various scenarios
    TEST_QUERIES = [
        "generator",
        "port engine maintenance",
        "oil change",
        "pump repair",
        "scheduled maintenance",
        "generator leak",
        "hydraulic system",
        "fuel filter replacement",
        "cooling system check",
        "electrical fault",
        "bearing replacement",
        "routine inspection",
        "emergency repair",
        "valve service",
        "compressor maintenance",
        "WO-12345",
        "urgent generator service",
        "starboard engine oil leak",
        "bilge pump failure",
        "air conditioning maintenance",
    ]

    async def execute_single_query(self, query: str, query_id: int) -> Dict[str, Any]:
        """
        Execute a single query and measure performance.

        Returns:
            Dict with timing, success, and result info
        """
        start_time = time.time()
        success = False
        error = None
        result_count = 0

        try:
            # Execute query through pipeline
            result = await self.pipeline.process_query(query)

            # Extract results
            if result and isinstance(result, dict):
                capabilities = result.get("capabilities_executed", [])
                results = result.get("results", [])
                result_count = len(results)
                success = True
            else:
                error = "Invalid result format"

        except Exception as e:
            error = str(e)
            success = False

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        return {
            "query_id": query_id,
            "query": query,
            "success": success,
            "elapsed_ms": elapsed_ms,
            "result_count": result_count,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

    async def run_user_workload(self, user_id: int) -> List[Dict]:
        """
        Simulate a single user making multiple queries.

        Returns:
            List of query results
        """
        results = []

        for i in range(QUERIES_PER_USER):
            # Select query (round-robin through test queries)
            query_idx = (user_id * QUERIES_PER_USER + i) % len(self.TEST_QUERIES)
            query = self.TEST_QUERIES[query_idx]

            # Execute query
            query_id = user_id * QUERIES_PER_USER + i
            result = await self.execute_single_query(query, query_id)
            results.append(result)

            # Small delay between queries (simulate human behavior)
            await asyncio.sleep(0.1)

        return results

    async def run_stress_test(self):
        """Run stress test with concurrent users."""
        print("=" * 80)
        print("RUNNING STRESS TEST")
        print("=" * 80)
        print(f"Launching {CONCURRENT_USERS} concurrent users...")
        print("")

        start_time = time.time()

        # Create tasks for all concurrent users
        tasks = []
        for user_id in range(CONCURRENT_USERS):
            task = self.run_user_workload(user_id)
            tasks.append(task)

        # Execute all tasks concurrently
        all_results = await asyncio.gather(*tasks)

        # Flatten results
        for user_results in all_results:
            self.test_results["timings"].extend(user_results)
            for result in user_results:
                if not result["success"]:
                    self.test_results["errors"].append({
                        "query": result["query"],
                        "error": result["error"],
                        "query_id": result["query_id"]
                    })

        end_time = time.time()
        total_elapsed = end_time - start_time

        print(f"✅ Stress test complete in {total_elapsed:.2f}s")
        print("")

        # Calculate statistics
        self._calculate_statistics()
        self._print_summary()

    def _calculate_statistics(self):
        """Calculate performance statistics."""
        timings = [r["elapsed_ms"] for r in self.test_results["timings"]]
        successes = [r["success"] for r in self.test_results["timings"]]

        total_queries = len(timings)
        successful_queries = sum(successes)
        failed_queries = total_queries - successful_queries

        success_rate = successful_queries / total_queries if total_queries > 0 else 0

        # Only calculate percentiles for successful queries
        successful_timings = [r["elapsed_ms"] for r in self.test_results["timings"] if r["success"]]

        if successful_timings:
            sorted_timings = sorted(successful_timings)
            p50 = statistics.median(sorted_timings)
            p95_idx = int(len(sorted_timings) * 0.95)
            p99_idx = int(len(sorted_timings) * 0.99)
            p95 = sorted_timings[p95_idx] if p95_idx < len(sorted_timings) else sorted_timings[-1]
            p99 = sorted_timings[p99_idx] if p99_idx < len(sorted_timings) else sorted_timings[-1]
            mean = statistics.mean(successful_timings)
            min_time = min(successful_timings)
            max_time = max(successful_timings)
        else:
            p50 = p95 = p99 = mean = min_time = max_time = 0

        self.test_results["summary"] = {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate": success_rate,
            "timings": {
                "min_ms": min_time,
                "max_ms": max_time,
                "mean_ms": mean,
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
            },
            "targets": {
                "p95_target_ms": TARGET_P95_MS,
                "p95_met": p95 < TARGET_P95_MS,
                "p99_target_ms": TARGET_P99_MS,
                "p99_met": p99 < TARGET_P99_MS,
                "success_rate_target": TARGET_SUCCESS_RATE,
                "success_rate_met": success_rate > TARGET_SUCCESS_RATE,
            }
        }

    def _print_summary(self):
        """Print test summary."""
        print("=" * 80)
        print("STRESS TEST SUMMARY")
        print("=" * 80)

        summary = self.test_results["summary"]
        timings = summary["timings"]
        targets = summary["targets"]

        print(f"Total Queries: {summary['total_queries']}")
        print(f"Successful: {summary['successful_queries']} ✅")
        print(f"Failed: {summary['failed_queries']} {'❌' if summary['failed_queries'] > 0 else '✅'}")
        print(f"Success Rate: {summary['success_rate']*100:.2f}% {'✅' if targets['success_rate_met'] else '❌'}")
        print("")

        print("Response Times:")
        print(f"  Min:  {timings['min_ms']:.2f}ms")
        print(f"  Mean: {timings['mean_ms']:.2f}ms")
        print(f"  P50:  {timings['p50_ms']:.2f}ms")
        print(f"  P95:  {timings['p95_ms']:.2f}ms {'✅' if targets['p95_met'] else '❌'} (target: < {TARGET_P95_MS}ms)")
        print(f"  P99:  {timings['p99_ms']:.2f}ms {'✅' if targets['p99_met'] else '❌'} (target: < {TARGET_P99_MS}ms)")
        print(f"  Max:  {timings['max_ms']:.2f}ms")
        print("")

        # Top errors
        if self.test_results["errors"]:
            print(f"Top Errors ({len(self.test_results['errors'])} total):")
            error_counts = {}
            for error in self.test_results["errors"]:
                err_msg = error["error"]
                error_counts[err_msg] = error_counts.get(err_msg, 0) + 1

            for err_msg, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {err_msg}: {count} occurrences")
            print("")

        # Save detailed results
        self.test_results["end_time"] = datetime.now().isoformat()

        summary_file = TEST_OUTPUT_DIR / f"stress_test_{TEST_RUN_ID}.json"
        with open(summary_file, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print(f"💾 Detailed results saved to: {summary_file}")
        print("")

        # Final verdict
        all_targets_met = (
            targets["p95_met"] and
            targets["p99_met"] and
            targets["success_rate_met"]
        )

        if all_targets_met:
            print("=" * 80)
            print("✅ VERDICT: ALL PERFORMANCE TARGETS MET")
            print("=" * 80)
        else:
            print("=" * 80)
            print("❌ VERDICT: SOME PERFORMANCE TARGETS NOT MET")
            print("=" * 80)
            if not targets["p95_met"]:
                print(f"  ❌ P95 response time: {timings['p95_ms']:.2f}ms > {TARGET_P95_MS}ms")
            if not targets["p99_met"]:
                print(f"  ❌ P99 response time: {timings['p99_ms']:.2f}ms > {TARGET_P99_MS}ms")
            if not targets["success_rate_met"]:
                print(f"  ❌ Success rate: {summary['success_rate']*100:.2f}% < {TARGET_SUCCESS_RATE*100}%")

        print("")

        return all_targets_met


async def main():
    """Main test execution."""
    tests = WorkOrderStressTests()
    await tests.setup()
    await tests.run_stress_test()


if __name__ == "__main__":
    asyncio.run(main())
