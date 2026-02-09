#!/usr/bin/env python3
"""
Document Lens - Entity Extraction Pipeline Tests
=================================================

Tests extraction through the ACTUAL pipeline (regex_extractor.py).
Covers: Normal paths, edge cases, stress patterns, failure modes.

Run: python3 tests/entity_extraction/test_document_lens_extraction_pipeline.py
"""

import sys
import os

# Add apps/api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'api'))

from extraction.regex_extractor import RegexExtractor

# Initialize extractor
extractor = RegexExtractor()


def test_extract(query: str, expected_types: list, test_name: str) -> dict:
    """Run extraction and check results."""
    # extract() returns (entities, covered_spans)
    entities, _ = extractor.extract(query)

    found_types = set()
    found_values = {}

    for entity in entities:
        entity_type = entity.type
        entity_text = entity.text
        found_types.add(entity_type)
        if entity_type not in found_values:
            found_values[entity_type] = []
        found_values[entity_type].append(entity_text)

    # Check expected types found
    missing = set(expected_types) - found_types
    passed = len(missing) == 0

    return {
        'test': test_name,
        'query': query,
        'expected': expected_types,
        'found_types': list(found_types),
        'found_values': found_values,
        'missing': list(missing),
        'passed': passed
    }


def print_result(r: dict):
    """Print test result."""
    status = "✅ PASS" if r['passed'] else "❌ FAIL"
    print(f"\n{status}: {r['test']}")
    print(f"  Query: \"{r['query']}\"")
    print(f"  Expected: {r['expected']}")
    print(f"  Found: {r['found_types']}")
    if r['found_values']:
        for t, vals in r['found_values'].items():
            print(f"    {t}: {vals}")
    if r['missing']:
        print(f"  ⚠️ MISSING: {r['missing']}")


# ============================================================================
# TEST SUITE
# ============================================================================

results = []

print("=" * 70)
print("DOCUMENT LENS - ENTITY EXTRACTION PIPELINE TESTS")
print("=" * 70)


# ----------------------------------------------------------------------------
# SECTION 1: NORMAL PATH - document_type extraction
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 1: document_type - Normal Path")
print("=" * 70)

normal_doc_type_tests = [
    ("find the service manual for the generator", ["document_type"], "Basic manual query"),
    ("where is the wiring diagram", ["document_type"], "Diagram query"),
    ("show me the safety certificate", ["document_type"], "Certificate query"),
    ("I need the parts catalog", ["document_type"], "Catalog query"),
    ("get the maintenance log for engine room", ["document_type"], "Log query"),
    ("show solas certificate", ["document_type"], "SOLAS cert query"),
    ("find the fire control plan", ["document_type"], "Fire plan query"),
    ("where is the annual survey report", ["document_type"], "Survey query"),
]

for query, expected, name in normal_doc_type_tests:
    r = test_extract(query, expected, name)
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 2: NORMAL PATH - document_id extraction
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 2: document_id - Normal Path")
print("=" * 70)

normal_doc_id_tests = [
    ("find document CERT-12345", ["document_id"], "CERT pattern"),
    ("look up IMO-1234567", ["document_id"], "IMO pattern"),
    ("get DNV-123456 certificate", ["document_id"], "DNV class society"),
    ("find LR-12345", ["document_id"], "Lloyd's Register"),
    ("document REV-2.1", ["document_id"], "Revision pattern"),
    ("ISM-12345 audit report", ["document_id"], "ISM pattern"),
    ("SMC-12345 certificate", ["document_id"], "SMC pattern"),
    ("ABS-123456 class cert", ["document_id"], "ABS pattern"),
]

for query, expected, name in normal_doc_id_tests:
    r = test_extract(query, expected, name)
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 3: COMBINED - document_type + document_id
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 3: Combined Extraction")
print("=" * 70)

combined_tests = [
    ("find DNV-123456 loadline certificate", ["document_id", "document_type"], "Class cert with ID"),
    ("get IMO-9876543 safety certificate", ["document_id", "document_type"], "IMO + safety cert"),
    ("where is the ABS-789012 annual survey report", ["document_id", "document_type"], "ABS + survey"),
    ("need ISM-2024-001 safety management certificate", ["document_id", "document_type"], "ISM + SMC"),
]

for query, expected, name in combined_tests:
    r = test_extract(query, expected, name)
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 4: EDGE CASES - Boundary conditions
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 4: Edge Cases")
print("=" * 70)

