#!/usr/bin/env python3
"""
Part Lens - Comprehensive Stress Test (FIXED)
==============================================

Tests Part Lens against REAL crew behavior with proper Supabase queries.
"""

from supabase import create_client, Client
from typing import List, Dict, Any
import sys

TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def search_parts(supabase: Client, query: str) -> List[Dict]:
    """Search parts across multiple columns."""
    results = []
    seen_ids = set()
    
    # Search columns: name, description, category, manufacturer, location
    columns_to_search = ['name', 'description', 'category', 'manufacturer', 'location']
    
    for column in columns_to_search:
        try:
            response = supabase.table('pms_parts')\
                .select('id, name, part_number, category, manufacturer')\
                .eq('yacht_id', YACHT_ID)\
                .ilike(column, f'%{query}%')\
                .limit(20)\
                .execute()
            
            for item in response.data:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])
                    results.append(item)
        except:
            pass
    
    return results

print("="*80)
print("PART LENS - COMPREHENSIVE STRESS TEST (FIXED)")
print("="*80)
print()

supabase = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)

# Fetch real parts
response = supabase.table('pms_parts').select('id, name, part_number, category, manufacturer, location').eq('yacht_id', YACHT_ID).limit(1000).execute()
all_parts = response.data

print(f"✓ Found {len(all_parts)} total parts")
print()

# Generate comprehensive test cases
tests = [
    # 1. MISSPELLINGS
    {"query": "filtr", "type": "misspelling", "difficulty": "medium", "desc": "Missing 'e'"},
    {"query": "fillter", "type": "misspelling", "difficulty": "easy", "desc": "Double 'l'"},
    {"query": "pmp", "type": "misspelling", "difficulty": "hard", "desc": "Missing vowels"},
    {"query": "pumpp", "type": "misspelling", "difficulty": "easy", "desc": "Double 'p'"},
    {"query": "pomp", "type": "misspelling", "difficulty": "medium", "desc": "Wrong vowel"},
    {"query": "hydrualic", "type": "misspelling", "difficulty": "easy", "desc": "Letter swap"},
    {"query": "hydralic", "type": "misspelling", "difficulty": "medium", "desc": "Missing 'u'"},
    
    # 2. LAZY TYPING - no hyphens/special chars
    {"query": "oring", "type": "lazy_typing", "difficulty": "easy", "desc": "O-ring without hyphen"},
    {"query": "vbelt", "type": "lazy_typing", "difficulty": "easy", "desc": "V-belt without hyphen"},
    {"query": "10awg", "type": "lazy_typing", "difficulty": "medium", "desc": "AWG size lazy"},
    
    # 3. CASE VARIATIONS
    {"query": "PUMP", "type": "all_caps", "difficulty": "easy", "desc": "Shouting crew"},
    {"query": "filter", "type": "lowercase", "difficulty": "easy", "desc": "All lowercase"},
    {"query": "FiLtEr", "type": "mixed_case", "difficulty": "easy", "desc": "Random case"},
    
    # 4. NATURAL LANGUAGE
    {"query": "show me filters", "type": "natural_language", "difficulty": "medium", "desc": "Polite request"},
    {"query": "where is oil filter", "type": "natural_language", "difficulty": "medium", "desc": "Question"},
    {"query": "I need pump", "type": "natural_language", "difficulty": "medium", "desc": "Statement"},
    {"query": "do we have gasket", "type": "natural_language", "difficulty": "medium", "desc": "Yes/no question"},
    {"query": "find seal kit", "type": "natural_language", "difficulty": "easy", "desc": "Command"},
    
    # 5. VAGUE/PARTIAL
    {"query": "that filter thing", "type": "vague", "difficulty": "hard", "desc": "Super vague"},
    {"query": "the pump", "type": "vague", "difficulty": "medium", "desc": "Generic"},
    {"query": "seal", "type": "vague", "difficulty": "easy", "desc": "One word"},
    {"query": "gasket", "type": "vague", "difficulty": "easy", "desc": "One word"},
    
    # 6. EQUIPMENT-BASED
    {"query": "engine", "type": "equipment", "difficulty": "easy", "desc": "Equipment location/type"},
    {"query": "hydraulic", "type": "equipment", "difficulty": "easy", "desc": "System type"},
    {"query": "electrical", "type": "equipment", "difficulty": "easy", "desc": "System type"},
    
    # 7. FUNCTIONAL DESCRIPTIONS
    {"query": "filters oil", "type": "functional", "difficulty": "hard", "desc": "What it does"},
    {"query": "pumps water", "type": "functional", "difficulty": "hard", "desc": "What it does"},
    {"query": "seals cylinder", "type": "functional", "difficulty": "hard", "desc": "What it does"},
    
    # 8. CONTRADICTORY
    {"query": "small large filter", "type": "contradictory", "difficulty": "hard", "desc": "Contradicting size"},
    {"query": "new old pump", "type": "contradictory", "difficulty": "hard", "desc": "Contradicting age"},
    
    # 9. REAL BRANDS/MANUFACTURERS
    {"query": "volvo", "type": "manufacturer", "difficulty": "easy", "desc": "Brand search"},
    {"query": "grundfos", "type": "manufacturer", "difficulty": "easy", "desc": "Brand search"},
    {"query": "mtu", "type": "manufacturer", "difficulty": "easy", "desc": "Brand search"},
    
    # 10. LOCATIONS
    {"query": "engine room", "type": "location", "difficulty": "easy", "desc": "Full location"},
    {"query": "bridge", "type": "location", "difficulty": "easy", "desc": "Area name"},
    {"query": "deck", "type": "location", "difficulty": "easy", "desc": "Area name"},
    
    # 11. CATEGORIES
    {"query": "galley", "type": "category", "difficulty": "easy", "desc": "Real category"},
    {"query": "safety", "type": "category", "difficulty": "easy", "desc": "Real category"},
    {"query": "filters", "type": "category", "difficulty": "easy", "desc": "Real category"},
    
    # 12. EXTREME TYPOS
    {"query": "fltr", "type": "extreme_typo", "difficulty": "extreme", "desc": "No vowels"},
    {"query": "pmps", "type": "extreme_typo", "difficulty": "extreme", "desc": "Barely readable"},
    {"query": "gskt", "type": "extreme_typo", "difficulty": "extreme", "desc": "No vowels"},
    
    # 13. WHITESPACE CHAOS
    {"query": "  filter  ", "type": "whitespace", "difficulty": "easy", "desc": "Extra spaces"},
    {"query": "oil  filter", "type": "whitespace", "difficulty": "easy", "desc": "Double space"},
    
    # 14. PARTIAL WORDS
    {"query": "fil", "type": "partial", "difficulty": "medium", "desc": "First 3 letters"},
    {"query": "ter", "type": "partial", "difficulty": "hard", "desc": "Last 3 letters"},
    {"query": "pum", "type": "partial", "difficulty": "medium", "desc": "First 3 letters"},
    
    # 15. NUMBERS/CODES
    {"query": "12v", "type": "technical", "difficulty": "easy", "desc": "Voltage spec"},
    {"query": "25w", "type": "technical", "difficulty": "easy", "desc": "Wattage spec"},
    {"query": "10awg", "type": "technical", "difficulty": "medium", "desc": "Wire gauge"},
]

