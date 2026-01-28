"""
CelesteOS API - Cache Key Tests
================================

Tests for utils/cache_keys.py

Security invariants tested:
1. Keys MUST include yacht_id, user_id, role (no exceptions)
2. Different yachts get different cache keys
3. Different roles get different cache keys
4. Role changes alter cache key
5. TTL rules are enforced
"""

import pytest
from unittest.mock import MagicMock
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


class TestBuildCacheKey:
    """Test build_cache_key function."""

    def test_includes_all_required_fields(self):
        """Cache key must include yacht_id, user_id, role."""
        from utils.cache_keys import build_cache_key

        key = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123-uuid",
            user_id="user-456-uuid",
            role="captain",
            query_hash="abc123",
        )

        assert "yacht-123-uuid" in key
        assert "user-456" in key  # truncated to 16 chars
        assert "captain" in key
        assert "search" in key

    def test_missing_yacht_id_raises(self):
        """Missing yacht_id must raise ValueError."""
        from utils.cache_keys import build_cache_key

        with pytest.raises(ValueError, match="yacht_id is required"):
            build_cache_key(
                endpoint="search",
                yacht_id=None,
                user_id="user-123",
                role="captain",
                query_hash="abc",
            )

    def test_missing_user_id_raises(self):
        """Missing user_id must raise ValueError."""
        from utils.cache_keys import build_cache_key

        with pytest.raises(ValueError, match="user_id is required"):
            build_cache_key(
                endpoint="search",
                yacht_id="yacht-123",
                user_id=None,
                role="captain",
                query_hash="abc",
            )

    def test_missing_role_raises(self):
        """Missing role must raise ValueError."""
        from utils.cache_keys import build_cache_key

        with pytest.raises(ValueError, match="role is required"):
            build_cache_key(
                endpoint="search",
                yacht_id="yacht-123",
                user_id="user-123",
                role=None,
                query_hash="abc",
            )

    def test_missing_endpoint_raises(self):
        """Missing endpoint must raise ValueError."""
        from utils.cache_keys import build_cache_key

        with pytest.raises(ValueError, match="endpoint is required"):
            build_cache_key(
                endpoint=None,
                yacht_id="yacht-123",
                user_id="user-123",
                role="captain",
                query_hash="abc",
            )

    def test_different_yachts_different_keys(self):
        """Different yacht_ids must produce different keys."""
        from utils.cache_keys import build_cache_key

        key1 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-AAA",
            user_id="user-123",
            role="captain",
            query_hash="abc",
        )

        key2 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-BBB",
            user_id="user-123",
            role="captain",
            query_hash="abc",
        )

        assert key1 != key2

    def test_different_roles_different_keys(self):
        """Different roles must produce different keys."""
        from utils.cache_keys import build_cache_key

        key_captain = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-123",
            role="captain",
            query_hash="abc",
        )

        key_crew = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-123",
            role="crew",
            query_hash="abc",
        )

        assert key_captain != key_crew

    def test_different_users_different_keys(self):
        """Different users must produce different keys."""
        from utils.cache_keys import build_cache_key

        key1 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-AAA-123456789",
            role="captain",
            query_hash="abc",
        )

        key2 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-BBB-123456789",
            role="captain",
            query_hash="abc",
        )

        assert key1 != key2

    def test_includes_phase(self):
        """Cache key must include phase for streaming."""
        from utils.cache_keys import build_cache_key

        key_phase1 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-123",
            role="captain",
            query_hash="abc",
            phase=1,
        )

        key_phase2 = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-123",
            role="captain",
            query_hash="abc",
            phase=2,
        )

        assert key_phase1 != key_phase2
        assert ":1:" in key_phase1
        assert ":2:" in key_phase2

    def test_includes_version_prefix(self):
        """Cache key must include version prefix."""
        from utils.cache_keys import build_cache_key, CACHE_KEY_VERSION

        key = build_cache_key(
            endpoint="search",
            yacht_id="yacht-123",
            user_id="user-123",
            role="captain",
            query_hash="abc",
        )

        assert key.startswith(CACHE_KEY_VERSION + ":")


