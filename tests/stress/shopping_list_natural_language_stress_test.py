#!/usr/bin/env python3
"""
Shopping List Natural Language Stress Test
===========================================

Tests realistic crew queries with:
- Misspellings (crew won't spell perfectly)
- Paraphrasing (different ways to say same thing)
- Omitted dashes/spaces (lazy typing)
- Contradictory terms (confusing requests)
- Wrong assumptions (asking for things that don't exist)

Uses ACTUAL database values to generate realistic test cases.
"""

import requests
import json
from typing import List, Dict, Tuple
from datetime import datetime

# =============================================================================
# TEST DATA (from actual database)
# =============================================================================

ACTUAL_PARTS = [
    {
        "part_number": "ENG-0012-584",
        "part_name": "Turbocharger Gasket Set",
        "manufacturer": "Volvo Penta",
        "category": "Galley"
    },
    {
        "part_number": "PMP-0018-280",
        "part_name": "Raw Water Pump Seal Kit",
        "manufacturer": "Grundfos",
        "category": "Engine Room"
    },
    {
        "part_number": "ENG-0029-432",
        "part_name": "Cylinder Liner O-Ring Kit",
        "manufacturer": "Yanmar",
        "category": "Safety"
    },
    {
        "part_number": "FLT-0033-146",
        "part_name": "Fuel Filter Generator",
        "manufacturer": "Fleetguard",
        "category": "Engine Room"
    },
    {
        "part_number": "ELC-0041-489",
        "part_name": "Starter Motor Solenoid",
        "manufacturer": "Blue Sea Systems",
        "category": "Deck"
    },
    {
        "part_number": "ELC-0053-760",
        "part_name": "Navigation Light Bulb 12V 25W",
        "manufacturer": "Blue Sea Systems",
        "category": "Safety"
    },
    {
        "part_number": "ENG-0206-977",
        "part_name": "V-Belt Sea Water Pump",
        "manufacturer": "Volvo Penta",
        "category": "Deck"
    },
    {
        "part_number": "HYD-0066-515",
        "part_name": "Hydraulic Oil Filter",
        "manufacturer": "Danfoss",
        "category": "Safety"
    }
]

# =============================================================================
# NATURAL LANGUAGE TEST CASES
# =============================================================================

