#!/usr/bin/env python3
"""
Validate Autolinking - Success Criteria Checker

Measures linking accuracy against ground truth and reports metrics.

Success Criteria:
- L1 precision ≥ 95%
- L2.5 top-1 alignment ≥ 80%
- ≥ 50% acceptance rate on L2.5 strong suggestions
- ≥ 70% of non-L1 tests produce at least weak suggestion
- P50 ≤ 2min, P95 ≤ 5min latency
- Worker errors < 1%

Usage:
    python scripts/autonomy/validate_autolinking.py
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from integrations.supabase import get_supabase_client


def load_ground_truth() -> List[Dict[str, Any]]:
    """Load ground truth data."""
    gt_path = 'test-results/autonomy/ground_truth.json'

    if not os.path.exists(gt_path):
        print(f"⚠ Ground truth not found at {gt_path}")
        return []

    with open(gt_path, 'r') as f:
        return json.load(f)


def check_thread_linking(supabase, thread_id: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check linking results for a thread against ground truth.

    Returns:
        Validation result with metrics
    """
    # Get thread tokens and suggestions_generated_at
    try:
        thread_result = supabase.table('email_threads').select(
            'extracted_tokens, suggestions_generated_at, created_at'
        ).eq('id', thread_id).maybe_single().execute()

        if not thread_result.data:
            return {
                'thread_id': thread_id,
                'status': 'thread_not_found',
                'error': True,
            }

        thread = thread_result.data
        tokens_extracted = thread.get('extracted_tokens') is not None
        suggestions_generated = thread.get('suggestions_generated_at') is not None

        # Calculate latency (created_at → suggestions_generated_at)
        latency_seconds = None
        if suggestions_generated:
            created_at = datetime.fromisoformat(thread['created_at'].replace('Z', '+00:00'))
            generated_at = datetime.fromisoformat(thread['suggestions_generated_at'].replace('Z', '+00:00'))
            latency_seconds = (generated_at - created_at).total_seconds()

        # Get suggestions
        links_result = supabase.table('email_links').select(
            'object_type, object_id, confidence, is_primary, score, is_active, suggested_reason'
        ).eq('thread_id', thread_id).order(
            'score', desc=True
        ).execute()

        suggestions = links_result.data or []

        # Validate against ground truth
        expected_object_id = ground_truth.get('expected_object_id')
        expected_object_type = ground_truth.get('expected_object_type')
        expected_level = ground_truth.get('expected_level')

        # Check if primary suggestion matches
        primary_match = False
        top_3_match = False
        suggestion_count = len(suggestions)

        if suggestions:
            # Check primary (first/highest score)
            primary = suggestions[0]
            if primary['object_id'] == expected_object_id and primary['object_type'] == expected_object_type:
                primary_match = True

            # Check top 3
            for sugg in suggestions[:3]:
                if sugg['object_id'] == expected_object_id and sugg['object_type'] == expected_object_type:
                    top_3_match = True
                    break

        return {
            'thread_id': thread_id,
            'subject': ground_truth.get('subject'),
            'scenario': ground_truth.get('scenario'),
            'expected_level': expected_level,
            'expected_object_type': expected_object_type,
            'expected_object_id': expected_object_id,
            'tokens_extracted': tokens_extracted,
            'suggestions_generated': suggestions_generated,
            'suggestion_count': suggestion_count,
            'primary_match': primary_match,
            'top_3_match': top_3_match,
            'latency_seconds': latency_seconds,
            'suggestions': suggestions,
            'error': False,
        }

    except Exception as e:
        return {
            'thread_id': thread_id,
            'status': 'validation_error',
            'error': True,
            'error_message': str(e),
        }


