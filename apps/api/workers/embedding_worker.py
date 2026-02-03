#!/usr/bin/env python3
"""
F1 Search - Embedding Worker

Polls embedding_jobs table, generates 384-dim embeddings using local model,
writes to search_index.embedding.

GUARDRAILS:
- Use service role in private worker environment only
- Normalize embeddings (cosine sim expects normalization)
- Don't spawn >2 workers until pool is tuned
- Rate-limit if CPU spikes

Usage:
    DATABASE_URL=postgresql://... python embedding_worker.py
"""

import os
import time
import logging

import psycopg2
import psycopg2.extras
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DB_DSN = os.getenv("DATABASE_URL")  # Use service role; never ship in code
MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")  # 384 dims
BATCH_SLEEP_SEC = float(os.getenv("BATCH_SLEEP_SEC", "0.5"))
ERROR_SLEEP_SEC = float(os.getenv("ERROR_SLEEP_SEC", "0.2"))

# ============================================================================
# Model (lazy load)
# ============================================================================

_model = None


def get_model() -> SentenceTransformer:
    """Lazy load embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


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

    vec must be python list[float] length 384.
    """
    # Format as PostgreSQL vector literal
    vec_str = f"[{','.join(str(x) for x in vec)}]"
    cur.execute("""
        UPDATE search_index
        SET embedding = %s::vector(384),
            embedding_version = 1,
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

            # Generate embedding
            model = get_model()
            vec = model.encode([text], normalize_embeddings=True)[0].tolist()

            if len(vec) != 384:
                mark(cur, job_id, 'failed', f'bad dim {len(vec)}')
                conn.commit()
                logger.error(f"Job {job_id}: bad dimension {len(vec)}, expected 384")
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
