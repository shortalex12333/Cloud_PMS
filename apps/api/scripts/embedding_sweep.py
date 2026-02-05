#!/usr/bin/env python3
"""
Embedding Sweep Cron Script

Auto-queue items with stale or missing embeddings.
Run via cron every 5-10 minutes.

Usage:
    DATABASE_URL=postgresql://... python embedding_sweep.py [--dry-run]

Schedule (crontab):
    */5 * * * * cd /app && DATABASE_URL=$DATABASE_URL python scripts/embedding_sweep.py

Environment:
    DATABASE_URL: PostgreSQL connection string
    EMBED_STALE_DAYS: Days before embedding is considered stale (default: 30)
    SWEEP_BATCH_SIZE: Max items to enqueue per run (default: 100)
"""

import os
import sys
from datetime import datetime, timezone

import psycopg2

DB_DSN = os.getenv("DATABASE_URL")
STALE_DAYS = int(os.getenv("EMBED_STALE_DAYS", "30"))
BATCH_SIZE = int(os.getenv("SWEEP_BATCH_SIZE", "100"))


def get_missing_count(cur) -> int:
    """Count rows missing embeddings entirely."""
    cur.execute("SELECT COUNT(*) FROM search_index WHERE embedding IS NULL")
    return cur.fetchone()[0]


def get_stale_count(cur) -> int:
    """Count rows with stale embeddings (older than STALE_DAYS)."""
    cur.execute("""
        SELECT COUNT(*) FROM search_index
        WHERE embedding IS NOT NULL
          AND embedded_at < NOW() - INTERVAL '%s days'
    """, (STALE_DAYS,))
    return cur.fetchone()[0]


def enqueue_missing(cur, limit: int) -> int:
    """
    Enqueue rows missing embeddings.
    Returns count of newly enqueued rows.
    """
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


def enqueue_stale(cur, limit: int) -> int:
    """
    Enqueue rows with stale embeddings (older than STALE_DAYS).
    Returns count of newly enqueued rows.
    """
    cur.execute("""
        INSERT INTO embedding_jobs (object_type, object_id, status)
        SELECT object_type, object_id, 'queued'
        FROM search_index
        WHERE embedding IS NOT NULL
          AND embedded_at < NOW() - INTERVAL '%s days'
          AND NOT EXISTS (
              SELECT 1 FROM embedding_jobs ej
              WHERE ej.object_type = search_index.object_type
                AND ej.object_id = search_index.object_id
                AND ej.status IN ('queued', 'working')
          )
        LIMIT %s
        ON CONFLICT (object_type, object_id) DO NOTHING
        RETURNING object_id
    """, (STALE_DAYS, limit))
    return cur.rowcount


def main():
    if not DB_DSN:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    timestamp = datetime.now(timezone.utc).isoformat()

    with psycopg2.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            # Get counts
            missing_count = get_missing_count(cur)
            stale_count = get_stale_count(cur)

            if verbose:
                print(f"[{timestamp}] Missing: {missing_count}, Stale (>{STALE_DAYS}d): {stale_count}")

            if dry_run:
                print(f"[DRY RUN] Would enqueue up to {BATCH_SIZE} items")
                print(f"  Missing embeddings: {missing_count}")
                print(f"  Stale embeddings (>{STALE_DAYS}d): {stale_count}")
                return

            # Priority 1: Missing embeddings
            enqueued_missing = 0
            if missing_count > 0:
                enqueued_missing = enqueue_missing(cur, BATCH_SIZE)
                conn.commit()

            # Priority 2: Stale embeddings (use remaining budget)
            remaining_budget = BATCH_SIZE - enqueued_missing
            enqueued_stale = 0
            if stale_count > 0 and remaining_budget > 0:
                enqueued_stale = enqueue_stale(cur, remaining_budget)
                conn.commit()

            total_enqueued = enqueued_missing + enqueued_stale

            # Output for cron logging
            if total_enqueued > 0 or verbose:
                print(f"[{timestamp}] Sweep: enqueued={total_enqueued} (missing={enqueued_missing}, stale={enqueued_stale})")

            # Exit code: 0 if no work needed, 0 if work done
            # Non-zero only on error
            sys.exit(0)


if __name__ == "__main__":
    main()
