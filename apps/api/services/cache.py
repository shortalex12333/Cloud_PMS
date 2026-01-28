"""
CelesteOS API - Cache Service
==============================

Centralized caching with invalidation for security-critical operations.

Security invariants:
1. Cache keys MUST include yacht_id, user_id, role to prevent cross-tenant bleed
2. Role changes MUST trigger cache invalidation
3. Membership revocation MUST trigger cache invalidation
4. TTL-bounded caching (max 120s for security-sensitive data)
5. Explicit invalidation for immediate effect (in addition to TTL)

Key format: v1:{tenant}:{yacht_id}:{user_id}:{role}:{endpoint}:{phase}:{query_hash}

Usage:
    from services.cache import (
        CacheService,
        get_cache_service,
        clear_cache_for_user,
        clear_cache_for_yacht,
    )

    # Build keys using the builder
    cache = get_cache_service()
    key = cache.build_key(ctx, "search", query_hash, phase=1)

    # Invalidate on role change
    clear_cache_for_user(user_id, yacht_id)

    # Invalidate on yacht freeze
    clear_cache_for_yacht(yacht_id)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
import hashlib

from utils.cache_keys import (
    build_cache_key,
    build_streaming_cache_key,
    normalize_query_hash,
    CACHE_KEY_VERSION,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Max TTL for cached data (seconds)
CACHE_MAX_TTL = int(os.getenv("CACHE_MAX_TTL", "120"))

# Default TTLs by type
CACHE_TTL_SEARCH = int(os.getenv("CACHE_TTL_SEARCH", "60"))
CACHE_TTL_STREAMING_P1 = int(os.getenv("CACHE_TTL_STREAMING_P1", "60"))
CACHE_TTL_STREAMING_P2 = int(os.getenv("CACHE_TTL_STREAMING_P2", "15"))
CACHE_TTL_BOOTSTRAP = int(os.getenv("CACHE_TTL_BOOTSTRAP", "300"))


# ============================================================================
# Cache Entry
# ============================================================================

@dataclass
class CacheEntry:
    """Single cache entry with TTL."""
    value: Any
    expires_at: float
    yacht_id: str
    user_id: str
    role: str

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


# ============================================================================
# In-Memory Cache Store
# ============================================================================

class InMemoryCacheStore:
    """
    In-memory cache store with TTL and prefix-based invalidation.

    Thread-safe via asyncio lock.
    Designed for single-process deployment; migrate to Redis for multi-process.
    """

    def __init__(self) -> None:
        self._store: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        # Index for fast invalidation
        self._by_yacht: Dict[str, Set[str]] = {}  # yacht_id -> set of keys
        self._by_user: Dict[str, Set[str]] = {}   # user_id -> set of keys

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired:
                self._remove_key(key)
                return None
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int,
        yacht_id: str,
        user_id: str,
        role: str,
    ) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            # Enforce max TTL
            effective_ttl = min(ttl, CACHE_MAX_TTL)

            entry = CacheEntry(
                value=value,
                expires_at=time.monotonic() + effective_ttl,
                yacht_id=yacht_id,
                user_id=user_id,
                role=role,
            )
            self._store[key] = entry

            # Update indexes
            if yacht_id not in self._by_yacht:
                self._by_yacht[yacht_id] = set()
            self._by_yacht[yacht_id].add(key)

            if user_id not in self._by_user:
                self._by_user[user_id] = set()
            self._by_user[user_id].add(key)

    async def delete(self, key: str) -> bool:
        """Delete a single key."""
        async with self._lock:
            return self._remove_key(key)

    def _remove_key(self, key: str) -> bool:
        """Remove key from store and indexes (not thread-safe, use under lock)."""
        entry = self._store.pop(key, None)
        if entry is None:
            return False

        # Remove from indexes
        if entry.yacht_id in self._by_yacht:
            self._by_yacht[entry.yacht_id].discard(key)
        if entry.user_id in self._by_user:
            self._by_user[entry.user_id].discard(key)

        return True

    async def clear_for_user(self, user_id: str, yacht_id: str = None) -> int:
        """
        Clear all cache entries for a user.

        If yacht_id provided, only clear entries for that user+yacht combination.

        Args:
            user_id: User UUID
            yacht_id: Optional yacht UUID for scoped clear

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            keys_to_remove = set()

            user_keys = self._by_user.get(user_id, set()).copy()
            for key in user_keys:
                entry = self._store.get(key)
                if entry is None:
                    continue
                if yacht_id is None or entry.yacht_id == yacht_id:
                    keys_to_remove.add(key)

            count = 0
            for key in keys_to_remove:
                if self._remove_key(key):
                    count += 1

            logger.info(
                f"[Cache] Cleared {count} entries for user={user_id[:8]}..., "
                f"yacht={yacht_id[:8] if yacht_id else 'all'}..."
            )
            return count

    async def clear_for_yacht(self, yacht_id: str) -> int:
        """
        Clear all cache entries for a yacht.

        Args:
            yacht_id: Yacht UUID

        Returns:
            Number of entries cleared
        """
        async with self._lock:
            keys_to_remove = self._by_yacht.get(yacht_id, set()).copy()

            count = 0
            for key in keys_to_remove:
                if self._remove_key(key):
                    count += 1

            logger.info(f"[Cache] Cleared {count} entries for yacht={yacht_id[:8]}...")
            return count

    async def clear_all(self) -> int:
        """Clear entire cache."""
        async with self._lock:
            count = len(self._store)
            self._store.clear()
            self._by_yacht.clear()
            self._by_user.clear()
            logger.info(f"[Cache] Cleared all {count} entries")
            return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total = len(self._store)
            expired = sum(1 for e in self._store.values() if e.is_expired)
            by_yacht = {k: len(v) for k, v in self._by_yacht.items()}
            by_user = {k: len(v) for k, v in self._by_user.items()}

            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "yachts_cached": len(by_yacht),
                "users_cached": len(by_user),
            }

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            expired_keys = [k for k, v in self._store.items() if v.is_expired]
            count = 0
            for key in expired_keys:
                if self._remove_key(key):
                    count += 1
            if count > 0:
                logger.info(f"[Cache] Cleaned up {count} expired entries")
            return count


