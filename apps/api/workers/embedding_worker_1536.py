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

# OpenAI limits
MAX_CHARS_PER_TEXT = 8000  # Safe limit for embedding

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


def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts via OpenAI API.

    Returns list of normalized 1536-dim vectors.
    """
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
            return embeddings

        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) * 0.5
                logger.warning(f"OpenAI API error (attempt {attempt + 1}): {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                raise


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
# Main Processing
# ============================================================================

def process_batch(conn) -> int:
    """
    Process one batch of rows.

    Returns count of rows processed, or 0 if queue is empty.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        rows = fetch_batch_needing_embedding(cur, BATCH_SIZE)

        if not rows:
            conn.commit()
            return 0

        logger.info(f"Processing batch of {len(rows)} rows...")

        try:
            # Extract texts
            texts = [r['search_text'] for r in rows]

            # Generate embeddings via OpenAI
            embeddings = embed_texts_batch(texts)

            # Verify dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != EMBED_DIMS:
                    logger.error(f"Bad embedding dimension {len(emb)} for row {rows[i]['id']}")
                    embeddings[i] = [0.0] * EMBED_DIMS  # Fallback

            # Write to database
            updated = write_embeddings_batch(cur, rows, embeddings)
            conn.commit()

            logger.info(f"Batch complete: {updated} rows embedded")
            return updated

        except Exception as e:
            conn.rollback()
            logger.error(f"Batch error: {e}")
            return 0


def main():
    """Main worker loop."""
    global _shutdown

    if not DB_DSN:
        logger.error("DATABASE_URL not set")
        return 1

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set")
        return 1

    logger.info(f"Embedding worker 1536 starting")
    logger.info(f"  Model: {EMBED_MODEL}")
    logger.info(f"  Dimensions: {EMBED_DIMS}")
    logger.info(f"  Version: {EMBED_VERSION}")
    logger.info(f"  Batch size: {BATCH_SIZE}")

    # Pre-verify OpenAI client
    try:
        get_client()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return 1

    logger.info("Connecting to database...")

    with psycopg2.connect(DB_DSN) as conn:
        conn.autocommit = False

        # Log initial stats
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            stats = get_embedding_stats(cur)
            logger.info(f"Initial stats: total={stats['total']}, "
                       f"with_1536={stats['with_1536']}, "
                       f"needs={stats['needs_embedding']}, "
                       f"coverage={stats['coverage_pct']}%")

        logger.info("Starting worker loop...")

        total_processed = 0
        empty_batches = 0
        start_time = time.time()

        while not _shutdown:
            try:
                processed = process_batch(conn)

                if processed > 0:
                    total_processed += processed
                    empty_batches = 0

                    if total_processed % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = total_processed / elapsed if elapsed > 0 else 0
                        logger.info(f"Progress: {total_processed} rows, {rate:.1f} rows/sec")
                else:
                    empty_batches += 1
                    # Exponential backoff when queue is empty
                    sleep_time = min(BATCH_SLEEP_SEC * (2 ** empty_batches), 30)
                    time.sleep(sleep_time)

                # Brief sleep between batches to avoid rate limits
                if processed > 0:
                    time.sleep(BATCH_SLEEP_SEC)

            except psycopg2.Error as e:
                logger.error(f"Database error: {e}")
                conn.rollback()
                time.sleep(ERROR_SLEEP_SEC)

        # Final stats
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            stats = get_embedding_stats(cur)
            elapsed = time.time() - start_time
            logger.info(f"Final stats: total={stats['total']}, "
                       f"with_1536={stats['with_1536']}, "
                       f"coverage={stats['coverage_pct']}%")
            logger.info(f"Session: {total_processed} rows in {elapsed:.1f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
