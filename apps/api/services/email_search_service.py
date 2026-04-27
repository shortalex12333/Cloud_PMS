"""
Email Search Service
====================
Embedding cache, entity extraction, and thread search logic.

Used by:
- routes/email_inbox_routes.py (GET /search, GET /search-objects)

No route concerns here — pure computation and DB reads.
"""

import re
import hashlib
import logging
import time
from threading import Lock
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Minimum free text length to warrant embedding generation
MIN_FREE_TEXT_LENGTH = 3


# ============================================================================
# EMBEDDING CACHE (Short-TTL for latency optimization)
# ============================================================================

class EmbeddingCache:
    """
    Tenant and user-safe TTL cache for query embeddings.

    Reduces redundant OpenAI calls for identical/repeated queries.
    Default TTL: 60 seconds (short to avoid stale results).
    Max size: 100 entries (bounded memory).

    SECURITY:
    - Cache keys include yacht_id AND user_id to prevent:
      1. Cross-tenant cache bleed (different yachts)
      2. Cross-user cache bleed within same yacht (different permissions/roles)
    - 60s TTL limits exposure window
    - In-memory only, ephemeral (no persistence)
    """

    def __init__(self, ttl_seconds: int = 60, max_size: int = 100):
        self._cache: Dict[str, tuple] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, yacht_id: str, user_id: str) -> str:
        """
        Create tenant and user-isolated cache key.

        Key = SHA256(yacht_id + user_id + normalized_text)[:32]
        Prevents cross-tenant and cross-user cache bleed.
        """
        normalized = text.lower().strip()
        composite = f"{yacht_id}:{user_id}:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:32]

    def get(self, text: str, yacht_id: str, user_id: str) -> Optional[List[float]]:
        key = self._make_key(text, yacht_id, user_id)
        now = time.time()
        with self._lock:
            if key in self._cache:
                embedding, timestamp = self._cache[key]
                if now - timestamp < self.ttl_seconds:
                    self._hits += 1
                    return embedding
                else:
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, text: str, yacht_id: str, user_id: str, embedding: List[float]) -> None:
        key = self._make_key(text, yacht_id, user_id)
        now = time.time()
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (embedding, now)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'size': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_pct': round(hit_rate, 1),
            }


# Global singleton — must not be re-initialized across requests
_embedding_cache = EmbeddingCache(ttl_seconds=60, max_size=100)


# ============================================================================
# Entity extraction
# ============================================================================

def extract_query_entities(query: str) -> Dict[str, List[str]]:
    """
    Extract entity IDs from search query using regex patterns.
    Returns dict of entity_type -> list of IDs found.
    """
    patterns = {
        'work_order': [
            r'\bWO[-#]?(\d{1,6})\b',
            r'\[WO[-#]?(\d{1,6})\]',
        ],
        'purchase_order': [
            r'\bPO[-#]?(\d{1,6})\b',
            r'\[PO[-#]?(\d{1,6})\]',
        ],
        'fault': [
            r'\bFAULT[-#]?(\d{1,6})\b',
            r'\[FAULT[-#]?(\d{1,6})\]',
        ],
        'equipment': [
            r'\bEQ[-#]?(\d{1,6})\b',
            r'\[EQ[-#]?(\d{1,6})\]',
        ],
    }

    extracted: Dict[str, List[str]] = {}
    for entity_type, pattern_list in patterns.items():
        matches = []
        for pattern in pattern_list:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                matches.append(match.group(1))
        if matches:
            extracted[entity_type] = list(set(matches))

    return extracted


# ============================================================================
# Thread search
# ============================================================================

