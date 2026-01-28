"""
CelesteOS API - Canonical Cache Key Builder
===========================================

Builds cache keys per 07_CACHE_KEY_AND_INVALIDATION_SPEC.md

Security invariants:
1. Keys MUST include yacht_id, user_id, role (no exceptions)
2. Keys are scoped to prevent cross-tenant cache bleed
3. Role changes alter cache key (user gets fresh data)
4. Phase is included for streaming search (phase 1 vs phase 2)
5. TTL rules enforced at cache layer, not in key

Key format:
    v1:{tenant}:{yacht_id}:{user_id}:{role}:{endpoint}:{phase}:{query_hash}:{version}

Example:
    v1:y85fe1119:85fe1119-b04c-41ac-80f1-829d23322598:abc123:chief_engineer:search:1:sha256abc:1

Usage:
    from utils.cache_keys import build_cache_key, CacheKeyBuilder

    # Simple function
    key = build_cache_key(
        endpoint="search",
        yacht_id=ctx.yacht_id,
        user_id=ctx.user_id,
        role=ctx.role,
        query_hash=hash_query(query),
        phase=1,
    )

    # Builder pattern (for complex scenarios)
    builder = CacheKeyBuilder(ctx)
    key = builder.for_search(query, phase=1)
    key = builder.for_suggestions(domain="faults")
"""

from typing import Optional, Any, Dict
from dataclasses import dataclass
import hashlib
import json
import re

# Cache key version - increment when format changes
CACHE_KEY_VERSION = "v1"

# Maximum TTLs by endpoint type (in seconds)
# Enforced at cache layer, documented here for reference
TTL_RULES = {
    "streaming_phase_1": 120,    # 30-120s - counts/categories only
    "streaming_phase_2": 30,     # 10-30s - detailed results (shorter, more sensitive)
    "search": 120,               # 30-120s
    "suggestions": 60,           # Action suggestions
    "bootstrap": 300,            # User context (cleared on role change)
    "signed_url": 0,             # Never cache signed URLs beyond their lifetime
}


@dataclass
class CacheContext:
    """Context required for building cache keys."""
    yacht_id: str
    user_id: str
    role: str
    tenant_key_alias: Optional[str] = None


def normalize_query_hash(query: str, max_length: int = 32) -> str:
    """
    Normalize and hash query string for cache key.

    Normalization:
    - Lowercase
    - Strip whitespace
    - Remove special characters
    - SHA256 hash

    Args:
        query: Raw query string
        max_length: Max hash length (default 32)

    Returns:
        Normalized hash string
    """
    if not query:
        return "empty"

    # Normalize
    normalized = query.lower().strip()
    # Remove multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    # Hash
    hash_value = hashlib.sha256(normalized.encode()).hexdigest()
    return hash_value[:max_length]


def build_cache_key(
    endpoint: str,
    yacht_id: str,
    user_id: str,
    role: str,
    query_hash: str,
    phase: int = 1,
    tenant_key_alias: Optional[str] = None,
    dataset_version: Optional[str] = None,
) -> str:
    """
    Build canonical cache key per spec.

    All parameters except dataset_version are REQUIRED.
    Missing yacht_id, user_id, or role will raise ValueError.

    Args:
        endpoint: API endpoint name (e.g., "search", "suggestions")
        yacht_id: Yacht UUID (from ctx.yacht_id)
        user_id: User UUID (from ctx.user_id)
        role: User role (from ctx.role)
        query_hash: Hashed query string
        phase: Streaming phase (1=counts, 2=details)
        tenant_key_alias: Tenant alias (optional, derived from yacht_id if not provided)
        dataset_version: Dataset version for cache busting (optional)

    Returns:
        Cache key string

    Raises:
        ValueError: Missing required parameter
    """
    # Validate required fields
    if not yacht_id:
        raise ValueError("yacht_id is required for cache key")
    if not user_id:
        raise ValueError("user_id is required for cache key")
    if not role:
        raise ValueError("role is required for cache key")
    if not endpoint:
        raise ValueError("endpoint is required for cache key")

    # Derive tenant alias if not provided
    tenant = tenant_key_alias or f"y{yacht_id[:8]}"

    # Build key components
    components = [
        CACHE_KEY_VERSION,
        tenant,
        yacht_id,
        user_id[:16],  # Truncate user_id for key length
        role,
        endpoint,
        str(phase),
        query_hash or "none",
    ]

    # Add optional dataset version
    if dataset_version:
        components.append(dataset_version)

    return ":".join(components)


