"""
Stress Test Runner
==================
Executes load tests against production endpoints with full logging.
"""

import asyncio
import aiohttp
import json
import time
import random
import os
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    EXTRACT_URL, SEARCH_URL, HEALTH_URL, SERVICE_KEY, TEST_YACHT_ID,
    VALID_LANES, LOG_DIR, MIN_CONCURRENCY, MAX_CONCURRENCY
)
from query_generator import (
    get_query_for_lane, get_random_query, get_search_query,
    get_polite_prefix_query, get_non_domain_query,
    generate_random_session_id, generate_random_user_id, generate_random_role
)

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

class StressTestRunner:
    def __init__(self, day: int = 1):
        self.day = day
        self.results = []
        self.metrics = {
            "total_calls": 0,
            "success": 0,
            "failures": 0,
            "lane_distribution": defaultdict(int),
            "latencies": [],
            "errors": defaultdict(int),
            "http_status": defaultdict(int),
            "infra_errors": 0,
            "logic_errors": 0,
        }
        self.violations = []
        self.log_file = os.path.join(LOG_DIR, f"day{day}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")

    def log_result(self, result: Dict):
        """Append result to log file."""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(result) + '\n')

    async def call_extract(self, session: aiohttp.ClientSession, query: str, expected_lane: str = None) -> Dict:
        """Call /extract endpoint and return result."""
        start = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/extract",
            "query": query,
            "expected_lane": expected_lane,
            "session_id": generate_random_session_id(),
            "user_id": generate_random_user_id(),
        }

        try:
            async with session.post(
                EXTRACT_URL,
                json={"query": query},
                headers={
                    "Authorization": f"Bearer {SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result["http_status"] = resp.status
                result["latency_ms"] = (time.time() - start) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    result["lane"] = data.get("lane")
                    result["lane_reason"] = data.get("lane_reason")
                    result["intent"] = data.get("intent")
                    result["intent_confidence"] = data.get("intent_confidence")
                    result["entities"] = len(data.get("entities", []))
                    result["success"] = True

                    # Check lane validity
                    if result["lane"] not in VALID_LANES:
                        result["violation"] = f"Invalid lane: {result['lane']}"
                        self.violations.append(result)

                    # Check expected lane match
                    if expected_lane and result["lane"] != expected_lane:
                        result["lane_mismatch"] = True
                else:
                    result["success"] = False
                    result["error"] = f"HTTP {resp.status}"
                    try:
                        result["error_body"] = await resp.text()
                    except:
                        pass

        except asyncio.TimeoutError:
            result["success"] = False
            result["error"] = "timeout"
            result["latency_ms"] = (time.time() - start) * 1000
        except aiohttp.ClientError as e:
            result["success"] = False
            result["error"] = f"client_error: {str(e)}"
            result["latency_ms"] = (time.time() - start) * 1000
        except Exception as e:
            result["success"] = False
            result["error"] = f"exception: {str(e)}"
            result["latency_ms"] = (time.time() - start) * 1000

        self.log_result(result)
        return result

    async def call_search(self, session: aiohttp.ClientSession, query: str) -> Dict:
        """Call /v2/search endpoint and return result."""
        start = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": "/v2/search",
            "query": query,
            "yacht_id": TEST_YACHT_ID,
            "session_id": generate_random_session_id(),
            "user_id": generate_random_user_id(),
            "role": generate_random_role(),
        }

        try:
            async with session.post(
                SEARCH_URL,
                json={
                    "query": query,
                    "yacht_id": TEST_YACHT_ID,
                    "session_id": result["session_id"],
                },
                headers={
                    "Authorization": f"Bearer {SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                result["http_status"] = resp.status
                result["latency_ms"] = (time.time() - start) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    result["success"] = True
                    result["result_count"] = len(data.get("results", []))
                    result["entities"] = len(data.get("entities", []))
                    result["rpc_executed"] = "results" in data  # Indicates RPC was called
                else:
                    result["success"] = False
                    result["error"] = f"HTTP {resp.status}"
                    try:
                        error_body = await resp.json()
                        result["error_message"] = error_body.get("error", str(error_body))
                    except:
                        result["error_body"] = await resp.text()

        except asyncio.TimeoutError:
            result["success"] = False
            result["error"] = "timeout"
            result["latency_ms"] = (time.time() - start) * 1000
        except aiohttp.ClientError as e:
            result["success"] = False
            result["error"] = f"client_error: {str(e)}"
            result["latency_ms"] = (time.time() - start) * 1000
        except Exception as e:
            result["success"] = False
            result["error"] = f"exception: {str(e)}"
            result["latency_ms"] = (time.time() - start) * 1000

        self.log_result(result)
        return result

    async def run_batch(self, session: aiohttp.ClientSession, batch_size: int, endpoint: str = "extract"):
        """Run a batch of concurrent requests."""
        tasks = []
        for _ in range(batch_size):
            if endpoint == "extract":
                query, expected = get_random_query()
                tasks.append(self.call_extract(session, query, expected))
            else:
                query = get_search_query()
                tasks.append(self.call_search(session, query))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def update_metrics(self, results: List[Dict]):
        """Update running metrics from results."""
        for r in results:
            if isinstance(r, Exception):
                self.metrics["failures"] += 1
                self.metrics["errors"]["exception"] += 1
                continue

            self.metrics["total_calls"] += 1
            self.metrics["http_status"][r.get("http_status", "unknown")] += 1

            if r.get("success"):
                self.metrics["success"] += 1
                self.metrics["latencies"].append(r.get("latency_ms", 0))
                if r.get("lane"):
                    self.metrics["lane_distribution"][r["lane"]] += 1
            else:
                self.metrics["failures"] += 1
                error = r.get("error", "unknown")
                self.metrics["errors"][error] += 1

                # Classify as infra vs logic error
                if any(x in str(error).lower() for x in ["timeout", "502", "503", "connection", "client_error"]):
                    self.metrics["infra_errors"] += 1
                else:
                    self.metrics["logic_errors"] += 1

    async def run_load_test(self, total_calls: int, endpoint: str = "extract"):
        """Run load test with variable concurrency."""
        print(f"\n{'='*60}")
        print(f" LOAD TEST: {endpoint.upper()} ({total_calls} calls)")
        print(f"{'='*60}\n")

        async with aiohttp.ClientSession() as session:
            remaining = total_calls
            batch_num = 0

            while remaining > 0:
                # Variable concurrency
                concurrency = random.randint(MIN_CONCURRENCY, MAX_CONCURRENCY)
                batch_size = min(concurrency, remaining)

                batch_num += 1
                print(f"  Batch {batch_num}: {batch_size} concurrent requests...", end=" ", flush=True)

                results = await self.run_batch(session, batch_size, endpoint)
                self.update_metrics(results)

                successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
                print(f"Done ({successes}/{batch_size} success)")

                remaining -= batch_size

                # Variable delay between batches (simulate real traffic)
                delay = random.uniform(0.5, 3.0)
                await asyncio.sleep(delay)

        self.print_metrics()

    def print_metrics(self):
        """Print current metrics summary."""
        print(f"\n{'='*60}")
        print(" METRICS SUMMARY")
        print(f"{'='*60}")
        print(f"  Total Calls: {self.metrics['total_calls']}")
        print(f"  Success: {self.metrics['success']}")
        print(f"  Failures: {self.metrics['failures']}")

        if self.metrics["total_calls"] > 0:
            success_rate = self.metrics["success"] / self.metrics["total_calls"] * 100
            print(f"  Success Rate: {success_rate:.2f}%")

        print(f"\n  Lane Distribution:")
        for lane, count in sorted(self.metrics["lane_distribution"].items()):
            print(f"    {lane}: {count}")

        print(f"\n  HTTP Status Codes:")
        for status, count in sorted(self.metrics["http_status"].items()):
            print(f"    {status}: {count}")

        if self.metrics["latencies"]:
            latencies = sorted(self.metrics["latencies"])
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else latencies[-1]
            print(f"\n  Latency (ms):")
            print(f"    P50: {p50:.0f}")
            print(f"    P95: {p95:.0f}")
            print(f"    P99: {p99:.0f}")

        if self.metrics["errors"]:
            print(f"\n  Errors:")
            for error, count in sorted(self.metrics["errors"].items(), key=lambda x: -x[1])[:10]:
                print(f"    {error}: {count}")

        print(f"\n  Infra Errors: {self.metrics['infra_errors']}")
        print(f"  Logic Errors: {self.metrics['logic_errors']}")

        if self.violations:
            print(f"\n  VIOLATIONS: {len(self.violations)}")
            for v in self.violations[:5]:
                print(f"    - {v.get('violation')}: {v.get('query', '')[:50]}")

    def save_metrics(self):
        """Save metrics to file."""
        metrics_file = os.path.join(LOG_DIR, f"metrics_day{self.day}.json")
        with open(metrics_file, 'w') as f:
            # Convert defaultdicts to regular dicts for JSON
            metrics_copy = {
                k: dict(v) if isinstance(v, defaultdict) else v
                for k, v in self.metrics.items()
            }
            json.dump(metrics_copy, f, indent=2)
        print(f"\n  Metrics saved to: {metrics_file}")


async def run_lane_verification(runner: StressTestRunner):
    """Run lane verification suite."""
    print(f"\n{'='*60}")
    print(" LANE VERIFICATION SUITE")
    print(f"{'='*60}\n")

    results = {
        "BLOCKED": {"total": 0, "correct": 0, "queries": []},
        "RULES_ONLY": {"total": 0, "correct": 0, "queries": []},
        "NO_LLM": {"total": 0, "correct": 0, "queries": []},
        "GPT": {"total": 0, "correct": 0, "queries": []},
    }

    async with aiohttp.ClientSession() as session:
        # Test each lane
        for lane, count in [("BLOCKED", 30), ("RULES_ONLY", 50), ("NO_LLM", 200), ("GPT", 100)]:
            print(f"  Testing {lane} ({count} queries)...", end=" ", flush=True)

            for _ in range(count):
                query = get_query_for_lane(lane)
                result = await runner.call_extract(session, query, lane)
                runner.update_metrics([result])

                results[lane]["total"] += 1
                if result.get("lane") == lane:
                    results[lane]["correct"] += 1
                else:
                    results[lane]["queries"].append({
                        "query": query,
                        "expected": lane,
                        "got": result.get("lane"),
                        "reason": result.get("lane_reason"),
                    })

                await asyncio.sleep(0.1)  # Rate limiting

            accuracy = results[lane]["correct"] / results[lane]["total"] * 100
            print(f"{results[lane]['correct']}/{results[lane]['total']} ({accuracy:.1f}%)")

    # Summary
    print(f"\n  LANE VERIFICATION RESULTS:")
    all_pass = True
    for lane, data in results.items():
        accuracy = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        status = "PASS" if accuracy >= 95 else "FAIL"
        if accuracy < 95:
            all_pass = False
        print(f"    {lane}: {accuracy:.1f}% ({status})")

        # Log failures
        if data["queries"]:
            print(f"      Failures ({len(data['queries'])}):")
            for q in data["queries"][:3]:
                print(f"        '{q['query'][:40]}...' → {q['got']} (expected {q['expected']})")

    return results, all_pass


async def run_polite_prefix_test(runner: StressTestRunner):
    """Test polite prefix routing (must go to RULES_ONLY)."""
    print(f"\n{'='*60}")
    print(" POLITE PREFIX VERIFICATION")
    print(f"{'='*60}\n")

    prefixes = [
        "please ", "can you ", "could you ", "would you ",
        "hey can you ", "I'd like you to ", "I need you to ",
        "pls ", "could you please ", "I want to ",
    ]
    commands = [
        "create work order", "log engine hours", "schedule maintenance",
        "update inventory", "assign task", "add note", "export report",
    ]

    correct = 0
    total = 0
    failures = []

    async with aiohttp.ClientSession() as session:
        for prefix in prefixes:
            for cmd in commands:
                query = prefix + cmd
                result = await runner.call_extract(session, query, "RULES_ONLY")
                runner.update_metrics([result])

                total += 1
                if result.get("lane") == "RULES_ONLY":
                    correct += 1
                else:
                    failures.append({
                        "query": query,
                        "got": result.get("lane"),
                        "reason": result.get("lane_reason"),
                    })

                await asyncio.sleep(0.05)

    accuracy = correct / total * 100 if total > 0 else 0
    status = "PASS" if accuracy >= 95 else "FAIL"
    print(f"  Polite Prefix Routing: {correct}/{total} ({accuracy:.1f}%) - {status}")

    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures[:5]:
            print(f"    '{f['query']}' → {f['got']} ({f['reason']})")

    return accuracy >= 95, failures


async def run_non_domain_test(runner: StressTestRunner):
    """Test non-domain blocking."""
    print(f"\n{'='*60}")
    print(" NON-DOMAIN BLOCKING VERIFICATION")
    print(f"{'='*60}\n")

    queries = [
        "what is the weather", "tell me a joke", "latest news",
        "calculate 2+2", "who is the president", "what time is it",
        "stock market today", "bitcoin price", "translate hello",
        "what is quantum physics", "explain relativity",
        "how are you", "what's up", "hello there",
    ]

    correct = 0
    total = 0
    failures = []

    async with aiohttp.ClientSession() as session:
        for query in queries:
            result = await runner.call_extract(session, query, "BLOCKED")
            runner.update_metrics([result])

            total += 1
            if result.get("lane") == "BLOCKED":
                correct += 1
            else:
                failures.append({
                    "query": query,
                    "got": result.get("lane"),
                    "reason": result.get("lane_reason"),
                })

            await asyncio.sleep(0.05)

    accuracy = correct / total * 100 if total > 0 else 0
    status = "PASS" if accuracy >= 95 else "FAIL"
    print(f"  Non-Domain Blocking: {correct}/{total} ({accuracy:.1f}%) - {status}")

    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures:
            print(f"    '{f['query']}' → {f['got']} ({f['reason']})")

    return accuracy >= 95, failures


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, default=1)
    parser.add_argument("--calls", type=int, default=500)
    parser.add_argument("--endpoint", choices=["extract", "search", "both"], default="both")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    runner = StressTestRunner(day=args.day)

    async def main():
        if args.verify_only:
            await run_lane_verification(runner)
            await run_polite_prefix_test(runner)
            await run_non_domain_test(runner)
        else:
            if args.endpoint in ["extract", "both"]:
                await runner.run_load_test(args.calls, "extract")
            if args.endpoint in ["search", "both"]:
                await runner.run_load_test(args.calls // 2, "search")

            # Always run verification
            await run_lane_verification(runner)
            await run_polite_prefix_test(runner)
            await run_non_domain_test(runner)

        runner.save_metrics()

    asyncio.run(main())
