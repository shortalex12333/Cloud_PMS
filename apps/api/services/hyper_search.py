#!/usr/bin/env python3
"""
Hyper Search Service — f1_search_cards RPC wrapper + signal connection pool.

Two concerns:
1. call_hyper_search(): Shared RPC wrapper used by both spotlight and signal.
   Callers pass their own connection — this function is pool-agnostic.
2. get_db_pool(): Signal-only pool (12s timeout, min_size=2).
   Spotlight maintains its own pool in routes/f1_search_streaming.py (800ms).

Consumers:
- routes/f1_search_streaming.py     (spotlight — uses call_hyper_search only, own pool)
- handlers/show_related_signal_handlers.py  (signal — uses both pool + call_hyper_search)
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import asyncpg

from cortex.rewrites import Rewrite
from services.types import UserContext

logger = logging.getLogger(__name__)


# ============================================================================
# Database Connection
# ============================================================================

_raw_dsn = os.getenv("READ_DB_DSN") or os.getenv("DATABASE_URL")

# Ensure Supavisor pooler (port 6543) not direct connection (port 5432).
# Direct connections exhaust PostgreSQL slots under SSE streaming load.
if _raw_dsn and ":5432" in _raw_dsn:
    READ_DSN: Optional[str] = _raw_dsn.replace(":5432", ":6543")
    logger.warning("[HyperSearch] Switched port 5432 → 6543 (Supavisor pooler)")
else:
    READ_DSN = _raw_dsn

_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Best-effort statement_timeout for signal pool connections.

    Supavisor transaction mode resets this after the first query.
    The actual hard ceiling is command_timeout=15s on the pool.
    Kept for direct-connection scenarios (local dev, non-Supavisor).
    """
    await conn.execute("SET statement_timeout = '12000ms'")


async def get_db_pool() -> asyncpg.Pool:
    """Get or create the signal search connection pool.

    This pool is used ONLY by the signal handler (show_related_signal_routes.py).
    The spotlight endpoint (f1_search_streaming.py) has its own pool with 800ms timeout.

    command_timeout=15s: must exceed statement_timeout (12s) + network latency.
    Signal search is not latency-critical — runs on-demand when panel opens.
    """
    global _pool
    if _pool is None:
        if not READ_DSN:
            raise ValueError("READ_DB_DSN or DATABASE_URL not configured")
        _pool = await asyncpg.create_pool(
            READ_DSN,
            min_size=2,
            max_size=5,
            command_timeout=15.0,  # must exceed statement_timeout (12s) + network latency
            statement_cache_size=0,  # LAW 14: pgbouncer/Supavisor compatibility
            init=_init_connection,
        )
    return _pool


async def get_db_connection() -> asyncpg.Connection:
    """Get a single connection with statement_timeout (for non-pooled use)."""
    if not READ_DSN:
        raise ValueError("READ_DB_DSN or DATABASE_URL not configured")
    conn = await asyncpg.connect(
        READ_DSN,
        statement_cache_size=0,  # LAW 14
    )
    await conn.execute("SET statement_timeout = '800ms'")
    return conn


# ============================================================================
# f1_search_cards RPC Wrapper
# ============================================================================

async def call_hyper_search(
    conn: asyncpg.Connection,
    rewrites: List[Rewrite],
    ctx: UserContext,
    rrf_k: int = 60,
    page_limit: int = 20,
    object_types: Optional[List[str]] = None,
    exclude_ids: Optional[List[str]] = None,
    vessel_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Call f1_search_cards RPC via asyncpg (single round-trip).

    GUARDRAILS:
    - ctx.org_id is required (RLS enforcement)
    - Max 3 rewrites honoured
    - statement_timeout enforced at connection level

    Args:
        conn: asyncpg connection (from pool)
        rewrites: List of Rewrite objects (max 3)
        ctx: UserContext with org_id and yacht_id
        rrf_k: RRF smoothing constant (default 60, Waterloo paper)
        page_limit: Max results to return (default 20)
        object_types: Optional filter by object_type list (None = all types)
        exclude_ids: Optional list of object_ids to exclude post-RPC

    Returns:
        List of dicts with keys: object_type, object_id, payload,
        fused_score, best_rewrite_idx, ranks, components
    """
    rewrites = rewrites[:3]

    texts = [r.text for r in rewrites]

    # Build pgvector literals; pass NULL for rewrites without an embedding
    vec_literals = []
    for r in rewrites:
        if r.embedding is not None:
            vec_literals.append(f"[{','.join(str(x) for x in r.embedding)}]")
        else:
            vec_literals.append(None)

    # Dynamic trigram threshold based on query length
    # Short queries (IDs/codes ≤6 chars): lower threshold for recall
    original_query = texts[0] if texts else ""
    trgm_limit = 0.07 if len(original_query.strip()) <= 6 else 0.15

    # Multi-vessel search: run search per vessel and merge by fused_score.
    # Each vessel gets its own f1_search_cards call — results are attributed.
    if vessel_ids and len(vessel_ids) > 1:
        import asyncio
        all_results = []

        async def search_vessel(vid: str):
            try:
                vid_uuid = uuid.UUID(vid)
            except ValueError:
                return []  # Skip non-UUID vessel IDs
            vessel_rows = await conn.fetch(
                """
                SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components
                FROM f1_search_cards($1::text[], $2::vector(1536)[], $3::uuid, $4::uuid, $5::int, $6::int, $7::real, $8::text[])
                """,
                texts, vec_literals, uuid.UUID(ctx.org_id), vid_uuid,
                rrf_k, page_limit, trgm_limit, object_types,
            )
            results = []
            for r in vessel_rows:
                d = dict(r)
                # Attribute each result to its vessel
                if isinstance(d.get("payload"), dict):
                    d["payload"]["yacht_id"] = vid
                results.append(d)
            return results

        # Run searches sequentially (same connection, can't parallelize on one conn)
        for vid in vessel_ids:
            vessel_results = await search_vessel(vid)
            all_results.extend(vessel_results)

        # Merge by fused_score descending, take top page_limit
        all_results.sort(key=lambda r: r.get("fused_score", 0), reverse=True)
        results = all_results[:page_limit]
    else:
        # Single vessel search (existing behavior)
        rows = await conn.fetch(
            """
            SELECT object_type, object_id, payload, fused_score, best_rewrite_idx, ranks, components
            FROM f1_search_cards($1::text[], $2::vector(1536)[], $3::uuid, $4::uuid, $5::int, $6::int, $7::real, $8::text[])
            """,
            texts, vec_literals, uuid.UUID(ctx.org_id),
            uuid.UUID(ctx.yacht_id) if ctx.yacht_id else None,
            rrf_k, page_limit, trgm_limit, object_types,
        )
        results = [dict(r) for r in rows]

    # Post-RPC exclusion (e.g. exclude the source entity from its own results)
    if exclude_ids:
        exclude_set = set(str(i) for i in exclude_ids)
        results = [r for r in results if str(r.get("object_id", "")) not in exclude_set]

    return results


__all__ = [
    "call_hyper_search",
    "get_db_pool",
    "get_db_connection",
]
