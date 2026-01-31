#!/usr/bin/env python3
"""
Document Comments Stress Testing - Natural Language Variance

Tests document comment actions with:
1. Explicit microaction terms
2. Paraphrases
3. Misspellings
4. Timeframes
5. Chaotic natural language
6. Role-based (crew, chief_engineer, captain)
7. Department RLS (engineering, deck, interior)

Real data testing against production database.
"""

import os
import sys
import time
import json
import statistics
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# =============================================================================
# CONFIGURATION
# =============================================================================

API_BASE = os.getenv('API_URL', 'https://pipeline-core.int.celeste7.ai')
# Auth happens via MASTER Supabase
MASTER_URL = os.getenv('MASTER_SUPABASE_URL', 'https://qvzmkaamzaqxpzbewjxe.supabase.co')
MASTER_ANON_KEY = os.getenv('MASTER_SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw')
YACHT_ID = os.getenv('TEST_YACHT_ID', '85fe1119-b04c-41ac-80f1-829d23322598')

# Test users by role - real test user
TEST_USERS = {
    "captain": {
        "email": os.getenv('TEST_USER_EMAIL', 'x@alex-short.com'),
        "password": os.getenv('TEST_USER_PASSWORD', 'Password2!'),
        "role": "captain",
        "department": "bridge"
    },
}

# JWT token cache
_jwt_cache: Dict[str, str] = {}


# =============================================================================
# QUERY VARIANCE MATRIX
# =============================================================================

class QueryType(Enum):
    EXPLICIT = "explicit"
    PARAPHRASE = "paraphrase"
    MISSPELLED = "misspelled"
    TIMEFRAME = "timeframe"
    SPECIFIC = "specific"
    CHAOTIC = "chaotic"
    AMBIGUOUS = "ambiguous"


@dataclass
class TestQuery:
    query: str
    query_type: QueryType
    expected_action: str
    expected_match: bool
    difficulty: str  # easy, medium, hard
    description: str


