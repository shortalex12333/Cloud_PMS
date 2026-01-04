"""
Generate 1500 Search Test Cases
================================

Categories:
1. Entity Routing (500 tests) - Each entity type routes to correct tables
2. Match Type (300 tests) - EXACT/ILIKE/TRIGRAM work correctly
3. Wave Budget (200 tests) - Timing compliance
4. Security (200 tests) - yacht_id enforcement
5. Ranking (150 tests) - Confidence scores
6. Diversity (100 tests) - Results from multiple sources
7. Edge Cases (50 tests) - Empty, timeouts, errors
"""

import json
import random
import string
from typing import Dict, List, Any

# Test yacht_id (valid)
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

# Sample values for each entity type
ENTITY_SAMPLES = {
    "PART_NUMBER": [
        "ENG-0008-103", "MTU-FIL-001", "CAT-3208-INJ", "VIC-BAT-200",
        "KOH-GEN-001", "SEA-WTR-PMP", "FUE-INJ-NZL", "OIL-FLT-012",
        "AIR-FLT-006", "HYD-PMP-003", "EXH-MNF-001", "CLC-TRM-005",
    ],
    "PART_NAME": [
        "fuel filter", "oil filter", "impeller", "thermostat", "alternator",
        "water pump", "fuel injector", "belt tensioner", "gasket set",
        "sea strainer", "raw water pump", "heat exchanger", "turbocharger",
        "fuel lift pump", "starter motor", "glow plug", "injector nozzle",
    ],
    "FAULT_CODE": [
        "E047", "1234", "SPN-524", "F001", "ALM-15", "ERR-42",
        "LOW-FUEL", "OVERHEAT", "HI-TEMP", "LO-PRESS", "OIL-WARN",
    ],
    "EQUIPMENT_NAME": [
        "main engine", "generator", "watermaker", "air conditioning",
        "bow thruster", "stern thruster", "anchor windlass", "hydraulic pump",
        "fresh water pump", "bilge pump", "fire pump", "stabilizers",
    ],
    "SYSTEM_NAME": [
        "fuel system", "propulsion", "HVAC", "electrical", "hydraulic",
        "navigation", "communication", "safety", "plumbing", "steering",
    ],
    "MANUFACTURER": [
        "MTU", "Caterpillar", "Kohler", "Victron", "Northern Lights",
        "Cummins", "Yanmar", "Volvo Penta", "MAN", "Perkins",
    ],
    "SYMPTOM_NAME": [
        "won't start", "overheating", "vibration", "noise", "smoke",
        "low power", "rough idle", "stalling", "leaking", "alarm",
    ],
    "STOCK_LOCATION": [
        "Yacht", "Agent - Antibes", "Agent - Monaco", "Warehouse", "In Transit",
    ],
    "DOCUMENT_QUERY": [
        "maintenance schedule", "oil change procedure", "winterization",
        "troubleshooting fuel", "electrical wiring diagram", "parts list",
        "service interval", "emergency procedures", "safety checklist",
    ],
    "FREE_TEXT": [
        "engine", "fuel", "oil", "filter", "pump", "system", "check",
        "replace", "inspect", "service", "warning", "alarm", "temperature",
    ],
}

# Expected table routes per entity type
ENTITY_TABLE_ROUTES = {
    "PART_NUMBER": ["pms_parts", "v_inventory"],
    "PART_NAME": ["pms_parts", "v_inventory"],
    "FAULT_CODE": ["search_fault_code_catalog"],
    "EQUIPMENT_NAME": ["graph_nodes", "pms_equipment"],
    "SYSTEM_NAME": ["graph_nodes", "alias_systems"],
    "MANUFACTURER": ["pms_parts", "pms_suppliers"],
    "SYMPTOM_NAME": ["alias_symptoms", "symptom_aliases", "search_document_chunks"],
    "STOCK_LOCATION": ["v_inventory"],
    "DOCUMENT_QUERY": ["search_document_chunks"],
    "FREE_TEXT": ["graph_nodes", "pms_parts", "search_document_chunks"],
}

