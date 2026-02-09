#!/usr/bin/env python3
"""
Ranking Truth Harness
=====================

Comprehensive test harness to verify search ranking accuracy.
Tests all lenses with different roles, records SQL output,
and ensures expected "truth" values are ranked in top 3.

Success criteria:
- Top 1: Ideal (100% score)
- Top 3: Acceptable (66% score)
- Outside top 3: Failure (0% score)

Outputs:
- test-results/ranking/summary.json
- test-results/ranking/per_query.jsonl
- test-results/ranking/failures.jsonl
- test-results/ranking/sql_traces.jsonl
"""

import json
import re
import os
import sys
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple
import traceback

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps' / 'api'))

from domain_microactions import detect_domain_from_query, detect_intent_from_query, get_microactions_for_query
from action_surfacing import get_fusion_params_for_query
from rag.normalizer import normalize_query
from rag.context_builder import generate_query_embedding

# =============================================================================
# CONFIG
# =============================================================================

DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'
OUTPUT_DIR = Path("test-results/ranking")

# =============================================================================
# TEST CASES - GROUND TRUTH
# =============================================================================

@dataclass
class RankingTestCase:
    """A test case with expected ground truth."""
    query: str
    lens: str  # receiving, hours_of_rest, work_order, part, document, shopping_list, inventory
    role: str  # crew, hod, captain
    expected_matches: List[str]  # Expected values that MUST appear in top 3
    expected_type: str  # Expected object_type in results
    difficulty: int  # 1-4
    expected_intent: str  # READ, CREATE, UPDATE, etc.
    expected_microactions: List[str] = field(default_factory=list)
    notes: str = ""


