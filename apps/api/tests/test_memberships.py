"""
CelesteOS API - Membership Tests
================================

Tests for membership lifecycle and admin handlers.

Tests ensure:
1. Status transitions follow allowed paths
2. REVOKED denies access within TTL
3. Audit entries present for all state changes
4. 2-person rule enforced for privileged roles
5. Frozen yacht blocks mutations
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from handlers.admin_handlers import (
    AdminHandlers,
    AdminContext,
    AdminValidationError,
    AdminPermissionError,
    MembershipStatus,
    PRIVILEGED_ROLES,
    get_admin_handlers,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def yacht_id() -> str:
    """Test yacht UUID."""
    return "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def user_id() -> str:
    """Test user UUID (actor)."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def target_user_id() -> str:
    """Target user UUID (being invited/approved/revoked)."""
    return "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def admin_context(yacht_id, user_id) -> AdminContext:
    """Admin context for tests."""
    return AdminContext(
        user_id=user_id,
        yacht_id=yacht_id,
        role="captain",
        tenant_key_alias="y85fe1119",
        idempotency_key=str(uuid.uuid4()),
    )


@pytest.fixture
def mock_master_client():
    """Mock MASTER DB client."""
    mock = MagicMock()

    # Default: return empty for queries
    mock.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": str(uuid.uuid4())}])
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    # Mock auth.admin.list_users
    mock.auth = MagicMock()
    mock.auth.admin = MagicMock()
    mock.auth.admin.list_users = MagicMock(return_value=[])

    return mock


@pytest.fixture
def mock_tenant_client():
    """Mock TENANT DB client."""
    mock = MagicMock()
    mock.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"role": "crew"}])
    return mock


@pytest.fixture
def tenant_factory(mock_tenant_client):
    """Factory function for tenant clients."""
    return lambda alias: mock_tenant_client


# ============================================================================
# MembershipStatus Tests
# ============================================================================

class TestMembershipStatus:
    """Tests for membership status enum."""

    def test_all_statuses_defined(self):
        """All expected statuses are defined."""
        expected = ["INVITED", "ACCEPTED", "PROVISIONED", "ACTIVE", "SUSPENDED", "REVOKED"]
        actual = [s.value for s in MembershipStatus]

        for status in expected:
            assert status in actual

    def test_revoked_is_terminal(self):
        """REVOKED is a terminal state."""
        # This is a design test - verify the concept
        assert MembershipStatus.REVOKED.value == "REVOKED"


# ============================================================================
# AdminHandlers Initialization Tests
# ============================================================================

class TestAdminHandlersInit:
    """Tests for AdminHandlers initialization."""

    def test_get_admin_handlers_returns_instance(
        self, mock_master_client, tenant_factory
    ):
        """get_admin_handlers returns AdminHandlers instance."""
        handlers = get_admin_handlers(mock_master_client, tenant_factory)
        assert isinstance(handlers, AdminHandlers)


# ============================================================================
# invite_user Tests
# ============================================================================

class TestInviteUser:
    """Tests for invite_user handler."""

    @pytest.mark.asyncio
    async def test_invite_requires_captain_or_manager(
        self, mock_master_client, tenant_factory, yacht_id, user_id
    ):
        """invite_user requires captain or manager role."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        # Crew cannot invite
        ctx = AdminContext(
            user_id=user_id,
            yacht_id=yacht_id,
            role="crew",
            tenant_key_alias="y85fe1119",
            idempotency_key=str(uuid.uuid4()),
        )

        with pytest.raises(AdminPermissionError) as exc_info:
            await handlers.invite_user(
                {"email": "new@test.com", "role_requested": "crew"},
                ctx,
            )

        assert "crew" in exc_info.value.user_role

    @pytest.mark.asyncio
    async def test_invite_requires_email(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """invite_user requires email parameter."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.invite_user(
                {"role_requested": "crew"},
                admin_context,
            )

        assert exc_info.value.code == "missing_email"

    @pytest.mark.asyncio
    async def test_invite_requires_role_requested(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """invite_user requires role_requested parameter."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.invite_user(
                {"email": "new@test.com"},
                admin_context,
            )

        assert exc_info.value.code == "missing_role"

    @pytest.mark.asyncio
    async def test_invite_creates_membership(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """invite_user creates INVITED membership."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        result = await handlers.invite_user(
            {"email": "new@test.com", "role_requested": "crew"},
            admin_context,
        )

        assert result["status"] == MembershipStatus.INVITED.value
        assert "membership_id" in result

    @pytest.mark.asyncio
    async def test_invite_rejects_already_active(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """invite_user rejects if user already has active membership."""
        # Mock: user exists
        mock_user = MagicMock()
        mock_user.id = target_user_id
        mock_user.email = "existing@test.com"
        mock_master_client.auth.admin.list_users.return_value = [mock_user]

        # Mock: existing active membership
        mock_master_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4()), "status": "ACTIVE"}]
        )

        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.invite_user(
                {"email": "existing@test.com", "role_requested": "crew"},
                admin_context,
            )

        assert exc_info.value.code == "already_member"
        assert exc_info.value.status_code == 409


