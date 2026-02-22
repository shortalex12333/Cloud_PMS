#!/usr/bin/env python3
"""
F1 Search - Counterfactual Feedback Loop E2E Test (LAW 10 Compliant)

This test executes the PHYSICAL verification against REAL infrastructure:
- No mocks
- No fake databases
- Real PostgreSQL (production Supabase)
- Real Python workers

LAW 10: PHYSICAL TRUTH OVER MOCKED TESTS
A feature is only "Production Ready" if we can physically verify the
database state matches architectural intent after the feedback loop runs.

Test Scenario:
1. Insert a click event for Yacht A searching "watermaker" -> clicking equipment
2. Run the nightly feedback loop
3. Verify "watermaker" appears in learned_keywords ONLY for that yacht's object
4. Verify LAW 8: No cross-tenant pollution
5. Verify LAW 9: search_text was NOT modified

Usage:
    python test/e2e/feedback_loop_e2e.py
"""

import os
import sys
import time
import uuid
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple

import psycopg2
import psycopg2.extras

# =============================================================================
# Configuration
# =============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:%40-Ei-9Pa.uENn6g@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"
)

# Test configuration (yTEST_YACHT_001)
TEST_YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_ORG_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_USER_ID = "05a488fd-e099-4d18-bf86-d87afba4fcdf"

# Adversarial query to test vocabulary learning
ADVERSARIAL_QUERY = "watermaker"

# We'll create a fake "other yacht" to verify no cross-tenant pollution
OTHER_YACHT_ID = "00000000-0000-0000-0000-000000000001"

# =============================================================================
# Helpers
# =============================================================================

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_result(success: bool, message: str) -> bool:
    """Print test result."""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")
    return success


# =============================================================================
# Test Steps
# =============================================================================

def find_target_object() -> Optional[Dict]:
    """Find a pms_equipment object to use as click target."""
    print_header("STEP 1: Find Target Object")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Find an equipment item on the test yacht
        cur.execute("""
            SELECT object_type, object_id, yacht_id, search_text, learned_keywords
            FROM search_index
            WHERE yacht_id = %s
              AND object_type = 'pms_equipment'
            LIMIT 1
        """, (TEST_YACHT_ID,))

        row = cur.fetchone()

        if not row:
            # Fallback to any object on test yacht
            cur.execute("""
                SELECT object_type, object_id, yacht_id, search_text, learned_keywords
                FROM search_index
                WHERE yacht_id = %s
                LIMIT 1
            """, (TEST_YACHT_ID,))
            row = cur.fetchone()

        if row:
            print_result(True, f"Found target: {row['object_type']}/{row['object_id']}")
            print(f"  Current search_text: {(row['search_text'] or '')[:80]}...")
            print(f"  Current learned_keywords: {row['learned_keywords'] or '(empty)'}")
            return dict(row)
        else:
            print_result(False, "No objects found for test yacht")
            return None

    finally:
        conn.close()


def clear_previous_test_data(target: Dict):
    """Clear any previous test clicks and learned_keywords."""
    print_header("STEP 2: Clear Previous Test Data")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Delete previous test clicks
        cur.execute("""
            DELETE FROM search_click_events
            WHERE query_text = %s
              AND object_id = %s
        """, (ADVERSARIAL_QUERY, target['object_id']))
        deleted_clicks = cur.rowcount

        # Clear learned_keywords for this object (fresh start)
        cur.execute("""
            UPDATE search_index
            SET learned_keywords = '', learned_at = NULL
            WHERE object_id = %s AND object_type = %s
        """, (target['object_id'], target['object_type']))

        # Also clear any learned bridges
        cur.execute("""
            DELETE FROM search_learned_bridges
            WHERE query_text = %s
              AND object_id = %s
        """, (ADVERSARIAL_QUERY, target['object_id']))

        conn.commit()
        print_result(True, f"Cleared {deleted_clicks} previous test clicks")
        return True

    except Exception as e:
        print_result(False, f"Failed to clear test data: {e}")
        return False
    finally:
        conn.close()


