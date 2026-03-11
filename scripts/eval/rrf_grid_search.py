#!/usr/bin/env python3
"""
RRF Parameter Grid Search
=========================

Optimizes Reciprocal Rank Fusion (RRF) parameters for f1_search_cards:
- p_rrf_k: Smoothing constant (30, 60, 100)
- p_trgm_limit: Trigram similarity threshold (0.10, 0.15, 0.20, 0.25)

Uses a sample of queries for fast iteration, measuring:
- Recall@3: Whether truth entity appears in top 3
- Lens Accuracy: Whether top-1 result type matches expected lens
- Latency: Response time in milliseconds

Output: test-results/rrf-grid/results_matrix.md
"""

import json
import os
import sys
import psycopg2
import psycopg2.extras
import time
import random
import itertools
import openai
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

# =============================================================================
# CONFIG
# =============================================================================

DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'
DEFAULT_ORG = None  # Will be fetched from DB

TRUTH_SETS_DIR = Path(__file__).parent.parent.parent / 'truth_sets'
INTENT_TRUTH_SET = Path(__file__).parent.parent.parent / '.planning/agents/nlp-variants/intent_truth_set.jsonl'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'test-results/rrf-grid'

# RRF parameters to test
RRF_K_VALUES = [30, 60, 100]
TRGM_LIMIT_VALUES = [0.10, 0.15, 0.20, 0.25]

# Sample size for fast iteration
DEFAULT_SAMPLE_SIZE = 75

# Lens mapping for truth set files
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
}

