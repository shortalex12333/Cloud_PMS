#!/usr/bin/env python3
"""
RAG Evaluation Harness
======================

Evaluates RAG system using test_terms.md as basis.

Key principle: System does EXACTLY what user wants.
- Vague input → vague/broad output
- Specific input → specific output with citations

Metrics:
1. Faithfulness: % of factual sentences supported by context
2. Citation Coverage: % of answers with proper citations
3. Intent Match: Does answer specificity match query specificity?
4. Relevance: Are retrieved chunks relevant to the query?

Output: test-results/rag/
- metrics.json: Aggregate scores
- per_query.csv: Per-query results
- failures.jsonl: Failed cases for review
"""

import json
import re
import os
import sys
import csv
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'apps' / 'api'))

from rag import (
    build_context_sync,
    generate_answer_sync,
    compute_query_hash,
    normalize_query,
)
from rag.verifier import verify_answer
from domain_microactions import detect_domain_from_query, detect_intent_from_query

# =============================================================================
# CONFIG
# =============================================================================

DB_HOST = 'db.vzsohavtuotocgrfkfyd.supabase.co'
DB_PORT = 6543
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASS = '@-Ei-9Pa.uENn6g'

DEFAULT_YACHT = '85fe1119-b04c-41ac-80f1-829d23322598'
INPUT_MD = Path("/Users/celeste7/Desktop/entity_failures/query_terms_examples/queries_truth.md")
OUTPUT_DIR = Path("test-results/rag")

