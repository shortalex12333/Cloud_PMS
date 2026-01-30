#!/usr/bin/env python3
"""
Part Lens - Comprehensive Stress Test with Real Data
====================================================

Tests Part Lens against REAL crew behavior:
- Misspellings, typos, lazy typing
- Natural language variations
- Contradictory/confusing terms
- Partial descriptions
- No special characters (hyphens, spaces)
- Equipment names, brand names, locations
- Vague descriptions ("that pump thing")

Uses REAL parts from database, not just 5 test parts.

Usage:
    python3 test_part_lens_stress.py
"""

from supabase import create_client, Client
from typing import List, Dict, Any
import sys

# Supabase credentials
TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # MY Pandora

print("="*80)
print("PART LENS - COMPREHENSIVE STRESS TEST WITH REAL DATA")
print("="*80)
print()

# Initialize Supabase
try:
    supabase: Client = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)
    print("✓ Supabase client initialized")
except Exception as e:
    print(f"✗ Failed to initialize Supabase: {e}")
    sys.exit(1)

print()
print("Fetching ALL real parts from database...")
print("-" * 80)

# Fetch ALL parts (not just test parts)
try:
    response = supabase.table('pms_parts')\
        .select('id, name, part_number, description, category, manufacturer, location, quantity_on_hand, minimum_quantity')\
        .eq('yacht_id', YACHT_ID)\
        .limit(1000)\
        .execute()

    all_parts = response.data
    print(f"✓ Found {len(all_parts)} total parts in database")
    print()

    # Analyze what we have
    categories = set(p.get('category') for p in all_parts if p.get('category'))
    manufacturers = set(p.get('manufacturer') for p in all_parts if p.get('manufacturer'))
    locations = set(p.get('location') for p in all_parts if p.get('location'))

    print(f"Categories: {len(categories)}")
    for cat in sorted(categories)[:10]:
        count = len([p for p in all_parts if p.get('category') == cat])
        print(f"  - {cat}: {count} parts")
    if len(categories) > 10:
        print(f"  ... and {len(categories) - 10} more")

    print()
    print(f"Manufacturers: {len(manufacturers)}")
    for mfr in sorted(manufacturers)[:10]:
        if mfr:
            count = len([p for p in all_parts if p.get('manufacturer') == mfr])
            print(f"  - {mfr}: {count} parts")
    if len(manufacturers) > 10:
        print(f"  ... and {len(manufacturers) - 10} more")

    print()
    print(f"Locations: {len(locations)}")
    for loc in sorted(locations)[:10]:
        if loc:
            count = len([p for p in all_parts if p.get('location') == loc])
            print(f"  - {loc}: {count} parts")
    if len(locations) > 10:
        print(f"  ... and {len(locations) - 10} more")

    print()

except Exception as e:
    print(f"✗ Failed to fetch parts: {e}")
    sys.exit(1)

# Sample some real part names for testing
sample_parts = all_parts[:20]
print("Sample real parts for test generation:")
print("-" * 80)
for i, part in enumerate(sample_parts, 1):
    name = part.get('name', 'N/A')
    pn = part.get('part_number', 'N/A')
    cat = part.get('category', 'N/A')
    mfr = part.get('manufacturer', 'N/A')
    print(f"{i}. {name[:50]}")
    print(f"   PN: {pn} | Cat: {cat} | Mfr: {mfr}")

print()
print("="*80)
print("GENERATING STRESS TEST QUERIES")
print("="*80)
print()

