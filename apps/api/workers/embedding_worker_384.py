#!/usr/bin/env python3
"""
!!! DEPRECATED - DO NOT USE IN PRODUCTION !!!

This worker was replaced by embedding_worker_1536.py (OpenAI text-embedding-3-small).
The canonical embedding model for F1 Search is 1536-dim OpenAI, not 384-dim bge-small.

See: docs/migrations/20260205_EMBEDDING_1536_MIGRATION.md

If you run this worker, it will NOT write to columns used by production RPCs.
The embedding_1536 column is the only vector column read by hyper_search.

=============================================================================
ORIGINAL DOCSTRING (preserved for reference):
=============================================================================

F1 Search - Embedding Worker (384-dim, bge-small-en-v1.5)

Processes search_index rows that need embeddings using local SentenceTransformer model.
Uses content_hash for delta policy - only re-embeds if content has changed.

GUARDRAILS:
- 384-dim embeddings for HNSW cosine similarity
- content_hash comparison prevents redundant API calls
- Batch processing with rate limiting
- Graceful shutdown on SIGINT

Usage:
    DATABASE_URL=postgresql://... python embedding_worker_384.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required)
    EMBED_MODEL - Model name (default: BAAI/bge-small-en-v1.5)
    EMBED_DIM - Embedding dimension (default: 384)
    BATCH_SIZE - Rows per batch (default: 50)
    BATCH_SLEEP_SEC - Sleep between batches (default: 0.1)

Content Hash Policy:
    - Only re-embed if content_hash differs from stored hash
    - Hash is SHA-256 of search_text (first 32 chars of hex digest)
    - Skip embedding if content_hash matches (delta policy)
"""

import os
import sys
import time
import logging
import math
import hashlib
import signal
from typing import List, Dict, Any, Optional, Tuple

import psycopg2
import psycopg2.extras

# Lazy-load sentence_transformers to avoid import time
_model = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DB_DSN = os.getenv("DATABASE_URL")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
BATCH_SLEEP_SEC = float(os.getenv("BATCH_SLEEP_SEC", "0.1"))
ERROR_SLEEP_SEC = float(os.getenv("ERROR_SLEEP_SEC", "1.0"))

# Graceful shutdown flag
_shutdown = False


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown
    logger.info("Received shutdown signal, finishing current batch...")
    _shutdown = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# SentenceTransformer Model (Lazy Load)
# ============================================================================

def get_model():
    """Lazy load SentenceTransformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBED_MODEL}")
            _model = SentenceTransformer(EMBED_MODEL)
            logger.info(f"Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            sys.exit(1)
    return _model


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


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts using local model.

    Returns list of normalized 384-dim vectors.
    """
    model = get_model()

    # Truncate texts if too long (model has token limits)
    max_chars = 8000
    truncated = [t[:max_chars] if len(t) > max_chars else t for t in texts]

    # Batch encode
    embeddings = model.encode(truncated, normalize_embeddings=True, show_progress_bar=False)

    # Convert numpy arrays to lists
    return [emb.tolist() for emb in embeddings]


# ============================================================================
# Database Operations
# ============================================================================

def fetch_batch_for_embedding(cur, batch_size: int) -> List[Dict[str, Any]]:
    """
    Fetch rows that need embedding (delta policy using content_hash).

    Returns rows where:
    1. embedding IS NULL (never embedded), OR
    2. content_hash differs from stored hash (content changed)

    Uses FOR UPDATE SKIP LOCKED for concurrent worker safety.
    """
    cur.execute("""
        SELECT id, object_type, object_id, search_text, content_hash
        FROM search_index
        WHERE (
            -- Never embedded
            embedding IS NULL
            -- OR content changed (hash mismatch)
            OR content_hash IS NULL
            OR content_hash != md5(search_text)::text
        )
        AND search_text IS NOT NULL
        AND search_text != ''
        ORDER BY updated_at DESC
        FOR UPDATE SKIP LOCKED
        LIMIT %s
    """, (batch_size,))
    return [dict(r) for r in cur.fetchall()]


