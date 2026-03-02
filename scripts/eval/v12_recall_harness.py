#!/usr/bin/env python3
"""
v1.2 Recall@3 Evaluation Harness
================================

Measures Recall@3 against truth sets with real entity IDs from production.

For each NLP query:
1. Execute search via f1_search_fusion
2. Check if ANY entity from the corresponding lens's truth set appears in top 3
3. Track: hit/miss, latency, difficulty_tier

Outputs: test-results/v12/recall_report.md
"""

import json
import os
import sys
import psycopg2
import psycopg2.extras
import time
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps' / 'api'))

try:
    from rag.normalizer import normalize_query
    from rag.context_builder import generate_query_embedding
    from action_surfacing import get_fusion_params_for_query
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import local modules: {e}")
    IMPORTS_AVAILABLE = False

# =============================================================================
# CONFIG
# =============================================================================

DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'
TRUTH_SETS_DIR = Path(__file__).parent.parent.parent / 'truth_sets'
INTENT_TRUTH_SET = Path(__file__).parent.parent.parent / '.planning/agents/nlp-variants/intent_truth_set.jsonl'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'test-results/v12'

# Recall@3 targets by tier
TARGETS = {
    1: 0.90,  # 90% for simple queries
    2: 0.70,  # 70% for entity-specific queries
    3: 0.50,  # 50% for ambiguous queries
    4: None,  # Tier 4 = fallback, no target (should NOT have button renders)
}

# Map lens names to truth set files
LENS_TO_TRUTH_FILE = {
    'certificate': 'certificate_truth.jsonl',
    'email': 'email_truth.jsonl',
    'equipment': 'equipment_truth.jsonl',
    'fault': 'fault_truth.jsonl',
    'handover': 'handover_truth.jsonl',
    'hours_of_rest': 'hours_of_rest_truth.jsonl',
    'inventory': 'inventory_truth.jsonl',
    'part': 'part_truth.jsonl',
    'receiving': 'receiving_truth.jsonl',
    'shopping_list': 'shopping_list_truth.jsonl',
    'work_order': 'work_order_truth.jsonl',
    # Warranty has no truth set (0 entities)
}


@dataclass
class QueryResult:
    """Result of a single query evaluation."""
    query: str
    lens: str
    tier: int
    hit: bool
    latency_ms: float
    results_count: int
    top_3_ids: List[str]
    matching_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# TRUTH SET LOADING
# =============================================================================

def load_truth_sets() -> Dict[str, Set[str]]:
    """
    Load all truth set entity IDs by lens.
    Returns: {lens: set of entity_ids}
    """
    truth_sets = {}

    for lens, filename in LENS_TO_TRUTH_FILE.items():
        filepath = TRUTH_SETS_DIR / filename
        if not filepath.exists():
            print(f"  Warning: Truth set not found: {filepath}")
            truth_sets[lens] = set()
            continue

        entity_ids = set()
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        entity_id = record.get('entity_id')
                        if entity_id:
                            entity_ids.add(entity_id)
                    except json.JSONDecodeError:
                        continue

        truth_sets[lens] = entity_ids
        print(f"  Loaded {len(entity_ids)} entities for lens: {lens}")

    return truth_sets


