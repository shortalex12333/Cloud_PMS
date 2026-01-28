"""
CelesteOS API - Revocation Cache Invalidation Tests
====================================================

Tests for cache invalidation on role change and membership revocation.

Security invariants tested:
1. Role change clears user's cache entries
2. Membership revocation clears user's cache entries
3. Yacht freeze clears all cache entries for that yacht
4. Cache clear is bounded in time (TTL enforcement)
5. Cross-yacht cache entries are NOT affected by single yacht operations
6. Cache clear functions are called during admin operations
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
import asyncio

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_cache_store():
    """Mock in-memory cache store."""
    from services.cache import InMemoryCacheStore
    store = InMemoryCacheStore()
    return store


@pytest.fixture
def sample_cache_entries():
    """Sample cache entries for testing."""
    return {
        # User 1 on Yacht A
        "v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123": {"data": "cached1"},
        "v1:yYachtA:yacht-a:user-001:captain:search.stream:2:abc123": {"data": "cached2"},
        # User 2 on Yacht A
        "v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456": {"data": "cached3"},
        # User 1 on Yacht B (different yacht)
        "v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789": {"data": "cached4"},
        # User 3 on Yacht B
        "v1:yYachtB:yacht-b:user-003:captain:search.stream:1:jkl012": {"data": "cached5"},
    }


# ============================================================================
# CACHE SERVICE TESTS
# ============================================================================

class TestCacheService:
    """Test cache service functionality."""

    @pytest.mark.asyncio
    async def test_cache_get_set_basic(self, mock_cache_store):
        """Test basic cache get/set operations."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Set value
        await service.set("test-key", {"data": "value"}, ttl=60)

        # Get value
        result = await service.get("test-key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_clear_for_user_single_yacht(self, mock_cache_store, sample_cache_entries):
        """Test clearing cache for user on specific yacht."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate cache
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Verify all entries exist
        for key in sample_cache_entries:
            assert await service.get(key) is not None

        # Clear cache for user-001 on yacht-a only
        cleared = await service.clear_for_user("user-001", "yacht-a")

        # Should have cleared 2 entries (user-001 on yacht-a)
        assert cleared == 2

        # User-001's yacht-a entries should be gone
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:2:abc123") is None

        # User-001's yacht-b entry should still exist
        assert await service.get("v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789") is not None

        # Other users' entries should still exist
        assert await service.get("v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456") is not None

    @pytest.mark.asyncio
    async def test_cache_clear_for_user_all_yachts(self, mock_cache_store, sample_cache_entries):
        """Test clearing cache for user across all yachts."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Clear cache for user-001 on ALL yachts (no yacht_id)
        cleared = await service.clear_for_user("user-001", yacht_id=None)

        # Should have cleared 3 entries (all user-001)
        assert cleared == 3

        # All user-001 entries gone
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:2:abc123") is None
        assert await service.get("v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789") is None

        # Other users still exist
        assert await service.get("v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456") is not None
        assert await service.get("v1:yYachtB:yacht-b:user-003:captain:search.stream:1:jkl012") is not None

    @pytest.mark.asyncio
    async def test_cache_clear_for_yacht(self, mock_cache_store, sample_cache_entries):
        """Test clearing all cache entries for a yacht."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Clear cache for yacht-a
        cleared = await service.clear_for_yacht("yacht-a")

        # Should have cleared 3 entries (all yacht-a entries)
        assert cleared == 3

        # All yacht-a entries gone
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:2:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456") is None

        # Yacht-b entries still exist
        assert await service.get("v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789") is not None
        assert await service.get("v1:yYachtB:yacht-b:user-003:captain:search.stream:1:jkl012") is not None


# ============================================================================
# ROLE CHANGE CACHE INVALIDATION TESTS
# ============================================================================

class TestRoleChangeCacheInvalidation:
    """Test cache invalidation on role change."""

    @pytest.mark.asyncio
    async def test_role_change_triggers_cache_clear(self):
        """Test that role change triggers cache clear for user."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import ActionContext

        mock_master = MagicMock()
        mock_tenant = MagicMock()
        mock_tenant.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"role": "crew"}])

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        ctx = ActionContext(
            user_id="admin-001",
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
            idempotency_key="idem-001",
        )

        with patch('handlers.secure_admin_handlers.clear_tenant_cache') as mock_clear_tenant:
            with patch('handlers.secure_admin_handlers.clear_cache_for_user', new_callable=AsyncMock) as mock_clear_cache:
                with patch('handlers.secure_admin_handlers.asyncio.create_task') as mock_task:
                    result = await handlers["admin_change_role"](
                        ctx,
                        target_user_id="user-target-001",
                        new_role="chief_engineer",
                    )

                    # Verify tenant cache was cleared
                    mock_clear_tenant.assert_called_once_with("user-target-001")

                    # Verify cache clear was scheduled
                    assert mock_task.called

                    # Verify result indicates cache cleared
                    assert result.get("cache_cleared") is True

    @pytest.mark.asyncio
    async def test_role_change_cache_key_affected(self, mock_cache_store, sample_cache_entries):
        """Test that role change makes old cache keys invalid."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate with user's captain role cache
        old_key = "v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123"
        await service.set(old_key, {"data": "old_captain_data"}, ttl=3600)

        # Simulate role change by clearing user's cache
        await service.clear_for_user("user-001", "yacht-a")

        # Old cache key should be gone
        assert await service.get(old_key) is None

        # New cache key with new role would be different
        new_key = "v1:yYachtA:yacht-a:user-001:chief_engineer:search.stream:1:abc123"
        # This would be a cache miss (no existing entry with new role)
        assert await service.get(new_key) is None


# ============================================================================
# REVOCATION CACHE INVALIDATION TESTS
# ============================================================================

class TestRevocationCacheInvalidation:
    """Test cache invalidation on membership revocation."""

    @pytest.mark.asyncio
    async def test_revocation_triggers_cache_clear(self):
        """Test that membership revocation triggers cache clear."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import ActionContext

        mock_master = MagicMock()
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        ctx = ActionContext(
            user_id="admin-001",
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
            idempotency_key="idem-002",
        )

        with patch('handlers.secure_admin_handlers.clear_tenant_cache') as mock_clear_tenant:
            with patch('handlers.secure_admin_handlers.clear_cache_for_user', new_callable=AsyncMock) as mock_clear_cache:
                with patch('handlers.secure_admin_handlers.asyncio.create_task') as mock_task:
                    result = await handlers["admin_revoke_membership"](
                        ctx,
                        target_user_id="user-target-002",
                        reason="Policy violation",
                    )

                    # Verify tenant cache was cleared
                    mock_clear_tenant.assert_called_once_with("user-target-002")

                    # Verify cache clear was scheduled
                    assert mock_task.called

                    # Verify result indicates cache cleared
                    assert result.get("cache_cleared") is True

    @pytest.mark.asyncio
    async def test_revoked_user_cache_completely_cleared(self, mock_cache_store, sample_cache_entries):
        """Test that revoked user's cache is completely cleared."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate with user's entries
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Simulate revocation by clearing all user-002's cache on yacht-a
        cleared = await service.clear_for_user("user-002", "yacht-a")

        assert cleared == 1  # user-002 only has 1 entry on yacht-a

        # user-002's entry should be gone
        assert await service.get("v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456") is None

        # Other users unaffected
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123") is not None


# ============================================================================
# YACHT FREEZE CACHE INVALIDATION TESTS
# ============================================================================

class TestYachtFreezeCacheInvalidation:
    """Test cache invalidation on yacht freeze."""

    @pytest.mark.asyncio
    async def test_yacht_freeze_triggers_cache_clear(self):
        """Test that yacht freeze triggers cache clear for entire yacht."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import ActionContext

        mock_master = MagicMock()
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        ctx = ActionContext(
            user_id="admin-001",
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
            idempotency_key="idem-003",
        )

        with patch('handlers.secure_admin_handlers.clear_cache_for_yacht', new_callable=AsyncMock) as mock_clear:
            with patch('handlers.secure_admin_handlers.asyncio.create_task') as mock_task:
                result = await handlers["admin_freeze_yacht"](
                    ctx,
                    freeze=True,
                    reason="Security investigation",
                )

                # Verify yacht cache clear was scheduled
                assert mock_task.called

    @pytest.mark.asyncio
    async def test_yacht_freeze_clears_all_yacht_entries(self, mock_cache_store, sample_cache_entries):
        """Test that yacht freeze clears all entries for that yacht."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Simulate yacht freeze by clearing all yacht-a cache
        cleared = await service.clear_for_yacht("yacht-a")

        assert cleared == 3  # All 3 yacht-a entries

        # All yacht-a entries gone (both users)
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-001:captain:search.stream:2:abc123") is None
        assert await service.get("v1:yYachtA:yacht-a:user-002:crew:search.stream:1:def456") is None

        # Yacht-b unaffected (cross-yacht isolation)
        assert await service.get("v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789") is not None


# ============================================================================
# CROSS-YACHT ISOLATION TESTS
# ============================================================================

class TestCrossYachtCacheIsolation:
    """Test that cache operations don't affect other yachts."""

    @pytest.mark.asyncio
    async def test_user_clear_respects_yacht_boundary(self, mock_cache_store, sample_cache_entries):
        """Test that clearing user cache respects yacht boundaries."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Clear user-001 on yacht-a only
        await service.clear_for_user("user-001", "yacht-a")

        # user-001 on yacht-b should NOT be affected
        assert await service.get("v1:yYachtB:yacht-b:user-001:manager:search.stream:1:ghi789") is not None

    @pytest.mark.asyncio
    async def test_yacht_clear_does_not_affect_other_yachts(self, mock_cache_store, sample_cache_entries):
        """Test that clearing yacht cache doesn't affect other yachts."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Pre-populate
        for key, value in sample_cache_entries.items():
            await service.set(key, value, ttl=3600)

        # Count entries per yacht before
        yacht_a_count_before = sum(1 for k in sample_cache_entries if "yacht-a" in k)
        yacht_b_count_before = sum(1 for k in sample_cache_entries if "yacht-b" in k)

        assert yacht_a_count_before == 3
        assert yacht_b_count_before == 2

        # Clear yacht-a
        await service.clear_for_yacht("yacht-a")

        # Yacht-b should still have all its entries
        yacht_b_entries_after = []
        for key in sample_cache_entries:
            if "yacht-b" in key:
                val = await service.get(key)
                if val:
                    yacht_b_entries_after.append(key)

        assert len(yacht_b_entries_after) == 2


