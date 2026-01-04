#!/usr/bin/env python3
"""
Local Lane Validation Test
===========================

Tests lane routing logic directly against microaction_service.route_to_lane()
without needing HTTP server or JWT authentication.

Usage:
    python3 tests/local_lane_validator.py

Outputs validation results showing lane accuracy, misroutes, and Hard FP detection.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Add api/ to path
api_dir = Path(__file__).parent.parent / 'api'
sys.path.insert(0, str(api_dir))

# Import the routing function directly
from microaction_service import route_to_lane

# ============================================================================
# LOAD STRESS TEST DATASET
# ============================================================================

def load_stress_test():
    """Load the 600-query stress test dataset"""
    dataset_path = Path(__file__).parent / 'stress_test_600.jsonl'
    queries = []
    with open(dataset_path) as f:
        for line in f:
            queries.append(json.loads(line))
    return queries


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

def validate_routing(queries):
    """Validate routing for all queries"""
    results = {
        'total': len(queries),
        'correct': 0,
        'misroutes': [],
        'hard_fp': [],  # State-changing action executed without intent (SACRED = 0)
        'by_expected_lane': defaultdict(lambda: {'total': 0, 'correct': 0}),
        'by_actual_lane': defaultdict(int),
        'by_reason': defaultdict(int),
    }

    for q in queries:
        query_id = q['id']
        query = q['query']
        expected_lane = q['labels']['expected_lane']
        lane_reason = q['labels']['lane_reason']
        expected_action = q['labels'].get('expected_action', 'unknown')
        is_trap = q['labels'].get('is_false_positive_trap', False)

        # Call the actual routing function
        try:
            routing = route_to_lane(query)
            actual_lane = routing.get('lane', 'UNKNOWN')
            actual_reason = routing.get('lane_reason', 'unknown')
        except Exception as e:
            actual_lane = 'ERROR'
            actual_reason = str(e)

        # Track stats
        results['by_expected_lane'][expected_lane]['total'] += 1
        results['by_actual_lane'][actual_lane] += 1
        results['by_reason'][actual_reason] += 1

        # Check correctness
        is_correct = (actual_lane == expected_lane)

        # Special handling for BLOCKED: if we expected BLOCKED and got NO_LLM, that's a failure
        # If we expected GPT but got NO_LLM for simple queries, that may be acceptable

        if is_correct:
            results['correct'] += 1
            results['by_expected_lane'][expected_lane]['correct'] += 1
        else:
            misroute = {
                'id': query_id,
                'query': query[:80] + ('...' if len(query) > 80 else ''),
                'expected_lane': expected_lane,
                'actual_lane': actual_lane,
                'expected_reason': lane_reason,
                'actual_reason': actual_reason,
                'is_trap': is_trap,
            }
            results['misroutes'].append(misroute)

            # HARD FP CHECK: Did RULES_ONLY trigger on a trap query?
            # Trap queries should NOT route to RULES_ONLY
            if is_trap and actual_lane == 'RULES_ONLY':
                results['hard_fp'].append(misroute)

    return results


def print_results(results):
    """Print validation results"""
    print("=" * 70)
    print("LANE ROUTING VALIDATION RESULTS")
    print("=" * 70)

    # Overall accuracy
    accuracy = results['correct'] / results['total'] * 100
    print(f"\nOverall Accuracy: {results['correct']}/{results['total']} ({accuracy:.1f}%)")

    # Hard FP (Sacred metric)
    print(f"\n🛡️  HARD FP (MUST BE 0): {len(results['hard_fp'])}")
    if results['hard_fp']:
        print("   ⚠️  CRITICAL: These trap queries triggered RULES_ONLY:")
        for fp in results['hard_fp'][:10]:
            print(f"      - {fp['id']}: \"{fp['query'][:50]}...\"")

    # Per-lane breakdown
    print("\nPer-Lane Accuracy:")
    for lane, stats in sorted(results['by_expected_lane'].items()):
        lane_acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        emoji = "✅" if lane_acc >= 90 else "⚠️" if lane_acc >= 70 else "❌"
        print(f"  {emoji} {lane}: {stats['correct']}/{stats['total']} ({lane_acc:.1f}%)")

    # Actual lane distribution
    print("\nActual Lane Distribution:")
    for lane, count in sorted(results['by_actual_lane'].items()):
        pct = count / results['total'] * 100
        print(f"  {lane}: {count} ({pct:.1f}%)")

    # Top misroute patterns
    if results['misroutes']:
        print(f"\nMisroutes: {len(results['misroutes'])} total")

        # Group by misroute type
        misroute_types = defaultdict(list)
        for m in results['misroutes']:
            key = f"{m['expected_lane']} -> {m['actual_lane']}"
            misroute_types[key].append(m)

        print("\nMisroute Patterns:")
        for pattern, items in sorted(misroute_types.items(), key=lambda x: -len(x[1])):
            print(f"  {pattern}: {len(items)} cases")
            for item in items[:3]:
                print(f"    - {item['id']}: \"{item['query'][:40]}...\"")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more")

    # Top reasons
    print("\nRouting Reasons (actual):")
    for reason, count in sorted(results['by_reason'].items(), key=lambda x: -x[1])[:10]:
        pct = count / results['total'] * 100
        print(f"  {reason}: {count} ({pct:.1f}%)")

    print("\n" + "=" * 70)

    # Return exit code
    if results['hard_fp']:
        print("❌ FAIL: Hard FP > 0 - NOT PRODUCTION READY")
        return 1
    elif accuracy < 80:
        print("⚠️  WARNING: Accuracy below 80% - review misroutes")
        return 0
    else:
        print("✅ PASS: Hard FP = 0, routing looks good")
        return 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("Loading stress test dataset...")
    queries = load_stress_test()
    print(f"Loaded {len(queries)} queries")

    print("\nValidating routing...")
    results = validate_routing(queries)

    exit_code = print_results(results)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