edge_case_tests = [
    # Case sensitivity
    ("FIND THE SERVICE MANUAL", ["document_type"], "All caps query"),
    ("dnv-123456 certificate", ["document_id", "document_type"], "Lowercase document_id"),

    # Minimal queries
    ("manual", ["document_type"], "Single word - manual"),
    ("certificate", ["document_type"], "Single word - certificate"),
    ("schematic", ["document_type"], "Single word - schematic"),

    # Multi-word document types
    ("cargo ship safety certificate", ["document_type"], "Multi-word doc type"),
    ("ballast water record book", ["document_type"], "Complex doc type"),
    ("continuous synopsis record", ["document_type"], "CSR document"),

    # Boundary lengths
    ("IMO-1234567", ["document_id"], "Exactly 7 digits (IMO)"),
    ("CERT-1234", ["document_id"], "Min length cert"),
    ("CERT-12345678", ["document_id"], "Max length cert"),
]

for query, expected, name in edge_case_tests:
    r = test_extract(query, expected, name)
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 5: CHAOTIC INPUT - Typos, noise, unusual formatting
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 5: Chaotic Input")
print("=" * 70)

chaotic_tests = [
    # Typos (should still work if core pattern matches)
    ("find teh service mannual", [], "Typos - may not match"),
    ("certifcate for DNV-123456", ["document_id"], "Typo but ID matches"),

    # Extra punctuation
    ("find the manual!!!", ["document_type"], "Extra punctuation"),
    ("(certificate) for vessel", ["document_type"], "Parentheses"),
    ("manual - generator - caterpillar", ["document_type"], "Dashes"),

    # Mixed content
    ("email about IMO-1234567 certificate renewal", ["document_id", "document_type"], "Email context"),
    ("crew asking about safety certificate location", ["document_type"], "Conversational"),

    # Unicode/special chars
    ("Wärtsilä manual", ["document_type"], "Umlaut in query"),

    # Very long query
    ("I am looking for the service manual for the main engine which is a Caterpillar 3516C and I believe the document number is DNV-123456",
     ["document_type", "document_id", "equipment"], "Long complex query"),
]

for query, expected, name in chaotic_tests:
    r = test_extract(query, expected, name)
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 6: NEGATIVE TESTS - Should NOT extract document entities
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 6: Negative Tests (Should NOT match document entities)")
print("=" * 70)

negative_tests = [
    ("oil filter for caterpillar", [], "Part query - no document"),
    ("engine temperature too high", [], "Symptom - no document"),
    ("work order 12345", [], "Work order - not document_id"),
    ("buy more coolant", [], "Shopping - no document"),
]

for query, expected, name in negative_tests:
    r = test_extract(query, expected, name)
    # For negative tests, pass if document_type and document_id NOT found
    doc_types_found = 'document_type' in r['found_types'] or 'document_id' in r['found_types']
    r['passed'] = not doc_types_found
    if doc_types_found:
        r['missing'] = ['UNEXPECTED: document entities found when none expected']
    results.append(r)
    print_result(r)


# ----------------------------------------------------------------------------
# SECTION 7: STRESS PATTERNS - High volume extraction
# ----------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SECTION 7: Stress Test - Pattern Matching Performance")
print("=" * 70)

import time

stress_queries = [
    "find the manual",
    "DNV-123456 certificate",
    "where is the schematic",
    "IMO-1234567 safety cert",
    "get loadline certificate",
] * 100  # 500 queries

start = time.time()
for q in stress_queries:
    extractor.extract(q)
elapsed = time.time() - start

stress_result = {
    'test': f"Stress: 500 extractions",
    'query': f"{len(stress_queries)} queries",
    'expected': ['< 10 seconds'],
    'found_types': [f"{elapsed:.2f} seconds"],
    'found_values': {'avg_ms': [f"{elapsed/len(stress_queries)*1000:.2f}ms"]},
    'missing': [],
    'passed': elapsed < 10.0  # Relaxed threshold for CI variability
}
results.append(stress_result)
print_result(stress_result)


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

passed = sum(1 for r in results if r['passed'])
failed = sum(1 for r in results if not r['passed'])
total = len(results)

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed} ({passed/total*100:.1f}%)")
print(f"Failed: {failed} ({failed/total*100:.1f}%)")

if failed > 0:
    print("\n⚠️ FAILED TESTS:")
    for r in results:
        if not r['passed']:
            print(f"  - {r['test']}: {r['query']}")
            if r['missing']:
                print(f"    Missing: {r['missing']}")

print("\n" + "=" * 70)
if failed == 0:
    print("✅ ALL TESTS PASSED - Entity extraction ready")
    sys.exit(0)
else:
    print(f"❌ {failed} TESTS FAILED - Review issues above")
    sys.exit(1)
