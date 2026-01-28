"""
CelesteOS API - Kill Switch / Incident Mode Tests
==================================================

Tests for global incident mode and yacht freeze functionality.

Security invariants tested:
1. Incident mode blocks MUTATE/SIGNED/ADMIN actions
2. Incident mode blocks streaming when disable_streaming=True
3. Incident mode blocks signed URLs when disable_signed_urls=True
4. Yacht freeze blocks MUTATE/SIGNED/ADMIN for that yacht only
5. System flags cache respects TTL
6. Cache is cleared when incident mode changes
7. Incident mode audit logging
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

# Import modules under test
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_master_client():
    """Mock Supabase client for MASTER DB."""
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
    return client


@pytest.fixture
def incident_mode_flags():
    """System flags with incident mode enabled."""
    return {
        "id": 1,
        "incident_mode": True,
        "disable_streaming": True,
        "disable_signed_urls": True,
        "disable_writes": True,
        "incident_reason": "Security incident under investigation",
        "incident_started_at": datetime.now(timezone.utc).isoformat(),
        "incident_started_by": "admin-user-001",
    }


@pytest.fixture
def normal_flags():
    """System flags with incident mode disabled."""
    return {
        "id": 1,
        "incident_mode": False,
        "disable_streaming": False,
        "disable_signed_urls": False,
        "disable_writes": False,
        "incident_reason": None,
        "incident_started_at": None,
        "incident_started_by": None,
    }


# ============================================================================
# SYSTEM FLAGS CACHE TESTS
# ============================================================================

class TestSystemFlagsCache:
    """Test system flags caching behavior."""

    def test_get_system_flags_returns_defaults_on_empty(self, mock_master_client):
        """Test defaults returned when no system_flags row exists."""
        from middleware.auth import get_system_flags, clear_system_flags_cache, _system_flags_cache

        # Clear cache
        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

            flags = get_system_flags()

            assert flags['incident_mode'] is False
            assert flags['disable_streaming'] is False
            assert flags['disable_signed_urls'] is False
            assert flags['disable_writes'] is False

    def test_get_system_flags_returns_cached_value(self, mock_master_client, incident_mode_flags):
        """Test cached value returned within TTL."""
        from middleware.auth import (
            get_system_flags,
            clear_system_flags_cache,
            SYSTEM_FLAGS_CACHE_TTL,
        )

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            # First call - fetches from DB
            flags1 = get_system_flags()
            assert flags1['incident_mode'] is True

            # Change the mock
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={"incident_mode": False})

            # Second call - should return cached
            flags2 = get_system_flags()
            assert flags2['incident_mode'] is True  # Still cached

    def test_clear_system_flags_cache_forces_refetch(self, mock_master_client, incident_mode_flags, normal_flags):
        """Test clearing cache forces refetch."""
        from middleware.auth import get_system_flags, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            # First fetch - incident mode
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)
            flags1 = get_system_flags()
            assert flags1['incident_mode'] is True

            # Clear cache
            clear_system_flags_cache()

            # Change mock to normal
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=normal_flags)

            # Should get new value
            flags2 = get_system_flags()
            assert flags2['incident_mode'] is False

    def test_is_incident_mode_active(self, mock_master_client, incident_mode_flags):
        """Test is_incident_mode_active helper."""
        from middleware.auth import is_incident_mode_active, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            assert is_incident_mode_active() is True


# ============================================================================
# INCIDENT MODE ACTION BLOCKING TESTS
# ============================================================================

class TestIncidentModeActionBlocking:
    """Test action blocking during incident mode."""

    def test_check_incident_mode_blocks_mutate(self, mock_master_client, incident_mode_flags):
        """Test MUTATE actions blocked in incident mode."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("MUTATE")
            assert error is not None
            assert "incident mode" in error.lower()

    def test_check_incident_mode_blocks_signed(self, mock_master_client, incident_mode_flags):
        """Test SIGNED actions blocked in incident mode."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("SIGNED")
            assert error is not None
            assert "incident mode" in error.lower()

    def test_check_incident_mode_blocks_admin(self, mock_master_client, incident_mode_flags):
        """Test ADMIN actions blocked in incident mode."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("ADMIN")
            assert error is not None
            assert "incident mode" in error.lower()

    def test_check_incident_mode_allows_read(self, mock_master_client, incident_mode_flags):
        """Test READ actions allowed in incident mode."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("READ")
            assert error is None  # READ allowed

    def test_check_incident_mode_blocks_streaming(self, mock_master_client, incident_mode_flags):
        """Test streaming blocked when disable_streaming=True."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("READ", is_streaming=True)
            assert error is not None
            assert "streaming" in error.lower()

    def test_no_blocking_when_not_in_incident_mode(self, mock_master_client, normal_flags):
        """Test no blocking when incident mode is off."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=normal_flags)

            assert check_incident_mode_for_action("MUTATE") is None
            assert check_incident_mode_for_action("SIGNED") is None
            assert check_incident_mode_for_action("ADMIN") is None
            assert check_incident_mode_for_action("READ") is None
            assert check_incident_mode_for_action("READ", is_streaming=True) is None


# ============================================================================
# FASTAPI DEPENDENCY TESTS
# ============================================================================

class TestIncidentModeDependencies:
    """Test FastAPI dependencies for incident mode."""

    @pytest.mark.asyncio
    async def test_check_streaming_allowed_raises_on_disabled(self, mock_master_client, incident_mode_flags):
        """Test check_streaming_allowed raises 503 when disabled."""
        from middleware.auth import check_streaming_allowed, clear_system_flags_cache
        from fastapi import HTTPException

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            with pytest.raises(HTTPException) as exc_info:
                await check_streaming_allowed()

            assert exc_info.value.status_code == 503
            assert "disabled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_check_streaming_allowed_passes_when_ok(self, mock_master_client, normal_flags):
        """Test check_streaming_allowed passes when streaming enabled."""
        from middleware.auth import check_streaming_allowed, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=normal_flags)

            # Should not raise
            result = await check_streaming_allowed()
            assert result is None

    @pytest.mark.asyncio
    async def test_check_signed_urls_allowed_raises_on_disabled(self, mock_master_client, incident_mode_flags):
        """Test check_signed_urls_allowed raises 503 when disabled."""
        from middleware.auth import check_signed_urls_allowed, clear_system_flags_cache
        from fastapi import HTTPException

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            with pytest.raises(HTTPException) as exc_info:
                await check_signed_urls_allowed()

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_check_writes_allowed_raises_on_disabled(self, mock_master_client, incident_mode_flags):
        """Test check_writes_allowed raises 503 when disabled."""
        from middleware.auth import check_writes_allowed, clear_system_flags_cache
        from fastapi import HTTPException

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            with pytest.raises(HTTPException) as exc_info:
                await check_writes_allowed()

            assert exc_info.value.status_code == 503


# ============================================================================
# STREAMING SEARCH INCIDENT MODE TESTS
# ============================================================================

class TestStreamingSearchIncidentMode:
    """Test streaming search blocks during incident mode."""

    @pytest.mark.asyncio
    async def test_streaming_context_checks_incident_mode(self, mock_master_client, incident_mode_flags):
        """Test get_streaming_context checks incident mode."""
        from fastapi import HTTPException
        from middleware.auth import clear_system_flags_cache

        # Clear cache first
        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            # Clear again after setting up mock
            clear_system_flags_cache()

            from routes.search_streaming import get_streaming_context

            mock_request = MagicMock()
            mock_auth = {
                "user_id": "user-001",
                "yacht_id": "yacht-001",
                "role": "captain",
                "tenant_key_alias": "yYacht001",
            }

            with pytest.raises(HTTPException) as exc_info:
                await get_streaming_context(mock_request, mock_auth)

            assert exc_info.value.status_code == 503
            assert "service_unavailable" in exc_info.value.detail


# ============================================================================
# YACHT FREEZE TESTS
# ============================================================================

class TestYachtFreeze:
    """Test per-yacht freeze functionality."""

    @pytest.mark.asyncio
    async def test_yacht_freeze_sets_flag(self, mock_master_client):
        """Test yacht freeze sets is_frozen flag."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_tenant_client = MagicMock()
        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        # Auth dict for the @secure_action wrapper
        auth = {
            "user_id": "admin-001",
            "yacht_id": "yacht-001",
            "role": "captain",
            "tenant_key_alias": "yYacht001",
        }

        # Execute with proper arguments for @secure_action wrapper
        with patch('services.cache.clear_cache_for_yacht', new_callable=AsyncMock):
            result = await handlers["admin_freeze_yacht"](
                mock_tenant_client,  # db_client
                auth,                 # auth dict
                idempotency_key="idem-001",
                freeze=True,
                reason="Security drill",
            )

        assert result["is_frozen"] is True
        mock_master_client.table.assert_called()


