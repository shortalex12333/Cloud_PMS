#!/usr/bin/env python3
"""
F1 Search - Streaming Fusion Layer (SSE)

Server-Sent Events endpoint for F1 hybrid search.
Emits results as they arrive - NEVER blocks on one shard before emitting others.

Event sequence:
1. diagnostics - Search started, search_id
2. result_batch - Fused results (every ~100ms or on early win)
3. finalized - Search complete, latency metrics

Flow: JWT → UserContext → Extraction → Cortex → Signal Router → hyper_search_multi → SSE

GUARDRAILS:
- ONE round-trip per search using hyper_search_multi
- statement_timeout=120ms on DB connection
- Cancel pending tasks on exact_match_win (deterministic only)

See: apps/api/docs/F1_SEARCH/STREAMING_FUSION_LAYER.md
     apps/api/docs/F1_SEARCH/FRONTEND_STREAMING_API.md
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from types import SimpleNamespace
from typing import AsyncGenerator, Optional, Dict, Any, List

import asyncpg
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

# Redis for result caching (optional, graceful degradation)
try:
    import redis.asyncio as redis_async
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_async = None
from starlette.responses import StreamingResponse

# Auth middleware
from middleware.auth import get_authenticated_user

# F1 Search types and services
from services.types import UserContext, SearchBudget, DEFAULT_BUDGET
from services.signal_router import build_route_plan, RoutePlan

# Cortex rewrites
from cortex.rewrites import generate_rewrites, Rewrite, RewriteResult

# Extraction pipeline
from extraction.regex_extractor import RegexExtractor

# Reranker (lazy-loaded, feature-flagged)
from rankers import rerank as rerank_items

# OTEL tracing
from observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer("f1.search")

# Feature flags
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "false").lower() == "true"

# Org UUIDs allowed to use F1 streaming search (CSV)
# Example: STREAMING_ENABLED_ORGS=85fe1119-b04c-41ac-80f1-829d23322598,uuid2,uuid3
STREAMING_ENABLED_ORGS = set(filter(None, os.getenv("STREAMING_ENABLED_ORGS", "").split(",")))
logger.info(f"[F1] STREAMING_ENABLED_ORGS: {len(STREAMING_ENABLED_ORGS)} orgs configured")

router = APIRouter(prefix="/api/f1/search", tags=["f1-search"])

# ============================================================================
# Database Connection (asyncpg)
# ============================================================================

# READ_DSN: Use read replica if available, otherwise primary
# Format: postgresql://service_role:...@db.xxx.supabase.co:6543/postgres
READ_DSN = os.getenv("READ_DB_DSN") or os.getenv("DATABASE_URL")

# Connection pool (lazy init)
_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn):
    """Initialize connection with statement_timeout (Supabase doesn't support as startup param)."""
    await conn.execute("SET statement_timeout = '800ms'")


async def get_db_pool() -> asyncpg.Pool:
    """Get or create connection pool with statement_timeout."""
    global _pool
    if _pool is None:
        if not READ_DSN:
            raise ValueError("READ_DB_DSN or DATABASE_URL not configured")
        _pool = await asyncpg.create_pool(
            READ_DSN,
            min_size=2,
            max_size=10,
            command_timeout=0.5,  # 500ms max
            init=_init_connection,  # Set statement_timeout after connection
        )
    return _pool


async def get_db_connection() -> asyncpg.Connection:
    """Get single connection with statement_timeout (for non-pooled use)."""
    if not READ_DSN:
        raise ValueError("READ_DB_DSN or DATABASE_URL not configured")
    conn = await asyncpg.connect(READ_DSN)
    # Set statement_timeout after connection (Supabase doesn't support as startup param)
    await conn.execute("SET statement_timeout = '800ms'")
    return conn


# ============================================================================
# Redis Result Cache (optional, graceful degradation)
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL")
RESULT_CACHE_TTL = 120  # 2 minutes
EMBED_VERSION = "openai-3-small-1536"  # For cache key versioning

_redis: Optional[redis_async.Redis] = None


async def get_redis() -> Optional[redis_async.Redis]:
    """Get or create Redis connection (lazy, graceful degradation)."""
    global _redis
    if not REDIS_AVAILABLE or not REDIS_URL:
        return None
    if _redis is None:
        try:
            _redis = await redis_async.from_url(REDIS_URL, decode_responses=True)
            await _redis.ping()
            logger.info("[F1Search] Redis connected for result caching")
        except Exception as e:
            logger.warning(f"[F1Search] Redis unavailable: {e}")
            _redis = None
    return _redis


def make_cache_key(query: str, org_id: str, yacht_id: Optional[str]) -> str:
    """
    Create cache key for result cache.
    Format: rs:{query_hash}:{org}:{yacht}:{embed_ver}
    """
    # Normalize query: lowercase, strip whitespace
    norm_q = query.strip().lower()
    q_hash = hashlib.sha256(norm_q.encode()).hexdigest()[:16]
    yacht_part = yacht_id or ""
    return f"rs:{q_hash}:{org_id}:{yacht_part}:{EMBED_VERSION}"


async def get_cached_results(redis_conn, cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached results if available."""
    if not redis_conn:
        return None
    try:
        cached = await redis_conn.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"[F1Search] Cache get error: {e}")
    return None


async def set_cached_results(redis_conn, cache_key: str, items: List[Dict[str, Any]]) -> None:
    """Cache results with TTL."""
    if not redis_conn:
        return
    try:
        await redis_conn.set(cache_key, json.dumps(items), ex=RESULT_CACHE_TTL)
        logger.debug(f"[F1Search] Cached {len(items)} results for key={cache_key[:30]}...")
    except Exception as e:
        logger.warning(f"[F1Search] Cache set error: {e}")


# ============================================================================
# Extraction (Lazy Load)
# ============================================================================

_extractor = None


def get_extractor() -> RegexExtractor:
    """Lazy-load extraction pipeline."""
    global _extractor
    if _extractor is None:
        _extractor = RegexExtractor()
    return _extractor


# ============================================================================
# Early-Win Detection (Deterministic)
# ============================================================================

def is_exact_win(item: dict) -> bool:
    """
    Check if result is a deterministic exact match.

    GUARDRAILS (deterministic only):
    - trigram_rank == 1 AND trigram_score >= 0.95
    - object_type must be actionable (part, inventory)
    - Do NOT cancel on fuzzy matches or low scores

    If you cancel without deterministic condition, you will lose results.
    """
    ranks = item.get('ranks') or {}
    comps = item.get('components') or {}
    trig_rank = ranks.get('trigram')
    trig_score = comps.get('trigram', 0)
    return trig_rank == 1 and (trig_score or 0) >= 0.95 and item.get('object_type') in ('part', 'inventory')


# ============================================================================
# SSE Event Helpers
# ============================================================================

def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format Server-Sent Event.

    Format:
        event: <type>
        data: <json>

        (blank line terminates event)
    """
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


# ============================================================================
# Context Builder
# ============================================================================

def build_user_context(auth: Dict[str, Any]) -> UserContext:
    """
    Build UserContext from JWT auth payload.

    CRITICAL: org_id is required for RLS. If missing, raises 403.
    """
    user_id = auth.get("user_id")
    org_id = auth.get("org_id") or auth.get("yacht_id")  # Fallback: yacht_id as org scope
    yacht_id = auth.get("yacht_id")
    role = auth.get("role", "crew")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing user_id in auth context"
        )

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing org_id - RLS enforcement requires org scope"
        )

    return UserContext(
        user_id=str(user_id),
        org_id=str(org_id),
        yacht_id=str(yacht_id) if yacht_id else None,
        role=role,
        locale=auth.get("locale"),
    )