# Document Comment Test Queries
COMMENT_QUERIES = [
    # ==========================================================================
    # EXPLICIT - Direct microaction terms
    # ==========================================================================
    TestQuery(
        query="add document comment",
        query_type=QueryType.EXPLICIT,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="easy",
        description="Exact microaction name"
    ),
    TestQuery(
        query="list document comments",
        query_type=QueryType.EXPLICIT,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="easy",
        description="Exact microaction name"
    ),
    TestQuery(
        query="delete document comment",
        query_type=QueryType.EXPLICIT,
        expected_action="delete_document_comment",
        expected_match=True,
        difficulty="easy",
        description="Exact microaction name"
    ),
    TestQuery(
        query="update document comment",
        query_type=QueryType.EXPLICIT,
        expected_action="update_document_comment",
        expected_match=True,
        difficulty="easy",
        description="Exact microaction name"
    ),

    # ==========================================================================
    # PARAPHRASE - Natural language equivalents
    # ==========================================================================
    TestQuery(
        query="leave a note on this document",
        query_type=QueryType.PARAPHRASE,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Natural phrasing for add comment"
    ),
    TestQuery(
        query="add a remark to the file",
        query_type=QueryType.PARAPHRASE,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Synonym usage"
    ),
    TestQuery(
        query="comment on the manual",
        query_type=QueryType.PARAPHRASE,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Implicit add"
    ),
    TestQuery(
        query="show me all the notes",
        query_type=QueryType.PARAPHRASE,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Notes = comments"
    ),
    TestQuery(
        query="what did people say about this doc",
        query_type=QueryType.PARAPHRASE,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Conversational query"
    ),
    TestQuery(
        query="remove my comment",
        query_type=QueryType.PARAPHRASE,
        expected_action="delete_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Remove = delete"
    ),
    TestQuery(
        query="edit what I wrote",
        query_type=QueryType.PARAPHRASE,
        expected_action="update_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Edit = update"
    ),
    TestQuery(
        query="change my note",
        query_type=QueryType.PARAPHRASE,
        expected_action="update_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Change = update"
    ),

    # ==========================================================================
    # MISSPELLED - Typos and errors
    # ==========================================================================
    TestQuery(
        query="add documnet commnent",
        query_type=QueryType.MISSPELLED,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Common typos"
    ),
    TestQuery(
        query="coment on the file",
        query_type=QueryType.MISSPELLED,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="medium",
        description="Missing letter"
    ),
    TestQuery(
        query="delet my comemnt",
        query_type=QueryType.MISSPELLED,
        expected_action="delete_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Multiple typos"
    ),
    TestQuery(
        query="updte teh commnet",
        query_type=QueryType.MISSPELLED,
        expected_action="update_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Severe typos"
    ),
    TestQuery(
        query="lst all coments",
        query_type=QueryType.MISSPELLED,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Truncated words"
    ),

    # ==========================================================================
    # TIMEFRAME - Temporal queries
    # ==========================================================================
    TestQuery(
        query="comments from last week",
        query_type=QueryType.TIMEFRAME,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Relative time"
    ),
    TestQuery(
        query="notes added yesterday",
        query_type=QueryType.TIMEFRAME,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Specific day"
    ),
    TestQuery(
        query="what was said in january",
        query_type=QueryType.TIMEFRAME,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Month reference"
    ),
    TestQuery(
        query="show recent comments",
        query_type=QueryType.TIMEFRAME,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="easy",
        description="Recency"
    ),
    TestQuery(
        query="comments from 2nd of this month",
        query_type=QueryType.TIMEFRAME,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="hard",
        description="Specific date"
    ),

    # ==========================================================================
    # SPECIFIC - Named entities and specific references
    # ==========================================================================
    TestQuery(
        query="what did John say about the engine manual",
        query_type=QueryType.SPECIFIC,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="hard",
        description="Person + document reference"
    ),
    TestQuery(
        query="comments on the oil change procedure",
        query_type=QueryType.SPECIFIC,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="medium",
        description="Document name reference"
    ),
    TestQuery(
        query="notes from the chief engineer on safety docs",
        query_type=QueryType.SPECIFIC,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="hard",
        description="Role + document type"
    ),
    TestQuery(
        query="add note to ISM manual section 4",
        query_type=QueryType.SPECIFIC,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Specific document section"
    ),

    # ==========================================================================
    # CHAOTIC - Real user input patterns
    # ==========================================================================
    TestQuery(
        query="that thing someone wrote on the doc about the engine idk when",
        query_type=QueryType.CHAOTIC,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="hard",
        description="Vague with filler words"
    ),
    TestQuery(
        query="uhh show me the notes or comments or whatever on that file",
        query_type=QueryType.CHAOTIC,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="hard",
        description="Uncertainty and alternatives"
    ),
    TestQuery(
        query="i need to write something on the document thing",
        query_type=QueryType.CHAOTIC,
        expected_action="add_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Vague intent"
    ),
    TestQuery(
        query="wait no delete that comment i just made",
        query_type=QueryType.CHAOTIC,
        expected_action="delete_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Conversational delete"
    ),
    TestQuery(
        query="can you like change what i wrote on the oil thing",
        query_type=QueryType.CHAOTIC,
        expected_action="update_document_comment",
        expected_match=True,
        difficulty="hard",
        description="Casual edit request"
    ),

    # ==========================================================================
    # AMBIGUOUS - Vague input should return vague/multiple results
    # ==========================================================================
    TestQuery(
        query="comments",
        query_type=QueryType.AMBIGUOUS,
        expected_action="list_document_comments",
        expected_match=True,
        difficulty="easy",
        description="Single word - default to list"
    ),
    TestQuery(
        query="document stuff",
        query_type=QueryType.AMBIGUOUS,
        expected_action=None,  # Multiple possible matches
        expected_match=False,
        difficulty="medium",
        description="Too vague - should return 'here similar'"
    ),
    TestQuery(
        query="the thing",
        query_type=QueryType.AMBIGUOUS,
        expected_action=None,
        expected_match=False,
        difficulty="hard",
        description="Completely vague"
    ),
]


# =============================================================================
# JWT GENERATION VIA SUPABASE AUTH
# =============================================================================