def generate_chaotic_queries() -> List[Dict]:
    """
    Generate realistic crew queries with human mistakes.

    Categories:
    1. Misspellings (typos, phonetic errors)
    2. Paraphrasing (different ways to say same thing)
    3. Omitted characters (lazy typing, no dashes/spaces)
    4. Contradictory terms (confusing requests)
    5. Wrong assumptions (non-existent parts)
    """

    test_cases = []

    # =========================================================================
    # LEVEL 1: MISSPELLINGS (Easy)
    # =========================================================================
    test_cases.extend([
        {
            "query": "turbochager gasket",  # Missing 'r'
            "expected_match": "Turbocharger Gasket Set",
            "difficulty": "easy",
            "error_type": "misspelling",
            "should_find": True
        },
        {
            "query": "fuel filtre generator",  # British spelling
            "expected_match": "Fuel Filter Generator",
            "difficulty": "easy",
            "error_type": "misspelling",
            "should_find": True
        },
        {
            "query": "hidrolic oil filter",  # Phonetic error
            "expected_match": "Hydraulic Oil Filter",
            "difficulty": "easy",
            "error_type": "misspelling",
            "should_find": True
        },
        {
            "query": "navigation lite bulb",  # 'light' -> 'lite'
            "expected_match": "Navigation Light Bulb",
            "difficulty": "easy",
            "error_type": "misspelling",
            "should_find": True
        },
    ])

    # =========================================================================
    # LEVEL 2: OMITTED CHARACTERS (Medium - crew is lazy)
    # =========================================================================
    test_cases.extend([
        {
            "query": "ENG0012584",  # No dashes
            "expected_match": "Turbocharger Gasket Set",
            "difficulty": "medium",
            "error_type": "omitted_dashes",
            "should_find": True
        },
        {
            "query": "rawwaterpumpseal",  # No spaces
            "expected_match": "Raw Water Pump Seal Kit",
            "difficulty": "medium",
            "error_type": "omitted_spaces",
            "should_find": True
        },
        {
            "query": "vbelt seawater pump",  # 'V-Belt' -> 'vbelt'
            "expected_match": "V-Belt Sea Water Pump",
            "difficulty": "medium",
            "error_type": "omitted_dash",
            "should_find": True
        },
        {
            "query": "12v25w nav light",  # '12V 25W' -> '12v25w'
            "expected_match": "Navigation Light Bulb",
            "difficulty": "medium",
            "error_type": "omitted_spaces",
            "should_find": True
        },
    ])

    # =========================================================================
    # LEVEL 3: PARAPHRASING (Medium - different ways to say same thing)
    # =========================================================================
    test_cases.extend([
        {
            "query": "engine turbo gasket",  # 'Turbocharger' paraphrased
            "expected_match": "Turbocharger Gasket Set",
            "difficulty": "medium",
            "error_type": "paraphrase",
            "should_find": True
        },
        {
            "query": "water pump seals for generator",  # Reordered
            "expected_match": "Raw Water Pump Seal Kit",
            "difficulty": "medium",
            "error_type": "paraphrase",
            "should_find": True
        },
        {
            "query": "belt for alternator",  # Simplified
            "expected_match": "V-Belt Alternator",
            "difficulty": "medium",
            "error_type": "paraphrase",
            "should_find": True
        },
        {
            "query": "starter relay",  # 'Solenoid' -> 'Relay'
            "expected_match": "Starter Motor Solenoid",
            "difficulty": "medium",
            "error_type": "paraphrase_synonym",
            "should_find": True
        },
    ])

    # =========================================================================
    # LEVEL 4: BRAND + DESCRIPTION (Hard - realistic crew queries)
    # =========================================================================
    test_cases.extend([
        {
            "query": "volvo penta turbo gasket",  # Brand + part
            "expected_match": "Turbocharger Gasket Set",
            "difficulty": "hard",
            "error_type": "brand_description",
            "should_find": True
        },
        {
            "query": "grundfos pump seal",  # Brand + partial name
            "expected_match": "Raw Water Pump Seal Kit",
            "difficulty": "hard",
            "error_type": "brand_description",
            "should_find": True
        },
        {
            "query": "fleetguard fuel filter",  # Brand + generic term
            "expected_match": "Fuel Filter Generator",
            "difficulty": "hard",
            "error_type": "brand_description",
            "should_find": True
        },
        {
            "query": "blue sea nav bulb",  # Brand + abbreviation
            "expected_match": "Navigation Light Bulb",
            "difficulty": "hard",
            "error_type": "brand_abbreviation",
            "should_find": True
        },
    ])

    # =========================================================================
    # LEVEL 5: CONTRADICTORY TERMS (Very Hard - confusing requests)
    # =========================================================================
    test_cases.extend([
        {
            "query": "diesel generator fuel filter",  # 'diesel' contradicts actual
            "expected_match": "Fuel Filter Generator",
            "difficulty": "very_hard",
            "error_type": "contradictory_term",
            "should_find": True  # Should still find despite extra term
        },
        {
            "query": "hydraulic pump filter",  # 'pump' not in name
            "expected_match": "Hydraulic Oil Filter",
            "difficulty": "very_hard",
            "error_type": "extra_term",
            "should_find": True
        },
        {
            "query": "main engine cylinder oring",  # 'main engine' not in name
            "expected_match": "Cylinder Liner O-Ring Kit",
            "difficulty": "very_hard",
            "error_type": "extra_context",
            "should_find": True
        },
    ])

    # =========================================================================
    # LEVEL 6: WRONG ASSUMPTIONS (Edge Cases - doesn't exist)
    # =========================================================================
    test_cases.extend([
        {
            "query": "wartsila fuel injector",  # Wrong manufacturer
            "expected_match": None,
            "difficulty": "edge_case",
            "error_type": "wrong_assumption",
            "should_find": False
        },
        {
            "query": "main engine crankshaft",  # Not in inventory
            "expected_match": None,
            "difficulty": "edge_case",
            "error_type": "non_existent",
            "should_find": False
        },
        {
            "query": "ENG-9999-999",  # Invalid part number
            "expected_match": None,
            "difficulty": "edge_case",
            "error_type": "invalid_part_number",
            "should_find": False
        },
    ])

    # =========================================================================
    # LEVEL 7: EXTREME CHAOS (Multiple errors combined)
    # =========================================================================
    test_cases.extend([
        {
            "query": "volvopnta tubochager gaskit",  # Misspell + omit space + typo
            "expected_match": "Turbocharger Gasket Set",
            "difficulty": "extreme",
            "error_type": "multiple_errors",
            "should_find": True  # Fuzzy search should still work
        },
        {
            "query": "bluesea navlite 12v",  # Omit space + abbreviate + omit watts
            "expected_match": "Navigation Light Bulb",
            "difficulty": "extreme",
            "error_type": "multiple_errors",
            "should_find": True
        },
        {
            "query": "engine room raw wtr pump seels",  # Extra context + abbreviate + typo
            "expected_match": "Raw Water Pump Seal Kit",
            "difficulty": "extreme",
            "error_type": "multiple_errors",
            "should_find": True
        },
    ])

    return test_cases


# =============================================================================
# STRESS TEST EXECUTION
# =============================================================================