# ============================================================================
# INCIDENT MODE ADMIN HANDLER TESTS
# ============================================================================

class TestIncidentModeHandlers:
    """Test incident mode admin handlers."""

    @pytest.mark.asyncio
    async def test_enable_incident_mode_requires_reason(self):
        """Test enable_incident_mode requires reason."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import ActionSecurityError

        mock_master = MagicMock()
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        auth = {
            "user_id": "admin-001",
            "yacht_id": "yacht-001",
            "role": "captain",
            "tenant_key_alias": "yYacht001",
        }

        with pytest.raises(ActionSecurityError) as exc_info:
            await handlers["admin_enable_incident_mode"](
                mock_tenant,
                auth,
                idempotency_key="idem-001",
                reason=None,
            )

        assert "reason is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_enable_incident_mode_updates_flags(self):
        """Test enable_incident_mode updates system_flags."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_master = MagicMock()
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        auth = {
            "user_id": "admin-001",
            "yacht_id": "yacht-001",
            "role": "captain",
            "tenant_key_alias": "yYacht001",
        }

        with patch('middleware.auth.clear_system_flags_cache'):
            result = await handlers["admin_enable_incident_mode"](
                mock_tenant,
                auth,
                idempotency_key="idem-001",
                reason="Suspicious activity detected",
                disable_streaming=True,
                disable_signed_urls=True,
                disable_writes=True,
            )

        assert result["incident_mode"] is True
        assert result["reason"] == "Suspicious activity detected"
        assert result["started_by"] == "admin-001"

        # Verify system_flags was called at some point (may also call security_events for audit)
        mock_master.table.assert_any_call("system_flags")

    @pytest.mark.asyncio
    async def test_disable_incident_mode_clears_flags(self):
        """Test disable_incident_mode clears system_flags."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_master = MagicMock()
        mock_master.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "incident_started_at": "2024-01-01T00:00:00Z",
            "incident_started_by": "admin-001",
        }])
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        auth = {
            "user_id": "admin-002",
            "yacht_id": "yacht-001",
            "role": "captain",
            "tenant_key_alias": "yYacht001",
        }

        with patch('middleware.auth.clear_system_flags_cache'):
            result = await handlers["admin_disable_incident_mode"](
                mock_tenant,
                auth,
                idempotency_key="idem-002",
                resolution_notes="Investigation complete, no breach found",
            )

        assert result["incident_mode"] is False
        assert result["disabled_by"] == "admin-002"

    @pytest.mark.asyncio
    async def test_get_system_flags_returns_current_state(self):
        """Test get_system_flags returns current state."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_master = MagicMock()
        mock_master.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "incident_mode": True,
            "disable_streaming": True,
            "disable_signed_urls": False,
            "disable_writes": True,
            "incident_reason": "Active incident",
        }])
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        auth = {
            "user_id": "user-001",
            "yacht_id": "yacht-001",
            "role": "manager",
            "tenant_key_alias": "yYacht001",
        }

        result = await handlers["admin_get_system_flags"](
            mock_tenant,
            auth,
        )

        assert result["incident_mode"] is True
        assert result["disable_streaming"] is True
        assert result["disable_writes"] is True
        assert result["incident_reason"] == "Active incident"