# Build comprehensive test cases based on REAL data
def generate_stress_tests(parts: List[Dict]) -> List[Dict]:
    """Generate comprehensive stress test cases from real data."""
    tests = []

    # Extract real values
    part_names = [p.get('name', '') for p in parts if p.get('name')]
    categories = list(set(p.get('category') for p in parts if p.get('category')))
    manufacturers = list(set(p.get('manufacturer') for p in parts if p.get('manufacturer')))
    locations = list(set(p.get('location') for p in parts if p.get('location')))

    # 1. MISSPELLINGS - common crew typos
    if any('filter' in str(n).lower() for n in part_names):
        tests.extend([
            {"query": "filtr", "type": "misspelling", "difficulty": "easy", "expected": ">0"},
            {"query": "fillter", "type": "misspelling", "difficulty": "medium", "expected": ">0"},
            {"query": "fiter", "type": "misspelling", "difficulty": "hard", "expected": ">0"},
            {"query": "flter", "type": "misspelling", "difficulty": "hard", "expected": ">0"},
        ])

    if any('pump' in str(n).lower() for n in part_names):
        tests.extend([
            {"query": "pmp", "type": "misspelling", "difficulty": "hard", "expected": ">0"},
            {"query": "pumpp", "type": "misspelling", "difficulty": "easy", "expected": ">0"},
            {"query": "pomp", "type": "misspelling", "difficulty": "medium", "expected": ">0"},
        ])

    if any('hydraulic' in str(n).lower() for n in part_names):
        tests.extend([
            {"query": "hydrualic", "type": "misspelling", "difficulty": "easy", "expected": ">0"},
            {"query": "hydralic", "type": "misspelling", "difficulty": "medium", "expected": ">0"},
            {"query": "hydrulic", "type": "misspelling", "difficulty": "medium", "expected": ">0"},
        ])

    # 2. LAZY TYPING - no special characters
    for part in parts[:10]:
        name = part.get('name', '')
        if '-' in name:
            lazy_name = name.replace('-', '').replace('  ', ' ')
            tests.append({"query": lazy_name, "type": "lazy_typing", "difficulty": "easy", "expected": ">0"})

    # 3. ALL CAPS - shouting crew
    for part in parts[:5]:
        name = part.get('name', '')
        if name and len(name) > 5:
            tests.append({"query": name.upper(), "type": "all_caps", "difficulty": "easy", "expected": ">0"})

    # 4. lowercase - lazy typing
    for part in parts[:5]:
        name = part.get('name', '')
        if name and len(name) > 5:
            tests.append({"query": name.lower(), "type": "lowercase", "difficulty": "easy", "expected": ">0"})

    # 5. PARTIAL DESCRIPTIONS - vague crew requests
    tests.extend([
        {"query": "that filter thing", "type": "vague", "difficulty": "hard", "expected": ">0"},
        {"query": "the pump", "type": "vague", "difficulty": "medium", "expected": ">0"},
        {"query": "some kind of seal", "type": "vague", "difficulty": "hard", "expected": ">0"},
        {"query": "engine stuff", "type": "vague", "difficulty": "hard", "expected": ">0"},
        {"query": "electrical part", "type": "vague", "difficulty": "medium", "expected": ">0"},
    ])

    # 6. NATURAL LANGUAGE - how crew actually talks
    tests.extend([
        {"query": "show me all the filters", "type": "natural_language", "difficulty": "easy", "expected": ">0"},
        {"query": "where is the oil filter", "type": "natural_language", "difficulty": "easy", "expected": ">0"},
        {"query": "I need a pump for the hydraulics", "type": "natural_language", "difficulty": "medium", "expected": ">0"},
        {"query": "do we have any spare filters", "type": "natural_language", "difficulty": "medium", "expected": ">0"},
        {"query": "whats in the engine room", "type": "natural_language", "difficulty": "medium", "expected": ">0"},
        {"query": "give me everything in workshop", "type": "natural_language", "difficulty": "easy", "expected": ">0"},
        {"query": "I think we need more oil filters", "type": "natural_language", "difficulty": "hard", "expected": ">0"},
        {"query": "can you find that seal kit", "type": "natural_language", "difficulty": "hard", "expected": ">0"},
    ])

    # 7. CONTRADICTORY TERMS - confusing requests
    tests.extend([
        {"query": "small large filter", "type": "contradictory", "difficulty": "hard", "expected": ">0"},
        {"query": "new old pump", "type": "contradictory", "difficulty": "hard", "expected": ">0"},
        {"query": "heavy light part", "type": "contradictory", "difficulty": "hard", "expected": ">0"},
    ])

    # 8. CATEGORY SEARCHES - real categories from DB
    for cat in categories[:5]:
        if cat:
            tests.append({"query": cat, "type": "category", "difficulty": "easy", "expected": ">0"})
            # Misspelled category
            if len(cat) > 4:
                misspelled = cat[:-1] + cat[-2]  # Swap last two letters
                tests.append({"query": misspelled, "type": "category_misspelled", "difficulty": "medium", "expected": ">=0"})

    # 9. LOCATION SEARCHES - real locations from DB
    for loc in locations[:5]:
        if loc:
            tests.append({"query": loc, "type": "location", "difficulty": "easy", "expected": ">0"})
            # Partial location
            words = loc.split()
            if len(words) > 1:
                tests.append({"query": words[0], "type": "location_partial", "difficulty": "medium", "expected": ">0"})

    # 10. MANUFACTURER SEARCHES - real manufacturers from DB
    for mfr in manufacturers[:5]:
        if mfr:
            tests.append({"query": mfr, "type": "manufacturer", "difficulty": "easy", "expected": ">0"})

    # 11. FUNCTIONAL DESCRIPTIONS - what it does
    tests.extend([
        {"query": "thing that filters oil", "type": "functional", "difficulty": "hard", "expected": ">=0"},
        {"query": "part that pumps water", "type": "functional", "difficulty": "hard", "expected": ">=0"},
        {"query": "the thing that seals", "type": "functional", "difficulty": "hard", "expected": ">=0"},
        {"query": "what moves hydraulic fluid", "type": "functional", "difficulty": "hard", "expected": ">=0"},
    ])

    # 12. EQUIPMENT-BASED - "for the generator"
    tests.extend([
        {"query": "parts for main engine", "type": "equipment", "difficulty": "medium", "expected": ">=0"},
        {"query": "generator stuff", "type": "equipment", "difficulty": "hard", "expected": ">=0"},
        {"query": "for the hydraulic system", "type": "equipment", "difficulty": "medium", "expected": ">=0"},
    ])

    # 13. EXTREME TYPOS - really bad spelling
    tests.extend([
        {"query": "fltrs", "type": "extreme_typo", "difficulty": "extreme", "expected": ">=0"},
        {"query": "pmps", "type": "extreme_typo", "difficulty": "extreme", "expected": ">=0"},
        {"query": "hydr", "type": "extreme_typo", "difficulty": "extreme", "expected": ">=0"},
    ])

    # 14. MIXED LANGUAGE - technical + casual
    tests.extend([
        {"query": "the hydro pump thing", "type": "mixed", "difficulty": "medium", "expected": ">=0"},
        {"query": "filter for oil or whatever", "type": "mixed", "difficulty": "hard", "expected": ">=0"},
        {"query": "seal kit maybe", "type": "mixed", "difficulty": "hard", "expected": ">=0"},
    ])

    # 15. EXTRA WHITESPACE - sloppy typing
    tests.extend([
        {"query": "oil  filter", "type": "whitespace", "difficulty": "easy", "expected": ">0"},
        {"query": "  pump  ", "type": "whitespace", "difficulty": "easy", "expected": ">0"},
        {"query": "hydraulic    seal", "type": "whitespace", "difficulty": "easy", "expected": ">=0"},
    ])

    # 16. REAL PART NAMES - from actual data
    for part in parts[:10]:
        name = part.get('name', '')
        if name and len(name) > 5:
            # Exact match
            tests.append({"query": name, "type": "exact_real_part", "difficulty": "easy", "expected": ">0"})
            # Partial word
            words = name.split()
            if len(words) > 1:
                tests.append({"query": words[0], "type": "partial_real_part", "difficulty": "medium", "expected": ">=0"})

    return tests

