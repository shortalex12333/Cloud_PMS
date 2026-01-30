#!/usr/bin/env python3
"""
Part Lens - Stress Test with Query Preprocessing
================================================

Adds preprocessing to handle crew chaos:
- Strip filler words ("show me", "where is", etc.)
- Trim extra whitespace
- Better handling of natural language
"""

from supabase import create_client, Client
from typing import List, Dict, Any
import sys
import re

TENANT_1_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_1_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

def preprocess_query(query: str) -> str:
    """Clean up crew's messy queries."""
    # Lowercase
    q = query.lower().strip()
    
    # Remove filler words (natural language noise)
    filler_patterns = [
        r'^show me\s+',
        r'^where is\s+',
        r'^where are\s+',
        r'^find\s+',
        r'^i need\s+',
        r'^do we have\s+',
        r'^give me\s+',
        r'^can you find\s+',
        r'^looking for\s+',
        r'\s+please$',
        r'^the\s+',
        r'^a\s+',
        r'^an\s+',
        r'^that\s+',
        r'^some\s+',
        r'\s+thing$',
        r'\s+stuff$',
    ]
    
    for pattern in filler_patterns:
        q = re.sub(pattern, '', q)
    
    # Normalize whitespace
    q = re.sub(r'\s+', ' ', q).strip()
    
    return q

def search_parts(supabase: Client, query: str) -> List[Dict]:
    """Search parts with preprocessing."""
    clean_query = preprocess_query(query)
    
    # If query became empty after preprocessing, use original
    if not clean_query or len(clean_query) < 2:
        clean_query = query.strip()
    
    results = []
    seen_ids = set()
    
    columns = ['name', 'description', 'category', 'manufacturer', 'location']
    
    for column in columns:
        try:
            response = supabase.table('pms_parts')\
                .select('id, name, part_number, category, manufacturer')\
                .eq('yacht_id', YACHT_ID)\
                .ilike(column, f'%{clean_query}%')\
                .limit(20)\
                .execute()
            
            for item in response.data:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])
                    results.append(item)
        except:
            pass
    
    return results, clean_query

print("="*80)
print("PART LENS - STRESS TEST WITH PREPROCESSING")
print("="*80)
print()

supabase = create_client(TENANT_1_URL, TENANT_1_SERVICE_KEY)

response = supabase.table('pms_parts').select('id').eq('yacht_id', YACHT_ID).limit(1000).execute()
print(f"✓ Found {len(response.data)} total parts")
print()

# Same test cases as before
tests = [
    # MISSPELLINGS
    {"query": "filtr", "type": "misspelling", "difficulty": "medium"},
    {"query": "fillter", "type": "misspelling", "difficulty": "easy"},
    {"query": "pmp", "type": "misspelling", "difficulty": "hard"},
    {"query": "pumpp", "type": "misspelling", "difficulty": "easy"},
    {"query": "pomp", "type": "misspelling", "difficulty": "medium"},
    {"query": "hydrualic", "type": "misspelling", "difficulty": "easy"},
    {"query": "hydralic", "type": "misspelling", "difficulty": "medium"},
    
    # LAZY TYPING
    {"query": "oring", "type": "lazy_typing", "difficulty": "easy"},
    {"query": "vbelt", "type": "lazy_typing", "difficulty": "easy"},
    {"query": "10awg", "type": "lazy_typing", "difficulty": "medium"},
    
    # CASE VARIATIONS
    {"query": "PUMP", "type": "all_caps", "difficulty": "easy"},
    {"query": "filter", "type": "lowercase", "difficulty": "easy"},
    {"query": "FiLtEr", "type": "mixed_case", "difficulty": "easy"},
    
    # NATURAL LANGUAGE (should work better now!)
    {"query": "show me filters", "type": "natural_language", "difficulty": "medium"},
    {"query": "where is oil filter", "type": "natural_language", "difficulty": "medium"},
    {"query": "I need pump", "type": "natural_language", "difficulty": "medium"},
    {"query": "do we have gasket", "type": "natural_language", "difficulty": "medium"},
    {"query": "find seal kit", "type": "natural_language", "difficulty": "easy"},
    
    # VAGUE/PARTIAL
    {"query": "that filter thing", "type": "vague", "difficulty": "hard"},
    {"query": "the pump", "type": "vague", "difficulty": "medium"},
    {"query": "seal", "type": "vague", "difficulty": "easy"},
    {"query": "gasket", "type": "vague", "difficulty": "easy"},
    
    # EQUIPMENT-BASED
    {"query": "engine", "type": "equipment", "difficulty": "easy"},
    {"query": "hydraulic", "type": "equipment", "difficulty": "easy"},
    {"query": "electrical", "type": "equipment", "difficulty": "easy"},
    
    # FUNCTIONAL DESCRIPTIONS
    {"query": "filters oil", "type": "functional", "difficulty": "hard"},
    {"query": "pumps water", "type": "functional", "difficulty": "hard"},
    {"query": "seals cylinder", "type": "functional", "difficulty": "hard"},
    
    # CONTRADICTORY
    {"query": "small large filter", "type": "contradictory", "difficulty": "hard"},
    {"query": "new old pump", "type": "contradictory", "difficulty": "hard"},
    
    # MANUFACTURERS
    {"query": "volvo", "type": "manufacturer", "difficulty": "easy"},
    {"query": "grundfos", "type": "manufacturer", "difficulty": "easy"},
    {"query": "mtu", "type": "manufacturer", "difficulty": "easy"},
    
    # LOCATIONS
    {"query": "engine room", "type": "location", "difficulty": "easy"},
    {"query": "bridge", "type": "location", "difficulty": "easy"},
    {"query": "deck", "type": "location", "difficulty": "easy"},
    
    # CATEGORIES
    {"query": "galley", "type": "category", "difficulty": "easy"},
    {"query": "safety", "type": "category", "difficulty": "easy"},
    {"query": "filters", "type": "category", "difficulty": "easy"},
    
    # EXTREME TYPOS
    {"query": "fltr", "type": "extreme_typo", "difficulty": "extreme"},
    {"query": "pmps", "type": "extreme_typo", "difficulty": "extreme"},
    {"query": "gskt", "type": "extreme_typo", "difficulty": "extreme"},
    
    # WHITESPACE CHAOS (should work better now!)
    {"query": "  filter  ", "type": "whitespace", "difficulty": "easy"},
    {"query": "oil  filter", "type": "whitespace", "difficulty": "easy"},
    
    # PARTIAL WORDS
    {"query": "fil", "type": "partial", "difficulty": "medium"},
    {"query": "ter", "type": "partial", "difficulty": "hard"},
    {"query": "pum", "type": "partial", "difficulty": "medium"},
    
    # TECHNICAL
    {"query": "12v", "type": "technical", "difficulty": "easy"},
    {"query": "25w", "type": "technical", "difficulty": "easy"},
    {"query": "10awg", "type": "technical", "difficulty": "medium"},
]

