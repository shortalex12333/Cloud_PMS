#!/usr/bin/env python3
"""
F1 Search - Projection Worker (Production-Grade, Render-Ready)

Processes search_index rows with pending/processing embedding_status and maintains
search_index + search_document_chunks. Single writer pattern for consistent indexing
with Hard Tiers support.

Key Features:
- Atomic chunk replacement for documents (DELETE → INSERT in one transaction)
- Chunk keyword aggregation into search_text for fuzzy trigram recall
- Content hash for delta threshold embedding policy
- Source version guard for idempotent upserts
- pg_notify cache invalidation on successful changes
- Hard Tiers: recency_ts and ident_norm population per projection.yaml

GUARDRAILS:
- Use Supavisor transaction pooler (port 6543)
- Gate with F1_PROJECTION_WORKER_ENABLED=true
- Start with low concurrency (1-2 workers)
- Never leave zero chunks on failure
- Graceful shutdown on SIGINT/SIGTERM

Usage:
    F1_PROJECTION_WORKER_ENABLED=true DATABASE_URL=postgresql://... python projection_worker.py

Environment:
    DATABASE_URL - PostgreSQL connection string (required, use port 6543)
    F1_PROJECTION_WORKER_ENABLED - Set to 'true' to enable (default: false)
    PROJECTION_BATCH_SIZE - Batch size for queue claims (default: 50)
    PROJECTION_POLL_INTERVAL - Seconds to wait when queue empty (default: 5)
    PROJECTION_MAX_SEARCH_TEXT - Max chars for search_text (default: 12000)
    PROJECTION_CHUNK_KEYWORDS - Top-K chunk keywords to aggregate (default: 20)

See: apps/api/docs/PROJECTION_WORKER_RUNBOOK.md
"""

import os
import sys
import time
import json
import re
import hashlib
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from collections import Counter
from decimal import Decimal

import yaml
import psycopg2
import psycopg2.extras

# Maritime entity extraction for intelligent keyword extraction
try:
    from extraction.entity_extractor import get_extractor
    ENTITY_EXTRACTOR_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTOR_AVAILABLE = False

# Graceful shutdown flag
_shutdown = False


def signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown
    logging.getLogger('projection_worker').info("Received shutdown signal, finishing current batch...")
    _shutdown = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger('projection_worker')

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class Config:
    """Worker configuration from environment."""
    enabled: bool = False
    db_dsn: str = ""
    batch_size: int = 50
    poll_interval: float = 5.0
    max_search_text: int = 12000
    chunk_keywords_top_k: int = 20
    pg_notify_channel: str = "f1_cache_invalidate"

    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            enabled=os.getenv("F1_PROJECTION_WORKER_ENABLED", "false").lower() == "true",
            db_dsn=os.getenv("DATABASE_URL", ""),
            batch_size=int(os.getenv("PROJECTION_BATCH_SIZE", "50")),
            poll_interval=float(os.getenv("PROJECTION_POLL_INTERVAL", "5")),
            max_search_text=int(os.getenv("PROJECTION_MAX_SEARCH_TEXT", "12000")),
            chunk_keywords_top_k=int(os.getenv("PROJECTION_CHUNK_KEYWORDS", "20")),
        )

CONFIG = Config.from_env()

# Paths
CONFIG_DIR = Path(__file__).parent.parent / "config"
PROJECTION_YAML = CONFIG_DIR / "projection.yaml"

# YAML config cache
_yaml_config: Optional[Dict[str, Any]] = None


def load_yaml_config() -> Dict[str, Any]:
    """Load projection.yaml for Hard Tiers mappings."""
    global _yaml_config
    if _yaml_config is None:
        if PROJECTION_YAML.exists():
            with open(PROJECTION_YAML, 'r') as f:
                _yaml_config = yaml.safe_load(f)
            logger.info(f"Loaded projection.yaml with {len(_yaml_config)} entries")
        else:
            logger.warning(f"projection.yaml not found at {PROJECTION_YAML}")
            _yaml_config = {}
    return _yaml_config


def get_yaml_domain_config(object_type: str) -> Optional[Dict[str, Any]]:
    """Get YAML config for a domain by object_type."""
    config = load_yaml_config()
    for domain_key, domain_conf in config.items():
        if domain_key == 'promoted_facets':
            continue
        if isinstance(domain_conf, dict) and domain_conf.get('object_type') == object_type:
            return domain_conf
    return None


