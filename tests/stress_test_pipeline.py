#!/usr/bin/env python3
"""
Pipeline V1 Stress Test Runner
==============================

Runs queries from stress_test_dataset_v3.json against deployed pipeline.

Usage:
    python tests/stress_test_pipeline.py [--limit N] [--url URL] [--delay SECONDS]

Examples:
    python tests/stress_test_pipeline.py --limit 50          # Quick test
    python tests/stress_test_pipeline.py --limit 500         # Full test
    python tests/stress_test_pipeline.py --url http://localhost:8000  # Local
"""

import argparse
import json
import httpx
import time
from pathlib import Path

DEFAULT_URL = "https://celeste-microactions.onrender.com"
DEFAULT_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_FILE = Path(__file__).parent / "stress_test_dataset_v3.json"


def run_stress_test(base_url: str, yacht_id: str, limit: int, delay: float):
    """Run stress test against pipeline endpoint."""
    
    with open(TEST_FILE, 'r') as f:
        data = json.load(f)
    
    cases = data.get('cases', [])[:limit]
    
    results = {
        'total': len(cases),
        'extraction_success': 0,
        'results_found': 0,
        'action_triggered': 0,
        'should_trigger_total': 0,
        'should_trigger_success': 0,
        'negative_total': 0,
        'negative_correct': 0,
        'errors': 0,
        'timings': [],
    }
    
    failures = []
    
    print(f"Pipeline Stress Test")
    print(f"URL: {base_url}")
    print(f"Queries: {len(cases)}")
    print("=" * 60)
    
    with httpx.Client(timeout=60.0) as client:
        for i, case in enumerate(cases):
            query = case.get('query', '')
            expected = case.get('expected', {})
            should_trigger = expected.get('should_trigger_action', False)
            
            if should_trigger:
                results['should_trigger_total'] += 1
            else:
                results['negative_total'] += 1
            
            try:
                start = time.time()
                resp = client.post(
                    f"{base_url}/search",
                    json={"query": query, "yacht_id": yacht_id, "limit": 10},
                    timeout=30.0
                )
                elapsed = (time.time() - start) * 1000
                results['timings'].append(elapsed)
                
                if resp.status_code == 200:
                    data = resp.json()
                    entities = data.get('entities', [])
                    rows = data.get('results', [])
                    actions = data.get('available_actions', [])
                    
                    if entities:
                        results['extraction_success'] += 1
                    if rows:
                        results['results_found'] += 1
                    if actions:
                        results['action_triggered'] += 1
                    
                    if should_trigger and (rows or actions):
                        results['should_trigger_success'] += 1
                    elif should_trigger and not rows:
                        failures.append({
                            'id': case.get('id'),
                            'query': query,
                            'expected_action': expected.get('primary_action'),
                            'entities': entities,
                        })
                    elif not should_trigger and not rows:
                        results['negative_correct'] += 1
                else:
                    results['errors'] += 1
                    
            except Exception as e:
                results['errors'] += 1
                
            if (i + 1) % 30 == 0:
                print(f"  Progress: {i+1}/{len(cases)}")
            
            time.sleep(delay)
    
    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total: {results['total']}")
    print(f"Extraction success: {results['extraction_success']} ({100*results['extraction_success']/max(1,results['total']):.1f}%)")
    print(f"Results found: {results['results_found']} ({100*results['results_found']/max(1,results['total']):.1f}%)")
    print(f"Actions triggered: {results['action_triggered']}")
    print(f"Errors: {results['errors']}")
    
    print(f"\nPositive tests (should_trigger_action=true):")
    print(f"  Total: {results['should_trigger_total']}")
    print(f"  Success: {results['should_trigger_success']} ({100*results['should_trigger_success']/max(1,results['should_trigger_total']):.1f}%)")
    
    print(f"\nNegative tests (should_trigger_action=false):")
    print(f"  Total: {results['negative_total']}")
    print(f"  Correct: {results['negative_correct']} ({100*results['negative_correct']/max(1,results['negative_total']):.1f}%)")
    
    if results['timings']:
        print(f"\nTiming:")
        print(f"  Avg: {sum(results['timings'])/len(results['timings']):.0f}ms")
        print(f"  Max: {max(results['timings']):.0f}ms")
    
    total_pass = results['should_trigger_success'] + results['negative_correct']
    total_tests = results['should_trigger_total'] + results['negative_total']
    print(f"\n{'=' * 60}")
    print(f"PASS RATE: {total_pass}/{total_tests} ({100*total_pass/max(1,total_tests):.1f}%)")
    print("=" * 60)
    
    if failures[:5]:
        print(f"\nSample failures:")
        for f in failures[:5]:
            print(f"  {f['id']}: \"{f['query'][:50]}...\"")
            print(f"       Expected: {f['expected_action']}")
            print(f"       Entities: {[(e['type'], e['value']) for e in f['entities']]}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline stress test")
    parser.add_argument("--url", default=DEFAULT_URL, help="Pipeline URL")
    parser.add_argument("--yacht-id", default=DEFAULT_YACHT_ID, help="Yacht UUID")
    parser.add_argument("--limit", type=int, default=150, help="Max queries to test")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests")
    
    args = parser.parse_args()
    run_stress_test(args.url, args.yacht_id, args.limit, args.delay)