class TestNormalizeQueryHash:
    """Test normalize_query_hash function."""

    def test_normalizes_case(self):
        """Query hash should be case-insensitive."""
        from utils.cache_keys import normalize_query_hash

        hash1 = normalize_query_hash("Hello World")
        hash2 = normalize_query_hash("hello world")

        assert hash1 == hash2

    def test_normalizes_whitespace(self):
        """Query hash should normalize whitespace."""
        from utils.cache_keys import normalize_query_hash

        hash1 = normalize_query_hash("hello world")
        hash2 = normalize_query_hash("hello    world")
        hash3 = normalize_query_hash("  hello world  ")

        assert hash1 == hash2
        assert hash2 == hash3

    def test_empty_query_returns_empty(self):
        """Empty query should return 'empty'."""
        from utils.cache_keys import normalize_query_hash

        assert normalize_query_hash("") == "empty"
        assert normalize_query_hash(None) == "empty"


class TestCacheKeyBuilder:
    """Test CacheKeyBuilder class."""

    def test_requires_all_context(self):
        """Builder requires yacht_id, user_id, role."""
        from utils.cache_keys import CacheKeyBuilder

        with pytest.raises(ValueError):
            CacheKeyBuilder(yacht_id="yacht-123", user_id="user-123", role=None)

        with pytest.raises(ValueError):
            CacheKeyBuilder(yacht_id="yacht-123", user_id=None, role="captain")

        with pytest.raises(ValueError):
            CacheKeyBuilder(yacht_id=None, user_id="user-123", role="captain")

    def test_for_search(self):
        """Builder creates search keys correctly."""
        from utils.cache_keys import CacheKeyBuilder

        builder = CacheKeyBuilder(
            yacht_id="yacht-123",
            user_id="user-456",
            role="captain",
        )

        key = builder.for_search("test query", phase=1)

        assert "yacht-123" in key
        assert "captain" in key
        assert "search" in key

    def test_for_streaming(self):
        """Builder creates streaming keys correctly."""
        from utils.cache_keys import CacheKeyBuilder

        builder = CacheKeyBuilder(
            yacht_id="yacht-123",
            user_id="user-456",
            role="captain",
        )

        key = builder.for_streaming("test query", phase=2)

        assert "streaming_phase_2" in key
        assert ":2:" in key

    def test_for_suggestions(self):
        """Builder creates suggestion keys correctly."""
        from utils.cache_keys import CacheKeyBuilder

        builder = CacheKeyBuilder(
            yacht_id="yacht-123",
            user_id="user-456",
            role="captain",
        )

        key = builder.for_suggestions(domain="faults", entity_type="fault")

        assert "suggestions" in key


class TestActionContextIntegration:
    """Test ActionContext integration with cache keys."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock ActionContext."""
        from middleware.action_security import ActionContext

        return ActionContext(
            user_id="user-123-uuid-456789",
            yacht_id="yacht-abc-uuid-123456",
            role="chief_engineer",
            tenant_key_alias="test_yacht",
        )

    def test_build_cache_key_from_ctx(self, mock_ctx):
        """build_cache_key_from_ctx uses ctx fields."""
        from utils.cache_keys import build_cache_key_from_ctx, normalize_query_hash

        key = build_cache_key_from_ctx(
            ctx=mock_ctx,
            endpoint="search",
            query_hash=normalize_query_hash("test query"),
            phase=1,
        )

        assert mock_ctx.yacht_id in key
        assert mock_ctx.role in key
        assert "search" in key

    def test_builder_from_ctx(self, mock_ctx):
        """builder_from_ctx creates builder with ctx fields."""
        from utils.cache_keys import builder_from_ctx

        builder = builder_from_ctx(mock_ctx)

        assert builder.yacht_id == mock_ctx.yacht_id
        assert builder.user_id == mock_ctx.user_id
        assert builder.role == mock_ctx.role

    def test_ctx_integration_different_yachts(self, mock_ctx):
        """Different yacht contexts produce different keys."""
        from utils.cache_keys import build_cache_key_from_ctx
        from middleware.action_security import ActionContext

        ctx2 = ActionContext(
            user_id=mock_ctx.user_id,
            yacht_id="other-yacht-uuid",
            role=mock_ctx.role,
            tenant_key_alias="other_yacht",
        )

        key1 = build_cache_key_from_ctx(
            ctx=mock_ctx,
            endpoint="search",
            query_hash="abc",
        )

        key2 = build_cache_key_from_ctx(
            ctx=ctx2,
            endpoint="search",
            query_hash="abc",
        )

        assert key1 != key2

    def test_ctx_integration_role_change(self, mock_ctx):
        """Role change produces different cache key."""
        from utils.cache_keys import build_cache_key_from_ctx
        from middleware.action_security import ActionContext

        ctx_captain = ActionContext(
            user_id=mock_ctx.user_id,
            yacht_id=mock_ctx.yacht_id,
            role="captain",
            tenant_key_alias=mock_ctx.tenant_key_alias,
        )

        ctx_crew = ActionContext(
            user_id=mock_ctx.user_id,
            yacht_id=mock_ctx.yacht_id,
            role="crew",
            tenant_key_alias=mock_ctx.tenant_key_alias,
        )

        key_captain = build_cache_key_from_ctx(
            ctx=ctx_captain,
            endpoint="search",
            query_hash="abc",
        )

        key_crew = build_cache_key_from_ctx(
            ctx=ctx_crew,
            endpoint="search",
            query_hash="abc",
        )

        assert key_captain != key_crew