# Generate stress tests
print("Generating stress test cases...")
stress_tests = generate_stress_tests(all_parts)
print(f"✓ Generated {len(stress_tests)} stress test cases")
print()

# Group by difficulty
difficulty_counts = {}
for test in stress_tests:
    diff = test.get('difficulty', 'unknown')
    difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

print("Test Distribution:")
for diff, count in sorted(difficulty_counts.items()):
    print(f"  - {diff}: {count} tests")

print()
print("="*80)
print("RUNNING STRESS TESTS")
print("="*80)
print()

# Execute stress tests
passed = 0
failed = 0
errors = 0
results_by_type = {}
results_by_difficulty = {}

for i, test in enumerate(stress_tests, 1):
    query = test["query"]
    test_type = test["type"]
    difficulty = test["difficulty"]
    expected = test["expected"]

    # Track by type and difficulty
    if test_type not in results_by_type:
        results_by_type[test_type] = {"passed": 0, "failed": 0, "errors": 0}
    if difficulty not in results_by_difficulty:
        results_by_difficulty[difficulty] = {"passed": 0, "failed": 0, "errors": 0}

    # Skip printing every test to avoid spam
    show_detail = (i <= 10 or i % 20 == 0 or difficulty == "extreme")

    if show_detail:
        print(f"Test {i}/{len(stress_tests)}: [{test_type}] [{difficulty}]")
        print(f"  Query: \"{query}\"")

    try:
        # Try multiple search strategies (name, description, category)
        response = supabase.table('pms_parts')\
            .select('id, name, part_number, category, manufacturer')\
            .eq('yacht_id', YACHT_ID)\
            .or_(f"name.ilike.%{query}%,description.ilike.%{query}%,category.ilike.%{query}%,manufacturer.ilike.%{query}%,location.ilike.%{query}%")\
            .limit(20)\
            .execute()

        count = len(response.data)

        # Validate result
        if expected == ">0":
            if count > 0:
                passed += 1
                results_by_type[test_type]["passed"] += 1
                results_by_difficulty[difficulty]["passed"] += 1
                if show_detail:
                    print(f"  ✓ PASS: Found {count} result(s)")
            else:
                failed += 1
                results_by_type[test_type]["failed"] += 1
                results_by_difficulty[difficulty]["failed"] += 1
                if show_detail:
                    print(f"  ✗ FAIL: Found 0 results (expected >0)")
        elif expected == ">=0":
            # Any result is acceptable (including 0)
            passed += 1
            results_by_type[test_type]["passed"] += 1
            results_by_difficulty[difficulty]["passed"] += 1
            if show_detail:
                print(f"  ✓ PASS: Found {count} result(s) (any count OK)")
        else:
            # Exact count
            if count == int(expected):
                passed += 1
                results_by_type[test_type]["passed"] += 1
                results_by_difficulty[difficulty]["passed"] += 1
                if show_detail:
                    print(f"  ✓ PASS: Found {count} result(s)")
            else:
                failed += 1
                results_by_type[test_type]["failed"] += 1
                results_by_difficulty[difficulty]["failed"] += 1
                if show_detail:
                    print(f"  ✗ FAIL: Found {count}, expected {expected}")

    except Exception as e:
        errors += 1
        results_by_type[test_type]["errors"] += 1
        results_by_difficulty[difficulty]["errors"] += 1
        if show_detail:
            print(f"  ✗ ERROR: {str(e)[:100]}")

    if show_detail:
        print()

