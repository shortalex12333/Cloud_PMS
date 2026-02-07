#!/usr/bin/env python3
"""
Email Linking Readiness Verification

Checks DB state for L2.5 hybrid linking:
1. TSV index exists
2. Embedding coverage for targets (work_order, equipment, part)
3. search_role_bias populated
4. embedding_jobs queue depth
5. match_link_targets_v2 RPC test

Usage:
    DATABASE_URL=postgresql://... python verify_email_linking_readiness.py [--yacht-id UUID]
"""

import os
import sys
import argparse
from datetime import datetime

# Add api to path
sys.path.insert(0, '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api')

import psycopg2
import psycopg2.extras

# Read DATABASE_URL from env or use Supavisor port
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    # Default to Supabase project with Supavisor
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://vzsohavtuotocgrfkfyd.supabase.co')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

    if SUPABASE_SERVICE_KEY:
        # Extract project ref from URL
        project_ref = SUPABASE_URL.replace('https://', '').replace('.supabase.co', '')
        DATABASE_URL = f"postgresql://postgres.{project_ref}:{SUPABASE_SERVICE_KEY}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    else:
        print("ERROR: Set DATABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)


def check_tsv_index(cur):
    """Check if TSV index exists on search_index."""
    print("\n" + "="*60)
    print("1. TSV INDEX CHECK")
    print("="*60)

    cur.execute("""
        SELECT to_regclass('public.idx_search_index_tsv') AS tsv_idx,
               to_regclass('public.ix_search_tsv_p') AS tsv_idx_p
    """)
    row = cur.fetchone()

    if row['tsv_idx'] or row['tsv_idx_p']:
        print("✓ TSV GIN index exists:", row['tsv_idx'] or row['tsv_idx_p'])
        return True
    else:
        print("✗ TSV GIN index NOT FOUND")
        print("  Run: CREATE INDEX idx_search_index_tsv ON search_index USING GIN (tsv);")
        return False


def check_embedding_coverage(cur, yacht_id=None):
    """Check embedding coverage for L2.5 target types."""
    print("\n" + "="*60)
    print("2. EMBEDDING COVERAGE")
    print("="*60)

    where_clause = "WHERE object_type IN ('work_order', 'equipment', 'part')"
    params = []

    if yacht_id:
        where_clause += " AND yacht_id = %s"
        params.append(yacht_id)

    # Check for both embedding columns (legacy and 1536)
    cur.execute(f"""
        SELECT
            object_type,
            COUNT(*) AS total,
            SUM((embedding IS NOT NULL)::int) AS with_embedding,
            SUM((embedding_1536 IS NOT NULL)::int) AS with_embedding_1536,
            ROUND(100.0 * SUM((embedding_1536 IS NOT NULL)::int) / NULLIF(COUNT(*), 0), 1) AS coverage_pct
        FROM public.search_index
        {where_clause}
        GROUP BY object_type
        ORDER BY object_type
    """, params)

    rows = cur.fetchall()

    if not rows:
        print("✗ No search_index rows found for target types")
        return False

    all_good = True
    for row in rows:
        status = "✓" if row['coverage_pct'] and row['coverage_pct'] >= 95 else "✗"
        print(f"  {status} {row['object_type']}: {row['with_embedding_1536'] or 0}/{row['total']} embedded ({row['coverage_pct'] or 0}%)")
        if row['coverage_pct'] is None or row['coverage_pct'] < 95:
            all_good = False

    if not all_good:
        print("\n  ACTION: Run embedding_worker_1536.py to backfill embeddings")

    return all_good


def check_embedding_jobs_queue(cur, yacht_id=None):
    """Check embedding_jobs queue depth."""
    print("\n" + "="*60)
    print("3. EMBEDDING JOBS QUEUE")
    print("="*60)

    where_clause = ""
    params = []

    if yacht_id:
        where_clause = "WHERE yacht_id = %s"
        params.append(yacht_id)

    cur.execute(f"""
        SELECT
            status,
            COUNT(*) AS count,
            MIN(queued_at) AS oldest,
            MAX(queued_at) AS newest
        FROM public.embedding_jobs
        {where_clause}
        GROUP BY status
        ORDER BY status
    """, params)

    rows = cur.fetchall()

    if not rows:
        print("  No embedding_jobs found (table may be empty)")
        return True

    queued_count = 0
    for row in rows:
        print(f"  {row['status']}: {row['count']} jobs")
        if row['oldest']:
            print(f"      oldest: {row['oldest']}")
        if row['status'] == 'queued':
            queued_count = row['count']

    if queued_count > 0:
        print(f"\n  WARNING: {queued_count} jobs queued - run embedding_worker_1536.py")
        return False

    return True


def check_role_bias(cur):
    """Check search_role_bias table."""
    print("\n" + "="*60)
    print("4. ROLE BIAS TABLE")
    print("="*60)

    cur.execute("""
        SELECT
            role,
            COUNT(*) AS rules,
            COUNT(object_type) AS with_object_type,
            COUNT(bias_weight) AS with_bias_weight
        FROM public.search_role_bias
        GROUP BY role
        ORDER BY role
    """)

    rows = cur.fetchall()

    if not rows:
        print("✗ search_role_bias is empty")
        print("  Run migration 20260206000008 to seed role biases")
        return False

    for row in rows:
        print(f"  {row['role']}: {row['rules']} rules ({row['with_object_type']} with object_type)")

    return True


def check_text_search(cur, yacht_id=None):
    """Test text search with websearch_to_tsquery."""
    print("\n" + "="*60)
    print("5. TEXT SEARCH TEST")
    print("="*60)

    test_query = "generator maintenance"

    where_clause = "WHERE tsv @@ websearch_to_tsquery('english', %s)"
    params = [test_query]

    if yacht_id:
        where_clause += " AND yacht_id = %s"
        params.append(yacht_id)

    cur.execute(f"""
        SELECT
            object_type,
            object_id,
            ts_rank_cd(tsv, websearch_to_tsquery('english', %s)) AS rank,
            LEFT(search_text, 80) AS snippet
        FROM public.search_index
        {where_clause}
        ORDER BY rank DESC
        LIMIT 5
    """, [test_query] + params)

    rows = cur.fetchall()

    if not rows:
        print(f"  No results for '{test_query}'")
        return False

    print(f"  Query: '{test_query}'")
    print(f"  Results: {len(rows)}")
    for i, row in enumerate(rows, 1):
        print(f"    {i}. [{row['object_type']}] rank={row['rank']:.4f}")
        print(f"       {row['snippet']}...")

    return True


def check_match_link_targets_v2(cur, yacht_id=None):
    """Test match_link_targets_v2 RPC."""
    print("\n" + "="*60)
    print("6. MATCH_LINK_TARGETS_V2 RPC TEST")
    print("="*60)

    if not yacht_id:
        # Get a sample yacht_id
        cur.execute("SELECT DISTINCT yacht_id FROM search_index LIMIT 1")
        row = cur.fetchone()
        if row:
            yacht_id = row['yacht_id']
        else:
            print("  No yacht_id found in search_index")
            return False

    test_query = "engine oil leak repair"

    # Generate a dummy embedding (zeros) - real test would use OpenAI
    dummy_embedding = "[" + ",".join(["0.0"] * 1536) + "]"

    try:
        cur.execute("""
            SELECT * FROM public.match_link_targets_v2(
                %s::uuid,
                %s,
                %s::vector(1536),
                ARRAY['work_order', 'equipment', 'part'],
                'chief_engineer',
                365,
                50,
                50,
                0.50
            )
            LIMIT 10
        """, (str(yacht_id), test_query, dummy_embedding))

        rows = cur.fetchall()

        print(f"  Query: '{test_query}'")
        print(f"  yacht_id: {yacht_id}")
        print(f"  Results: {len(rows)}")

        if rows:
            for i, row in enumerate(rows[:5], 1):
                print(f"    {i}. [{row['object_type']}] S_text={row['s_text']:.3f} S_vector={row['s_vector']:.3f}")
                print(f"       {row['label'][:60]}...")
            return True
        else:
            print("  No results - check embedding coverage and text indexing")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        print("  RPC may not be deployed - run migration 20260206000006")
        return False


def main():
    parser = argparse.ArgumentParser(description='Verify email linking readiness')
    parser.add_argument('--yacht-id', help='Filter by yacht_id')
    args = parser.parse_args()

    yacht_id = args.yacht_id

    print("="*60)
    print("EMAIL LINKING READINESS VERIFICATION")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("="*60)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return 1

    results = {}

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        results['tsv_index'] = check_tsv_index(cur)
        results['embedding_coverage'] = check_embedding_coverage(cur, yacht_id)
        results['embedding_queue'] = check_embedding_jobs_queue(cur, yacht_id)
        results['role_bias'] = check_role_bias(cur)
        results['text_search'] = check_text_search(cur, yacht_id)
        results['rpc_v2'] = check_match_link_targets_v2(cur, yacht_id)

    conn.close()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    all_pass = True
    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {check}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n✓ All checks passed - L2.5 hybrid linking is ready!")
        return 0
    else:
        print("\n✗ Some checks failed - see above for remediation steps")
        return 1


if __name__ == "__main__":
    sys.exit(main())
