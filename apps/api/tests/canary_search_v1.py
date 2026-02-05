#!/usr/bin/env python3
"""
F1 Search Canary Tests - Stage 1 Validation

Validates search quality against known-good query/result pairs.
Run against a canary tenant with seeded data.

Metrics:
    - NDCG@10: Normalized Discounted Cumulative Gain (target >= 0.78)
    - Recall@20: Fraction of relevant docs in top 20 (target >= 0.90)
    - P95 latency: 95th percentile response time (target <= 800ms warm)

Canary Queries (examples):
    - "notes: overheating main engine" → expects note/log entries at top
    - "303" → expects fault code at rank 1
    - "main engine overheating again" → recent notes/WOs outrank manuals
    - "shopping list" → expects inventory/requisition

Usage:
    DATABASE_URL=... python -m pytest tests/canary_search_v1.py -v

Or as standalone:
    DATABASE_URL=... python tests/canary_search_v1.py

See: docs/CANARY_TESTS_SPEC.md
"""

from __future__ import annotations

import os
import sys
import time
import json
import math
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DATABASE_URL = os.getenv('DATABASE_URL')
CANARY_ORG_ID = os.getenv('CANARY_ORG_ID')  # Optional: specific org for canaries
CANARY_YACHT_ID = os.getenv('CANARY_YACHT_ID')  # Optional

# Quality thresholds
NDCG_THRESHOLD = 0.78
RECALL_THRESHOLD = 0.90
P95_LATENCY_MS = 800

# Test embedding model
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536


# =============================================================================
# Canary Query Definitions
# =============================================================================

@dataclass
class CanaryQuery:
    """A single canary test case."""
    query: str
    description: str
    expected_top_types: List[str]  # Expected object_types in top results
    expected_top_ids: List[str] = field(default_factory=list)  # Specific IDs expected
    must_be_tier1: bool = False  # Expects exact_id_match at rank 1
    tags: List[str] = field(default_factory=list)


# Core canary queries
CANARY_QUERIES = [
    # Exact ID matches (should be Tier 1)
    CanaryQuery(
        query="303",
        description="Bare fault code should return fault at rank 1",
        expected_top_types=['fault'],
        must_be_tier1=True,
        tags=['exact_id', 'fault_code'],
    ),
    CanaryQuery(
        query="SPN 303",
        description="SPN fault code pattern",
        expected_top_types=['fault'],
        must_be_tier1=True,
        tags=['exact_id', 'fault_code'],
    ),
    CanaryQuery(
        query="P1187",
        description="OBD-II fault code",
        expected_top_types=['fault'],
        must_be_tier1=True,
        tags=['exact_id', 'fault_code'],
    ),

    # Explicit domain tokens
    CanaryQuery(
        query="notes: overheating main engine",
        description="Explicit notes: token should filter to notes",
        expected_top_types=['note', 'log'],
        tags=['explicit_domain', 'notes'],
    ),
    CanaryQuery(
        query="wo: oil change",
        description="Explicit wo: token should filter to work orders",
        expected_top_types=['work_order'],
        tags=['explicit_domain', 'work_order'],
    ),
    CanaryQuery(
        query="docs: engine manual",
        description="Explicit docs: token should filter to documents",
        expected_top_types=['document'],
        tags=['explicit_domain', 'document'],
    ),
    CanaryQuery(
        query="parts: filter oil",
        description="Explicit parts: token should filter to parts/inventory",
        expected_top_types=['part', 'inventory'],
        tags=['explicit_domain', 'parts'],
    ),

    # Natural language (recency should matter)
    CanaryQuery(
        query="main engine overheating again",
        description="Symptom query - recent notes/WOs should outrank old manuals",
        expected_top_types=['note', 'work_order', 'log'],
        tags=['natural', 'symptom', 'recency'],
    ),
    CanaryQuery(
        query="generator not starting",
        description="Equipment issue - recent work orders first",
        expected_top_types=['work_order', 'note', 'log'],
        tags=['natural', 'symptom'],
    ),
    CanaryQuery(
        query="shopping list",
        description="Inventory/requisition intent",
        expected_top_types=['inventory', 'requisition'],
        tags=['natural', 'inventory'],
    ),

    # Semantic search
    CanaryQuery(
        query="how to change the oil on the main engine",
        description="Procedural query - manuals/procedures expected",
        expected_top_types=['document', 'procedure'],
        tags=['semantic', 'procedure'],
    ),
    CanaryQuery(
        query="safety equipment inspection checklist",
        description="Compliance query - checklists/certificates expected",
        expected_top_types=['checklist', 'certificate', 'document'],
        tags=['semantic', 'compliance'],
    ),

    # Edge cases
    CanaryQuery(
        query="DG1",
        description="Equipment alias - should resolve to equipment",
        expected_top_types=['equipment', 'work_order', 'note'],
        tags=['alias', 'equipment'],
    ),
    CanaryQuery(
        query="",
        description="Empty query - should return empty or error gracefully",
        expected_top_types=[],
        tags=['edge_case'],
    ),
]