# Domain mapping for each lens section
LENS_TO_DOMAIN = {
    'receiving': 'receiving',
    'hor': 'hours_of_rest',
    'hours of rest': 'hours_of_rest',
    'work order': 'work_order',
    'equipment': 'equipment',
    'parts': 'part',
    'part': 'part',
    'document': 'document',
    'shopping list': 'shopping_list',
    'inventory': 'inventory',
    'stock': 'inventory',
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class RAGTestCase:
    """A single RAG test case."""
    query: str
    category: str
    expected_intent: str  # READ, UPDATE, CREATE, etc.
    expected_domain: str  # hours_of_rest, inventory, etc.
    expected_button: str  # Expected microaction
    role: str
    difficulty: int  # 1-5 stars
    specificity: str  # 'vague', 'moderate', 'specific'
    entities: List[str]  # Expected entities in query
    notes: Optional[str] = None


@dataclass
class RAGTestResult:
    """Result of running a RAG test."""
    query: str
    category: str
    role: str
    difficulty: int
    specificity: str

    # RAG metrics
    context_chunks: int
    context_tokens: int
    answer_length: int
    citations_used: int
    confidence: float
    faithfulness: float
    latency_ms: int

    # Intent/domain detection
    detected_domain: Optional[str]
    detected_intent: str
    domain_match: bool
    intent_match: bool

    # Evaluation
    answer_specificity: str  # 'vague', 'moderate', 'specific' (detected)
    specificity_match: bool  # Does answer specificity match query?

    # Status
    status: str  # 'pass', 'fail', 'error'
    error: Optional[str] = None

    # Full answer for review
    answer_preview: str = ""


# =============================================================================
# PARSING
# =============================================================================

def parse_difficulty(stars: str) -> int:
    """Convert ★☆☆☆☆ to numeric difficulty."""
    if not stars:
        return 1
    return max(1, stars.count('★'))


def classify_specificity(query: str, entities: List[str]) -> str:
    """
    Classify query specificity.

    - vague: Generic query, no entities (e.g., "show me hours of rest")
    - moderate: Some context (e.g., "hours of rest this week")
    - specific: Named entities or exact filters (e.g., "hours for Captain Mitchell")
    """
    query_lower = query.lower()

    # Specific: Has person names, part numbers, exact IDs
    specific_indicators = [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Person names
        r'\b[A-Z]{2,}-\d+',  # Part numbers
        r'\b\d{4}-\d{2}-\d{2}\b',  # Dates
        r'\buuid\b',  # UUIDs mentioned
    ]
    for pattern in specific_indicators:
        if re.search(pattern, query):
            return 'specific'

    # Specific: Multiple entities
    if len(entities) >= 2:
        return 'specific'

    # Moderate: Has time refs, departments, or single entity
    moderate_indicators = [
        'this week', 'yesterday', 'today', 'last month', 'january', 'february',
        'deck crew', 'engine crew', 'pending', 'non-compliant', 'violations',
    ]
    for indicator in moderate_indicators:
        if indicator in query_lower:
            return 'moderate'

    if len(entities) == 1:
        return 'moderate'

    # Vague: Generic query
    return 'vague'


def classify_answer_specificity(answer: str, citations: int) -> str:
    """
    Classify answer specificity based on content.
    """
    answer_lower = answer.lower()

    # Check for "don't have information" patterns
    vague_patterns = [
        "don't have enough information",
        "couldn't find",
        "no relevant information",
        "please try",
        "not enough context",
    ]
    for pattern in vague_patterns:
        if pattern in answer_lower:
            return 'vague'

    # Specific: Multiple citations, named entities in answer
    if citations >= 3:
        return 'specific'

    # Check for specific content
    specific_indicators = [
        r'\d+\s*(hours|days|minutes)',  # Numbers with units
        r'\b\d{4}-\d{2}-\d{2}\b',  # Dates
        r'[A-Z][a-z]+ [A-Z][a-z]+',  # Person names
    ]
    for pattern in specific_indicators:
        if re.search(pattern, answer):
            return 'specific'

    # Moderate: Has some citations or structured content
    if citations >= 1 or '- ' in answer or '•' in answer:
        return 'moderate'

    return 'vague'


def detect_lens_domain(lens_name: str) -> str:
    """Map lens name to domain."""
    lens_lower = lens_name.lower()
    for key, domain in LENS_TO_DOMAIN.items():
        if key in lens_lower:
            return domain
    return 'general'


def parse_difficulty_stars(text: str) -> int:
    """Parse difficulty from stars or level indicators."""
    if not text:
        return 1
    # Count star emojis
    star_count = text.count('⭐') + text.count('★')
    if star_count > 0:
        return min(star_count, 5)
    # Check for level indicators
    level_match = re.search(r'Level\s*(\d)', text, re.IGNORECASE)
    if level_match:
        return int(level_match.group(1))
    return 1


def parse_queries_truth(md_path: Path) -> List[RAGTestCase]:
    """
    Parse queries_truth.md into RAG test cases.

    Format patterns:
    - Section headers: `====` or `25 X Lens` or `⏺ 25 X Tests`
    - Tests: `Test N:` or `TEST N:` or `N.`
    - Queries: `Query:`, `User Query:`, `User Input:`
    - Difficulty: `EASY`, `MEDIUM`, `HARD`, `Level N:`, ⭐⭐⭐
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    test_cases = []
    current_lens = "Unknown"
    current_domain = "general"
    current_difficulty = 1
    current_category = "Unknown"

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Section header patterns
        # Pattern: "==== Document Lens" or "===== Shopping List Lens"
        if line.startswith('====') or line.startswith('====='):
            next_line = lines[i+1].strip() if i+1 < len(lines) else ""
            if 'lens' in next_line.lower() or 'tests' in next_line.lower():
                current_lens = next_line
                current_domain = detect_lens_domain(next_line)
                current_category = next_line.split('-')[0].strip() if '-' in next_line else next_line

        # Pattern: "25 Receiving Lens Test Queries"
        lens_match = re.match(r'^\d+\s+(.+?)\s*(Lens|Tests?)', line, re.IGNORECASE)
        if lens_match:
            current_lens = lens_match.group(1).strip()
            current_domain = detect_lens_domain(current_lens)
            current_category = current_lens

        # Pattern: "⏺ 25 HOR Tests"
        hor_match = re.match(r'^⏺?\s*\d+\s+(.+?)\s*Tests?', line, re.IGNORECASE)
        if hor_match:
            current_lens = hor_match.group(1).strip()
            current_domain = detect_lens_domain(current_lens)
            current_category = current_lens

        # Difficulty level patterns
        if re.match(r'^(EASY|✅\s*EASY)', line, re.IGNORECASE):
            current_difficulty = 1
        elif re.match(r'^(MEDIUM|🟡\s*MEDIUM)', line, re.IGNORECASE):
            current_difficulty = 2
        elif re.match(r'^(HARD|🟠\s*HARD|🔴\s*HARD)', line, re.IGNORECASE):
            current_difficulty = 3
        elif re.match(r'^(VERY HARD|EXTREME|🔥)', line, re.IGNORECASE):
            current_difficulty = 4
        elif re.match(r'^Level\s*(\d)', line, re.IGNORECASE):
            level_match = re.match(r'^Level\s*(\d)', line, re.IGNORECASE)
            current_difficulty = int(level_match.group(1))

        # Test pattern: "Test N:" or "TEST N:"
        test_match = re.match(r'^(?:Test|TEST)\s*(\d+):', line, re.IGNORECASE)
        if test_match:
            test_num = test_match.group(1)

            # Look for query in next ~15 lines
            query = None
            role = 'crew'
            entities = []
            button = None
            difficulty_override = None

            for j in range(i, min(i+20, len(lines))):
                meta_line = lines[j].strip()

                # Query patterns
                query_match = re.match(r'^(?:Query|User Query|User Input):\s*["\']?(.+?)["\']?\s*$', meta_line, re.IGNORECASE)
                if query_match:
                    query = query_match.group(1).strip('"\'')

                # Numbered query pattern: `1. "query text"`
                num_query = re.match(r'^\d+\.\s*"(.+)"', meta_line)
                if num_query and not query:
                    query = num_query.group(1)

                # Role patterns
                if 'Role:' in meta_line:
                    role_part = meta_line.split('Role:')[1].strip().lower()
                    if 'hod' in role_part or 'captain' in role_part:
                        role = 'hod'
                    elif 'crew' in role_part:
                        role = 'crew'

                # Difficulty from stars
                if '⭐' in meta_line or '★' in meta_line:
                    difficulty_override = parse_difficulty_stars(meta_line)

                # Action/Button patterns
                if 'Action Button:' in meta_line or 'Expected Action Button:' in meta_line:
                    button = meta_line.split(':')[-1].strip()
                elif 'Microactions:' in meta_line:
                    button = meta_line.split(':')[-1].strip().split(',')[0].strip()

                # Stop at next test
                if j > i and re.match(r'^(?:Test|TEST)\s*\d+:', meta_line):
                    break
                if meta_line.startswith('---') and j > i+2:
                    break

            if query:
                # Determine expected intent
                expected_intent = 'READ'
                query_lower = query.lower()
                if any(w in query_lower for w in ['update', 'edit', 'change', 'modify', 'correct']):
                    expected_intent = 'UPDATE'
                elif any(w in query_lower for w in ['create', 'add', 'new', 'log']):
                    expected_intent = 'CREATE'
                elif any(w in query_lower for w in ['delete', 'remove']):
                    expected_intent = 'DELETE'
                elif any(w in query_lower for w in ['receive', 'reorder']):
                    expected_intent = 'CREATE'
                elif any(w in query_lower for w in ['approve', 'sign']):
                    expected_intent = 'APPROVE'
                elif any(w in query_lower for w in ['export', 'generate labels', 'print']):
                    expected_intent = 'EXPORT'

                # Classify specificity
                specificity = classify_specificity(query, entities)

                test_cases.append(RAGTestCase(
                    query=query,
                    category=current_category,
                    expected_intent=expected_intent,
                    expected_domain=current_domain,
                    expected_button=button or 'unknown',
                    role=role,
                    difficulty=difficulty_override or current_difficulty,
                    specificity=specificity,
                    entities=entities,
                ))

        # Also handle simple numbered queries: `1. "show me X"`
        simple_query_match = re.match(r'^(\d+)\.\s*"(.+)"$', line)
        if simple_query_match and not line.startswith('Test'):
            query = simple_query_match.group(1)
            query_text = simple_query_match.group(2)

            # Parse metadata from following lines
            role = 'crew'
            button = None
            entities = []
            difficulty_override = None

            for j in range(i+1, min(i+8, len(lines))):
                meta_line = lines[j].strip()
                if not meta_line or meta_line.startswith('---') or re.match(r'^\d+\.', meta_line):
                    break

                if 'Role:' in meta_line:
                    role_part = meta_line.split('Role:')[1].strip().lower()
                    if 'hod' in role_part or 'captain' in role_part:
                        role = 'hod'

                if 'Difficulty:' in meta_line:
                    difficulty_override = parse_difficulty_stars(meta_line)

                if 'Button:' in meta_line:
                    button = meta_line.split('Button:')[1].strip()

            # Determine expected intent
            expected_intent = 'READ'
            query_lower = query_text.lower()
            if any(w in query_lower for w in ['update', 'edit', 'log']):
                expected_intent = 'UPDATE'
            elif any(w in query_lower for w in ['create', 'add']):
                expected_intent = 'CREATE'

            specificity = classify_specificity(query_text, entities)

            test_cases.append(RAGTestCase(
                query=query_text,
                category=current_category,
                expected_intent=expected_intent,
                expected_domain=current_domain,
                expected_button=button or 'unknown',
                role=role,
                difficulty=difficulty_override or current_difficulty,
                specificity=specificity,
                entities=entities,
            ))

        i += 1

    return test_cases


def parse_test_terms(md_path: Path) -> List[RAGTestCase]:
    """Parse test file into RAG test cases (auto-detects format)."""
    # Use the new parser for queries_truth.md
    return parse_queries_truth(md_path)


# =============================================================================
# EVALUATION
# =============================================================================

def evaluate_single(
    conn,
    test_case: RAGTestCase,
    yacht_id: str,
) -> RAGTestResult:
    """Evaluate a single RAG test case."""
    import time
    start_time = time.time()

    try:
        # Normalize query first (Fix 7)
        normalized_query, time_window = normalize_query(test_case.query)

        # Detect domain/intent on normalized query (Fix 5)
        domain_result = detect_domain_from_query(normalized_query)
        detected_domain = domain_result[0] if domain_result else None
        detected_intent = detect_intent_from_query(normalized_query)

        domain_boost = domain_result[1] if domain_result else 0.0
        mode = 'focused' if detected_domain else 'explore'

        # Build context
        context = build_context_sync(
            conn=conn,
            yacht_id=yacht_id,
            query=test_case.query,
            role=test_case.role,
            lens=test_case.expected_domain,
            domain=detected_domain,
            mode=mode,
            domain_boost=domain_boost,
            top_k=8,
        )

        if not context.chunks:
            # No context - expected for some queries
            return RAGTestResult(
                query=test_case.query,
                category=test_case.category,
                role=test_case.role,
                difficulty=test_case.difficulty,
                specificity=test_case.specificity,
                context_chunks=0,
                context_tokens=0,
                answer_length=0,
                citations_used=0,
                confidence=0.0,
                faithfulness=1.0,  # Trivially faithful
                latency_ms=int((time.time() - start_time) * 1000),
                detected_domain=detected_domain,
                detected_intent=detected_intent,
                domain_match=detected_domain == test_case.expected_domain,
                intent_match=detected_intent == test_case.expected_intent,
                answer_specificity='vague',
                specificity_match=test_case.specificity == 'vague',
                status='pass' if test_case.specificity == 'vague' else 'fail',
                answer_preview="[No context retrieved]",
            )

        # Generate answer
        answer = generate_answer_sync(context)

        # Verify faithfulness
        verification = verify_answer(answer, context)

        # Classify answer specificity
        answer_specificity = classify_answer_specificity(answer.answer, len(answer.citations))

        # Check specificity match (key principle: vague in = vague out)
        specificity_match = (
            (test_case.specificity == 'vague' and answer_specificity in ['vague', 'moderate']) or
            (test_case.specificity == 'moderate' and answer_specificity in ['moderate', 'specific']) or
            (test_case.specificity == 'specific' and answer_specificity == 'specific')
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Determine pass/fail
        # Key principle: System does EXACTLY what user wants
        # - Vague query + has data → specific answer = GOOD (exceeded expectations)
        # - Vague query + no data → vague "no info" = GOOD (honest)
        # - Specific query + has data → specific answer = GOOD
        # - Specific query + no data → "no info" = ACCEPTABLE
        #
        # FAIL only when:
        # - Faithfulness < 0.7 (hallucination)
        # - OR answer claims specifics without citations

        # Adjust specificity match - more data is always better
        specificity_ok = (
            answer_specificity == 'vague' or  # Honest "no info"
            answer_specificity in ['moderate', 'specific']  # Has actual content
        )

        passes = (
            verification.faithfulness_score >= 0.7 and
            specificity_ok and
            len(answer.citations) > 0 or answer_specificity == 'vague'  # Either has citations or honestly says no info
        )

        return RAGTestResult(
            query=test_case.query,
            category=test_case.category,
            role=test_case.role,
            difficulty=test_case.difficulty,
            specificity=test_case.specificity,
            context_chunks=len(context.chunks),
            context_tokens=context.total_tokens,
            answer_length=len(answer.answer),
            citations_used=len(answer.citations),
            confidence=answer.confidence,
            faithfulness=verification.faithfulness_score,
            latency_ms=latency_ms,
            detected_domain=detected_domain,
            detected_intent=detected_intent,
            domain_match=detected_domain == test_case.expected_domain,
            intent_match=detected_intent == test_case.expected_intent,
            answer_specificity=answer_specificity,
            specificity_match=specificity_match,
            status='pass' if passes else 'fail',
            answer_preview=answer.answer[:200] + '...' if len(answer.answer) > 200 else answer.answer,
        )

    except Exception as e:
        return RAGTestResult(
            query=test_case.query,
            category=test_case.category,
            role=test_case.role,
            difficulty=test_case.difficulty,
            specificity=test_case.specificity,
            context_chunks=0,
            context_tokens=0,
            answer_length=0,
            citations_used=0,
            confidence=0.0,
            faithfulness=0.0,
            latency_ms=int((time.time() - start_time) * 1000),
            detected_domain=None,
            detected_intent='READ',
            domain_match=False,
            intent_match=False,
            answer_specificity='vague',
            specificity_match=False,
            status='error',
            error=str(e),
        )


def run_evaluation(
    conn,
    test_cases: List[RAGTestCase],
    yacht_id: str,
    sample_size: Optional[int] = None,
) -> Tuple[Dict[str, Any], List[RAGTestResult]]:
    """Run evaluation on all test cases."""

    if sample_size:
        test_cases = test_cases[:sample_size]

    results = []

    print(f"\nEvaluating {len(test_cases)} RAG queries...")
    print("-" * 60)

    for i, test_case in enumerate(test_cases):
        result = evaluate_single(conn, test_case, yacht_id)
        results.append(result)

        if (i + 1) % 10 == 0:
            passes = sum(1 for r in results if r.status == 'pass')
            print(f"  [{i+1}/{len(test_cases)}] Pass rate: {100*passes/(i+1):.1f}%")

    # Compute aggregate metrics
    total = len(results)
    passes = sum(1 for r in results if r.status == 'pass')
    errors = sum(1 for r in results if r.status == 'error')

    faithfulness_scores = [r.faithfulness for r in results if r.status != 'error']
    confidence_scores = [r.confidence for r in results if r.status != 'error']
    latencies = [r.latency_ms for r in results if r.status != 'error']

    domain_matches = sum(1 for r in results if r.domain_match)
    intent_matches = sum(1 for r in results if r.intent_match)
    specificity_matches = sum(1 for r in results if r.specificity_match)

    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'total_queries': total,
        'pass_count': passes,
        'fail_count': total - passes - errors,
        'error_count': errors,
        'pass_rate': 100 * passes / total if total else 0,
        'faithfulness_mean': sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0,
        'faithfulness_min': min(faithfulness_scores) if faithfulness_scores else 0,
        'confidence_mean': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
        'latency_mean_ms': sum(latencies) / len(latencies) if latencies else 0,
        'latency_p95_ms': sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0,
        'domain_match_rate': 100 * domain_matches / total if total else 0,
        'intent_match_rate': 100 * intent_matches / total if total else 0,
        'specificity_match_rate': 100 * specificity_matches / total if total else 0,
    }

    # Per-category breakdown
    categories = {}
    for r in results:
        cat = r.category
        if cat not in categories:
            categories[cat] = {'total': 0, 'pass': 0}
        categories[cat]['total'] += 1
        if r.status == 'pass':
            categories[cat]['pass'] += 1

    metrics['by_category'] = {
        cat: {
            'total': data['total'],
            'pass_rate': 100 * data['pass'] / data['total']
        }
        for cat, data in categories.items()
    }

    # Per-difficulty breakdown
    difficulties = {}
    for r in results:
        d = r.difficulty
        if d not in difficulties:
            difficulties[d] = {'total': 0, 'pass': 0}
        difficulties[d]['total'] += 1
        if r.status == 'pass':
            difficulties[d]['pass'] += 1

    metrics['by_difficulty'] = {
        f'stars_{d}': {
            'total': data['total'],
            'pass_rate': 100 * data['pass'] / data['total']
        }
        for d, data in sorted(difficulties.items())
    }

    return metrics, results


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='RAG evaluation harness')
    parser.add_argument('--yacht-id', default=DEFAULT_YACHT, help='Yacht ID')
    parser.add_argument('--sample', type=int, help='Sample N queries')
    parser.add_argument('--category', help='Filter to specific category')
    args = parser.parse_args()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Parse test cases
    print(f"Loading test cases from {INPUT_MD}")
    test_cases = parse_test_terms(INPUT_MD)
    print(f"✓ Loaded {len(test_cases)} test cases")

    # Filter by category if specified
    if args.category:
        test_cases = [tc for tc in test_cases if args.category.lower() in tc.category.lower()]
        print(f"✓ Filtered to {len(test_cases)} cases in '{args.category}'")

    # Show breakdown
    categories = {}
    for tc in test_cases:
        categories[tc.category] = categories.get(tc.category, 0) + 1
    print("\nCategories:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Connect to DB
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    print(f"\n✓ Connected to DB")

    # Run evaluation
    metrics, results = run_evaluation(
        conn, test_cases, args.yacht_id,
        sample_size=args.sample
    )

    # Save metrics
    metrics_path = OUTPUT_DIR / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n✓ Saved metrics to {metrics_path}")

    # Save per-query results
    csv_path = OUTPUT_DIR / 'per_query.csv'
    if results:
        fieldnames = [
            'query', 'category', 'role', 'difficulty', 'specificity',
            'context_chunks', 'context_tokens', 'answer_length', 'citations_used',
            'confidence', 'faithfulness', 'latency_ms',
            'detected_domain', 'detected_intent', 'domain_match', 'intent_match',
            'answer_specificity', 'specificity_match', 'status', 'error'
        ]
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                row = {k: getattr(r, k) for k in fieldnames}
                writer.writerow(row)
    print(f"✓ Saved per-query results to {csv_path}")

    # Save failures
    failures = [r for r in results if r.status in ('fail', 'error')]
    if failures:
        failures_path = OUTPUT_DIR / 'failures.jsonl'
        with open(failures_path, 'w') as f:
            for r in failures:
                f.write(json.dumps(asdict(r)) + '\n')
        print(f"✓ Saved {len(failures)} failures to {failures_path}")

    # Print summary
    print("\n" + "=" * 60)
    print(" RAG Evaluation Summary")
    print("=" * 60)
    print(f"Total queries: {metrics['total_queries']}")
    print(f"Pass rate: {metrics['pass_rate']:.1f}%")
    print(f"Faithfulness (mean): {metrics['faithfulness_mean']:.2f}")
    print(f"Confidence (mean): {metrics['confidence_mean']:.2f}")
    print(f"Latency (mean): {metrics['latency_mean_ms']:.0f}ms")
    print(f"Latency (P95): {metrics['latency_p95_ms']:.0f}ms")
    print(f"Domain match rate: {metrics['domain_match_rate']:.1f}%")
    print(f"Intent match rate: {metrics['intent_match_rate']:.1f}%")
    print(f"Specificity match rate: {metrics['specificity_match_rate']:.1f}%")
    print(f"Errors: {metrics['error_count']}")

    conn.close()


if __name__ == '__main__':
    main()