def normalize_ident(value: Any) -> Optional[str]:
    """
    Normalize identifier for exact matching.
    Strip whitespace/dashes, uppercase.
    """
    if value is None:
        return None
    s = str(value).strip().upper()
    s = re.sub(r'[\s\-_]+', '', s)
    return s if s and len(s) <= 100 else None


def get_recency_ts(row: Dict, yaml_config: Dict) -> Optional[datetime]:
    """Get recency_ts from source row per YAML config."""
    recency_source = yaml_config.get('recency_source')
    if not recency_source:
        return None

    value = row.get(recency_source)

    # Try fallback if primary is NULL
    if value is None and 'recency_fallback' in yaml_config:
        value = row.get(yaml_config['recency_fallback'])

    # Final fallback to updated_at
    if value is None:
        value = row.get('updated_at')

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


def get_ident_norm(row: Dict, yaml_config: Dict) -> Optional[str]:
    """Get normalized identifier from source row per YAML config."""
    ident_source = yaml_config.get('ident_source')
    if not ident_source:
        return None

    # Direct field lookup
    value = row.get(ident_source)
    return normalize_ident(value)


# =============================================================================
# METRICS
# =============================================================================

@dataclass
class Metrics:
    """Runtime metrics for observability."""
    total_processed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    last_batch_size: int = 0
    last_claim_ms: float = 0
    last_process_ms: float = 0
    last_upsert_ms: float = 0
    last_chunk_ms: float = 0
    last_notify_ms: float = 0
    errors: List[str] = field(default_factory=list)

    def record_error(self, msg: str):
        self.errors.append(f"{datetime.utcnow().isoformat()}: {msg}")
        if len(self.errors) > 100:
            self.errors = self.errors[-50:]  # Keep last 50

    def summary(self) -> Dict[str, Any]:
        return {
            "processed": self.total_processed,
            "failed": self.total_failed,
            "skipped": self.total_skipped,
            "last_batch": self.last_batch_size,
            "timings_ms": {
                "claim": self.last_claim_ms,
                "process": self.last_process_ms,
                "upsert": self.last_upsert_ms,
                "chunk": self.last_chunk_ms,
                "notify": self.last_notify_ms,
            },
            "recent_errors": self.errors[-5:] if self.errors else [],
        }

METRICS = Metrics()

# =============================================================================
# MAPPING REGISTRY
# =============================================================================

MAPPINGS: Dict[str, Dict] = {}

def load_mappings(cur) -> None:
    """Load projection mappings from search_projection_map."""
    global MAPPINGS
    cur.execute("""
        SELECT domain, source_table, object_type, search_text_cols, filter_map, payload_map
        FROM search_projection_map
        WHERE enabled = true
    """)
    MAPPINGS.clear()
    for row in cur.fetchall():
        MAPPINGS[row['source_table']] = {
            'domain': row['domain'],
            'object_type': row['object_type'],
            'search_text_cols': row['search_text_cols'] or [],
            'filter_map': row['filter_map'] or {},
            'payload_map': row['payload_map'] or {}
        }
    logger.info(f"Loaded {len(MAPPINGS)} domain mappings: {list(MAPPINGS.keys())}")

# =============================================================================
# TEXT PROCESSING
# =============================================================================

def compute_content_hash(text: str, context: str = "") -> str:
    """Compute SHA256 hash of search_text || context_text."""
    combined = f"{text}||{context}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def extract_keywords(text: str, top_k: int = 20) -> List[str]:
    """
    Extract top-K keywords from text using MaritimeEntityExtractor.

    Extracts canonical values of 'hard' entities (parts, equipment, brands,
    faults, models, measurements, certificates) for high-quality search keywords.
    Falls back to simple frequency-based extraction if extractor unavailable.
    """
    if not text or not text.strip():
        return []

    # Use MaritimeEntityExtractor for intelligent keyword extraction
    if ENTITY_EXTRACTOR_AVAILABLE:
        extractor = get_extractor()
        entities = extractor.extract_entities(text)

        # Extract canonical values from hard entities only
        # Hard entities: fault_code, measurement, model, brand, part, equipment, certificate
        hard_keywords = [
            entity.canonical
            for entity in entities
            if entity.is_hard and entity.canonical
        ]

        # Deduplicate while preserving order (higher confidence entities first)
        seen = set()
        unique_keywords = []
        for kw in hard_keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw)
                if len(unique_keywords) >= top_k:
                    break

        return unique_keywords

    # Fallback: simple frequency-based extraction
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    stopwords = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'were', 'they',
        'their', 'this', 'that', 'with', 'from', 'will', 'would', 'there', 'what',
        'which', 'when', 'where', 'who', 'how', 'than', 'then', 'these', 'those',
    }
    words = [w for w in words if w not in stopwords]
    counts = Counter(words)
    return [word for word, _ in counts.most_common(top_k)]