def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate aggregated metrics from validation results.

    Returns:
        Metrics dict with success criteria evaluations
    """
    # Filter out errors
    valid_results = [r for r in results if not r.get('error')]

    if not valid_results:
        return {'error': 'No valid results'}

    total = len(valid_results)

    # Scenario breakdown
    l1_results = [r for r in valid_results if r['expected_level'] == 'L1']
    l25_results = [r for r in valid_results if r['expected_level'] == 'L2.5']
    other_results = [r for r in valid_results if r['expected_level'] not in ('L1', 'L2.5')]

    # L1 Precision (primary match rate)
    l1_precision = 0
    if l1_results:
        l1_matches = sum(1 for r in l1_results if r['primary_match'])
        l1_precision = (l1_matches / len(l1_results)) * 100

    # L2.5 Top-1 Alignment
    l25_top1_alignment = 0
    if l25_results:
        l25_matches = sum(1 for r in l25_results if r['primary_match'])
        l25_top1_alignment = (l25_matches / len(l25_results)) * 100

    # L2.5 Top-3 Alignment
    l25_top3_alignment = 0
    if l25_results:
        l25_top3_matches = sum(1 for r in l25_results if r['top_3_match'])
        l25_top3_alignment = (l25_top3_matches / len(l25_results)) * 100

    # Suggestion coverage (non-L1 with at least 1 suggestion)
    non_l1 = l25_results + other_results
    suggestion_coverage = 0
    if non_l1:
        with_suggestions = sum(1 for r in non_l1 if r['suggestion_count'] > 0)
        suggestion_coverage = (with_suggestions / len(non_l1)) * 100

    # Latency metrics (exclude None)
    latencies = [r['latency_seconds'] for r in valid_results if r.get('latency_seconds') is not None]

    p50_latency = None
    p95_latency = None
    if latencies:
        p50_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

    # Processing status
    suggestions_generated_count = sum(1 for r in valid_results if r['suggestions_generated'])
    tokens_extracted_count = sum(1 for r in valid_results if r['tokens_extracted'])

    metrics = {
        'total_tests': total,
        'l1_tests': len(l1_results),
        'l25_tests': len(l25_results),
        'other_tests': len(other_results),
        'l1_precision': round(l1_precision, 2),
        'l25_top1_alignment': round(l25_top1_alignment, 2),
        'l25_top3_alignment': round(l25_top3_alignment, 2),
        'suggestion_coverage': round(suggestion_coverage, 2),
        'p50_latency_seconds': round(p50_latency, 2) if p50_latency else None,
        'p95_latency_seconds': round(p95_latency, 2) if p95_latency else None,
        'tokens_extracted_count': tokens_extracted_count,
        'suggestions_generated_count': suggestions_generated_count,
        'errors': len([r for r in results if r.get('error')]),
    }

    # Success criteria checks
    criteria = {
        'l1_precision_target': 95.0,
        'l1_precision_pass': l1_precision >= 95.0 if l1_results else None,
        'l25_top1_target': 80.0,
        'l25_top1_pass': l25_top1_alignment >= 80.0 if l25_results else None,
        'suggestion_coverage_target': 70.0,
        'suggestion_coverage_pass': suggestion_coverage >= 70.0 if non_l1 else None,
        'p50_latency_target': 120.0,  # 2 minutes
        'p50_latency_pass': p50_latency <= 120.0 if p50_latency else None,
        'p95_latency_target': 300.0,  # 5 minutes
        'p95_latency_pass': p95_latency <= 300.0 if p95_latency else None,
    }

    metrics['success_criteria'] = criteria

    return metrics


def print_report(metrics: Dict[str, Any], results: List[Dict[str, Any]]):
    """Print validation report."""
    print()
    print("=" * 60)
    print("AUTONOMOUS LINKING VALIDATION REPORT")
    print("=" * 60)
    print()

    # Overall stats
    print(f"Total Tests: {metrics['total_tests']}")
    print(f"  L1 Tests: {metrics['l1_tests']}")
    print(f"  L2.5 Tests: {metrics['l25_tests']}")
    print(f"  Other Tests: {metrics['other_tests']}")
    print()

    # Success Criteria
    print("SUCCESS CRITERIA:")
    print("-" * 60)

    criteria = metrics['success_criteria']

    # L1 Precision
    l1_status = "✓ PASS" if criteria['l1_precision_pass'] else "✗ FAIL"
    print(f"L1 Precision: {metrics['l1_precision']}% (target: ≥{criteria['l1_precision_target']}%) {l1_status}")

    # L2.5 Top-1 Alignment
    l25_status = "✓ PASS" if criteria['l25_top1_pass'] else "✗ FAIL"
    print(f"L2.5 Top-1 Alignment: {metrics['l25_top1_alignment']}% (target: ≥{criteria['l25_top1_target']}%) {l25_status}")

    # Suggestion Coverage
    coverage_status = "✓ PASS" if criteria['suggestion_coverage_pass'] else "✗ FAIL"
    print(f"Suggestion Coverage: {metrics['suggestion_coverage']}% (target: ≥{criteria['suggestion_coverage_target']}%) {coverage_status}")

    # Latency
    if metrics['p50_latency_seconds']:
        p50_status = "✓ PASS" if criteria['p50_latency_pass'] else "✗ FAIL"
        print(f"P50 Latency: {metrics['p50_latency_seconds']}s (target: ≤{criteria['p50_latency_target']}s) {p50_status}")

    if metrics['p95_latency_seconds']:
        p95_status = "✓ PASS" if criteria['p95_latency_pass'] else "✗ FAIL"
        print(f"P95 Latency: {metrics['p95_latency_seconds']}s (target: ≤{criteria['p95_latency_target']}s) {p95_status}")

    print()

    # Additional Metrics
    print("ADDITIONAL METRICS:")
    print("-" * 60)
    print(f"L2.5 Top-3 Alignment: {metrics['l25_top3_alignment']}%")
    print(f"Tokens Extracted: {metrics['tokens_extracted_count']}/{metrics['total_tests']}")
    print(f"Suggestions Generated: {metrics['suggestions_generated_count']}/{metrics['total_tests']}")
    print(f"Errors: {metrics['errors']}")
    print()

    # Failures
    failures = [r for r in results if not r.get('error') and not r.get('primary_match')]
    if failures:
        print("FAILURES (Primary Match Miss):")
        print("-" * 60)
        for f in failures[:10]:  # Show first 10
            print(f"  [{f['scenario']}] {f['subject'][:60]}")
            print(f"    Expected: {f['expected_object_type']} {f['expected_object_id']}")
            print(f"    Suggestions: {f['suggestion_count']}, Top-3 Match: {f['top_3_match']}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
        print()

    # Overall status
    all_pass = all([
        criteria.get('l1_precision_pass', True),
        criteria.get('l25_top1_pass', True),
        criteria.get('suggestion_coverage_pass', True),
        criteria.get('p50_latency_pass', True),
        criteria.get('p95_latency_pass', True),
    ])

    print("=" * 60)
    if all_pass:
        print("✓ ALL SUCCESS CRITERIA PASSED")
    else:
        print("✗ SOME SUCCESS CRITERIA FAILED")
    print("=" * 60)


def main():
    # Connect to yTEST_YACHT_001
    os.environ['SUPABASE_URL'] = os.getenv('yTEST_YACHT_001_SUPABASE_URL', '')
    os.environ['SUPABASE_SERVICE_KEY'] = os.getenv('yTEST_YACHT_001_SUPABASE_SERVICE_KEY', '')

    supabase = get_supabase_client()

    # Load ground truth
    ground_truths = load_ground_truth()

    if not ground_truths:
        print("⚠ No ground truth data found. Run simulate_self_email.py first.")
        return

    print("=" * 60)
    print("Validating Autolinking Results")
    print("=" * 60)
    print(f"Validating {len(ground_truths)} test emails...")
    print()

    # Validate each thread
    results = []
    for i, gt in enumerate(ground_truths):
        result = check_thread_linking(supabase, gt['thread_id'], gt)
        results.append(result)

        if not result.get('error'):
            status_icon = "✓" if result['primary_match'] else "○"
            print(f"{status_icon} [{i+1}/{len(ground_truths)}] {result['scenario']}: {result.get('subject', '')[:50]}")
        else:
            print(f"✗ [{i+1}/{len(ground_truths)}] Error: {result.get('error_message', 'Unknown')}")

    # Calculate metrics
    metrics = calculate_metrics(results)

    # Print report
    print_report(metrics, results)

    # Save results
    results_path = f"test-results/autonomy/validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'results': results,
        }, f, indent=2, default=str)

    print(f"\n✓ Detailed results saved to {results_path}")


if __name__ == '__main__':
    main()
