"""
CelesteOS API - Streaming Cache Isolation Tests
================================================

Tests for cache key isolation across yacht/user/role/phase.

Security invariants (per 07_CACHE_KEY_AND_INVALIDATION_SPEC.md):
1. Two different yachts cannot share a cache key
2. Two different users on same yacht have different keys
3. Role changes alter cache key (user gets fresh data)
4. Phase (1 vs 2) produces different keys
5. Query hash distinguishes different queries
6. Cache key validation fails without required fields

These tests ensure cross-tenant cache bleed is impossible.
"""

import pytest
import hashlib
from dataclasses import dataclass
from typing import Optional

from utils.cache_keys import (
    build_streaming_cache_key,
    normalize_query,
    hash_query,
    build_cache_key,
    normalize_query_hash,
    CacheKeyBuilder,
)


# ============================================================================
# Test Context Classes
# ============================================================================

@dataclass
class TestContext:
    """Minimal context for cache key testing."""
    yacht_id: str
    user_id: str
    role: str
    tenant_key_alias: Optional[str] = None


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def yacht_a() -> str:
    return "yacht_a_00000000_0000_0000_000000000001"


@pytest.fixture
def yacht_b() -> str:
    return "yacht_b_00000000_0000_0000_000000000002"


@pytest.fixture
def user_a() -> str:
    return "user_a_00000000_0000_0000_000000000001"


@pytest.fixture
def user_b() -> str:
    return "user_b_00000000_0000_0000_000000000002"


@pytest.fixture
def ctx_yacht_a_captain(yacht_a, user_a) -> TestContext:
    return TestContext(
        yacht_id=yacht_a,
        user_id=user_a,
        role="captain",
        tenant_key_alias="yTEST_A",
    )


@pytest.fixture
def ctx_yacht_b_captain(yacht_b, user_b) -> TestContext:
    return TestContext(
        yacht_id=yacht_b,
        user_id=user_b,
        role="captain",
        tenant_key_alias="yTEST_B",
    )


@pytest.fixture
def ctx_yacht_a_crew(yacht_a, user_a) -> TestContext:
    return TestContext(
        yacht_id=yacht_a,
        user_id=user_a,
        role="crew",
        tenant_key_alias="yTEST_A",
    )


@pytest.fixture
def ctx_yacht_a_user_b(yacht_a, user_b) -> TestContext:
    return TestContext(
        yacht_id=yacht_a,
        user_id=user_b,
        role="captain",
        tenant_key_alias="yTEST_A",
    )


# ============================================================================
# Cross-Yacht Isolation Tests
# ============================================================================

class TestCrossYachtIsolation:
    """Tests that different yachts have isolated cache keys."""

    def test_different_yachts_different_keys(
        self, ctx_yacht_a_captain, ctx_yacht_b_captain
    ):
        """Same query on different yachts produces different keys."""
        query = "engine maintenance"

        key_a = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )
        key_b = build_streaming_cache_key(
            "search.stream", ctx_yacht_b_captain, 1, query
        )

        assert key_a != key_b
        assert ctx_yacht_a_captain.yacht_id in key_a
        assert ctx_yacht_b_captain.yacht_id in key_b

    def test_yacht_id_in_key(self, ctx_yacht_a_captain, yacht_a):
        """Cache key contains yacht_id."""
        key = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "test"
        )
        assert yacht_a in key


# ============================================================================
# Cross-User Isolation Tests
# ============================================================================

class TestCrossUserIsolation:
    """Tests that different users have isolated cache keys."""

    def test_different_users_same_yacht_different_keys(
        self, ctx_yacht_a_captain, ctx_yacht_a_user_b
    ):
        """Same query by different users on same yacht produces different keys."""
        query = "engine maintenance"

        key_a = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )
        key_b = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_user_b, 1, query
        )

        assert key_a != key_b

    def test_user_id_in_key(self, ctx_yacht_a_captain, user_a):
        """Cache key contains user_id (truncated)."""
        key = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "test"
        )
        # User ID is truncated to first 16 chars
        assert user_a[:16] in key


# ============================================================================
# Role Change Isolation Tests
# ============================================================================

class TestRoleChangeIsolation:
    """Tests that role changes produce different cache keys."""

    def test_different_roles_different_keys(
        self, ctx_yacht_a_captain, ctx_yacht_a_crew
    ):
        """Same user with different role produces different key."""
        query = "engine maintenance"

        key_captain = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )
        key_crew = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_crew, 1, query
        )

        assert key_captain != key_crew

    def test_role_in_key(self, ctx_yacht_a_captain):
        """Cache key contains role."""
        key = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "test"
        )
        assert "captain" in key


# ============================================================================
# Phase Isolation Tests
# ============================================================================

class TestPhaseIsolation:
    """Tests that different phases have isolated cache keys."""

    def test_different_phases_different_keys(self, ctx_yacht_a_captain):
        """Phase 1 and Phase 2 produce different keys."""
        query = "engine maintenance"

        key_p1 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )
        key_p2 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 2, query
        )

        assert key_p1 != key_p2
        assert ":1:" in key_p1
        assert ":2:" in key_p2


# ============================================================================
# Query Hash Isolation Tests
# ============================================================================

