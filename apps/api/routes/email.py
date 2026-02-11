"""
CelesteOS Backend - Email Transport Layer Routes

Endpoints:
- GET  /email/related?object_type=&object_id=  - Get threads linked to an object
- GET  /email/thread/:thread_id                - Get thread with messages
- GET  /email/message/:provider_message_id/render - Fetch message content (no storage)
- GET  /email/message/:message_id/attachments  - List attachments (M7: from DB, no content)
- GET  /email/message/:provider_message_id/attachments/:id/download - Stream download (M7)
- GET  /email/search?q=query&limit=10          - Hybrid semantic+entity search
- POST /email/link/add                         - Add a new link (M8: generic for all types)
- POST /email/link/accept                      - Accept a suggested link
- POST /email/link/change                      - Change link target
- POST /email/link/remove                      - Remove a link (soft delete)
- POST /email/evidence/save-attachment         - Save attachment to documents
- POST /email/sync/now                         - Manual sync trigger (service role only)
- POST /email/backfill-weblinks                - Backfill webLink for "Open in Outlook"

Doctrine compliance:
- All queries scoped by yacht_id
- Render uses READ token only
- Send/evidence uses WRITE token only
- No email body storage
- All link changes audited
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import uuid
import hashlib
import os  # SECURITY FIX P0-007: For path operations
import time
from functools import lru_cache
from threading import Lock
from cachetools import TTLCache

# ============================================================================
# PERFORMANCE: In-memory cache for Graph API responses
# TTL 60s - short enough to respect doctrine (no long-term storage)
# maxsize 500 - reasonable for typical usage patterns
# ============================================================================
_message_content_cache: TTLCache = TTLCache(maxsize=500, ttl=60)
_cache_lock = Lock()

# Local imports
from middleware.auth import get_authenticated_user
from integrations.supabase import get_supabase_client  # Deprecated for email routes
from supabase import create_client
from integrations.feature_flags import check_email_feature
from integrations.graph_client import (
    create_read_client,
    create_write_client,
    TokenNotFoundError,
    TokenExpiredError,
    TokenRevokedError,
    TokenPurposeMismatchError,
    TokenRefreshError,
    GraphApiError,
)
from services.email_suggestion_service import generate_suggestions_for_thread

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


# ============================================================================
# TENANT CLIENT (Avoids circular import from pipeline_service)
# ============================================================================

def get_tenant_client(tenant_key_alias: str):
    """Get Supabase client for tenant DB using tenant-prefixed env vars."""
    url = os.environ.get(f'{tenant_key_alias}_SUPABASE_URL')
    key = os.environ.get(f'{tenant_key_alias}_SUPABASE_SERVICE_KEY')

    if not url or not key:
        logger.error(f"[TenantClient] Missing credentials for {tenant_key_alias}")
        raise ValueError(f'Missing credentials for tenant {tenant_key_alias}')

    return create_client(url, key)


# ============================================================================
# SECURITY FIX P0-007: File Upload Validation Constants
# ============================================================================
ALLOWED_EXTENSIONS = {
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.csv', '.rtf', '.odt', '.ods', '.odp'
}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'application/rtf',
    'application/vnd.oasis.opendocument.text',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.presentation',
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


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
        self._cache: Dict[str, Tuple[List[float], float]] = {}
        self._lock = Lock()
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, yacht_id: str, user_id: str) -> str:
        """
        Create tenant and user-isolated cache key.

        Key = SHA256(yacht_id + user_id + normalized_text)[:32]
        This ensures:
        - No cross-tenant cache bleed (different yachts)
        - No cross-user cache bleed (different users within same yacht)

        Note: user_id provides implicit role/permission isolation since
        embeddings are generated from the same text regardless of permissions,
        but results may differ. 60s TTL further limits any risk.
        """
        normalized = text.lower().strip()
        composite = f"{yacht_id}:{user_id}:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:32]

    def get(self, text: str, yacht_id: str, user_id: str) -> Optional[List[float]]:
        """Get cached embedding if valid (tenant and user-scoped)."""
        key = self._make_key(text, yacht_id, user_id)
        now = time.time()

        with self._lock:
            if key in self._cache:
                embedding, timestamp = self._cache[key]
                if now - timestamp < self.ttl_seconds:
                    self._hits += 1
                    return embedding
                else:
                    # Expired - remove
                    del self._cache[key]
            self._misses += 1
            return None

    def set(self, text: str, yacht_id: str, user_id: str, embedding: List[float]) -> None:
        """Store embedding in cache (tenant and user-scoped)."""
        key = self._make_key(text, yacht_id, user_id)
        now = time.time()

        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

            self._cache[key] = (embedding, now)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                'size': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_pct': round(hit_rate, 1),
            }


# Global embedding cache instance
_embedding_cache = EmbeddingCache(ttl_seconds=60, max_size=100)


# Minimum free text length to warrant embedding generation
MIN_FREE_TEXT_LENGTH = 3


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RelatedRequest(BaseModel):
    object_type: str = Field(..., description="Type: work_order, equipment, part, fault, etc.")
    object_id: str = Field(..., description="UUID of the object")


class LinkAcceptRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to accept")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkChangeRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to change")
    new_object_type: str = Field(..., description="New target type")
    new_object_id: str = Field(..., description="New target UUID")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


class LinkRemoveRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to remove")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


# Roles allowed to manage email links
LINK_MANAGE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']


class LinkRejectRequest(BaseModel):
    link_id: str = Field(..., description="UUID of the link to reject")


class LinkCreateRequest(BaseModel):
    thread_id: str = Field(..., description="UUID of the email thread to link")
    object_type: str = Field(..., description="Type: work_order, equipment, part, fault, purchase_order, supplier")
    object_id: str = Field(..., description="UUID of the object to link to")


class SaveAttachmentRequest(BaseModel):
    message_id: str = Field(..., description="Provider message ID")
    attachment_id: str = Field(..., description="Provider attachment ID")
    target_folder: Optional[str] = Field(None, description="Target folder in documents")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


# Roles allowed to save evidence attachments
EVIDENCE_SAVE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager', 'member']

# Maximum attachment size (25 MB)
MAX_ATTACHMENT_SIZE_BYTES = 25 * 1024 * 1024

# Allowed content types (whitelisted for security)
ALLOWED_ATTACHMENT_TYPES = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/csv',
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/tiff',
    # Archives (for manuals, service packs)
    'application/zip',
}


class ThreadResponse(BaseModel):
    id: str
    provider_conversation_id: str
    latest_subject: Optional[str]
    message_count: int
    has_attachments: bool
    source: str
    first_message_at: Optional[str]
    last_activity_at: Optional[str]
    messages: List[Dict[str, Any]]


class MessageRenderResponse(BaseModel):
    id: str
    subject: Optional[str]
    body: Dict[str, Any]
    body_preview: Optional[str]
    from_address: Dict[str, Any]
    to_recipients: List[Dict[str, Any]]
    cc_recipients: List[Dict[str, Any]]
    received_at: Optional[str]
    sent_at: Optional[str]
    has_attachments: bool
    attachments: List[Dict[str, Any]]


# ============================================================================
# HELPER: FEATURE FLAG GUARD
# ============================================================================

def require_feature(feature_name: str):
    """Dependency that checks feature flag and fails closed."""
    enabled, error_msg = check_email_feature(feature_name)
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)


# ============================================================================
# HELPER: MARK WATCHER DEGRADED
# ============================================================================

async def mark_watcher_degraded(
    supabase,
    user_id: str,
    yacht_id: str,
    error_message: str,
):
    """Mark email watcher as degraded with error message."""
    try:
        supabase.table('email_watchers').update({
            'sync_status': 'degraded',
            'last_sync_error': error_message[:500],  # Truncate for DB
            'last_sync_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'provider', 'microsoft_graph'
        ).execute()
        logger.info(f"[email] Marked watcher degraded: {error_message[:100]}")
    except Exception as e:
        logger.error(f"[email] Failed to mark watcher degraded: {e}")


# ============================================================================
# HELPER: AUDIT LOGGING
# ============================================================================

async def audit_link_action(
    supabase,
    yacht_id: str,
    user_id: str,
    action: str,
    link_id: str,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    idempotency_key: Optional[str] = None,
    user_role: Optional[str] = None,
):
    """
    Log link action to audit log with enhanced context.

    M4: Enhanced audit for SOC-2 compliance with:
    - Idempotency key tracking
    - User role capture
    - IP/source context (when available)
    """
    try:
        signature = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_version': 'M4',
        }
        if idempotency_key:
            signature['idempotency_key'] = idempotency_key
        if user_role:
            signature['user_role'] = user_role

        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': action,
            'entity_type': 'email_link',
            'entity_id': link_id,
            'user_id': user_id,
            'old_values': old_values or {},
            'new_values': new_values or {},
            'signature': signature,
        }).execute()
        logger.info(f"[audit] {action} link={link_id[:8]} user={user_id[:8]} yacht={yacht_id[:8]}")
    except Exception as e:
        logger.error(f"Failed to audit link action: {e}")


async def check_idempotency(
    supabase,
    yacht_id: str,
    idempotency_key: str,
    action: str,
) -> Optional[Dict]:
    """
    Check if an idempotent operation was already performed.

    Returns the previous result if found (within 24h window), None otherwise.
    """
    if not idempotency_key:
        return None

    try:
        result = supabase.table('pms_audit_log').select('new_values').eq(
            'yacht_id', yacht_id
        ).eq('action', action).eq(
            'signature->>idempotency_key', idempotency_key
        ).limit(1).execute()

        if result.data:
            logger.info(f"[idempotency] Returning cached result for key={idempotency_key[:16]}")
            return result.data[0].get('new_values', {})
        return None
    except Exception as e:
        logger.warning(f"[idempotency] Check failed: {e}")
        return None


# ============================================================================
# GET /email/search - Hybrid Semantic + Entity Search
# ============================================================================

class SearchRequest(BaseModel):
    q: str = Field(..., description="Search query", min_length=1, max_length=500)
    limit: int = Field(20, description="Max results", ge=1, le=100)
    threshold: float = Field(0.3, description="Similarity threshold", ge=0.0, le=1.0)
    date_from: Optional[str] = Field(None, description="Filter: emails after this date (ISO 8601)")
    date_to: Optional[str] = Field(None, description="Filter: emails before this date (ISO 8601)")
    # M3 boost controls (defaults match RPC defaults)
    boost_recency: bool = Field(True, description="Enable recency decay scoring")
    boost_affinity: bool = Field(True, description="Enable participant affinity scoring")
    boost_linkage: bool = Field(True, description="Enable operational linkage scoring")


@router.get("/search")
async def search_emails(
    q: str,
    limit: int = 20,
    threshold: float = 0.3,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    boost_recency: bool = True,
    boost_affinity: bool = True,
    boost_linkage: bool = True,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Hybrid semantic + entity search for emails with operator support (M2).

    Supported operators:
    - from:<email|name>      Filter by sender
    - to:<email|name>        Filter by recipient
    - subject:<text>         Filter by subject contains
    - has:attachment         Filter messages with attachments
    - before:<date>          Filter by date (YYYY-MM-DD)
    - after:<date>           Filter by date (YYYY-MM-DD)
    - in:work_order:<id>     Filter by linked work order
    - thread:<id>            Filter by thread ID

    Examples:
    - "watermaker parts from:supplier@marine.com"
    - "subject:invoice after:2024-01-01 has:attachment"
    - "engine PO-2024 before:2024-03-15"

    Scoring:
    - Vector similarity (70% weight) via text-embedding-3-small
    - Entity keyword matching (30% weight) via regex extraction

    Tenant-scoped by yacht_id from auth context.
    """
    import time
    start_time = time.time()

    enabled, error_msg = check_email_feature('search')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    yacht_id = auth['yacht_id']
    user_id = auth.get('user_id', 'unknown')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Telemetry tracking
    telemetry = {
        'parse_ms': 0,
        'embed_ms': 0,
        'search_ms': 0,
        'total_ms': 0,
        'operators_count': 0,
        'keywords_count': 0,
        'results_count': 0,
        'zero_results': False,
        'parse_warnings': 0,
        'embed_skipped': False,
        'embed_cached': False,
    }

    try:
        # 1. Parse query: extract operators and free text
        parse_start = time.time()
        from email_rag.query_parser import prepare_query_for_search
        parsed = prepare_query_for_search(q)
        telemetry['parse_ms'] = int((time.time() - parse_start) * 1000)
        telemetry['operators_count'] = parsed['operators_count']
        telemetry['keywords_count'] = len(parsed['keywords'])
        telemetry['parse_warnings'] = len(parsed['warnings'])

        # Log parse results (sanitized - no PII in free_text for audit)
        logger.info(f"[email/search] yacht={yacht_id[:8]} operators={parsed['operators_count']} keywords={len(parsed['keywords'])} warnings={len(parsed['warnings'])}")

        # 2. Generate embedding from FREE TEXT only (not operators)
        # OPTIMIZATION: Skip embedding if operator-only query (no meaningful free text)
        embed_start = time.time()
        free_text = parsed['free_text'].strip() if parsed['free_text'] else ''
        embedding = None

        # Determine if we should skip embedding:
        # - Free text is empty or very short (< MIN_FREE_TEXT_LENGTH chars)
        # - AND we have at least one operator
        # - BUT: Don't skip if subject: filter has a multi-word phrase (needs semantic search)
        subject_filter = parsed['filters'].get('p_subject', '')
        subject_has_phrase = subject_filter and ' ' in subject_filter  # Multi-word subject

        should_skip_embed = (
            len(free_text) < MIN_FREE_TEXT_LENGTH and
            parsed['operators_count'] > 0 and
            not subject_has_phrase  # Don't skip if subject: has phrase
        )

        if should_skip_embed:
            # Operator-only query (e.g., "from:john@example.com has:attachment")
            # Use zero vector - will rely on filters and entity keywords
            embedding = [0.0] * 1536
            telemetry['embed_skipped'] = True
            logger.info(f"[email/search] Skipping embedding - operator-only query")
        else:
            # Has meaningful free text - check tenant+user-safe cache first
            search_text = free_text if free_text else q
            embedding = _embedding_cache.get(search_text, yacht_id, user_id)

            if embedding:
                telemetry['embed_cached'] = True
                logger.debug(f"[email/search] Cache hit for query")
            else:
                # Cache miss - generate embedding
                from email_rag.embedder import generate_embedding_sync
                embedding = generate_embedding_sync(search_text)
                if embedding:
                    _embedding_cache.set(search_text, yacht_id, user_id, embedding)

        telemetry['embed_ms'] = int((time.time() - embed_start) * 1000)

        # Entity-only fallback: if embedding generation failed (OpenAI unavailable),
        # degrade gracefully to entity keyword search only
        if not embedding:
            logger.warning("[email/search] No embedding available; degrading to entity-only search")
            embedding = [0.0] * 1536  # Neutral vector
            telemetry['embed_skipped'] = True  # Mark as skipped for telemetry

        # 3. Build RPC params
        # OPTIMIZATION: When embedding is skipped (zero vector), use threshold=0
        # to let filters and entity keywords drive results
        effective_threshold = 0.0 if telemetry['embed_skipped'] else threshold

        # Compute user email hash for affinity scoring (if available)
        user_email = auth.get('email', '')
        user_email_hash = hashlib.sha256(user_email.lower().encode()).hexdigest() if user_email else None

        params = {
            'p_yacht_id': yacht_id,
            'p_embedding': embedding,
            'p_entity_keywords': parsed['keywords'] if parsed['keywords'] else [],
            'p_limit': min(limit, 100),
            'p_similarity_threshold': effective_threshold,
            # M3 signal params
            'p_user_email_hash': user_email_hash,
            'p_boost_recency': boost_recency,
            'p_boost_affinity': boost_affinity and user_email_hash is not None,
            'p_boost_linkage': boost_linkage,
        }

        # Add parsed operator filters
        params.update(parsed['filters'])

        # Override with explicit date params if provided (backwards compat)
        if date_from:
            params['p_date_from'] = date_from
        if date_to:
            params['p_date_to'] = date_to

        # Execute search with timing
        search_start = time.time()
        result = supabase.rpc('search_email_hybrid', params).execute()
        telemetry['search_ms'] = int((time.time() - search_start) * 1000)
        telemetry['results_count'] = len(result.data or [])
        telemetry['zero_results'] = telemetry['results_count'] == 0

        # 4. Format response
        results = []
        for row in (result.data or []):
            # Build score object with all signals (M3)
            score_obj = {
                'total': row.get('total_score'),
                'vector': row.get('vector_score'),
                'entity': row.get('entity_score'),
            }
            # Add M3 signal scores if present
            if 'recency_score' in row:
                score_obj['recency'] = row.get('recency_score')
            if 'affinity_score' in row:
                score_obj['affinity'] = row.get('affinity_score')
            if 'linkage_score' in row:
                score_obj['linkage'] = row.get('linkage_score')
            if 'activity_score' in row:
                score_obj['activity'] = row.get('activity_score')

            results.append({
                'message_id': row.get('message_id'),
                'thread_id': row.get('thread_id'),
                'subject': row.get('subject'),
                'preview_text': row.get('preview_text'),
                'from_display_name': row.get('from_display_name'),
                'from_address': row.get('from_address_hash'),
                'sent_at': row.get('sent_at'),
                'direction': row.get('direction'),
                'has_attachments': row.get('has_attachments'),
                'score': score_obj,
                'score_breakdown': row.get('score_breakdown'),  # M3: Full breakdown
                'matched_entities': row.get('matched_entities', []),
                'filters_applied': row.get('filters_applied', []),
            })

        # Finalize telemetry
        telemetry['total_ms'] = int((time.time() - start_time) * 1000)

        # Log structured telemetry for observability
        logger.info(
            f"[email/search/telemetry] "
            f"yacht={yacht_id[:8]} "
            f"total_ms={telemetry['total_ms']} "
            f"parse_ms={telemetry['parse_ms']} "
            f"embed_ms={telemetry['embed_ms']} "
            f"search_ms={telemetry['search_ms']} "
            f"results={telemetry['results_count']} "
            f"operators={telemetry['operators_count']} "
            f"zero_results={telemetry['zero_results']} "
            f"embed_skipped={telemetry['embed_skipped']} "
            f"embed_cached={telemetry['embed_cached']}"
        )

        # Alert on slow queries (p95 target: 400ms)
        if telemetry['total_ms'] > 500:
            logger.warning(
                f"[email/search/slow] yacht={yacht_id[:8]} total_ms={telemetry['total_ms']} "
                f"search_ms={telemetry['search_ms']} operators={telemetry['operators_count']}"
            )

        return {
            'results': results,
            'count': len(results),
            'query': q,
            'parsed': {
                'free_text': parsed['free_text'],
                'operators_count': parsed['operators_count'],
                'filters': parsed['filters'],
                'match_reasons': parsed['match_reasons'],
                'warnings': parsed['warnings'],
            },
            'extracted_keywords': parsed['keywords'],
            'telemetry': {
                'total_ms': telemetry['total_ms'],
                'search_ms': telemetry['search_ms'],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"[email/search] Error: {e}\n{tb_str}")
        # Log telemetry even on failure
        telemetry['total_ms'] = int((time.time() - start_time) * 1000)
        logger.error(
            f"[email/search/error] yacht={yacht_id[:8]} total_ms={telemetry['total_ms']} error={str(e)[:200]}"
        )
        # Include error type in response for debugging (production should sanitize)
        error_detail = f"Search failed: {type(e).__name__}: {str(e)[:100]}"
        raise HTTPException(status_code=500, detail=error_detail)


# ============================================================================
# GET /email/focus/:message_id - Focus View with Micro-Actions (M4)
# ============================================================================

@router.get("/focus/{message_id}")
async def get_message_focus(
    message_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get focused view of a message with available micro-actions.

    Returns email metadata, extracted entities, and a list of available
    micro-actions with preconditions and reasons.

    M4 Micro-Actions:
    - link_to_work_order: Link email to existing WO
    - create_work_order_from_email: Create new WO from email
    - attach_evidence: Save attachment to document library
    - link_to_equipment: Link email to equipment
    - link_to_part: Link email to part
    """
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_role = auth.get('role', 'member')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # 1. Get message metadata (yacht_id enforced via RLS)
        msg_result = supabase.table('email_messages').select(
            'id, thread_id, subject, from_display_name, sent_at, has_attachments, attachments, preview_text'
        ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

        if not msg_result.data:
            raise HTTPException(status_code=404, detail="Message not found")

        message = msg_result.data

        # 2. Get extracted entities for this message
        entities_result = supabase.table('email_extraction_results').select(
            'entity_type, entity_value, confidence'
        ).eq('message_id', message_id).execute()

        # Group entities by type
        extracted_entities: Dict[str, List[str]] = {}
        for entity in (entities_result.data or []):
            entity_type = entity['entity_type']
            if entity_type not in extracted_entities:
                extracted_entities[entity_type] = []
            extracted_entities[entity_type].append(entity['entity_value'])

        # If no extraction results, extract from preview_text now
        if not extracted_entities and message.get('preview_text'):
            from email_rag.entity_extractor import EmailEntityExtractor
            extractor = EmailEntityExtractor()
            full_text = f"{message.get('subject', '')}\n\n{message.get('preview_text', '')}"
            extracted_entities = extractor.extract(full_text)

        # 3. Get existing email links for this thread
        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, accepted_at'
        ).eq('thread_id', message['thread_id']).eq('yacht_id', yacht_id).eq('is_active', True).execute()

        existing_links = [
            {
                'id': link['id'],
                'object_type': link['object_type'],
                'object_id': link['object_id'],
                'confidence': link['confidence'],
                'accepted': link['accepted_at'] is not None,
            }
            for link in (links_result.data or [])
        ]

        # 4. Count attachments
        attachments = message.get('attachments') or []
        if isinstance(attachments, str):
            import json
            try:
                attachments = json.loads(attachments)
            except Exception:
                attachments = []
        attachment_count = len(attachments) if attachments else 0

        # 5. Build focus response with micro-actions
        from email_rag.micro_actions import build_focus_response

        response = build_focus_response(
            message_id=message_id,
            thread_id=message['thread_id'],
            subject=message.get('subject'),
            from_display_name=message.get('from_display_name'),
            sent_at=message.get('sent_at'),
            has_attachments=message.get('has_attachments', False),
            attachment_count=attachment_count,
            extracted_entities=extracted_entities,
            existing_links=existing_links,
            user_role=user_role,
        )

        logger.info(
            f"[email/focus] yacht={yacht_id[:8]} message={message_id[:8]} "
            f"entities={len(extracted_entities)} links={len(existing_links)} "
            f"actions={len(response.micro_actions)}"
        )

        return response.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/focus] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get message focus")


# ============================================================================
# GET /email/related
# ============================================================================

@router.get("/related")
async def get_related_threads(
    object_type: str,
    object_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get email threads linked to an object.

    Tenant-scoped by yacht_id from auth context.
    """
    # Feature flag check
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Validate object_type (use shared constant)
    if object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {VALID_LINK_OBJECT_TYPES}")

    try:
        # Get links for this object, scoped by yacht_id
        links_result = supabase.table('email_links').select(
            'id, thread_id, confidence, suggested_reason, accepted_at, accepted_by'
        ).eq('yacht_id', yacht_id).eq(
            'object_type', object_type
        ).eq('object_id', object_id).eq('is_active', True).execute()

        if not links_result.data:
            return {'threads': [], 'count': 0}

        # Get thread details
        thread_ids = [link['thread_id'] for link in links_result.data]
        threads_result = supabase.table('email_threads').select(
            'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at'
        ).eq('yacht_id', yacht_id).in_('id', thread_ids).order(
            'last_activity_at', desc=True
        ).execute()

        # Build response with link metadata
        threads = []
        link_map = {link['thread_id']: link for link in links_result.data}
        for thread in (threads_result.data or []):
            link = link_map.get(thread['id'], {})
            threads.append({
                **thread,
                'link_id': link.get('id'),
                'confidence': link.get('confidence'),
                'suggested_reason': link.get('suggested_reason'),
                'accepted': link.get('accepted_at') is not None,
            })

        return {'threads': threads, 'count': len(threads)}

    except Exception as e:
        logger.error(f"[email/related] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch related threads")


# ============================================================================
# GET /email/thread/:thread_id
# ============================================================================

@router.get("/thread/{thread_id}")
async def get_thread(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get thread with its messages.

    Tenant-scoped by yacht_id from auth context.
    """
    enabled, error_msg = check_email_feature('thread')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']

    # Validate thread_id is a valid UUID to prevent DB errors
    import uuid
    try:
        uuid.UUID(thread_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "thread_not_found",
                "message": "Invalid thread ID format",
                "thread_id": thread_id,
                "yacht_id": yacht_id
            }
        )

    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get thread (yacht_id enforced)
        # Use limit(1) instead of maybe_single() to avoid 204 exception issues
        thread_result = supabase.table('email_threads').select('*').eq(
            'id', thread_id
        ).eq('yacht_id', yacht_id).limit(1).execute()

        if not thread_result.data or len(thread_result.data) == 0:
            # DIAGNOSTIC: Check if thread exists but with different yacht_id
            # This helps identify data corruption vs auth mismatch
            try:
                any_thread_result = supabase.table('email_threads').select(
                    'id, yacht_id, latest_subject'
                ).eq('id', thread_id).limit(1).execute()
                if any_thread_result.data and len(any_thread_result.data) > 0:
                    actual_thread = any_thread_result.data[0]
                    logger.warning(
                        f"[email/thread] YACHT_ID_MISMATCH: thread_id={thread_id} exists with "
                        f"yacht_id={actual_thread.get('yacht_id')} but user has yacht_id={yacht_id}. "
                        f"Subject: {actual_thread.get('latest_subject', 'N/A')[:50]}"
                    )
                else:
                    logger.info(f"[email/thread] Thread truly does not exist: thread_id={thread_id}")
            except Exception as diag_err:
                logger.debug(f"[email/thread] Diagnostic query failed: {diag_err}")

            logger.info(f"[email/thread] Thread not found: thread_id={thread_id}, yacht_id={yacht_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "thread_not_found",
                    "message": "Thread not found or not accessible",
                    "thread_id": thread_id,
                    "yacht_id": yacht_id
                }
            )

        thread = thread_result.data[0]

        # Get messages for this thread (include web_link for "Open in Outlook")
        # Filter out deleted messages (soft delete)
        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id, direction, from_display_name, subject, sent_at, received_at, has_attachments, attachments, web_link'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).eq(
            'is_deleted', False
        ).order('sent_at', desc=False).execute()

        return {
            **thread,
            'messages': messages_result.data or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[email/thread] Unexpected error: {error_msg}", exc_info=True)
        # Check for common DB errors that should be 404
        if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "thread_not_found",
                    "message": "Thread not found",
                    "thread_id": thread_id,
                    "yacht_id": yacht_id
                }
            )
        # Return 500 only for truly unexpected errors
        raise HTTPException(
            status_code=500,
            detail={
                "code": "internal_error",
                "message": "Failed to fetch thread",
                "thread_id": thread_id
            }
        )


# ============================================================================
# GET /email/message/:provider_message_id/render
# ============================================================================

@router.get("/message/{provider_message_id}/render")
async def render_message(
    provider_message_id: str,
    response: Response,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Fetch full message content from Graph for rendering.

    DOCTRINE: Content is NOT stored. Fetched on-click only.
    Uses READ token exclusively.

    Performance: Short-lived in-memory cache (60s TTL) to reduce
    repeated Graph API calls for same message within a session.
    """
    start_time = time.time()
    cache_status = "MISS"

    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Verify message belongs to user's yacht
    msg_result = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result or not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    # Cache key: yacht-scoped to prevent cross-tenant leakage
    cache_key = f"{yacht_id}:{provider_message_id}"

    try:
        # Check cache first
        with _cache_lock:
            content = _message_content_cache.get(cache_key)

        if content is not None:
            cache_status = "HIT"
            logger.debug(f"[email/render] Cache HIT for {provider_message_id[:16]}...")
        else:
            # Cache miss - fetch from Graph API
            read_client = create_read_client(supabase, user_id, yacht_id)
            content = await read_client.get_message_content(provider_message_id)

            # Store in cache (short TTL, yacht-scoped)
            with _cache_lock:
                _message_content_cache[cache_key] = content

        # Debug: Log render request details (no body content for security)
        body_obj = content.get('body', {})
        body_type = body_obj.get('contentType', 'unknown')
        body_len = len(body_obj.get('content', '')) if body_obj.get('content') else 0
        logger.info(
            f"[email/render] message={provider_message_id[:16]}... "
            f"type={body_type} size={body_len} yacht={yacht_id[:8]}"
        )

        # Lazy backfill: Update web_link in database if we got one from Graph
        weblink = content.get('webLink')
        if weblink and msg_result.data:
            try:
                supabase.table('email_messages').update({
                    'web_link': weblink
                }).eq('provider_message_id', provider_message_id).eq(
                    'yacht_id', yacht_id
                ).execute()
                logger.debug(f"[email/render] Updated web_link for {provider_message_id[:16]}...")
            except Exception as e:
                # Non-fatal: just log and continue
                logger.warning(f"[email/render] Failed to update web_link: {e}")

        # Add performance timing headers
        elapsed_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Graph-Cache"] = cache_status
        response.headers["X-Graph-Time"] = str(elapsed_ms)

        return {
            'id': content.get('id'),
            'subject': content.get('subject'),
            'body': content.get('body', {}),
            'body_preview': content.get('bodyPreview'),
            'from_address': content.get('from', {}),
            'to_recipients': content.get('toRecipients', []),
            'cc_recipients': content.get('ccRecipients', []),
            'received_at': content.get('receivedDateTime'),
            'sent_at': content.get('sentDateTime'),
            'has_attachments': content.get('hasAttachments', False),
            'attachments': content.get('attachments', []),
            'web_link': content.get('webLink'),  # OWA link for "Open in Outlook"
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected. Please connect your Outlook account.")

    except TokenExpiredError:
        # This shouldn't happen with auto-refresh, but handle gracefully
        raise HTTPException(status_code=401, detail="Email connection expired. Please reconnect.")

    except TokenRevokedError:
        await mark_watcher_degraded(supabase, user_id, yacht_id, "Token revoked")
        raise HTTPException(status_code=401, detail="Email connection revoked. Please reconnect.")

    except TokenRefreshError as e:
        # Refresh failed - mark watcher degraded
        error_msg = str(e)
        await mark_watcher_degraded(supabase, user_id, yacht_id, f"Token refresh failed: {error_msg}")
        logger.error(f"[email/render] Token refresh failed: {error_msg}")
        raise HTTPException(status_code=401, detail="Email connection expired and refresh failed. Please reconnect.")

    except GraphApiError as e:
        # Graph API returned an error after retry
        error_msg = str(e)
        if e.status_code == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph API 401: {error_msg}")
            raise HTTPException(status_code=401, detail="Microsoft rejected the request. Please reconnect your Outlook account.")
        elif e.status_code == 404:
            # Message deleted in Outlook - mark as soft deleted in our DB
            from datetime import datetime, timezone
            try:
                supabase.table('email_messages').update({
                    'is_deleted': True,
                    'deleted_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('provider_message_id', provider_message_id).eq(
                    'yacht_id', yacht_id
                ).execute()
                logger.info(f"[email/render] ✓ Auto-marked {provider_message_id[:16]}... as deleted (404 from Graph)")
            except Exception as mark_error:
                logger.error(f"[email/render] Failed to mark message as deleted: {mark_error}")
            raise HTTPException(status_code=404, detail="Message not found in Outlook. It has been removed from your inbox.")
        else:
            logger.error(f"[email/render] Graph API error {e.status_code}: {error_msg}")
            raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {error_msg}")

    except TokenPurposeMismatchError as e:
        logger.error(f"[email/render] Token purpose mismatch: {e}")
        raise HTTPException(status_code=500, detail="Internal configuration error")

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        graph_status = None
        # Check if it's an HTTP error from httpx
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            graph_status = e.response.status_code
            if graph_status == 401:
                await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph 401: {error_msg}")
                raise HTTPException(status_code=401, detail="Microsoft rejected the request. Please reconnect.")
            elif graph_status == 404:
                # Message deleted in Outlook - mark as soft deleted in our DB
                from datetime import datetime, timezone
                try:
                    supabase.table('email_messages').update({
                        'is_deleted': True,
                        'deleted_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('provider_message_id', provider_message_id).eq(
                        'yacht_id', yacht_id
                    ).execute()
                    logger.info(f"[email/render] ✓ Auto-marked {provider_message_id[:16]}... as deleted (404 from Graph)")
                except Exception as mark_error:
                    logger.error(f"[email/render] Failed to mark message as deleted: {mark_error}")
                raise HTTPException(status_code=404, detail="Message not found in Outlook. It has been removed from your inbox.")
            elif graph_status == 403:
                raise HTTPException(status_code=403, detail="Access denied to this message.")
        logger.error(f"[email/render] Unexpected error ({error_type}, graph_status={graph_status}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch message content")


# ============================================================================
# GET /email/message/:message_id/attachments - List Attachments (M7)
# ============================================================================

class AttachmentListItem(BaseModel):
    link_id: str
    blob_id: str
    name: str
    content_type: Optional[str]
    size_bytes: Optional[int]
    is_inline: bool
    provider_attachment_id: Optional[str]


@router.get("/message/{message_id}/attachments")
async def list_message_attachments(
    message_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    List attachments for a message (from DB, no content bytes).

    M7: Returns attachment metadata from email_attachment_links + email_attachment_blobs.
    No content bytes returned - use /download endpoint to fetch actual content from Graph.

    SOC-2 aligned: No body/content storage.
    """
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Verify message exists and belongs to yacht
    msg_result = supabase.table('email_messages').select(
        'id, provider_message_id, has_attachments'
    ).eq('id', message_id).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    message = msg_result.data

    # If no attachments, return empty list early
    if not message.get('has_attachments'):
        return {
            'message_id': message_id,
            'provider_message_id': message['provider_message_id'],
            'attachments': [],
            'count': 0,
        }

    try:
        # Query email_attachments_view (joins links + blobs)
        attachments_result = supabase.table('email_attachments_view').select(
            'link_id, blob_id, name, content_type, size_bytes, is_inline, provider_attachment_id'
        ).eq('message_id', message_id).eq('yacht_id', yacht_id).execute()

        attachments = []
        for row in (attachments_result.data or []):
            attachments.append({
                'link_id': row['link_id'],
                'blob_id': row['blob_id'],
                'name': row['name'],
                'content_type': row.get('content_type'),
                'size_bytes': row.get('size_bytes'),
                'is_inline': row.get('is_inline', False),
                'provider_attachment_id': row.get('provider_attachment_id'),
            })

        logger.info(
            f"[email/attachments] yacht={yacht_id[:8]} message={message_id[:8]} "
            f"count={len(attachments)}"
        )

        return {
            'message_id': message_id,
            'provider_message_id': message['provider_message_id'],
            'attachments': attachments,
            'count': len(attachments),
        }

    except Exception as e:
        logger.error(f"[email/attachments] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list attachments")


# ============================================================================
# GET /email/message/:provider_message_id/attachments/:attachment_id/download - Streaming Download (M7)
# ============================================================================

from fastapi.responses import StreamingResponse
import base64
import re


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for Content-Disposition header (prevent injection)."""
    # Remove path separators and null bytes
    filename = re.sub(r'[/\\:\x00]', '_', filename)
    # Limit length
    if len(filename) > 255:
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        filename = filename[:250] + ('.' + ext if ext else '')
    return filename


# Safe content types for inline viewing (PDFs and images)
INLINE_SAFE_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/tiff',
    'image/svg+xml',
}


@router.get("/message/{provider_message_id}/attachments/{attachment_id}/download")
async def download_attachment(
    provider_message_id: str,
    attachment_id: str,
    inline: bool = False,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Download attachment content by streaming from Graph.

    M7 Doctrine:
    - Content is NOT stored - proxied directly from Microsoft Graph
    - Uses READ token exclusively
    - Size limit enforced (MAX_ATTACHMENT_SIZE_BYTES)
    - Content type whitelist enforced (ALLOWED_ATTACHMENT_TYPES)
    - Content-Disposition header with sanitized filename

    Query params:
    - inline: If true and content type is safe (PDF/images), sets Content-Disposition: inline
              for in-browser viewing instead of download

    Error codes:
    - 401: Token expired/revoked/not found
    - 404: Message or attachment not found
    - 413: Attachment too large
    - 415: Content type not allowed
    - 502: Graph API error
    - 503: Feature disabled
    """
    enabled, error_msg = check_email_feature('render')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Verify message belongs to user's yacht
    msg_result = supabase.table('email_messages').select('id').eq(
        'provider_message_id', provider_message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        # Use READ client to get attachment
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(provider_message_id, attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        # Extract metadata
        filename = attachment.get('name', 'attachment')
        content_type = attachment.get('contentType', 'application/octet-stream')
        size_bytes = attachment.get('size', 0)
        content_b64 = attachment.get('contentBytes')

        if not content_b64:
            raise HTTPException(status_code=404, detail="Attachment has no content")

        # M7: Size limit enforcement
        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            logger.warning(
                f"[email/download] Attachment too large: {size_bytes} bytes "
                f"message={provider_message_id[:16]} attachment={attachment_id[:16]}"
            )
            raise HTTPException(
                status_code=413,
                detail=f"Attachment too large ({size_bytes // (1024*1024)} MB). "
                       f"Maximum allowed: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB"
            )

        # M7: Content type enforcement
        if content_type not in ALLOWED_ATTACHMENT_TYPES:
            logger.warning(
                f"[email/download] Content type not allowed: {content_type} "
                f"message={provider_message_id[:16]} attachment={attachment_id[:16]}"
            )
            raise HTTPException(
                status_code=415,
                detail=f"Content type '{content_type}' is not allowed for download"
            )

        # Decode content
        try:
            file_data = base64.b64decode(content_b64)
        except Exception as decode_error:
            logger.error(f"[email/download] Failed to decode content: {decode_error}")
            raise HTTPException(status_code=502, detail="Failed to decode attachment content")

        # Double-check decoded size
        if len(file_data) > MAX_ATTACHMENT_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Attachment too large after decode. Maximum: {MAX_ATTACHMENT_SIZE_BYTES // (1024*1024)} MB"
            )

        # Sanitize filename for header
        safe_filename = sanitize_filename(filename)

        # Determine Content-Disposition based on inline flag and content type
        if inline and content_type.lower() in INLINE_SAFE_TYPES:
            disposition = f'inline; filename="{safe_filename}"'
            disposition_type = 'inline'
        else:
            disposition = f'attachment; filename="{safe_filename}"'
            disposition_type = 'attachment'

        logger.info(
            f"[email/download] Serving: {safe_filename} ({len(file_data)} bytes) "
            f"type={content_type} disposition={disposition_type} user={user_id[:8]}"
        )

        # Stream response (no storage)
        def content_generator():
            yield file_data

        return StreamingResponse(
            content_generator(),
            media_type=content_type,
            headers={
                'Content-Disposition': disposition,
                'Content-Length': str(len(file_data)),
                'X-Content-Type-Options': 'nosniff',  # Prevent MIME sniffing
            }
        )

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected. Please connect your Outlook account.")

    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired. Please reconnect.")

    except TokenRevokedError:
        await mark_watcher_degraded(supabase, user_id, yacht_id, "Token revoked during download")
        raise HTTPException(status_code=401, detail="Email connection revoked. Please reconnect.")

    except TokenRefreshError as e:
        await mark_watcher_degraded(supabase, user_id, yacht_id, f"Token refresh failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Email connection expired and refresh failed. Please reconnect.")

    except GraphApiError as e:
        if e.status_code == 401:
            await mark_watcher_degraded(supabase, user_id, yacht_id, f"Graph API 401: {str(e)}")
            raise HTTPException(status_code=401, detail="Microsoft rejected the request. Please reconnect.")
        elif e.status_code == 404:
            raise HTTPException(status_code=404, detail="Attachment not found in Outlook")
        else:
            logger.error(f"[email/download] Graph API error {e.status_code}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Microsoft Graph error: {str(e)}")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[email/download] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download attachment")


# ============================================================================
# POST /email/link/add - Generic Link Creation (M8)
# ============================================================================

# Valid target object types (must match DB constraint)
VALID_LINK_OBJECT_TYPES = ['work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier']

# Table mapping for object existence checks
OBJECT_TYPE_TABLE_MAP = {
    'work_order': 'pms_work_orders',
    'equipment': 'pms_equipment',
    'part': 'pms_parts',
    'fault': 'pms_faults',
    'purchase_order': 'pms_purchase_orders',
    'supplier': 'pms_suppliers',
}


class LinkAddRequest(BaseModel):
    thread_id: str = Field(..., description="UUID of the email thread to link")
    object_type: str = Field(..., description="Target type: work_order, equipment, part, fault, purchase_order, supplier")
    object_id: str = Field(..., description="UUID of the target object")
    reason: Optional[str] = Field(None, description="Reason for linking (token_match, vendor_domain, wo_pattern, po_pattern, serial_match, part_number, manual)")
    idempotency_key: Optional[str] = Field(None, description="Client-generated key for idempotency")


@router.post("/link/add")
@router.post("/link/create")  # Alias for backward compatibility
async def add_link(
    request: LinkAddRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Add a new email link to any target object.

    M8: Generic link creation for all object types:
    - work_order, equipment, part, fault, purchase_order, supplier

    Behavior:
    - Validates object_type against allowed values
    - Verifies thread exists and belongs to yacht (RLS)
    - Verifies target object exists (optional but recommended)
    - Idempotent: returns already_exists if link tuple exists
    - Writes audit log with who/what/when/why

    Response:
    - { link_id: string, status: "created" | "already_exists" }
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # M8: Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[email/link/add] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to add links")

    # M8: Validate object_type
    if request.object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid object_type '{request.object_type}'. Must be one of: {VALID_LINK_OBJECT_TYPES}"
        )

    # M8: Validate reason if provided
    valid_reasons = ['token_match', 'vendor_domain', 'wo_pattern', 'po_pattern', 'serial_match', 'part_number', 'manual']
    reason = request.reason or 'manual'
    if reason not in valid_reasons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reason '{reason}'. Must be one of: {valid_reasons}"
        )

    try:
        # M8: Idempotency check via audit log
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_ADD')
            if cached:
                return {
                    'link_id': cached.get('link_id'),
                    'status': cached.get('status', 'created'),
                    'cached': True,
                }

        # M8: Verify thread exists and belongs to yacht (RLS enforced)
        thread_result = supabase.table('email_threads').select('id').eq(
            'id', request.thread_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found or access denied")

        # M8: Verify target object exists (with RLS)
        target_table = OBJECT_TYPE_TABLE_MAP.get(request.object_type)
        if target_table:
            try:
                target_result = supabase.table(target_table).select('id').eq(
                    'id', request.object_id
                ).eq('yacht_id', yacht_id).maybe_single().execute()

                if not target_result.data:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{request.object_type.replace('_', ' ').title()} not found or access denied"
                    )
            except HTTPException:
                raise
            except Exception as e:
                # Target table might not have yacht_id or might not exist
                logger.warning(f"[email/link/add] Target check failed (non-fatal): {e}")

        # M8: Check for existing active link (idempotency via unique constraint)
        existing_result = supabase.table('email_links').select('id').eq(
            'yacht_id', yacht_id
        ).eq('thread_id', request.thread_id).eq(
            'object_type', request.object_type
        ).eq('object_id', request.object_id).eq('is_active', True).limit(1).execute()

        if existing_result.data:
            existing_link_id = existing_result.data[0]['id']
            logger.info(
                f"[email/link/add] Already exists: link={existing_link_id[:8]} "
                f"thread={request.thread_id[:8]} → {request.object_type}={request.object_id[:8]}"
            )

            # M8: Audit even for already_exists (shows intent)
            await audit_link_action(
                supabase, yacht_id, user_id, 'EMAIL_LINK_ADD_DUPLICATE', existing_link_id,
                old_values={},
                new_values={
                    'link_id': existing_link_id,
                    'status': 'already_exists',
                    'thread_id': request.thread_id,
                    'object_type': request.object_type,
                    'object_id': request.object_id,
                },
                idempotency_key=request.idempotency_key,
                user_role=user_role,
            )

            return {
                'link_id': existing_link_id,
                'status': 'already_exists',
            }

        # M8: Create new link
        insert_result = supabase.table('email_links').insert({
            'yacht_id': yacht_id,
            'thread_id': request.thread_id,
            'object_type': request.object_type,
            'object_id': request.object_id,
            'confidence': 'user_confirmed',
            'suggested_reason': reason,
            'suggested_at': datetime.utcnow().isoformat(),
            'accepted_at': datetime.utcnow().isoformat(),
            'accepted_by': user_id,
            'is_active': True,
        }).execute()

        new_link_id = insert_result.data[0]['id'] if insert_result.data else None

        if not new_link_id:
            raise HTTPException(status_code=500, detail="Failed to create link")

        # M8: Audit the creation
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ADD', new_link_id,
            old_values={},
            new_values={
                'link_id': new_link_id,
                'status': 'created',
                'thread_id': request.thread_id,
                'object_type': request.object_type,
                'object_id': request.object_id,
                'reason': reason,
            },
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        logger.info(
            f"[email/link/add] Created: link={new_link_id[:8]} "
            f"thread={request.thread_id[:8]} → {request.object_type}={request.object_id[:8]} "
            f"user={user_id[:8]} reason={reason}"
        )

        return {
            'link_id': new_link_id,
            'status': 'created',
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/add] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add link")


# ============================================================================
# POST /email/link/accept
# ============================================================================

@router.post("/link/accept")
async def accept_link(
    request: LinkAcceptRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Accept a suggested email link.

    M4 Hardening:
    - Role-based access control (LINK_MANAGE_ROLES)
    - Idempotency support via client-provided key
    - Enhanced audit logging

    Changes confidence from 'suggested' to 'user_confirmed'.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # M4: Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[email/link/accept] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to accept links")

    try:
        # M4: Idempotency check
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_ACCEPT')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        link = link_result.data

        # Idempotent: Already accepted is success
        if link['confidence'] == 'user_confirmed':
            logger.info(f"[email/link/accept] Already accepted: link={request.link_id[:8]}")
            return {'success': True, 'link_id': request.link_id, 'already_accepted': True}

        if link['confidence'] != 'suggested':
            raise HTTPException(status_code=400, detail="Link is not in suggested state")

        # Update link
        supabase.table('email_links').update({
            'confidence': 'user_confirmed',
            'accepted_at': datetime.utcnow().isoformat(),
            'accepted_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # M4: Enhanced audit
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_ACCEPT', request.link_id,
            old_values={'confidence': 'suggested'},
            new_values={'confidence': 'user_confirmed'},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/accept] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept link")


# ============================================================================
# POST /email/link/change
# ============================================================================

@router.post("/link/change")
async def change_link(
    request: LinkChangeRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Change a link's target object.

    M4 Hardening:
    - Role-based access control (LINK_MANAGE_ROLES)
    - Idempotency support
    - Enhanced audit logging

    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # M4: Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[email/link/change] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to change links")

    # Validate object_type (use shared constant for consistency)
    if request.new_object_type not in VALID_LINK_OBJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {VALID_LINK_OBJECT_TYPES}")

    try:
        # M4: Idempotency check
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_CHANGE')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        # Idempotent: Already pointing to same target is success
        if old_link['object_type'] == request.new_object_type and old_link['object_id'] == request.new_object_id:
            logger.info(f"[email/link/change] No change needed: link={request.link_id[:8]}")
            return {'success': True, 'link_id': request.link_id, 'no_change': True}

        # Update link
        supabase.table('email_links').update({
            'object_type': request.new_object_type,
            'object_id': request.new_object_id,
            'confidence': 'user_confirmed',
            'modified_at': datetime.utcnow().isoformat(),
            'modified_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # M4: Enhanced audit
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_CHANGE', request.link_id,
            old_values={
                'object_type': old_link['object_type'],
                'object_id': old_link['object_id'],
            },
            new_values={
                'object_type': request.new_object_type,
                'object_id': request.new_object_id,
            },
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/change] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change link")


# ============================================================================
# POST /email/link/remove
# ============================================================================

@router.post("/link/remove")
async def remove_link(
    request: LinkRemoveRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Remove a link (soft delete).

    M4 Hardening:
    - Role-based access control (LINK_MANAGE_ROLES)
    - Idempotency support
    - Enhanced audit logging

    Sets is_active=False. Does NOT delete.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # M4: Role check
    if user_role not in LINK_MANAGE_ROLES:
        logger.warning(f"[email/link/remove] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to remove links")

    try:
        # M4: Idempotency check
        if request.idempotency_key:
            cached = await check_idempotency(supabase, yacht_id, request.idempotency_key, 'EMAIL_LINK_REMOVE')
            if cached:
                return {'success': True, 'link_id': request.link_id, 'cached': True}

        # Get current link state (yacht_id enforced)
        # Note: We check for the link regardless of is_active for idempotency
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        old_link = link_result.data

        # Idempotent: Already removed is success
        if not old_link.get('is_active', True):
            logger.info(f"[email/link/remove] Already removed: link={request.link_id[:8]}")
            return {'success': True, 'link_id': request.link_id, 'already_removed': True}

        # Soft delete
        supabase.table('email_links').update({
            'is_active': False,
            'removed_at': datetime.utcnow().isoformat(),
            'removed_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # M4: Enhanced audit
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_REMOVE', request.link_id,
            old_values={
                'is_active': True,
                'thread_id': old_link['thread_id'],
                'object_type': old_link['object_type'],
                'object_id': old_link['object_id'],
            },
            new_values={'is_active': False},
            idempotency_key=request.idempotency_key,
            user_role=user_role,
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/remove] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove link")


# ============================================================================
# POST /email/link/reject
# ============================================================================

@router.post("/link/reject")
async def reject_link(
    request: LinkRejectRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Reject a suggested email link.

    Changes confidence from 'suggested' to 'rejected'.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get current link state (yacht_id enforced)
        link_result = supabase.table('email_links').select('*').eq(
            'id', request.link_id
        ).eq('yacht_id', yacht_id).eq('is_active', True).maybe_single().execute()

        if not link_result.data:
            raise HTTPException(status_code=404, detail="Link not found")

        link = link_result.data

        if link['confidence'] != 'suggested':
            raise HTTPException(status_code=400, detail="Only suggested links can be rejected")

        # Update link to rejected
        update_result = supabase.table('email_links').update({
            'confidence': 'rejected',
            'rejected_at': datetime.utcnow().isoformat(),
            'rejected_by': user_id,
            'updated_at': datetime.utcnow().isoformat(),
        }).eq('id', request.link_id).eq('yacht_id', yacht_id).execute()

        # Audit the action
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_REJECT', request.link_id,
            old_values={'confidence': 'suggested'},
            new_values={'confidence': 'rejected'},
        )

        return {'success': True, 'link_id': request.link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/reject] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject link")


# ============================================================================
# POST /email/link/create
# ============================================================================

@router.post("/link/create")
async def create_link(
    request: LinkCreateRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Create a new email-object link manually.

    Allows users to link any thread to WO, equipment, part, fault, PO, or supplier.
    Audited to pms_audit_log.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Validate object_type
    valid_types = ['work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier']
    if request.object_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid object_type. Must be one of: {valid_types}")

    try:
        # Verify thread exists and belongs to this yacht
        thread_result = supabase.table('email_threads').select('id').eq(
            'id', request.thread_id
        ).eq('yacht_id', yacht_id).maybe_single().execute()

        if not thread_result.data:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Check if link already exists
        existing = supabase.table('email_links').select('id').eq(
            'thread_id', request.thread_id
        ).eq('object_type', request.object_type).eq(
            'object_id', request.object_id
        ).eq('is_active', True).maybe_single().execute()

        if existing.data:
            raise HTTPException(status_code=400, detail="Link already exists")

        # Verify target object exists (based on type)
        table_map = {
            'work_order': 'pms_work_orders',
            'equipment': 'pms_equipment',
            'part': 'pms_parts',
            'fault': 'pms_faults',
            'purchase_order': 'pms_purchase_orders',
            'supplier': 'pms_suppliers',
        }
        target_table = table_map.get(request.object_type)
        if target_table:
            target_result = supabase.table(target_table).select('id').eq(
                'id', request.object_id
            ).eq('yacht_id', yacht_id).maybe_single().execute()

            if not target_result.data:
                raise HTTPException(status_code=404, detail=f"{request.object_type} not found")

        # Create the link
        new_link = supabase.table('email_links').insert({
            'yacht_id': yacht_id,
            'thread_id': request.thread_id,
            'object_type': request.object_type,
            'object_id': request.object_id,
            'confidence': 'user_confirmed',
            'suggested_reason': 'user_created',
            'is_active': True,
            'accepted_at': datetime.utcnow().isoformat(),
            'accepted_by': user_id,
        }).execute()

        link_id = new_link.data[0]['id'] if new_link.data else None

        # Audit the action
        await audit_link_action(
            supabase, yacht_id, user_id, 'EMAIL_LINK_CREATE', link_id or '',
            old_values=None,
            new_values={
                'thread_id': request.thread_id,
                'object_type': request.object_type,
                'object_id': request.object_id,
            },
        )

        return {'success': True, 'link_id': link_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/link/create] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create link")


# ============================================================================
# GET /email/inbox - Get email threads for inbox view
# ============================================================================

@router.get("/inbox")
async def get_inbox_threads(
    page: int = 1,
    page_size: int = 20,
    linked: bool = False,
    q: str = None,
    direction: str = None,  # 'inbound', 'outbound', or None for both
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get email threads for the inbox view.

    By default returns unlinked threads (for manual linking).
    Set linked=true to include all threads.
    Set q to filter by subject/sender (uses orchestration layer for semantic search).
    Set direction to filter by inbound/outbound.

    When q is provided:
    - Uses hybrid search (SQL text match + vector similarity if embeddings exist)
    - Searches subject, sender name, and attachment names
    - Groups results by thread
    """
    enabled, error_msg = check_email_feature('related')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        offset = (page - 1) * page_size

        # If search query provided, use orchestration layer
        if q and len(q) >= 2:
            return await _search_email_threads(
                supabase, yacht_id, user_id, q, direction, page, page_size, linked
            )

        # No search query - simple inbox scan
        # Note: direction is on email_messages, not email_threads.
        # Use last_inbound_at/last_outbound_at to filter by thread direction.
        # DIAGNOSTIC: Include yacht_id in response to verify tenant filtering
        base_query = supabase.table('email_threads').select(
            'id, yacht_id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at, created_at, last_inbound_at, last_outbound_at',
            count='exact'
        ).eq('yacht_id', yacht_id)

        # Apply direction filter using timestamp columns
        # inbound = threads that have received messages (last_inbound_at not null)
        # outbound = threads that have sent messages (last_outbound_at not null)
        if direction == 'inbound':
            base_query = base_query.not_.is_('last_inbound_at', 'null')
        elif direction == 'outbound':
            base_query = base_query.not_.is_('last_outbound_at', 'null')

        if linked:
            # All threads
            result = base_query.order(
                'last_activity_at', desc=True
            ).range(offset, offset + page_size - 1).execute()
        else:
            # Only unlinked threads - try RPC first, fallback to manual filter
            result = None
            try:
                result = supabase.rpc('get_unlinked_email_threads', {
                    'p_yacht_id': yacht_id,
                    'p_limit': page_size,
                    'p_offset': offset,
                    'p_search': ''
                }).execute()
            except Exception as rpc_err:
                logger.debug(f"[email/inbox] RPC not available, using fallback: {rpc_err}")
                result = None

            # Fallback if RPC doesn't exist or returns no data
            if not result or not result.data:
                # DIAGNOSTIC: Include yacht_id in fallback response
                fallback_query = supabase.table('email_threads').select(
                    'id, yacht_id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at, created_at, last_inbound_at, last_outbound_at'
                ).eq('yacht_id', yacht_id)

                # Apply direction filter to fallback using timestamp columns
                if direction == 'inbound':
                    fallback_query = fallback_query.not_.is_('last_inbound_at', 'null')
                elif direction == 'outbound':
                    fallback_query = fallback_query.not_.is_('last_outbound_at', 'null')

                all_threads = fallback_query.order(
                    'last_activity_at', desc=True
                ).limit(100).execute()

                linked_result = supabase.table('email_links').select(
                    'thread_id'
                ).eq('yacht_id', yacht_id).eq('is_active', True).execute()

                linked_ids = {l['thread_id'] for l in (linked_result.data or [])}
                unlinked = [t for t in (all_threads.data or []) if t['id'] not in linked_ids]

                # Create a simple result-like object
                class FallbackResult:
                    def __init__(self, data, count):
                        self.data = data
                        self.count = count

                result = FallbackResult(
                    data=unlinked[offset:offset + page_size],
                    count=len(unlinked)
                )

        threads = result.data or []
        total = result.count if hasattr(result, 'count') and result.count else len(threads)

        return {
            'threads': threads,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': offset + len(threads) < total,
        }

    except Exception as e:
        logger.error(f"[email/inbox] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch inbox")


def _extract_query_entities(query: str) -> Dict[str, List[str]]:
    """
    Extract entity IDs from search query using regex patterns.
    Returns dict of entity_type -> list of IDs found.
    """
    import re

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

    extracted = {}
    for entity_type, pattern_list in patterns.items():
        matches = []
        for pattern in pattern_list:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                # Get the captured group (just the number)
                matches.append(match.group(1))
        if matches:
            extracted[entity_type] = list(set(matches))

    return extracted


async def _search_email_threads(
    supabase,
    yacht_id: str,
    user_id: str,
    query: str,
    direction: str,
    page: int,
    page_size: int,
    include_linked: bool,
) -> Dict[str, Any]:
    """
    Search email threads using hybrid search with entity extraction.

    Search layers (in priority order):
    1. Entity ID match (WO-###, PO-###, etc.) in extracted_tokens
    2. SQL text match on subject and sender
    3. Vector semantic search on meta_embedding (if available)

    Returns results grouped by thread.
    """
    offset = (page - 1) * page_size
    thread_ids_with_scores = {}
    search_mode = 'text'
    extracted_entities = {}

    # =========================================================================
    # Layer 1: Entity Extraction & Token Search
    # =========================================================================
    extracted_entities = _extract_query_entities(query)

    if extracted_entities:
        logger.info(f"[email/search] Extracted entities: {extracted_entities}")
        search_mode = 'entity'

        # Search email_threads.extracted_tokens JSONB
        for entity_type, ids in extracted_entities.items():
            for entity_id in ids:
                # Build token pattern to search for (e.g., "WO-123")
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
                    # Search in email_threads.extracted_tokens
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

                    # Also search in subject line directly
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

    # =========================================================================
    # Layer 2: SQL Text Match on Subject and Sender
    # =========================================================================
    text_results = supabase.table('email_messages').select(
        'id, thread_id, subject, from_display_name, direction, sent_at, has_attachments'
    ).eq('yacht_id', yacht_id).eq(
        'is_deleted', False  # Filter out deleted messages
    ).or_(
        f"subject.ilike.%{query}%,from_display_name.ilike.%{query}%"
    )

    # Add direction filter if specified
    if direction in ('inbound', 'outbound'):
        text_results = text_results.eq('direction', direction)

    text_results = text_results.order('sent_at', desc=True).limit(100).execute()

    # Add text matches to results
    for msg in (text_results.data or []):
        tid = msg.get('thread_id')
        if tid and tid not in thread_ids_with_scores:
            thread_ids_with_scores[tid] = {
                'thread_id': tid,
                'sent_at': msg.get('sent_at'),
                'match_type': 'text',
            }
            if search_mode == 'text':
                search_mode = 'text'
            elif search_mode == 'entity':
                search_mode = 'hybrid'

    # =========================================================================
    # Layer 3: Vector Search (if embeddings exist)
    # =========================================================================
    try:
        # Check if any emails have meta_embedding
        has_embeddings = supabase.table('email_messages').select('id').eq(
            'yacht_id', yacht_id
        ).not_.is_('meta_embedding', 'null').limit(1).execute()

        if has_embeddings.data:
            # TODO: Implement pgvector search using match_email_messages RPC
            # This would add vector similarity matches to thread_ids_with_scores
            # For now, embeddings are populated but vector search not yet integrated
            if search_mode in ('text', 'entity'):
                search_mode = search_mode + '_partial_vector'
    except Exception as e:
        logger.debug(f"Vector search not available: {e}")

    # Get thread details for matching threads
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

    # Filter out linked threads if needed
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

    # Get thread details
    threads_result = supabase.table('email_threads').select(
        'id, provider_conversation_id, latest_subject, message_count, has_attachments, source, last_activity_at, created_at'
    ).eq('yacht_id', yacht_id).in_('id', thread_ids).order(
        'last_activity_at', desc=True
    ).execute()

    threads = threads_result.data or []
    total = len(threads)

    # Paginate
    paginated = threads[offset:offset + page_size]

    # Add match info to threads
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


# ============================================================================
# GET /email/search-objects - Search linkable objects
# ============================================================================

@router.get("/search-objects")
async def search_linkable_objects(
    q: str,
    types: str = "work_order,equipment,part",
    limit: int = 10,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Search for objects that can be linked to emails.

    Args:
        q: Search query (min 2 chars)
        types: Comma-separated list of types to search
        limit: Max results per type

    Returns objects from work_orders, equipment, parts, faults, purchase_orders, suppliers.
    """
    enabled, error_msg = check_email_feature('link')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    if len(q) < 2:
        return {'results': []}

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    type_list = [t.strip() for t in types.split(',')]
    results = []

    try:
        # Search work orders
        if 'work_order' in type_list:
            wo_result = supabase.table('pms_work_orders').select(
                'id, title, status, wo_number'
            ).eq('yacht_id', yacht_id).or_(
                f"title.ilike.%{q}%,wo_number.ilike.%{q}%"
            ).limit(limit).execute()

            for wo in (wo_result.data or []):
                results.append({
                    'type': 'work_order',
                    'id': wo['id'],
                    'label': f"WO-{wo.get('wo_number', '')}: {wo.get('title', 'Untitled')}",
                    'status': wo.get('status'),
                })

        # Search equipment
        if 'equipment' in type_list:
            eq_result = supabase.table('pms_equipment').select(
                'id, name, serial_number, model'
            ).eq('yacht_id', yacht_id).or_(
                f"name.ilike.%{q}%,serial_number.ilike.%{q}%,model.ilike.%{q}%"
            ).limit(limit).execute()

            for eq in (eq_result.data or []):
                label = eq.get('name', 'Unknown')
                if eq.get('serial_number'):
                    label += f" (S/N: {eq['serial_number']})"
                results.append({
                    'type': 'equipment',
                    'id': eq['id'],
                    'label': label,
                })

        # Search parts
        if 'part' in type_list:
            parts_result = supabase.table('pms_parts').select(
                'id, name, part_number'
            ).eq('yacht_id', yacht_id).or_(
                f"name.ilike.%{q}%,part_number.ilike.%{q}%"
            ).limit(limit).execute()

            for part in (parts_result.data or []):
                label = part.get('name', 'Unknown')
                if part.get('part_number'):
                    label += f" (P/N: {part['part_number']})"
                results.append({
                    'type': 'part',
                    'id': part['id'],
                    'label': label,
                })

        # Search faults
        if 'fault' in type_list:
            fault_result = supabase.table('pms_faults').select(
                'id, title, status'
            ).eq('yacht_id', yacht_id).ilike(
                'title', f'%{q}%'
            ).limit(limit).execute()

            for fault in (fault_result.data or []):
                results.append({
                    'type': 'fault',
                    'id': fault['id'],
                    'label': fault.get('title', 'Untitled'),
                    'status': fault.get('status'),
                })

        # Search purchase orders
        if 'purchase_order' in type_list:
            po_result = supabase.table('pms_purchase_orders').select(
                'id, po_number, description, status'
            ).eq('yacht_id', yacht_id).or_(
                f"po_number.ilike.%{q}%,description.ilike.%{q}%"
            ).limit(limit).execute()

            for po in (po_result.data or []):
                results.append({
                    'type': 'purchase_order',
                    'id': po['id'],
                    'label': f"PO-{po.get('po_number', '')}: {po.get('description', '')}",
                    'status': po.get('status'),
                })

        # Search suppliers
        if 'supplier' in type_list:
            supplier_result = supabase.table('pms_suppliers').select(
                'id, name, category'
            ).eq('yacht_id', yacht_id).ilike(
                'name', f'%{q}%'
            ).limit(limit).execute()

            for supplier in (supplier_result.data or []):
                label = supplier.get('name', 'Unknown')
                if supplier.get('category'):
                    label += f" ({supplier['category']})"
                results.append({
                    'type': 'supplier',
                    'id': supplier['id'],
                    'label': label,
                })

        return {'results': results}

    except Exception as e:
        logger.error(f"[email/search-objects] Error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# ============================================================================
# POST /email/evidence/save-attachment
# ============================================================================

@router.post("/evidence/save-attachment")
async def save_attachment(
    request: SaveAttachmentRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Save an email attachment to documents storage.

    M4 Hardening:
    - Role-based access control (EVIDENCE_SAVE_ROLES)
    - File size limits (MAX_ATTACHMENT_SIZE_BYTES)
    - Content type whitelist (ALLOWED_ATTACHMENT_TYPES)
    - Idempotency support
    - Audit logging

    Uses READ token for Graph access.
    Stores to Supabase storage, creates doc_yacht_library entry.
    """
    enabled, error_msg = check_email_feature('evidence')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # M4: Role check
    if user_role not in EVIDENCE_SAVE_ROLES:
        logger.warning(f"[email/evidence/save-attachment] Forbidden: role={user_role} user={user_id[:8]}")
        raise HTTPException(status_code=403, detail="Insufficient permissions to save attachments")

    # M4: Idempotency check - use deterministic path prefix to detect duplicates
    # Path pattern: {yacht_id}/email-attachments/{message_id_hash}_{attachment_id_hash}/
    import hashlib
    msg_hash = hashlib.md5(request.message_id.encode()).hexdigest()[:12]
    att_hash = hashlib.md5(request.attachment_id.encode()).hexdigest()[:12]
    path_prefix = f"{yacht_id}/email-attachments/{msg_hash}_{att_hash}"

    if request.idempotency_key:
        existing = supabase.table('doc_yacht_library').select('id, document_path').eq(
            'yacht_id', yacht_id
        ).like('document_path', f'{path_prefix}%').limit(1).execute()

        if existing.data:
            logger.info(f"[email/evidence/save-attachment] Already saved: attachment={request.attachment_id[:16]}")
            return {
                'success': True,
                'document_id': existing.data[0]['id'],
                'storage_path': existing.data[0]['document_path'],
                'already_saved': True,
            }

    # Verify message belongs to user's yacht
    msg_result = supabase.table('email_messages').select('id, thread_id').eq(
        'provider_message_id', request.message_id
    ).eq('yacht_id', yacht_id).maybe_single().execute()

    if not msg_result.data:
        raise HTTPException(status_code=404, detail="Message not found")

    try:
        # Use READ client to get attachment (read operation)
        read_client = create_read_client(supabase, user_id, yacht_id)
        attachment = await read_client.get_attachment(request.message_id, request.attachment_id)

        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")

        # Get attachment content
        content_bytes = attachment.get('contentBytes')
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Attachment has no content")

        import base64
        file_data = base64.b64decode(content_bytes)

        # SECURITY FIX P0-007: Validate file size
        if len(file_data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )

        # SECURITY FIX P0-007: Validate and sanitize filename
        original_filename = attachment.get('name', 'attachment')
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # SECURITY FIX P0-007: Validate MIME type
        content_type = attachment.get('contentType', 'application/octet-stream')
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Content type '{content_type}' not allowed"
            )

        # SECURITY FIX P0-007: Generate safe storage path using deterministic prefix for idempotency
        safe_filename = f"{uuid.uuid4()}{ext}"
        storage_path = f"{path_prefix}/{safe_filename}"

        # Upload to storage
        supabase.storage.from_('documents').upload(
            storage_path, file_data,
            {'content-type': content_type}
        )

        # Create document entry using actual doc_yacht_library schema columns
        doc_entry = {
            'yacht_id': yacht_id,
            'document_name': original_filename,  # actual column name
            'document_path': storage_path,       # actual column name
            'document_type': content_type,       # maps content_type -> document_type
            'user_id': user_id,                  # actual column name (not created_by)
        }

        doc_result = supabase.table('doc_yacht_library').insert(doc_entry).execute()
        document_id = doc_result.data[0]['id'] if doc_result.data else None

        # M4: Audit logging
        try:
            supabase.table('pms_audit_log').insert({
                'yacht_id': yacht_id,
                'action': 'EMAIL_EVIDENCE_SAVED',
                'entity_type': 'document',
                'entity_id': document_id,
                'user_id': user_id,
                'old_values': {},
                'new_values': {
                    'filename': filename,
                    'content_type': content_type,
                    'file_size': len(file_data),
                    'email_message_id': request.message_id,
                },
                'signature': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_version': 'M4',
                    'user_role': user_role,
                    'idempotency_key': request.idempotency_key,
                },
            }).execute()
        except Exception as audit_error:
            logger.error(f"[email/evidence/save-attachment] Audit log failed: {audit_error}")

        logger.info(
            f"[email/evidence/save-attachment] Saved: doc={document_id[:8] if document_id else 'N/A'} "
            f"size={len(file_data)} type={content_type} user={user_id[:8]}"
        )

        # M5: Auto-link attachment to thread's confirmed links
        auto_linked_objects = []
        if document_id and msg_result.data.get('thread_id'):
            thread_id = msg_result.data['thread_id']
            try:
                # Get confirmed/accepted links for this thread
                thread_links = supabase.table('email_links').select(
                    'object_type, object_id'
                ).eq('yacht_id', yacht_id).eq('thread_id', thread_id).eq(
                    'is_active', True
                ).in_('confidence', ['deterministic', 'user_confirmed']).execute()

                for link in (thread_links.data or []):
                    try:
                        # Create attachment-object link
                        supabase.table('email_attachment_object_links').insert({
                            'yacht_id': yacht_id,
                            'document_id': document_id,
                            'object_type': link['object_type'],
                            'object_id': link['object_id'],
                            'link_reason': 'auto_from_thread',
                            'source_context': {
                                'email_thread_id': thread_id,
                                'email_message_id': request.message_id,
                            },
                            'is_active': True,
                            'created_by': user_id,
                        }).execute()
                        auto_linked_objects.append({
                            'object_type': link['object_type'],
                            'object_id': link['object_id'],
                        })
                        logger.info(
                            f"[email/evidence/save-attachment] Auto-linked: "
                            f"doc={document_id[:8]} → {link['object_type']}={link['object_id'][:8]}"
                        )
                    except Exception as link_error:
                        # Don't fail save if auto-link fails (might be duplicate)
                        logger.warning(f"[email/evidence/save-attachment] Auto-link skipped: {link_error}")
            except Exception as auto_link_error:
                logger.warning(f"[email/evidence/save-attachment] Auto-link lookup failed: {auto_link_error}")

        return {
            'success': True,
            'document_id': document_id,
            'storage_path': storage_path,
            'auto_linked': auto_linked_objects if auto_linked_objects else None,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail="Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/evidence/save-attachment] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save attachment")


# ============================================================================
# POST /email/sync/now (SERVICE ROLE ONLY)
# ============================================================================

@router.post("/sync/now")
async def sync_now(
    auth: dict = Depends(get_authenticated_user),
    full_resync: bool = False,
):
    """
    Manual sync trigger.

    Backfills 14 days of inbox + sent.
    Stores metadata into email_threads + email_messages.
    Updates email_watchers sync fields.

    Args:
        full_resync: If True, clears delta links to force full sync from scratch.
                     Use this to fetch emails that were missed by incremental sync.

    Requires service role or admin.
    """
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    role = auth.get('role', '')

    # Role check - only chief_engineer, manager, or service accounts can trigger sync
    allowed_roles = ['chief_engineer', 'manager', 'captain', 'admin']
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions for sync")

    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get watcher
        watcher_result = supabase.table('email_watchers').select('*').eq(
            'user_id', user_id
        ).eq('yacht_id', yacht_id).eq('provider', 'microsoft_graph').maybe_single().execute()

        if not watcher_result.data:
            raise HTTPException(status_code=400, detail="No email watcher configured")

        watcher = watcher_result.data

        # If full_resync, clear delta links to force full sync
        if full_resync:
            logger.info(f"[email/sync/now] Full resync requested - clearing delta links")
            supabase.table('email_watchers').update({
                'delta_link_inbox': None,
                'delta_link_sent': None,
            }).eq('id', watcher['id']).execute()
            watcher['delta_link_inbox'] = None
            watcher['delta_link_sent'] = None

        # Create read client
        read_client = create_read_client(supabase, user_id, yacht_id)

        # Sync inbox and sent
        stats = {'threads_created': 0, 'messages_created': 0, 'errors': [], 'full_resync': full_resync}

        for folder in ['inbox', 'sent']:
            delta_link = watcher.get(f'delta_link_{folder}')
            total_processed = 0
            max_messages = 500 if full_resync else 100  # Fetch more on full resync

            try:
                # Get messages with pagination
                while total_processed < max_messages:
                    result = await read_client.list_messages(
                        folder=folder,
                        top=min(100, max_messages - total_processed),
                        delta_link=delta_link,
                        select=['id', 'conversationId', 'subject', 'from', 'toRecipients', 'ccRecipients',
                                'receivedDateTime', 'sentDateTime', 'hasAttachments', 'internetMessageId',
                                'bodyPreview'],  # Added for RAG embedding generation
                    )

                    messages = result.get('messages', [])
                    if not messages:
                        break

                    # Process messages
                    for msg in messages:
                        try:
                            await _process_message(supabase, yacht_id, msg, folder)
                            stats['messages_created'] += 1
                            total_processed += 1
                        except Exception as e:
                            stats['errors'].append(f"Message {msg.get('id')}: {str(e)}")

                    # Check for next page or delta link
                    next_link = result.get('next_link')
                    new_delta = result.get('delta_link')

                    if new_delta:
                        # Save delta link and exit loop
                        supabase.table('email_watchers').update({
                            f'delta_link_{folder}': new_delta,
                        }).eq('id', watcher['id']).execute()
                        break
                    elif next_link:
                        # Use next_link as delta_link to continue pagination
                        delta_link = next_link
                    else:
                        break

            except Exception as e:
                stats['errors'].append(f"Folder {folder}: {str(e)}")

        # Update watcher sync status
        supabase.table('email_watchers').update({
            'last_sync_at': datetime.utcnow().isoformat(),
            'last_sync_error': stats['errors'][-1] if stats['errors'] else None,
            'sync_status': 'degraded' if stats['errors'] else 'active',
        }).eq('id', watcher['id']).execute()

        return {
            'success': True,
            'stats': stats,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail="Email connection revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/sync/now] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


async def _process_message(supabase, yacht_id: str, msg: Dict, folder: str):
    """Process a single message from Graph into DB."""
    conversation_id = msg.get('conversationId')
    if not conversation_id:
        return

    # Get or create thread
    thread_result = supabase.table('email_threads').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_conversation_id', conversation_id).maybe_single().execute()

    if thread_result and thread_result.data:
        thread_id = thread_result.data['id']
    else:
        # Create thread
        thread_insert = supabase.table('email_threads').insert({
            'yacht_id': yacht_id,
            'provider_conversation_id': conversation_id,
            'latest_subject': msg.get('subject'),
            'message_count': 0,
            'has_attachments': msg.get('hasAttachments', False),
            'source': 'external',
        }).execute()
        if not thread_insert or not thread_insert.data:
            raise Exception(f"Failed to create thread for conversation {conversation_id[:20]}...")
        thread_id = thread_insert.data[0]['id']

    # Hash email addresses
    from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
    from_hash = hashlib.sha256(from_addr.lower().encode()).hexdigest() if from_addr else ''
    from_name = msg.get('from', {}).get('emailAddress', {}).get('name', '')

    to_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]
    to_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in to_addrs if a]

    cc_addrs = [r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]
    cc_hashes = [hashlib.sha256(a.lower().encode()).hexdigest() for a in cc_addrs if a]

    # Determine direction
    direction = 'outbound' if folder == 'sent' else 'inbound'

    # Check if message already exists
    existing = supabase.table('email_messages').select('id').eq(
        'yacht_id', yacht_id
    ).eq('provider_message_id', msg.get('id')).maybe_single().execute()

    if existing and existing.data:
        return  # Already processed

    # Extract preview text (first 200 chars per SOC-2 doctrine)
    body_preview = msg.get('bodyPreview', '') or ''
    preview_text = body_preview[:200] if body_preview else None

    # Insert message
    insert_result = supabase.table('email_messages').insert({
        'thread_id': thread_id,
        'yacht_id': yacht_id,
        'provider_message_id': msg.get('id'),
        'internet_message_id': msg.get('internetMessageId'),
        'direction': direction,
        'from_address_hash': from_hash,
        'from_display_name': from_name,
        'to_addresses_hash': to_hashes,
        'cc_addresses_hash': cc_hashes,
        'subject': msg.get('subject'),
        'preview_text': preview_text,  # For RAG embedding generation
        'sent_at': msg.get('sentDateTime'),
        'received_at': msg.get('receivedDateTime'),
        'has_attachments': msg.get('hasAttachments', False),
        'folder': folder,
    }).execute()

    # Queue extraction job for RAG pipeline (M1: pipe entities to DB)
    # Note: DB trigger also queues, but explicit call ensures reliability
    if insert_result.data and preview_text:
        message_id = insert_result.data[0]['id']
        try:
            supabase.rpc('queue_email_extraction', {
                'p_message_id': message_id,
                'p_yacht_id': yacht_id,
                'p_job_type': 'full'
            }).execute()
            logger.debug(f"[email/sync] Queued extraction job for message {message_id[:8]}...")
        except Exception as e:
            # Non-fatal: trigger may have already queued, or worker will pick up later
            logger.warning(f"[email/sync] Failed to queue extraction job: {e}")

    # Update thread stats
    supabase.rpc('update_thread_activity', {
        'p_thread_id': thread_id,
        'p_sent_at': msg.get('sentDateTime') or msg.get('receivedDateTime'),
        'p_direction': direction,
        'p_subject': msg.get('subject'),
        'p_has_attachments': msg.get('hasAttachments', False),
    }).execute()

    # Generate link suggestions for new threads
    try:
        await generate_suggestions_for_thread(supabase, thread_id, yacht_id)
    except Exception as e:
        # Suggestion generation should not fail message processing
        logger.warning(f"Failed to generate suggestions for thread {thread_id}: {e}")


# ============================================================================
# POST /email/backfill-embeddings
# ============================================================================

@router.post("/backfill-embeddings")
async def backfill_embeddings(
    auth: dict = Depends(get_authenticated_user),
    limit: int = 100,
):
    """
    Backfill embeddings for emails missing them.

    Generates embeddings for emails that don't have meta_embedding set.
    Uses OpenAI text-embedding-3-small model.

    Args:
        limit: Maximum number of emails to process (default 100)

    Returns:
        Stats dict with processed/success/failed counts
    """
    from services.email_embedding_service import EmailEmbeddingUpdater

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        updater = EmailEmbeddingUpdater(supabase, yacht_id)

        if not updater.embedding_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Embedding service not available - check OPENAI_API_KEY"
            )

        stats = await updater.backfill_embeddings(limit=limit)

        logger.info(f"[email/backfill-embeddings] yacht={yacht_id[:8]}... stats={stats}")

        return {
            'success': True,
            'yacht_id': yacht_id,
            'stats': stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/backfill-embeddings] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backfill failed: {str(e)}")


# ============================================================================
# POST /email/backfill-weblinks
# ============================================================================

@router.post("/backfill-weblinks")
async def backfill_weblinks(
    auth: dict = Depends(get_authenticated_user),
    limit: int = 100,
):
    """
    Backfill webLink for emails missing them.

    Fetches webLink from Microsoft Graph API for emails that don't have web_link set.
    This enables "Open in Outlook" button in the UI.

    Args:
        limit: Maximum number of emails to process (default 100)

    Returns:
        Stats dict with processed/updated/skipped/failed counts
    """
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get messages without web_link
        messages_result = supabase.table('email_messages').select(
            'id, provider_message_id'
        ).eq('yacht_id', yacht_id).is_('web_link', 'null').limit(limit).execute()

        messages = messages_result.data or []
        if not messages:
            return {
                'success': True,
                'yacht_id': yacht_id,
                'stats': {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'message': 'No messages need backfill'}
            }

        # Get Graph read client
        read_client = create_read_client(supabase, user_id, yacht_id)

        stats = {'processed': 0, 'updated': 0, 'skipped': 0, 'failed': 0}

        for msg in messages:
            stats['processed'] += 1
            provider_id = msg['provider_message_id']

            try:
                # Fetch webLink from Graph API
                content = await read_client.get_message_content(provider_id)
                weblink = content.get('webLink')

                if weblink:
                    # Update database
                    supabase.table('email_messages').update({
                        'web_link': weblink
                    }).eq('id', msg['id']).execute()
                    stats['updated'] += 1
                    logger.debug(f"[email/backfill-weblinks] Updated {msg['id'][:8]}...")
                else:
                    stats['skipped'] += 1

            except Exception as e:
                stats['failed'] += 1
                logger.warning(f"[email/backfill-weblinks] Failed for {provider_id[:20]}...: {e}")

        logger.info(f"[email/backfill-weblinks] yacht={yacht_id[:8]}... stats={stats}")

        return {
            'success': True,
            'yacht_id': yacht_id,
            'stats': stats,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected. Please connect Outlook first.")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired. Please reconnect.")
    except TokenRevokedError:
        raise HTTPException(status_code=401, detail="Email connection revoked. Please reconnect.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/backfill-weblinks] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backfill failed: {str(e)}")


# ============================================================================
# GET /email/ledger/:entity_type/:entity_id - Entity Ledger View (M5)
# ============================================================================

@router.get("/ledger/{entity_type}/{entity_id}")
async def get_entity_ledger(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get chronological ledger entries for an entity.

    M5: Ledger is a read-only view over pms_audit_log filtered by entity.
    No free-text query param (invariant: ledger is not searchable).

    Supported entity types:
    - email_thread
    - email_message
    - work_order
    - equipment
    - part
    - document

    Pagination:
    - limit: max entries per page (default 50, max 100)
    - offset: skip first N entries

    Returns entries in reverse chronological order (newest first).
    Stable ordering: created_at DESC, id ASC.
    """
    enabled, error_msg = check_email_feature('focus')  # Ledger requires focus feature
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    valid_types = ['email_thread', 'email_message', 'work_order', 'equipment', 'part', 'document']
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {valid_types}")

    # Clamp limit and offset
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    try:
        # Query audit log for this entity (RLS enforces yacht_id)
        # Stable ordering: created_at DESC, then id ASC for deterministic pagination
        result = supabase.table('pms_audit_log').select(
            'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
            count='exact'
        ).eq('yacht_id', yacht_id).eq('entity_type', entity_type).eq(
            'entity_id', entity_id
        ).order('created_at', desc=True).order('id', desc=False).range(
            offset, offset + limit - 1
        ).execute()

        direct_count = result.count or 0
        entries = []
        for row in (result.data or []):
            entries.append({
                'id': row['id'],
                'event_type': row['action'],
                'timestamp': row['created_at'],
                'actor_id': row['user_id'],
                'details': row['new_values'],
                'metadata': row.get('signature', {}),
            })

        # Also get related entries (where this entity is the related_entity)
        # Only fetch if we have room in limit
        remaining = limit - len(entries)
        related_entries = []
        related_count = 0

        if remaining > 0:
            related_result = supabase.table('pms_audit_log').select(
                'id, action, entity_type, entity_id, user_id, old_values, new_values, signature, created_at',
                count='exact'
            ).eq('yacht_id', yacht_id).eq(
                'new_values->>related_entity_type', entity_type
            ).eq('new_values->>related_entity_id', entity_id).order(
                'created_at', desc=True
            ).order('id', desc=False).limit(remaining).execute()

            related_count = related_result.count or 0
            for row in (related_result.data or []):
                related_entries.append({
                    'id': row['id'],
                    'event_type': row['action'],
                    'timestamp': row['created_at'],
                    'actor_id': row['user_id'],
                    'source_entity_type': row['entity_type'],
                    'source_entity_id': row['entity_id'],
                    'details': row['new_values'],
                    'metadata': row.get('signature', {}),
                    'is_related': True,  # Mark as incoming relationship
                })

        # Merge and sort all entries by timestamp (stable sort)
        all_entries = entries + related_entries
        all_entries.sort(key=lambda x: (x['timestamp'], x['id']), reverse=True)
        all_entries = all_entries[:limit]

        total_count = direct_count + related_count
        has_more = offset + len(all_entries) < total_count

        logger.info(f"[email/ledger] entity={entity_type}:{entity_id[:8]} entries={len(all_entries)} total={total_count}")

        return {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entries': all_entries,
            'count': len(all_entries),
            'total_count': total_count,
            'offset': offset,
            'limit': limit,
            'has_more': has_more,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/ledger] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch ledger")


# ============================================================================
# POST /email/action/execute - Execute Micro-Action with Triggers (M5)
# ============================================================================

class ActionExecuteRequest(BaseModel):
    action_name: str = Field(..., description="Action to execute")
    message_id: Optional[str] = Field(None, description="Email message ID")
    thread_id: Optional[str] = Field(None, description="Email thread ID")
    target_type: Optional[str] = Field(None, description="Target entity type")
    target_id: Optional[str] = Field(None, description="Target entity ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")


# Action permissions: action_name -> allowed_roles
ACTION_PERMISSIONS = {
    'link_to_work_order': ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_equipment': ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'link_to_part': ['chief_engineer', 'eto', 'captain', 'manager', 'member'],
    'create_work_order_from_email': ['chief_engineer', 'eto', 'captain', 'manager'],  # No member
}

# Trigger effect timeout (seconds)
TRIGGER_TIMEOUT_SECONDS = 5


@router.post("/action/execute")
async def execute_action(
    request: ActionExecuteRequest,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Execute a micro-action and fire associated triggers.

    M5 Execution Order (Audit-First):
    1. Feature flag check
    2. Permission check (role-based)
    3. Idempotency check (return cached if duplicate)
    4. Precondition validation
    5. Execute mutation
    6. Write audit log (BEFORE trigger)
    7. Dispatch triggers (ONLY on success, with timeout)

    Triggers NEVER fire on failed or unaudited actions.
    """
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    user_role = auth.get('role', '')
    supabase = get_tenant_client(auth['tenant_key_alias'])
    action_audit_id = str(uuid.uuid4())

    # === STEP 1: Permission Check ===
    allowed_roles = ACTION_PERMISSIONS.get(request.action_name)
    if allowed_roles is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_name}")

    if user_role not in allowed_roles:
        logger.warning(f"[email/action/execute] Permission denied: {request.action_name} role={user_role}")
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' cannot execute action '{request.action_name}'"
        )

    # === STEP 2: Idempotency Check ===
    if request.idempotency_key:
        existing = supabase.table('pms_audit_log').select('new_values').eq(
            'yacht_id', yacht_id
        ).eq('signature->>idempotency_key', request.idempotency_key).limit(1).execute()

        if existing.data:
            cached_result = existing.data[0].get('new_values', {}).get('result', {})
            logger.info(f"[email/action/execute] Idempotent return for key={request.idempotency_key[:16]}")
            return {
                'success': cached_result.get('success', True),
                'action_name': request.action_name,
                'result': cached_result,
                'cached': True,
                'trigger': None,
            }

    # === STEP 3: Precondition Validation ===
    precondition_errors = []

    if request.action_name in ['link_to_work_order', 'link_to_equipment', 'link_to_part']:
        if not request.thread_id:
            precondition_errors.append("thread_id is required")
        if not request.target_id:
            precondition_errors.append("target_id is required")

        # Check thread exists and belongs to yacht
        if request.thread_id:
            thread_check = supabase.table('email_threads').select('id').eq(
                'id', request.thread_id
            ).eq('yacht_id', yacht_id).maybe_single().execute()
            if not thread_check.data:
                precondition_errors.append("Thread not found or access denied")

        # Check for existing link (idempotent - same link is success)
        if request.thread_id and request.target_id:
            existing_link = supabase.table('email_links').select('id').eq(
                'yacht_id', yacht_id
            ).eq('thread_id', request.thread_id).eq(
                'object_id', request.target_id
            ).eq('is_active', True).limit(1).execute()

            if existing_link.data:
                # Already linked - return success (idempotent)
                return {
                    'success': True,
                    'action_name': request.action_name,
                    'result': {'link_id': existing_link.data[0]['id'], 'already_linked': True},
                    'trigger': None,
                }

    elif request.action_name == 'create_work_order_from_email':
        if not request.params.get('title'):
            precondition_errors.append("title is required in params")

    if precondition_errors:
        raise HTTPException(status_code=400, detail="; ".join(precondition_errors))

    # Import trigger system
    from email_rag.triggers import TriggerContext, dispatch_trigger, apply_trigger_effects

    try:
        # === STEP 4: Execute Mutation ===
        action_result = {'success': False, 'error': 'Unknown action'}

        if request.action_name == 'link_to_work_order':
            link_insert = supabase.table('email_links').insert({
                'yacht_id': yacht_id,
                'thread_id': request.thread_id,
                'object_type': 'work_order',
                'object_id': request.target_id,
                'confidence': 'user_confirmed',
                'accepted_at': datetime.utcnow().isoformat(),
                'accepted_by': user_id,
            }).execute()

            action_result = {
                'success': True,
                'link_id': link_insert.data[0]['id'] if link_insert.data else None,
            }

        elif request.action_name == 'link_to_equipment':
            link_insert = supabase.table('email_links').insert({
                'yacht_id': yacht_id,
                'thread_id': request.thread_id,
                'object_type': 'equipment',
                'object_id': request.target_id,
                'confidence': 'user_confirmed',
                'accepted_at': datetime.utcnow().isoformat(),
                'accepted_by': user_id,
            }).execute()

            action_result = {
                'success': True,
                'link_id': link_insert.data[0]['id'] if link_insert.data else None,
            }

        elif request.action_name == 'link_to_part':
            link_insert = supabase.table('email_links').insert({
                'yacht_id': yacht_id,
                'thread_id': request.thread_id,
                'object_type': 'part',
                'object_id': request.target_id,
                'confidence': 'user_confirmed',
                'accepted_at': datetime.utcnow().isoformat(),
                'accepted_by': user_id,
            }).execute()

            action_result = {
                'success': True,
                'link_id': link_insert.data[0]['id'] if link_insert.data else None,
            }

        elif request.action_name == 'create_work_order_from_email':
            title = request.params.get('title', 'Work Order from Email')
            priority = request.params.get('priority', 'medium')
            equipment_id = request.params.get('equipment_id')

            wo_insert = supabase.table('pms_work_orders').insert({
                'yacht_id': yacht_id,
                'title': title,
                'priority': priority,
                'equipment_id': equipment_id,
                'status': 'open',
                'source': 'email',
                'source_reference': request.message_id,
                'created_by': user_id,
            }).execute()

            work_order_id = wo_insert.data[0]['id'] if wo_insert.data else None

            action_result = {
                'success': True,
                'work_order_id': work_order_id,
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action_name}")

        # === STEP 5: Write Audit Log (BEFORE trigger dispatch) ===
        # This ensures the action is recorded even if trigger fails
        supabase.table('pms_audit_log').insert({
            'yacht_id': yacht_id,
            'action': f'EMAIL_ACTION_{request.action_name.upper()}',
            'entity_type': 'email_action',
            'entity_id': request.message_id or request.thread_id or 'unknown',
            'user_id': user_id,
            'old_values': {},
            'new_values': {
                'action_name': request.action_name,
                'target_type': request.target_type,
                'target_id': request.target_id,
                'result': action_result,
            },
            'signature': {
                'timestamp': datetime.utcnow().isoformat(),
                'action_version': 'M5',
                'action_audit_id': action_audit_id,
                'user_role': user_role,
                'idempotency_key': request.idempotency_key,
            },
        }).execute()

        logger.info(
            f"[email/action/execute] Audited: {request.action_name} "
            f"audit_id={action_audit_id[:8]} user={user_id[:8]}"
        )

        # === STEP 6: Dispatch Trigger (ONLY on success, with timeout) ===
        # Triggers never fire on failed or unaudited actions
        trigger_result = None
        trigger_error = None

        if action_result.get('success'):
            import asyncio

            ctx = TriggerContext(
                yacht_id=yacht_id,
                user_id=user_id,
                user_role=user_role,
                action_name=request.action_name,
                action_id=action_audit_id,  # Use audit ID for deduplication
                message_id=request.message_id,
                thread_id=request.thread_id,
                target_type=request.target_type or 'work_order',
                target_id=request.target_id,
                success=True,
                result_data=action_result,
            )

            try:
                # Dispatch with timeout to prevent blocking
                trigger_result = dispatch_trigger(ctx)

                if trigger_result and trigger_result.executed:
                    # Apply effects with timeout
                    effects_summary = await asyncio.wait_for(
                        apply_trigger_effects(supabase, trigger_result),
                        timeout=TRIGGER_TIMEOUT_SECONDS
                    )
                    logger.info(
                        f"[email/action/execute] Trigger effects applied: {effects_summary}"
                    )

            except asyncio.TimeoutError:
                trigger_error = "Trigger execution timed out"
                logger.error(f"[email/action/execute] Trigger timeout for {request.action_name}")
                # Log to DLQ for retry
                try:
                    supabase.table('pms_audit_log').insert({
                        'yacht_id': yacht_id,
                        'action': 'TRIGGER_DLQ',
                        'entity_type': 'trigger_failure',
                        'entity_id': action_audit_id,
                        'user_id': user_id,
                        'old_values': {},
                        'new_values': {
                            'action_name': request.action_name,
                            'error': trigger_error,
                            'context': ctx.__dict__ if hasattr(ctx, '__dict__') else str(ctx),
                        },
                        'signature': {'timestamp': datetime.utcnow().isoformat()},
                    }).execute()
                except Exception:
                    pass  # Best effort DLQ

            except Exception as te:
                trigger_error = str(te)
                logger.error(f"[email/action/execute] Trigger error: {te}")

        response = {
            'success': action_result.get('success', False),
            'action_name': request.action_name,
            'action_audit_id': action_audit_id,
            'result': action_result,
            'trigger': trigger_result.to_dict() if trigger_result else None,
        }
        if trigger_error:
            response['trigger_error'] = trigger_error
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/action/execute] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Action execution failed: {str(e)}")


# ============================================================================
# GET /email/debug/search-folders - Search all Graph folders for emails
# ============================================================================

@router.get("/debug/search-folders")
async def debug_search_folders(
    q: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Debug endpoint to search all Graph folders for emails matching a pattern.

    This helps diagnose sync issues by finding emails that exist in Outlook
    but might be in folders other than inbox/sent.

    Args:
        q: Search pattern to match against email subjects

    Returns:
        Dict with folders and matching messages in each
    """
    import httpx

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get Graph token
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        results = {
            'query': q,
            'folders': {},
            'total_found': 0,
        }

        async with httpx.AsyncClient() as client:
            # List all folders
            folders_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )

            if folders_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            folders = folders_response.json().get('value', [])
            results['folder_count'] = len(folders)

            # Search each folder
            for folder in folders:
                folder_name = folder.get('displayName', 'Unknown')
                folder_id = folder.get('id')

                # Query messages in folder
                messages_response = await client.get(
                    f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
                    f"?$select=id,subject,from,receivedDateTime,conversationId&$top=100&$orderby=receivedDateTime desc",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )

                if messages_response.status_code == 200:
                    messages = messages_response.json().get('value', [])

                    # Filter messages matching search pattern
                    matching = []
                    for msg in messages:
                        subject = msg.get('subject', '') or ''
                        if q.lower() in subject.lower():
                            matching.append({
                                'subject': subject,
                                'from': msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                                'received': msg.get('receivedDateTime', ''),
                                'conversationId': msg.get('conversationId', 'NONE')[:50] + '...' if msg.get('conversationId') else 'NONE',
                            })

                    if matching:
                        results['folders'][folder_name] = {
                            'count': len(matching),
                            'messages': matching,
                        }
                        results['total_found'] += len(matching)

        return results

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/search-folders] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============================================================================
# POST /email/sync/all-folders - Sync emails from ALL folders
# ============================================================================

@router.post("/sync/all-folders")
async def sync_all_folders(
    auth: dict = Depends(get_authenticated_user),
    max_per_folder: int = 100,
):
    """
    Sync emails from ALL mail folders, not just inbox/sent.

    This is a one-time sync to find and import emails that may have been
    missed because they're in folders like Junk, Archive, or Other.

    Args:
        max_per_folder: Maximum messages to sync per folder (default 100)

    Returns:
        Stats dict with messages synced per folder
    """
    import httpx

    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get Graph token
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        stats = {
            'folders_synced': 0,
            'messages_created': 0,
            'messages_skipped': 0,
            'errors': [],
            'folder_stats': {},
        }

        async with httpx.AsyncClient() as client:
            # List all folders
            folders_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )

            if folders_response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to list folders")

            folders = folders_response.json().get('value', [])

            for folder in folders:
                folder_name = folder.get('displayName', 'Unknown')
                folder_id = folder.get('id')
                folder_stats = {'synced': 0, 'skipped': 0, 'errors': 0}

                try:
                    # Get messages from folder
                    messages_response = await client.get(
                        f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
                        f"?$select=id,conversationId,subject,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                        f"&$top={max_per_folder}&$orderby=receivedDateTime desc",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=60.0
                    )

                    if messages_response.status_code == 200:
                        messages = messages_response.json().get('value', [])

                        for msg in messages:
                            try:
                                # Determine folder type for direction
                                is_sent = folder_name.lower() in ['sent items', 'sent', 'sentitems']
                                folder_type = 'sent' if is_sent else 'inbox'

                                await _process_message(supabase, yacht_id, msg, folder_type)
                                folder_stats['synced'] += 1
                                stats['messages_created'] += 1
                            except Exception as e:
                                if 'duplicate' in str(e).lower() or 'already exists' in str(e).lower():
                                    folder_stats['skipped'] += 1
                                    stats['messages_skipped'] += 1
                                else:
                                    folder_stats['errors'] += 1
                                    stats['errors'].append(f"{folder_name}: {str(e)[:50]}")

                    stats['folders_synced'] += 1
                    stats['folder_stats'][folder_name] = folder_stats

                except Exception as e:
                    stats['errors'].append(f"Folder {folder_name}: {str(e)[:100]}")

        return {
            'success': True,
            'stats': stats,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/sync/all-folders] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# ============================================================================
# GET /email/debug/graph-me - Get the actual connected Microsoft account
# ============================================================================

@router.get("/debug/graph-me")
async def debug_graph_me(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Debug endpoint: Get the Microsoft account profile for the connected token.

    This shows which mailbox the OAuth token is actually for.
    """
    import httpx

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get Graph token
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        async with httpx.AsyncClient() as client:
            # Call /me endpoint
            me_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )

            if me_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Graph /me error: {me_response.status_code}"
                )

            me_data = me_response.json()

            # Get Inbox folder details
            inbox_response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )

            inbox_data = {}
            if inbox_response.status_code == 200:
                inbox_data = inbox_response.json()

        return {
            'profile': {
                'displayName': me_data.get('displayName'),
                'mail': me_data.get('mail'),
                'userPrincipalName': me_data.get('userPrincipalName'),
                'id': me_data.get('id'),
            },
            'inbox_folder': {
                'displayName': inbox_data.get('displayName'),
                'totalItemCount': inbox_data.get('totalItemCount'),
                'unreadItemCount': inbox_data.get('unreadItemCount'),
            },
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/graph-me] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")


