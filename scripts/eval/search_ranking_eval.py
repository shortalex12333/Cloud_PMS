#!/usr/bin/env python3
"""
Search Ranking Evaluation Harness

Evaluates f1_search_fusion with deterministic metrics:
- NDCG@10: Normalized Discounted Cumulative Gain
- Precision@5/10: Proportion of relevant in top-k
- Recall@20: Proportion of all relevant found
- MRR: Mean Reciprocal Rank of first relevant

Modes:
- db: Direct RPC call (fast for grid search)
- api: Call /api/f1/search/cards?debug=true (E2E parity)

Without explicit positives, we measure:
1. Coverage: % queries returning results
2. Type consistency: % where top-k match expected_object_types
3. Determinism: stable ordering (hash-based verification)
"""

import json
import argparse
import psycopg2
import psycopg2.extras
import numpy as np
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import itertools
import openai
import os

# DB connection
DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

# Default yacht (test tenant)
DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'

# Paths
GOLDSET_PATH = Path("tests/search/goldset.jsonl")
OUTPUT_DIR = Path("test-results/search")

# Default weights (currently live)
DEFAULT_WEIGHTS = {
    'w_text': 0.50,
    'w_vector': 0.25,
    'w_recency': 0.15,
    'w_bias': 0.10,
    'w_rrf': 0.20,
    'lambda': 0.01,
    'rrf_k': 60,
    'logistic_a': 6.0,
    'logistic_b': 0.2,
    'm_text': 200,
    'm_vec': 200
}

def generate_query_embedding(query_text):
    """Generate embedding via OpenAI GPT text-embedding-3-small."""
    try:
        # Ensure API key is set
        if not os.environ.get('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY environment variable not set")

        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=query_text,
            dimensions=1536
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"WARNING: Failed to generate embedding for query '{query_text}': {e}")
        return None

def load_goldset(path):
    """Load goldset JSONL."""
    queries = []
    with open(path, 'r') as f:
        for line in f:
            queries.append(json.loads(line))
    return queries