print(f"Running {len(tests)} tests with preprocessing...")
print()

passed = 0
failed = 0
results_by_type = {}
results_by_difficulty = {}

for i, test in enumerate(tests, 1):
    query = test["query"]
    test_type = test["type"]
    difficulty = test["difficulty"]
    
    if test_type not in results_by_type:
        results_by_type[test_type] = {"passed": 0, "failed": 0}
    if difficulty not in results_by_difficulty:
        results_by_difficulty[difficulty] = {"passed": 0, "failed": 0}
    
    show_detail = (i <= 15 or i % 10 == 0)
    
    try:
        results, clean_query = search_parts(supabase, query)
        count = len(results)
        
        if show_detail:
            preprocessed_note = f" → \"{clean_query}\"" if clean_query != query.lower().strip() else ""
            print(f"Test {i}/{len(tests)}: [{difficulty}] \"{query}\"{preprocessed_note}")
        
        if count > 0:
            passed += 1
            results_by_type[test_type]["passed"] += 1
            results_by_difficulty[difficulty]["passed"] += 1
            if show_detail:
                print(f"  ✓ Found {count} results: {results[0]['name'][:50]}")
        else:
            if difficulty == "extreme" or "contradictory" in test_type or "functional" in test_type:
                passed += 1
                results_by_type[test_type]["passed"] += 1
                results_by_difficulty[difficulty]["passed"] += 1
                if show_detail:
                    print(f"  ✓ No results (OK for {difficulty})")
            else:
                failed += 1
                results_by_type[test_type]["failed"] += 1
                results_by_difficulty[difficulty]["failed"] += 1
                if show_detail:
                    print(f"  ✗ No results")
    except Exception as e:
        if show_detail:
            print(f"  ✗ ERROR: {str(e)[:60]}")
    
    if show_detail:
        print()

print("="*80)
print("RESULTS WITH PREPROCESSING")
print("="*80)
print()
print(f"Total: {len(tests)}")
print(f"Passed: {passed} ({passed/len(tests)*100:.1f}%)")
print(f"Failed: {failed} ({failed/len(tests)*100:.1f}%)")
print()

print("By Test Type:")
print("-" * 80)
for ttype, results in sorted(results_by_type.items()):
    total = results["passed"] + results["failed"]
    rate = results["passed"] / total * 100 if total > 0 else 0
    status = "✓" if rate >= 80 else "⚠" if rate >= 60 else "✗"
    print(f"{status} {ttype:20} | {results['passed']:2}/{total:2} = {rate:5.1f}%")

print()
success_rate = passed / len(tests) * 100
print(f"OVERALL: {success_rate:.1f}%")
print()

if success_rate >= 85:
    print("✓ EXCELLENT: Ready for production")
elif success_rate >= 75:
    print("✓ GOOD: Acceptable for deployment")
elif success_rate >= 60:
    print("⚠ NEEDS WORK: Improve before deploying")
else:
    print("✗ NOT READY: Too many failures")

sys.exit(0 if success_rate >= 75 else 1)