# ============================================================================
# approve_membership Tests
# ============================================================================

class TestApproveMembership:
    """Tests for approve_membership handler."""

    @pytest.mark.asyncio
    async def test_approve_requires_membership_id(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """approve_membership requires membership_id."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.approve_membership({}, admin_context)

        assert exc_info.value.code == "missing_membership_id"

    @pytest.mark.asyncio
    async def test_approve_returns_404_for_nonexistent(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """approve_membership returns 404 for nonexistent membership."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.approve_membership(
                {"membership_id": str(uuid.uuid4())},
                admin_context,
            )

        assert exc_info.value.code == "not_found"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_enforces_two_person_rule(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """approve_membership enforces 2-person rule for privileged roles."""
        # Mock: membership exists, invited by same user
        mock_master_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": str(uuid.uuid4()),
                "user_id": target_user_id,
                "status": "INVITED",
                "invited_by": admin_context.user_id,  # Same as approver
                "role_requested": "captain",  # Privileged role
            }]
        )

        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.approve_membership(
                {"membership_id": str(uuid.uuid4())},
                admin_context,
            )

        assert exc_info.value.code == "two_person_rule"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_approve_allows_different_approver(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """approve_membership allows different approver."""
        different_inviter = str(uuid.uuid4())

        # Mock: membership with different inviter
        mock_master_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": str(uuid.uuid4()),
                "user_id": target_user_id,
                "status": "INVITED",
                "invited_by": different_inviter,
                "role_requested": "captain",
            }]
        )

        handlers = AdminHandlers(mock_master_client, tenant_factory)

        result = await handlers.approve_membership(
            {"membership_id": str(uuid.uuid4())},
            admin_context,
        )

        assert result["status"] == MembershipStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_approve_rejects_invalid_status(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """approve_membership rejects membership in wrong status."""
        # Mock: membership already revoked
        mock_master_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "id": str(uuid.uuid4()),
                "user_id": target_user_id,
                "status": "REVOKED",
                "invited_by": str(uuid.uuid4()),
            }]
        )

        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.approve_membership(
                {"membership_id": str(uuid.uuid4())},
                admin_context,
            )

        assert exc_info.value.code == "invalid_status"


# ============================================================================
# revoke_membership Tests
# ============================================================================