# Expected match types per entity type
ENTITY_MATCH_TYPES = {
    "PART_NUMBER": ["exact", "ilike"],
    "PART_NAME": ["ilike", "trigram"],
    "FAULT_CODE": ["exact", "ilike"],
    "EQUIPMENT_NAME": ["ilike", "trigram"],
    "SYSTEM_NAME": ["exact", "ilike", "trigram"],
    "MANUFACTURER": ["ilike"],
    "SYMPTOM_NAME": ["ilike", "trigram"],
    "STOCK_LOCATION": ["exact", "ilike"],
    "DOCUMENT_QUERY": ["ilike", "trigram", "vector"],
    "FREE_TEXT": ["ilike", "trigram"],
}


def generate_entity_routing_tests(count: int = 500) -> List[Dict]:
    """Generate tests for entity type → table routing."""
    tests = []
    test_id = 1000

    for entity_type, samples in ENTITY_SAMPLES.items():
        expected_tables = ENTITY_TABLE_ROUTES.get(entity_type, [])

        # Generate multiple tests per entity type
        for _ in range(count // len(ENTITY_SAMPLES)):
            value = random.choice(samples)
            tests.append({
                "id": f"ER-{test_id}",
                "category": "entity_routing",
                "entity_type": entity_type,
                "search_value": value,
                "yacht_id": TEST_YACHT_ID,
                "expected_tables": expected_tables,
                "expected_outcome": "routes_correctly",
                "description": f"Entity {entity_type} should route to {expected_tables}",
            })
            test_id += 1

    return tests[:count]


def generate_match_type_tests(count: int = 300) -> List[Dict]:
    """Generate tests for match type behavior."""
    tests = []
    test_id = 2000

    match_type_cases = [
        # EXACT match tests
        {"match_type": "exact", "value": "ENG-0008-103", "entity": "PART_NUMBER",
         "expected": "single_exact_match"},
        {"match_type": "exact", "value": "Yacht", "entity": "STOCK_LOCATION",
         "expected": "exact_location_match"},
        {"match_type": "exact", "value": "1234", "entity": "FAULT_CODE",
         "expected": "exact_code_match"},

        # ILIKE match tests
        {"match_type": "ilike", "value": "fuel", "entity": "PART_NAME",
         "expected": "partial_match"},
        {"match_type": "ilike", "value": "engine", "entity": "FREE_TEXT",
         "expected": "partial_match"},
        {"match_type": "ilike", "value": "MTU", "entity": "MANUFACTURER",
         "expected": "partial_match"},

        # TRIGRAM match tests (fuzzy)
        {"match_type": "trigram", "value": "fule flter", "entity": "PART_NAME",
         "expected": "fuzzy_match"},
        {"match_type": "trigram", "value": "wtermaker", "entity": "EQUIPMENT_NAME",
         "expected": "fuzzy_match"},
    ]

    for _ in range(count // len(match_type_cases)):
        for case in match_type_cases:
            tests.append({
                "id": f"MT-{test_id}",
                "category": "match_type",
                "match_type": case["match_type"],
                "entity_type": case["entity"],
                "search_value": case["value"],
                "yacht_id": TEST_YACHT_ID,
                "expected_outcome": case["expected"],
                "description": f"{case['match_type'].upper()} match for {case['entity']}",
            })
            test_id += 1

    return tests[:count]


def generate_wave_budget_tests(count: int = 200) -> List[Dict]:
    """Generate tests for wave timing compliance."""
    tests = []
    test_id = 3000

    wave_scenarios = [
        {"wave": 0, "max_time_ms": 100, "entity": "PART_NUMBER", "value": "ENG-0008-103"},
        {"wave": 0, "max_time_ms": 100, "entity": "FAULT_CODE", "value": "1234"},
        {"wave": 1, "max_time_ms": 300, "entity": "PART_NAME", "value": "fuel filter"},
        {"wave": 1, "max_time_ms": 300, "entity": "EQUIPMENT_NAME", "value": "generator"},
        {"wave": 2, "max_time_ms": 800, "entity": "FREE_TEXT", "value": "maintenance"},
        {"wave": 2, "max_time_ms": 800, "entity": "DOCUMENT_QUERY", "value": "oil change"},
    ]

    for _ in range(count // len(wave_scenarios)):
        for scenario in wave_scenarios:
            tests.append({
                "id": f"WB-{test_id}",
                "category": "wave_budget",
                "wave": scenario["wave"],
                "max_time_ms": scenario["max_time_ms"],
                "entity_type": scenario["entity"],
                "search_value": scenario["value"],
                "yacht_id": TEST_YACHT_ID,
                "expected_outcome": "within_budget",
                "description": f"Wave {scenario['wave']} should complete within {scenario['max_time_ms']}ms",
            })
            test_id += 1

    return tests[:count]


def generate_security_tests(count: int = 200) -> List[Dict]:
    """Generate security tests for yacht_id enforcement."""
    tests = []
    test_id = 4000

    security_cases = [
        # Valid yacht_id tests
        {"yacht_id": TEST_YACHT_ID, "expected": "success"},

        # Invalid yacht_id tests
        {"yacht_id": None, "expected": "error_yacht_id"},
        {"yacht_id": "", "expected": "error_yacht_id"},
        {"yacht_id": "invalid-uuid", "expected": "error_yacht_id"},
        {"yacht_id": "12345678-1234-1234-1234-123456789abc", "expected": "empty_result"},

        # SQL injection attempts
        {"yacht_id": "'; DROP TABLE users; --", "expected": "error_yacht_id"},
        {"yacht_id": "1 OR 1=1", "expected": "error_yacht_id"},
    ]

    for _ in range(count // len(security_cases)):
        for case in security_cases:
            for entity_type in ["PART_NUMBER", "PART_NAME", "FAULT_CODE"]:
                tests.append({
                    "id": f"SEC-{test_id}",
                    "category": "security",
                    "entity_type": entity_type,
                    "search_value": random.choice(ENTITY_SAMPLES.get(entity_type, ["test"])),
                    "yacht_id": case["yacht_id"],
                    "expected_outcome": case["expected"],
                    "description": f"Security test: yacht_id={case['yacht_id'][:20] if case['yacht_id'] else 'None'}",
                })
                test_id += 1

    return tests[:count]


def generate_ranking_tests(count: int = 150) -> List[Dict]:
    """Generate tests for confidence scoring."""
    tests = []
    test_id = 5000

    ranking_cases = [
        # Exact match should have highest confidence
        {"entity": "PART_NUMBER", "value": "ENG-0008-103", "expected_confidence": "high"},

        # Partial match should have medium confidence
        {"entity": "PART_NAME", "value": "fuel", "expected_confidence": "medium"},

        # Fuzzy match should have lower confidence
        {"entity": "FREE_TEXT", "value": "engne", "expected_confidence": "low"},
    ]

    for _ in range(count // len(ranking_cases)):
        for case in ranking_cases:
            tests.append({
                "id": f"RNK-{test_id}",
                "category": "ranking",
                "entity_type": case["entity"],
                "search_value": case["value"],
                "yacht_id": TEST_YACHT_ID,
                "expected_confidence": case["expected_confidence"],
                "expected_outcome": "ranked_correctly",
                "description": f"Ranking test: {case['entity']} should have {case['expected_confidence']} confidence",
            })
            test_id += 1

    return tests[:count]


def generate_diversity_tests(count: int = 100) -> List[Dict]:
    """Generate tests for result diversity."""
    tests = []
    test_id = 6000

    diversity_cases = [
        {"entity": "FREE_TEXT", "value": "engine", "min_sources": 2},
        {"entity": "PART_NAME", "value": "filter", "min_sources": 2},
        {"entity": "DOCUMENT_QUERY", "value": "maintenance", "min_sources": 1},
    ]

    for _ in range(count // len(diversity_cases)):
        for case in diversity_cases:
            tests.append({
                "id": f"DIV-{test_id}",
                "category": "diversity",
                "entity_type": case["entity"],
                "search_value": case["value"],
                "yacht_id": TEST_YACHT_ID,
                "min_sources": case["min_sources"],
                "expected_outcome": "diverse_results",
                "description": f"Diversity test: {case['entity']} should return results from {case['min_sources']}+ sources",
            })
            test_id += 1

    return tests[:count]


def generate_edge_case_tests(count: int = 50) -> List[Dict]:
    """Generate edge case tests."""
    tests = []
    test_id = 7000

    edge_cases = [
        # Empty search value
        {"value": "", "expected": "error_validation"},

        # Very short search value
        {"value": "a", "expected": "empty_or_error"},

        # Very long search value
        {"value": "a" * 500, "expected": "empty_or_success"},

        # Special characters
        {"value": "<script>alert('xss')</script>", "expected": "empty_or_sanitized"},
        {"value": "'; DROP TABLE parts; --", "expected": "empty_or_sanitized"},

        # Unicode
        {"value": "fuel\u00e9", "expected": "empty_or_success"},
        {"value": "\ud83d\udd27", "expected": "empty_or_success"},

        # Numbers only
        {"value": "12345", "expected": "empty_or_success"},

        # All caps
        {"value": "FUEL FILTER", "expected": "case_insensitive_match"},

        # All lowercase
        {"value": "fuel filter", "expected": "case_insensitive_match"},
    ]

    for case in edge_cases:
        for entity_type in ["PART_NAME", "FREE_TEXT"]:
            tests.append({
                "id": f"EDGE-{test_id}",
                "category": "edge_case",
                "entity_type": entity_type,
                "search_value": case["value"],
                "yacht_id": TEST_YACHT_ID,
                "expected_outcome": case["expected"],
                "description": f"Edge case: {case['value'][:30]}...",
            })
            test_id += 1

    return tests[:count]


def generate_all_tests() -> Dict:
    """Generate all 1500 tests."""
    all_tests = []

    # Generate each category
    all_tests.extend(generate_entity_routing_tests(500))
    all_tests.extend(generate_match_type_tests(300))
    all_tests.extend(generate_wave_budget_tests(200))
    all_tests.extend(generate_security_tests(200))
    all_tests.extend(generate_ranking_tests(150))
    all_tests.extend(generate_diversity_tests(100))
    all_tests.extend(generate_edge_case_tests(50))

    # Summary
    summary = {
        "total_tests": len(all_tests),
        "categories": {
            "entity_routing": len([t for t in all_tests if t["category"] == "entity_routing"]),
            "match_type": len([t for t in all_tests if t["category"] == "match_type"]),
            "wave_budget": len([t for t in all_tests if t["category"] == "wave_budget"]),
            "security": len([t for t in all_tests if t["category"] == "security"]),
            "ranking": len([t for t in all_tests if t["category"] == "ranking"]),
            "diversity": len([t for t in all_tests if t["category"] == "diversity"]),
            "edge_case": len([t for t in all_tests if t["category"] == "edge_case"]),
        },
        "yacht_id": TEST_YACHT_ID,
        "generated_at": "2026-01-03",
    }

    return {
        "summary": summary,
        "tests": all_tests,
    }


if __name__ == "__main__":
    tests = generate_all_tests()

    # Save to file
    output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))tests/search_tests/search_tests_1500.json"
    with open(output_path, "w") as f:
        json.dump(tests, f, indent=2)

    print(f"Generated {tests['summary']['total_tests']} tests")
    print(f"Saved to: {output_path}")
    print()
    print("Category breakdown:")
    for cat, count in tests['summary']['categories'].items():
        print(f"  {cat}: {count}")
