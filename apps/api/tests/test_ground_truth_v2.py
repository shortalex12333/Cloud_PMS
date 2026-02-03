#!/usr/bin/env python3
"""
Ground Truth Test Runner for Natural Language Query Extraction
==============================================================
Tests the entity extraction pipeline against ground_truth_v2.json test cases.
Tracks accuracy by dimension (misspelling, time_frame, negative, etc.)

Run: python -m tests.test_ground_truth_v2
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the extraction pipeline
try:
    from extraction.regex_extractor import RegexExtractor
    from extraction.text_normalizer import TextNormalizer, normalize_for_matching
    NORMALIZER = TextNormalizer()
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Make sure you're running from the api directory.")
    sys.exit(1)

# Scoring categories
EXACT = "EXACT"       # Entity type and value both match perfectly
PARTIAL = "PARTIAL"   # Entity type matches, value is close
FUZZY = "FUZZY"       # Fuzzy match (e.g., misspelling corrected)
MISS = "MISS"         # Expected entity not found
FALSE_POS = "FALSE_POS"  # Extracted entity not in expected


def load_ground_truth() -> Dict:
    """Load ground truth test cases from JSON file."""
    gt_path = Path(__file__).parent / "ground_truth_v2.json"
    with open(gt_path, 'r') as f:
        return json.load(f)


def normalize_value(value: str) -> str:
    """Normalize value for comparison."""
    return value.lower().strip().replace('_', ' ').replace('-', ' ')


# Type mappings: ground_truth type -> extraction pipeline types that are equivalent
TYPE_ALIASES = {
    # Status types
    'status': ['stock_status', 'equipment_status', 'work_order_status', 'receiving_status', 'symptom', 'fault_classification'],
    'stock_status': ['status', 'inventory_status', 'stock_status'],
    'compliance': ['REST_COMPLIANCE', 'rest_compliance', 'compliance'],

    # Time types
    'time_ref': ['time_ref', 'time', 'date', 'duration'],

    # Location types
    'location': ['location_on_board', 'location'],

    # Person/role types
    'person': ['person', 'crew', 'role', 'org'],  # org added for name extraction
    'role': ['person', 'crew', 'role'],

    # Equipment/part types
    'part': ['equipment_type', 'part', 'component', 'equipment', 'subcomponent'],
    'equipment': ['equipment', 'equipment_type', 'system'],

    # Brand types
    'brand': ['brand', 'equipment_brand', 'org'],

    # Action types
    'action': ['action', 'work_order_status', 'fault_classification'],

    # Exclusion types
    'exclude': ['exclusion'],

    # Quantity/measurement types
    'quantity': ['quantity_comparison', 'measurement', 'stock_status'],  # stock_status for "zero stock"
    'measurement': ['measurement', 'quantity_comparison'],

    # Certificate/document types
    'certificate_type': ['document_type', 'certificate_type'],
    'certificate_id': ['document_id', 'certificate_number', 'po_number'],
    'certificate_name': ['certificate_name', 'document_type', 'brand'],
    'authority': ['issuing_authority', 'organization', 'org', 'brand'],

    # Priority/severity types
    'priority': ['priority', 'WARNING_SEVERITY', 'urgency_level'],
    'criticality': ['criticality', 'WARNING_SEVERITY', 'urgency_level'],

    # Work order types
    'work_order_type': ['work_order_status', 'type', 'action'],

    # Document types
    'po_number': ['po_number', 'document_id'],
    'part_number': ['part_number', 'identifier', 'po_number'],
    'part_number_prefix': ['part_number', 'identifier'],

    # Voyage types
    'voyage_type': ['voyage_type', 'location', 'REST_COMPLIANCE', 'location_on_board'],

    # System types
    'system_type': ['system_type', 'system', 'equipment_type', 'equipment'],
}

# Value mappings: ground_truth value -> extraction values that are equivalent
# NOTE: Equipment synonyms, plurals, and abbreviations are NOW handled by TextNormalizer
# This dict only contains SEMANTIC mappings that can't be derived algorithmically
VALUE_ALIASES = {
    # Stock status (semantic: different words same meaning)
    'out_of_stock': ['out of stock', 'no stock', 'zero stock', 'not in stock', 'none stock', 'none in stock'],
    'low_stock': ['low stock', 'stock low', 'running low', 'below minimum', 'critically low'],
    'in_stock': ['in stock', 'available', 'stocked', 'on hand'],

    # Work/equipment status (semantic states)
    'not_completed': ['not completed', 'incomplete', 'unfinished', 'uncompleted', 'not done'],
    'not_operational': ['not operational', 'inoperative', 'non-operational', 'out of service'],
    'non_compliant': ['non-compliant', 'non compliant', 'noncompliant'],
    'operational': ['operational', 'in service', 'online', 'running'],
    'failed': ['failed', 'failure', 'failing'],
    'degraded': ['degraded', 'degrading'],
    'maintenance': ['maintenance', 'under maintenance', 'being serviced'],
    'in_progress': ['in progress', 'in_progress', 'ongoing', 'active'],
    'completed': ['completed', 'complete', 'done', 'finished', 'completed_maintenance'],
    'planned': ['planned', 'scheduled'],
    'violation': ['violation', 'violations', 'breach', 'breaches', 'infringement'],
    'critical': ['critical', 'urgent', 'high priority'],

    # Time references (semantic)
    'overdue': ['overdue', 'past due', 'late', 'expired'],
    'this_week': ['this week'],
    'this_month': ['this month'],
    'last_week': ['last week'],
    'last_month': ['last month'],
    'last_7_days': ['last 7 days', '7 days ago'],
    '30_days': ['30 days', 'in 30 days', 'expiring in 30 days', 'within 30 days'],
    '90_days': ['90 days', 'in 90 days', 'expiring in 90 days', 'within 90 days'],
    'yesterday': ['yesterday'],
    'today': ['today'],
    'tomorrow': ['tomorrow'],

    # Voyage types (semantic)
    'at_sea': ['at sea', 'sea', 'underway', 'sailing', 'passage'],
    'in_port': ['in port', 'port', 'moored', 'docked', 'berthed'],

    # Quantity comparisons (symbolic -> natural language)
    '<5': ['below 5', 'less than 5', 'under 5', 'fewer than 5'],
    '>10': ['more than 10', 'greater than 10', 'over 10', 'above 10'],
    '0': ['zero', 'zero stock', 'no stock', 'none', '0'],
    '<10_hours': ['less than 10 hours', 'less than 10', 'under 10 hours'],

    # Certificate types (semantic - these are domain-specific)
    'class': ['class', 'classification'],
    'safety': ['safety', 'solas safety'],
    'environmental': ['environmental', 'iopp', 'ispp'],

    # Work order types (semantic)
    'corrective': ['corrective', 'corrective maintenance', 'repair'],
    'preventive': ['preventive', 'preventive maintenance', 'pm'],

    # Person names (partial name matching - semantic)
    'Captain James Mitchell': ['captain mitchell', 'captain james mitchell', 'capt mitchell', 'mitchell'],
    'First Officer Michael Thompson': ['first officer thompson', 'first officer michael thompson', '1st officer thompson', 'thompson'],

    # NOTE: The following are NOW handled by TextNormalizer automatically:
    # - Plurals: gaskets → gasket (singularization)
    # - Abbreviations: gen 1 → generator 1 (expansion)
    # - Synonyms: desalinator → watermaker (synonym mapping)
    # - Compounds: water maker → watermaker (normalization)
}


def extract_entities(extractor: RegexExtractor, query: str) -> List[Dict]:
    """Extract entities from query using the pipeline."""
    entities, spans = extractor.extract(query)  # Returns (entities, spans)
    result = []
    for e in entities:
        result.append({
            'type': e.type,
            'value': e.text,
            'confidence': e.confidence,
            'source': e.source
        })
    return result


def types_match(expected_type: str, extracted_type: str) -> bool:
    """Check if types match, considering aliases."""
    if expected_type == extracted_type:
        return True
    # Check if extracted type is in the aliases for expected type
    aliases = TYPE_ALIASES.get(expected_type, [])
    if extracted_type in aliases:
        return True
    # Also check reverse - if expected is in aliases of extracted
    aliases_reverse = TYPE_ALIASES.get(extracted_type, [])
    if expected_type in aliases_reverse:
        return True
    return False


def values_match(expected_value: str, extracted_value: str, entity_type: str = None) -> Tuple[bool, bool]:
    """
    Check if values match using intelligent normalization.
    Returns (exact_match, partial_match).

    Uses TextNormalizer for:
    - Pluralization (gaskets → gasket)
    - Abbreviation expansion (gen 1 → generator 1)
    - Synonym matching (desalinator → watermaker)
    """
    exp_norm = normalize_value(expected_value)
    ext_norm = normalize_value(extracted_value)

    # Direct match
    if exp_norm == ext_norm:
        return True, True

    # Use TextNormalizer for equipment/part entities
    if entity_type in ('equipment', 'part', 'equipment_type', 'system', 'system_type', None):
        exp_normalized = NORMALIZER.normalize_for_matching(expected_value)
        ext_normalized = NORMALIZER.normalize_for_matching(extracted_value)

        # Match after full normalization (handles plurals, abbreviations, synonyms)
        if exp_normalized == ext_normalized:
            return True, True

        # Partial match after normalization
        if exp_normalized in ext_normalized or ext_normalized in exp_normalized:
            return False, True

    # Check value aliases (for non-equipment types like status, time_ref)
    aliases = VALUE_ALIASES.get(expected_value, [])
    aliases_norm = [normalize_value(a) for a in aliases]
    if ext_norm in aliases_norm:
        return True, True

    # Partial match (substring)
    if exp_norm in ext_norm or ext_norm in exp_norm:
        return False, True

    # Check if any alias is a partial match
    for alias_norm in aliases_norm:
        if alias_norm in ext_norm or ext_norm in alias_norm:
            return False, True

    return False, False


def score_extraction(expected: List[Dict], extracted: List[Dict]) -> Dict:
    """
    Score extracted entities against expected.

    Returns:
        {
            'scores': [{'expected': {...}, 'extracted': {...}, 'result': 'EXACT|PARTIAL|MISS'}],
            'false_positives': [{'extracted': {...}}],
            'summary': {'exact': N, 'partial': N, 'fuzzy': N, 'miss': N, 'false_pos': N}
        }
    """
    scores = []
    matched_extracted = set()

    # Try to match each expected entity
    for exp in expected:
        best_match = None
        best_result = MISS
        best_score = 0  # 3=exact, 2=partial, 1=fuzzy

        for i, ext in enumerate(extracted):
            if i in matched_extracted:
                continue

            # Check for type match (with aliases)
            type_match = types_match(exp['type'], ext['type'])

            # Check for value match (with normalization)
            value_exact, value_partial = values_match(exp['value'], ext['value'], exp['type'])

            # Score based on matches
            if type_match and value_exact and best_score < 3:
                best_match = ext
                best_result = EXACT
                best_score = 3
                matched_extracted.add(i)
                break  # Perfect match, stop looking
            elif type_match and value_partial and best_score < 2:
                best_match = ext
                best_result = PARTIAL
                best_score = 2
                # Don't break - might find better match
            elif (value_exact or value_partial) and best_score < 1:
                # Value matches but type differs - fuzzy match
                best_match = ext
                best_result = FUZZY
                best_score = 1

        # If we found a match, mark it as used
        if best_match and best_score >= 1:
            idx = next(i for i, e in enumerate(extracted) if e == best_match)
            matched_extracted.add(idx)

        scores.append({
            'expected': {'type': exp['type'], 'value': exp['value']},
            'extracted': best_match,
            'result': best_result
        })

    # Find false positives (extracted but not expected)
    false_positives = []
    for i, ext in enumerate(extracted):
        if i not in matched_extracted:
            # Check if this is a useful extraction (not noise)
            if ext.get('confidence', 0) >= 0.3:  # Only count high-confidence extractions
                false_positives.append({'extracted': ext})

    # Calculate summary
    summary = {
        'exact': sum(1 for s in scores if s['result'] == EXACT),
        'partial': sum(1 for s in scores if s['result'] == PARTIAL),
        'fuzzy': sum(1 for s in scores if s['result'] == FUZZY),
        'miss': sum(1 for s in scores if s['result'] == MISS),
        'false_pos': len(false_positives)
    }

    return {
        'scores': scores,
        'false_positives': false_positives,
        'summary': summary
    }


def run_tests(verbose: bool = False, dimension_filter: str = None) -> Dict:
    """
    Run all ground truth tests.

    Args:
        verbose: Print details for each test
        dimension_filter: Only run tests for this dimension

    Returns:
        Results summary by dimension
    """
    ground_truth = load_ground_truth()
    extractor = RegexExtractor()

    results_by_dimension = defaultdict(lambda: {
        'total': 0,
        'exact': 0,
        'partial': 0,
        'fuzzy': 0,
        'miss': 0,
        'false_pos': 0,
        'tests': []
    })

    tests = ground_truth.get('tests', [])

    print(f"\n{'='*80}")
    print(f"RUNNING {len(tests)} GROUND TRUTH TESTS")
    print(f"{'='*80}")

    for test in tests:
        test_id = test['id']
        dimension = test['dimension']
        lens = test['lens']
        query = test['query']
        expected = test['expected']

        # Apply dimension filter if specified
        if dimension_filter and dimension != dimension_filter:
            continue

        # Extract entities
        extracted = extract_entities(extractor, query)

        # Score the extraction
        result = score_extraction(expected, extracted)

        # Update dimension stats
        dim_results = results_by_dimension[dimension]
        dim_results['total'] += len(expected)
        dim_results['exact'] += result['summary']['exact']
        dim_results['partial'] += result['summary']['partial']
        dim_results['fuzzy'] += result['summary']['fuzzy']
        dim_results['miss'] += result['summary']['miss']
        dim_results['false_pos'] += result['summary']['false_pos']

        # Store test details
        dim_results['tests'].append({
            'id': test_id,
            'query': query,
            'result': result
        })

        # Print verbose output
        if verbose:
            status = 'PASS' if result['summary']['miss'] == 0 else 'FAIL'
            print(f"\n[{status}] {test_id} ({dimension})")
            print(f"  Query: {query}")
            for score in result['scores']:
                exp = score['expected']
                ext = score['extracted']
                res = score['result']
                if ext:
                    print(f"  {res}: {exp['type']}:'{exp['value']}' → {ext['type']}:'{ext['value']}'")
                else:
                    print(f"  {res}: {exp['type']}:'{exp['value']}' → NOT FOUND")
            for fp in result['false_positives'][:3]:  # Limit false positives shown
                ext = fp['extracted']
                print(f"  FALSE_POS: {ext['type']}:'{ext['value']}'")

    return dict(results_by_dimension)


def print_summary(results: Dict):
    """Print a summary of test results by dimension."""
    print(f"\n{'='*80}")
    print("RESULTS BY DIMENSION")
    print(f"{'='*80}")

    total_expected = 0
    total_exact = 0
    total_partial = 0
    total_fuzzy = 0
    total_miss = 0
    total_false_pos = 0

    for dimension, stats in sorted(results.items()):
        total = stats['total']
        exact = stats['exact']
        partial = stats['partial']
        fuzzy = stats['fuzzy']
        miss = stats['miss']
        false_pos = stats['false_pos']

        accuracy = (exact + partial + fuzzy) / total * 100 if total > 0 else 0

        print(f"\n{dimension}:")
        print(f"  Total expected: {total}")
        print(f"  Exact:          {exact} ({exact/total*100:.1f}%)" if total > 0 else "  Exact: 0")
        print(f"  Partial:        {partial} ({partial/total*100:.1f}%)" if total > 0 else "  Partial: 0")
        print(f"  Fuzzy:          {fuzzy} ({fuzzy/total*100:.1f}%)" if total > 0 else "  Fuzzy: 0")
        print(f"  Miss:           {miss} ({miss/total*100:.1f}%)" if total > 0 else "  Miss: 0")
        print(f"  False Pos:      {false_pos}")
        print(f"  Accuracy:       {accuracy:.1f}%")

        # Show failed tests
        failed = [t for t in stats['tests'] if t['result']['summary']['miss'] > 0]
        if failed:
            print(f"  Failed tests:")
            for t in failed[:5]:  # Limit to 5
                print(f"    - {t['id']}: {t['query']}")

        total_expected += total
        total_exact += exact
        total_partial += partial
        total_fuzzy += fuzzy
        total_miss += miss
        total_false_pos += false_pos

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")

    overall_accuracy = (total_exact + total_partial + total_fuzzy) / total_expected * 100 if total_expected > 0 else 0
    exact_accuracy = total_exact / total_expected * 100 if total_expected > 0 else 0

    print(f"Total expected entities: {total_expected}")
    print(f"Exact matches:           {total_exact} ({exact_accuracy:.1f}%)")
    print(f"Partial matches:         {total_partial}")
    print(f"Fuzzy matches:           {total_fuzzy}")
    print(f"Misses:                  {total_miss}")
    print(f"False positives:         {total_false_pos}")
    print(f"\nOVERALL ACCURACY: {overall_accuracy:.1f}%")
    print(f"EXACT ACCURACY:   {exact_accuracy:.1f}%")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run ground truth tests for entity extraction')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output for each test')
    parser.add_argument('-d', '--dimension', type=str, help='Only run tests for this dimension')
    args = parser.parse_args()

    results = run_tests(verbose=args.verbose, dimension_filter=args.dimension)
    print_summary(results)


if __name__ == '__main__':
    main()
