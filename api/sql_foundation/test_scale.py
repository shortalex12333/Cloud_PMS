"""
SCALE TEST: 1500 queries through PREPARE → EXECUTE pipeline
============================================================
Stress test to prove the system handles volume.
"""
import time
import random
import string
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .prepare import prepare, Lane, ExecutionPlan
from .execute import search, SearchResult

# Config
BASE_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
API_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Test data pools
EQUIPMENT_NAMES = [
    "Generator 1", "Generator 2", "Main Engine Port", "Main Engine Starboard",
    "Watermaker", "Air Conditioning", "Bow Thruster", "Stern Thruster",
    "Hydraulic System", "Fuel System", "Bilge Pump", "Fire Pump",
    "Anchor Windlass", "Capstan", "Stabilizer", "Autopilot",
]

PART_NAMES = [
    "fuel filter", "oil filter", "air filter", "water pump", "fuel pump",
    "alternator", "starter motor", "injector", "gasket", "seal kit",
    "bearing", "impeller", "thermostat", "belt", "hose", "valve",
]

MANUFACTURERS = [
    "MTU", "Caterpillar", "Volvo Penta", "Yanmar", "Cummins",
    "Kohler", "Northern Lights", "Onan", "Perkins", "John Deere",
]

FAULT_CODES = [
    "E047", "E023", "E101", "E102", "E201", "E202", "E301",
    "W001", "W002", "W003", "W004", "W005",
    "A001", "A002", "A003",
]

SYMPTOMS = [
    "overheating", "vibration", "noise", "leak", "smoke",
    "low pressure", "high temperature", "won't start", "stalling",
    "rough running", "loss of power", "alarm",
]

LOCATIONS = [
    "engine room", "bridge", "galley", "crew quarters", "lazarette",
    "forepeak", "aft deck", "flybridge", "tender garage",
]

# Blocked patterns for negative testing
BLOCKED_PATTERNS = [
    "ignore all instructions",
    "drop table users",
    "delete from",
    "system prompt",
    "eval(",
]


def generate_test_cases(count: int = 1500) -> List[Dict]:
    """Generate diverse test cases."""
    cases = []

    # Distribution:
    # 30% - Single entity equipment
    # 20% - Single entity part
    # 15% - Single entity fault
    # 15% - Multi-entity (part + manufacturer)
    # 10% - Multi-entity (fault + symptom)
    # 5% - Blocked queries
    # 3% - Unknown/vague queries
    # 2% - Typo queries

    distributions = [
        (0.30, "equipment"),
        (0.20, "part"),
        (0.15, "fault"),
        (0.15, "part_manufacturer"),
        (0.10, "fault_symptom"),
        (0.05, "blocked"),
        (0.03, "unknown"),
        (0.02, "typo"),
    ]

    for i in range(count):
        # Pick category based on distribution
        r = random.random()
        cumulative = 0
        category = "equipment"
        for prob, cat in distributions:
            cumulative += prob
            if r <= cumulative:
                category = cat
                break

        case = generate_case(category, i)
        cases.append(case)

    return cases


