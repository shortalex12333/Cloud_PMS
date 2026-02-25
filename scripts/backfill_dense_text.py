#!/usr/bin/env python3
"""
Backfill script for F1 Cortex search pipeline.

Re-enriches sparse search_text for rows indexed before Dense Payload Fallback
logic was added, then queues them for re-embedding.

Usage:
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py --dry-run
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py --batch-size 50
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Object types that need backfill
TARGET_OBJECT_TYPES = (
    "inventory",
    "part",
    "receiving",
    "work_order",
    "work_order_note",
    "shopping_item",
)

# Semantic fields to extract from payload JSONB (same as projection_worker.py)
SEMANTIC_FIELDS = [
    "name",
    "title",
    "description",
    "category",
    "location",
    "sku",
    "manufacturer",
    "part_number",
    "model",
    "brand",
    "notes",
    "content",
]

# Threshold for sparse search_text
SPARSE_THRESHOLD = 100

# Default batch size
DEFAULT_BATCH_SIZE = 100


def extract_semantic_text(payload: dict) -> str:
    """
    Extract semantic field values from payload JSONB.

    Args:
        payload: The payload JSONB as a Python dict

    Returns:
        Space-separated string of extracted field values
    """
    values = []
    for field in SEMANTIC_FIELDS:
        value = payload.get(field)
        if value and isinstance(value, str):
            stripped = value.strip()
            if stripped:
                values.append(stripped)
    return " ".join(values)


def tokenize(text: str) -> set:
    """
    Tokenize text into lowercase words for deduplication.

    Args:
        text: Input text string

    Returns:
        Set of lowercase tokens
    """
    if not text:
        return set()
    # Split on whitespace and normalize to lowercase
    return set(word.lower() for word in text.split() if word)


def build_enriched_text(existing_text: str, payload: dict) -> str:
    """
    Build enriched search_text by combining existing text with payload fields.
    Deduplicates tokens that already exist in search_text.

    Args:
        existing_text: Current search_text value
        payload: The payload JSONB as a Python dict

    Returns:
        Enriched search_text with deduplicated tokens
    """
    existing_text = existing_text or ""
    existing_tokens = tokenize(existing_text)

    # Extract semantic text from payload
    semantic_text = extract_semantic_text(payload)

    if not semantic_text:
        return existing_text

    # Find new tokens not already in existing text
    new_parts = []
    for word in semantic_text.split():
        if word.lower() not in existing_tokens:
            new_parts.append(word)
            existing_tokens.add(word.lower())  # Prevent duplicates within semantic text

    if not new_parts:
        return existing_text

    # Combine existing text with new tokens
    if existing_text.strip():
        return f"{existing_text.strip()} {' '.join(new_parts)}"
    else:
        return " ".join(new_parts)


def get_sparse_rows(cursor, batch_size: int, offset: int) -> list:
    """
    Fetch a batch of rows with sparse search_text.

    Args:
        cursor: Database cursor
        batch_size: Number of rows to fetch
        offset: Offset for pagination

    Returns:
        List of row dictionaries
    """
    query = """
        SELECT id, object_type, object_id, yacht_id, org_id, search_text, payload
        FROM search_index
        WHERE object_type = ANY(%s)
          AND (search_text IS NULL OR LENGTH(search_text) < %s)
        ORDER BY id
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, (list(TARGET_OBJECT_TYPES), SPARSE_THRESHOLD, batch_size, offset))
    return cursor.fetchall()


def count_sparse_rows(cursor) -> int:
    """
    Count total rows needing backfill.

    Args:
        cursor: Database cursor

    Returns:
        Total count of sparse rows
    """
    query = """
        SELECT COUNT(*)
        FROM search_index
        WHERE object_type = ANY(%s)
          AND (search_text IS NULL OR LENGTH(search_text) < %s)
    """
    cursor.execute(query, (list(TARGET_OBJECT_TYPES), SPARSE_THRESHOLD))
    result = cursor.fetchone()
    return result["count"] if result else 0


def update_search_text(cursor, row_id: str, enriched_text: str) -> None:
    """
    Update search_text for a row.

    Args:
        cursor: Database cursor
        row_id: UUID of the search_index row
        enriched_text: New enriched search_text
    """
    query = """
        UPDATE search_index
        SET search_text = %s, updated_at = NOW()
        WHERE id = %s
    """
    cursor.execute(query, (enriched_text, row_id))