# ============================================================================
# Cache Service
# ============================================================================

class CacheService:
    """
    High-level cache service with key building and invalidation.

    Enforces security invariants:
    - Keys always include yacht_id, user_id, role
    - TTL bounded to CACHE_MAX_TTL
    - Invalidation APIs for role change and revocation
    """

    def __init__(self, store: InMemoryCacheStore = None) -> None:
        self._store = store or InMemoryCacheStore()

    def build_key(
        self,
        ctx,
        endpoint: str,
        query_hash: str,
        phase: int = 1,
        dataset_version: str = None,
    ) -> str:
        """
        Build cache key from context.

        Args:
            ctx: ActionContext or similar with yacht_id, user_id, role
            endpoint: Endpoint name
            query_hash: Hashed query
            phase: Phase number (1 or 2)
            dataset_version: Optional version for cache busting

        Returns:
            Cache key string
        """
        return build_cache_key(
            endpoint=endpoint,
            yacht_id=getattr(ctx, 'yacht_id', ''),
            user_id=getattr(ctx, 'user_id', ''),
            role=getattr(ctx, 'role', ''),
            query_hash=query_hash,
            phase=phase,
            tenant_key_alias=getattr(ctx, 'tenant_key_alias', None),
            dataset_version=dataset_version,
        )

    def build_streaming_key(
        self,
        ctx,
        raw_query: str,
        phase: int,
        dataset_version: str = None,
    ) -> str:
        """
        Build cache key for streaming search.

        Args:
            ctx: ActionContext
            raw_query: Raw query (will be normalized and hashed)
            phase: Phase number (1 or 2)
            dataset_version: Optional version

        Returns:
            Cache key string
        """
        return build_streaming_cache_key(
            endpoint="search.stream",
            ctx=ctx,
            phase=phase,
            raw_query=raw_query,
            dataset_version=dataset_version,
        )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ctx,
        ttl: int = None,
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ctx: ActionContext (for indexing)
            ttl: TTL in seconds (default CACHE_TTL_SEARCH)
        """
        await self._store.set(
            key=key,
            value=value,
            ttl=ttl or CACHE_TTL_SEARCH,
            yacht_id=getattr(ctx, 'yacht_id', ''),
            user_id=getattr(ctx, 'user_id', ''),
            role=getattr(ctx, 'role', ''),
        )

    async def delete(self, key: str) -> bool:
        """Delete a single key."""
        return await self._store.delete(key)

    async def clear_for_user(self, user_id: str, yacht_id: str = None) -> int:
        """
        Clear cache for user (on role change or revocation).

        MUST be called when:
        - User's role changes
        - User's membership is revoked
        - User is suspended

        Args:
            user_id: User UUID
            yacht_id: Optional yacht UUID (if None, clears for all yachts)

        Returns:
            Number of entries cleared
        """
        return await self._store.clear_for_user(user_id, yacht_id)

    async def clear_for_yacht(self, yacht_id: str) -> int:
        """
        Clear all cache for a yacht.

        MUST be called when:
        - Yacht is frozen
        - Yacht enters incident mode
        - Bulk data changes on yacht

        Args:
            yacht_id: Yacht UUID

        Returns:
            Number of entries cleared
        """
        return await self._store.clear_for_yacht(yacht_id)

    async def clear_all(self) -> int:
        """Clear entire cache (for global incident mode)."""
        return await self._store.clear_all()

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self._store.get_stats()

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        return await self._store.cleanup_expired()


# ============================================================================
# Singleton Instance
# ============================================================================

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the singleton cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# ============================================================================
# Convenience Functions
# ============================================================================

async def clear_cache_for_user(user_id: str, yacht_id: str = None) -> int:
    """
    Clear cache for user (convenience function).

    Call this when:
    - User's role changes (change_role)
    - User's membership is revoked (revoke_membership)
    - User is suspended
    """
    return await get_cache_service().clear_for_user(user_id, yacht_id)


async def clear_cache_for_yacht(yacht_id: str) -> int:
    """
    Clear cache for yacht (convenience function).

    Call this when:
    - Yacht is frozen (freeze_yacht)
    - Yacht enters incident mode
    - Bulk data changes
    """
    return await get_cache_service().clear_for_yacht(yacht_id)


async def clear_all_cache() -> int:
    """
    Clear entire cache (convenience function).

    Call this when:
    - Global incident mode activated
    - Emergency cache flush
    """
    return await get_cache_service().clear_all()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Configuration
    "CACHE_MAX_TTL",
    "CACHE_TTL_SEARCH",
    "CACHE_TTL_STREAMING_P1",
    "CACHE_TTL_STREAMING_P2",
    "CACHE_TTL_BOOTSTRAP",
    # Classes
    "CacheEntry",
    "InMemoryCacheStore",
    "CacheService",
    # Singleton
    "get_cache_service",
    # Convenience functions
    "clear_cache_for_user",
    "clear_cache_for_yacht",
    "clear_all_cache",
]