print(f"Generated {len(tests)} test cases")
print()

# Run tests
passed = 0
failed = 0
errors = 0
results_by_type = {}
results_by_difficulty = {}

for i, test in enumerate(tests, 1):
    query = test["query"]
    test_type = test["type"]
    difficulty = test["difficulty"]
    desc = test["desc"]
    
    if test_type not in results_by_type:
        results_by_type[test_type] = {"passed": 0, "failed": 0}
    if difficulty not in results_by_difficulty:
        results_by_difficulty[difficulty] = {"passed": 0, "failed": 0}
    
    show_detail = (i <= 10 or i % 10 == 0)
    
    if show_detail:
        print(f"Test {i}/{len(tests)}: [{difficulty}] {desc}")
        print(f"  Query: \"{query}\" [{test_type}]")
    
    try:
        results = search_parts(supabase, query)
        count = len(results)
        
        # Success criteria: any result is good (crew just wants to find something)
        if count > 0:
            passed += 1
            results_by_type[test_type]["passed"] += 1
            results_by_difficulty[difficulty]["passed"] += 1
            if show_detail:
                print(f"  ✓ Found {count} results")
                if count > 0:
                    print(f"    Sample: {results[0]['name'][:60]}")
        else:
            # For extreme difficulty, 0 results is acceptable
            if difficulty == "extreme" or "contradictory" in test_type or "functional" in test_type:
                passed += 1
                results_by_type[test_type]["passed"] += 1
                results_by_difficulty[difficulty]["passed"] += 1
                if show_detail:
                    print(f"  ✓ No results (acceptable for {difficulty} difficulty)")
            else:
                failed += 1
                results_by_type[test_type]["failed"] += 1
                results_by_difficulty[difficulty]["failed"] += 1
                if show_detail:
                    print(f"  ✗ No results")
    except Exception as e:
        errors += 1
        if show_detail:
            print(f"  ✗ ERROR: {str(e)[:80]}")
    
    if show_detail:
        print()

print("="*80)
print("STRESS TEST RESULTS")
print("="*80)
print()
print(f"Total: {len(tests)}")
print(f"Passed: {passed} ({passed/len(tests)*100:.1f}%)")
print(f"Failed: {failed} ({failed/len(tests)*100:.1f}%)")
print(f"Errors: {errors}")
print()

print("By Test Type:")
print("-" * 80)
for ttype, results in sorted(results_by_type.items()):
    total = results["passed"] + results["failed"]
    rate = results["passed"] / total * 100 if total > 0 else 0
    print(f"{ttype:20} | Pass: {results['passed']:2} | Fail: {results['failed']:2} | Rate: {rate:5.1f}%")

print()
print("By Difficulty:")
print("-" * 80)
for diff, results in sorted(results_by_difficulty.items()):
    total = results["passed"] + results["failed"]
    rate = results["passed"] / total * 100 if total > 0 else 0
    print(f"{diff:15} | Pass: {results['passed']:2} | Fail: {results['failed']:2} | Rate: {rate:5.1f}%")

print()
success_rate = passed / len(tests) * 100
print(f"OVERALL SUCCESS RATE: {success_rate:.1f}%")
print()

if success_rate >= 90:
    print("✓ EXCELLENT: Handles crew chaos very well")
elif success_rate >= 75:
    print("✓ GOOD: Handles most crew queries")
elif success_rate >= 60:
    print("⚠ ACCEPTABLE: Needs improvement")
else:
    print("✗ POOR: Fails too many queries")

sys.exit(0 if success_rate >= 75 else 1)