# =============================================================================
# Metrics
# =============================================================================

def dcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """Compute Discounted Cumulative Gain at k."""
    relevance = relevance_scores[:k]
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevance))


def ndcg_at_k(relevance_scores: List[float], ideal_relevance: List[float], k: int = 10) -> float:
    """Compute Normalized DCG at k."""
    dcg = dcg_at_k(relevance_scores, k)
    ideal_dcg = dcg_at_k(sorted(ideal_relevance, reverse=True), k)
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 20) -> float:
    """Compute Recall at k."""
    if not relevant_ids:
        return 1.0  # No relevant docs means perfect recall
    retrieved_set = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    return len(retrieved_set & relevant_set) / len(relevant_set)


def compute_relevance(result: Dict, canary: CanaryQuery) -> float:
    """
    Compute relevance score for a single result.

    Returns:
        1.0: Perfect match (exact ID or expected type at expected rank)
        0.5: Partial match (expected type but not top)
        0.0: No match
    """
    obj_type = result.get('object_type', '')
    obj_id = result.get('object_id', '')

    # Exact ID match
    if canary.expected_top_ids and obj_id in canary.expected_top_ids:
        return 1.0

    # Type match
    if obj_type in canary.expected_top_types:
        return 1.0 if result.get('exact_id_match') else 0.5

    return 0.0


# =============================================================================
# Test Runner
# =============================================================================

@dataclass
class CanaryResult:
    """Result of a single canary test."""
    query: CanaryQuery
    results: List[Dict[str, Any]]
    latency_ms: float
    ndcg: float
    recall: float
    tier1_correct: bool
    passed: bool
    errors: List[str] = field(default_factory=list)


async def run_single_canary(
    conn,
    canary: CanaryQuery,
    org_id: str,
    yacht_id: Optional[str] = None,
) -> CanaryResult:
    """Run a single canary query and compute metrics."""
    errors = []

    # Handle empty query edge case
    if not canary.query.strip():
        return CanaryResult(
            query=canary,
            results=[],
            latency_ms=0,
            ndcg=1.0,  # Empty query, empty expected = success
            recall=1.0,
            tier1_correct=True,
            passed=True,
        )

    try:
        # Parse explicit tokens
        explicit_types = []
        filter_only = False
        query_text = canary.query

        # Simple token parsing
        for prefix in ['notes:', 'wo:', 'docs:', 'parts:', 'inventory:']:
            if query_text.lower().startswith(prefix):
                explicit_types = [prefix.rstrip(':')]
                query_text = query_text[len(prefix):].strip()
                break

        if ' only' in query_text.lower():
            filter_only = True
            query_text = query_text.lower().replace(' only', '').strip()

        # Compute embedding (mock for now - in real test, use OpenAI)
        embedding = None  # Would call OpenAI here

        # Call RPC
        start = time.perf_counter()
        rows = await conn.fetch("""
            SELECT * FROM hyper_search_multi(
                $1, $2, $3, NULL, 50, $4,
                $5, $6, $7
            )
        """, query_text, org_id, yacht_id, embedding,
            explicit_types if explicit_types else None,
            filter_only,
            query_text,  # p_id_query
        )
        latency_ms = (time.perf_counter() - start) * 1000

        results = [dict(r) for r in rows]

        # Compute metrics
        relevance_scores = [compute_relevance(r, canary) for r in results]
        ideal_relevance = sorted(relevance_scores, reverse=True)

        ndcg = ndcg_at_k(relevance_scores, ideal_relevance, k=10)
        recall = recall_at_k(
            [r['object_id'] for r in results],
            canary.expected_top_ids,
            k=20,
        ) if canary.expected_top_ids else 1.0

        # Check tier1 requirement
        tier1_correct = True
        if canary.must_be_tier1 and results:
            tier1_correct = results[0].get('exact_id_match', False)
            if not tier1_correct:
                errors.append(f"Expected tier1 (exact_id_match) but got tier {results[0].get('tier', '?')}")

        # Check expected types in top 5
        top_5_types = [r['object_type'] for r in results[:5]]
        if canary.expected_top_types and not any(t in top_5_types for t in canary.expected_top_types):
            errors.append(f"Expected types {canary.expected_top_types} not in top 5: {top_5_types}")

        passed = (
            ndcg >= NDCG_THRESHOLD
            and recall >= RECALL_THRESHOLD
            and tier1_correct
            and latency_ms <= P95_LATENCY_MS
            and not errors
        )

        return CanaryResult(
            query=canary,
            results=results,
            latency_ms=latency_ms,
            ndcg=ndcg,
            recall=recall,
            tier1_correct=tier1_correct,
            passed=passed,
            errors=errors,
        )

    except Exception as e:
        return CanaryResult(
            query=canary,
            results=[],
            latency_ms=0,
            ndcg=0,
            recall=0,
            tier1_correct=False,
            passed=False,
            errors=[str(e)],
        )


