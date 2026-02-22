#!/usr/bin/env python3
"""
F1 Search - Nightly Counterfactual Feedback Loop

Aggregates search click telemetry to learn yacht-specific vocabulary.
Strictly enforces tenant isolation (LAW 8) and projection immutability (LAW 9).

ARCHITECTURE:
- Reads from search_click_events (click telemetry)
- Aggregates by (yacht_id, object_id, query_text) with click threshold
- Updates search_index.learned_keywords (NOT search_text - preserved by Worker 4)
- Triggers re-embedding by updating content_hash

LAWS ENFORCED:
- LAW 8: All aggregation is partitioned by yacht_id. No cross-tenant learning.
- LAW 9: Only updates learned_keywords column, never search_text.

MEMORY GUARDRAILS:
- Uses server-side cursors (fetchmany) to stream aggregation results
- Never loads full click history into memory
- Safe for 512MB Render workers

Usage:
    DATABASE_URL=postgresql://... python nightly_feedback_loop.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required, use port 6543)
    MIN_CLICKS - Minimum clicks to learn a query (default: 3)
    LOOKBACK_DAYS - How many days of clicks to consider (default: 30)
    BATCH_SIZE - Rows to process per batch (default: 100)
    DRY_RUN - If "true", log changes without applying (default: false)
    LOG_LEVEL - Logging level (default: INFO)
"""

from __future__ import annotations

import os
import sys
import time
import logging
import signal
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

import psycopg2
import psycopg2.extras

# ============================================================================
# Configuration from Environment
# ============================================================================

DB_DSN = os.getenv("DATABASE_URL")
MIN_CLICKS = int(os.getenv("MIN_CLICKS", "3"))
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Memory safety: max keywords per object to prevent unbounded growth
MAX_KEYWORDS_PER_OBJECT = 50
MAX_KEYWORD_LENGTH = 100

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown
_shutdown = False


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown
    logger.info("Received shutdown signal, finishing current batch...")
    _shutdown = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class LearnedBridge:
    """A vocabulary bridge learned from click behavior."""
    yacht_id: str
    object_type: str
    object_id: str
    query_text: str
    click_count: int


@dataclass
class ObjectLearning:
    """Aggregated learning for a single object on a yacht."""
    yacht_id: str
    object_type: str
    object_id: str
    keywords: Set[str]


# ============================================================================
# Database Connection
# ============================================================================

def get_connection():
    """Create a database connection."""
    if not DB_DSN:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    # Ensure we're using the Supavisor pooler port
    dsn = DB_DSN
    if ":5432" in dsn:
        dsn = dsn.replace(":5432", ":6543")
        logger.warning("Switched port 5432 → 6543 (Supavisor pooler)")

    return psycopg2.connect(dsn)


# ============================================================================
# Phase 1: Aggregate Click Events (Memory-Safe)
# ============================================================================

def stream_aggregated_clicks(
    conn,
    min_clicks: int = MIN_CLICKS,
    lookback_days: int = LOOKBACK_DAYS,
) -> Dict[Tuple[str, str, str], Set[str]]:
    """
    Stream aggregated click data using server-side cursor.

    Returns: {(yacht_id, object_type, object_id): {query1, query2, ...}}

    Memory guarantee: Uses fetchmany() to stream results, never loads
    full click history into memory.
    """
    logger.info(f"Aggregating clicks (min_clicks={min_clicks}, lookback_days={lookback_days})")

    object_keywords: Dict[Tuple[str, str, str], Set[str]] = defaultdict(set)
    total_bridges = 0

    with conn.cursor(name='aggregate_clicks_cursor') as cur:
        # Use the aggregate_click_events function we created in the migration
        cur.execute(
            """
            SELECT yacht_id, object_type, object_id, query_text, click_count
            FROM aggregate_click_events(%s, %s)
            """,
            (min_clicks, lookback_days)
        )

        while not _shutdown:
            rows = cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            for row in rows:
                yacht_id, object_type, object_id, query_text, click_count = row

                # Sanitize query text
                query_text = str(query_text).strip()[:MAX_KEYWORD_LENGTH]
                if not query_text:
                    continue

                key = (str(yacht_id), object_type, str(object_id))

                # LAW 8: Each key is already yacht-scoped by the aggregation
                # Limit keywords per object to prevent unbounded growth
                if len(object_keywords[key]) < MAX_KEYWORDS_PER_OBJECT:
                    object_keywords[key].add(query_text)
                    total_bridges += 1

    logger.info(f"Aggregated {total_bridges} bridges for {len(object_keywords)} objects")
    return object_keywords


# ============================================================================
# Phase 2: Apply Learned Keywords (Batch Update)
# ============================================================================