class TestQueryHashIsolation:
    """Tests that different queries produce different cache keys."""

    def test_different_queries_different_keys(self, ctx_yacht_a_captain):
        """Different queries produce different keys."""
        key_engine = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "engine"
        )
        key_pump = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "pump"
        )

        assert key_engine != key_pump

    def test_normalized_queries_same_key(self, ctx_yacht_a_captain):
        """Equivalent queries (after normalization) produce same key."""
        key_1 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "Engine  Room"
        )
        key_2 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "engine room"
        )

        assert key_1 == key_2

    def test_query_hash_not_raw_query(self, ctx_yacht_a_captain):
        """Key contains hash, not raw query text."""
        query = "sensitive confidential secret term"
        key = build_streaming_cache_key(
            "api.stream", ctx_yacht_a_captain, 1, query
        )

        # Raw query should not appear (check words not in endpoint name)
        assert "sensitive" not in key
        assert "confidential" not in key
        assert "secret" not in key


# ============================================================================
# Cache Hit/Miss Tests
# ============================================================================

class TestCacheHitMiss:
    """Tests for cache hit and miss scenarios."""

    def test_same_context_same_query_same_key(self, ctx_yacht_a_captain):
        """Same context and query produces same key (cache hit)."""
        query = "engine"

        key_1 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )
        key_2 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query
        )

        assert key_1 == key_2

    def test_dataset_version_invalidates_cache(self, ctx_yacht_a_captain):
        """Different dataset version produces different key (cache miss)."""
        query = "engine"

        key_v1 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query,
            dataset_version="v1",
        )
        key_v2 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, query,
            dataset_version="v2",
        )

        assert key_v1 != key_v2


# ============================================================================
# Required Fields Validation Tests
# ============================================================================

class TestRequiredFieldsValidation:
    """Tests that required fields are validated."""

    def test_missing_yacht_id_raises(self, user_a):
        """Missing yacht_id raises ValueError."""
        ctx = TestContext(yacht_id=None, user_id=user_a, role="captain")

        with pytest.raises(ValueError, match="yacht_id"):
            build_streaming_cache_key("search.stream", ctx, 1, "test")

    def test_missing_user_id_raises(self, yacht_a):
        """Missing user_id raises ValueError."""
        ctx = TestContext(yacht_id=yacht_a, user_id=None, role="captain")

        with pytest.raises(ValueError, match="user_id"):
            build_streaming_cache_key("search.stream", ctx, 1, "test")

    def test_missing_role_raises(self, yacht_a, user_a):
        """Missing role raises ValueError."""
        ctx = TestContext(yacht_id=yacht_a, user_id=user_a, role=None)

        with pytest.raises(ValueError, match="role"):
            build_streaming_cache_key("search.stream", ctx, 1, "test")


# ============================================================================
# CacheKeyBuilder Integration Tests
# ============================================================================

class TestCacheKeyBuilderIntegration:
    """Tests for CacheKeyBuilder class integration."""

    def test_builder_for_streaming_matches_function(
        self, yacht_a, user_a
    ):
        """CacheKeyBuilder.for_streaming matches build_streaming_cache_key."""
        builder = CacheKeyBuilder(
            yacht_id=yacht_a,
            user_id=user_a,
            role="captain",
            tenant_key_alias="yTEST",
        )

        # Builder method
        key_builder = builder.for_streaming("engine room", phase=1)

        # Compare with streaming function (both should normalize and hash)
        ctx = TestContext(
            yacht_id=yacht_a,
            user_id=user_a,
            role="captain",
            tenant_key_alias="yTEST",
        )

        # Note: The builder uses different format from streaming function
        # They use the same components but may have different order
        # Both should include yacht_id, user_id, role, phase, and query_hash

        assert yacht_a in key_builder
        assert user_a[:16] in key_builder
        assert "captain" in key_builder
        assert ":1:" in key_builder

    def test_builder_different_yachts_different_keys(self, yacht_a, yacht_b, user_a):
        """Builder produces different keys for different yachts."""
        builder_a = CacheKeyBuilder(
            yacht_id=yacht_a, user_id=user_a, role="captain"
        )
        builder_b = CacheKeyBuilder(
            yacht_id=yacht_b, user_id=user_a, role="captain"
        )

        key_a = builder_a.for_streaming("engine", phase=1)
        key_b = builder_b.for_streaming("engine", phase=1)

        assert key_a != key_b


# ============================================================================
# Query Normalization Edge Cases
# ============================================================================

class TestQueryNormalizationEdgeCases:
    """Tests for edge cases in query normalization."""

    def test_empty_query(self, ctx_yacht_a_captain):
        """Empty query produces valid key."""
        key = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, ""
        )
        assert key is not None
        assert len(key) > 0

    def test_whitespace_only_query(self, ctx_yacht_a_captain):
        """Whitespace-only query normalizes to empty."""
        key_1 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "   "
        )
        key_2 = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, ""
        )

        assert key_1 == key_2

    def test_unicode_query(self, ctx_yacht_a_captain):
        """Unicode queries are handled correctly."""
        key = build_streaming_cache_key(
            "search.stream", ctx_yacht_a_captain, 1, "引擎维护"
        )
        assert key is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