# ============================================================================
# TTL ENFORCEMENT TESTS
# ============================================================================

class TestCacheTTLEnforcement:
    """Test that cache entries expire correctly."""

    @pytest.mark.asyncio
    async def test_cache_entry_expires_after_ttl(self, mock_cache_store):
        """Test that cache entries expire after TTL."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Set with very short TTL
        await service.set("short-ttl-key", {"data": "value"}, ttl=0.1)

        # Should exist immediately
        assert await service.get("short-ttl-key") == {"data": "value"}

        # Wait for TTL
        await asyncio.sleep(0.15)

        # Should be expired
        assert await service.get("short-ttl-key") is None

    @pytest.mark.asyncio
    async def test_revocation_effective_within_ttl(self, mock_cache_store):
        """Test that revocation is effective even with cache (TTL < 2 min)."""
        from services.cache import CacheService

        service = CacheService(store=mock_cache_store)

        # Per spec: TTL must be < 2 minutes
        # Streaming Phase 1: 30-120s, Phase 2: 10-30s
        max_ttl = 120  # seconds

        # Set entry with max allowed TTL
        key = "v1:yYachtA:yacht-a:user-001:captain:search.stream:1:abc123"
        await service.set(key, {"data": "cached"}, ttl=max_ttl)

        # Entry exists
        assert await service.get(key) is not None

        # Simulate revocation - clear immediately
        await service.clear_for_user("user-001", "yacht-a")

        # Entry should be gone immediately (not waiting for TTL)
        assert await service.get(key) is None


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_clear_cache_for_user_function(self):
        """Test clear_cache_for_user convenience function."""
        from services.cache import clear_cache_for_user, get_cache_service

        with patch.object(get_cache_service(), 'clear_for_user', new_callable=AsyncMock) as mock_clear:
            mock_clear.return_value = 5

            result = await clear_cache_for_user("user-001", "yacht-001")

            mock_clear.assert_called_once_with("user-001", "yacht-001")
            assert result == 5

    @pytest.mark.asyncio
    async def test_clear_cache_for_yacht_function(self):
        """Test clear_cache_for_yacht convenience function."""
        from services.cache import clear_cache_for_yacht, get_cache_service

        with patch.object(get_cache_service(), 'clear_for_yacht', new_callable=AsyncMock) as mock_clear:
            mock_clear.return_value = 10

            result = await clear_cache_for_yacht("yacht-001")

            mock_clear.assert_called_once_with("yacht-001")
            assert result == 10


# ============================================================================
# INTEGRATION WITH STREAMING SEARCH
# ============================================================================

class TestStreamingSearchCacheIntegration:
    """Test cache invalidation integrates with streaming search."""

    def test_cache_key_includes_role(self):
        """Test that cache key includes role (invalidation boundary)."""
        from utils.cache_keys import build_streaming_cache_key
        from middleware.action_security import ActionContext

        ctx = ActionContext(
            user_id="user-001",
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
        )

        key = build_streaming_cache_key(
            endpoint="search.stream",
            ctx=ctx,
            phase=1,
            raw_query="engine",
        )

        # Key must include role
        assert "captain" in key

        # Change role, key should be different
        ctx2 = ActionContext(
            user_id="user-001",
            yacht_id="yacht-001",
            role="crew",  # Different role
            tenant_key_alias="yYacht001",
        )

        key2 = build_streaming_cache_key(
            endpoint="search.stream",
            ctx=ctx2,
            phase=1,
            raw_query="engine",
        )

        assert key != key2
        assert "crew" in key2

    def test_cache_key_includes_user_id(self):
        """Test that cache key includes user_id (invalidation boundary)."""
        from utils.cache_keys import build_streaming_cache_key
        from middleware.action_security import ActionContext

        ctx1 = ActionContext(
            user_id="user-001",
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
        )

        ctx2 = ActionContext(
            user_id="user-002",  # Different user
            yacht_id="yacht-001",
            role="captain",
            tenant_key_alias="yYacht001",
        )

        key1 = build_streaming_cache_key("search.stream", ctx1, 1, "engine")
        key2 = build_streaming_cache_key("search.stream", ctx2, 1, "engine")

        assert key1 != key2
        assert "user-001" in key1
        assert "user-002" in key2


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