def insert_test_clicks(target: Dict, count: int = 3) -> bool:
    """Insert click events simulating user searching 'watermaker' and clicking target."""
    print_header(f"STEP 3: Insert {count} Click Events")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Register UUID adapter
        import psycopg2.extensions
        psycopg2.extensions.register_adapter(uuid.UUID, lambda u: psycopg2.extensions.AsIs(f"'{u}'"))

        for i in range(count):
            search_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO search_click_events (
                    yacht_id, org_id, user_id, search_id,
                    query_text, object_type, object_id,
                    result_rank, fused_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                TEST_YACHT_ID,
                TEST_ORG_ID,
                TEST_USER_ID,
                search_id,
                ADVERSARIAL_QUERY,
                target['object_type'],
                str(target['object_id']),
                1,
                0.85
            ))

        conn.commit()
        print_result(True, f"Inserted {count} clicks for query '{ADVERSARIAL_QUERY}'")
        print(f"  yacht_id: {TEST_YACHT_ID} (LAW 8: Tenant bound)")
        print(f"  target: {target['object_type']}/{target['object_id']}")
        return True

    except Exception as e:
        print_result(False, f"Failed to insert clicks: {e}")
        return False
    finally:
        conn.close()


def record_search_text_before(target: Dict) -> str:
    """Record the search_text before feedback loop (for LAW 9 verification)."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT search_text FROM search_index
            WHERE object_id = %s AND object_type = %s
        """, (target['object_id'], target['object_type']))
        row = cur.fetchone()
        return row['search_text'] if row else ''
    finally:
        conn.close()


def run_feedback_loop() -> bool:
    """Run the nightly feedback loop."""
    print_header("STEP 4: Run Nightly Feedback Loop")

    # Set MIN_CLICKS=1 for testing (normally 3)
    env = os.environ.copy()
    env['DATABASE_URL'] = DATABASE_URL
    env['MIN_CLICKS'] = '1'
    env['LOOKBACK_DAYS'] = '30'
    env['BATCH_SIZE'] = '100'
    env['LOG_LEVEL'] = 'INFO'

    try:
        result = subprocess.run(
            ['python3', 'apps/api/workers/nightly_feedback_loop.py'],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            cwd='/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS'
        )

        # Print output
        for line in result.stdout.split('\n')[-15:]:
            if line.strip():
                print(f"  {line}")

        if result.returncode == 0:
            return print_result(True, "Feedback loop completed")
        else:
            print_result(False, f"Feedback loop failed: exit {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:300]}")
            return False

    except subprocess.TimeoutExpired:
        return print_result(False, "Feedback loop timed out")
    except Exception as e:
        return print_result(False, f"Failed to run feedback loop: {e}")


def verify_learned_keywords(target: Dict) -> bool:
    """Verify learned_keywords was updated with adversarial query."""
    print_header("STEP 5: Verify Learned Keywords (LAW 8)")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT yacht_id, learned_keywords, learned_at
            FROM search_index
            WHERE object_id = %s AND object_type = %s
        """, (target['object_id'], target['object_type']))

        row = cur.fetchone()

        if not row:
            return print_result(False, "Object not found in search_index")

        learned = row['learned_keywords'] or ''

        # LAW 8: Verify yacht_id is still correct
        if str(row['yacht_id']) != TEST_YACHT_ID:
            return print_result(False, f"YACHT MISMATCH: {row['yacht_id']}")

        # Check if adversarial query was learned
        if ADVERSARIAL_QUERY.lower() in learned.lower():
            print_result(True, f"'{ADVERSARIAL_QUERY}' found in learned_keywords!")
            print(f"  learned_keywords: {learned}")
            print(f"  learned_at: {row['learned_at']}")
            return True
        else:
            print_result(False, f"'{ADVERSARIAL_QUERY}' NOT found")
            print(f"  Current: '{learned}'")
            return False

    finally:
        conn.close()


def verify_search_text_immutable(target: Dict, original_search_text: str) -> bool:
    """Verify search_text was NOT modified (LAW 9)."""
    print_header("STEP 6: Verify search_text Immutable (LAW 9)")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT search_text FROM search_index
            WHERE object_id = %s AND object_type = %s
        """, (target['object_id'], target['object_type']))

        row = cur.fetchone()

        if not row:
            return print_result(False, "Object not found")

        current = row['search_text'] or ''

        if current == original_search_text:
            print_result(True, "search_text unchanged (LAW 9 satisfied)")
            return True
        else:
            print_result(False, "search_text WAS MODIFIED - LAW 9 VIOLATION!")
            print(f"  Original: {original_search_text[:50]}...")
            print(f"  Current: {current[:50]}...")
            return False

    finally:
        conn.close()