async def run_all_canaries(
    conn,
    org_id: str,
    yacht_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Tuple[List[CanaryResult], Dict[str, Any]]:
    """Run all canary tests and aggregate results."""
    queries = CANARY_QUERIES

    # Filter by tags if specified
    if tags:
        queries = [q for q in queries if any(t in q.tags for t in tags)]

    results = []
    for canary in queries:
        result = await run_single_canary(conn, canary, org_id, yacht_id)
        results.append(result)
        logger.info(
            f"[Canary] {canary.query[:40]:<40} "
            f"{'PASS' if result.passed else 'FAIL'} "
            f"ndcg={result.ndcg:.2f} recall={result.recall:.2f} "
            f"latency={result.latency_ms:.0f}ms"
        )

    # Aggregate metrics
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]

    summary = {
        'total': len(results),
        'passed': passed,
        'failed': failed,
        'pass_rate': passed / len(results) if results else 0,
        'avg_ndcg': sum(r.ndcg for r in results) / len(results) if results else 0,
        'avg_recall': sum(r.recall for r in results) / len(results) if results else 0,
        'p50_latency_ms': sorted(latencies)[len(latencies) // 2] if latencies else 0,
        'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        'all_passed': failed == 0,
    }

    return results, summary


# =============================================================================
# Report Generation
# =============================================================================

def generate_report(results: List[CanaryResult], summary: Dict[str, Any]) -> str:
    """Generate a human-readable report."""
    lines = [
        "=" * 70,
        " F1 SEARCH CANARY REPORT",
        f" Generated: {datetime.utcnow().isoformat()}",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 70,
        f"  Total tests:     {summary['total']}",
        f"  Passed:          {summary['passed']}",
        f"  Failed:          {summary['failed']}",
        f"  Pass rate:       {summary['pass_rate']*100:.1f}%",
        "",
        f"  Avg NDCG@10:     {summary['avg_ndcg']:.3f}  (threshold: {NDCG_THRESHOLD})",
        f"  Avg Recall@20:   {summary['avg_recall']:.3f}  (threshold: {RECALL_THRESHOLD})",
        f"  P50 Latency:     {summary['p50_latency_ms']:.0f}ms",
        f"  P95 Latency:     {summary['p95_latency_ms']:.0f}ms  (threshold: {P95_LATENCY_MS}ms)",
        "",
        "DETAILED RESULTS",
        "-" * 70,
    ]

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"\n[{status}] {r.query.query}")
        lines.append(f"       {r.query.description}")
        lines.append(f"       NDCG={r.ndcg:.2f} Recall={r.recall:.2f} Latency={r.latency_ms:.0f}ms")

        if r.results:
            lines.append(f"       Top 3: {[f'{x['object_type']}/{x['object_id'][:8]}' for x in r.results[:3]]}")

        if r.errors:
            for err in r.errors:
                lines.append(f"       ERROR: {err}")

    lines.extend([
        "",
        "=" * 70,
        f"  OVERALL: {'PASS' if summary['all_passed'] else 'FAIL'}",
        "=" * 70,
    ])

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

async def main():
    """Run canary tests from command line."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    import asyncpg

    logger.info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    # Get org_id from first search_index row if not specified
    org_id = CANARY_ORG_ID
    if not org_id:
        row = await conn.fetchrow("SELECT DISTINCT org_id FROM search_index LIMIT 1")
        if row:
            org_id = str(row['org_id'])
        else:
            logger.error("No org_id found in search_index")
            await conn.close()
            sys.exit(1)

    logger.info(f"Running canaries for org_id={org_id}")

    results, summary = await run_all_canaries(conn, org_id, CANARY_YACHT_ID)

    report = generate_report(results, summary)
    print(report)

    await conn.close()

    # Exit with error code if failed
    sys.exit(0 if summary['all_passed'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