def login_user(email: str, password: str) -> str:
    """Login via Supabase auth and return JWT token."""
    global _jwt_cache

    # Check cache first
    if email in _jwt_cache:
        return _jwt_cache[email]

    # Login via MASTER Supabase (auth is centralized)
    auth_url = f"{MASTER_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": MASTER_ANON_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "password": password
    }

    try:
        r = requests.post(auth_url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            if token:
                _jwt_cache[email] = token
                return token
            raise ValueError(f"No access_token in response: {data}")
        else:
            raise ValueError(f"Login failed: {r.status_code} - {r.text}")
    except Exception as e:
        raise ValueError(f"Login error: {e}")


def get_jwt_for_role(role: str) -> str:
    """Get JWT token for a specific role."""
    user = TEST_USERS.get(role)
    if not user:
        raise ValueError(f"No test user configured for role: {role}")
    return login_user(user["email"], user["password"])


# =============================================================================
# API CALLS
# =============================================================================

def search_actions(jwt_token: str, query: str, domain: str = "documents") -> Dict[str, Any]:
    """
    Search for actions matching query.

    Returns: {
        status_code,
        latency_ms,
        actions: [...],
        matched_action,
        error
    }
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    start = time.time()
    try:
        # Try action search endpoint
        r = requests.get(
            f"{API_BASE}/v1/actions/list",
            headers=headers,
            params={"q": query, "domain": domain},
            timeout=30
        )
        latency_ms = int((time.time() - start) * 1000)

        if r.status_code == 200:
            data = r.json()
            actions = data.get("actions", [])
            matched = actions[0]["action_id"] if actions else None
            return {
                "status_code": r.status_code,
                "latency_ms": latency_ms,
                "actions": actions,
                "matched_action": matched,
                "total_count": data.get("total_count", 0),
                "error": None
            }
        else:
            return {
                "status_code": r.status_code,
                "latency_ms": latency_ms,
                "actions": [],
                "matched_action": None,
                "total_count": 0,
                "error": r.text
            }

    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "status_code": 0,
            "latency_ms": latency_ms,
            "actions": [],
            "matched_action": None,
            "total_count": 0,
            "error": str(e)
        }


def execute_action(jwt_token: str, action_id: str, payload: Dict) -> Dict[str, Any]:
    """
    Execute an action.

    Returns: {
        status_code,
        latency_ms,
        result,
        error
    }
    """
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }

    request_body = {
        "action": action_id,
        "context": {"yacht_id": YACHT_ID},
        "payload": {**payload, "yacht_id": YACHT_ID}
    }

    start = time.time()
    try:
        r = requests.post(
            f"{API_BASE}/v1/actions/execute",
            headers=headers,
            json=request_body,
            timeout=30
        )
        latency_ms = int((time.time() - start) * 1000)

        return {
            "status_code": r.status_code,
            "latency_ms": latency_ms,
            "result": r.json() if r.status_code == 200 else None,
            "error": r.text if r.status_code >= 400 else None
        }

    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {
            "status_code": 0,
            "latency_ms": latency_ms,
            "result": None,
            "error": str(e)
        }


# =============================================================================
# TEST RUNNER
# =============================================================================

@dataclass
class TestResult:
    query: TestQuery
    role: str
    department: str
    search_result: Dict[str, Any]
    matched: bool
    expected_matched: bool
    correct: bool
    latency_ms: int


def run_query_variance_tests(role: str) -> List[TestResult]:
    """Run all query variance tests for a specific role."""
    user = TEST_USERS.get(role, TEST_USERS["captain"])  # Default to captain
    jwt_token = get_jwt_for_role(role) if role in TEST_USERS else get_jwt_for_role("captain")

    results = []

    for test_query in COMMENT_QUERIES:
        search_result = search_actions(jwt_token, test_query.query)

        matched_action = search_result.get("matched_action")
        matched = matched_action == test_query.expected_action if test_query.expected_action else False

        # For ambiguous queries, success = no single strong match
        if test_query.query_type == QueryType.AMBIGUOUS and not test_query.expected_match:
            correct = matched_action is None or search_result.get("total_count", 0) > 1
        else:
            correct = matched == test_query.expected_match

        results.append(TestResult(
            query=test_query,
            role=role,
            department=user["department"],
            search_result=search_result,
            matched=matched,
            expected_matched=test_query.expected_match,
            correct=correct,
            latency_ms=search_result.get("latency_ms", 0)
        ))

    return results


def run_rls_tests() -> List[Dict[str, Any]]:
    """Test department-based RLS on comments."""
    results = []

    # TODO: Create test comments from different departments
    # Then verify each role can only see appropriate comments

    # This requires:
    # 1. Existing test document
    # 2. Comments from engineering, deck, interior departments
    # 3. Verify filtering works

    return results


def analyze_results(results: List[TestResult]) -> Dict[str, Any]:
    """Analyze test results."""
    total = len(results)
    correct = sum(1 for r in results if r.correct)

    by_type = {}
    for qt in QueryType:
        type_results = [r for r in results if r.query.query_type == qt]
        if type_results:
            by_type[qt.value] = {
                "total": len(type_results),
                "correct": sum(1 for r in type_results if r.correct),
                "accuracy": round(sum(1 for r in type_results if r.correct) / len(type_results) * 100, 1)
            }

    by_difficulty = {}
    for diff in ["easy", "medium", "hard"]:
        diff_results = [r for r in results if r.query.difficulty == diff]
        if diff_results:
            by_difficulty[diff] = {
                "total": len(diff_results),
                "correct": sum(1 for r in diff_results if r.correct),
                "accuracy": round(sum(1 for r in diff_results if r.correct) / len(diff_results) * 100, 1)
            }

    latencies = [r.latency_ms for r in results if r.latency_ms > 0]

    return {
        "total_tests": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "by_type": by_type,
        "by_difficulty": by_difficulty,
        "latencies": {
            "p50": statistics.median(latencies) if latencies else 0,
            "p95": latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else 0,
            "max": max(latencies) if latencies else 0
        }
    }


def print_results(results: List[TestResult], analysis: Dict[str, Any], role: str):
    """Print test results."""
    print(f"\n{'='*80}")
    print(f"DOCUMENT COMMENTS STRESS TEST - Role: {role.upper()}")
    print(f"{'='*80}")

    print(f"\nOverall Accuracy: {analysis['accuracy']}% ({analysis['correct']}/{analysis['total_tests']})")

    print(f"\nBy Query Type:")
    for qt, stats in analysis["by_type"].items():
        status = "✅" if stats["accuracy"] >= 80 else "⚠️" if stats["accuracy"] >= 50 else "❌"
        print(f"  {status} {qt}: {stats['accuracy']}% ({stats['correct']}/{stats['total']})")

    print(f"\nBy Difficulty:")
    for diff, stats in analysis["by_difficulty"].items():
        status = "✅" if stats["accuracy"] >= 80 else "⚠️" if stats["accuracy"] >= 50 else "❌"
        print(f"  {status} {diff}: {stats['accuracy']}% ({stats['correct']}/{stats['total']})")

    print(f"\nLatencies:")
    print(f"  P50: {analysis['latencies']['p50']}ms")
    print(f"  P95: {analysis['latencies']['p95']}ms")
    print(f"  Max: {analysis['latencies']['max']}ms")

    # Print failures
    failures = [r for r in results if not r.correct]
    if failures:
        print(f"\n❌ FAILURES ({len(failures)}):")
        for f in failures[:10]:  # Show first 10
            print(f"  - '{f.query.query}' ({f.query.query_type.value})")
            print(f"    Expected: {f.query.expected_action}, Got: {f.search_result.get('matched_action')}")


def main():
    print("="*80)
    print("DOCUMENT COMMENTS - NATURAL LANGUAGE STRESS TEST")
    print("="*80)
    print(f"\nAPI: {API_BASE}")
    print(f"Yacht: {YACHT_ID}")
    print(f"Test Queries: {len(COMMENT_QUERIES)}")
    print(f"Roles: {list(TEST_USERS.keys())}")

    all_results = []
    all_analyses = []

    for role in list(TEST_USERS.keys()):
        print(f"\n{'─'*40}")
        print(f"Testing role: {role}")
        print(f"{'─'*40}")

        try:
            results = run_query_variance_tests(role)
            analysis = analyze_results(results)
            print_results(results, analysis, role)

            all_results.extend(results)
            all_analyses.append({"role": role, "analysis": analysis})

        except Exception as e:
            print(f"❌ Error testing {role}: {e}")

    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")

    total_correct = sum(1 for r in all_results if r.correct)
    total_tests = len(all_results)
    overall_accuracy = round(total_correct / total_tests * 100, 1) if total_tests > 0 else 0

    print(f"\nTotal Tests: {total_tests}")
    print(f"Correct: {total_correct}")
    print(f"Overall Accuracy: {overall_accuracy}%")

    if overall_accuracy >= 80:
        print("\n✅ PASS - Natural language understanding meets threshold")
        verdict = "PASS"
    elif overall_accuracy >= 50:
        print("\n⚠️ PARTIAL - Some improvement needed")
        verdict = "PARTIAL"
    else:
        print("\n❌ FAIL - Significant improvement needed")
        verdict = "FAIL"

    # Save results
    output_file = f"document_comments_stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "verdict": verdict,
            "overall_accuracy": overall_accuracy,
            "total_tests": total_tests,
            "by_role": all_analyses,
            "failures": [
                {
                    "query": r.query.query,
                    "type": r.query.query_type.value,
                    "expected": r.query.expected_action,
                    "got": r.search_result.get("matched_action"),
                    "role": r.role
                }
                for r in all_results if not r.correct
            ]
        }, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