def truncate_text(text: str, max_len: int) -> str:
    """Truncate text to max length, preserving word boundaries."""
    if len(text) <= max_len:
        return text
    # Find last space before max_len
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.8:
        return truncated[:last_space]
    return truncated

# =============================================================================
# PROJECTION LOGIC
# =============================================================================

def build_search_text(row: Dict, mapping: Dict) -> str:
    """
    Build search_text from configured columns.

    Includes Dense Payload Fallback: if the initial text is too short (<100 chars),
    parse the row's payload/source data and extract semantic fields to enrich it.
    This handles inventory/purchase_order rows that only have UUIDs in search_text_cols.
    """
    cols = mapping.get('search_text_cols', [])
    parts = []

    for col in cols:
        # Skip virtual columns like 'chunks_keywords' - handled separately
        if col == 'chunks_keywords':
            continue

        val = row.get(col)
        if val:
            if isinstance(val, list):
                parts.append(' '.join(str(v) for v in val if v))
            else:
                parts.append(str(val))

    text = ' '.join(parts).strip()

    # Dense Payload Fallback: enrich sparse search_text from semantic fields
    if len(text) < 100:
        semantic_fields = [
            'name', 'title', 'description', 'category', 'location',
            'sku', 'manufacturer', 'part_number', 'model', 'brand',
            'notes', 'content'
        ]
        seen = set(text.lower().split())
        fallback_parts = []

        for field in semantic_fields:
            val = row.get(field)
            if val and isinstance(val, str) and val.strip():
                # Deduplicate: only add tokens not already present
                tokens = val.strip().split()
                new_tokens = [t for t in tokens if t.lower() not in seen]
                if new_tokens:
                    fallback_parts.append(' '.join(new_tokens))
                    seen.update(t.lower() for t in new_tokens)

        if fallback_parts:
            text = f"{text} {' '.join(fallback_parts)}".strip()

    return truncate_text(text, CONFIG.max_search_text)

def build_filters(row: Dict, mapping: Dict) -> Dict[str, Any]:
    """Build filters JSONB from filter_map."""
    filter_map = mapping.get('filter_map', {})
    filters = {}

    for filter_key, source_col in filter_map.items():
        val = row.get(source_col)
        if val is not None:
            if hasattr(val, 'isoformat'):
                filters[filter_key] = val.isoformat()[:10]
            elif isinstance(val, Decimal):
                filters[filter_key] = float(val)
            elif isinstance(val, (str, int, float, bool)):
                filters[filter_key] = val
            else:
                filters[filter_key] = str(val)

    return filters

def build_payload(row: Dict, mapping: Dict) -> Dict[str, Any]:
    """Build payload JSONB from payload_map."""
    payload_map = mapping.get('payload_map', {})
    payload = {}

    for payload_key, source_col in payload_map.items():
        val = row.get(source_col)
        if val is not None:
            if hasattr(val, 'isoformat'):
                payload[payload_key] = val.isoformat()
            elif isinstance(val, Decimal):
                payload[payload_key] = float(val)
            else:
                payload[payload_key] = val

    return payload

def fetch_source_row(cur, table: str, object_id: str) -> Optional[Dict]:
    """Fetch the source row by ID."""
    try:
        cur.execute(f"SELECT * FROM {table} WHERE id = %s", (object_id,))
        return cur.fetchone()
    except Exception as e:
        logger.error(f"Error fetching {table}/{object_id}: {e}")
        return None

# =============================================================================
# DOCUMENT CHUNK AGGREGATION
# =============================================================================

def aggregate_chunk_keywords(cur, doc_id: str, top_k: int = 20) -> str:
    """
    Aggregate top-K keywords from document chunks.
    Returns space-separated keywords for search_text inclusion.
    """
    try:
        cur.execute("""
            SELECT content FROM search_document_chunks
            WHERE document_id = %s AND content IS NOT NULL
            ORDER BY chunk_index
        """, (doc_id,))

        all_text = ' '.join(row['content'] for row in cur.fetchall() if row['content'])
        if not all_text:
            return ""

        keywords = extract_keywords(all_text, top_k)
        return ' '.join(keywords)

    except Exception as e:
        logger.error(f"Error aggregating chunk keywords for {doc_id}: {e}")
        return ""

