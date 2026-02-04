#!/usr/bin/env python3
"""
Embedding Coverage Monitor

Reports:
- % with_vec (embedding coverage)
- Time-to-embed P50/P95
- Queue lag (pending jobs)
- Retry rate

Usage:
    DATABASE_URL=postgresql://... python embedding_coverage.py
"""

import os
import sys

import psycopg2

DB_DSN = os.getenv("DATABASE_URL")

def get_coverage_stats(cur):
    """Get embedding coverage statistics."""
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_vec,
            ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*), 0), 2) AS pct_coverage
        FROM search_index
    """)
    return cur.fetchone()

def get_coverage_by_domain(cur):
    """Get coverage by object_type."""
    cur.execute("""
        SELECT
            object_type,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_vec,
            ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*), 0), 2) AS pct
        FROM search_index
        GROUP BY object_type
        ORDER BY total DESC
    """)
    return cur.fetchall()

def get_queue_stats(cur):
    """Get embedding job queue statistics."""
    cur.execute("""
        SELECT
            status,
            COUNT(*) AS cnt,
            MIN(created_at) AS oldest
        FROM embedding_jobs
        GROUP BY status
        ORDER BY status
    """)
    return cur.fetchall()

def get_time_to_embed(cur):
    """Get time-to-embed P50/P95 for recent jobs."""
    cur.execute("""
        SELECT
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (updated_at - created_at))) AS p50_sec,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (updated_at - created_at))) AS p95_sec
        FROM embedding_jobs
        WHERE status = 'done'
          AND updated_at > NOW() - INTERVAL '24 hours'
    """)
    return cur.fetchone()

def get_retry_rate(cur):
    """Get retry rate (jobs with attempt > 1)."""
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE attempt > 1) AS retried,
            COUNT(*) AS total,
            ROUND(100.0 * COUNT(*) FILTER (WHERE attempt > 1) / NULLIF(COUNT(*), 0), 2) AS retry_pct
        FROM embedding_jobs
        WHERE status IN ('done', 'failed')
          AND updated_at > NOW() - INTERVAL '24 hours'
    """)
    return cur.fetchone()

def enqueue_missing(cur, limit=100):
    """Enqueue rows missing embeddings."""
    cur.execute("""
        INSERT INTO embedding_jobs (object_type, object_id, status)
        SELECT object_type, object_id, 'queued'
        FROM search_index
        WHERE embedding IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM embedding_jobs ej
              WHERE ej.object_type = search_index.object_type
                AND ej.object_id = search_index.object_id
                AND ej.status IN ('queued', 'working')
          )
        LIMIT %s
        ON CONFLICT (object_type, object_id) DO NOTHING
        RETURNING object_id
    """, (limit,))
    return cur.rowcount

def main():
    if not DB_DSN:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    with psycopg2.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            print("=" * 60)
            print("EMBEDDING COVERAGE REPORT")
            print("=" * 60)

            # Overall coverage
            total, with_vec, pct = get_coverage_stats(cur)
            print(f"\n📊 Overall Coverage: {with_vec}/{total} ({pct}%)")

            # Coverage by domain
            print("\n📁 Coverage by Domain:")
            for row in get_coverage_by_domain(cur):
                obj_type, total, with_vec, pct = row
                status = "✅" if pct and pct >= 95 else "⚠️"
                print(f"   {status} {obj_type}: {with_vec}/{total} ({pct}%)")

            # Queue stats
            print("\n📋 Queue Status:")
            for row in get_queue_stats(cur):
                status, cnt, oldest = row
                print(f"   {status}: {cnt} (oldest: {oldest})")

            # Time to embed
            p50, p95 = get_time_to_embed(cur)
            print(f"\n⏱️  Time-to-Embed (24h):")
            print(f"   P50: {p50:.2f}s" if p50 else "   P50: N/A")
            print(f"   P95: {p95:.2f}s" if p95 else "   P95: N/A")

            # Retry rate
            retried, total, retry_pct = get_retry_rate(cur)
            print(f"\n🔄 Retry Rate (24h): {retried}/{total} ({retry_pct}%)")

            # Enqueue missing
            if "--enqueue" in sys.argv:
                enqueued = enqueue_missing(cur)
                conn.commit()
                print(f"\n➕ Enqueued {enqueued} missing rows")

            print("\n" + "=" * 60)

            # SLO check
            if pct and pct < 95:
                print("⚠️  WARNING: Coverage below 95% SLO!")
                sys.exit(1)
            else:
                print("✅ Coverage SLO met (≥95%)")

if __name__ == "__main__":
    main()
