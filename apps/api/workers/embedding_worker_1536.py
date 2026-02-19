#!/usr/bin/env python3
"""
F1 Search - Embedding Worker (1536-dim, OpenAI text-embedding-3-small)

Generates 1536-dim embeddings for search_index rows using OpenAI API.
Writes to embedding_1536 column with delta tracking via content_hash.

GUARDRAILS:
- 1536-dim embeddings for HNSW cosine similarity
- Delta embedding: only when embedding_hash != content_hash OR embedding_version <> 3
- Batch processing with rate limiting
- Uses Supavisor port 6543 for connection pooling

Usage:
    DATABASE_URL=postgresql://... OPENAI_API_KEY=sk-... python embedding_worker_1536.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required, use port 6543)
    OPENAI_API_KEY - OpenAI API key (required)
    EMBED_MODEL - Model name (default: text-embedding-3-small)
    EMBED_DIMS - Embedding dimension (default: 1536)
    EMBEDDING_VERSION - Schema version (default: 3)
    BATCH_SIZE - Rows per batch (default: 100)
    BATCH_SLEEP_SEC - Sleep between batches (default: 0.1)
    ERROR_SLEEP_SEC - Sleep on error (default: 2.0)
    REQUEST_TIMEOUT_SEC - API timeout (default: 30)
    LOG_LEVEL - Logging level (default: INFO)

Delta Policy:
    Only re-embed when:
    - embedding_1536 IS NULL (never embedded)
    - embedding_hash IS NULL (no hash recorded)
    - embedding_hash != content_hash (content changed)
    - embedding_version IS NULL OR embedding_version < 3 (old schema)
"""

from __future__ import annotations

import os
import sys
import time
import logging
import math
import hashlib
import signal
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable

import psycopg2
import psycopg2.extras

# ============================================================================
# Configuration from Environment
# ============================================================================