# Map lens names to expected object_types
LENS_TO_OBJECT_TYPES = {
    'certificate': ['certificate'],
    'email': ['email'],
    'equipment': ['equipment'],
    'fault': ['fault'],
    'handover': ['handover', 'handover_note'],
    'hours_of_rest': ['hours_of_rest'],
    'inventory': ['inventory', 'part'],
    'part': ['part', 'inventory'],
    'receiving': ['receiving'],
    'shopping_list': ['shopping_list', 'shopping_item'],
    'work_order': ['work_order'],
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
    top_3_types: List[str] = field(default_factory=list)
    lens_accurate: bool = False
    matching_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class GridSearchResult:
    """Result of a single parameter combination."""
    rrf_k: int
    trgm_limit: float
    recall_at_3: float
    lens_accuracy: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_queries: int
    hits: int
    errors: int


# =============================================================================
# DATA LOADING
# =============================================================================

def load_truth_sets() -> Dict[str, Set[str]]:
    """Load all truth set entity IDs by lens."""
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
    """Load queries from intent_truth_set.jsonl with stratified sampling."""
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
    print(f"\n  Total queries available: {total}")
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

        return sampled[:sample_size]

    # Return all queries flattened
    all_queries = []
    for tier in sorted(queries_by_tier.keys()):
        all_queries.extend(queries_by_tier[tier])
    return all_queries


def get_org_id_for_yacht(conn, yacht_id: str) -> Optional[str]:
    """Fetch org_id for a yacht from the database.
    Falls back to search_index if yachts table is not accessible (RLS).
    """
    cursor = conn.cursor()
    try:
        # Try yachts table first
        cursor.execute("SELECT org_id FROM yachts WHERE id = %s", (yacht_id,))
        result = cursor.fetchone()
        if result:
            cursor.close()
            return str(result[0]) if result[0] else None
    except Exception:
        pass  # Table may not exist or RLS blocks access

    try:
        # Fallback: get org_id from search_index
        cursor.execute(
            "SELECT DISTINCT org_id FROM search_index WHERE yacht_id = %s LIMIT 1",
            (yacht_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        return str(result[0]) if result and result[0] else None
    except Exception:
        cursor.close()
        return None  # org_id is optional in f1_search_cards


# =============================================================================
# EMBEDDING GENERATION
# =============================================================================

def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using OpenAI text-embedding-3-small."""
    try:
        if not os.environ.get('OPENAI_API_KEY'):
            return None

        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  Warning: Embedding generation failed: {e}")
        return None


# =============================================================================
# SEARCH EXECUTION
# =============================================================================

def execute_search_f1_cards(
    conn,
    query: str,
    yacht_id: str,
    org_id: Optional[str],
    lens: str,
    rrf_k: int,
    trgm_limit: float,
    limit: int = 10,
) -> Tuple[List[Dict], float]:
    """
    Execute search using f1_search_cards with specified RRF parameters.
    Returns: (results, latency_ms)
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Generate embedding for the query
    embedding = generate_embedding(query)

    # Format embedding for PostgreSQL
    if embedding:
        vec_literal = '[' + ','.join(str(x) for x in embedding) + ']'
        embeddings_array = f"ARRAY['{vec_literal}'::vector(1536)]"
    else:
        embeddings_array = "NULL::vector(1536)[]"

    # Get object types for this lens
    object_types = LENS_TO_OBJECT_TYPES.get(lens)
    if object_types:
        object_types_sql = "ARRAY[" + ",".join(f"'{t}'" for t in object_types) + "]::text[]"
    else:
        object_types_sql = "NULL::text[]"

    start_time = time.time()

    # Call f1_search_cards with explicit parameter types
    sql = f"""
        SELECT
            object_type,
            object_id,
            payload,
            fused_score,
            best_rewrite_idx,
            ranks,
            components
        FROM f1_search_cards(
            ARRAY[%s]::text[],                  -- p_texts (single query)
            {embeddings_array},                 -- p_embeddings
            %s::uuid,                           -- p_org_id
            %s::uuid,                           -- p_yacht_id
            %s::int,                            -- p_rrf_k
            %s::int,                            -- p_page_limit
            %s::real,                           -- p_trgm_limit
            {object_types_sql}                  -- p_object_types
        )
    """

    try:
        cursor.execute(sql, (query, org_id, yacht_id, rrf_k, limit, trgm_limit))
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
    """Check if any truth entity appears in top-k results."""
    for result in results[:k]:
        object_id = str(result.get('object_id', ''))
        if object_id in truth_ids:
            return True, object_id
    return False, None


# =============================================================================
# EVALUATION
# =============================================================================

def evaluate_with_params(
    conn,
    queries: List[Dict],
    truth_sets: Dict[str, Set[str]],
    yacht_id: str,
    org_id: Optional[str],
    rrf_k: int,
    trgm_limit: float,
    verbose: bool = False,
) -> GridSearchResult:
    """Evaluate all queries with specific RRF parameters."""
    results = []
    latencies = []
    hits = 0
    lens_accurate_count = 0
    errors = 0

    for i, query_data in enumerate(queries):
        query = query_data.get('query', '')
        lens = query_data.get('expected_lens', '')
        tier = query_data.get('difficulty_tier', 1)

        truth_ids = truth_sets.get(lens, set())

        if not truth_ids:
            # No truth set for this lens
            errors += 1
            continue

        try:
            search_results, latency_ms = execute_search_f1_cards(
                conn, query, yacht_id, org_id, lens, rrf_k, trgm_limit
            )

            hit, matching_id = check_recall(search_results, truth_ids, k=3)
            if hit:
                hits += 1

            # Check lens accuracy
            if search_results:
                top_type = search_results[0].get('object_type', '')
                expected_types = LENS_TO_OBJECT_TYPES.get(lens, [lens])
                if top_type in expected_types:
                    lens_accurate_count += 1

            latencies.append(latency_ms)

            if verbose and (i + 1) % 25 == 0:
                print(f"    [{i+1}/{len(queries)}] processed...")

        except Exception as e:
            errors += 1
            if verbose:
                print(f"    Error on query '{query[:30]}...': {e}")

    valid = len(queries) - errors
    recall_at_3 = hits / valid if valid > 0 else 0
    lens_accuracy = lens_accurate_count / valid if valid > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    return GridSearchResult(
        rrf_k=rrf_k,
        trgm_limit=trgm_limit,
        recall_at_3=recall_at_3,
        lens_accuracy=lens_accuracy,
        avg_latency_ms=avg_latency,
        p95_latency_ms=p95_latency,
        total_queries=len(queries),
        hits=hits,
        errors=errors,
    )


def run_grid_search(
    conn,
    queries: List[Dict],
    truth_sets: Dict[str, Set[str]],
    yacht_id: str,
    org_id: Optional[str],
    rrf_k_values: List[int],
    trgm_limit_values: List[float],
) -> List[GridSearchResult]:
    """Run grid search across all parameter combinations."""
    combinations = list(itertools.product(rrf_k_values, trgm_limit_values))
    total_combos = len(combinations)

    print(f"\n{'='*70}")
    print(" RRF PARAMETER GRID SEARCH")
    print(f"{'='*70}")
    print(f"Parameter combinations: {total_combos}")
    print(f"RRF K values: {rrf_k_values}")
    print(f"Trigram limits: {trgm_limit_values}")
    print(f"Sample size: {len(queries)} queries")
    print(f"{'='*70}\n")

    results = []

    for i, (rrf_k, trgm_limit) in enumerate(combinations):
        print(f"[{i+1}/{total_combos}] Testing k={rrf_k}, trgm={trgm_limit:.2f}...")

        result = evaluate_with_params(
            conn, queries, truth_sets, yacht_id, org_id,
            rrf_k, trgm_limit, verbose=False
        )
        results.append(result)

        print(f"    Recall@3: {result.recall_at_3*100:.1f}%  "
              f"Lens: {result.lens_accuracy*100:.1f}%  "
              f"Latency: {result.avg_latency_ms:.0f}ms")

    return results


# =============================================================================
# REPORTING
# =============================================================================

def generate_results_matrix(results: List[GridSearchResult]) -> str:
    """Generate markdown table of results."""
    # Sort by recall descending
    results_sorted = sorted(results, key=lambda r: (-r.recall_at_3, -r.lens_accuracy))

    lines = [
        "# RRF Grid Search Results",
        "",
        f"**Generated:** {datetime.utcnow().isoformat()}",
        f"**Sample Size:** {results[0].total_queries if results else 0} queries",
        "",
        "## Results Matrix (sorted by Recall@3)",
        "",
        "| k   | trgm | Recall@3 | Lens Acc | Avg Latency | P95 Latency | Hits | Errors |",
        "|-----|------|----------|----------|-------------|-------------|------|--------|",
    ]

    for r in results_sorted:
        lines.append(
            f"| {r.rrf_k:3d} | {r.trgm_limit:.2f} | "
            f"{r.recall_at_3*100:5.1f}% | {r.lens_accuracy*100:5.1f}% | "
            f"{r.avg_latency_ms:6.0f}ms | {r.p95_latency_ms:6.0f}ms | "
            f"{r.hits:4d} | {r.errors:4d} |"
        )

    # Find best combination
    best = results_sorted[0]

    lines.extend([
        "",
        "## Best Configuration",
        "",
        f"- **p_rrf_k:** {best.rrf_k}",
        f"- **p_trgm_limit:** {best.trgm_limit:.2f}",
        f"- **Recall@3:** {best.recall_at_3*100:.1f}%",
        f"- **Lens Accuracy:** {best.lens_accuracy*100:.1f}%",
        f"- **Average Latency:** {best.avg_latency_ms:.0f}ms",
        "",
        "## Analysis",
        "",
    ])

    # Group by k to analyze trends
    by_k = defaultdict(list)
    for r in results:
        by_k[r.rrf_k].append(r)

    lines.append("### By RRF K (smoothing constant)")
    lines.append("")
    for k in sorted(by_k.keys()):
        avg_recall = sum(r.recall_at_3 for r in by_k[k]) / len(by_k[k])
        lines.append(f"- k={k}: avg Recall@3 = {avg_recall*100:.1f}%")
    lines.append("")

    # Group by trgm limit
    by_trgm = defaultdict(list)
    for r in results:
        by_trgm[r.trgm_limit].append(r)

    lines.append("### By Trigram Threshold")
    lines.append("")
    for trgm in sorted(by_trgm.keys()):
        avg_recall = sum(r.recall_at_3 for r in by_trgm[trgm]) / len(by_trgm[trgm])
        lines.append(f"- trgm={trgm:.2f}: avg Recall@3 = {avg_recall*100:.1f}%")
    lines.append("")

    lines.extend([
        "## Recommendations",
        "",
        f"1. Use `p_rrf_k = {best.rrf_k}` for optimal result fusion",
        f"2. Use `p_trgm_limit = {best.trgm_limit:.2f}` for trigram matching threshold",
        "3. Consider latency vs accuracy tradeoffs for production deployment",
        "",
        "---",
        "*Generated by rrf_grid_search.py*",
    ])

    return "\n".join(lines)


def save_results(results: List[GridSearchResult], output_dir: Path):
    """Save results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    results_json = [
        {
            'rrf_k': r.rrf_k,
            'trgm_limit': r.trgm_limit,
            'recall_at_3': r.recall_at_3,
            'lens_accuracy': r.lens_accuracy,
            'avg_latency_ms': r.avg_latency_ms,
            'p95_latency_ms': r.p95_latency_ms,
            'total_queries': r.total_queries,
            'hits': r.hits,
            'errors': r.errors,
        }
        for r in results
    ]

    json_path = output_dir / 'grid_results.json'
    with open(json_path, 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'parameters': {
                'rrf_k_values': RRF_K_VALUES,
                'trgm_limit_values': TRGM_LIMIT_VALUES,
            },
            'results': results_json,
        }, f, indent=2)

    # Save markdown report
    report = generate_results_matrix(results)
    report_path = output_dir / 'results_matrix.md'
    with open(report_path, 'w') as f:
        f.write(report)

    # Find best and save
    best = max(results, key=lambda r: (r.recall_at_3, r.lens_accuracy))
    best_path = output_dir / 'best_config.json'
    with open(best_path, 'w') as f:
        json.dump({
            'timestamp': datetime.utcnow().isoformat(),
            'best_params': {
                'p_rrf_k': best.rrf_k,
                'p_trgm_limit': best.trgm_limit,
            },
            'metrics': {
                'recall_at_3': best.recall_at_3,
                'lens_accuracy': best.lens_accuracy,
                'avg_latency_ms': best.avg_latency_ms,
            }
        }, f, indent=2)

    return json_path, report_path, best_path


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='RRF Parameter Grid Search')
    parser.add_argument('--yacht-id', default=DEFAULT_YACHT, help='Yacht ID')
    parser.add_argument('--sample', type=int, default=DEFAULT_SAMPLE_SIZE,
                       help='Sample size for queries (default: 75)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--rrf-k', type=str, default=None,
                       help='Custom RRF K values, comma-separated (e.g., "30,60,100")')
    parser.add_argument('--trgm', type=str, default=None,
                       help='Custom trigram thresholds, comma-separated (e.g., "0.10,0.15,0.20")')
    parser.add_argument('--quick', action='store_true',
                       help='Quick mode: fewer parameters, smaller sample')
    args = parser.parse_args()

    random.seed(args.seed)

    # Parse custom parameter values if provided
    rrf_k_values = RRF_K_VALUES
    trgm_limit_values = TRGM_LIMIT_VALUES

    if args.rrf_k:
        rrf_k_values = [int(x.strip()) for x in args.rrf_k.split(',')]
    if args.trgm:
        trgm_limit_values = [float(x.strip()) for x in args.trgm.split(',')]

    if args.quick:
        rrf_k_values = [30, 60]
        trgm_limit_values = [0.10, 0.15]
        sample_size = 50
    else:
        sample_size = args.sample

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

    # Get org_id for yacht
    org_id = get_org_id_for_yacht(conn, args.yacht_id)
    print(f"  Yacht ID: {args.yacht_id}")
    print(f"  Org ID: {org_id}")

    # Run grid search
    results = run_grid_search(
        conn, queries, truth_sets, args.yacht_id, org_id,
        rrf_k_values, trgm_limit_values
    )

    # Save results
    json_path, report_path, best_path = save_results(results, OUTPUT_DIR)

    # Print summary
    report = generate_results_matrix(results)
    print(f"\n{report}")

    print(f"\n{'='*70}")
    print(" OUTPUT FILES")
    print(f"{'='*70}")
    print(f"  Report: {report_path}")
    print(f"  JSON: {json_path}")
    print(f"  Best config: {best_path}")

    conn.close()

    # Find best result
    best = max(results, key=lambda r: (r.recall_at_3, r.lens_accuracy))
    print(f"\nBEST CONFIGURATION:")
    print(f"  p_rrf_k = {best.rrf_k}")
    print(f"  p_trgm_limit = {best.trgm_limit}")
    print(f"  Recall@3 = {best.recall_at_3*100:.1f}%")
    print(f"  Lens Accuracy = {best.lens_accuracy*100:.1f}%")

    return 0


if __name__ == '__main__':
    exit(main())