def apply_learned_keywords(
    conn,
    object_keywords: Dict[Tuple[str, str, str], Set[str]],
    dry_run: bool = DRY_RUN,
) -> Tuple[int, int]:
    """
    Apply learned keywords to search_index.

    Updates learned_keywords column and triggers re-embedding.
    Respects LAW 9: Never touches search_text (owned by Worker 4).

    Returns: (updated_count, skipped_count)
    """
    updated = 0
    skipped = 0

    items = list(object_keywords.items())
    logger.info(f"Applying keywords to {len(items)} objects (dry_run={dry_run})")

    with conn.cursor() as cur:
        for i in range(0, len(items), BATCH_SIZE):
            if _shutdown:
                logger.info("Shutdown requested, stopping early")
                break

            batch = items[i:i + BATCH_SIZE]

            for (yacht_id, object_type, object_id), keywords in batch:
                # Convert keywords set to sorted list for determinism
                keywords_list = sorted(keywords)[:MAX_KEYWORDS_PER_OBJECT]

                if dry_run:
                    logger.debug(
                        f"[DRY RUN] Would update {object_type}/{object_id} "
                        f"on yacht {yacht_id[:8]}... with {len(keywords_list)} keywords"
                    )
                    updated += 1
                    continue

                try:
                    # Use the apply_learned_keywords function from migration
                    cur.execute(
                        """
                        SELECT apply_learned_keywords(%s, %s, %s, %s)
                        """,
                        (yacht_id, object_type, object_id, keywords_list)
                    )
                    result = cur.fetchone()
                    if result and result[0]:
                        updated += 1
                        logger.debug(
                            f"Updated {object_type}/{object_id} "
                            f"with {len(keywords_list)} learned keywords"
                        )
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(
                        f"Error updating {object_type}/{object_id}: {e}"
                    )
                    skipped += 1
                    continue

            # Commit after each batch
            if not dry_run:
                conn.commit()
                logger.debug(f"Committed batch {i // BATCH_SIZE + 1}")

    return updated, skipped


# ============================================================================
# Phase 3: Upsert to Audit Table (Optional)
# ============================================================================

def record_learned_bridges(
    conn,
    object_keywords: Dict[Tuple[str, str, str], Set[str]],
) -> int:
    """
    Record learned bridges to audit table for observability.

    This creates an audit trail of what the system learned.
    """
    recorded = 0

    with conn.cursor() as cur:
        for (yacht_id, object_type, object_id), keywords in object_keywords.items():
            if _shutdown:
                break

            for query_text in keywords:
                try:
                    cur.execute(
                        """
                        INSERT INTO search_learned_bridges (
                            yacht_id, object_type, object_id, query_text,
                            click_count, applied, applied_at, last_clicked_at
                        )
                        VALUES (%s, %s, %s, %s, 1, TRUE, NOW(), NOW())
                        ON CONFLICT (yacht_id, object_type, object_id, query_text)
                        DO UPDATE SET
                            click_count = search_learned_bridges.click_count + 1,
                            applied = TRUE,
                            applied_at = NOW(),
                            last_clicked_at = NOW()
                        """,
                        (yacht_id, object_type, object_id, query_text)
                    )
                    recorded += 1
                except Exception as e:
                    logger.warning(f"Failed to record bridge: {e}")

        conn.commit()

    return recorded


# ============================================================================
# Phase 4: Cleanup Old Click Events (Optional)
# ============================================================================

def cleanup_old_clicks(conn, retention_days: int = 90) -> int:
    """
    Delete click events older than retention period.

    Memory-safe: Uses batched deletes to avoid locking.
    """
    deleted = 0
    batch_delete_size = 1000

    logger.info(f"Cleaning up clicks older than {retention_days} days")

    with conn.cursor() as cur:
        while not _shutdown:
            cur.execute(
                """
                DELETE FROM search_click_events
                WHERE id IN (
                    SELECT id FROM search_click_events
                    WHERE clicked_at < NOW() - INTERVAL '%s days'
                    LIMIT %s
                )
                """,
                (retention_days, batch_delete_size)
            )
            batch_deleted = cur.rowcount
            conn.commit()

            if batch_deleted == 0:
                break

            deleted += batch_deleted
            logger.debug(f"Deleted batch of {batch_deleted} old click events")

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old click events")

    return deleted


# ============================================================================
# Main Entry Point
# ============================================================================

def run_feedback_loop():
    """
    Execute the nightly feedback loop.

    Steps:
    1. Aggregate clicks by (yacht_id, object_id, query_text)
    2. Apply learned keywords to search_index
    3. Record to audit table
    4. Cleanup old click events
    """
    logger.info("=" * 60)
    logger.info("F1 Search - Nightly Counterfactual Feedback Loop")
    logger.info("=" * 60)
    logger.info(f"Config: min_clicks={MIN_CLICKS}, lookback={LOOKBACK_DAYS}d, batch={BATCH_SIZE}")
    logger.info(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")

    start_time = time.time()

    try:
        conn = get_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    try:
        # Phase 1: Aggregate
        object_keywords = stream_aggregated_clicks(conn)

        if not object_keywords:
            logger.info("No vocabulary bridges to learn. Exiting.")
            return

        # Phase 2: Apply
        updated, skipped = apply_learned_keywords(conn, object_keywords)

        # Phase 3: Audit trail
        if not DRY_RUN:
            recorded = record_learned_bridges(conn, object_keywords)
            logger.info(f"Recorded {recorded} bridges to audit table")

        # Phase 4: Cleanup (only if not dry run)
        if not DRY_RUN:
            cleanup_old_clicks(conn)

        elapsed = time.time() - start_time

        logger.info("=" * 60)
        logger.info("Feedback Loop Complete")
        logger.info(f"  Objects updated: {updated}")
        logger.info(f"  Objects skipped: {skipped}")
        logger.info(f"  Total keywords learned: {sum(len(kw) for kw in object_keywords.values())}")
        logger.info(f"  Elapsed: {elapsed:.2f}s")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"Feedback loop failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    run_feedback_loop()