DB_DSN = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
EMBED_DIMS = int(os.getenv("EMBED_DIMS", os.getenv("EMBED_DIM", "1536")))
EMBED_VERSION = int(os.getenv("EMBEDDING_VERSION", "3"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
BATCH_SLEEP_SEC = float(os.getenv("BATCH_SLEEP_SEC", "0.1"))
ERROR_SLEEP_SEC = float(os.getenv("ERROR_SLEEP_SEC", "2.0"))
REQUEST_TIMEOUT_SEC = int(os.getenv("REQUEST_TIMEOUT_SEC", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# OpenAI limits
MAX_CHARS_PER_TEXT = 8000  # Safe limit for embedding

# Circuit breaker configuration (prevents death spiral during OpenAI outages)
CIRCUIT_BREAKER_THRESHOLD = 5      # Consecutive failures before circuit opens
CIRCUIT_BREAKER_RESET_SEC = 60     # Seconds to wait before trying again
MAX_RETRY_COUNT = 3                # Max retries per row before moving to DLQ
DLQ_TABLE = "search_embedding_dlq" # Dead letter queue table

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Graceful shutdown
_shutdown = False

# Circuit breaker state
_circuit_failures = 0
_circuit_open_until = 0.0  # timestamp when circuit can close


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown
    logger.info("Received shutdown signal, finishing current batch...")
    _shutdown = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# OpenAI Client
# ============================================================================

_client = None


def get_client():
    """Lazy load OpenAI client."""
    global _client
    if _client is None:
        try:
            from openai import OpenAI
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            logger.info(f"Initializing OpenAI client (model={EMBED_MODEL}, dims={EMBED_DIMS})")
            _client = OpenAI(api_key=OPENAI_API_KEY, timeout=REQUEST_TIMEOUT_SEC)
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            sys.exit(1)
    return _client


def normalize_vector(vec: List[float]) -> List[float]:
    """Normalize vector to unit length for cosine similarity."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of text content (first 32 chars)."""
    if not text:
        return ""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]


def check_circuit_breaker() -> bool:
    """
    Check if circuit breaker allows requests.

    Returns True if requests should be blocked (circuit is open).
    Returns False if requests are allowed (circuit is closed).
    """
    global _circuit_failures, _circuit_open_until

    if _circuit_failures >= CIRCUIT_BREAKER_THRESHOLD:
        if time.time() < _circuit_open_until:
            return True  # Circuit is open, block requests
        else:
            # Try to close circuit (half-open state)
            logger.info("Circuit breaker: attempting to close (half-open state)")
            return False
    return False


def record_circuit_success():
    """Record a successful API call - closes circuit."""
    global _circuit_failures, _circuit_open_until
    if _circuit_failures > 0:
        logger.info(f"Circuit breaker: closing (was at {_circuit_failures} failures)")
    _circuit_failures = 0
    _circuit_open_until = 0.0


def record_circuit_failure(error: Exception):
    """Record a failed API call - may open circuit."""
    global _circuit_failures, _circuit_open_until
    _circuit_failures += 1

    if _circuit_failures >= CIRCUIT_BREAKER_THRESHOLD:
        _circuit_open_until = time.time() + CIRCUIT_BREAKER_RESET_SEC
        logger.error(f"Circuit breaker: OPEN after {_circuit_failures} consecutive failures. "
                    f"Will retry in {CIRCUIT_BREAKER_RESET_SEC}s. Last error: {error}")


def is_rate_limit_error(error: Exception) -> bool:
    """Check if error is a rate limit (429) error."""
    error_str = str(error).lower()
    return '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str


def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts via OpenAI API.

    HARDENED: Includes circuit breaker pattern to prevent death spiral.

    Returns list of normalized 1536-dim vectors.
    Raises CircuitBreakerOpen if circuit is open.
    """
    # Check circuit breaker BEFORE attempting API call
    if check_circuit_breaker():
        raise CircuitBreakerOpenError(f"Circuit breaker open until {_circuit_open_until}")

    client = get_client()

    # Truncate long texts
    truncated = [t[:MAX_CHARS_PER_TEXT] if len(t) > MAX_CHARS_PER_TEXT else t for t in texts]

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBED_MODEL,
                input=truncated,
                dimensions=EMBED_DIMS
            )
            embeddings = []
            for item in response.data:
                vec = normalize_vector(item.embedding)
                embeddings.append(vec)

            # Success - close circuit
            record_circuit_success()
            return embeddings

        except Exception as e:
            # Check for rate limit - use longer backoff
            if is_rate_limit_error(e):
                wait = min(30, (2 ** attempt) * 5)  # 5s, 10s, 20s for rate limits
                logger.warning(f"OpenAI rate limited (attempt {attempt + 1}): {e}, backing off {wait}s...")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                wait = (2 ** attempt) * 0.5
                logger.warning(f"OpenAI API error (attempt {attempt + 1}): {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                # Final failure - record for circuit breaker
                record_circuit_failure(e)
                logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    pass


# ============================================================================
# Database Operations
# ============================================================================

def fetch_batch_needing_embedding(cur, batch_size: int) -> List[Dict[str, Any]]:
    """
    Fetch rows that need 1536-dim embedding (delta policy).

    Returns rows where:
    1. embedding_1536 IS NULL (never embedded), OR
    2. embedding_hash IS NULL (no hash recorded), OR
    3. embedding_hash != content_hash (content changed), OR
    4. embedding_version IS NULL OR < 3 (old schema)

    Uses FOR UPDATE SKIP LOCKED for concurrent worker safety.
    """
    cur.execute("""
        SELECT id, object_type, object_id, search_text, content_hash
        FROM search_index
        WHERE search_text IS NOT NULL
          AND search_text != ''
          AND (
              embedding_1536 IS NULL
              OR embedding_hash IS NULL
              OR embedding_hash != content_hash
              OR embedding_version IS NULL
              OR embedding_version < %s
          )
        ORDER BY updated_at DESC
        FOR UPDATE SKIP LOCKED
        LIMIT %s
    """, (EMBED_VERSION, batch_size))
    return [dict(r) for r in cur.fetchall()]


def write_embeddings_batch(
    cur,
    rows: List[Dict[str, Any]],
    embeddings: List[List[float]]
) -> int:
    """
    Write 1536-dim embeddings to search_index.

    Updates:
    - embedding_1536: the 1536-dim vector
    - embedding_model: model name
    - embedding_version: schema version (3)
    - embedding_hash: hash of search_text for delta tracking
    - content_hash: also updated to ensure consistency
    - updated_at: timestamp

    Returns count of rows updated.
    """
    if not rows or not embeddings:
        return 0

    updated = 0
    for row, vec in zip(rows, embeddings):
        # Compute hash from the text we embedded
        new_hash = compute_content_hash(row['search_text'])

        # Format as PostgreSQL vector literal
        vec_str = f"[{','.join(str(x) for x in vec)}]"

        cur.execute(f"""
            UPDATE search_index
            SET embedding_1536 = %s::vector({EMBED_DIMS}),
                embedding_model = %s,
                embedding_version = %s,
                embedding_hash = %s,
                content_hash = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (vec_str, EMBED_MODEL, EMBED_VERSION, new_hash, new_hash, row['id']))
        updated += cur.rowcount

    return updated


def get_embedding_stats(cur) -> Dict[str, Any]:
    """Get current embedding statistics."""
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(embedding_1536) AS with_1536,
            COUNT(CASE WHEN embedding_version = %s THEN 1 END) AS version_current,
            COUNT(CASE WHEN embedding_hash IS NOT NULL
                        AND embedding_hash = content_hash
                        AND embedding_version = %s THEN 1 END) AS up_to_date
        FROM search_index
        WHERE search_text IS NOT NULL AND search_text != ''
    """, (EMBED_VERSION, EMBED_VERSION))
    row = cur.fetchone()
    return {
        'total': row['total'],
        'with_1536': row['with_1536'],
        'version_current': row['version_current'],
        'up_to_date': row['up_to_date'],
        'needs_embedding': row['total'] - row['up_to_date'],
        'coverage_pct': round(100.0 * row['with_1536'] / row['total'], 1) if row['total'] > 0 else 0,
    }


# ============================================================================
# Queue-Based Entity Handlers
# ============================================================================

def handle_handover_export(entity_id: str, cur) -> dict:
    """
    Process a handover export for search indexing.

    Extracts text from edited_content sections and creates searchable content.
    Only indexes exports with review_status = 'complete'.
    """
    cur.execute("""
        SELECT id, handover_id, yacht_id, signed_storage_url,
               edited_content, user_signature, hod_signature, review_status
        FROM handover_exports
        WHERE id = %s
    """, (entity_id,))
    row = cur.fetchone()

    if not row:
        raise ValueError(f"Handover export {entity_id} not found")

    export_data = dict(row)

    # Only index complete exports
    if export_data["review_status"] != "complete":
        return {"skipped": True, "reason": "Not complete"}

    # Extract searchable text
    text_parts = []

    # Add section content from edited_content JSONB
    edited_content = export_data.get("edited_content") or {}
    if isinstance(edited_content, str):
        try:
            edited_content = json.loads(edited_content)
        except (json.JSONDecodeError, TypeError):
            edited_content = {}

    sections = edited_content.get("sections", [])
    for section in sections:
        text_parts.append(f"## {section.get('title', '')}")
        text_parts.append(section.get("content", ""))

        for item in section.get("items", []):
            priority = item.get("priority", "")
            content = item.get("content", "")
            text_parts.append(f"[{priority}] {content}")

    # Add signature info
    user_signature = export_data.get("user_signature") or {}
    if isinstance(user_signature, str):
        try:
            user_signature = json.loads(user_signature)
        except (json.JSONDecodeError, TypeError):
            user_signature = {}

    hod_signature = export_data.get("hod_signature") or {}
    if isinstance(hod_signature, str):
        try:
            hod_signature = json.loads(hod_signature)
        except (json.JSONDecodeError, TypeError):
            hod_signature = {}

    if user_signature:
        text_parts.append(
            f"Signed by: {user_signature.get('signer_name')} on {user_signature.get('signed_at')}"
        )

    if hod_signature:
        text_parts.append(
            f"Approved by: {hod_signature.get('signer_name')} on {hod_signature.get('signed_at')}"
        )

    full_text = "\n".join(filter(None, text_parts))

    # Generate embedding via OpenAI
    embedding = embed_texts_batch([full_text])[0]
    vec_str = f"[{','.join(str(x) for x in embedding)}]"
    content_hash = compute_content_hash(full_text)
    now_utc = datetime.now(timezone.utc).isoformat()

    metadata = {
        "handover_id": str(export_data["handover_id"]) if export_data.get("handover_id") else None,
        "section_count": len(sections),
        "signed_at": user_signature.get("signed_at") if user_signature else None,
        "approved_at": hod_signature.get("signed_at") if hod_signature else None,
    }

    # Upsert into search_index (ON CONFLICT on entity_type + entity_id)
    cur.execute(f"""
        INSERT INTO search_index (
            entity_type, entity_id, yacht_id, content,
            embedding_1536, embedding_model, embedding_version, embedding_hash, content_hash,
            metadata, indexed_at, updated_at
        ) VALUES (
            'handover_export', %s, %s, %s,
            %s::vector({EMBED_DIMS}), %s, %s, %s, %s,
            %s::jsonb, %s, NOW()
        )
        ON CONFLICT (entity_type, entity_id) DO UPDATE SET
            content = EXCLUDED.content,
            embedding_1536 = EXCLUDED.embedding_1536,
            embedding_model = EXCLUDED.embedding_model,
            embedding_version = EXCLUDED.embedding_version,
            embedding_hash = EXCLUDED.embedding_hash,
            content_hash = EXCLUDED.content_hash,
            metadata = EXCLUDED.metadata,
            indexed_at = EXCLUDED.indexed_at,
            updated_at = NOW()
    """, (
        entity_id,
        str(export_data["yacht_id"]) if export_data.get("yacht_id") else None,
        full_text[:10000],
        vec_str,
        EMBED_MODEL,
        EMBED_VERSION,
        content_hash,
        content_hash,
        json.dumps(metadata),
        now_utc,
    ))

    return {
        "indexed": True,
        "text_length": len(full_text),
        "section_count": len(sections),
    }


# Registry of queue-based entity type handlers.
# Maps entity_type string to handler function(entity_id, cur) -> dict.
ENTITY_HANDLERS: Dict[str, Callable[[str, Any], dict]] = {
    "handover_export": handle_handover_export,
}


# ============================================================================
# Queue-Based Processing (search_index_queue)
# ============================================================================

def process_queue_batch(conn) -> int:
    """
    Process one batch of items from search_index_queue.

    Fetches up to BATCH_SIZE pending items, processes each via ENTITY_HANDLERS,
    and marks items as complete or failed. Returns count of items processed.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Fetch pending items ordered by priority DESC (higher priority first)
        cur.execute("""
            SELECT id, entity_type, entity_id, yacht_id
            FROM search_index_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (BATCH_SIZE,))
        items = [dict(r) for r in cur.fetchall()]

        if not items:
            conn.commit()
            return 0

        logger.info(f"Queue: processing {len(items)} pending item(s)...")
        processed = 0

        for item in items:
            item_id = item["id"]
            entity_type = item["entity_type"]
            entity_id = str(item["entity_id"])

            # Mark as processing
            cur.execute("""
                UPDATE search_index_queue
                SET status = 'processing',
                    started_at = NOW()
                WHERE id = %s
            """, (item_id,))

            handler = ENTITY_HANDLERS.get(entity_type)
            if not handler:
                cur.execute("""
                    UPDATE search_index_queue
                    SET status = 'failed',
                        error = %s
                    WHERE id = %s
                """, (f"Unknown entity type: {entity_type}", item_id))
                logger.warning(f"Queue: unknown entity type '{entity_type}' for item {item_id}")
                processed += 1
                continue

            try:
                result = handler(entity_id, cur)
                result_json = json.dumps(result)
                cur.execute("""
                    UPDATE search_index_queue
                    SET status = 'complete',
                        completed_at = NOW(),
                        result = %s::jsonb
                    WHERE id = %s
                """, (result_json, item_id))
                logger.info(f"Queue: {entity_type}/{entity_id} indexed — {result}")
                processed += 1

            except Exception as e:
                error_msg = str(e)[:2000]
                cur.execute("""
                    UPDATE search_index_queue
                    SET status = 'failed',
                        error = %s
                    WHERE id = %s
                """, (error_msg, item_id))
                logger.error(f"Queue: failed to index {entity_type}/{entity_id}: {e}")
                processed += 1

        conn.commit()
        return processed


# ============================================================================
# Main Processing
# ============================================================================

def ensure_dlq_table(cur):
    """
    Ensure dead letter queue table exists.

    HARDENED: Creates DLQ table if missing for poisoned message isolation.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_embedding_dlq (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_table TEXT NOT NULL,
            source_id UUID NOT NULL,
            error_message TEXT,
            retry_count INT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_attempt_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(source_table, source_id)
        )
    """)


def move_to_dlq(cur, row: Dict[str, Any], error: str, retry_count: int = 0):
    """
    Move a poisoned row to dead letter queue.

    HARDENED: Prevents infinite retry loops for bad data.
    """
    try:
        cur.execute("""
            INSERT INTO search_embedding_dlq (source_table, source_id, error_message, retry_count, last_attempt_at)
            VALUES ('search_index', %s, %s, %s, NOW())
            ON CONFLICT (source_table, source_id) DO UPDATE SET
                error_message = EXCLUDED.error_message,
                retry_count = search_embedding_dlq.retry_count + 1,
                last_attempt_at = NOW()
        """, (row['id'], error[:2000], retry_count))
        logger.warning(f"Moved row {row['id']} to DLQ: {error[:200]}")
    except Exception as dlq_error:
        logger.error(f"Failed to move row {row['id']} to DLQ: {dlq_error}")


def process_batch(conn) -> int:
    """
    Process one batch of rows.

    HARDENED: Per-row error isolation prevents one bad row from crashing batch.

    Returns count of rows processed, or 0 if queue is empty.
    """
    # Check circuit breaker before even fetching rows
    if check_circuit_breaker():
        logger.warning("Circuit breaker open, skipping batch")
        time.sleep(CIRCUIT_BREAKER_RESET_SEC / 2)  # Wait before next attempt
        return 0

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Ensure DLQ table exists
        try:
            ensure_dlq_table(cur)
            conn.commit()
        except Exception as e:
            logger.warning(f"Could not ensure DLQ table: {e}")
            conn.rollback()

        rows = fetch_batch_needing_embedding(cur, BATCH_SIZE)

        if not rows:
            conn.commit()
            return 0

        logger.info(f"Processing batch of {len(rows)} rows...")

        # HARDENED: Process rows individually to isolate failures
        updated = 0
        failed = 0

        for row in rows:
            try:
                # Extract text for single row
                text = row.get('search_text', '')
                if not text:
                    logger.warning(f"Row {row['id']} has empty search_text, skipping")
                    continue

                # Generate embedding for single row
                embeddings = embed_texts_batch([text])

                if not embeddings or len(embeddings) == 0:
                    raise ValueError("No embedding returned")

                emb = embeddings[0]

                # Verify dimension
                if len(emb) != EMBED_DIMS:
                    logger.error(f"Bad embedding dimension {len(emb)} for row {row['id']}")
                    emb = [0.0] * EMBED_DIMS  # Fallback

                # Write single row
                row_updated = write_embeddings_batch(cur, [row], [emb])
                conn.commit()
                updated += row_updated

            except CircuitBreakerOpenError as cbe:
                # Circuit breaker opened mid-batch - stop processing
                logger.warning(f"Circuit breaker opened during batch: {cbe}")
                conn.rollback()
                break

            except Exception as e:
                # HARDENED: Isolate failure to this row only
                conn.rollback()
                failed += 1
                logger.error(f"Failed to embed row {row['id']}: {e}")

                # Move to DLQ after MAX_RETRY_COUNT failures
                # (In production, track retry count in a column or separate table)
                move_to_dlq(cur, row, str(e))
                conn.commit()

        if failed > 0:
            logger.warning(f"Batch complete with errors: {updated} embedded, {failed} failed (moved to DLQ)")
        else:
            logger.info(f"Batch complete: {updated} rows embedded")

        return updated


def _open_connection() -> psycopg2.extensions.connection:
    """
    Open a new database connection with autocommit disabled.

    Separated from main() so reconnect logic can call it without
    duplicating the connection options.
    """
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    return conn


def _connection_is_alive(conn) -> bool:
    """
    Return True if the connection is usable, False if it is broken.

    Uses a cheap server-side no-op (SELECT 1) rather than relying on the
    psycopg2 closed/status flags, which only reflect *known* failures and
    miss silent TCP drops.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        # The SELECT opens an implicit transaction; roll it back so we do not
        # leave the connection in an idle-in-transaction state.
        conn.rollback()
        return True
    except Exception:
        return False


def main():
    """Main worker loop with connection resilience and circuit-breaker awareness."""
    global _shutdown

    if not DB_DSN:
        logger.error("DATABASE_URL not set")
        return 1

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set")
        return 1

    logger.info("Embedding worker 1536 starting")
    logger.info(f"  Model:      {EMBED_MODEL}")
    logger.info(f"  Dimensions: {EMBED_DIMS}")
    logger.info(f"  Version:    {EMBED_VERSION}")
    logger.info(f"  Batch size: {BATCH_SIZE}")

    # Pre-verify OpenAI client before touching the database.
    try:
        get_client()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return 1

    # -----------------------------------------------------------------------
    # Connection retry loop
    # Outer loop: re-establish the DB connection whenever it drops.
    # Inner loop: the normal batch-processing while loop.
    # -----------------------------------------------------------------------
    MAX_RECONNECT_ATTEMPTS = 10
    RECONNECT_BASE_SLEEP = 2.0   # seconds; doubles each failed attempt

    reconnect_attempt = 0
    total_processed = 0
    start_time = time.time()

    while not _shutdown:
        # -- Connect (or reconnect) ----------------------------------------
        conn = None
        try:
            logger.info("Connecting to database...")
            conn = _open_connection()
            reconnect_attempt = 0  # reset back-off on successful connect
        except psycopg2.OperationalError as e:
            reconnect_attempt += 1
            wait = min(RECONNECT_BASE_SLEEP * (2 ** (reconnect_attempt - 1)), 120)
            logger.error(
                f"DB connection failed (attempt {reconnect_attempt}/{MAX_RECONNECT_ATTEMPTS}): "
                f"{e} — retrying in {wait:.0f}s"
            )
            if reconnect_attempt >= MAX_RECONNECT_ATTEMPTS:
                logger.critical("Exceeded maximum reconnection attempts. Exiting.")
                return 1
            time.sleep(wait)
            continue  # retry outer loop

        # -- Log initial stats on fresh connection -------------------------
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                stats = get_embedding_stats(cur)
                logger.info(
                    f"Stats: total={stats['total']}, "
                    f"with_1536={stats['with_1536']}, "
                    f"needs={stats['needs_embedding']}, "
                    f"coverage={stats['coverage_pct']}%"
                )
        except Exception as e:
            logger.warning(f"Could not fetch initial stats: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        logger.info("Starting worker loop...")
        empty_batches = 0

        # -- Inner batch-processing loop -----------------------------------
        while not _shutdown:
            try:
                # Health-check: detect silent TCP drops before each batch.
                if not _connection_is_alive(conn):
                    logger.warning("Database connection lost (health check failed). Reconnecting...")
                    try:
                        conn.close()
                    except Exception:
                        pass
                    break  # exit inner loop → outer loop will reconnect

                # Process direct search_index embeddings (delta policy).
                processed = process_batch(conn)

                # Process queue-based entity indexing (handover_export, etc.).
                queue_processed = 0
                try:
                    queue_processed = process_queue_batch(conn)
                except psycopg2.ProgrammingError as qe:
                    # search_index_queue table may not exist yet; log and skip.
                    conn.rollback()
                    logger.debug(f"Queue processing skipped (table may not exist): {qe}")

                total_in_cycle = processed + queue_processed

                if total_in_cycle > 0:
                    total_processed += total_in_cycle
                    empty_batches = 0

                    if total_processed % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = total_processed / elapsed if elapsed > 0 else 0
                        logger.info(f"Progress: {total_processed} rows, {rate:.1f} rows/sec")

                    # Brief pause between active batches to avoid rate limits.
                    time.sleep(BATCH_SLEEP_SEC)
                else:
                    empty_batches += 1
                    # Exponential back-off when both queues are empty.
                    sleep_time = min(BATCH_SLEEP_SEC * (2 ** empty_batches), 30)
                    time.sleep(sleep_time)

            except CircuitBreakerOpenError as cbe:
                # OpenAI is down. Wait for the reset window before trying again;
                # no need to reconnect to the database.
                wait = max(0.0, _circuit_open_until - time.time())
                logger.warning(
                    f"Circuit breaker open — pausing embedding for {wait:.0f}s: {cbe}"
                )
                # Sleep in small increments so SIGTERM is still handled promptly.
                deadline = time.time() + wait
                while not _shutdown and time.time() < deadline:
                    time.sleep(min(5, deadline - time.time()))

            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                # Connection-level error (dropped socket, server restart, etc.).
                logger.error(f"Database connection error: {e} — will reconnect")
                try:
                    conn.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(ERROR_SLEEP_SEC)
                break  # exit inner loop → outer loop will reconnect

            except psycopg2.Error as e:
                # Other database errors (constraint violation, syntax, etc.) —
                # recoverable; roll back and keep running.
                logger.error(f"Database error: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                time.sleep(ERROR_SLEEP_SEC)

        # -- Clean-up after inner loop exits (shutdown or reconnect) -------
        if conn is not None:
            try:
                # Attempt final stats only on clean shutdown (not mid-reconnect).
                if _shutdown:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        stats = get_embedding_stats(cur)
                        elapsed = time.time() - start_time
                        logger.info(
                            f"Final stats: total={stats['total']}, "
                            f"with_1536={stats['with_1536']}, "
                            f"coverage={stats['coverage_pct']}%"
                        )
                        logger.info(f"Session: {total_processed} rows in {elapsed:.1f}s")
            except Exception as e:
                logger.warning(f"Could not fetch final stats: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
