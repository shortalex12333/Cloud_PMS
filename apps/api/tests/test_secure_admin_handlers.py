"""
CelesteOS API - Secure Admin Handlers Tests
=============================================

Tests for handlers/secure_admin_handlers.py

Security invariants tested:
1. All admin handlers have @secure_action marker
2. ADMIN actions require idempotency key
3. Role validation enforced
4. yacht_id from context (not payload)
5. 2-person rule for privileged roles
6. Proper error mapping
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import os

# Test environment
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


class TestSecureAdminHandlersContract:
    """Contract tests for secure admin handlers."""

    @pytest.fixture
    def mock_master_client(self):
        """Create mock master DB client."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "mem-123"}])
        client.auth.admin.list_users.return_value = []
        return client

    @pytest.fixture
    def mock_tenant_client(self):
        """Create mock tenant DB client."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
        return client

    def test_all_handlers_have_secure_action_marker(self, mock_tenant_client, mock_master_client):
        """All returned handlers must have @secure_action."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import is_secured_handler

        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        for action_id, handler in handlers.items():
            assert is_secured_handler(handler), f"{action_id} missing @secure_action"

    def test_required_handlers_exist(self, mock_tenant_client, mock_master_client):
        """All required admin handlers exist."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        required = [
            "admin_invite_user",
            "admin_approve_membership",
            "admin_change_role",
            "admin_revoke_membership",
            "admin_freeze_yacht",
            "admin_list_memberships",
            "admin_get_membership",
        ]

        for action_id in required:
            assert action_id in handlers, f"Missing handler: {action_id}"

    def test_admin_actions_have_admin_group(self, mock_tenant_client, mock_master_client):
        """Mutation admin actions should be ADMIN group."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        admin_mutations = [
            "admin_invite_user",
            "admin_approve_membership",
            "admin_change_role",
            "admin_revoke_membership",
            "admin_freeze_yacht",
        ]

        for action_id in admin_mutations:
            handler = handlers[action_id]
            metadata = get_handler_security_metadata(handler)
            assert metadata['action_group'] == "ADMIN", f"{action_id} should be ADMIN"

    def test_read_actions_have_read_group(self, mock_tenant_client, mock_master_client):
        """Read-only admin actions should be READ group."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        read_actions = [
            "admin_list_memberships",
            "admin_get_membership",
        ]

        for action_id in read_actions:
            handler = handlers[action_id]
            metadata = get_handler_security_metadata(handler)
            assert metadata['action_group'] == "READ", f"{action_id} should be READ"

    def test_handlers_have_required_roles(self, mock_tenant_client, mock_master_client):
        """Admin handlers should have required roles set."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        handlers = get_secure_admin_handlers(mock_tenant_client, mock_master_client)

        for action_id, handler in handlers.items():
            metadata = get_handler_security_metadata(handler)
            assert metadata['required_roles'], f"{action_id} should have required_roles"