def atomic_chunk_replacement(cur, doc_id: str, yacht_id: str, chunks: List[Dict]) -> bool:
    """
    Atomically replace all chunks for a document.
    DELETE old → INSERT new in one transaction.
    Never leaves zero chunks on failure.
    """
    if not chunks:
        logger.warning(f"No chunks to insert for document {doc_id}")
        return False

    try:
        # Delete old chunks
        cur.execute("""
            DELETE FROM search_document_chunks WHERE document_id = %s
        """, (doc_id,))

        # Insert new chunks
        for chunk in chunks:
            content_hash = compute_content_hash(chunk['content'])
            cur.execute("""
                INSERT INTO search_document_chunks
                    (document_id, yacht_id, chunk_index, content, content_hash, tsv)
                VALUES
                    (%s, %s, %s, %s, %s, to_tsvector('english', %s))
            """, (
                doc_id,
                yacht_id,
                chunk['chunk_index'],
                chunk['content'],
                content_hash,
                chunk['content']
            ))

        return True

    except Exception as e:
        logger.error(f"Error in atomic chunk replacement for {doc_id}: {e}")
        raise  # Re-raise to trigger rollback

# =============================================================================
# UPSERT WITH SOURCE_VERSION GUARD
# =============================================================================

def upsert_search_index(cur, item: Dict, row: Dict, mapping: Dict,
                        chunk_keywords: str = "") -> Tuple[bool, bool]:
    """
    Upsert search_index with source_version guard.
    Includes Hard Tiers fields (recency_ts, ident_norm).
    Returns (success, was_updated).
    """
    try:
        object_type = mapping['object_type']

        # Build fields
        search_text = build_search_text(row, mapping)

        # Prepend chunk keywords for documents
        if chunk_keywords:
            search_text = f"{chunk_keywords} {search_text}"
            search_text = truncate_text(search_text, CONFIG.max_search_text)

        filters = build_filters(row, mapping)
        payload = build_payload(row, mapping)
        payload['source_table'] = item['source_table']

        # Compute content hash
        content_hash = compute_content_hash(search_text)

        # Get org_id (from source row or default to yacht_id)
        org_id = row.get('org_id') or item['yacht_id']

        # Hard Tiers: Get recency_ts and ident_norm from YAML config
        yaml_config = get_yaml_domain_config(object_type)
        recency_ts = None
        ident_norm = None

        if yaml_config:
            recency_ts = get_recency_ts(row, yaml_config)
            ident_norm = get_ident_norm(row, yaml_config)

            # Add ident_norm to payload if present (for display)
            if ident_norm:
                payload['ident_norm'] = ident_norm

        # Upsert with source_version guard
        #
        # LAW 9: PROJECTION IMMUTABILITY
        # ==============================
        # This upsert deliberately EXCLUDES the following columns:
        #   - learned_keywords (owned by nightly_feedback_loop.py)
        #   - learned_at (owned by nightly_feedback_loop.py)
        #   - embedding_1536 (owned by embedding_worker_1536.py)
        #   - embedding_status (owned by embedding_worker_1536.py)
        #
        # If you add any of these columns to the UPDATE SET, you will
        # destroy machine learning state or cause embedding re-runs.
        # The tsv column is a GENERATED column that auto-includes
        # both search_text AND learned_keywords.
        #
        cur.execute("""
            INSERT INTO search_index (
                object_type, object_id, org_id, yacht_id,
                search_text, filters, payload,
                recency_ts, ident_norm,
                source_version, content_hash, updated_at
            ) VALUES (
                %(object_type)s, %(object_id)s, %(org_id)s, %(yacht_id)s,
                %(search_text)s, %(filters)s, %(payload)s,
                %(recency_ts)s, %(ident_norm)s,
                %(source_version)s, %(content_hash)s, now()
            )
            ON CONFLICT (object_type, object_id)
            DO UPDATE SET
                search_text = EXCLUDED.search_text,
                filters = EXCLUDED.filters,
                payload = EXCLUDED.payload,
                recency_ts = EXCLUDED.recency_ts,
                ident_norm = EXCLUDED.ident_norm,
                source_version = EXCLUDED.source_version,
                content_hash = EXCLUDED.content_hash,
                updated_at = now()
            WHERE search_index.source_version < EXCLUDED.source_version
            RETURNING id
        """, {
            'object_type': object_type,
            'object_id': str(item['object_id']),
            'org_id': str(org_id),
            'yacht_id': str(item['yacht_id']),
            'search_text': search_text,
            'filters': json.dumps(filters),
            'payload': json.dumps(payload),
            'recency_ts': recency_ts,
            'ident_norm': ident_norm,
            'source_version': item['source_version'],
            'content_hash': content_hash,
        })

        result = cur.fetchone()
        was_updated = result is not None
        return True, was_updated

    except Exception as e:
        logger.error(f"Error upserting search_index: {e}")
        return False, False