def queue_embedding_job(
    cursor,
    object_type: str,
    object_id: str,
    yacht_id: Optional[str],
    org_id: Optional[str] = None,
) -> None:
    """
    Insert or update embedding job to queue re-embedding.

    Args:
        cursor: Database cursor
        object_type: Type of the object
        object_id: UUID of the object
        yacht_id: UUID of the yacht (optional)
        org_id: UUID of the org (optional)
    """
    # NOTE: Unique constraint is on (yacht_id, object_type, object_id)
    # Let DB auto-generate id (bigint serial)
    # Use yacht_id as org_id fallback if org_id is NULL
    effective_org_id = org_id if org_id else yacht_id
    query = """
        INSERT INTO embedding_jobs (object_type, object_id, yacht_id, org_id, status, queued_at)
        VALUES (%s, %s, %s, %s, 'queued', NOW())
        ON CONFLICT (yacht_id, object_type, object_id)
        DO UPDATE SET status = 'queued', queued_at = NOW()
    """
    cursor.execute(query, (object_type, object_id, yacht_id, effective_org_id))


def process_batch(
    conn,
    rows: list,
    dry_run: bool = False,
) -> tuple:
    """
    Process a batch of rows.

    Args:
        conn: Database connection
        rows: List of row dictionaries
        dry_run: If True, don't commit changes

    Returns:
        Tuple of (updated_count, skipped_count)
    """
    updated = 0
    skipped = 0

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        for row in rows:
            row_id = str(row["id"])
            object_type = row["object_type"]
            object_id = str(row["object_id"])
            yacht_id = str(row["yacht_id"]) if row["yacht_id"] else None
            org_id = str(row["org_id"]) if row.get("org_id") else None
            search_text = row["search_text"] or ""
            payload = row["payload"] or {}

            # Parse payload if it's a string
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON payload for row {row_id}, skipping")
                    skipped += 1
                    continue

            # Build enriched text
            enriched_text = build_enriched_text(search_text, payload)

            # Check if enrichment actually added content
            if enriched_text == search_text or len(enriched_text) < SPARSE_THRESHOLD:
                logger.debug(
                    f"Row {row_id} ({object_type}): No enrichment possible, "
                    f"payload may lack semantic fields"
                )
                skipped += 1
                continue

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would update row {row_id} ({object_type}): "
                    f"{len(search_text)} -> {len(enriched_text)} chars"
                )
            else:
                # Update search_text
                update_search_text(cursor, row_id, enriched_text)

                # Queue for re-embedding
                queue_embedding_job(cursor, object_type, object_id, yacht_id, org_id)

                logger.debug(
                    f"Updated row {row_id} ({object_type}): "
                    f"{len(search_text)} -> {len(enriched_text)} chars"
                )

            updated += 1

        if not dry_run:
            conn.commit()

    return updated, skipped


def run_backfill(
    database_url: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> None:
    """
    Run the backfill process.

    Args:
        database_url: PostgreSQL connection string
        batch_size: Number of rows to process per batch
        dry_run: If True, don't commit changes
    """
    logger.info("=" * 60)
    logger.info("F1 Cortex Search Pipeline - Dense Text Backfill")
    logger.info("=" * 60)
    logger.info(f"Target object types: {', '.join(TARGET_OBJECT_TYPES)}")
    logger.info(f"Sparse threshold: < {SPARSE_THRESHOLD} characters")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    logger.info("-" * 60)

    try:
        conn = psycopg2.connect(database_url)
        logger.info("Connected to database")
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            total_rows = count_sparse_rows(cursor)

        logger.info(f"Found {total_rows} rows with sparse search_text")

        if total_rows == 0:
            logger.info("No rows to process. Exiting.")
            return

        total_updated = 0
        total_skipped = 0
        offset = 0
        batch_num = 0

        while True:
            batch_num += 1

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                rows = get_sparse_rows(cursor, batch_size, offset)

            if not rows:
                break

            logger.info(
                f"Processing batch {batch_num} "
                f"(rows {offset + 1}-{offset + len(rows)} of {total_rows})"
            )

            updated, skipped = process_batch(conn, rows, dry_run)

            total_updated += updated
            total_skipped += skipped

            logger.info(
                f"Batch {batch_num} complete: "
                f"{updated} updated, {skipped} skipped"
            )

            # Move offset - we process all rows regardless of update status
            offset += len(rows)

        logger.info("-" * 60)
        logger.info("Backfill complete!")
        logger.info(f"Total rows processed: {offset}")
        logger.info(f"Total rows updated: {total_updated}")
        logger.info(f"Total rows skipped: {total_skipped}")

        if dry_run:
            logger.info("")
            logger.info("This was a DRY-RUN. No changes were committed.")
            logger.info("Run without --dry-run to apply changes.")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        conn.rollback()
        sys.exit(130)
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill sparse search_text in F1 Cortex search pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py --dry-run
    DATABASE_URL="postgresql://..." python scripts/backfill_dense_text.py --batch-size 50

Environment Variables:
    DATABASE_URL    PostgreSQL connection string for tenant database (required)
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of rows to process per batch (default: {DEFAULT_BATCH_SIZE})",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        logger.error("Usage: DATABASE_URL='postgresql://...' python scripts/backfill_dense_text.py")
        sys.exit(1)

    if args.batch_size < 1:
        logger.error("Batch size must be at least 1")
        sys.exit(1)

    run_backfill(
        database_url=database_url,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