def write_embeddings_batch(
    cur,
    rows: List[Dict[str, Any]],
    embeddings: List[List[float]]
) -> int:
    """
    Write embeddings to search_index in batch.

    Updates:
    - embedding: the 384-dim vector
    - embedding_model: model name for provenance
    - content_hash: hash of search_text to track changes
    - updated_at: current timestamp

    Returns count of rows updated.
    """
    if not rows or not embeddings:
        return 0

    updated = 0
    for row, vec in zip(rows, embeddings):
        # Compute content_hash from the text we embedded
        content_hash = compute_content_hash(row['search_text'])

        # Format as PostgreSQL vector literal
        vec_str = f"[{','.join(str(x) for x in vec)}]"

        cur.execute(f"""
            UPDATE search_index
            SET embedding = %s::vector({EMBED_DIM}),
                embedding_model = %s,
                content_hash = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (vec_str, EMBED_MODEL, content_hash, row['id']))
        updated += cur.rowcount

    return updated


def get_embedding_stats(cur) -> Dict[str, int]:
    """Get current embedding statistics."""
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(embedding) AS with_embedding,
            COUNT(*) - COUNT(embedding) AS without_embedding,
            COUNT(CASE WHEN embedding IS NOT NULL AND content_hash IS NULL THEN 1 END) AS missing_hash
        FROM search_index
        WHERE search_text IS NOT NULL AND search_text != ''
    """)
    row = cur.fetchone()
    return {
        'total': row[0],
        'with_embedding': row[1],
        'without_embedding': row[2],
        'missing_hash': row[3],
    }


# ============================================================================
# Main Loop
# ============================================================================

def process_batch(conn) -> int:
    """
    Process one batch of rows.

    Returns count of rows processed, or 0 if queue is empty.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # Fetch batch
        rows = fetch_batch_for_embedding(cur, BATCH_SIZE)

        if not rows:
            conn.commit()
            return 0

        logger.info(f"Processing batch of {len(rows)} rows...")

        try:
            # Extract texts
            texts = [r['search_text'] for r in rows]

            # Generate embeddings (local model)
            embeddings = embed_texts(texts)

            # Verify dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != EMBED_DIM:
                    logger.error(f"Bad embedding dimension {len(emb)} for row {rows[i]['id']}")
                    embeddings[i] = [0.0] * EMBED_DIM  # Fallback to zero vector

            # Write to database
            updated = write_embeddings_batch(cur, rows, embeddings)
            conn.commit()

            logger.info(f"Batch complete: {updated} rows updated")
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
        return

    logger.info(f"Embedding worker starting (model={EMBED_MODEL}, dim={EMBED_DIM})")
    logger.info(f"Batch size: {BATCH_SIZE}, sleep: {BATCH_SLEEP_SEC}s")

    # Pre-load model
    try:
        get_model()
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return

    logger.info("Connecting to database...")

    with psycopg2.connect(DB_DSN) as conn:
        conn.autocommit = False

        # Log initial stats
        with conn.cursor() as cur:
            stats = get_embedding_stats(cur)
            logger.info(f"Initial stats: total={stats['total']}, "
                       f"with_embedding={stats['with_embedding']}, "
                       f"without_embedding={stats['without_embedding']}")

        logger.info("Starting worker loop...")

        total_processed = 0
        empty_batches = 0

        while not _shutdown:
            try:
                processed = process_batch(conn)

                if processed > 0:
                    total_processed += processed
                    empty_batches = 0

                    if total_processed % 100 == 0:
                        logger.info(f"Progress: {total_processed} rows embedded")
                else:
                    empty_batches += 1
                    # Exponential backoff when queue is empty
                    sleep_time = min(BATCH_SLEEP_SEC * (2 ** empty_batches), 30)
                    time.sleep(sleep_time)

            except psycopg2.Error as e:
                logger.error(f"Database error: {e}")
                conn.rollback()
                time.sleep(ERROR_SLEEP_SEC)

        # Final stats
        with conn.cursor() as cur:
            stats = get_embedding_stats(cur)
            logger.info(f"Final stats: total={stats['total']}, "
                       f"with_embedding={stats['with_embedding']}, "
                       f"without_embedding={stats['without_embedding']}")

        logger.info(f"Shutting down. Total rows embedded: {total_processed}")


# ============================================================================
# CLI for one-shot embedding
# ============================================================================

def embed_all_missing():
    """One-shot: embed all rows missing embeddings."""
    global _shutdown

    if not DB_DSN:
        logger.error("DATABASE_URL not set")
        return

    logger.info("One-shot embedding: processing all missing embeddings...")

    # Pre-load model
    get_model()

    with psycopg2.connect(DB_DSN) as conn:
        conn.autocommit = False

        with conn.cursor() as cur:
            stats = get_embedding_stats(cur)
            logger.info(f"Initial: {stats['without_embedding']} rows need embedding")

        total = 0
        while not _shutdown:
            processed = process_batch(conn)
            if processed == 0:
                break
            total += processed

        with conn.cursor() as cur:
            stats = get_embedding_stats(cur)

        logger.info(f"Complete: {total} rows embedded, "
                   f"{stats['without_embedding']} remaining")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="F1 Search Embedding Worker (384-dim)")
    parser.add_argument("--one-shot", action="store_true",
                       help="Embed all missing rows and exit")
    args = parser.parse_args()

    if args.one_shot:
        embed_all_missing()
    else:
        main()
