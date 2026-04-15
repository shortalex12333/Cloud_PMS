#!/usr/bin/env python3
"""
Extraction Worker — downloads documents from Supabase Storage, extracts text,
writes chunks and enriched search_text, then sets embedding_status='pending'
for the embedding worker to pick up.

Pattern follows projection_worker.py: poll loop, batch claiming with
FOR UPDATE SKIP LOCKED, graceful shutdown, connection recovery.
"""

import hashlib
import json
import logging
import os
import re
import signal
import sys
import tempfile
import time

import psycopg2
import psycopg2.extras
import requests

# ── sys.path fix (same pattern as projection_worker.py) ─────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.extraction.extractor import extract_text

# ── Configuration from environment ──────────────────────────────────────
DB_DSN = os.environ.get("DATABASE_URL", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BATCH_SIZE = int(os.environ.get("EXTRACTION_BATCH_SIZE", "5"))
POLL_INTERVAL = int(os.environ.get("EXTRACTION_POLL_INTERVAL", "10"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
CHUNK_SIZE = 2000  # characters per chunk
DEFAULT_STORAGE_BUCKET = "documents"  # fallback when payload.bucket is missing
ORPHAN_TIMEOUT_MINUTES = 10

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("extraction_worker")

# ── Graceful shutdown ───────────────────────────────────────────────────
_shutdown = False


def _signal_handler(signum, frame):
    global _shutdown
    logger.info("Received signal %d, shutting down after current item...", signum)
    _shutdown = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ── Helpers ─────────────────────────────────────────────────────────────

def compute_content_hash(text: str) -> str:
    """SHA256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_search_text(
    filename: str,
    storage_path: str,
    doc_type: str = "",
    system_tag: str = "",
    extracted_text: str = "",
) -> str:
    """
    Build structured search_text from filename, path, and classification.
    Reuses the proven pattern from yacht-deployment indexer.py.
    """
    # Clean filename: strip extension, replace separators with spaces
    name_part = filename.rsplit(".", 1)[0] if "." in filename else filename
    clean_name = re.sub(r"[_\-\.]+", " ", name_part).strip()

    # Build directory breadcrumb from storage_path
    parts = storage_path.replace("\\", "/").strip("/").split("/")
    # Skip yacht_id (first segment) and filename (last segment)
    dir_parts = parts[1:-1] if len(parts) > 2 else []

    breadcrumb = ""
    if dir_parts:
        clean_dirs = []
        for d in dir_parts:
            stripped = re.sub(r"^\d+[_\-\.\s]*", "", d).strip()
            if stripped:
                clean_dirs.append(stripped)
        breadcrumb = " > ".join(clean_dirs)

    # Assemble: name | breadcrumb | doc_type | system_tag
    segments = [clean_name]
    if breadcrumb:
        segments.append(breadcrumb)
    if doc_type and doc_type != "general":
        segments.append(doc_type)
    if system_tag and system_tag != "general":
        segments.append(system_tag)

    search_text = " | ".join(segments)

    # Append extracted text
    if extracted_text:
        truncated = extracted_text[:4000].strip()
        if truncated:
            search_text = f"{search_text}\n\n{truncated}"

    return search_text


def download_from_storage(storage_path: str, dest_path: str, bucket: str = DEFAULT_STORAGE_BUCKET) -> bool:
    """
    Download a file from Supabase Storage to a local path.
    Returns True on success.

    The bucket is resolved per-row from the search_index payload (see process_row).
    Callers should pass the bucket recorded on the doc_metadata row so that lens
    uploads (bucket=documents), part labels (bucket=pms-label-pdfs), and any
    future domain-specific buckets all route correctly.
    """
    url = f"{SUPABASE_URL}/storage/v1/object/authenticated/{bucket}/{storage_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=120, stream=True)
        if resp.status_code != 200:
            logger.error(
                "Storage download failed %d for %s (bucket=%s): %s",
                resp.status_code, storage_path, bucket, resp.text[:200],
            )
            return False

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
        return True

    except requests.RequestException as exc:
        logger.error("Storage download error for %s: %s", storage_path, exc)
        return False


def atomic_chunk_replacement(cur, doc_id: str, yacht_id: str, chunks: list) -> bool:
    """
    Atomically replace all chunks for a document.
    DELETE old → INSERT new in one transaction.
    Pattern from projection_worker.py:484-521.

    NOTE 2026-04-15 — `search_document_chunks.tsv` is a `GENERATED ALWAYS AS
    (to_tsvector('english', COALESCE(content, ''))) STORED` column.
    Generated columns cannot be written to directly — Postgres rejects
    every INSERT that names them with `GeneratedAlways: cannot insert a
    non-DEFAULT value into column "tsv"`.

    Previous version of this function explicitly wrote `to_tsvector(...)`
    into the `tsv` column, which silently failed for every chunk in
    production. The exception was swallowed by the caller's non-fatal
    handler, leaving search_document_chunks empty for every uploaded
    document. Discovered via the diag patch in PR #541.

    Fix: omit `tsv` from the INSERT column list. Postgres will populate
    it from `content` automatically.
    """
    if not chunks:
        return False

    # Delete old chunks
    cur.execute(
        "DELETE FROM search_document_chunks WHERE document_id = %s",
        (doc_id,),
    )

    # Insert new chunks — DO NOT write to `tsv` (generated column).
    for chunk in chunks:
        content_hash = compute_content_hash(chunk["content"])
        cur.execute(
            """
            INSERT INTO search_document_chunks
                (document_id, yacht_id, chunk_index, content, content_hash)
            VALUES
                (%s, %s, %s, %s, %s)
            """,
            (
                doc_id,
                yacht_id,
                chunk["chunk_index"],
                chunk["content"],
                content_hash,
            ),
        )

    return True


# ── Main loop ───────────────────────────────────────────────────────────

def reset_orphans(conn):
    """Reset rows stuck in 'extracting' for >10 minutes (crash recovery)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE search_index
            SET embedding_status = 'pending_extraction', updated_at = now()
            WHERE embedding_status = 'extracting'
              AND updated_at < now() - interval '%s minutes'
            """,
            (ORPHAN_TIMEOUT_MINUTES,),
        )
        count = cur.rowcount
        conn.commit()
        if count:
            logger.info("Reset %d orphaned 'extracting' rows to 'pending_extraction'", count)


def claim_batch(conn) -> list:
    """Claim a batch of rows for extraction using FOR UPDATE SKIP LOCKED."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, object_type, object_id, yacht_id, payload
            FROM search_index
            WHERE embedding_status = 'pending_extraction'
            ORDER BY updated_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
            """,
            (BATCH_SIZE,),
        )
        rows = cur.fetchall()

        if rows:
            ids = [r["id"] for r in rows]
            cur.execute(
                """
                UPDATE search_index
                SET embedding_status = 'extracting', updated_at = now()
                WHERE id = ANY(%s)
                """,
                (ids,),
            )
            conn.commit()

        return rows


def process_row(conn, row: dict) -> bool:
    """Process a single extraction row. Returns True on success."""
    row_id = row["id"]
    object_id = row["object_id"]
    yacht_id = row["yacht_id"]
    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")

    storage_path = payload.get("storage_path", "")
    filename = payload.get("filename", "")
    doc_type = payload.get("doc_type", "")
    system_tag = payload.get("system_tag", "")
    bucket = payload.get("bucket") or DEFAULT_STORAGE_BUCKET

    if not storage_path:
        logger.warning("Row %s has no storage_path in payload, marking pending", row_id)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE search_index SET embedding_status = 'pending', updated_at = now() WHERE id = %s",
                (row_id,),
            )
            conn.commit()
        return True

    logger.info("Extracting: %s (object_id=%s)", filename or storage_path, object_id)

    # ------------------------------------------------------------------
    # Diagnostic block — captures everything the worker observes during
    # extraction and writes it into search_index.payload.extract_diag so
    # the post-deploy investigation can read it from the DB without
    # needing Render shell or log access.
    # ------------------------------------------------------------------
    from datetime import datetime as _dt
    diag = {
        "ts": _dt.utcnow().isoformat(),
        "bucket": bucket,
        "filename": filename,
        "ext": os.path.splitext(filename)[1].lower() if filename else "",
    }

    # Download to temp file
    suffix = os.path.splitext(filename)[1] if filename else ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp_path = tmp.name

        if not download_from_storage(storage_path, tmp_path, bucket=bucket):
            diag["download_ok"] = False
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE search_index
                    SET embedding_status = 'extraction_failed',
                        payload = COALESCE(payload, '{}'::jsonb)
                                  || jsonb_build_object('extract_diag', %s::jsonb),
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (json.dumps(diag), row_id),
                )
                conn.commit()
            return False

        diag["download_ok"] = True

        # Capture file diagnostics — what does the worker actually have on disk?
        try:
            file_size = os.path.getsize(tmp_path)
            diag["file_size"] = file_size
            with open(tmp_path, "rb") as fh:
                head = fh.read(32)
            diag["file_head_hex"] = head.hex()
            diag["file_head_ascii"] = "".join(
                chr(b) if 32 <= b < 127 else "." for b in head
            )
        except Exception as e:
            diag["file_inspect_error"] = f"{type(e).__name__}: {e}"

        # Try the production extract_text + capture what it returned.
        try:
            extracted_text = extract_text(tmp_path)
            diag["extract_text_len"] = len(extracted_text or "")
            diag["extract_text_preview"] = (extracted_text or "")[:120]
        except Exception as e:
            extracted_text = ""
            diag["extract_text_exception"] = f"{type(e).__name__}: {e}"

        # If PDF: also try fitz directly to bypass extract_text wrapper +
        # capture per-page byte counts. Isolates whether the bug is in
        # _extract_pdf or in fitz itself in the Render container.
        if diag["ext"] == ".pdf":
            try:
                import fitz  # pymupdf
                diag["fitz_available"] = True
                doc = fitz.open(tmp_path)
                diag["fitz_page_count"] = len(doc)
                page_lens = []
                for i in range(min(len(doc), 5)):
                    try:
                        t = doc[i].get_text("text") or ""
                    except Exception as pe:
                        t = ""
                        diag.setdefault("fitz_page_errors", []).append(
                            f"p{i}:{type(pe).__name__}:{pe}"
                        )
                    page_lens.append(len(t))
                doc.close()
                diag["fitz_page_text_lens"] = page_lens
                diag["fitz_total_chars"] = sum(page_lens)
            except ImportError as e:
                diag["fitz_available"] = False
                diag["fitz_import_error"] = str(e)
            except Exception as e:
                diag["fitz_exception"] = f"{type(e).__name__}: {e}"

    # Build enriched search_text
    enriched = build_search_text(
        filename=filename,
        storage_path=storage_path,
        doc_type=doc_type,
        system_tag=system_tag,
        extracted_text=extracted_text,
    )
    diag["enriched_len"] = len(enriched)

    with conn.cursor() as cur:
        # Write chunks if we have extracted text
        chunks_written = 0
        if extracted_text:
            chunks = []
            clean = extracted_text.strip()
            for i in range(0, len(clean), CHUNK_SIZE):
                segment = clean[i : i + CHUNK_SIZE].strip()
                if segment:
                    chunks.append({"chunk_index": len(chunks), "content": segment})

            if chunks:
                try:
                    atomic_chunk_replacement(cur, object_id, yacht_id, chunks)
                    chunks_written = len(chunks)
                    logger.info("Wrote %d chunks for %s", len(chunks), filename or object_id)
                except Exception as exc:
                    logger.warning(
                        "Chunk write failed for %s: %s (non-fatal)", object_id, exc
                    )
                    conn.rollback()
                    diag["chunk_write_exception"] = f"{type(exc).__name__}: {exc}"
        diag["chunks_written"] = chunks_written

        # Update search_index: enriched search_text + status → pending + diag
        cur.execute(
            """
            UPDATE search_index
            SET search_text = %s,
                embedding_status = 'pending',
                payload = COALESCE(payload, '{}'::jsonb)
                          || jsonb_build_object('extract_diag', %s::jsonb),
                updated_at = now()
            WHERE id = %s
            """,
            (enriched, json.dumps(diag), row_id),
        )
        conn.commit()

    logger.info(
        "Extracted: %s → text=%d enriched=%d fitz=%s",
        filename or storage_path,
        len(extracted_text),
        len(enriched),
        diag.get("fitz_total_chars", "n/a"),
    )
    return True


def run_worker():
    """Main worker loop with connection recovery."""
    if not DB_DSN:
        logger.error("DATABASE_URL not set — exiting")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — exiting")
        sys.exit(1)

    logger.info(
        "Extraction worker started — batch_size=%d, poll_interval=%ds",
        BATCH_SIZE, POLL_INTERVAL,
    )

    reconnect_delay = 5
    max_reconnect_attempts = 10
    reconnect_attempts = 0
    conn = None

    while not _shutdown:
        try:
            # Connect / reconnect
            if conn is None or conn.closed:
                logger.info("Connecting to database...")
                conn = psycopg2.connect(DB_DSN)
                conn.autocommit = False
                reconnect_attempts = 0
                reconnect_delay = 5
                logger.info("Connected to database")

                # Reset orphaned rows on startup/reconnect
                reset_orphans(conn)

            # Claim batch
            rows = claim_batch(conn)

            if not rows:
                # Nothing to do — sleep
                for _ in range(POLL_INTERVAL):
                    if _shutdown:
                        break
                    time.sleep(1)
                continue

            # Process each row
            for row in rows:
                if _shutdown:
                    break
                try:
                    process_row(conn, row)
                except Exception as exc:
                    logger.error(
                        "Error processing row %s: %s", row.get("id"), exc, exc_info=True
                    )
                    try:
                        conn.rollback()
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE search_index
                                SET embedding_status = 'extraction_failed',
                                    updated_at = now()
                                WHERE id = %s
                                """,
                                (row["id"],),
                            )
                            conn.commit()
                    except Exception:
                        logger.error("Failed to mark row %s as extraction_failed", row.get("id"))

        except psycopg2.OperationalError as e:
            reconnect_attempts += 1
            logger.error(
                "Connection lost: %s (attempt %d/%d)",
                e, reconnect_attempts, max_reconnect_attempts,
            )

            if reconnect_attempts >= max_reconnect_attempts:
                logger.error("Max reconnect attempts reached, exiting")
                break

            logger.info("Reconnecting in %ds...", reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 120)
            conn = None

        except Exception as e:
            logger.error("Unexpected error: %s", e, exc_info=True)
            time.sleep(5)

    # Cleanup
    if conn and not conn.closed:
        conn.close()
    logger.info("Extraction worker stopped")


if __name__ == "__main__":
    run_worker()