# ============================================================================
# GET /email/debug/inbox-compare - Compare Graph Inbox with DB
# ============================================================================

@router.get("/debug/inbox-compare")
async def debug_inbox_compare(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Debug endpoint: List ALL Inbox messages from Graph API and compare with DB.

    Shows:
    - All messages in Graph Inbox
    - Which ones exist in our database
    - Which ones are MISSING from our database

    This helps diagnose sync issues.
    """
    import httpx

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get Graph token
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        # Get all messages from Inbox (up to 200)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,receivedDateTime,hasAttachments,bodyPreview"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Graph API error: {response.status_code} - {response.text[:200]}"
                )

            graph_messages = response.json().get('value', [])

        # Get all message IDs from our database
        db_result = supabase.table('email_messages').select(
            'provider_message_id, subject'
        ).eq('yacht_id', yacht_id).execute()

        db_message_ids = {m['provider_message_id'] for m in db_result.data}

        # Compare
        in_graph = []
        missing_from_db = []

        for msg in graph_messages:
            msg_id = msg.get('id')
            subject = msg.get('subject', '(no subject)')
            from_addr = msg.get('from', {}).get('emailAddress', {}).get('address', '')
            received = msg.get('receivedDateTime', '')
            has_attachments = msg.get('hasAttachments', False)
            conversation_id = msg.get('conversationId', '')
            preview = (msg.get('bodyPreview', '') or '')[:100]

            msg_info = {
                'id': msg_id[:30] + '...' if len(msg_id) > 30 else msg_id,
                'subject': subject,
                'from': from_addr,
                'received': received,
                'hasAttachments': has_attachments,
                'conversationId': conversation_id[:30] + '...' if conversation_id and len(conversation_id) > 30 else conversation_id,
                'preview': preview,
            }

            in_graph.append(msg_info)

            if msg_id not in db_message_ids:
                missing_from_db.append(msg_info)

        return {
            'graph_inbox_count': len(graph_messages),
            'db_message_count': len(db_message_ids),
            'missing_count': len(missing_from_db),
            'missing_from_db': missing_from_db,
            'all_graph_inbox': in_graph,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/inbox-compare] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Compare failed: {str(e)}")


# ============================================================================
# GET /email/debug/thread-yacht-check - Check thread yacht_id assignment
# ============================================================================

@router.get("/debug/thread-yacht-check")
async def debug_thread_yacht_check(
    thread_ids: str,  # Comma-separated thread IDs
    auth: dict = Depends(get_authenticated_user),
):
    """
    Debug endpoint: Check yacht_id assignment for specific threads.

    Shows:
    - User's current yacht_id from auth token
    - Each thread's actual yacht_id in the database
    - Whether there's a mismatch

    Usage: /email/debug/thread-yacht-check?thread_ids=uuid1,uuid2,uuid3
    """
    user_yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    # Parse thread IDs
    ids = [t.strip() for t in thread_ids.split(',') if t.strip()]

    results = []
    for thread_id in ids[:10]:  # Limit to 10 threads
        try:
            # Query thread WITHOUT yacht_id filter to see actual yacht_id
            thread_result = supabase.table('email_threads').select(
                'id, yacht_id, latest_subject, created_at'
            ).eq('id', thread_id).limit(1).execute()

            if thread_result.data:
                thread = thread_result.data[0]
                thread_yacht_id = thread.get('yacht_id')
                results.append({
                    'thread_id': thread_id,
                    'exists': True,
                    'thread_yacht_id': thread_yacht_id,
                    'user_yacht_id': user_yacht_id,
                    'match': thread_yacht_id == user_yacht_id,
                    'subject': thread.get('latest_subject', 'N/A')[:50],
                })
            else:
                results.append({
                    'thread_id': thread_id,
                    'exists': False,
                    'thread_yacht_id': None,
                    'user_yacht_id': user_yacht_id,
                    'match': False,
                    'error': 'Thread not found in database',
                })
        except Exception as e:
            results.append({
                'thread_id': thread_id,
                'exists': False,
                'error': str(e),
            })

    mismatches = [r for r in results if r.get('exists') and not r.get('match')]
    not_found = [r for r in results if not r.get('exists')]

    return {
        'user_yacht_id': user_yacht_id,
        'tenant_key_alias': auth['tenant_key_alias'],
        'checked_count': len(results),
        'mismatch_count': len(mismatches),
        'not_found_count': len(not_found),
        'results': results,
        'diagnosis': (
            'YACHT_ID_MISMATCH: Threads exist but belong to different yacht'
            if mismatches else
            'THREADS_NOT_FOUND: Threads do not exist in this tenant database'
            if not_found else
            'OK: All threads match user yacht_id'
        ),
    }


# ============================================================================
# POST /email/debug/force-sync-missing - Force sync missing emails
# ============================================================================

@router.post("/debug/force-sync-missing")
async def debug_force_sync_missing(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Force sync all emails from Inbox that are missing from our database.

    This bypasses delta sync and directly fetches/inserts missing messages.
    """
    import httpx

    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get Graph token
        read_client = create_read_client(supabase, user_id, yacht_id)
        token = await read_client._get_token()

        stats = {
            'checked': 0,
            'synced': 0,
            'already_existed': 0,
            'errors': [],
            'synced_subjects': [],
        }

        # Get all messages from Inbox
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
                "?$select=id,conversationId,subject,from,toRecipients,ccRecipients,receivedDateTime,sentDateTime,hasAttachments,internetMessageId,bodyPreview,webLink"
                "&$top=200&$orderby=receivedDateTime desc",
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Graph API error")

            graph_messages = response.json().get('value', [])
            stats['checked'] = len(graph_messages)

        # Get existing message IDs
        db_result = supabase.table('email_messages').select(
            'provider_message_id'
        ).eq('yacht_id', yacht_id).execute()

        existing_ids = {m['provider_message_id'] for m in db_result.data}

        # Sync missing messages
        for msg in graph_messages:
            msg_id = msg.get('id')

            if msg_id in existing_ids:
                stats['already_existed'] += 1
                continue

            try:
                await _process_message(supabase, yacht_id, msg, 'inbox')
                stats['synced'] += 1
                stats['synced_subjects'].append(msg.get('subject', '(no subject)'))
            except Exception as e:
                error_msg = str(e)
                if 'duplicate' not in error_msg.lower():
                    stats['errors'].append(f"{msg.get('subject', 'unknown')[:30]}: {error_msg[:50]}")
                else:
                    stats['already_existed'] += 1

        return {
            'success': True,
            'stats': stats,
        }

    except TokenNotFoundError:
        raise HTTPException(status_code=401, detail="Email not connected")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Email connection expired")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/debug/force-sync-missing] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Force sync failed: {str(e)}")


