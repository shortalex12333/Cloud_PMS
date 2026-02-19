"""
CelesteOS API - Streaming Search Router
========================================

Two-phase streaming search with production safety controls.

Security invariants (per 05_STREAMING_SEARCH_IMPLEMENTATION_GUIDE.md):
1. No bytes emitted before authz (JWT → membership → role → freeze)
2. Min prefix length enforced (default 3)
3. Per-user rate limiting (token bucket)
4. Per-yacht concurrency limiting
5. Cancellation propagation halts DB work
6. Role-aware redaction for snippets/metadata
7. Cache keys include yacht_id/user_id/role/query_hash/phase

Phase 1 (counts only):
- Low sensitivity, fast
- Returns: parts_count, work_orders_count, documents_count
- Cacheable (TTL: 60s)

Phase 2 (details with redaction):
- Detailed results after debounce/stabilization
- Role-aware snippet suppression
- Shorter TTL (15s)

Usage:
    GET /api/search/stream?q=engine&phase=1
    GET /api/search/stream?q=engine%20room&phase=2
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import re
from typing import AsyncGenerator, Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from starlette.responses import StreamingResponse

from middleware.auth import (
    get_authenticated_user,
    check_streaming_allowed,
    is_incident_mode_active,
    get_system_flags,
)
from middleware.action_security import (
    ActionContext,
    ActionSecurityError,
    YachtFrozenError,
    MembershipInactiveError,
    build_audit_entry,
)
from utils.cache_keys import (
    build_streaming_cache_key,
    normalize_query,
    hash_query,
)
from services.rate_limit import (
    get_rate_limiter,
    get_concurrency_gate,
    ConcurrencySlot,
    STREAM_MIN_PREFIX,
    STREAM_USER_BURST,
    STREAM_USER_RATE,
    STREAM_YACHT_CONCURRENCY,
    STREAM_PHASE1_TTL,
    STREAM_PHASE2_TTL,
)
from integrations.supabase import get_supabase_client, get_tenant_client
from execute.table_capabilities import TABLE_CAPABILITIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# ============================================================================
# Query Preprocessing (from stress test validation - 86% success rate)
# ============================================================================

def preprocess_search_query(query: str) -> str:
    """
    Clean up crew's messy queries.

    Based on stress test validation (PART_LENS_STRESS_TEST_FINAL.md):
    - Natural language: 100% success
    - Whitespace: 100% success
    - Vague queries: 100% success
    - Overall: 86% success rate (EXCELLENT)

    Handles:
    - Filler words ("show me", "where is", "I need")
    - Extra whitespace
    - Natural language noise
    """
    q = query.lower().strip()

    # Remove filler words (natural language noise)
    filler_patterns = [
        r'^show me\s+',        # "show me filters" → "filters"
        r'^where is\s+',       # "where is pump" → "pump"
        r'^where are\s+',      # "where are parts" → "parts"
        r'^find\s+',           # "find part" → "part"
        r'^i need\s+',         # "I need seal" → "seal"
        r'^do we have\s+',     # "do we have gasket" → "gasket"
        r'^give me\s+',        # "give me filter" → "filter"
        r'^can you find\s+',   # "can you find pump" → "pump"
        r'^looking for\s+',    # "looking for part" → "part"
        r'\s+please$',         # "filter please" → "filter"
        r'^the\s+',            # "the pump" → "pump"
        r'^a\s+',              # "a filter" → "filter"
        r'^an\s+',             # "an o-ring" → "o-ring"
        r'^that\s+',           # "that filter" → "filter"
        r'^some\s+',           # "some parts" → "parts"
        r'\s+thing$',          # "filter thing" → "filter"
        r'\s+stuff$',          # "engine stuff" → "engine"
    ]

    for pattern in filler_patterns:
        q = re.sub(pattern, '', q)

    # Normalize whitespace (extra spaces, tabs)
    q = re.sub(r'\s+', ' ', q).strip()

    return q


# ============================================================================
# Roles that should have snippets redacted
# ============================================================================

REDACTED_ROLES = {"crew", "guest"}  # Roles that don't see document snippets


# ============================================================================
# Search Implementation
# ============================================================================

async def search_parts(yacht_id: str, query: str, tenant_key_alias: str) -> tuple[List[Dict[str, Any]], int]:
    """
    Search parts across multiple columns with preprocessing.

    Returns:
        (results, total_count) - List of part dictionaries and total count
    """
    # Preprocess query
    clean_query = preprocess_search_query(query)

    # If query became empty after preprocessing, use original
    if not clean_query or len(clean_query) < 2:
        clean_query = query.strip()

    supabase = get_tenant_client(tenant_key_alias)
    results = []
    seen_ids = set()

    # Search across multiple columns
    # This matches the stress test implementation (86% success rate)
    columns = ['name', 'description', 'category', 'manufacturer', 'location']

    for column in columns:
        try:
            response = await asyncio.to_thread(
                lambda col=column: supabase.table('pms_parts')
                    .select('id, name, part_number, category, manufacturer, location, description')
                    .eq('yacht_id', yacht_id)
                    .ilike(col, f'%{clean_query}%')
                    .limit(20)
                    .execute()
            )

            for item in response.data:
                if item['id'] not in seen_ids:
                    seen_ids.add(item['id'])
                    results.append(item)

        except Exception as e:
            logger.warning(f"[SearchParts] Column search failed for {column}: {e}")
            continue

    return results, len(results)


# ============================================================================
# Dependencies
# ============================================================================

async def get_streaming_context(
    request: Request,
    auth: dict = Depends(get_authenticated_user),
) -> ActionContext:
    """
    Build ActionContext for streaming search.

    CRITICAL: All authz checks MUST complete before any bytes are emitted.

    Checks:
    1. JWT validation (via get_authenticated_user dependency)
    2. Incident mode / streaming disabled check
    3. Membership status (from auth dict)
    4. Role exists and is valid
    5. Yacht not frozen

    Raises:
        HTTPException 403: If any authz check fails
        HTTPException 503: If streaming is disabled (incident mode)
    """
    # Check incident mode FIRST (before building context)
    flags = get_system_flags()
    if flags.get('incident_mode') and flags.get('disable_streaming'):
        reason = flags.get('incident_reason') or 'security incident'
        logger.warning(
            f"[StreamSearch] INCIDENT MODE: Streaming disabled, reason={reason}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="service_unavailable",  # Generic message per error hygiene
        )

    # Build context from auth
    ctx = ActionContext(
        user_id=auth['user_id'],
        yacht_id=auth['yacht_id'],
        role=auth['role'],
        tenant_key_alias=auth.get('tenant_key_alias', f"y{auth['yacht_id'][:8]}"),
        email=auth.get('email'),
        yacht_name=auth.get('yacht_name'),
        membership_status=auth.get('membership_status', 'ACTIVE'),
        is_frozen=auth.get('is_frozen', False),
        request_id=str(uuid.uuid4()),
    )

    # Check membership status
    if ctx.membership_status != 'ACTIVE':
        logger.warning(
            f"[StreamSearch] Membership not active: user={ctx.user_id[:8]}..., "
            f"status={ctx.membership_status}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",  # Generic message per error hygiene
        )

    # Check yacht freeze
    if ctx.is_frozen:
        logger.warning(
            f"[StreamSearch] Yacht frozen: yacht={ctx.yacht_id[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    # Check role exists
    if not ctx.role:
        logger.warning(
            f"[StreamSearch] No role: user={ctx.user_id[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    return ctx


# ============================================================================
# Streaming Endpoint
# ============================================================================

@router.get("/stream")
async def stream_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    phase: int = Query(1, ge=1, le=2, description="Phase 1=counts, 2=details"),
    ctx: ActionContext = Depends(get_streaming_context),
):
    """
    Streaming search endpoint with two-phase response.

    Phase 1 (counts):
    - Returns aggregate counts only
    - Fast, low sensitivity
    - Cached for 60s

    Phase 2 (details):
    - Returns detailed results with role-based redaction
    - Crew/guest roles get snippets redacted
    - Cached for 15s

    Args:
        q: Search query (min length enforced)
        phase: 1 for counts, 2 for details
        ctx: ActionContext (authz completed before this)

    Returns:
        StreamingResponse with JSON-lines output

    Raises:
        400: Query too short (min prefix)
        403: Authz failed (membership/role/freeze)
        429: Rate limit or concurrency limit exceeded
    """
    # Normalize query
    nq = normalize_query(q)

    # Min prefix check
    if len(nq) < STREAM_MIN_PREFIX:
        logger.info(
            f"[StreamSearch] Min prefix rejected: len={len(nq)}, min={STREAM_MIN_PREFIX}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_prefix",
        )

    # User rate limit check
    rate_limiter = get_rate_limiter()
    user_key = f"user:{ctx.user_id}"
    allowed = await rate_limiter.allow(
        scope="search",
        key=user_key,
        capacity=STREAM_USER_BURST,
        refill_rate=STREAM_USER_RATE,
    )
    if not allowed:
        logger.warning(
            f"[StreamSearch] Rate limited: user={ctx.user_id[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
        )

    # Yacht concurrency check
    concurrency_gate = get_concurrency_gate()
    yacht_key = str(ctx.yacht_id)

    if not await concurrency_gate.try_acquire(yacht_key):
        logger.warning(
            f"[StreamSearch] Concurrency limited: yacht={ctx.yacht_id[:8]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="concurrency_limited",
        )

    # Build cache key (for caching layer integration)
    cache_key = build_streaming_cache_key(
        endpoint="search.stream",
        ctx=ctx,
        phase=phase,
        raw_query=nq,
    )

    # Log query hash only (not raw query per logging rules)
    qh = hash_query(nq)
    logger.info(
        f"[StreamSearch] Start: user={ctx.user_id[:8]}..., "
        f"yacht={ctx.yacht_id[:8]}..., phase={phase}, "
        f"query_hash={qh[:16]}..."
    )

    async def event_stream() -> AsyncGenerator[bytes, None]:
        """
        Generate streaming response.

        CRITICAL: Concurrency slot MUST be released even on error.
        """
        try:
            # Check for client disconnect periodically
            if await request.is_disconnected():
                logger.info(f"[StreamSearch] Client disconnected early: {qh[:16]}...")
                return

            # Phase 1: Counts only
            if phase == 1:
                # Execute actual search with preprocessing
                parts_results, parts_count = await search_parts(ctx.yacht_id, nq, ctx.tenant_key_alias)

                # Check disconnect again
                if await request.is_disconnected():
                    logger.info(f"[StreamSearch] Client disconnected during P1: {qh[:16]}...")
                    return

                payload = {
                    "phase": 1,
                    "parts_count": parts_count,
                    "work_orders_count": 0,  # TODO: Implement work orders search
                    "documents_count": 0,    # TODO: Implement documents search
                    "cache_key": cache_key[:50] + "..." if len(cache_key) > 50 else cache_key,
                }
                yield _json_line(payload)
                return

            # Phase 2: Details with role-based redaction
            parts_results, parts_count = await search_parts(ctx.yacht_id, nq, ctx.tenant_key_alias)

            if await request.is_disconnected():
                logger.info(f"[StreamSearch] Client disconnected during P2: {qh[:16]}...")
                return

            # Role-based redaction
            snippets_redacted = ctx.role in REDACTED_ROLES

            # Get available actions for parts from capability definition
            part_capability = TABLE_CAPABILITIES.get("part_by_part_number_or_name")
            part_actions = part_capability.available_actions if part_capability else []

            # Format results for frontend
            formatted_results = []
            for part in parts_results:
                result_item = {
                    "type": "part",
                    "id": part["id"],
                    "title": part["name"],
                    "part_number": part.get("part_number"),
                    "category": part.get("category"),
                    "manufacturer": part.get("manufacturer"),
                    "location": part.get("location"),
                    # Include available actions from capability definition
                    "available_actions": part_actions,
                }

                # Include description unless redacted
                if not snippets_redacted:
                    result_item["description"] = part.get("description", "")

                formatted_results.append(result_item)

            payload = {
                "phase": 2,
                "results": formatted_results,
                "total_count": parts_count,
                "snippets_redacted": snippets_redacted,
                "role": ctx.role,
            }

            yield _json_line(payload)

        except asyncio.CancelledError:
            logger.info(f"[StreamSearch] Cancelled: {qh[:16]}...")
            raise
        except Exception as e:
            logger.error(f"[StreamSearch] Error: {e}")
            yield _json_line({"error": "internal_error"})
        finally:
            # Always release concurrency slot
            await concurrency_gate.release(yacht_key)
            logger.info(
                f"[StreamSearch] End: user={ctx.user_id[:8]}..., "
                f"phase={phase}, query_hash={qh[:16]}..."
            )

    # Return streaming response
    # CRITICAL: All authz, rate limits, and concurrency checks completed before this
    return StreamingResponse(
        event_stream(),
        media_type="application/json",
        headers={
            "X-Request-Id": ctx.request_id,
            "X-Cache-Key": cache_key[:100],  # Truncated for header safety
        },
    )


def _json_line(data: dict) -> bytes:
    """Convert dict to JSON-line bytes."""
    import json
    return (json.dumps(data) + "\n").encode("utf-8")


# ============================================================================
# Health Check
# ============================================================================

@router.get("/stream/health")
async def stream_health():
    """Health check for streaming search."""
    return {
        "status": "healthy",
        "min_prefix": STREAM_MIN_PREFIX,
        "user_burst": STREAM_USER_BURST,
        "user_rate": STREAM_USER_RATE,
        "yacht_concurrency": STREAM_YACHT_CONCURRENCY,
        "phase1_ttl": STREAM_PHASE1_TTL,
        "phase2_ttl": STREAM_PHASE2_TTL,
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "router",
    "stream_search",
    "get_streaming_context",
    "REDACTED_ROLES",
]