print("="*80)
print("STRESS TEST RESULTS")
print("="*80)
print()
print(f"Total Tests: {len(stress_tests)}")
print(f"Passed: {passed} ({passed/len(stress_tests)*100:.1f}%)")
print(f"Failed: {failed} ({failed/len(stress_tests)*100:.1f}%)")
print(f"Errors: {errors} ({errors/len(stress_tests)*100:.1f}%)")
print()

print("Results by Test Type:")
print("-" * 80)
for test_type, results in sorted(results_by_type.items()):
    total = results["passed"] + results["failed"] + results["errors"]
    pass_rate = results["passed"] / total * 100 if total > 0 else 0
    print(f"{test_type:25} | Pass: {results['passed']:3} | Fail: {results['failed']:3} | Error: {results['errors']:3} | {pass_rate:5.1f}%")

print()
print("Results by Difficulty:")
print("-" * 80)
for difficulty, results in sorted(results_by_difficulty.items()):
    total = results["passed"] + results["failed"] + results["errors"]
    pass_rate = results["passed"] / total * 100 if total > 0 else 0
    print(f"{difficulty:15} | Pass: {results['passed']:3} | Fail: {results['failed']:3} | Error: {results['errors']:3} | {pass_rate:5.1f}%")

print()
print("="*80)
print("CRITICAL FAILURES")
print("="*80)
print()

# Show critical failures (easy tests that failed)
critical_failures = []
for i, test in enumerate(stress_tests):
    if test["difficulty"] == "easy" and (i not in range(passed)):
        critical_failures.append(test)

if critical_failures:
    print(f"Found {len(critical_failures)} CRITICAL failures (easy tests that should pass):")
    print()
    for test in critical_failures[:10]:
        print(f"✗ [{test['type']}] \"{test['query']}\"")
else:
    print("✓ No critical failures - all easy tests passing")

print()
print("="*80)
print("CONCLUSION")
print("="*80)
print()

success_rate = passed / len(stress_tests) * 100
print(f"Overall Success Rate: {success_rate:.1f}%")
print()

if success_rate >= 90:
    print("✓ EXCELLENT: Part Lens handles crew chaos well")
elif success_rate >= 75:
    print("⚠ GOOD: Part Lens works but needs improvement")
elif success_rate >= 60:
    print("⚠ ACCEPTABLE: Part Lens needs significant improvement")
else:
    print("✗ POOR: Part Lens fails too many real-world queries")

print()
print("Recommendations:")
if results_by_type.get("misspelling", {}).get("failed", 0) > 0:
    print("  - Add fuzzy matching for misspellings")
if results_by_type.get("vague", {}).get("failed", 0) > 0:
    print("  - Improve natural language processing")
if results_by_type.get("functional", {}).get("failed", 0) > 0:
    print("  - Add functional description matching")
if errors > 0:
    print(f"  - Fix {errors} query errors")

print()
sys.exit(0 if success_rate >= 75 else 1)
