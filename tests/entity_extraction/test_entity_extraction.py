#!/usr/bin/env python3
"""
Comprehensive Entity Extraction Test Suite
==========================================

This test suite validates:
1. No false positive substring matches (e.g., "vent" in "inventory")
2. Correct entity type assignment
3. Weight consistency
4. Regression tests for fixed bugs
5. Edge cases and boundary conditions

Run with: python -m pytest tests/entity_extraction/test_entity_extraction.py -v
Or standalone: python tests/entity_extraction/test_entity_extraction.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api"))

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Import extractor
from api.module_b_entity_extractor import MaritimeEntityExtractor, EntityDetection


@dataclass
class TestCase:
    """Test case definition."""
    query: str
    expected_entities: List[Dict]  # [{"type": "brand", "value": "MTU", "canonical": "MTU"}]
    forbidden_matches: List[str]   # Terms that should NOT be extracted
    description: str


# =============================================================================
# TEST CASES: FALSE POSITIVE PREVENTION
# =============================================================================
# These test substring matching bugs - terms should NOT match inside words

SUBSTRING_FALSE_POSITIVE_TESTS = [
    # "vent" should NOT match inside these words
    TestCase(
        query="inventory box 3d",
        expected_entities=[{"type": "location", "canonical": "BOX_3D"}],
        forbidden_matches=["vent", "VENT", "vent_system", "VENT_SYSTEM"],
        description="'vent' should not match inside 'inventory'"
    ),
    TestCase(
        query="eventually the system failed",
        expected_entities=[],
        forbidden_matches=["vent", "VENT", "VENT_SYSTEM"],
        description="'vent' should not match inside 'eventually'"
    ),
    TestCase(
        query="prevent overheating by checking coolant",
        expected_entities=[],  # "overheating" may or may not extract standalone
        forbidden_matches=["vent", "VENT", "VENT_SYSTEM"],
        description="'vent' should not match inside 'prevent'"
    ),
    TestCase(
        query="adventure cruising requires maintenance",
        expected_entities=[],
        forbidden_matches=["vent", "VENT", "VENT_SYSTEM"],
        description="'vent' should not match inside 'adventure'"
    ),
    TestCase(
        query="convention for naming parts",
        expected_entities=[],
        forbidden_matches=["vent", "VENT", "co", "CO", "VENT_SYSTEM", "CARBON_MONOXIDE"],
        description="'vent' and 'co' should not match inside 'convention'"
    ),

    # "co" should NOT match inside these words
    TestCase(
        query="cooling system maintenance",
        expected_entities=[],
        forbidden_matches=["co", "CO", "carbon_monoxide", "CARBON_MONOXIDE"],
        description="'co' should not match inside 'cooling'"
    ),
    TestCase(
        query="precool the engine before starting",
        expected_entities=[{"type": "equipment", "value": "engine"}],
        forbidden_matches=["co", "CO", "CARBON_MONOXIDE"],
        description="'co' should not match inside 'precool'"
    ),

    # "run" should NOT match inside these words
    TestCase(
        query="running diagnostics on generator",
        expected_entities=[{"type": "equipment", "value": "generator"}],
        forbidden_matches=["run_operation", "RUN_OPERATION"],
        description="'run' should not match inside 'running'"
    ),
    TestCase(
        query="runner bearing needs replacement",
        expected_entities=[{"type": "part", "value": "bearing"}],
        forbidden_matches=["run_operation", "RUN_OPERATION"],
        description="'run' should not match inside 'runner'"
    ),
    TestCase(
        query="overrun condition on generator",
        expected_entities=[{"type": "equipment", "value": "generator"}],
        forbidden_matches=["run_operation", "RUN_OPERATION"],
        description="'run' should not match inside 'overrun'"
    ),

    # "test" should NOT match inside these words
    TestCase(
        query="testing complete for all systems",
        expected_entities=[],
        forbidden_matches=["test_mode", "TEST_MODE"],
        description="'test' should not match inside 'testing'"
    ),
    TestCase(
        query="contest winner announced",
        expected_entities=[],
        forbidden_matches=["test", "TEST_MODE", "co", "CARBON_MONOXIDE"],
        description="'test' and 'co' should not match inside 'contest'"
    ),

    # "set" should NOT match inside these words
    TestCase(
        query="setting parameter values",
        expected_entities=[],
        forbidden_matches=["set_parameter", "SET_PARAMETER"],
        description="'set' should not match inside 'setting'"
    ),
    TestCase(
        query="offset value needs adjustment",
        expected_entities=[],
        forbidden_matches=["set_parameter", "SET_PARAMETER"],
        description="'set' should not match inside 'offset'"
    ),

    # "open" should NOT match inside these words
    TestCase(
        query="opening the valve slowly",
        expected_entities=[{"type": "equipment", "value": "valve"}],
        forbidden_matches=["open_menu", "OPEN_MENU"],
        description="'open' should not match inside 'opening'"
    ),
    TestCase(
        query="door opener mechanism",
        expected_entities=[],
        forbidden_matches=["open_menu", "OPEN_MENU"],
        description="'open' should not match inside 'opener'"
    ),

    # "filter" should NOT match inside these words
    TestCase(
        query="filtered water supply",
        expected_entities=[],
        forbidden_matches=["filter_fluid", "FILTER_FLUID"],
        description="'filter' should not match inside 'filtered'"
    ),
    TestCase(
        query="filtering process ongoing",
        expected_entities=[],
        forbidden_matches=["filter_fluid", "FILTER_FLUID"],
        description="'filter' should not match inside 'filtering'"
    ),

    # "manual" should NOT match inside these words
    TestCase(
        query="manufacture date unknown",
        expected_entities=[],
        forbidden_matches=["manual_mode", "MANUAL_MODE"],
        description="'manual' should not match inside 'manufacture'"
    ),

    # Fault code patterns should not match false positives
    TestCase(
        query="temperature 85 celsius",
        expected_entities=[],
        forbidden_matches=["E85", "E-85", "fault_code"],
        description="'e 85' should not match as fault code in 'temperature 85'"
    ),
]


# =============================================================================
# TEST CASES: TRUE POSITIVE DETECTION
# =============================================================================
# These tests verify that legitimate entities ARE detected

TRUE_POSITIVE_TESTS = [
    # Brands
    TestCase(
        query="MTU 16V4000 engine overheating",
        expected_entities=[
            {"type": "brand", "value": "MTU"},
            {"type": "model", "value": "16V4000"},
            # Note: "engine overheating" may extract as compound symptom
        ],
        forbidden_matches=[],
        description="Should extract brand and model"
    ),
    TestCase(
        query="Caterpillar 3512 generator fault",
        expected_entities=[
            {"type": "brand", "canonical": "CATERPILLAR"},
            {"type": "equipment", "value": "generator"},
        ],
        forbidden_matches=[],
        description="Should extract Caterpillar brand and generator"
    ),
    TestCase(
        query="Seakeeper stabilizer not working",
        expected_entities=[
            {"type": "brand", "value": "Seakeeper"},
            {"type": "equipment", "value": "stabilizer"},
        ],
        forbidden_matches=[],
        description="Should extract Seakeeper brand"
    ),
    TestCase(
        query="Furuno radar display error",
        expected_entities=[
            {"type": "brand", "value": "Furuno"},
            {"type": "equipment", "value": "radar"},
        ],
        forbidden_matches=[],
        description="Should extract Furuno brand and radar"
    ),

    # Equipment types
    TestCase(
        query="generator not starting",
        expected_entities=[{"type": "equipment", "value": "generator"}],
        forbidden_matches=[],
        description="Should extract generator as equipment"
    ),
    TestCase(
        query="watermaker membrane replacement",
        expected_entities=[
            {"type": "equipment", "value": "watermaker"},
            {"type": "part", "value": "membrane"},
        ],
        forbidden_matches=[],
        description="Should extract watermaker and membrane"
    ),
    TestCase(
        query="bilge pump failure",
        expected_entities=[{"type": "equipment", "canonical": "BILGE_PUMP"}],
        forbidden_matches=[],
        description="Should extract bilge pump as equipment"
    ),

    # Parts
    TestCase(
        query="impeller needs replacement",
        expected_entities=[{"type": "part", "value": "impeller"}],
        forbidden_matches=[],
        description="Should extract impeller as part"
    ),
    TestCase(
        query="replace the bearing",
        expected_entities=[{"type": "part", "value": "bearing"}],
        forbidden_matches=["BEARING_READING"],  # Should be part, not measurement
        description="Should extract bearing as part"
    ),

    # Symptoms / Measurements
    TestCase(
        query="generator vibration detected",
        expected_entities=[
            {"type": "equipment", "value": "generator"},
            {"type": "measurement_term", "value": "vibration"},  # vibration is measured, so measurement_term
        ],
        forbidden_matches=[],
        description="Should extract generator and vibration as measurement_term"
    ),
    TestCase(
        query="coolant leak detected",
        expected_entities=[{"type": "symptom", "value": "leak"}],
        forbidden_matches=[],
        description="Should extract leak as symptom"
    ),

    # Fault codes
    TestCase(
        query="error code E-15 on radar",
        expected_entities=[
            {"type": "fault_code", "canonical": "E-15"},
            {"type": "equipment", "value": "radar"},
        ],
        forbidden_matches=[],
        description="Should extract E-15 fault code"
    ),
    TestCase(
        query="SPN 100 FMI 3 fault",
        expected_entities=[{"type": "fault_code"}],
        forbidden_matches=[],
        description="Should extract J1939 SPN/FMI fault code"
    ),

    # Measurements
    TestCase(
        query="voltage reading 24V",
        expected_entities=[{"type": "measurement"}],
        forbidden_matches=[],
        description="Should extract voltage measurement"
    ),
    TestCase(
        query="temperature 85°C on generator",
        expected_entities=[
            {"type": "equipment", "value": "generator"},
            {"type": "measurement"},
        ],
        forbidden_matches=["E85", "fault_code"],  # Should NOT match E85
        description="Should extract temperature measurement, not fault code"
    ),

    # Context-aware extractions
    TestCase(
        query="MTU 16V4000 manual",
        expected_entities=[
            {"type": "brand", "value": "MTU"},
            {"type": "model", "value": "16V4000"},
            {"type": "document_type", "canonical": "MANUAL"},
        ],
        forbidden_matches=["MANUAL_MODE"],  # Should NOT be a fault mode
        description="'manual' after brand should be document_type, not fault"
    ),
    TestCase(
        query="oil filter replacement",
        expected_entities=[{"type": "equipment", "canonical": "OIL_FILTER"}],
        forbidden_matches=[],
        description="Should extract 'oil filter' as single equipment entity"
    ),
    TestCase(
        query="fuel filter clogged",
        expected_entities=[{"type": "equipment", "canonical": "FUEL_FILTER"}],
        forbidden_matches=[],
        description="Should extract 'fuel filter' as equipment"
    ),

    # Location patterns
    TestCase(
        query="check box 3d for spare parts",
        expected_entities=[{"type": "location", "canonical": "BOX_3D"}],
        forbidden_matches=[],
        description="Should extract 'box 3d' as location"
    ),
    TestCase(
        query="locker A2 inventory",
        expected_entities=[{"type": "location", "canonical": "LOCKER_A2"}],
        forbidden_matches=["vent", "VENT_SYSTEM"],  # Should NOT match "vent" in "inventory"
        description="Should extract 'locker A2' as location"
    ),
]


# =============================================================================
# TEST CASES: WEIGHT CONSISTENCY
# =============================================================================

WEIGHT_TESTS = [
    # Higher weights for more specific entities
    ("brand", 3.0, 4.0),       # Brands should have weight 3.0-4.0
    ("model", 3.5, 4.5),       # Models should have weight 3.5-4.5
    ("fault_code", 4.0, 5.0),  # Fault codes should have highest weight
    ("symptom", 3.5, 4.5),     # Symptoms are important diagnostics
    ("equipment", 2.5, 3.5),   # Equipment types
    ("part", 2.5, 3.5),        # Parts
    ("location", 1.5, 2.5),    # Locations
    ("document_type", 2.5, 3.5), # Document types
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class EntityExtractionTestRunner:
    """Test runner for entity extraction validation."""

    def __init__(self):
        self.extractor = MaritimeEntityExtractor()
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "failures": []
        }

    def run_test(self, test: TestCase) -> Tuple[bool, str]:
        """Run a single test case."""
        entities = self.extractor.extract_entities(test.query)

        errors = []

        # Check forbidden matches (false positives)
        for forbidden in test.forbidden_matches:
            for entity in entities:
                if (forbidden.lower() in entity.value.lower() or
                    forbidden.lower() in entity.canonical.lower()):
                    errors.append(f"Forbidden match '{forbidden}' found: {entity.type}:{entity.value}→{entity.canonical}")

        # Check expected entities
        for expected in test.expected_entities:
            found = False
            for entity in entities:
                match = True
                for key, value in expected.items():
                    if key == "type" and entity.type != value:
                        match = False
                    elif key == "value" and value.lower() not in entity.value.lower():
                        match = False
                    elif key == "canonical" and value not in entity.canonical:
                        match = False
                if match:
                    found = True
                    break

            if not found:
                errors.append(f"Expected entity not found: {expected}")

        if errors:
            return False, "; ".join(errors)
        return True, "OK"

    def run_all_tests(self) -> Dict:
        """Run all test suites."""
        print("=" * 80)
        print("ENTITY EXTRACTION TEST SUITE")
        print("=" * 80)

        # Run false positive tests
        print("\n### 1. FALSE POSITIVE PREVENTION TESTS ###")
        for test in SUBSTRING_FALSE_POSITIVE_TESTS:
            passed, message = self.run_test(test)
            if passed:
                print(f"  ✓ PASS: {test.description}")
                self.results["passed"] += 1
            else:
                print(f"  ✗ FAIL: {test.description}")
                print(f"         Query: '{test.query}'")
                print(f"         Error: {message}")
                self.results["failed"] += 1
                self.results["failures"].append({
                    "test": test.description,
                    "query": test.query,
                    "error": message
                })

        # Run true positive tests
        print("\n### 2. TRUE POSITIVE DETECTION TESTS ###")
        for test in TRUE_POSITIVE_TESTS:
            passed, message = self.run_test(test)
            if passed:
                print(f"  ✓ PASS: {test.description}")
                self.results["passed"] += 1
            else:
                print(f"  ✗ FAIL: {test.description}")
                print(f"         Query: '{test.query}'")
                print(f"         Error: {message}")
                self.results["failed"] += 1
                self.results["failures"].append({
                    "test": test.description,
                    "query": test.query,
                    "error": message
                })

        # Run weight consistency tests
        print("\n### 3. WEIGHT CONSISTENCY TESTS ###")
        for entity_type, min_weight, max_weight in WEIGHT_TESTS:
            # Find entities of this type from previous tests
            test_queries = {
                "brand": "MTU generator",
                "model": "16V4000 engine",
                "fault_code": "error code E-15",
                "symptom": "engine overheating",
                "equipment": "generator maintenance",
                "part": "impeller replacement",
                "location": "check box 3d",
                "document_type": "MTU manual",
            }

            query = test_queries.get(entity_type, "")
            if query:
                entities = self.extractor.extract_entities(query)
                for entity in entities:
                    if entity.type == entity_type:
                        weight = entity.to_dict()["weight"]
                        if min_weight <= weight <= max_weight:
                            print(f"  ✓ PASS: {entity_type} weight {weight} in range [{min_weight}, {max_weight}]")
                            self.results["passed"] += 1
                        else:
                            print(f"  ✗ FAIL: {entity_type} weight {weight} NOT in range [{min_weight}, {max_weight}]")
                            self.results["failed"] += 1
                        break
                else:
                    print(f"  ? SKIP: No {entity_type} entity found in '{query}'")
                    self.results["warnings"] += 1

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        total = self.results["passed"] + self.results["failed"]
        print(f"  Passed:   {self.results['passed']}/{total}")
        print(f"  Failed:   {self.results['failed']}/{total}")
        print(f"  Warnings: {self.results['warnings']}")

        if self.results["failures"]:
            print("\n### FAILURES ###")
            for failure in self.results["failures"]:
                print(f"  - {failure['test']}")
                print(f"    Query: {failure['query']}")
                print(f"    Error: {failure['error']}")

        return self.results


# =============================================================================
# PYTEST INTEGRATION
# =============================================================================

def test_substring_false_positives():
    """Test that substring patterns don't cause false positives."""
    extractor = MaritimeEntityExtractor()

    for test in SUBSTRING_FALSE_POSITIVE_TESTS:
        entities = extractor.extract_entities(test.query)
        for forbidden in test.forbidden_matches:
            for entity in entities:
                assert forbidden.lower() not in entity.value.lower(), \
                    f"False positive: '{forbidden}' found in '{test.query}' as {entity.type}:{entity.value}"
                assert forbidden.lower() not in entity.canonical.lower(), \
                    f"False positive: '{forbidden}' found in canonical '{entity.canonical}'"