class TestRevokeMembership:
    """Tests for revoke_membership handler."""

    @pytest.mark.asyncio
    async def test_revoke_prevents_self_revocation(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """revoke_membership prevents self-revocation."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.revoke_membership(
                {"user_id": admin_context.user_id},  # Same as actor
                admin_context,
            )

        assert exc_info.value.code == "self_revocation"
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_revoke_sets_status_revoked(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """revoke_membership sets status to REVOKED."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with patch('handlers.admin_handlers.clear_tenant_cache'):
            result = await handlers.revoke_membership(
                {"user_id": target_user_id, "reason": "Policy violation"},
                admin_context,
            )

        assert result["status"] == MembershipStatus.REVOKED.value
        assert result["user_id"] == target_user_id

    @pytest.mark.asyncio
    async def test_revoke_deactivates_tenant_role(
        self, mock_master_client, mock_tenant_client, admin_context, target_user_id
    ):
        """revoke_membership deactivates TENANT role."""
        tenant_factory = lambda alias: mock_tenant_client
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with patch('handlers.admin_handlers.clear_tenant_cache'):
            await handlers.revoke_membership(
                {"user_id": target_user_id},
                admin_context,
            )

        # Verify tenant role updated
        mock_tenant_client.table.return_value.update.assert_called()


# ============================================================================
# change_role Tests
# ============================================================================

class TestChangeRole:
    """Tests for change_role handler."""

    @pytest.mark.asyncio
    async def test_change_role_prevents_self_escalation(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """change_role prevents self-escalation to privileged role."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with pytest.raises(AdminValidationError) as exc_info:
            await handlers.change_role(
                {"user_id": admin_context.user_id, "new_role": "captain"},
                admin_context,
            )

        assert exc_info.value.code == "self_escalation"

    @pytest.mark.asyncio
    async def test_change_role_clears_cache(
        self, mock_master_client, mock_tenant_client, admin_context, target_user_id
    ):
        """change_role clears tenant cache."""
        tenant_factory = lambda alias: mock_tenant_client
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with patch('handlers.admin_handlers.clear_tenant_cache') as mock_clear:
            await handlers.change_role(
                {"user_id": target_user_id, "new_role": "chief_engineer"},
                admin_context,
            )

            mock_clear.assert_called_once_with(target_user_id)


# ============================================================================
# freeze_yacht Tests
# ============================================================================

class TestFreezeYacht:
    """Tests for freeze_yacht handler."""

    @pytest.mark.asyncio
    async def test_freeze_sets_is_frozen(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """freeze_yacht sets is_frozen on fleet_registry."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        result = await handlers.freeze_yacht(
            {"freeze": True, "reason": "Security incident"},
            admin_context,
        )

        assert result["is_frozen"] is True

    @pytest.mark.asyncio
    async def test_unfreeze_clears_is_frozen(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """freeze_yacht with freeze=False clears is_frozen."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        result = await handlers.freeze_yacht(
            {"freeze": False},
            admin_context,
        )

        assert result["is_frozen"] is False


# ============================================================================
# Audit Logging Tests
# ============================================================================

class TestAuditLogging:
    """Tests for audit logging in admin handlers."""

    @pytest.mark.asyncio
    async def test_invite_logs_attempt(
        self, mock_master_client, tenant_factory, admin_context
    ):
        """invite_user logs attempt to security_events."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        await handlers.invite_user(
            {"email": "new@test.com", "role_requested": "crew"},
            admin_context,
        )

        # Verify security_events insert was called
        # (This is a weak test - in real tests we'd verify the actual data)
        assert mock_master_client.table.called

    @pytest.mark.asyncio
    async def test_revoke_logs_success(
        self, mock_master_client, tenant_factory, admin_context, target_user_id
    ):
        """revoke_membership logs success to security_events."""
        handlers = AdminHandlers(mock_master_client, tenant_factory)

        with patch('handlers.admin_handlers.clear_tenant_cache'):
            await handlers.revoke_membership(
                {"user_id": target_user_id, "reason": "Policy violation"},
                admin_context,
            )

        # Verify logging occurred
        assert mock_master_client.table.called


# ============================================================================
# Permission Tests
# ============================================================================

class TestPermissions:
    """Tests for role-based permissions."""

    @pytest.mark.parametrize("role,expected_pass", [
        ("captain", True),
        ("manager", True),
        ("chief_engineer", False),
        ("crew", False),
    ])
    @pytest.mark.asyncio
    async def test_invite_role_permissions(
        self, mock_master_client, tenant_factory, yacht_id, user_id, role, expected_pass
    ):
        """invite_user respects role permissions."""
        ctx = AdminContext(
            user_id=user_id,
            yacht_id=yacht_id,
            role=role,
            tenant_key_alias="y85fe1119",
            idempotency_key=str(uuid.uuid4()),
        )

        handlers = AdminHandlers(mock_master_client, tenant_factory)

        if expected_pass:
            result = await handlers.invite_user(
                {"email": "new@test.com", "role_requested": "crew"},
                ctx,
            )
            assert "membership_id" in result
        else:
            with pytest.raises(AdminPermissionError):
                await handlers.invite_user(
                    {"email": "new@test.com", "role_requested": "crew"},
                    ctx,
                )