class CacheKeyBuilder:
    """
    Builder for creating cache keys with consistent context.

    Use when creating multiple keys for the same request context.
    """

    def __init__(
        self,
        ctx: Optional[CacheContext] = None,
        yacht_id: str = None,
        user_id: str = None,
        role: str = None,
        tenant_key_alias: str = None,
    ):
        """
        Initialize builder with context.

        Can pass CacheContext object or individual parameters.
        """
        if ctx:
            self.yacht_id = ctx.yacht_id
            self.user_id = ctx.user_id
            self.role = ctx.role
            self.tenant_key_alias = ctx.tenant_key_alias
        else:
            self.yacht_id = yacht_id
            self.user_id = user_id
            self.role = role
            self.tenant_key_alias = tenant_key_alias

        # Validate
        if not self.yacht_id or not self.user_id or not self.role:
            raise ValueError("yacht_id, user_id, and role are required")

    def for_search(
        self,
        query: str,
        phase: int = 1,
        dataset_version: str = None,
    ) -> str:
        """Build cache key for search endpoint."""
        return build_cache_key(
            endpoint="search",
            yacht_id=self.yacht_id,
            user_id=self.user_id,
            role=self.role,
            query_hash=normalize_query_hash(query),
            phase=phase,
            tenant_key_alias=self.tenant_key_alias,
            dataset_version=dataset_version,
        )

    def for_streaming(
        self,
        query: str,
        phase: int,
        dataset_version: str = None,
    ) -> str:
        """Build cache key for streaming search endpoint."""
        endpoint = f"streaming_phase_{phase}"
        return build_cache_key(
            endpoint=endpoint,
            yacht_id=self.yacht_id,
            user_id=self.user_id,
            role=self.role,
            query_hash=normalize_query_hash(query),
            phase=phase,
            tenant_key_alias=self.tenant_key_alias,
            dataset_version=dataset_version,
        )

    def for_suggestions(
        self,
        domain: str = None,
        entity_type: str = None,
        entity_id: str = None,
    ) -> str:
        """Build cache key for action suggestions."""
        # Include context in hash if provided
        context_parts = [domain or "", entity_type or "", entity_id or ""]
        context_hash = normalize_query_hash(":".join(context_parts))

        return build_cache_key(
            endpoint="suggestions",
            yacht_id=self.yacht_id,
            user_id=self.user_id,
            role=self.role,
            query_hash=context_hash,
            phase=1,
            tenant_key_alias=self.tenant_key_alias,
        )

    def for_bootstrap(self) -> str:
        """Build cache key for user bootstrap data."""
        return build_cache_key(
            endpoint="bootstrap",
            yacht_id=self.yacht_id,
            user_id=self.user_id,
            role=self.role,
            query_hash="ctx",
            phase=1,
            tenant_key_alias=self.tenant_key_alias,
        )

    def for_entity(
        self,
        entity_type: str,
        entity_id: str,
        operation: str = "read",
    ) -> str:
        """Build cache key for entity operations."""
        return build_cache_key(
            endpoint=f"{entity_type}_{operation}",
            yacht_id=self.yacht_id,
            user_id=self.user_id,
            role=self.role,
            query_hash=entity_id[:16],
            phase=1,
            tenant_key_alias=self.tenant_key_alias,
        )


# ============================================================================
# Cache Invalidation Helpers
# ============================================================================


def invalidation_pattern_for_user(user_id: str) -> str:
    """
    Get pattern for invalidating all cache keys for a user.

    Use when: user role changes, user logs out
    """
    return f"*:{user_id[:16]}:*"


def invalidation_pattern_for_yacht(yacht_id: str) -> str:
    """
    Get pattern for invalidating all cache keys for a yacht.

    Use when: yacht frozen, incident mode, bulk data change
    """
    return f"*:{yacht_id}:*"


def invalidation_pattern_for_endpoint(endpoint: str) -> str:
    """
    Get pattern for invalidating all cache keys for an endpoint.

    Use when: endpoint code changes, schema migration
    """
    return f"*:{endpoint}:*"


def get_ttl_for_endpoint(endpoint: str) -> int:
    """
    Get recommended TTL for endpoint type.

    Returns TTL in seconds.
    """
    # Check exact match
    if endpoint in TTL_RULES:
        return TTL_RULES[endpoint]

    # Check prefix match
    for key, ttl in TTL_RULES.items():
        if endpoint.startswith(key):
            return ttl

    # Default: 60 seconds
    return 60
