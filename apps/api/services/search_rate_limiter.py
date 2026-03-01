"""
CelesteOS API - Streaming Rate Limit Service
=============================================

In-memory rate limiting for streaming search endpoints.

Features:
- Token bucket rate limiting (per-user)
- Concurrency limiting (per-yacht)
- Configurable via environment variables
- Designed for Redis migration (later)

Security invariants:
1. Rate limits prevent resource exhaustion attacks
2. Concurrency limits protect yacht from internal abuse
3. 429 errors don't leak metadata (generic messages)
4. All limits are yacht-scoped to prevent cross-tenant impact

Usage:
    from services.rate_limit import (
        InMemoryRateLimiter,
        InMemoryConcurrencyGate,
        STREAM_USER_BURST,
        STREAM_USER_RATE,
    )

    limiter = InMemoryRateLimiter()
    allowed = await limiter.allow(
        scope="search",
        key=f"user:{ctx.user_id}",
        capacity=STREAM_USER_BURST,
        refill_rate=STREAM_USER_RATE,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited")
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration (feature flags via environment)
# ============================================================================

# Minimum query prefix length (default 3)
STREAM_MIN_PREFIX = int(os.getenv("STREAM_MIN_PREFIX", "3"))

# User rate limits (token bucket)
STREAM_USER_BURST = int(os.getenv("STREAM_USER_BURST", "10"))  # Max burst capacity
STREAM_USER_RATE = float(os.getenv("STREAM_USER_RATE", "2.0"))  # Tokens per second

# Yacht concurrency limits
STREAM_YACHT_CONCURRENCY = int(os.getenv("STREAM_YACHT_CONCURRENCY", "10"))

# Cache TTLs (seconds)
STREAM_PHASE1_TTL = int(os.getenv("STREAM_PHASE1_TTL", "60"))  # Phase 1: counts only
STREAM_PHASE2_TTL = int(os.getenv("STREAM_PHASE2_TTL", "15"))  # Phase 2: details


# ============================================================================
# Token Bucket Rate Limiter
# ============================================================================

@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Tokens refill at a constant rate up to capacity.
    Each request consumes one token.
    """
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float
    last: float

    @classmethod
    def create(cls, capacity: int, refill_rate: float) -> "TokenBucket":
        """Create a new token bucket at full capacity."""
        now = time.monotonic()
        return cls(
            capacity=capacity,
            refill_rate=refill_rate,
            tokens=float(capacity),
            last=now,
        )

    def allow(self) -> bool:
        """
        Try to consume a token.

        Returns:
            True if token consumed (request allowed)
            False if no tokens available (rate limited)
        """
        now = time.monotonic()
        delta = now - self.last

        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def tokens_available(self) -> float:
        """Get current available tokens (for monitoring)."""
        now = time.monotonic()
        delta = now - self.last
        return min(self.capacity, self.tokens + delta * self.refill_rate)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using token buckets.

    Thread-safe via asyncio lock.
    Designed for single-process deployment; migrate to Redis for multi-process.
    """

    def __init__(self) -> None:
        self._buckets: Dict[Tuple[str, str], TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def allow(
        self,
        scope: str,
        key: str,
        capacity: int,
        refill_rate: float,
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            scope: Namespace for the limit (e.g., "search", "api")
            key: Unique identifier (e.g., "user:uuid")
            capacity: Maximum burst size
            refill_rate: Tokens per second

        Returns:
            True if allowed, False if rate limited
        """
        async with self._lock:
            bucket_key = (scope, key)
            tb = self._buckets.get(bucket_key)

            if tb is None:
                tb = TokenBucket.create(capacity, refill_rate)
                self._buckets[bucket_key] = tb

            allowed = tb.allow()

            if not allowed:
                logger.warning(
                    f"[RateLimit] Denied: scope={scope}, key={key[:16]}..., "
                    f"tokens={tb.tokens:.2f}"
                )

            return allowed

    async def get_stats(self, scope: str, key: str) -> Optional[Dict]:
        """Get rate limit stats for monitoring."""
        async with self._lock:
            bucket_key = (scope, key)
            tb = self._buckets.get(bucket_key)
            if tb is None:
                return None
            return {
                "capacity": tb.capacity,
                "tokens": tb.tokens_available(),
                "refill_rate": tb.refill_rate,
            }

    async def clear(self, scope: str = None) -> int:
        """
        Clear rate limit state.

        Args:
            scope: If provided, only clear buckets in this scope

        Returns:
            Number of buckets cleared
        """
        async with self._lock:
            if scope is None:
                count = len(self._buckets)
                self._buckets.clear()
            else:
                keys_to_remove = [k for k in self._buckets if k[0] == scope]
                for k in keys_to_remove:
                    del self._buckets[k]
                count = len(keys_to_remove)

            logger.info(f"[RateLimit] Cleared {count} buckets (scope={scope})")
            return count