def delete_search_index(cur, object_type: str, object_id: str) -> bool:
    """Delete from search_index on source delete."""
    try:
        cur.execute("""
            DELETE FROM search_index
            WHERE object_type = %s AND object_id = %s
        """, (object_type, object_id))

        # Also delete chunks if document
        if object_type == 'document':
            cur.execute("""
                DELETE FROM search_document_chunks WHERE document_id = %s
            """, (object_id,))

        return True
    except Exception as e:
        logger.error(f"Error deleting from search_index: {e}")
        return False

# =============================================================================
# CACHE INVALIDATION
# =============================================================================

def emit_cache_invalidation(cur, org_id: str, yacht_id: str,
                            object_type: str, object_id: str,
                            reason: str = "projection_update") -> None:
    """Emit pg_notify for cache invalidation."""
    start = time.perf_counter()
    try:
        payload = json.dumps({
            "scope": "search",
            "org_id": org_id,
            "yacht_id": yacht_id,
            "keys": [f"search_index:object:{object_type}:{object_id}"],
            "reason": reason,
        })
        cur.execute(f"SELECT pg_notify(%s, %s)", (CONFIG.pg_notify_channel, payload))
        METRICS.last_notify_ms = (time.perf_counter() - start) * 1000
    except Exception as e:
        logger.error(f"Error emitting cache invalidation: {e}")

# =============================================================================
# QUEUE OPERATIONS (using search_index.embedding_status)
# =============================================================================

def claim_batch(cur, object_types: Optional[List[str]] = None) -> List[Dict]:
    """
    Claim a batch of items from search_index with pending/processing embedding_status.

    Args:
        cur: Database cursor
        object_types: Optional list of object_types to filter (worker scope).
                      If None, processes all object types.

    Returns:
        List of search_index rows to process, with embedding_status set to 'processing'.
    """
    start = time.perf_counter()

    # Build WHERE clause for object_type filtering
    type_filter = ""
    params = [CONFIG.batch_size]
    if object_types:
        placeholders = ','.join(['%s'] * len(object_types))
        type_filter = f"AND object_type IN ({placeholders})"
        params = list(object_types) + [CONFIG.batch_size]

    # Claim rows by updating embedding_status to 'processing' and returning them
    # Use FOR UPDATE SKIP LOCKED for concurrent worker safety
    query = f"""
        WITH claimed AS (
            SELECT id, object_type, object_id, org_id, yacht_id,
                   payload->>'source_table' as source_table,
                   COALESCE(source_version, 0) as source_version
            FROM search_index
            WHERE embedding_status IN ('pending', 'processing')
            {type_filter}
            ORDER BY updated_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        UPDATE search_index si
        SET embedding_status = 'processing',
            updated_at = now()
        FROM claimed c
        WHERE si.id = c.id
        RETURNING c.id, c.object_type, c.object_id, c.org_id, c.yacht_id,
                  c.source_table, c.source_version
    """

    cur.execute(query, params)
    items = cur.fetchall()
    METRICS.last_claim_ms = (time.perf_counter() - start) * 1000
    METRICS.last_batch_size = len(items)
    return items

def mark_done(cur, object_type: str, object_id: str) -> None:
    """Mark search_index item as indexed (embedding complete)."""
    cur.execute("""
        UPDATE search_index
        SET embedding_status = 'indexed', updated_at = now()
        WHERE object_type = %s AND object_id = %s
    """, (object_type, object_id))