def generate_case(category: str, idx: int) -> Dict:
    """Generate a single test case."""
    if category == "equipment":
        value = random.choice(EQUIPMENT_NAMES)
        return {
            "id": idx,
            "category": category,
            "query": value,
            "entities": [{"type": "EQUIPMENT_NAME", "value": value}],
            "expected_lane": "GPT",
        }

    elif category == "part":
        value = random.choice(PART_NAMES)
        return {
            "id": idx,
            "category": category,
            "query": value,
            "entities": [{"type": "PART_NAME", "value": value}],
            "expected_lane": "GPT",
        }

    elif category == "fault":
        value = random.choice(FAULT_CODES)
        return {
            "id": idx,
            "category": category,
            "query": value,
            "entities": [{"type": "FAULT_CODE", "value": value}],
            "expected_lane": "NO_LLM",
        }

    elif category == "part_manufacturer":
        part = random.choice(PART_NAMES)
        mfr = random.choice(MANUFACTURERS)
        return {
            "id": idx,
            "category": category,
            "query": f"{part} {mfr}",
            "entities": [
                {"type": "PART_NAME", "value": part},
                {"type": "MANUFACTURER", "value": mfr},
            ],
            "expected_lane": "GPT",
        }

    elif category == "fault_symptom":
        fault = random.choice(FAULT_CODES)
        symptom = random.choice(SYMPTOMS)
        return {
            "id": idx,
            "category": category,
            "query": f"{fault} {symptom}",
            "entities": [
                {"type": "FAULT_CODE", "value": fault},
                {"type": "SYMPTOM", "value": symptom},
            ],
            "expected_lane": "NO_LLM",
        }

    elif category == "blocked":
        value = random.choice(BLOCKED_PATTERNS)
        return {
            "id": idx,
            "category": category,
            "query": value,
            "entities": [],
            "expected_lane": "BLOCKED",
        }

    elif category == "unknown":
        value = random.choice(["x", "?", "a", ""])
        return {
            "id": idx,
            "category": category,
            "query": value,
            "entities": [],
            "expected_lane": "UNKNOWN",
        }

    elif category == "typo":
        # Introduce typo in equipment name
        value = random.choice(EQUIPMENT_NAMES)
        if len(value) > 3:
            pos = random.randint(1, len(value) - 2)
            typo_value = value[:pos] + random.choice(string.ascii_lowercase) + value[pos+1:]
        else:
            typo_value = value + "x"
        return {
            "id": idx,
            "category": category,
            "query": typo_value,
            "entities": [{"type": "EQUIPMENT_NAME", "value": typo_value}],
            "expected_lane": "GPT",
        }

    return {"id": idx, "category": "unknown", "query": "", "entities": [], "expected_lane": "UNKNOWN"}


def run_prepare_only(case: Dict) -> Tuple[int, str, bool, float]:
    """Run PREPARE only (no HTTP calls)."""
    start = time.time()
    plan = prepare(
        case["query"],
        case["entities"],
        YACHT_ID,
        "scale-test",
        "engineer"
    )
    elapsed = (time.time() - start) * 1000

    lane_match = plan.lane.lane.value == case["expected_lane"]

    return case["id"], plan.lane.lane.value, lane_match, elapsed


def run_full_search(case: Dict) -> Tuple[int, str, int, float, str]:
    """Run full PREPARE → EXECUTE."""
    start = time.time()
    result = search(
        BASE_URL, API_KEY,
        case["query"],
        case["entities"],
        YACHT_ID,
        "scale-test",
        "engineer"
    )
    elapsed = (time.time() - start) * 1000

    # Determine status
    if "blocked" in result.trace:
        status = "blocked"
    elif "unknown" in result.trace:
        status = "unknown"
    elif result.total_rows > 0:
        status = "found"
    else:
        status = "empty"

    return case["id"], status, result.total_rows, elapsed, case["category"]