# ============================================================================
# Concurrency Gate
# ============================================================================

class InMemoryConcurrencyGate:
    """
    In-memory concurrency limiter.

    Limits concurrent requests per key (e.g., per-yacht).
    Thread-safe via asyncio lock.
    """

    def __init__(self, default_limit: int = 10) -> None:
        self._limit_by_key: Dict[str, int] = {}
        self._inflight: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._default = default_limit

    def set_limit(self, key: str, limit: int) -> None:
        """Set custom limit for a specific key."""
        self._limit_by_key[key] = limit

    async def try_acquire(self, key: str) -> bool:
        """
        Try to acquire a concurrency slot.

        Args:
            key: Unique identifier (e.g., yacht_id)

        Returns:
            True if slot acquired, False if at limit
        """
        async with self._lock:
            limit = self._limit_by_key.get(key, self._default)
            current = self._inflight.get(key, 0)

            if current >= limit:
                logger.warning(
                    f"[Concurrency] Denied: key={key[:16]}..., "
                    f"current={current}, limit={limit}"
                )
                return False

            self._inflight[key] = current + 1
            return True

    async def release(self, key: str) -> None:
        """Release a concurrency slot."""
        async with self._lock:
            current = self._inflight.get(key, 0)
            if current > 0:
                self._inflight[key] = current - 1

    async def get_current(self, key: str) -> int:
        """Get current inflight count for key."""
        async with self._lock:
            return self._inflight.get(key, 0)

    async def get_stats(self, key: str) -> Dict:
        """Get concurrency stats for monitoring."""
        async with self._lock:
            limit = self._limit_by_key.get(key, self._default)
            current = self._inflight.get(key, 0)
            return {
                "current": current,
                "limit": limit,
                "available": limit - current,
            }


# ============================================================================
# Context Manager for Concurrency
# ============================================================================

class ConcurrencySlot:
    """
    Context manager for automatic concurrency slot release.

    Usage:
        async with ConcurrencySlot(gate, yacht_id) as acquired:
            if not acquired:
                raise HTTPException(429, "concurrency_limited")
            # Do work
    """

    def __init__(self, gate: InMemoryConcurrencyGate, key: str):
        self._gate = gate
        self._key = key
        self._acquired = False

    async def __aenter__(self) -> bool:
        self._acquired = await self._gate.try_acquire(self._key)
        return self._acquired

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            await self._gate.release(self._key)


# ============================================================================
# Singleton Instances (for module-level use)
# ============================================================================

# Global instances for use across the application
# In production, these could be replaced with Redis-backed implementations
_rate_limiter: Optional[InMemoryRateLimiter] = None
_concurrency_gate: Optional[InMemoryConcurrencyGate] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


def get_concurrency_gate() -> InMemoryConcurrencyGate:
    """Get the singleton concurrency gate instance."""
    global _concurrency_gate
    if _concurrency_gate is None:
        _concurrency_gate = InMemoryConcurrencyGate(default_limit=STREAM_YACHT_CONCURRENCY)
    return _concurrency_gate


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Configuration
    "STREAM_MIN_PREFIX",
    "STREAM_USER_BURST",
    "STREAM_USER_RATE",
    "STREAM_YACHT_CONCURRENCY",
    "STREAM_PHASE1_TTL",
    "STREAM_PHASE2_TTL",
    # Classes
    "TokenBucket",
    "InMemoryRateLimiter",
    "InMemoryConcurrencyGate",
    "ConcurrencySlot",
    # Singletons
    "get_rate_limiter",
    "get_concurrency_gate",
]