def mark_failed(cur, object_type: str, object_id: str, error: str) -> None:
    """Mark search_index item as failed."""
    cur.execute("""
        UPDATE search_index
        SET embedding_status = 'failed',
            payload = jsonb_set(COALESCE(payload, '{}'::jsonb), '{embedding_error}', %s::jsonb),
            updated_at = now()
        WHERE object_type = %s AND object_id = %s
    """, (json.dumps(error[:500]), object_type, object_id))

# =============================================================================
# ITEM PROCESSING
# =============================================================================

def process_item(cur, item: Dict) -> Tuple[bool, str]:
    """
    Process a single search_index item for embedding generation.
    Items are claimed from search_index WHERE embedding_status IN ('pending', 'processing').
    Returns (success, error_message).
    """
    start = time.perf_counter()
    source_table = item.get('source_table')
    object_type = item['object_type']
    object_id = str(item['object_id'])
    yacht_id = str(item['yacht_id'])
    org_id = str(item.get('org_id') or yacht_id)

    # If no source_table in payload, use object_type to find mapping
    if not source_table:
        # Find mapping by object_type
        for table, mapping in MAPPINGS.items():
            if mapping.get('object_type') == object_type:
                source_table = table
                break

    if not source_table:
        # No source table needed for embedding - item already exists in search_index
        # Just mark as processed (embedding would be handled by embedding worker)
        METRICS.last_process_ms = (time.perf_counter() - start) * 1000
        return True, ""

    # Get mapping for this source table
    mapping = MAPPINGS.get(source_table)
    if not mapping:
        # No mapping but item exists - proceed with embedding
        METRICS.last_process_ms = (time.perf_counter() - start) * 1000
        return True, ""

    # Fetch source row to refresh search_index data if needed
    row = fetch_source_row(cur, source_table, object_id)
    if not row:
        # Source row may have been deleted - mark as failed
        return False, f"Source row not found: {source_table}/{object_id}"

    org_id = str(row.get('org_id') or yacht_id)

    # Document-specific: aggregate chunk keywords
    chunk_keywords = ""
    if source_table == 'doc_metadata':
        chunk_start = time.perf_counter()
        chunk_keywords = aggregate_chunk_keywords(cur, object_id, CONFIG.chunk_keywords_top_k)
        METRICS.last_chunk_ms = (time.perf_counter() - chunk_start) * 1000

    # Upsert search_index (refresh data before embedding)
    upsert_start = time.perf_counter()
    success, was_updated = upsert_search_index(cur, item, row, mapping, chunk_keywords)
    METRICS.last_upsert_ms = (time.perf_counter() - upsert_start) * 1000

    if not success:
        return False, "Upsert failed"

    # Emit cache invalidation if actually updated
    if was_updated:
        emit_cache_invalidation(cur, org_id, yacht_id, object_type, object_id)

    METRICS.last_process_ms = (time.perf_counter() - start) * 1000
    return True, ""

# =============================================================================
# WORKER LOOP
# =============================================================================