class TestTTLRules:
    """Test TTL rules for different endpoint types."""

    def test_streaming_phase_1_ttl(self):
        """Streaming phase 1 has longer TTL."""
        from utils.cache_keys import get_ttl_for_endpoint

        ttl = get_ttl_for_endpoint("streaming_phase_1")
        assert ttl == 120

    def test_streaming_phase_2_ttl(self):
        """Streaming phase 2 has shorter TTL (more sensitive)."""
        from utils.cache_keys import get_ttl_for_endpoint

        ttl = get_ttl_for_endpoint("streaming_phase_2")
        assert ttl == 30
        assert ttl < get_ttl_for_endpoint("streaming_phase_1")

    def test_signed_url_never_cached(self):
        """Signed URLs should never be cached."""
        from utils.cache_keys import get_ttl_for_endpoint

        ttl = get_ttl_for_endpoint("signed_url")
        assert ttl == 0

    def test_default_ttl(self):
        """Unknown endpoints get default TTL."""
        from utils.cache_keys import get_ttl_for_endpoint

        ttl = get_ttl_for_endpoint("unknown_endpoint")
        assert ttl == 60


class TestInvalidationPatterns:
    """Test cache invalidation patterns."""

    def test_invalidation_pattern_for_user(self):
        """User invalidation pattern includes user_id (truncated to 16 chars)."""
        from utils.cache_keys import invalidation_pattern_for_user

        pattern = invalidation_pattern_for_user("user-123-uuid-456789")

        # user_id is truncated to 16 chars: "user-123-uuid-45"
        assert "user-123-uuid-45" in pattern
        assert pattern.startswith("*:")
        assert pattern.endswith(":*")

    def test_invalidation_pattern_for_yacht(self):
        """Yacht invalidation pattern includes yacht_id."""
        from utils.cache_keys import invalidation_pattern_for_yacht

        pattern = invalidation_pattern_for_yacht("yacht-abc-123")

        assert "yacht-abc-123" in pattern
        assert pattern.startswith("*:")
        assert pattern.endswith(":*")

    def test_invalidation_pattern_for_endpoint(self):
        """Endpoint invalidation pattern includes endpoint."""
        from utils.cache_keys import invalidation_pattern_for_endpoint

        pattern = invalidation_pattern_for_endpoint("search")

        assert "search" in pattern


class TestCrossYachtCacheIsolation:
    """Test that cache keys enforce yacht isolation."""

    def test_same_query_different_yachts_different_keys(self):
        """Same query on different yachts gets different cache keys."""
        from utils.cache_keys import build_cache_key, normalize_query_hash

        query = "engine maintenance"
        query_hash = normalize_query_hash(query)

        key_yacht_a = build_cache_key(
            endpoint="search",
            yacht_id="yacht-aurora",
            user_id="user-123",
            role="captain",
            query_hash=query_hash,
        )

        key_yacht_b = build_cache_key(
            endpoint="search",
            yacht_id="yacht-borealis",
            user_id="user-123",
            role="captain",
            query_hash=query_hash,
        )

        # Keys must be different to prevent cross-tenant cache bleed
        assert key_yacht_a != key_yacht_b

        # Verify yacht_id is actually in the key
        assert "yacht-aurora" in key_yacht_a
        assert "yacht-borealis" in key_yacht_b
        assert "yacht-aurora" not in key_yacht_b
        assert "yacht-borealis" not in key_yacht_a


# Run with: pytest tests/test_cache_keys.py -v