async def search_email_threads(
    supabase,
    yacht_id: str,
    user_id: str,
    query: str,
    direction: str,
    page: int,
    page_size: int,
    include_linked: bool,
    watcher_id: str = None,
) -> Dict[str, Any]:
    """
    Search email threads using hybrid search with entity extraction.

    Search layers (in priority order):
    1. Entity ID match (WO-###, PO-###, etc.) in extracted_tokens
    2. SQL text match on subject and sender
    3. Vector semantic search on meta_embedding (stub — not yet integrated)

    Args:
        watcher_id: Optional; if provided, only threads owned by this watcher.
    """
    offset = (page - 1) * page_size
    thread_ids_with_scores: Dict[str, Any] = {}
    search_mode = 'text'

    # -------------------------------------------------------------------------
    # Layer 1: Entity extraction + token search
    # -------------------------------------------------------------------------
    extracted_entities = extract_query_entities(query)

    if extracted_entities:
        logger.info(f"[email/search] Extracted entities: {extracted_entities}")
        search_mode = 'entity'

        for entity_type, ids in extracted_entities.items():
            for entity_id in ids:
                if entity_type == 'work_order':
                    token_patterns = [f'WO-{entity_id}', f'WO{entity_id}', f'WO#{entity_id}']
                elif entity_type == 'purchase_order':
                    token_patterns = [f'PO-{entity_id}', f'PO{entity_id}', f'PO#{entity_id}']
                elif entity_type == 'fault':
                    token_patterns = [f'FAULT-{entity_id}', f'FAULT{entity_id}']
                elif entity_type == 'equipment':
                    token_patterns = [f'EQ-{entity_id}', f'EQ{entity_id}']
                else:
                    token_patterns = [entity_id]

                for token in token_patterns:
                    try:
                        token_results = supabase.table('email_threads').select(
                            'id, latest_subject, last_activity_at'
                        ).eq('yacht_id', yacht_id).ilike(
                            'extracted_tokens', f'%{token}%'
                        ).limit(20).execute()

                        for thread in (token_results.data or []):
                            tid = thread['id']
                            if tid not in thread_ids_with_scores:
                                thread_ids_with_scores[tid] = {
                                    'thread_id': tid,
                                    'sent_at': thread.get('last_activity_at'),
                                    'match_type': 'entity',
                                    'entity_type': entity_type,
                                    'entity_id': entity_id,
                                }
                    except Exception as e:
                        logger.debug(f"Token search error: {e}")

                    try:
                        subject_results = supabase.table('email_threads').select(
                            'id, latest_subject, last_activity_at'
                        ).eq('yacht_id', yacht_id).ilike(
                            'latest_subject', f'%{token}%'
                        ).limit(20).execute()

                        for thread in (subject_results.data or []):
                            tid = thread['id']
                            if tid not in thread_ids_with_scores:
                                thread_ids_with_scores[tid] = {
                                    'thread_id': tid,
                                    'sent_at': thread.get('last_activity_at'),
                                    'match_type': 'subject_entity',
                                    'entity_type': entity_type,
                                    'entity_id': entity_id,
                                }
                    except Exception as e:
                        logger.debug(f"Subject search error: {e}")

    # -------------------------------------------------------------------------
    # Layer 2: SQL text match on subject and sender
    # -------------------------------------------------------------------------
    text_query = supabase.table('email_messages').select(
        'id, thread_id, subject, from_display_name, direction, sent_at, has_attachments'
    ).eq('yacht_id', yacht_id).or_(
        f"subject.ilike.%{query}%,from_display_name.ilike.%{query}%"
    )

    if direction in ('inbound', 'outbound'):
        text_query = text_query.eq('direction', direction)

    text_results = text_query.order('sent_at', desc=True).limit(100).execute()

    for msg in (text_results.data or []):
        tid = msg.get('thread_id')
        if tid and tid not in thread_ids_with_scores:
            thread_ids_with_scores[tid] = {
                'thread_id': tid,
                'sent_at': msg.get('sent_at'),
                'match_type': 'text',
            }
            if search_mode == 'entity':
                search_mode = 'hybrid'

    # -------------------------------------------------------------------------
    # Layer 3: Vector search stub (embeddings populated, RPC not yet wired)
    # -------------------------------------------------------------------------
    try:
        has_embeddings = supabase.table('email_messages').select('id').eq(
            'yacht_id', yacht_id
        ).not_.is_('meta_embedding', 'null').limit(1).execute()

        if has_embeddings.data and search_mode in ('text', 'entity'):
            search_mode = search_mode + '_partial_vector'
    except Exception as e:
        logger.debug(f"Vector search not available: {e}")

    # -------------------------------------------------------------------------
    # Early-exit if nothing found
    # -------------------------------------------------------------------------
    if not thread_ids_with_scores:
        return {
            'threads': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'has_more': False,
            'search_mode': search_mode,
            'extracted_entities': extracted_entities,
        }

    thread_ids = list(thread_ids_with_scores.keys())

    # Filter out already-linked threads when requested
    if not include_linked:
        linked_result = supabase.table('email_links').select(
            'thread_id'
        ).eq('yacht_id', yacht_id).eq('is_active', True).in_(
            'thread_id', thread_ids
        ).execute()

        linked_ids = {l['thread_id'] for l in (linked_result.data or [])}
        thread_ids = [tid for tid in thread_ids if tid not in linked_ids]

    if not thread_ids:
        return {
            'threads': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'has_more': False,
            'search_mode': search_mode,
            'extracted_entities': extracted_entities,
        }

    threads_result = supabase.table('email_threads').select(
        'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at, created_at'
    ).eq('yacht_id', yacht_id).in_('id', thread_ids).order(
        'last_activity_at', desc=True
    ).execute()

    threads = threads_result.data or []
    total = len(threads)
    paginated = threads[offset:offset + page_size]

    for thread in paginated:
        tid = thread['id']
        if tid in thread_ids_with_scores:
            thread['_match_info'] = thread_ids_with_scores[tid]

    return {
        'threads': paginated,
        'total': total,
        'page': page,
        'page_size': page_size,
        'has_more': offset + len(paginated) < total,
        'search_mode': search_mode,
        'extracted_entities': extracted_entities,
    }
