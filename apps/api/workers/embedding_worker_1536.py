#!/usr/bin/env python3
"""
F1 Search - Embedding Worker (1536-dim, OpenAI text-embedding-3-small)

Generates 1536-dim embeddings for search_index rows using OpenAI API.
Writes to embedding_1536 column with delta tracking via content_hash.

ARCHITECTURE:
- Claims jobs from embedding_jobs table (queue-driven)
- Fetches search_text from search_index for claimed jobs
- Writes embeddings back to search_index
- Updates job status (done/failed) in embedding_jobs

GUARDRAILS:
- 1536-dim embeddings for HNSW cosine similarity
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
    WORKER_ID - Unique worker identifier (default: auto-generated)
"""

from __future__ import annotations

import os
import sys
import time
import logging
import math
import hashlib
import signal
import uuid
from typing import List, Dict, Any

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
WORKER_ID = os.getenv("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")

# OpenAI limits
MAX_CHARS_PER_TEXT = 8000  # Safe limit for embedding
MAX_EMBEDDING_CHARS = 24000  # ~8000 tokens * 3 chars/token safety margin for large scraped content

# Circuit breaker configuration (prevents death spiral during OpenAI outages)
CIRCUIT_BREAKER_THRESHOLD = 5      # Consecutive failures before circuit opens
CIRCUIT_BREAKER_RESET_SEC = 60     # Seconds to wait before trying again
MAX_RETRY_COUNT = 3                # Max retries per row before marking as DLQ

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


def truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """
    Truncate text to max_chars while respecting word boundaries.

    If the text exceeds max_chars, finds the last space before the limit
    and truncates there to avoid slicing words in half.
    """
    if not text or len(text) <= max_chars:
        return text

    # Find the last space before the character limit
    last_space = text.rfind(' ', 0, max_chars)

    if last_space > 0:
        return text[:last_space]

    # No space found - fall back to hard truncation
    return text[:max_chars]


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
    Truncates text to MAX_EMBEDDING_CHARS before API call to prevent 400 errors.

    Returns list of normalized 1536-dim vectors.
    Raises CircuitBreakerOpen if circuit is open.
    """
    # Check circuit breaker BEFORE attempting API call
    if check_circuit_breaker():
        raise CircuitBreakerOpenError(f"Circuit breaker open until {_circuit_open_until}")

    client = get_client()

    # Log and truncate large texts BEFORE sending to OpenAI to prevent 400 errors
    for i, t in enumerate(texts):
        if t and len(t) > MAX_EMBEDDING_CHARS:
            logger.warning(f"Truncating text from {len(t)} to {MAX_EMBEDDING_CHARS} chars")

    # Truncate to prevent API errors on large scraped content
    safe_texts = [t[:MAX_EMBEDDING_CHARS] if t else "" for t in texts]

    # Additional safety truncation (legacy limit) - respects word boundaries
    truncated = [truncate_at_word_boundary(t, MAX_CHARS_PER_TEXT) for t in safe_texts]

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
                # CRITICAL FIX: Rate-limit on final attempt must record circuit failure
                if attempt == max_retries - 1:
                    record_circuit_failure(e)
                    logger.error(f"OpenAI rate limit exhausted after {max_retries} attempts: {e}")
                    raise
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
# Database Operations - Job Queue
# ============================================================================

def claim_embedding_jobs(cur, batch_size: int, worker_id: str) -> List[Dict]:
    """
    Claim batch from embedding_jobs WHERE status='queued'.

    Uses FOR UPDATE SKIP LOCKED to allow concurrent workers.
    Orders by priority DESC (higher priority first), then queued_at ASC (oldest first).

    Returns list of dicts with job_id, object_type, object_id, yacht_id.
    """
    cur.execute("""
        WITH claimed AS (
            SELECT id, object_type, object_id, yacht_id
            FROM embedding_jobs
            WHERE status = 'queued'
            ORDER BY priority DESC NULLS LAST, queued_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        UPDATE embedding_jobs ej
        SET status = 'processing',
            started_at = NOW(),
            worker_id = %s,
            attempts = COALESCE(attempts, 0) + 1
        FROM claimed c
        WHERE ej.id = c.id
        RETURNING ej.id AS job_id, ej.object_type, ej.object_id, ej.yacht_id
    """, (batch_size, worker_id))
    return [dict(row) for row in cur.fetchall()]


def fetch_search_text_for_jobs(cur, jobs: List[Dict]) -> List[Dict]:
    """
    Fetch search_text from search_index for claimed jobs.

    Returns list of dicts with id, object_type, object_id, search_text, content_hash, job_id.
    Jobs without matching search_index rows are excluded from results.

    NOTE: search_text is concatenated with learned_keywords to ensure embeddings
    include yacht-specific vocabulary learned from the nightly feedback loop.
    This implements LAW 8 (Strict Linguistic Isolation) at the embedding level.
    """
    if not jobs:
        return []

    # Build VALUES clause for proper tuple matching
    # Concatenate search_text with learned_keywords to include yacht-specific vocabulary
    # in the embedding. The tsv (tsvector) column already does this for FTS, but
    # vector embeddings need explicit concatenation here.
    values_clause = ", ".join(
        cur.mogrify("(%s, %s)", (j['object_type'], str(j['object_id']))).decode()
        for j in jobs
    )
    cur.execute(f"""
        SELECT id, object_type, object_id,
               COALESCE(search_text, '') || ' ' || COALESCE(learned_keywords, '') AS search_text,
               content_hash
        FROM search_index
        WHERE (object_type, object_id::text) IN ({values_clause})
    """)

    rows = {(r['object_type'], str(r['object_id'])): dict(r) for r in cur.fetchall()}

    # Merge job_id into results
    for job in jobs:
        key = (job['object_type'], str(job['object_id']))
        if key in rows:
            rows[key]['job_id'] = job['job_id']

    return list(rows.values())


def complete_job(cur, job_id: str):
    """Mark an embedding job as successfully completed."""
    cur.execute("""
        UPDATE embedding_jobs
        SET status = 'done', completed_at = NOW(), last_error = NULL
        WHERE id = %s
    """, (job_id,))


def fail_job(cur, job_id: str, error: str):
    """Mark an embedding job as failed with error message."""
    cur.execute("""
        UPDATE embedding_jobs
        SET status = 'failed', completed_at = NOW(), last_error = %s
        WHERE id = %s
    """, (error[:2000], job_id))


# ============================================================================
# Database Operations - Search Index
# ============================================================================

def write_embeddings_batch(
    cur,
    rows: List[Dict[str, Any]],
    embeddings: List[List[float]]
) -> int:
    """
    Write 1536-dim embeddings to search_index using bulk UPDATE.

    Uses psycopg2.extras.execute_values for a single high-performance
    bulk update instead of N separate UPDATE statements.

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

    # Build values list for bulk update
    values = []
    for row, vec in zip(rows, embeddings):
        new_hash = compute_content_hash(row['search_text'])
        vec_str = f"[{','.join(str(x) for x in vec)}]"
        values.append((row['id'], vec_str, EMBED_MODEL, EMBED_VERSION, new_hash))

    # Bulk update using execute_values with UPDATE FROM pattern
    psycopg2.extras.execute_values(
        cur,
        f"""
        UPDATE search_index AS si
        SET embedding_1536 = v.vec::vector({EMBED_DIMS}),
            embedding_model = v.model,
            embedding_version = v.version,
            embedding_hash = v.hash,
            content_hash = v.hash,
            updated_at = NOW()
        FROM (VALUES %s) AS v(id, vec, model, version, hash)
        WHERE si.id = v.id::uuid
        """,
        values,
        template="(%s, %s, %s, %s, %s)"
    )

    return len(values)


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


def get_job_queue_stats(cur) -> Dict[str, Any]:
    """Get embedding_jobs queue statistics."""
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'queued') AS queued,
            COUNT(*) FILTER (WHERE status = 'processing') AS processing,
            COUNT(*) FILTER (WHERE status = 'done') AS done,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed
        FROM embedding_jobs
    """)
    row = cur.fetchone()
    return {
        'queued': row['queued'] or 0,
        'processing': row['processing'] or 0,
        'done': row['done'] or 0,
        'failed': row['failed'] or 0,
    }


# ============================================================================
# Main Processing
# ============================================================================

def process_batch(conn) -> int:
    """
    Process one batch of jobs from embedding_jobs queue.

    HARDENED: Per-row error isolation prevents one bad row from crashing batch.

    Returns count of rows processed, or 0 if queue is empty.
    """
    # Check circuit breaker before even fetching jobs
    if check_circuit_breaker():
        logger.warning("Circuit breaker open, skipping batch")
        time.sleep(CIRCUIT_BREAKER_RESET_SEC / 2)  # Wait before next attempt
        return 0

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Claim jobs from the queue
        jobs = claim_embedding_jobs(cur, BATCH_SIZE, WORKER_ID)
        conn.commit()

        if not jobs:
            return 0

        logger.info(f"Claimed {len(jobs)} jobs from queue...")

        # Fetch search_text for claimed jobs
        rows = fetch_search_text_for_jobs(cur, jobs)

        if not rows:
            # Jobs claimed but no matching search_index rows - mark as failed
            for job in jobs:
                fail_job(cur, job['job_id'], "No matching search_index row found")
            conn.commit()
            logger.warning(f"No search_index rows found for {len(jobs)} claimed jobs")
            return len(jobs)

        logger.info(f"Fetched search_text for {len(rows)} rows...")

        # Build lookup for jobs without search_index rows
        rows_by_key = {(r['object_type'], str(r['object_id'])): r for r in rows}

        # HARDENED: Process rows individually to isolate failures
        updated = 0
        failed = 0

        for job in jobs:
            job_id = job['job_id']
            key = (job['object_type'], str(job['object_id']))
            row = rows_by_key.get(key)

            if not row:
                # No search_index row for this job
                fail_job(cur, job_id, "No matching search_index row found")
                conn.commit()
                failed += 1
                continue

            try:
                # Extract text for single row
                text = row.get('search_text', '')
                if not text:
                    fail_job(cur, job_id, "Empty search_text")
                    conn.commit()
                    logger.warning(f"Job {job_id} has empty search_text, marking failed")
                    failed += 1
                    continue

                # Generate embedding for single row
                embeddings = embed_texts_batch([text])

                if not embeddings or len(embeddings) == 0:
                    raise ValueError("No embedding returned")

                emb = embeddings[0]

                # Verify dimension
                if len(emb) != EMBED_DIMS:
                    logger.error(f"Bad embedding dimension {len(emb)} for job {job_id}")
                    emb = [0.0] * EMBED_DIMS  # Fallback

                # Write single row to search_index
                row_updated = write_embeddings_batch(cur, [row], [emb])

                # Mark job as complete
                complete_job(cur, job_id)
                conn.commit()
                updated += row_updated

            except CircuitBreakerOpenError as cbe:
                # Circuit breaker opened mid-batch - stop processing
                # Don't mark as failed - job will be retried when circuit closes
                logger.warning(f"Circuit breaker opened during batch: {cbe}")
                conn.rollback()
                break

            except Exception as e:
                # HARDENED: Isolate failure to this job only
                conn.rollback()
                failed += 1
                error_msg = str(e)[:2000]
                logger.error(f"Failed to embed job {job_id}: {e}")

                # Mark job as failed
                fail_job(cur, job_id, error_msg)
                conn.commit()

        if failed > 0:
            logger.warning(f"Batch complete with errors: {updated} embedded, {failed} failed")
        else:
            logger.info(f"Batch complete: {updated} rows embedded")

        return updated + failed


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
    logger.info(f"  Worker ID:  {WORKER_ID}")
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
                    f"Search index stats: total={stats['total']}, "
                    f"with_1536={stats['with_1536']}, "
                    f"needs={stats['needs_embedding']}, "
                    f"coverage={stats['coverage_pct']}%"
                )

                # Also log job queue stats
                try:
                    queue_stats = get_job_queue_stats(cur)
                    logger.info(
                        f"Job queue stats: queued={queue_stats['queued']}, "
                        f"processing={queue_stats['processing']}, "
                        f"done={queue_stats['done']}, "
                        f"failed={queue_stats['failed']}"
                    )
                except Exception as qe:
                    logger.debug(f"Could not fetch queue stats (table may not exist): {qe}")
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

                # Process jobs from embedding_jobs queue
                processed = process_batch(conn)

                if processed > 0:
                    total_processed += processed
                    empty_batches = 0

                    if total_processed % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = total_processed / elapsed if elapsed > 0 else 0
                        logger.info(f"Progress: {total_processed} rows, {rate:.1f} rows/sec")

                    # Brief pause between active batches to avoid rate limits.
                    time.sleep(BATCH_SLEEP_SEC)
                else:
                    empty_batches += 1
                    # Exponential back-off when queue is empty.
                    # Cap empty_batches to prevent overflow (2**10 = 1024, well under 30s cap)
                    capped_batches = min(empty_batches, 10)
                    sleep_time = min(BATCH_SLEEP_SEC * (2 ** capped_batches), 30)
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