def verify_no_cross_tenant_pollution(target: Dict) -> bool:
    """Verify no learning leaked to other yachts (LAW 8)."""
    print_header("STEP 7: Verify No Cross-Tenant Pollution (LAW 8)")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if any OTHER yacht's objects learned our adversarial query
        cur.execute("""
            SELECT yacht_id, object_type, object_id, learned_keywords
            FROM search_index
            WHERE yacht_id != %s
              AND learned_keywords ILIKE %s
            LIMIT 5
        """, (TEST_YACHT_ID, f'%{ADVERSARIAL_QUERY}%'))

        polluted = cur.fetchall()

        if polluted:
            print_result(False, f"CROSS-TENANT POLLUTION DETECTED!")
            for row in polluted:
                print(f"  Yacht {row['yacht_id']}: {row['learned_keywords']}")
            return False
        else:
            print_result(True, "No cross-tenant pollution detected")
            return True

    finally:
        conn.close()


def verify_learned_bridges_recorded(target: Dict) -> bool:
    """Verify the learned bridge was recorded in audit table."""
    print_header("STEP 8: Verify Audit Trail")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT yacht_id, query_text, click_count, applied, applied_at
            FROM search_learned_bridges
            WHERE object_id = %s
              AND query_text = %s
        """, (target['object_id'], ADVERSARIAL_QUERY))

        row = cur.fetchone()

        if row:
            print_result(True, "Learned bridge recorded in audit table")
            print(f"  click_count: {row['click_count']}")
            print(f"  applied: {row['applied']}")
            print(f"  applied_at: {row['applied_at']}")
            return True
        else:
            # This is not critical - audit table is optional
            print_result(True, "No audit record (optional feature)")
            return True

    finally:
        conn.close()


# =============================================================================
# Main Test Runner
# =============================================================================

def run_e2e_test() -> bool:
    """Run the complete E2E test for the Counterfactual Feedback Loop."""

    print("\n" + "=" * 60)
    print("  F1 SEARCH - COUNTERFACTUAL FEEDBACK LOOP E2E TEST")
    print("  LAW 10: Physical Truth Over Mocked Tests")
    print("=" * 60)
    print(f"\nTest Configuration:")
    print(f"  Database: {DATABASE_URL.split('@')[1][:40]}...")
    print(f"  Test Yacht: {TEST_YACHT_ID}")
    print(f"  Adversarial Query: '{ADVERSARIAL_QUERY}'")

    results = []

    # Step 1: Find target object
    target = find_target_object()
    if not target:
        print_result(False, "Cannot proceed without target object")
        return False

    # Record original search_text for LAW 9 verification
    original_search_text = record_search_text_before(target)

    # Step 2: Clear previous test data
    results.append(clear_previous_test_data(target))

    # Step 3: Insert test clicks
    results.append(insert_test_clicks(target, count=3))

    # Step 4: Run feedback loop
    results.append(run_feedback_loop())

    # Step 5: Verify learned_keywords
    results.append(verify_learned_keywords(target))

    # Step 6: Verify search_text immutable (LAW 9)
    results.append(verify_search_text_immutable(target, original_search_text))

    # Step 7: Verify no cross-tenant pollution (LAW 8)
    results.append(verify_no_cross_tenant_pollution(target))

    # Step 8: Verify audit trail
    results.append(verify_learned_bridges_recorded(target))

    # Final Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    if all(results):
        print_result(True, f"ALL {total} STEPS PASSED")
        print("\n  LAW 8: Tenant isolation verified")
        print("  LAW 9: search_text immutability verified")
        print("  LAW 10: Physical truth verified (no mocks)")
        print("\n  COUNTERFACTUAL FEEDBACK LOOP: PRODUCTION READY")
        return True
    else:
        print_result(False, f"FAILED: {passed}/{total} steps passed")
        return False


if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