# ============================================================================
# hyper_search_multi RPC Call (asyncpg - single round-trip)
# ============================================================================

async def call_hyper_search_multi(
    conn: asyncpg.Connection,
    rewrites: List[Rewrite],
    ctx: UserContext,
    rrf_k: int = 60,
    page_limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Call hyper_search_multi RPC via asyncpg (single round-trip).

    GUARDRAILS:
    - Must have ctx.org_id (RLS requirement)
    - Max 3 rewrites
    - statement_timeout enforced by connection
    """
    # Ensure max 3 rewrites
    rewrites = rewrites[:3]

    texts = [r.text for r in rewrites]

    # Convert vectors: asyncpg needs explicit casts
    # If embedding is None, pass NULL
    vec_literals = []
    for r in rewrites:
        if r.embedding is not None:
            vec_literals.append(f"[{','.join(str(x) for x in r.embedding)}]")
        else:
            vec_literals.append(None)

    # Dynamic trigram threshold based on query length
    # Short queries (IDs/codes ≤6 chars): lower threshold for recall
    # Long queries: higher threshold to avoid flooding with weak matches
    original_query = texts[0] if texts else ""
    trgm_limit = 0.07 if len(original_query.strip()) <= 6 else 0.15

    # Try single round-trip with inline trgm_limit (migration 009)
    # Falls back to 2 round-trips if migration not applied yet
    try:
        rows = await conn.fetch(
            """
            SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components
            FROM hyper_search_multi($1::text[], $2::vector(1536)[], $3::uuid, $4::uuid, $5::int, $6::int, $7::real)
            """,
            texts,
            vec_literals,
            uuid.UUID(ctx.org_id),
            uuid.UUID(ctx.yacht_id) if ctx.yacht_id else None,
            rrf_k,
            page_limit,
            trgm_limit,
        )
    except asyncpg.PostgresError as e:
        # Fallback: migration 009 not applied yet, use old 2-roundtrip approach
        if "function hyper_search_multi" in str(e).lower():
            await conn.execute(f"SELECT set_limit({trgm_limit})")
            rows = await conn.fetch(
                """
                SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components
                FROM hyper_search_multi($1::text[], $2::vector(1536)[], $3::uuid, $4::uuid, $5::int, $6::int)
                """,
                texts,
                vec_literals,
                uuid.UUID(ctx.org_id),
                uuid.UUID(ctx.yacht_id) if ctx.yacht_id else None,
                rrf_k,
                page_limit,
            )
        else:
            raise

    # Convert asyncpg Records to dicts
    return [dict(r) for r in rows]


# ============================================================================
# F1 Streaming Search Endpoint
# ============================================================================

@router.get("/stream")
async def f1_search_stream(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    auth: dict = Depends(get_authenticated_user),
):
    """
    F1 Search streaming endpoint using Server-Sent Events.

    GUARDRAILS:
    - ONE round-trip per search using hyper_search_multi
    - Early exact-match wins emit immediately and cancel pending tasks
    - Result batches emit every ~100ms
    - Total budget: 500ms max
    - statement_timeout: 120ms on DB

    Events:
    - diagnostics: {"search_id": "...", "status": "started", "targets": [...]}
    - exact_match_win: {"object_id": "...", "object_type": "..."}
    - result_batch: {"items": [...], "partial": true/false}
    - finalized: {"search_id": "...", "latency_ms": N, "early_win": bool}

    Args:
        q: Search query (natural language)
        auth: JWT auth context (via dependency)

    Returns:
        StreamingResponse with SSE media type
    """
    # Build UserContext from auth; fail 400 if org_id missing
    ctx = build_user_context(auth)

    # Feature gate: only allow whitelisted orgs
    if STREAMING_ENABLED_ORGS and ctx.org_id not in STREAMING_ENABLED_ORGS:
        logger.warning(f"[F1Search] Org not enabled: {ctx.org_id[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "f1_search_not_enabled", "message": "F1 Search not enabled for this organization"}
        )

    # Generate search_id
    search_id = str(uuid.uuid4())

    logger.info(
        f"[F1Search] Start: user={ctx.user_id[:8]}..., "
        f"org={ctx.org_id[:8]}..., search_id={search_id[:8]}..., "
        f"query_len={len(q)}"
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        """
        Generate SSE events.

        Event order:
        1. diagnostics (immediately)
        2. exact_match_win (if deterministic hit found)
        3. result_batch (as results arrive)
        4. finalized (at end)
        """
        start = time.time()
        first_event_ms = 0  # SSE diagnostics: time to first event
        early_win = False
        reranked = False
        total_results = 0
        pending_tasks: List[asyncio.Task] = []

        try:
            # Check for client disconnect
            if await request.is_disconnected():
                logger.info(f"[F1Search] Client disconnected: {search_id[:8]}...")
                return

            # ================================================================
            # Phase 1: Emit diagnostics immediately
            # ================================================================

            yield sse_event("diagnostics", {
                "search_id": search_id,
                "status": "started",
                "query": q,
                "timestamp": time.time(),
            })
            first_event_ms = int((time.time() - start) * 1000)

            # ================================================================
            # Phase 2: Generate rewrites and embeddings (≤3, ≤150ms, cached)
            # ================================================================

            with tracer.start_as_current_span("cortex.rewrite") as span:
                span.set_attribute("search_id", search_id)
                span.set_attribute("query", q)
                rewrite_result = await generate_rewrites(q, ctx)
                rewrites = rewrite_result.rewrites
                span.set_attribute("rewrite_count", len(rewrites) if rewrites else 0)
                span.set_attribute("cache_hit", rewrite_result.cache_hit if hasattr(rewrite_result, 'cache_hit') else False)

            # Fallback: if no rewrites, use original query
            if not rewrites:
                rewrites = [SimpleNamespace(text=q, embedding=None)]

            logger.debug(
                f"[F1Search] Rewrites: {len(rewrites)} in {rewrite_result.latency_ms}ms"
            )

            # Check disconnect
            if await request.is_disconnected():
                logger.info(f"[F1Search] Client disconnected after rewrites: {search_id[:8]}...")
                return

            # ================================================================
            # Phase 3: Check cache OR call hyper_search_multi
            # ================================================================

            cache_key = make_cache_key(q, ctx.org_id, ctx.yacht_id)
            redis_conn = await get_redis()
            result_cache_hit = False
            rows = None

            # Check cache first
            if redis_conn:
                with tracer.start_as_current_span("cache.get") as span:
                    span.set_attribute("cache_key", cache_key[:30])
                    cached_items = await get_cached_results(redis_conn, cache_key)
                    if cached_items is not None:
                        result_cache_hit = True
                        # Convert cached items back to row format
                        rows = cached_items
                        span.set_attribute("cache_hit", True)
                        logger.info(f"[F1Search] Cache HIT: {search_id[:8]}..., key={cache_key[:30]}...")
                    else:
                        span.set_attribute("cache_hit", False)

            # Cache miss - call DB
            if rows is None:
                with tracer.start_as_current_span("db.hyper_search_multi") as span:
                    span.set_attribute("search_id", search_id)
                    span.set_attribute("org_id", ctx.org_id)
                    span.set_attribute("rewrite_count", len(rewrites))
                    conn = await get_db_connection()
                    try:
                        rows = await call_hyper_search_multi(conn, rewrites, ctx, rrf_k=60, page_limit=20)
                    finally:
                        await conn.close()
                    span.set_attribute("result_count", len(rows))

            total_results = len(rows)

            # ================================================================
            # Phase 4: Early win check (deterministic) + emit results
            # ================================================================

            items = []
            if result_cache_hit:
                # Cache hit: rows are already processed items
                items = rows
            else:
                # Cache miss: process raw DB rows
                for r in rows:
                    item = dict(r)
                    # Parse JSONB fields (asyncpg returns them as strings)
                    for key in ('payload', 'ranks', 'components'):
                        if key in item and isinstance(item[key], str):
                            item[key] = json.loads(item[key])

                    items.append({
                        "object_type": item.get('object_type'),
                        "object_id": str(item.get('object_id')),
                        "payload": item.get('payload'),
                        "fused_score": item.get('fused_score'),
                        "best_rewrite_idx": item.get('best_rewrite_idx'),
                        "ranks": item.get('ranks'),
                        "components": item.get('components'),
                    })

                # Cache the processed items (only on cache miss, successful result)
                if redis_conn and len(items) > 0:
                    await set_cached_results(redis_conn, cache_key, items)

            # Check for exact win on first item
            if len(items) > 0 and is_exact_win(items[0]):
                early_win = True
                item = items[0]

                logger.info(
                    f"[F1Search] Early win: search_id={search_id[:8]}..., "
                    f"object_id={item.get('object_id')}, "
                    f"ranks={item.get('ranks')}"
                )

                yield sse_event("exact_match_win", {
                    "search_id": search_id,
                    "object_type": item.get('object_type'),
                    "object_id": str(item.get('object_id')),
                    "payload": item.get('payload'),
                    "fused_score": item.get('fused_score'),
                    "ranks": item.get('ranks'),
                })

                # Cancel any pending tasks on exact match
                for t in pending_tasks:
                    if not t.done():
                        t.cancel()

            # ================================================================
            # Phase 4b: Optional re-ranking (feature-flagged, 80ms budget)
            # ================================================================
            reranked = False
            if RERANKER_ENABLED and len(items) > 1 and not early_win:
                with tracer.start_as_current_span("rerank.apply") as span:
                    span.set_attribute("search_id", search_id)
                    span.set_attribute("item_count", len(items))
                    items = rerank_items(q, items, top_k=10, budget_ms=80)
                    reranked = any("rerank_score" in it for it in items)
                    span.set_attribute("reranked", reranked)
                if reranked:
                    logger.debug(f"[F1Search] Reranked {len(items)} items")

            # Emit result batch
            with tracer.start_as_current_span("fusion.emit_batch") as span:
                span.set_attribute("search_id", search_id)
                span.set_attribute("item_count", len(items))
                span.set_attribute("early_win", early_win)
                yield sse_event("result_batch", {
                    "search_id": search_id,
                    "items": items,
                    "partial": False,
                    "count": len(items),
                })

            # ================================================================
            # Phase 5: Finalize
            # ================================================================

            finalized_ms = int((time.time() - start) * 1000)

            yield sse_event("finalized", {
                "search_id": search_id,
                "latency_ms": finalized_ms,  # Backwards compat
                "first_event_ms": first_event_ms,
                "finalized_ms": finalized_ms,
                "total_results": total_results,
                "rewrites_count": len(rewrites),
                "rewrite_cache_hit": rewrite_result.cache_hit if hasattr(rewrite_result, 'cache_hit') else False,
                "result_cache_hit": result_cache_hit,
                "early_win": early_win,
                "reranked": reranked,
                "status": "early_win" if early_win else "completed",
            })

            logger.info(
                f"[F1Search] Complete: search_id={search_id[:8]}..., "
                f"first_event={first_event_ms}ms, finalized={finalized_ms}ms, "
                f"results={total_results}, rewrites={len(rewrites)}, early_win={early_win}, "
                f"result_cache={'HIT' if result_cache_hit else 'MISS'}"
            )

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"[F1Search] Cancelled: {search_id[:8]}...")
            raise

        except asyncpg.exceptions.QueryCanceledError:
            # statement_timeout exceeded
            logger.warning(f"[F1Search] Timeout: search_id={search_id[:8]}...")
            yield sse_event("error", {
                "search_id": search_id,
                "error": "timeout",
                "message": "Search timed out",
            })

        except asyncpg.exceptions.PostgresError as e:
            # Database error with SQLSTATE for diagnosability
            sqlstate = getattr(e, 'sqlstate', 'UNKNOWN')
            detail = getattr(e, 'detail', None)
            logger.error(
                f"[F1Search] DB Error: {search_id[:8]}..., "
                f"SQLSTATE={sqlstate}, error={e}, detail={detail}",
                exc_info=True
            )
            yield sse_event("error", {
                "search_id": search_id,
                "error": "database_error",
                "message": str(e),
                "sqlstate": sqlstate,
            })

        except Exception as e:
            # Emit error event with full details for debugging
            logger.error(f"[F1Search] Error: {search_id[:8]}..., error={e}", exc_info=True)
            yield sse_event("error", {
                "search_id": search_id,
                "error": "internal_error",
                "message": str(e),
                "error_type": type(e).__name__,
            })

    # Return SSE streaming response
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Search-Id": search_id,
        },
    )


# ============================================================================
# Click Tracking Endpoint
# ============================================================================

@router.post("/click")
async def f1_search_click(
    request: Request,
    auth: dict = Depends(get_authenticated_user),
):
    """
    Record search result click for popularity feedback.

    Body: {"search_id": "...", "object_type": "...", "object_id": "..."}
    """
    ctx = build_user_context(auth)

    body = await request.json()
    search_id = body.get("search_id")
    object_type = body.get("object_type")
    object_id = body.get("object_id")

    if not all([search_id, object_type, object_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: search_id, object_type, object_id"
        )

    try:
        conn = await get_db_connection()
        try:
            await conn.execute(
                """
                INSERT INTO search_clicks (search_id, user_id, org_id, yacht_id, object_type, object_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid.UUID(search_id),
                uuid.UUID(ctx.user_id),
                uuid.UUID(ctx.org_id),
                uuid.UUID(ctx.yacht_id) if ctx.yacht_id else None,
                object_type,
                uuid.UUID(object_id),
            )
        finally:
            await conn.close()

        return {"status": "recorded"}

    except Exception as e:
        logger.error(f"[F1Search] Click error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record click"
        )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def f1_search_health():
    """Health check for F1 Search streaming."""
    return {
        "status": "healthy",
        "version": "f1-phase2.5",
        "db_dsn_configured": bool(READ_DSN),
        "budget": {
            "max_rewrites": DEFAULT_BUDGET.max_rewrites,
            "rewrite_budget_ms": DEFAULT_BUDGET.rewrite_budget_ms,
            "db_timeout_ms": DEFAULT_BUDGET.db_timeout_ms,
            "global_timeout_ms": DEFAULT_BUDGET.global_timeout_ms,
            "vector_dim": DEFAULT_BUDGET.vector_dim,
        },
        "capabilities": [
            "sse_streaming",
            "signal_routing",
            "user_context",
            "cortex_rewrites",
            "hyper_search_multi",
            "asyncpg_single_roundtrip",
            "statement_timeout_120ms",
            "early_win_cancellation",
            "embedding_pipeline",
            "hnsw_vector_search",
            "click_tracking",
        ],
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "router",
    "f1_search_stream",
    "f1_search_click",
    "build_user_context",
    "is_exact_win",
]