def test_true_positive_detection():
    """Test that legitimate entities are detected."""
    extractor = MaritimeEntityExtractor()

    for test in TRUE_POSITIVE_TESTS:
        entities = extractor.extract_entities(test.query)

        for expected in test.expected_entities:
            found = False
            for entity in entities:
                match = True
                for key, value in expected.items():
                    if key == "type" and entity.type != value:
                        match = False
                    elif key == "value" and value.lower() not in entity.value.lower():
                        match = False
                    elif key == "canonical" and value not in entity.canonical:
                        match = False
                if match:
                    found = True
                    break

            assert found, f"Expected {expected} not found in entities from '{test.query}'"


def test_weight_ranges():
    """Test that entity weights are within expected ranges."""
    extractor = MaritimeEntityExtractor()

    test_queries = {
        "brand": ("MTU generator", 3.0, 4.0),
        "equipment": ("generator maintenance", 2.5, 3.5),
        "symptom": ("engine overheating", 3.5, 4.5),
    }

    for entity_type, (query, min_w, max_w) in test_queries.items():
        entities = extractor.extract_entities(query)
        for entity in entities:
            if entity.type == entity_type:
                weight = entity.to_dict()["weight"]
                assert min_w <= weight <= max_w, \
                    f"{entity_type} weight {weight} not in [{min_w}, {max_w}]"


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    runner = EntityExtractionTestRunner()
    results = runner.run_all_tests()

    # Exit with error code if tests failed
    if results["failed"] > 0:
        sys.exit(1)
    sys.exit(0)