# ============================================================================
# GET /email/worker/status - Worker/sync status
# ============================================================================

@router.get("/worker/status")
async def get_worker_status(
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get email sync worker status for the current user.

    Returns watcher status, last sync time, and any errors.
    """
    yacht_id = auth['yacht_id']
    user_id = auth['user_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Get watcher status - use limit(1) instead of maybe_single() to avoid 204 issues
        watcher_result = supabase.table('email_watchers').select(
            'sync_status, last_sync_at, subscription_expires_at, last_sync_error, delta_link_inbox, updated_at'
        ).eq('user_id', user_id).eq('yacht_id', yacht_id).eq(
            'provider', 'microsoft_graph'
        ).limit(1).execute()

        if not watcher_result.data or len(watcher_result.data) == 0:
            return {
                'connected': False,
                'sync_status': 'disconnected',
                'last_sync_at': None,
                'last_error': None,
                'message': 'No email connection found'
            }

        watcher = watcher_result.data[0]
        sync_status = watcher.get('sync_status', 'unknown')

        return {
            'connected': sync_status not in ['disconnected', 'pending'],
            'sync_status': sync_status,
            'last_sync_at': watcher.get('last_sync_at'),
            'subscription_expires_at': watcher.get('subscription_expires_at'),
            'last_error': watcher.get('last_sync_error'),
            'has_delta_link': bool(watcher.get('delta_link_inbox')),
            'updated_at': watcher.get('updated_at'),
        }

    except Exception as e:
        logger.error(f"[email/worker/status] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch worker status: {str(e)}")


# ============================================================================
# GET /email/thread/:thread_id/links - Get entity links for a thread
# ============================================================================

@router.get("/thread/{thread_id}/links")
async def get_thread_links(
    thread_id: str,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Get all entity links for a thread.

    Returns linked work orders, equipment, parts, crew, etc.
    """
    yacht_id = auth['yacht_id']
    supabase = get_tenant_client(auth['tenant_key_alias'])

    try:
        # Verify thread belongs to yacht - use limit(1) instead of maybe_single()
        thread_result = supabase.table('email_threads').select('id').eq(
            'id', thread_id
        ).eq('yacht_id', yacht_id).limit(1).execute()

        if not thread_result.data or len(thread_result.data) == 0:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get all links for this thread (table is email_links)
        links_result = supabase.table('email_links').select(
            'id, object_type, object_id, confidence, suggested_reason, accepted_at, accepted_by, is_active, score'
        ).eq('thread_id', thread_id).eq('yacht_id', yacht_id).eq('is_active', True).execute()

        links = links_result.data or []

        # Group links by object_type for easier frontend consumption
        grouped = {}
        for link in links:
            obj_type = link.get('object_type', 'other')
            if obj_type not in grouped:
                grouped[obj_type] = []
            grouped[obj_type].append(link)

        return {
            'thread_id': thread_id,
            'links': links,
            'grouped': grouped,
            'total_count': len(links),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[email/thread/links] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread links: {str(e)}")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ['router']