def run_worker():
    """Main worker loop with connection recovery."""
    if not CONFIG.enabled:
        logger.error("Worker not enabled. Set F1_PROJECTION_WORKER_ENABLED=true")
        sys.exit(1)

    if not CONFIG.db_dsn:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info(" F1 SEARCH PROJECTION WORKER")
    logger.info("=" * 70)
    logger.info(f"Batch size: {CONFIG.batch_size}")
    logger.info(f"Poll interval: {CONFIG.poll_interval}s")
    logger.info(f"Max search_text: {CONFIG.max_search_text}")
    logger.info(f"Chunk keywords top-K: {CONFIG.chunk_keywords_top_k}")

    max_reconnect_attempts = 10
    reconnect_delay = 5
    reconnect_attempts = 0

    while not _shutdown:
        conn = None
        cur = None
        try:
            # Connect using Supavisor (should be port 6543 in DATABASE_URL)
            logger.info("Connecting to database...")
            conn = psycopg2.connect(CONFIG.db_dsn, cursor_factory=psycopg2.extras.RealDictCursor)
            conn.autocommit = False
            cur = conn.cursor()

            # Reset reconnect state on successful connection
            reconnect_attempts = 0
            reconnect_delay = 5

            logger.info("Loading mappings...")
            load_mappings(cur)
            conn.commit()

            # Reset orphaned processing items
            cur.execute("""
                UPDATE search_index
                SET embedding_status = 'pending'
                WHERE embedding_status = 'processing'
                AND updated_at < now() - interval '10 minutes'
            """)
            conn.commit()
            logger.info(f"Reset {cur.rowcount} orphaned processing items")

            logger.info("Starting worker loop...")

            while not _shutdown:
                # Connection health check before processing each batch
                try:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                except Exception:
                    logger.warning("Connection check failed, reconnecting...")
                    raise psycopg2.OperationalError("Health check failed")

                # Claim batch
                items = claim_batch(cur)
                conn.commit()

                if not items:
                    logger.debug(f"Queue empty, waiting {CONFIG.poll_interval}s...")
                    time.sleep(CONFIG.poll_interval)
                    continue

                logger.info(f"Processing {len(items)} items...")

                for item in items:
                    if _shutdown:
                        break

                    object_type = item['object_type']
                    object_id = str(item['object_id'])
                    source = f"{item.get('source_table', object_type)}/{object_id[:8]}..."

                    try:
                        success, error = process_item(cur, item)

                        if success:
                            mark_done(cur, object_type, object_id)
                            METRICS.total_processed += 1
                            logger.debug(f"  OK: {source}")
                        else:
                            mark_failed(cur, object_type, object_id, error)
                            METRICS.total_failed += 1
                            METRICS.record_error(f"{source}: {error}")
                            logger.warning(f"  FAIL: {source}: {error}")

                        conn.commit()

                    except Exception as e:
                        conn.rollback()
                        mark_failed(cur, object_type, object_id, str(e))
                        conn.commit()
                        METRICS.total_failed += 1
                        METRICS.record_error(f"{source}: {e}")
                        logger.error(f"  ERROR: {source}: {e}")

                # Log batch summary
                logger.info(f"Batch complete. Total: {METRICS.total_processed} done, "
                           f"{METRICS.total_failed} failed. "
                           f"Timings: claim={METRICS.last_claim_ms:.1f}ms, "
                           f"process={METRICS.last_process_ms:.1f}ms")

        except psycopg2.OperationalError as e:
            reconnect_attempts += 1
            logger.error(f"Connection lost: {e} (attempt {reconnect_attempts}/{max_reconnect_attempts})")

            if reconnect_attempts >= max_reconnect_attempts:
                logger.error("Max reconnect attempts reached, exiting")
                break

            logger.info(f"Reconnecting in {reconnect_delay}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 120)  # Exponential backoff

        except KeyboardInterrupt:
            logger.info("Worker stopped by user.")
            break

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            time.sleep(10)

        finally:
            if cur:
                try:
                    cur.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    logger.info(f"Final metrics: {json.dumps(METRICS.summary(), indent=2)}")

# =============================================================================
# SINGLE BATCH (for testing)
# =============================================================================

def process_once():
    """Process one batch and exit (for testing)."""
    if not CONFIG.db_dsn:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    logger.info("Single batch mode...")

    conn = psycopg2.connect(CONFIG.db_dsn, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    cur = conn.cursor()

    load_mappings(cur)
    conn.commit()

    # Check queue depth (items needing embedding processing)
    cur.execute("""
        SELECT COUNT(*) as cnt FROM search_index
        WHERE embedding_status IN ('pending', 'processing')
    """)
    queued = cur.fetchone()['cnt']
    logger.info(f"Queue depth: {queued} items pending embedding")

    if queued == 0:
        logger.info("Nothing to process.")
        cur.close()
        conn.close()
        return

    # Process one batch
    items = claim_batch(cur)
    conn.commit()

    logger.info(f"Processing {len(items)} items...")

    for item in items:
        object_type = item['object_type']
        object_id = str(item['object_id'])
        source = f"{item.get('source_table', object_type)}/{object_id[:8]}..."

        try:
            success, error = process_item(cur, item)
            if success:
                mark_done(cur, object_type, object_id)
                logger.info(f"  OK: {source}")
            else:
                mark_failed(cur, object_type, object_id, error)
                logger.warning(f"  FAIL: {source}: {error}")
            conn.commit()
        except Exception as e:
            conn.rollback()
            mark_failed(cur, object_type, object_id, str(e))
            conn.commit()
            logger.error(f"  ERROR: {source}: {e}")

    logger.info(f"Done. Metrics: {json.dumps(METRICS.summary(), indent=2)}")
    cur.close()
    conn.close()

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='F1 Search Projection Worker')
    parser.add_argument('--once', action='store_true', help='Process one batch and exit')
    args = parser.parse_args()

    if args.once:
        # Allow running without enable flag for testing
        CONFIG.enabled = True
        process_once()
    else:
        run_worker()