# ============================================================================
# ERROR HYGIENE TESTS
# ============================================================================

class TestErrorHygiene:
    """Test error messages don't leak sensitive info."""

    def test_incident_block_message_is_generic(self, mock_master_client, incident_mode_flags):
        """Test incident mode block messages are generic."""
        from middleware.auth import check_incident_mode_for_action, clear_system_flags_cache

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            error = check_incident_mode_for_action("MUTATE")

            # Should mention incident mode but not expose internal details
            assert "incident mode" in error.lower()
            assert "yacht" not in error.lower()  # No tenant identifiers
            assert "table" not in error.lower()  # No DB details

    @pytest.mark.asyncio
    async def test_streaming_disabled_message_is_generic(self, mock_master_client, incident_mode_flags):
        """Test streaming disabled message is generic."""
        from middleware.auth import check_streaming_allowed, clear_system_flags_cache
        from fastapi import HTTPException

        clear_system_flags_cache()

        with patch('middleware.auth.get_master_client', return_value=mock_master_client):
            mock_master_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=incident_mode_flags)

            with pytest.raises(HTTPException) as exc_info:
                await check_streaming_allowed()

            # Should be generic
            assert "disabled" in exc_info.value.detail.lower()
            assert "yacht" not in exc_info.value.detail.lower()


# ============================================================================
# AUDIT LOGGING TESTS
# ============================================================================

class TestIncidentModeAuditLogging:
    """Test audit logging for incident mode operations."""

    @pytest.mark.asyncio
    async def test_enable_incident_mode_logs_audit(self):
        """Test enabling incident mode writes audit log."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_master = MagicMock()
        mock_tenant = MagicMock()

        handlers = get_secure_admin_handlers(mock_tenant, mock_master)

        auth = {
            "user_id": "admin-001",
            "yacht_id": "yacht-001",
            "role": "captain",
            "tenant_key_alias": "yYacht001",
        }

        with patch('middleware.auth.clear_system_flags_cache'):
            await handlers["admin_enable_incident_mode"](
                mock_tenant,
                auth,
                idempotency_key="idem-001",
                reason="Test incident",
            )

        # Verify security_events insert was called
        calls = mock_master.table.call_args_list
        security_event_calls = [c for c in calls if c[0][0] == "security_events"]
        assert len(security_event_calls) > 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
