#!/usr/bin/env python3
"""
F1 Search - Embedding Worker (OpenAI)

Polls embedding_jobs table, generates 1536-dim embeddings using OpenAI API,
writes to search_index.embedding.

GUARDRAILS:
- Use service role in private worker environment only
- Normalize embeddings (cosine sim expects normalization)
- Rate-limit API calls to avoid billing spikes
- Don't spawn >2 workers until pool is tuned

Usage:
    DATABASE_URL=postgresql://... OPENAI_API_KEY=sk-... python embedding_worker.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required)
    OPENAI_API_KEY - OpenAI API key (required)
    EMBED_MODEL - Model name (default: text-embedding-3-small)
    EMBED_DIM - Embedding dimension (default: 1536)
    EMBED_PROVIDER - Provider (default: openai)
"""

import os
import time
import logging
import math

import psycopg2
import psycopg2.extras
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DB_DSN = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small").replace("openai/", "")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))
BATCH_SLEEP_SEC = float(os.getenv("BATCH_SLEEP_SEC", "0.5"))
ERROR_SLEEP_SEC = float(os.getenv("ERROR_SLEEP_SEC", "0.2"))

# ============================================================================
# OpenAI Client (lazy load)
# ============================================================================

_client = None


def get_client() -> OpenAI:
    """Lazy load OpenAI client."""
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        logger.info(f"Initializing OpenAI client for model: {EMBED_MODEL}")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def normalize_vector(vec: list[float]) -> list[float]:
    """Normalize vector to unit length for cosine similarity."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def embed_text(text: str) -> list[float]:
    """
    Generate embedding using OpenAI API.

    Returns normalized 1536-dim vector.
    """
    client = get_client()

    # Truncate text if too long (OpenAI has token limits)
    max_chars = 8000  # Safe limit for text-embedding-3-small
    if len(text) > max_chars:
        text = text[:max_chars]

    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
        dimensions=EMBED_DIM
    )

    vec = response.data[0].embedding
    # Normalize for cosine similarity
    return normalize_vector(vec)


# ============================================================================
# Database Operations
# ============================================================================

def fetch_job(cur):
    """
    Claim one queued job atomically.

    Uses FOR UPDATE SKIP LOCKED for concurrent worker safety.
    """
    cur.execute("""
        WITH j AS (
            SELECT id, object_type, object_id
            FROM embedding_jobs
            WHERE status = 'queued'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE embedding_jobs ej
        SET status = 'working', updated_at = now()
        FROM j
        WHERE ej.id = j.id
        RETURNING ej.id, ej.object_type, ej.object_id
    """)
    return cur.fetchone()


def load_text(cur, object_type, object_id):
    """Load search_text from search_index."""
    cur.execute("""
        SELECT search_text
        FROM search_index
        WHERE object_type = %s AND object_id = %s
    """, (object_type, str(object_id)))
    row = cur.fetchone()
    return row[0] if row else None


def write_embedding(cur, object_type, object_id, vec):
    """
    Write embedding to search_index.

    vec must be python list[float] length 1536.
    """
    # Format as PostgreSQL vector literal
    vec_str = f"[{','.join(str(x) for x in vec)}]"
    cur.execute(f"""
        UPDATE search_index
        SET embedding = %s::vector({EMBED_DIM}),
            embedding_version = 2,
            updated_at = now()
        WHERE object_type = %s AND object_id = %s
    """, (vec_str, object_type, str(object_id)))


def mark(cur, job_id, status, err=None):
    """Update job status."""
    cur.execute("""
        UPDATE embedding_jobs
        SET status = %s,
            attempt = CASE WHEN %s = 'failed' THEN attempt + 1 ELSE attempt END,
            last_error = %s,
            updated_at = now()
        WHERE id = %s
    """, (status, status, err, job_id))


# ============================================================================
# Main Loop
# ============================================================================

def process_one(conn) -> bool:
    """
    Process one job.

    Returns True if a job was processed, False if queue is empty.
    """
    with conn.cursor() as cur:
        job = fetch_job(cur)
        if not job:
            conn.commit()
            return False

        job_id, obj_type, obj_id = job
        logger.debug(f"Processing job {job_id}: {obj_type}/{obj_id}")

        try:
            # Load text
            text = load_text(cur, obj_type, obj_id)
            if not text:
                mark(cur, job_id, 'failed', 'missing search_text')
                conn.commit()
                logger.warning(f"Job {job_id}: missing search_text for {obj_type}/{obj_id}")
                return True

            # Generate embedding via OpenAI
            vec = embed_text(text)

            if len(vec) != EMBED_DIM:
                mark(cur, job_id, 'failed', f'bad dim {len(vec)}')
                conn.commit()
                logger.error(f"Job {job_id}: bad dimension {len(vec)}, expected {EMBED_DIM}")
                return True

            # Write embedding
            write_embedding(cur, obj_type, obj_id, vec)
            mark(cur, job_id, 'done', None)
            conn.commit()

            logger.info(f"Job {job_id}: embedded {obj_type}/{obj_id}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Job {job_id}: error - {e}")
            with conn.cursor() as cur2:
                mark(cur2, job_id, 'failed', str(e)[:500])
                conn.commit()
            return True


def main():
    """Main worker loop."""
    if not DB_DSN:
        logger.error("DATABASE_URL not set")
        return

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set")
        return

    logger.info(f"Embedding worker starting (model={EMBED_MODEL}, dim={EMBED_DIM})")
    logger.info("Connecting to database...")

    with psycopg2.connect(DB_DSN) as conn:
        conn.autocommit = False
        logger.info("Connected. Starting worker loop...")

        jobs_processed = 0
        while True:
            try:
                if process_one(conn):
                    jobs_processed += 1
                    if jobs_processed % 10 == 0:
                        logger.info(f"Progress: {jobs_processed} jobs processed")
                else:
                    # Queue empty, sleep
                    time.sleep(BATCH_SLEEP_SEC)

            except psycopg2.Error as e:
                logger.error(f"Database error: {e}")
                conn.rollback()
                time.sleep(ERROR_SLEEP_SEC)

            except KeyboardInterrupt:
                logger.info(f"Shutting down. Total jobs processed: {jobs_processed}")
                break


if __name__ == "__main__":
    main()