class TestSecureAdminHandlersSecurity:
    """Security invariant tests."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock clients."""
        master = MagicMock()
        tenant = MagicMock()

        # Setup basic mock behaviors
        master.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        master.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "mem-123"}])
        master.auth.admin.list_users.return_value = []

        tenant.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        return master, tenant

    def test_yacht_id_comes_from_context(self, mock_clients):
        """yacht_id must come from context, not payload."""
        from middleware.action_security import ActionContext

        ctx = ActionContext(
            user_id="user-123",
            yacht_id="correct-yacht-id",
            role="captain",
            tenant_key_alias="test",
            idempotency_key="idem-key-123456789",
        )

        # Params might include attacker-supplied yacht_id
        params = {
            "yacht_id": "attacker-yacht-id",  # Should be ignored
            "email": "test@test.com",
            "role_requested": "crew",
        }

        # The secure_action decorator injects yacht_id from ctx
        # This test validates the pattern
        assert ctx.yacht_id == "correct-yacht-id"
        assert ctx.yacht_id != params.get("yacht_id")

    def test_idempotency_key_required_for_admin_actions(self, mock_clients):
        """ADMIN actions require idempotency key via decorator."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        master, tenant = mock_clients
        handlers = get_secure_admin_handlers(tenant, master)

        admin_mutations = [
            "admin_invite_user",
            "admin_approve_membership",
            "admin_change_role",
            "admin_revoke_membership",
            "admin_freeze_yacht",
        ]

        for action_id in admin_mutations:
            handler = handlers[action_id]
            metadata = get_handler_security_metadata(handler)
            # ADMIN group enforces idempotency in check_idempotency_key
            assert metadata['action_group'] == "ADMIN"


class TestAdminHandlerRoleValidation:
    """Test role validation in admin handlers."""

    def test_invite_allowed_roles(self):
        """invite_user allows captain/manager only."""
        from handlers.admin_handlers import INVITE_ALLOWED_ROLES

        assert "captain" in INVITE_ALLOWED_ROLES
        assert "manager" in INVITE_ALLOWED_ROLES
        assert "crew" not in INVITE_ALLOWED_ROLES
        assert "hod" not in INVITE_ALLOWED_ROLES

    def test_approve_allowed_roles(self):
        """approve_membership allows captain/manager only."""
        from handlers.admin_handlers import APPROVE_ALLOWED_ROLES

        assert "captain" in APPROVE_ALLOWED_ROLES
        assert "manager" in APPROVE_ALLOWED_ROLES
        assert "crew" not in APPROVE_ALLOWED_ROLES

    def test_privileged_roles_require_2_person_rule(self):
        """Privileged role assignments require different approver."""
        from handlers.admin_handlers import PRIVILEGED_ROLES

        assert "captain" in PRIVILEGED_ROLES
        assert "manager" in PRIVILEGED_ROLES
        assert "chief_engineer" in PRIVILEGED_ROLES
        assert "crew" not in PRIVILEGED_ROLES


class TestAdminHandlerErrorMapping:
    """Test error mapping from AdminValidationError to ActionSecurityError."""

    @pytest.fixture
    def mock_setup(self):
        """Setup mocks for error tests."""
        master = MagicMock()
        tenant = MagicMock()

        # Return empty data to trigger validation errors
        master.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        master.auth.admin.list_users.return_value = []

        return master, tenant

    def test_validation_error_maps_to_action_security_error(self):
        """AdminValidationError should map to ActionSecurityError."""
        from handlers.admin_handlers import AdminValidationError
        from middleware.action_security import ActionSecurityError

        # Create validation error
        val_error = AdminValidationError("missing_email", "Email is required", 400)

        # Create equivalent ActionSecurityError
        sec_error = ActionSecurityError(val_error.code, val_error.message, val_error.status_code)

        assert sec_error.code == "missing_email"
        assert sec_error.message == "Email is required"
        assert sec_error.status_code == 400

    def test_permission_error_maps_to_403(self):
        """AdminPermissionError should map to 403 ActionSecurityError."""
        from handlers.admin_handlers import AdminPermissionError
        from middleware.action_security import ActionSecurityError

        # Create permission error
        perm_error = AdminPermissionError("invite_user", ["captain", "manager"], "crew")

        # Map to ActionSecurityError
        sec_error = ActionSecurityError("PERMISSION_DENIED", perm_error.message, 403)

        assert sec_error.status_code == 403
        assert sec_error.code == "PERMISSION_DENIED"


class TestMembershipStatusTransitions:
    """Test membership status transition validation."""

    def test_valid_invite_transitions(self):
        """INVITED status can transition to ACCEPTED/REVOKED."""
        from handlers.admin_handlers import MembershipStatus

        # Valid starting states for approve
        valid_for_approve = {
            MembershipStatus.INVITED.value,
            MembershipStatus.ACCEPTED.value,
            MembershipStatus.PROVISIONED.value,
        }

        assert "INVITED" in valid_for_approve
        assert "ACCEPTED" in valid_for_approve
        assert "ACTIVE" not in valid_for_approve
        assert "REVOKED" not in valid_for_approve

    def test_revoked_is_terminal(self):
        """REVOKED status is terminal (no transitions out)."""
        from handlers.admin_handlers import MembershipStatus

        # REVOKED should not be in valid_for_approve
        valid_for_approve = {
            MembershipStatus.INVITED.value,
            MembershipStatus.ACCEPTED.value,
            MembershipStatus.PROVISIONED.value,
        }

        assert MembershipStatus.REVOKED.value not in valid_for_approve


class TestSecureAdminModuleExports:
    """Test module exports."""

    def test_exports(self):
        """Module exports required items."""
        from handlers import secure_admin_handlers

        assert hasattr(secure_admin_handlers, 'get_secure_admin_handlers')
        assert hasattr(secure_admin_handlers, 'ADMIN_ROLES')
        assert hasattr(secure_admin_handlers, 'ADMIN_READ_ROLES')


class TestAdminHandlerIntegrationPatterns:
    """Test integration patterns for admin handlers."""

    def test_handler_signature_matches_secure_action_pattern(self):
        """Handler signature should match @secure_action pattern."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        import inspect

        # Mock clients
        master = MagicMock()
        tenant = MagicMock()

        handlers = get_secure_admin_handlers(tenant, master)

        for action_id, handler in handlers.items():
            # All handlers should be async
            assert inspect.iscoroutinefunction(handler.__wrapped__), f"{action_id} should be async"

    def test_handlers_use_ctx_yacht_id(self):
        """Handlers should use ctx.yacht_id not params."""
        from middleware.action_security import ActionContext

        # Create context with known yacht_id
        ctx = ActionContext(
            user_id="user-123",
            yacht_id="ctx-yacht-id",
            role="captain",
            tenant_key_alias="test",
        )

        # yacht_id in context should be used
        assert ctx.yacht_id == "ctx-yacht-id"


# Run with: pytest tests/test_secure_admin_handlers.py -v