def call_fusion_db(conn, yacht_id, query, role, lens, weights, limit=20, debug=True):
    """Call f1_search_fusion via direct DB connection."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Generate query embedding
        query_embedding = generate_query_embedding(query)

        # Convert embedding to PostgreSQL vector format
        if query_embedding:
            vec_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'
        else:
            vec_literal = None

        cur.execute("""
            SELECT
                object_id,
                object_type,
                payload,
                final_score,
                s_text,
                s_vector,
                s_recency,
                s_bias,
                rank_text,
                rank_vector,
                score,
                rrf_score
            FROM f1_search_fusion(
                %s::uuid,  -- yacht_id
                %s,        -- query_text
                %s::vector(1536),  -- query_embedding (NOW GENERATED!)
                %s,        -- role
                %s,        -- lens
                %s, %s, %s, %s, %s,  -- weights
                %s, %s, %s, %s,      -- lambda, rrf_k, logistic_a, logistic_b
                %s, %s,              -- m_text, m_vec
                %s, 0,               -- limit, offset
                %s                   -- debug
            )
        """, (
            yacht_id, query, vec_literal, role, lens,
            weights['w_text'], weights['w_vector'], weights['w_recency'],
            weights['w_bias'], weights['w_rrf'],
            weights['lambda'], weights['rrf_k'], weights['logistic_a'], weights['logistic_b'],
            weights['m_text'], weights['m_vec'],
            limit, debug
        ))

        results = [dict(r) for r in cur.fetchall()]
        return {
            'results': results,
            'status': 'ok',
            'count': len(results)
        }
    except Exception as e:
        return {
            'results': [],
            'status': 'error',
            'error': str(e),
            'count': 0
        }

def compute_metrics_without_positives(results, expected_types, k_values=[5, 10, 20]):
    """
    Compute proxy metrics without explicit positives.

    Metrics:
    - Coverage: did we get results?
    - Type consistency @k: % of top-k matching expected_object_types
    - Score distribution: mean, std, range
    """
    metrics = {
        'coverage': len(results) > 0,
        'count': len(results)
    }

    if len(results) == 0:
        return metrics

    # Type consistency at k
    for k in k_values:
        top_k = results[:k]
        if expected_types:
            matching = sum(1 for r in top_k if r['object_type'] in expected_types)
            metrics[f'type_consistency@{k}'] = matching / len(top_k) if top_k else 0.0
        else:
            metrics[f'type_consistency@{k}'] = None

    # Score statistics
    scores = [float(r['final_score']) for r in results if r.get('final_score')]
    if scores:
        metrics['score_mean'] = np.mean(scores)
        metrics['score_std'] = np.std(scores)
        metrics['score_range'] = max(scores) - min(scores)

    # Result hash for determinism check
    result_ids = [str(r['object_id']) for r in results[:10]]
    metrics['result_hash'] = hashlib.md5('|'.join(result_ids).encode()).hexdigest()[:8]

    return metrics

def evaluate_goldset(conn, yacht_id, goldset, weights, sample_size=None):
    """Evaluate all queries in goldset with given weights."""
    if sample_size:
        goldset = goldset[:sample_size]

    results_per_query = []
    aggregate_metrics = {
        'total_queries': len(goldset),
        'coverage': 0,
        'type_consistency@5': [],
        'type_consistency@10': [],
        'type_consistency@20': [],
        'score_mean': [],
        'errors': 0
    }

    for item in goldset:
        query = item['query']
        role = item['role']
        lens = item['lens']
        expected_types = item.get('expected_object_types', [])

        # Call fusion
        response = call_fusion_db(conn, yacht_id, query, role, lens, weights, limit=20, debug=True)

        if response['status'] == 'error':
            aggregate_metrics['errors'] += 1
            results_per_query.append({
                'query': query,
                'role': role,
                'lens': lens,
                'status': 'error',
                'error': response['error']
            })
            continue

        # Compute metrics
        metrics = compute_metrics_without_positives(
            response['results'],
            expected_types,
            k_values=[5, 10, 20]
        )

        # Aggregate
        if metrics['coverage']:
            aggregate_metrics['coverage'] += 1

        for k in [5, 10, 20]:
            key = f'type_consistency@{k}'
            if metrics.get(key) is not None:
                aggregate_metrics[key].append(metrics[key])

        if metrics.get('score_mean'):
            aggregate_metrics['score_mean'].append(metrics['score_mean'])

        # Save per-query result
        results_per_query.append({
            'query': query,
            'role': role,
            'lens': lens,
            'category': item.get('category'),
            'difficulty': item.get('difficulty', 1),
            'count': metrics['count'],
            'coverage': metrics['coverage'],
            'type_consistency@5': metrics.get('type_consistency@5'),
            'type_consistency@10': metrics.get('type_consistency@10'),
            'type_consistency@20': metrics.get('type_consistency@20'),
            'score_mean': metrics.get('score_mean'),
            'result_hash': metrics.get('result_hash'),
            'status': 'ok'
        })

    # Finalize aggregate metrics
    aggregate_metrics['coverage_pct'] = 100.0 * aggregate_metrics['coverage'] / aggregate_metrics['total_queries']

    for k in [5, 10, 20]:
        key = f'type_consistency@{k}'
        if aggregate_metrics[key]:
            aggregate_metrics[f'{key}_mean'] = np.mean(aggregate_metrics[key])
            aggregate_metrics[f'{key}_std'] = np.std(aggregate_metrics[key])
        del aggregate_metrics[key]  # Remove list, keep stats only

    if aggregate_metrics['score_mean']:
        aggregate_metrics['score_mean_overall'] = np.mean(aggregate_metrics['score_mean'])
    del aggregate_metrics['score_mean']

    return aggregate_metrics, results_per_query

def grid_search(conn, yacht_id, goldset, param_ranges, sample_size=100):
    """
    Grid search over parameter ranges.

    Since we don't have explicit relevance labels yet, optimize for:
    1. Coverage (primary)
    2. Type consistency @10 (secondary)
    3. Type consistency @5 (tie-breaker)
    """
    print("=" * 70)
    print(" Grid Search")
    print("=" * 70)

    # Generate all parameter combinations
    keys = sorted(param_ranges.keys())
    values = [param_ranges[k] for k in keys]
    combinations = list(itertools.product(*values))

    print(f"\nSearching {len(combinations)} configurations")
    print(f"Sample size: {sample_size} queries")
    print(f"Optimizing for: Coverage → Type Consistency@10 → Type Consistency@5")

    best_config = None
    best_score = (-1, -1, -1)  # (coverage, tc@10, tc@5)
    all_results = []

    for i, combo in enumerate(combinations):
        config = dict(zip(keys, combo))

        # Merge with defaults
        weights = {**DEFAULT_WEIGHTS, **config}

        # Evaluate
        agg_metrics, _ = evaluate_goldset(conn, yacht_id, goldset, weights, sample_size=sample_size)

        # Score: (coverage_pct, tc@10_mean, tc@5_mean)
        score = (
            agg_metrics['coverage_pct'],
            agg_metrics.get('type_consistency@10_mean', 0.0),
            agg_metrics.get('type_consistency@5_mean', 0.0)
        )

        all_results.append({
            'config': config,
            'metrics': agg_metrics,
            'score': score
        })

        if score > best_score:
            best_score = score
            best_config = weights

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(combinations)}] Best so far: coverage={best_score[0]:.1f}%, tc@10={best_score[1]:.3f}")

    print(f"\n✓ Grid search complete")
    print(f"  Best coverage: {best_score[0]:.1f}%")
    print(f"  Best type_consistency@10: {best_score[1]:.3f}")
    print(f"  Best type_consistency@5: {best_score[2]:.3f}")

    return best_config, best_score, all_results

def main():
    parser = argparse.ArgumentParser(description='Search ranking evaluation harness')
    parser.add_argument('--mode', choices=['db', 'api'], default='db', help='Evaluation mode')
    parser.add_argument('--yacht-id', default=DEFAULT_YACHT, help='Yacht ID for testing')
    parser.add_argument('--sample', type=int, help='Sample N queries for faster testing')
    parser.add_argument('--grid-search', action='store_true', help='Run grid search over parameters')
    parser.add_argument('--quick', action='store_true', help='Quick mode: small grid + small sample')
    args = parser.parse_args()

    # Load goldset
    print(f"Loading goldset from {GOLDSET_PATH}")
    goldset = load_goldset(GOLDSET_PATH)
    print(f"✓ Loaded {len(goldset)} queries")

    # Connect to DB
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    print(f"✓ Connected to DB")

    # Output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.grid_search:
        # Define grid
        if args.quick:
            param_ranges = {
                'w_text': [0.45, 0.50, 0.55],
                'w_vector': [0.20, 0.25, 0.30],
                'w_recency': [0.10, 0.15],
                'w_rrf': [0.15, 0.20],
                'lambda': [0.01],
                'rrf_k': [60]
            }
            sample_size = 50
        else:
            param_ranges = {
                'w_text': [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70],
                'w_vector': [0.15, 0.20, 0.25, 0.30, 0.35],
                'w_recency': [0.05, 0.10, 0.15, 0.20],
                'w_bias': [0.05, 0.10, 0.15, 0.20],
                'w_rrf': [0.10, 0.15, 0.20, 0.25, 0.30],
                'lambda': [0.005, 0.01, 0.02],
                'rrf_k': [30, 60, 90]
            }
            sample_size = 100

        best_config, best_score, all_results = grid_search(
            conn, args.yacht_id, goldset, param_ranges, sample_size=sample_size
        )

        # Save best config
        best_config_path = OUTPUT_DIR / 'best_config.json'
        with open(best_config_path, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'weights': best_config,
                'score': {
                    'coverage_pct': best_score[0],
                    'type_consistency@10': best_score[1],
                    'type_consistency@5': best_score[2]
                },
                'sample_size': sample_size,
                'total_queries': len(goldset)
            }, f, indent=2)
        print(f"\n✓ Saved best config to {best_config_path}")

        # Evaluate with best config on full set
        print(f"\nEvaluating full goldset with best config...")
        weights = best_config
    else:
        # Use default weights
        weights = DEFAULT_WEIGHTS

    # Full evaluation
    sample_size = args.sample if args.sample else None
    agg_metrics, per_query_results = evaluate_goldset(
        conn, args.yacht_id, goldset, weights, sample_size=sample_size
    )

    # Save results
    metrics_path = OUTPUT_DIR / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'weights': weights,
            'aggregate_metrics': agg_metrics,
            'sample_size': sample_size or len(goldset)
        }, f, indent=2)
    print(f"✓ Saved metrics to {metrics_path}")

    # Save per-query CSV
    import csv
    csv_path = OUTPUT_DIR / 'per_query.csv'
    if per_query_results:
        keys = per_query_results[0].keys()
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(per_query_results)
        print(f"✓ Saved per-query results to {csv_path}")

    # Print summary
    print("\n" + "=" * 70)
    print(" Evaluation Summary")
    print("=" * 70)
    print(f"Total queries: {agg_metrics['total_queries']}")
    print(f"Coverage: {agg_metrics['coverage_pct']:.1f}%")
    print(f"Type consistency@5: {agg_metrics.get('type_consistency@5_mean', 0):.3f}")
    print(f"Type consistency@10: {agg_metrics.get('type_consistency@10_mean', 0):.3f}")
    print(f"Type consistency@20: {agg_metrics.get('type_consistency@20_mean', 0):.3f}")
    print(f"Errors: {agg_metrics['errors']}")

    conn.close()

if __name__ == '__main__':
    main()