def load_intent_queries(sample_size: int = None) -> List[Dict]:
    """
    Load queries from intent_truth_set.jsonl.
    Optionally sample proportionally across tiers.
    """
    queries_by_tier = defaultdict(list)

    with open(INTENT_TRUTH_SET, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    if '_metadata' in record:
                        continue
                    tier = record.get('difficulty_tier', 1)
                    queries_by_tier[tier].append(record)
                except json.JSONDecodeError:
                    continue

    total = sum(len(v) for v in queries_by_tier.values())
    print(f"\n  Total queries: {total}")
    for tier in sorted(queries_by_tier.keys()):
        print(f"    Tier {tier}: {len(queries_by_tier[tier])} queries")

    if sample_size and sample_size < total:
        # Proportional stratified sampling
        sampled = []
        for tier in sorted(queries_by_tier.keys()):
            tier_queries = queries_by_tier[tier]
            tier_sample_size = max(1, int(sample_size * len(tier_queries) / total))
            tier_sample = random.sample(tier_queries, min(tier_sample_size, len(tier_queries)))
            sampled.extend(tier_sample)
            print(f"    Sampled {len(tier_sample)} from tier {tier}")

        # If we undersampled due to rounding, add more from tier 1
        while len(sampled) < sample_size and queries_by_tier[1]:
            remaining = [q for q in queries_by_tier[1] if q not in sampled]
            if remaining:
                sampled.append(random.choice(remaining))
            else:
                break

        return sampled[:sample_size]

    # Return all queries flattened
    all_queries = []
    for tier in sorted(queries_by_tier.keys()):
        all_queries.extend(queries_by_tier[tier])
    return all_queries


# =============================================================================
# SEARCH EXECUTION
# =============================================================================

def execute_search(
    conn,
    query: str,
    yacht_id: str,
    lens: str,
    role: str = 'crew',
    limit: int = 10,
) -> Tuple[List[Dict], float]:
    """
    Execute search and return results with latency.
    Uses f1_search_simple which has a straightforward signature.
    Returns: (results, latency_ms)
    """
    return execute_search_direct(conn, query, yacht_id, lens, limit)


def execute_search_direct(
    conn,
    query: str,
    yacht_id: str,
    lens: str,
    limit: int = 10,
) -> Tuple[List[Dict], float]:
    """
    Direct search using f1_search_fusion with minimal parameters.
    Embedding is generated server-side when NULL.
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    start_time = time.time()

    # Call f1_search_fusion with positional parameters (like ranking_truth_harness.py)
    # All explicit type casts to avoid "unknown" type errors
    sql = """
        SELECT
            object_id,
            object_type,
            payload,
            final_score as score
        FROM f1_search_fusion(
            %s::uuid,                       -- p_yacht_id
            %s::text,                       -- p_query_text
            NULL::vector(1536),             -- p_query_embedding (NULL = server-side text only)
            'crew'::text,                   -- p_role
            %s::text,                       -- p_lens
            NULL::text,                     -- p_domain
            'explore'::text,                -- p_mode
            0.25::numeric,                  -- p_domain_boost
            0.50::numeric,                  -- p_w_text (higher for text-only)
            0.0::numeric,                   -- p_w_vector (zero without embedding)
            0.15::numeric,                  -- p_w_recency
            0.10::numeric,                  -- p_w_bias
            0.25::numeric,                  -- p_w_rrf
            0.01::numeric,                  -- p_lambda
            60::integer,                    -- p_rrf_k
            6.0::numeric,                   -- p_logistic_a
            0.2::numeric,                   -- p_logistic_b
            200::integer,                   -- p_m_text
            200::integer,                   -- p_m_vec
            %s::integer,                    -- p_limit
            0::integer,                     -- p_offset
            false::boolean,                 -- p_debug
            0.08::real,                     -- p_trgm_limit
            150::integer,                   -- p_m_trgm
            0.20::numeric,                  -- p_w_trigram
            NULL::jsonb                     -- p_filters
        )
    """

    try:
        cursor.execute(sql, (yacht_id, query, lens, limit))
        results = [dict(r) for r in cursor.fetchall()]
        latency_ms = (time.time() - start_time) * 1000
        cursor.close()
        return results, latency_ms
    except Exception as e:
        conn.rollback()
        cursor.close()
        raise e


def check_recall(
    results: List[Dict],
    truth_ids: Set[str],
    k: int = 3
) -> Tuple[bool, Optional[str]]:
    """
    Check if any truth entity appears in top-k results.
    Returns: (hit, matching_id)
    """
    for result in results[:k]:
        object_id = str(result.get('object_id', ''))
        if object_id in truth_ids:
            return True, object_id
    return False, None


# =============================================================================
# EVALUATION
# =============================================================================

def run_evaluation(
    conn,
    queries: List[Dict],
    truth_sets: Dict[str, Set[str]],
    yacht_id: str,
) -> List[QueryResult]:
    """Run evaluation on all queries."""
    results = []
    total = len(queries)

    print(f"\n{'='*70}")
    print(" v1.2 RECALL@3 EVALUATION")
    print(f"{'='*70}")
    print(f"Queries: {total}")
    print(f"Yacht: {yacht_id}")
    print(f"{'='*70}\n")

    for i, query_data in enumerate(queries):
        query = query_data.get('query', '')
        lens = query_data.get('expected_lens', '')
        tier = query_data.get('difficulty_tier', 1)

        # Get truth set for this lens
        truth_ids = truth_sets.get(lens, set())

        if not truth_ids:
            # No truth set for this lens (e.g., warranty)
            results.append(QueryResult(
                query=query,
                lens=lens,
                tier=tier,
                hit=False,
                latency_ms=0,
                results_count=0,
                top_3_ids=[],
                error=f"No truth set for lens: {lens}"
            ))
            continue

        try:
            search_results, latency_ms = execute_search(
                conn, query, yacht_id, lens
            )

            hit, matching_id = check_recall(search_results, truth_ids, k=3)

            top_3_ids = [str(r.get('object_id', '')) for r in search_results[:3]]

            result = QueryResult(
                query=query,
                lens=lens,
                tier=tier,
                hit=hit,
                latency_ms=latency_ms,
                results_count=len(search_results),
                top_3_ids=top_3_ids,
                matching_id=matching_id,
            )

        except Exception as e:
            result = QueryResult(
                query=query,
                lens=lens,
                tier=tier,
                hit=False,
                latency_ms=0,
                results_count=0,
                top_3_ids=[],
                error=str(e),
            )

        results.append(result)

        # Progress output
        status = 'HIT' if result.hit else ('ERR' if result.error else 'MISS')
        status_icon = {
            'HIT': '+',
            'MISS': '-',
            'ERR': '!',
        }.get(status, '?')

        print(f"[{i+1:3d}/{total}] {status_icon} T{tier} {lens:15s} | {query[:45]}")

        if result.error:
            print(f"          Error: {result.error[:60]}")

    return results


def compute_metrics(results: List[QueryResult]) -> Dict:
    """Compute metrics from evaluation results."""
    # By tier
    by_tier = defaultdict(lambda: {'total': 0, 'hits': 0, 'errors': 0, 'latencies': []})

    # By lens
    by_lens = defaultdict(lambda: {'total': 0, 'hits': 0, 'errors': 0})

    # Overall
    total_latencies = []

    for r in results:
        # Skip queries with errors for recall calculation (but count them)
        by_tier[r.tier]['total'] += 1
        by_lens[r.lens]['total'] += 1

        if r.error:
            by_tier[r.tier]['errors'] += 1
            by_lens[r.lens]['errors'] += 1
            continue

        if r.hit:
            by_tier[r.tier]['hits'] += 1
            by_lens[r.lens]['hits'] += 1

        by_tier[r.tier]['latencies'].append(r.latency_ms)
        total_latencies.append(r.latency_ms)

    # Calculate recall rates
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_queries': len(results),
        'by_tier': {},
        'by_lens': {},
        'overall': {},
    }

    # Tier metrics
    for tier in sorted(by_tier.keys()):
        data = by_tier[tier]
        valid = data['total'] - data['errors']
        recall = data['hits'] / valid if valid > 0 else 0
        target = TARGETS.get(tier)

        metrics['by_tier'][tier] = {
            'queries': data['total'],
            'hits': data['hits'],
            'errors': data['errors'],
            'recall': recall,
            'target': target,
            'met_target': recall >= target if target else None,
            'avg_latency_ms': sum(data['latencies']) / len(data['latencies']) if data['latencies'] else 0,
        }

    # Lens metrics
    for lens in sorted(by_lens.keys()):
        data = by_lens[lens]
        valid = data['total'] - data['errors']
        recall = data['hits'] / valid if valid > 0 else 0

        metrics['by_lens'][lens] = {
            'queries': data['total'],
            'hits': data['hits'],
            'errors': data['errors'],
            'recall': recall,
        }

    # Overall (excluding tier 4)
    valid_results = [r for r in results if r.tier != 4 and not r.error]
    hits = sum(1 for r in valid_results if r.hit)

    metrics['overall'] = {
        'queries': len(valid_results),
        'hits': hits,
        'recall': hits / len(valid_results) if valid_results else 0,
        'avg_latency_ms': sum(total_latencies) / len(total_latencies) if total_latencies else 0,
        'p95_latency_ms': sorted(total_latencies)[int(len(total_latencies) * 0.95)] if total_latencies else 0,
    }

    return metrics


def generate_report(metrics: Dict, output_path: Path) -> str:
    """Generate markdown report."""
    lines = [
        "# v1.2 Recall@3 Report",
        "",
        f"**Generated:** {metrics['timestamp']}",
        f"**Total Queries:** {metrics['total_queries']}",
        "",
        "## Summary by Difficulty Tier",
        "",
        "| Tier | Queries | Hits | Errors | Recall@3 | Target | Status |",
        "|------|---------|------|--------|----------|--------|--------|",
    ]

    for tier in sorted(metrics['by_tier'].keys()):
        data = metrics['by_tier'][tier]
        target_str = f"{data['target']*100:.0f}%" if data['target'] else "N/A"
        recall_str = f"{data['recall']*100:.1f}%"

        if data['target'] is None:
            status = "-"
        elif data['met_target']:
            status = "PASS"
        else:
            status = "FAIL"

        lines.append(
            f"| {tier} | {data['queries']} | {data['hits']} | {data['errors']} | "
            f"{recall_str} | {target_str} | {status} |"
        )

    # Overall row
    overall = metrics['overall']
    lines.append(
        f"| **Overall** | {overall['queries']} | {overall['hits']} | - | "
        f"**{overall['recall']*100:.1f}%** | - | - |"
    )

    lines.extend([
        "",
        "## Summary by Lens",
        "",
        "| Lens | Queries | Hits | Errors | Recall@3 |",
        "|------|---------|------|--------|----------|",
    ])

    for lens in sorted(metrics['by_lens'].keys()):
        data = metrics['by_lens'][lens]
        recall_str = f"{data['recall']*100:.1f}%"
        lines.append(
            f"| {lens} | {data['queries']} | {data['hits']} | {data['errors']} | {recall_str} |"
        )

    lines.extend([
        "",
        "## Performance",
        "",
        f"- **Average Latency:** {overall['avg_latency_ms']:.0f}ms",
        f"- **P95 Latency:** {overall['p95_latency_ms']:.0f}ms",
        "",
        "## Targets",
        "",
        "| Tier | Description | Target |",
        "|------|-------------|--------|",
        "| 1 | Simple, explicit queries | 90% |",
        "| 2 | Entity-specific queries | 70% |",
        "| 3 | Ambiguous queries | 50% |",
        "| 4 | Fallback (no button render) | N/A |",
        "",
        "---",
        f"*Report generated by v12_recall_harness.py*",
    ])

    report = "\n".join(lines)

    with open(output_path, 'w') as f:
        f.write(report)

    return report


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='v1.2 Recall@3 Evaluation Harness')
    parser.add_argument('--yacht-id', default=DEFAULT_YACHT, help='Yacht ID')
    parser.add_argument('--sample', type=int, default=100, help='Sample size (0 for all)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for sampling')
    args = parser.parse_args()

    random.seed(args.seed)

    # Ensure output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(" LOADING DATA")
    print(f"{'='*70}")

    # Load truth sets
    print("\nLoading truth sets...")
    truth_sets = load_truth_sets()

    # Load queries
    print("\nLoading intent queries...")
    sample_size = args.sample if args.sample > 0 else None
    queries = load_intent_queries(sample_size)
    print(f"\n  Selected {len(queries)} queries for evaluation")

    # Connect to DB
    print("\nConnecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    conn.autocommit = True
    print("  Connected successfully")

    # Run evaluation
    results = run_evaluation(conn, queries, truth_sets, args.yacht_id)

    # Compute metrics
    metrics = compute_metrics(results)

    # Save detailed results
    results_path = OUTPUT_DIR / 'detailed_results.jsonl'
    with open(results_path, 'w') as f:
        for r in results:
            f.write(json.dumps({
                'query': r.query,
                'lens': r.lens,
                'tier': r.tier,
                'hit': r.hit,
                'latency_ms': r.latency_ms,
                'results_count': r.results_count,
                'top_3_ids': r.top_3_ids,
                'matching_id': r.matching_id,
                'error': r.error,
            }) + '\n')

    # Save metrics JSON
    metrics_path = OUTPUT_DIR / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    # Generate report
    report_path = OUTPUT_DIR / 'recall_report.md'
    report = generate_report(metrics, report_path)

    # Print summary
    print(f"\n{'='*70}")
    print(" RESULTS SUMMARY")
    print(f"{'='*70}")
    print(report)

    print(f"\n{'='*70}")
    print(" OUTPUT FILES")
    print(f"{'='*70}")
    print(f"  Report: {report_path}")
    print(f"  Metrics: {metrics_path}")
    print(f"  Details: {results_path}")

    conn.close()

    # Exit code based on tier 1-3 targets
    tier_results = metrics['by_tier']
    all_met = all(
        tier_results.get(t, {}).get('met_target', True)
        for t in [1, 2, 3]
        if t in tier_results
    )

    if all_met:
        print(f"\n  SUCCESS: All tier targets met")
        return 0
    else:
        print(f"\n  NEEDS IMPROVEMENT: Some tier targets not met")
        return 1


if __name__ == '__main__':
    exit(main())