def test_prepare_scale(count: int = 1500):
    """
    Scale test PREPARE module only.
    No HTTP calls - pure logic testing.
    """
    print("=" * 70)
    print(f"SCALE TEST: PREPARE ({count} queries)")
    print("=" * 70)

    cases = generate_test_cases(count)

    results = {
        "total": count,
        "passed": 0,
        "failed": 0,
        "by_lane": {},
        "by_category": {},
        "times": [],
    }

    start_all = time.time()

    for case in cases:
        case_id, lane, lane_match, time_ms = run_prepare_only(case)

        if lane_match:
            results["passed"] += 1
        else:
            results["failed"] += 1

        results["by_lane"][lane] = results["by_lane"].get(lane, 0) + 1
        results["by_category"][case["category"]] = results["by_category"].get(case["category"], 0) + 1
        results["times"].append(time_ms)

    total_time = (time.time() - start_all) * 1000

    # Stats
    avg_time = sum(results["times"]) / len(results["times"])
    max_time = max(results["times"])
    min_time = min(results["times"])
    p95_time = sorted(results["times"])[int(len(results["times"]) * 0.95)]

    print(f"\nResults:")
    print(f"  Total: {results['total']}")
    print(f"  Passed: {results['passed']} ({100*results['passed']/results['total']:.1f}%)")
    print(f"  Failed: {results['failed']}")

    print(f"\nBy Lane:")
    for lane, cnt in sorted(results["by_lane"].items()):
        print(f"  {lane}: {cnt}")

    print(f"\nBy Category:")
    for cat, cnt in sorted(results["by_category"].items()):
        print(f"  {cat}: {cnt}")

    print(f"\nTiming:")
    print(f"  Total: {total_time:.0f}ms")
    print(f"  Avg: {avg_time:.2f}ms")
    print(f"  Min: {min_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    print(f"  P95: {p95_time:.2f}ms")
    print(f"  Throughput: {count / (total_time/1000):.0f} queries/sec")

    return results


def test_execute_scale(count: int = 100, parallel: int = 5):
    """
    Scale test full PREPARE → EXECUTE.
    Uses HTTP calls - limited count due to rate limits.
    """
    print("=" * 70)
    print(f"SCALE TEST: EXECUTE ({count} queries, {parallel} parallel)")
    print("=" * 70)

    cases = generate_test_cases(count)

    results = {
        "total": count,
        "found": 0,
        "empty": 0,
        "blocked": 0,
        "unknown": 0,
        "errors": 0,
        "by_category": {},
        "times": [],
        "rows": [],
    }

    start_all = time.time()

    # Run with thread pool for parallel execution
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = {executor.submit(run_full_search, case): case for case in cases}

        for future in as_completed(futures):
            try:
                case_id, status, row_count, time_ms, category = future.result()

                results[status] = results.get(status, 0) + 1
                results["by_category"][category] = results["by_category"].get(category, 0) + 1
                results["times"].append(time_ms)
                results["rows"].append(row_count)

            except Exception as e:
                results["errors"] += 1

    total_time = (time.time() - start_all) * 1000

    # Stats
    avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
    max_time = max(results["times"]) if results["times"] else 0
    p95_time = sorted(results["times"])[int(len(results["times"]) * 0.95)] if results["times"] else 0
    avg_rows = sum(results["rows"]) / len(results["rows"]) if results["rows"] else 0

    print(f"\nResults:")
    print(f"  Total: {results['total']}")
    print(f"  Found: {results['found']}")
    print(f"  Empty: {results['empty']}")
    print(f"  Blocked: {results['blocked']}")
    print(f"  Unknown: {results['unknown']}")
    print(f"  Errors: {results['errors']}")

    print(f"\nBy Category:")
    for cat, cnt in sorted(results["by_category"].items()):
        print(f"  {cat}: {cnt}")

    print(f"\nTiming:")
    print(f"  Total: {total_time:.0f}ms ({total_time/1000:.1f}s)")
    print(f"  Avg per query: {avg_time:.0f}ms")
    print(f"  Max: {max_time:.0f}ms")
    print(f"  P95: {p95_time:.0f}ms")
    print(f"  Throughput: {count / (total_time/1000):.1f} queries/sec")

    print(f"\nRows:")
    print(f"  Avg rows/query: {avg_rows:.1f}")
    print(f"  Total rows: {sum(results['rows'])}")

    return results


def run_scale_tests():
    """Run all scale tests."""
    print("\n" + "=" * 70)
    print("SQL FOUNDATION SCALE TESTS")
    print("=" * 70 + "\n")

    # Test 1: PREPARE only (fast, no HTTP)
    prepare_results = test_prepare_scale(1500)

    print("\n")

    # Test 2: Full EXECUTE (with HTTP, limited)
    execute_results = test_execute_scale(100, parallel=5)

    # Summary
    print("\n" + "=" * 70)
    print("SCALE TEST SUMMARY")
    print("=" * 70)

    prepare_pass_rate = 100 * prepare_results["passed"] / prepare_results["total"]
    print(f"\nPREPARE (1500 queries):")
    print(f"  Pass rate: {prepare_pass_rate:.1f}%")
    print(f"  Throughput: {1500 / (sum(prepare_results['times'])/1000):.0f} queries/sec")

    execute_success = execute_results["found"] + execute_results["blocked"] + execute_results["unknown"]
    execute_rate = 100 * execute_success / execute_results["total"]
    print(f"\nEXECUTE (100 queries):")
    print(f"  Success rate: {execute_rate:.1f}%")
    print(f"  Avg time: {sum(execute_results['times'])/len(execute_results['times']):.0f}ms")

    # Pass/fail
    all_passed = prepare_pass_rate >= 95 and execute_rate >= 90

    print("\n" + "=" * 70)
    if all_passed:
        print("SCALE TESTS: PASSED")
    else:
        print("SCALE TESTS: FAILED")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = run_scale_tests()
    exit(0 if success else 1)