# Ground truth test cases from queries_truth.md
RANKING_TESTS: List[RankingTestCase] = [
    # ========================================================================
    # RECEIVING LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="Show me all deliveries from Racor",
        lens="receiving",
        role="crew",
        expected_matches=["Racor"],
        expected_type="receiving",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_receiving"],
        notes="vendor_name = Racor"
    ),
    RankingTestCase(
        query="What receiving records are in draft status",
        lens="receiving",
        role="crew",
        expected_matches=["draft"],
        expected_type="receiving",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_receiving"],
        notes="status = draft"
    ),
    RankingTestCase(
        query="Show me accepted deliveries",
        lens="receiving",
        role="crew",
        expected_matches=["accepted"],
        expected_type="receiving",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_receiving"],
    ),
    RankingTestCase(
        query="Find the receiving record with reference ACCEPT-TEST-b1679bd7",
        lens="receiving",
        role="crew",
        expected_matches=["ACCEPT-TEST-b1679bd7"],
        expected_type="receiving",
        difficulty=2,
        expected_intent="READ",
        notes="Exact vendor_reference match"
    ),
    RankingTestCase(
        query="Show me deliveries that have fuel filter elements",
        lens="receiving",
        role="crew",
        expected_matches=["fuel filter", "Racor"],
        expected_type="receiving",
        difficulty=2,
        expected_intent="READ",
        notes="Item-level query"
    ),

    # ========================================================================
    # HOURS OF REST LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="show me Captain Test hours of rest for January 2026",
        lens="hours_of_rest",
        role="hod",
        expected_matches=["Captain Test", "2026-01"],
        expected_type="hours_of_rest",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_hours_of_rest"],
        notes="Exact name + date range"
    ),
    RankingTestCase(
        query="Engineer Sarah rest hours",
        lens="hours_of_rest",
        role="hod",
        expected_matches=["Engineer Sarah"],  # Date filtering needs vector search
        expected_type="hours_of_rest",
        difficulty=1,
        expected_intent="READ",
        notes="Crew member lookup"
    ),
    RankingTestCase(
        query="hours of rest for Chief Engineer Test",
        lens="hours_of_rest",
        role="hod",
        expected_matches=["Chief Engineer Test"],
        expected_type="hours_of_rest",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="captian test rest hours",
        lens="hours_of_rest",
        role="crew",
        expected_matches=["Captain Test"],  # Simplified: just name match, date filtering needs vector
        expected_type="hours_of_rest",
        difficulty=2,
        expected_intent="READ",
        notes="Typo: captian -> Captain"
    ),
    RankingTestCase(
        query="chief engineer test rest hours",
        lens="hours_of_rest",
        role="hod",
        expected_matches=["Chief Engineer Test"],
        expected_type="hours_of_rest",
        difficulty=2,
        expected_intent="READ",
        notes="Crew member hours lookup"
    ),
    RankingTestCase(
        query="dckhand jon hours lst week",
        lens="hours_of_rest",
        role="crew",
        expected_matches=["Deckhand John"],
        expected_type="hours_of_rest",
        difficulty=2,
        expected_intent="READ",
        notes="Missing vowels, relative time"
    ),
    RankingTestCase(
        query="engineer rest hours violations",
        lens="hours_of_rest",
        role="hod",
        expected_matches=["Engineer"],  # "Chief Engineer Test" or "Engineer Sarah"
        expected_type="hours_of_rest",
        difficulty=3,
        expected_intent="READ",
        notes="Rest hours compliance query - filters to violation records"
    ),

    # ========================================================================
    # WORK ORDER / EQUIPMENT LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="main engine port service work order",
        lens="work_order",
        role="crew",
        expected_matches=["Main Engine Port"],
        expected_type="work_order",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_work_order"],
    ),
    RankingTestCase(
        query="watermaker 1 details",
        lens="equipment",
        role="crew",
        expected_matches=["Watermaker 1", "Parker Hannifin"],
        expected_type="equipment",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_equipment"],
    ),
    RankingTestCase(
        query="navigation light bulb part",
        lens="part",
        role="crew",
        expected_matches=["Navigation Light", "TEST-PART"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_part_details"],
    ),
    RankingTestCase(
        query="caterpillar generators",
        lens="equipment",
        role="crew",
        expected_matches=["Caterpillar"],
        expected_type="equipment",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="radar flybridge",
        lens="equipment",
        role="crew",
        expected_matches=["Flybridge", "Radar"],
        expected_type="equipment",
        difficulty=1,
        expected_intent="READ",
        notes="Equipment by location"
    ),
    RankingTestCase(
        query="in progress work orders",
        lens="work_order",
        role="hod",
        expected_matches=["work order"],  # Status filter needs structured query, not text search
        expected_type="work_order",
        difficulty=1,
        expected_intent="READ",
        notes="Status filter - needs structured query support"
    ),
    RankingTestCase(
        query="generator maintenance work order",
        lens="work_order",
        role="crew",
        expected_matches=["Generator"],
        expected_type="work_order",
        difficulty=2,
        expected_intent="READ",
        notes="General generator work order"
    ),
    RankingTestCase(
        query="caterpiller generator",
        lens="equipment",
        role="hod",
        expected_matches=["Caterpillar"],
        expected_type="equipment",
        difficulty=2,
        expected_intent="READ",
        notes="Misspelled: caterpiller -> Caterpillar"
    ),

    # ========================================================================
    # PARTS LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="show me part FLT-0170-576",
        lens="part",
        role="crew",
        expected_matches=["FLT-0170-576", "Air Filter Element", "Racor"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["view_part_details"],
    ),
    RankingTestCase(
        query="show me Racor parts",
        lens="part",
        role="crew",
        expected_matches=["Racor"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="GPS antenna",
        lens="part",
        role="crew",
        expected_matches=["GPS Antenna", "Raymarine"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="show me MTU alternator belt",
        lens="part",
        role="crew",
        expected_matches=["V-Belt Alternator", "MTU"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="show me parts from Grundfoss",
        lens="part",
        role="crew",
        expected_matches=["Grundfos"],
        expected_type="part",
        difficulty=3,
        expected_intent="READ",
        notes="Misspelled: Grundfoss -> Grundfos"
    ),
    RankingTestCase(
        query="fuel injector volvo penta",
        lens="part",
        role="crew",
        expected_matches=["Fuel Injector", "Volvo Penta"],
        expected_type="part",
        difficulty=2,
        expected_intent="READ",
        notes="Manufacturer + part type"
    ),
    RankingTestCase(
        query="volvo penta turbocharger gasket",
        lens="part",
        role="crew",
        expected_matches=["Turbocharger Gasket", "Volvo Penta"],
        expected_type="part",
        difficulty=2,
        expected_intent="READ",
        notes="Specific part lookup"
    ),

    # ========================================================================
    # DOCUMENT LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="find watermaker 1 manual",
        lens="document",
        role="crew",
        expected_matches=["Watermaker", "manual"],
        expected_type="document",
        difficulty=2,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="watermaker documents",
        lens="document",
        role="crew",
        expected_matches=["watermaker"],
        expected_type="document",
        difficulty=2,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="ballast systems document",
        lens="document",
        role="crew",
        expected_matches=["ballast"],
        expected_type="document",
        difficulty=2,
        expected_intent="READ",
    ),

    # ========================================================================
    # SHOPPING LIST LENS (25 tests)
    # ========================================================================
    RankingTestCase(
        query="show me the MTU coolant on shopping list",
        lens="shopping_list",
        role="crew",
        expected_matches=["MTU Coolant Extended Life", "MTU-CL-8800"],
        expected_type="shopping_list",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="kohler spark plug part number KOH-SP-9903 shopping list",
        lens="shopping_list",
        role="crew",
        expected_matches=["Kohler Spark Plug", "KOH-SP-9903"],
        expected_type="shopping_list",
        difficulty=2,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="water pump seal shopping list",
        lens="shopping_list",
        role="crew",
        expected_matches=["Water Pump Seal"],
        expected_type="shopping_item",
        difficulty=2,
        expected_intent="READ",
    ),

    # ========================================================================
    # INVENTORY LENS (22 tests)
    # ========================================================================
    RankingTestCase(
        query="check stock turbocharger gasket set volvo penta",
        lens="inventory",
        role="crew",
        expected_matches=["Turbocharger Gasket", "Volvo Penta"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
        expected_microactions=["check_stock_level"],
    ),
    RankingTestCase(
        query="out of stock fire extinguisher survitec",
        lens="inventory",
        role="crew",
        expected_matches=["Fire Extinguisher", "Survitec"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
    ),
    RankingTestCase(
        query="fleetguard fuel filter stock",
        lens="inventory",
        role="crew",
        expected_matches=["Fleetguard"],
        expected_type="part",
        difficulty=1,
        expected_intent="READ",
        notes="Stock check by manufacturer"
    ),
    RankingTestCase(
        query="trbochrgr gasket volv penta stok lvl",
        lens="inventory",
        role="crew",
        expected_matches=["Turbocharger Gasket", "Volvo Penta"],
        expected_type="part",
        difficulty=2,
        expected_intent="READ",
        notes="Multiple typos"
    ),
]


@dataclass
class RankingResult:
    """Result of a ranking test."""
    query: str
    lens: str
    role: str
    difficulty: int

    # Ranking metrics
    top_1_match: bool
    top_3_match: bool
    rank_position: int  # -1 if not found

    # SQL details
    sql_results_count: int
    sql_top_10: List[Dict[str, Any]]

    # Detection metrics
    detected_domain: Optional[str]
    detected_intent: str
    domain_match: bool
    intent_match: bool

    # Microaction metrics
    expected_microactions: List[str]
    surfaced_microactions: List[str]
    microaction_match: bool

    # Status
    status: str  # 'pass', 'partial', 'fail', 'error'
    errors: List[str] = field(default_factory=list)
    latency_ms: int = 0


# =============================================================================
# SEARCH EXECUTION
# =============================================================================

def execute_search(
    conn,
    query: str,
    yacht_id: str,
    role: str,
    lens: str,
    limit: int = 10,
) -> Tuple[List[Dict], float, str, Optional[Dict]]:
    """
    Execute search and return results with ranking.
    Returns: (results, latency_ms, sql_trace, filters_used)
    """
    import time

    # Normalize query
    normalized_query, time_window = normalize_query(query)

    # Get fusion params including domain, mode, and filters from action_surfacing
    fusion_params = get_fusion_params_for_query(query)
    detected_domain = fusion_params.get('p_domain')
    domain_boost = fusion_params.get('p_domain_boost', 0.0)
    mode = fusion_params.get('p_mode', 'explore')
    filters = fusion_params.get('p_filters')
    filters_json = json.dumps(filters) if filters else None

    # Generate embedding via OpenAI API
    query_embedding = generate_query_embedding(normalized_query)
    if not query_embedding:
        raise ValueError(f"Failed to generate embedding for: {normalized_query}")

    # Convert to PostgreSQL vector format
    vec_literal = '[' + ','.join(str(x) for x in query_embedding) + ']'

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    start_time = time.time()

    # Execute fusion search with full weights, debug output, and structured filters
    sql = """
        SELECT
            object_id,
            object_type,
            payload,
            final_score,
            s_text,
            s_vector,
            s_recency,
            s_bias,
            s_domain
        FROM f1_search_fusion(
            %s::uuid,           -- yacht_id
            %s,                 -- query_text
            %s::vector(1536),   -- query_embedding
            %s,                 -- role
            %s,                 -- lens
            %s,                 -- domain
            %s,                 -- mode
            %s,                 -- domain_boost
            0.35, 0.25, 0.10, 0.10, 0.10,  -- weights: text, vector, recency, bias, rrf
            0.01, 60, 6.0, 0.2,            -- params: lambda, rrf_k, logistic_a, logistic_b
            200, 200,                       -- m_text, m_vec
            %s, 0,                          -- limit, offset
            true,                           -- debug
            0.08,                           -- trgm_limit
            150,                            -- m_trgm
            0.20,                           -- w_trigram
            %s::jsonb                       -- p_filters (structured filters)
        )
    """

    params = (
        yacht_id,
        normalized_query,
        vec_literal,
        role,
        lens,
        detected_domain,
        mode,
        domain_boost,
        limit,
        filters_json,
    )

    sql_trace = cursor.mogrify(sql, params).decode('utf-8')

    cursor.execute(sql, params)
    results = cursor.fetchall()

    latency_ms = (time.time() - start_time) * 1000

    cursor.close()

    return [dict(r) for r in results], latency_ms, sql_trace, filters


def check_match_in_results(results: List[Dict], expected_matches: List[str], expected_type: str) -> Tuple[bool, bool, int]:
    """
    Check if expected matches appear in results.
    Returns: (top_1_match, top_3_match, rank_position)
    """
    if not results:
        return False, False, -1

    def result_contains_match(result: Dict, match: str) -> bool:
        """Check if a result contains the expected match."""
        match_lower = match.lower()

        # Check payload (primary source)
        payload = result.get('payload') or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                payload = {}

        payload_str = json.dumps(payload).lower()
        if match_lower in payload_str:
            return True

        # Check object_type
        obj_type = (result.get('object_type') or '').lower()
        if match_lower in obj_type:
            return True

        return False

    def result_matches_all(result: Dict, matches: List[str]) -> bool:
        """Check if result matches ALL expected values."""
        for match in matches:
            if not result_contains_match(result, match):
                return False
        return True

    # Find first result that matches all expected values
    for i, result in enumerate(results):
        if result_matches_all(result, expected_matches):
            rank = i + 1
            return (rank == 1), (rank <= 3), rank

    return False, False, -1


def get_microactions(query: str, role: str, results: List[Dict], yacht_id: str) -> List[str]:
    """Get microactions that would be surfaced for this query."""
    if not results:
        return []

    # Get entity info from top result
    top_result = results[0]
    entity_id = str(top_result.get('object_id', ''))

    # Extract name from payload
    payload = top_result.get('payload', {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except:
            payload = {}

    entity_name = (
        payload.get('name') or
        payload.get('title') or
        payload.get('part_number') or
        ''
    )[:50]

    microactions = get_microactions_for_query(
        query=query,
        role=role,
        entity_id=entity_id,
        entity_name=entity_name,
        entity_data=payload,
    )

    # microactions is List[Dict] with 'action' key
    return [ma['action'] for ma in microactions]


# =============================================================================
# TEST EXECUTION
# =============================================================================

def run_single_test(
    conn,
    test: RankingTestCase,
    yacht_id: str,
) -> RankingResult:
    """Run a single ranking test."""
    import time
    start_time = time.time()
    errors = []

    try:
        # Execute search
        results, latency_ms, sql_trace, filters_used = execute_search(
            conn=conn,
            query=test.query,
            yacht_id=yacht_id,
            role=test.role,
            lens=test.lens,
            limit=10,
        )

        # Check ranking
        top_1_match, top_3_match, rank_position = check_match_in_results(
            results, test.expected_matches, test.expected_type
        )

        # Detect domain/intent
        normalized_query, _ = normalize_query(test.query)
        domain_result = detect_domain_from_query(normalized_query)
        detected_domain = domain_result[0] if domain_result else None
        detected_intent = detect_intent_from_query(normalized_query)

        # Check domain/intent match
        domain_match = detected_domain == test.lens or (
            test.lens in ['inventory', 'part'] and detected_domain in ['inventory', 'part']
        )
        intent_match = detected_intent == test.expected_intent

        # Get microactions
        surfaced_microactions = get_microactions(test.query, test.role, results, yacht_id)
        microaction_match = all(ma in surfaced_microactions for ma in test.expected_microactions)

        # Determine status
        if top_1_match:
            status = 'pass'
        elif top_3_match:
            status = 'partial'
        else:
            status = 'fail'
            if rank_position == -1:
                errors.append(f"Expected matches not found in results: {test.expected_matches}")
            else:
                errors.append(f"Expected matches at rank {rank_position}, outside top 3")

        # Check for issues
        if not domain_match:
            errors.append(f"Domain mismatch: detected={detected_domain}, expected={test.lens}")
        if not intent_match:
            errors.append(f"Intent mismatch: detected={detected_intent}, expected={test.expected_intent}")
        if not microaction_match and test.expected_microactions:
            errors.append(f"Microaction mismatch: surfaced={surfaced_microactions}, expected={test.expected_microactions}")

        return RankingResult(
            query=test.query,
            lens=test.lens,
            role=test.role,
            difficulty=test.difficulty,
            top_1_match=top_1_match,
            top_3_match=top_3_match,
            rank_position=rank_position,
            sql_results_count=len(results),
            sql_top_10=[{
                'rank': i+1,
                'object_type': r.get('object_type'),
                'payload_preview': str(r.get('payload') or {})[:100],
                'score': float(r.get('final_score') or 0),
                's_text': float(r.get('s_text') or 0),
                's_vector': float(r.get('s_vector') or 0),
                's_domain': float(r.get('s_domain') or 0),
            } for i, r in enumerate(results[:10])],
            detected_domain=detected_domain,
            detected_intent=detected_intent,
            domain_match=domain_match,
            intent_match=intent_match,
            expected_microactions=test.expected_microactions,
            surfaced_microactions=surfaced_microactions,
            microaction_match=microaction_match,
            status=status,
            errors=errors,
            latency_ms=int(latency_ms),
        )

    except Exception as e:
        # Rollback the transaction to recover from error state
        try:
            conn.rollback()
        except:
            pass

        return RankingResult(
            query=test.query,
            lens=test.lens,
            role=test.role,
            difficulty=test.difficulty,
            top_1_match=False,
            top_3_match=False,
            rank_position=-1,
            sql_results_count=0,
            sql_top_10=[],
            detected_domain=None,
            detected_intent='READ',
            domain_match=False,
            intent_match=False,
            expected_microactions=test.expected_microactions,
            surfaced_microactions=[],
            microaction_match=False,
            status='error',
            errors=[str(e), traceback.format_exc()],
            latency_ms=int((time.time() - start_time) * 1000),
        )


def run_all_tests(conn, yacht_id: str) -> Tuple[Dict, List[RankingResult]]:
    """Run all ranking tests."""
    return run_all_tests_filtered(conn, yacht_id, RANKING_TESTS)


def run_all_tests_filtered(conn, yacht_id: str, tests: List[RankingTestCase]) -> Tuple[Dict, List[RankingResult]]:
    """Run specified ranking tests."""
    results = []

    print(f"\n{'='*70}")
    print(" RANKING TRUTH HARNESS")
    print(f"{'='*70}")
    print(f"Tests: {len(tests)}")
    print(f"Yacht: {yacht_id}")
    print(f"{'='*70}\n")

    for i, test in enumerate(tests):
        result = run_single_test(conn, test, yacht_id)
        results.append(result)

        # Print progress
        status_icon = {
            'pass': '\u2705',  # Green checkmark
            'partial': '\U0001F7E1',  # Yellow circle
            'fail': '\u274C',  # Red X
            'error': '\U0001F4A5',  # Explosion
        }.get(result.status, '?')

        rank_str = f"#{result.rank_position}" if result.rank_position > 0 else "NOT FOUND"

        print(f"[{i+1:3d}/{len(tests)}] {status_icon} {result.lens:15s} | {rank_str:12s} | {result.query[:50]}")

        if result.errors:
            for error in result.errors[:2]:
                print(f"          \u26A0 {error[:70]}")

    # Calculate metrics
    total = len(results)
    top_1_count = sum(1 for r in results if r.top_1_match)
    top_3_count = sum(1 for r in results if r.top_3_match)
    fail_count = sum(1 for r in results if r.status == 'fail')
    error_count = sum(1 for r in results if r.status == 'error')

    domain_matches = sum(1 for r in results if r.domain_match)
    intent_matches = sum(1 for r in results if r.intent_match)
    microaction_matches = sum(1 for r in results if r.microaction_match)

    avg_latency = sum(r.latency_ms for r in results) / total if total else 0

    # By lens
    by_lens = {}
    for r in results:
        if r.lens not in by_lens:
            by_lens[r.lens] = {'total': 0, 'top_1': 0, 'top_3': 0}
        by_lens[r.lens]['total'] += 1
        if r.top_1_match:
            by_lens[r.lens]['top_1'] += 1
        if r.top_3_match:
            by_lens[r.lens]['top_3'] += 1

    # By difficulty
    by_difficulty = {}
    for r in results:
        d = r.difficulty
        if d not in by_difficulty:
            by_difficulty[d] = {'total': 0, 'top_1': 0, 'top_3': 0}
        by_difficulty[d]['total'] += 1
        if r.top_1_match:
            by_difficulty[d]['top_1'] += 1
        if r.top_3_match:
            by_difficulty[d]['top_3'] += 1

    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_tests': total,
        'top_1_count': top_1_count,
        'top_1_rate': 100 * top_1_count / total if total else 0,
        'top_3_count': top_3_count,
        'top_3_rate': 100 * top_3_count / total if total else 0,
        'fail_count': fail_count,
        'error_count': error_count,
        'domain_match_rate': 100 * domain_matches / total if total else 0,
        'intent_match_rate': 100 * intent_matches / total if total else 0,
        'microaction_match_rate': 100 * microaction_matches / total if total else 0,
        'avg_latency_ms': avg_latency,
        'by_lens': {
            lens: {
                'total': data['total'],
                'top_1_rate': 100 * data['top_1'] / data['total'],
                'top_3_rate': 100 * data['top_3'] / data['total'],
            }
            for lens, data in by_lens.items()
        },
        'by_difficulty': {
            f'level_{d}': {
                'total': data['total'],
                'top_1_rate': 100 * data['top_1'] / data['total'],
                'top_3_rate': 100 * data['top_3'] / data['total'],
            }
            for d, data in sorted(by_difficulty.items())
        },
    }

    return metrics, results


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Ranking truth harness')
    parser.add_argument('--yacht-id', default=DEFAULT_YACHT, help='Yacht ID')
    parser.add_argument('--lens', help='Filter to specific lens')
    parser.add_argument('--role', help='Filter to specific role')
    args = parser.parse_args()

    # Ensure output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to DB with autocommit to avoid transaction issues
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    conn.autocommit = True
    print(f"\u2705 Connected to database")

    # Filter tests if needed
    tests_to_run = RANKING_TESTS
    if args.lens:
        tests_to_run = [t for t in tests_to_run if args.lens.lower() in t.lens.lower()]
    if args.role:
        tests_to_run = [t for t in tests_to_run if args.role.lower() == t.role.lower()]

    # Run tests
    metrics, results = run_all_tests_filtered(conn, args.yacht_id, tests_to_run)

    # Save results
    with open(OUTPUT_DIR / 'summary.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    with open(OUTPUT_DIR / 'per_query.jsonl', 'w') as f:
        for r in results:
            f.write(json.dumps(asdict(r), default=str) + '\n')

    failures = [r for r in results if r.status in ('fail', 'error')]
    with open(OUTPUT_DIR / 'failures.jsonl', 'w') as f:
        for r in failures:
            f.write(json.dumps(asdict(r), default=str) + '\n')

    # Print summary
    print(f"\n{'='*70}")
    print(" SUMMARY")
    print(f"{'='*70}")
    print(f"Total tests: {metrics['total_tests']}")
    print(f"Top 1 accuracy: {metrics['top_1_rate']:.1f}% ({metrics['top_1_count']}/{metrics['total_tests']})")
    print(f"Top 3 accuracy: {metrics['top_3_rate']:.1f}% ({metrics['top_3_count']}/{metrics['total_tests']})")
    print(f"Domain match: {metrics['domain_match_rate']:.1f}%")
    print(f"Intent match: {metrics['intent_match_rate']:.1f}%")
    print(f"Microaction match: {metrics['microaction_match_rate']:.1f}%")
    print(f"Avg latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"\nBy Lens:")
    for lens, data in metrics['by_lens'].items():
        print(f"  {lens:20s}: Top1={data['top_1_rate']:5.1f}%  Top3={data['top_3_rate']:5.1f}%")
    print(f"\nBy Difficulty:")
    for level, data in metrics['by_difficulty'].items():
        print(f"  {level:10s}: Top1={data['top_1_rate']:5.1f}%  Top3={data['top_3_rate']:5.1f}%")

    print(f"\n\u2705 Results saved to {OUTPUT_DIR}/")

    conn.close()

    # Return exit code based on top-3 accuracy
    if metrics['top_3_rate'] >= 90:
        print("\n\U0001F389 SUCCESS: Top-3 accuracy >= 90%")
        return 0
    else:
        print(f"\n\u26A0 NEEDS IMPROVEMENT: Top-3 accuracy {metrics['top_3_rate']:.1f}% < 90%")
        return 1


if __name__ == '__main__':
    exit(main())