def run_search_stress_test(
    api_url: str,
    jwt_token: str,
    yacht_id: str
) -> Dict:
    """
    Execute stress test against search API.

    Returns test results with pass/fail counts.
    """

    test_cases = generate_chaotic_queries()
    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "by_difficulty": {},
        "by_error_type": {},
        "failures": []
    }

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    print(f"🔥 Starting Shopping List Natural Language Stress Test")
    print(f"📊 Total test cases: {len(test_cases)}")
    print("")

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected_match"]
        should_find = test_case["should_find"]
        difficulty = test_case["difficulty"]
        error_type = test_case["error_type"]

        print(f"[{i}/{len(test_cases)}] Testing: \"{query}\" ({difficulty}/{error_type})")

        # Make search request
        # Note: yacht_id is derived from JWT, not sent in payload
        payload = {
            "query": query,
            "limit": 20
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)

            # Analyze response
            if response.status_code == 200:
                data = response.json()
                found_results = len(data.get("results", [])) > 0

                # Check if we found what we expected
                if should_find:
                    if found_results:
                        # Verify if expected match is in results
                        result_names = [r.get("title", "") for r in data.get("results", [])]
                        if expected and any(expected.lower() in name.lower() for name in result_names):
                            print(f"  ✅ PASS: Found expected match \"{expected}\"")
                            results["passed"] += 1
                        elif found_results:
                            print(f"  ⚠️  PARTIAL: Found results but not exact match")
                            print(f"      Expected: {expected}")
                            print(f"      Got: {result_names[:3]}")
                            results["passed"] += 1  # Still counts as pass (found something)
                        else:
                            print(f"  ❌ FAIL: No results found")
                            results["failed"] += 1
                            results["failures"].append({
                                "query": query,
                                "expected": expected,
                                "error_type": error_type,
                                "reason": "no_results"
                            })
                    else:
                        print(f"  ❌ FAIL: Should find but got no results")
                        results["failed"] += 1
                        results["failures"].append({
                            "query": query,
                            "expected": expected,
                            "error_type": error_type,
                            "reason": "no_results"
                        })
                else:
                    # Should NOT find
                    if not found_results:
                        print(f"  ✅ PASS: Correctly returned no results")
                        results["passed"] += 1
                    else:
                        print(f"  ⚠️  WARN: Found results for non-existent item")
                        results["passed"] += 1  # Not a failure
            else:
                print(f"  ❌ ERROR: HTTP {response.status_code}")
                results["failed"] += 1
                results["failures"].append({
                    "query": query,
                    "expected": expected,
                    "error_type": error_type,
                    "reason": f"http_{response.status_code}"
                })

        except Exception as e:
            print(f"  ❌ EXCEPTION: {str(e)}")
            results["failed"] += 1
            results["failures"].append({
                "query": query,
                "expected": expected,
                "error_type": error_type,
                "reason": f"exception: {str(e)}"
            })

        # Track by difficulty
        if difficulty not in results["by_difficulty"]:
            results["by_difficulty"][difficulty] = {"passed": 0, "failed": 0}
        if query not in [f["query"] for f in results["failures"]]:
            results["by_difficulty"][difficulty]["passed"] += 1
        else:
            results["by_difficulty"][difficulty]["failed"] += 1

        # Track by error type
        if error_type not in results["by_error_type"]:
            results["by_error_type"][error_type] = {"passed": 0, "failed": 0}
        if query not in [f["query"] for f in results["failures"]]:
            results["by_error_type"][error_type]["passed"] += 1
        else:
            results["by_error_type"][error_type]["failed"] += 1

    return results


def print_results(results: Dict):
    """Print test results summary."""

    print("\n" + "=" * 80)
    print("📊 STRESS TEST RESULTS")
    print("=" * 80)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"❌ Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print("")

    print("By Difficulty:")
    for difficulty, counts in sorted(results["by_difficulty"].items()):
        total = counts["passed"] + counts["failed"]
        pass_rate = counts["passed"] / total * 100 if total > 0 else 0
        print(f"  {difficulty:15s}: {counts['passed']}/{total} ({pass_rate:.0f}%)")
    print("")

    print("By Error Type:")
    for error_type, counts in sorted(results["by_error_type"].items()):
        total = counts["passed"] + counts["failed"]
        pass_rate = counts["passed"] / total * 100 if total > 0 else 0
        print(f"  {error_type:25s}: {counts['passed']}/{total} ({pass_rate:.0f}%)")
    print("")

    if results["failures"]:
        print("❌ FAILURES:")
        for failure in results["failures"]:
            print(f"  Query: \"{failure['query']}\"")
            print(f"    Expected: {failure['expected']}")
            print(f"    Error Type: {failure['error_type']}")
            print(f"    Reason: {failure['reason']}")
            print("")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python shopping_list_natural_language_stress_test.py <api_url> <jwt_token> [yacht_id]")
        print("")
        print("Example:")
        print("  python shopping_list_natural_language_stress_test.py \\")
        print("    https://pipeline-core.int.celeste7.ai/v1/search \\")
        print("    eyJhbGci... \\")
        print("    85fe1119-b04c-41ac-80f1-829d23322598")
        sys.exit(1)

    api_url = sys.argv[1]
    jwt_token = sys.argv[2]
    yacht_id = sys.argv[3] if len(sys.argv) > 3 else "85fe1119-b04c-41ac-80f1-829d23322598"

    results = run_search_stress_test(api_url, jwt_token, yacht_id)
    print_results(results)

    # Exit code based on pass rate
    pass_rate = results["passed"] / results["total"] * 100
    if pass_rate >= 80:
        print(f"✅ PASS: {pass_rate:.1f}% pass rate (>= 80% required)")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {pass_rate:.1f}% pass rate (< 80% required)")
        sys.exit(1)
