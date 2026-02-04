#!/usr/bin/env python3
"""
F1 Search - Cortex Rewrites

Generates tenant-aware query rewrites for hybrid search.

Budget: 150ms total, max 3 rewrites
Cache: (normalized_query, org_id, yacht_id, role, embedding_version)

See: apps/api/docs/F1_SEARCH/CORTEX_SPEC.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from functools import lru_cache

from openai import AsyncOpenAI

from services.types import UserContext, SearchBudget, DEFAULT_BUDGET

# Optional Redis for cross-process caching
try:
    import redis.asyncio as redis_async
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_async = None

# ============================================================================
# OpenAI Configuration
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small").replace("openai/", "")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))

_openai_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    """Get or create async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _normalize_vector(vec: List[float]) -> List[float]:
    """Normalize vector to unit length for cosine similarity."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]

logger = logging.getLogger(__name__)

# ============================================================================
# Types
# ============================================================================

@dataclass
class Rewrite:
    """A single query rewrite."""
    text: str
    source: str  # 'original', 'synonym', 'expansion', 'abbreviation'
    confidence: float = 1.0
    embedding: Optional[List[float]] = None


@dataclass
class RewriteResult:
    """Result of rewrite generation."""
    rewrites: List[Rewrite]
    cache_hit: bool = False
    latency_ms: int = 0
    budget_remaining_ms: int = 0


# ============================================================================
# Redis Connection (optional, graceful degradation)
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL")
_redis: Optional[Any] = None


async def _get_redis():
    """Get or create Redis connection (lazy, graceful degradation)."""
    global _redis
    if not REDIS_AVAILABLE or not REDIS_URL:
        return None
    if _redis is None:
        try:
            _redis = await redis_async.from_url(REDIS_URL, decode_responses=True)
            await _redis.ping()
            logger.info("[Cortex] Redis connected for rewrite/embedding cache")
        except Exception as e:
            logger.warning(f"[Cortex] Redis unavailable: {e}")
            _redis = False  # Mark as failed, don't retry
    return _redis if _redis else None


# ============================================================================
# Rewrite Cache (Redis-first with local LRU fallback)
# ============================================================================

# In-memory cache: key -> (rewrites, timestamp)
_rewrite_cache: Dict[str, Tuple[List[Rewrite], float]] = {}
_CACHE_TTL_SECONDS = int(os.getenv("REWRITE_CACHE_TTL", "900"))  # 15 minutes default
_CACHE_MAX_SIZE = 1000


def _build_cache_key(
    query: str,
    ctx: UserContext,
    embedding_version: int = 1
) -> str:
    """
    Build cache key for rewrites.

    Key components:
    - Normalized query (lowercase, stripped)
    - org_id (tenant isolation)
    - yacht_id (optional yacht scope)
    - role (role-aware rewrites)
    - embedding_version (invalidate on model change)
    """
    normalized = query.lower().strip()
    components = [
        normalized,
        ctx.org_id,
        ctx.yacht_id or "",
        ctx.role,
        str(embedding_version),
    ]
    key_str = "|".join(components)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


async def _get_cached_rewrites(key: str) -> Optional[List[Rewrite]]:
    """Get rewrites from Redis (primary) or local cache (fallback)."""
    # Try Redis first
    redis_conn = await _get_redis()
    if redis_conn:
        try:
            raw = await redis_conn.get(f"rw:{key}")
            if raw:
                data = json.loads(raw)
                return [Rewrite(**item) for item in data]
        except Exception as e:
            logger.debug(f"[Cortex] Redis get error: {e}")

    # Fallback to local cache
    if key in _rewrite_cache:
        rewrites, timestamp = _rewrite_cache[key]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            return rewrites
        else:
            del _rewrite_cache[key]
    return None


async def _set_cached_rewrites(key: str, rewrites: List[Rewrite]) -> None:
    """Set rewrites in Redis (primary) or local cache (fallback)."""
    global _rewrite_cache

    # Try Redis first
    redis_conn = await _get_redis()
    if redis_conn:
        try:
            payload = json.dumps([asdict(r) for r in rewrites])
            await redis_conn.setex(f"rw:{key}", _CACHE_TTL_SECONDS, payload)
            return
        except Exception as e:
            logger.debug(f"[Cortex] Redis set error: {e}")

    # Fallback to local cache
    if len(_rewrite_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_rewrite_cache.keys(), key=lambda k: _rewrite_cache[k][1])
        del _rewrite_cache[oldest_key]
    _rewrite_cache[key] = (rewrites, time.time())


# ============================================================================
# Synonym Expansion Rules
# ============================================================================

# Domain-specific synonyms for maritime/yacht context
SYNONYM_MAP: Dict[str, List[str]] = {
    # Equipment
    "filter": ["element", "strainer", "cartridge"],
    "pump": ["impeller", "motor pump"],
    "engine": ["motor", "powerplant", "main engine"],
    "generator": ["genset", "gen", "alternator"],
    "watermaker": ["desalinator", "reverse osmosis", "ro system"],

    # Parts
    "gasket": ["seal", "o-ring"],
    "bearing": ["bushing"],
    "belt": ["v-belt", "serpentine belt", "drive belt"],
    "impeller": ["pump impeller", "water impeller"],

    # Brands (expand abbreviations)
    "cat": ["caterpillar"],
    "cummins": ["qsm"],
    "volvo": ["volvo penta"],
    "nl": ["northern lights"],

    # Actions/Status
    "replace": ["change", "swap", "install"],
    "repair": ["fix", "service", "overhaul"],
    "low stock": ["below minimum", "needs reorder"],
    "out of stock": ["zero quantity", "none available"],

    # Locations
    "engine room": ["er", "machinery space"],
    "bridge": ["wheelhouse", "pilothouse"],
    "lazarette": ["stern locker", "aft storage"],
}

# Abbreviation expansions
ABBREVIATION_MAP: Dict[str, str] = {
    "er": "engine room",
    "me": "main engine",
    "gen": "generator",
    "wo": "work order",
    "po": "purchase order",
    "qty": "quantity",
    "min": "minimum",
    "loc": "location",
    "mfg": "manufacturer",
}


# ============================================================================
# Rewrite Generation
# ============================================================================

def _generate_synonyms(query: str) -> List[Rewrite]:
    """
    Generate synonym-based rewrites.

    Returns up to 2 synonym rewrites.
    """
    rewrites = []
    query_lower = query.lower()

    for term, synonyms in SYNONYM_MAP.items():
        if term in query_lower:
            for syn in synonyms[:2]:  # Max 2 synonyms per term
                rewritten = query_lower.replace(term, syn)
                if rewritten != query_lower:
                    rewrites.append(Rewrite(
                        text=rewritten,
                        source="synonym",
                        confidence=0.85,
                    ))
                if len(rewrites) >= 2:
                    return rewrites

    return rewrites


def _expand_abbreviations(query: str) -> Optional[Rewrite]:
    """
    Expand abbreviations in query.

    Returns single expansion rewrite if any abbreviation found.
    """
    query_lower = query.lower()
    expanded = query_lower

    for abbrev, expansion in ABBREVIATION_MAP.items():
        # Match whole word only
        import re
        pattern = r'\b' + re.escape(abbrev) + r'\b'
        if re.search(pattern, expanded):
            expanded = re.sub(pattern, expansion, expanded)

    if expanded != query_lower:
        return Rewrite(
            text=expanded,
            source="abbreviation",
            confidence=0.9,
        )

    return None


def _generate_prefix_expansion(query: str) -> Optional[Rewrite]:
    """
    Add context prefix for short queries.

    Example: "3512C" -> "caterpillar 3512C engine"
    """
    query_lower = query.lower().strip()

    # Model numbers often benefit from brand/type context
    import re
    if re.match(r'^[a-z]?\d{3,4}[a-z]?$', query_lower, re.I):
        # Looks like a model number
        return Rewrite(
            text=f"{query_lower} engine part",
            source="expansion",
            confidence=0.7,
        )

    return None


async def generate_rewrites(
    query: str,
    ctx: UserContext,
    budget: SearchBudget = DEFAULT_BUDGET,
    embedding_version: int = 1,
) -> RewriteResult:
    """
    Generate tenant-aware query rewrites.

    Budget: 150ms total, max 3 rewrites
    Cache: 5 minute TTL, tenant-isolated

    Args:
        query: Original search query
        ctx: UserContext with org_id, yacht_id, role
        budget: SearchBudget (default 150ms for rewrites)
        embedding_version: Current embedding model version (for cache key)

    Returns:
        RewriteResult with list of Rewrite objects

    GUARDRAILS:
    - Max 3 rewrites (including original)
    - Must complete within budget.rewrite_budget_ms
    - Cache key includes tenant context for isolation
    """
    start_time = time.time()
    budget_ms = budget.rewrite_budget_ms

    # Build cache key
    cache_key = _build_cache_key(query, ctx, embedding_version)

    # Check cache
    cached = await _get_cached_rewrites(cache_key)
    if cached:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.debug(f"[Cortex] Cache hit for query: {cache_key[:8]}...")
        return RewriteResult(
            rewrites=cached,
            cache_hit=True,
            latency_ms=latency_ms,
            budget_remaining_ms=budget_ms - latency_ms,
        )

    # Start with original query
    rewrites = [Rewrite(
        text=query,
        source="original",
        confidence=1.0,
    )]

    # Check time budget
    def _time_remaining_ms() -> int:
        return budget_ms - int((time.time() - start_time) * 1000)

    # Generate abbreviation expansion
    if _time_remaining_ms() > 10:
        abbrev_rewrite = _expand_abbreviations(query)
        if abbrev_rewrite and abbrev_rewrite.text not in [r.text for r in rewrites]:
            rewrites.append(abbrev_rewrite)

    # Generate synonym rewrites
    if len(rewrites) < 3 and _time_remaining_ms() > 10:
        synonym_rewrites = _generate_synonyms(query)
        for sr in synonym_rewrites:
            if len(rewrites) >= 3:
                break
            if sr.text not in [r.text for r in rewrites]:
                rewrites.append(sr)

    # Generate prefix expansion for short queries
    if len(rewrites) < 3 and len(query.strip()) <= 8 and _time_remaining_ms() > 10:
        prefix_rewrite = _generate_prefix_expansion(query)
        if prefix_rewrite and prefix_rewrite.text not in [r.text for r in rewrites]:
            rewrites.append(prefix_rewrite)

    # Cap at 3 rewrites
    rewrites = rewrites[:3]

    # Cache results
    await _set_cached_rewrites(cache_key, rewrites)

    latency_ms = int((time.time() - start_time) * 1000)

    logger.info(
        f"[Cortex] Generated {len(rewrites)} rewrites in {latency_ms}ms "
        f"(budget: {budget_ms}ms, org: {ctx.org_id[:8]}...)"
    )

    return RewriteResult(
        rewrites=rewrites,
        cache_hit=False,
        latency_ms=latency_ms,
        budget_remaining_ms=budget_ms - latency_ms,
    )


# ============================================================================
# Embedding Generation (OpenAI text-embedding-3-small, 1536-d)
# ============================================================================

# Embedding cache: (text, model_version) -> (embedding, timestamp)
_embedding_cache: Dict[str, Tuple[List[float], float]] = {}
_EMBED_CACHE_TTL_SECONDS = 1800  # 30 minutes
_EMBED_CACHE_MAX_SIZE = 500


def _get_embed_cache_key(text: str, org_id: str) -> str:
    """Build cache key for embedding."""
    normalized = text.lower().strip()
    return hashlib.sha256(f"{normalized}|{org_id}|{EMBED_DIM}".encode()).hexdigest()[:32]


async def _get_cached_embedding(key: str) -> Optional[List[float]]:
    """Get embedding from Redis (primary) or local cache (fallback)."""
    # Try Redis first
    redis_conn = await _get_redis()
    if redis_conn:
        try:
            raw = await redis_conn.get(f"emb:{key}")
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.debug(f"[Cortex] Redis embedding get error: {e}")

    # Fallback to local cache
    if key in _embedding_cache:
        embedding, timestamp = _embedding_cache[key]
        if time.time() - timestamp < _EMBED_CACHE_TTL_SECONDS:
            return embedding
        else:
            del _embedding_cache[key]
    return None


async def _set_cached_embedding(key: str, embedding: List[float]) -> None:
    """Set embedding in Redis (primary) or local cache (fallback)."""
    global _embedding_cache

    # Try Redis first
    redis_conn = await _get_redis()
    if redis_conn:
        try:
            payload = json.dumps(embedding)
            await redis_conn.setex(f"emb:{key}", _EMBED_CACHE_TTL_SECONDS, payload)
            return
        except Exception as e:
            logger.debug(f"[Cortex] Redis embedding set error: {e}")

    # Fallback to local cache
    if len(_embedding_cache) >= _EMBED_CACHE_MAX_SIZE:
        oldest_key = min(_embedding_cache.keys(), key=lambda k: _embedding_cache[k][1])
        del _embedding_cache[oldest_key]
    _embedding_cache[key] = (embedding, time.time())


async def generate_embeddings(
    rewrites: List[Rewrite],
    budget_ms: int = 100,
    org_id: str = "",
) -> List[Rewrite]:
    """
    Generate 1536-d embeddings for rewrites using OpenAI API.

    Args:
        rewrites: List of Rewrite objects to embed
        budget_ms: Time budget for embedding generation
        org_id: Organization ID for cache isolation

    Returns:
        List of Rewrite objects with embeddings populated (where possible)

    GUARDRAILS:
    - Timeout after budget_ms to avoid blocking search
    - Cache embeddings for 30 minutes per org
    - If embedding fails, return rewrite without embedding (text search continues)
    """
    if not OPENAI_API_KEY:
        logger.warning("[Cortex] OPENAI_API_KEY not set, skipping embeddings")
        return rewrites

    start_time = time.time()

    # Collect texts that need embedding (check cache first)
    texts_to_embed = []
    cache_keys = []
    for rewrite in rewrites:
        cache_key = _get_embed_cache_key(rewrite.text, org_id)
        cached = await _get_cached_embedding(cache_key)
        if cached:
            rewrite.embedding = cached
            logger.debug(f"[Cortex] Embedding cache hit: {rewrite.text[:20]}...")
        else:
            texts_to_embed.append(rewrite.text)
            cache_keys.append(cache_key)

    if not texts_to_embed:
        logger.debug("[Cortex] All embeddings from cache")
        return rewrites

    # Call OpenAI API with timeout
    try:
        client = _get_openai_client()

        # Calculate remaining budget
        elapsed_ms = int((time.time() - start_time) * 1000)
        remaining_ms = max(10, budget_ms - elapsed_ms)

        # Truncate texts if too long
        max_chars = 8000
        truncated_texts = [t[:max_chars] for t in texts_to_embed]

        # Call embedding API with timeout
        response = await asyncio.wait_for(
            client.embeddings.create(
                model=EMBED_MODEL,
                input=truncated_texts,
                dimensions=EMBED_DIM
            ),
            timeout=remaining_ms / 1000.0
        )

        # Map embeddings back to rewrites
        text_to_embedding = {}
        for i, data in enumerate(response.data):
            text = texts_to_embed[i]
            embedding = _normalize_vector(data.embedding)
            text_to_embedding[text] = embedding
            # Cache the embedding
            await _set_cached_embedding(cache_keys[i], embedding)

        # Update rewrites with embeddings
        for rewrite in rewrites:
            if rewrite.embedding is None and rewrite.text in text_to_embedding:
                rewrite.embedding = text_to_embedding[rewrite.text]

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"[Cortex] Generated {len(text_to_embedding)} embeddings in {latency_ms}ms "
            f"(budget: {budget_ms}ms)"
        )

    except asyncio.TimeoutError:
        logger.warning(f"[Cortex] Embedding timeout after {budget_ms}ms, continuing with text search")
    except Exception as e:
        logger.error(f"[Cortex] Embedding error: {e}, continuing with text search")

    return rewrites


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "generate_rewrites",
    "generate_embeddings",
    "Rewrite",
    "RewriteResult",
]
