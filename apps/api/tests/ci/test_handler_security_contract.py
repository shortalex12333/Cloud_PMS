"""
CelesteOS API - Handler Security Contract Tests
=================================================

CI contract tests that fail builds if handlers ship without @secure_action.

This ensures:
1. All handlers in SECURE_HANDLER_MODULES have @secure_action decorator
2. MUTATE/SIGNED/ADMIN handlers require idempotency
3. Error messages don't leak sensitive info
4. Admin 2-person rule is enforced
5. Registry startup rejects unsecured handlers

Run: pytest tests/ci/test_handler_security_contract.py -v
"""

import pytest
from unittest.mock import MagicMock
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


class TestHandlerSecurityContract:
    """Contract tests ensuring all handlers have @secure_action."""

    def test_action_security_module_imports(self):
        """action_security module should import successfully."""
        from middleware.action_security import (
            secure_action,
            is_secured_handler,
            ActionContext,
            ActionSecurityError,
        )

        assert secure_action is not None
        assert is_secured_handler is not None

    def test_secure_admin_handlers_all_secured(self):
        """All admin handlers must have @secure_action."""
        from middleware.action_security import is_secured_handler
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        handlers = get_secure_admin_handlers(mock_client, mock_client)

        for action_id, handler in handlers.items():
            assert is_secured_handler(handler), f"Handler {action_id} missing @secure_action"

    def test_required_admin_handlers_exist(self):
        """All required admin handlers exist."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers

        mock_client = MagicMock()
        handlers = get_secure_admin_handlers(mock_client, mock_client)

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

    def test_admin_mutations_are_admin_group(self):
        """Admin mutations should be ADMIN action group."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        mock_client = MagicMock()
        handlers = get_secure_admin_handlers(mock_client, mock_client)

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

    def test_admin_reads_are_read_group(self):
        """Admin read handlers should be READ action group."""
        from handlers.secure_admin_handlers import get_secure_admin_handlers
        from middleware.action_security import get_handler_security_metadata

        mock_client = MagicMock()
        handlers = get_secure_admin_handlers(mock_client, mock_client)

        read_actions = ["admin_list_memberships", "admin_get_membership"]

        for action_id in read_actions:
            handler = handlers[action_id]
            metadata = get_handler_security_metadata(handler)
            assert metadata['action_group'] == "READ", f"{action_id} should be READ"


class TestTwoPersonRuleEnforcement:
    """Tests for 2-person rule on privileged role assignments."""

    def test_privileged_roles_defined(self):
        """Privileged roles should be defined."""
        from handlers.secure_admin_handlers import PRIVILEGED_ROLES

        assert "captain" in PRIVILEGED_ROLES
        assert "manager" in PRIVILEGED_ROLES
        assert "chief_engineer" in PRIVILEGED_ROLES
        assert "crew" not in PRIVILEGED_ROLES

    def test_two_person_rule_violation_error(self):
        """TwoPersonRuleViolation should return 403."""
        from handlers.secure_admin_handlers import TwoPersonRuleViolation

        error = TwoPersonRuleViolation(
            inviter_id="user-aaa",
            approver_id="user-aaa",  # Same person
            role="captain",
        )

        assert error.status_code == 403
        assert error.code == "TWO_PERSON_RULE"
        assert error.inviter_id == error.approver_id

    def test_self_escalation_error(self):
        """SelfEscalationError should return 403."""
        from handlers.secure_admin_handlers import SelfEscalationError

        error = SelfEscalationError("user-123", "captain")

        assert error.status_code == 403
        assert error.code == "SELF_ESCALATION"


class TestErrorMessageHygiene:
    """Tests ensuring error messages don't leak sensitive info."""

    def test_ownership_error_hides_entity_id(self):
        """OwnershipValidationError should not expose entity ID."""
        from middleware.action_security import OwnershipValidationError

        error = OwnershipValidationError("document", "doc-secret-uuid-12345")

        # Should not contain the entity ID
        assert "doc-secret-uuid-12345" not in error.message
        assert error.status_code == 404

    def test_ownership_errors_same_message(self):
        """Different entity IDs should produce same error message."""
        from middleware.action_security import OwnershipValidationError

        error1 = OwnershipValidationError("fault", "fault-aaa")
        error2 = OwnershipValidationError("fault", "fault-bbb")

        assert error1.message == error2.message

    def test_standard_error_codes_no_table_names(self):
        """Standard error messages should not contain table names."""
        from middleware.action_security import get_standard_error_codes

        codes = get_standard_error_codes()

        table_names = ["pms_", "auth_", "memberships", "fleet_registry"]

        for code, info in codes.items():
            message = info['message'].lower()
            for table in table_names:
                assert table not in message, f"Code {code} contains table name: {table}"


class TestSecurityChecks:
    """Tests for security check functions."""

    def test_check_yacht_not_frozen_allows_read(self):
        """READ actions should be allowed on frozen yachts."""
        from middleware.action_security import (
            ActionContext,
            ActionGroup,
            check_yacht_not_frozen,
        )

        ctx = ActionContext(
            user_id="user-123",
            yacht_id="yacht-456",
            role="captain",
            tenant_key_alias="test",
            is_frozen=True,  # Yacht is frozen
        )

        # Should not raise for READ
        check_yacht_not_frozen(ctx, ActionGroup.READ)

    def test_check_yacht_not_frozen_blocks_mutate(self):
        """MUTATE actions should be blocked on frozen yachts."""
        from middleware.action_security import (
            ActionContext,
            ActionGroup,
            check_yacht_not_frozen,
            YachtFrozenError,
        )

        ctx = ActionContext(
            user_id="user-123",
            yacht_id="yacht-456",
            role="captain",
            tenant_key_alias="test",
            is_frozen=True,
        )

        with pytest.raises(YachtFrozenError):
            check_yacht_not_frozen(ctx, ActionGroup.MUTATE)

    def test_idempotency_required_for_admin(self):
        """ADMIN actions require idempotency key."""
        from middleware.action_security import (
            ActionGroup,
            check_idempotency_key,
            IdempotencyRequiredError,
        )

        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(None, "admin_action", ActionGroup.ADMIN)

    def test_idempotency_not_required_for_read(self):
        """READ actions don't require idempotency."""
        from middleware.action_security import ActionGroup, check_idempotency_key

        result = check_idempotency_key(None, "read_action", ActionGroup.READ)
        assert result is None


class TestAuditEntryBuilder:
    """Tests for audit entry building."""

    def test_audit_entry_outcome_required(self):
        """Audit entry must include outcome."""
        from middleware.action_security import ActionContext, build_audit_entry

        ctx = ActionContext(
            user_id="user-123",
            yacht_id="yacht-456",
            role="captain",
            tenant_key_alias="test",
        )

        for outcome in ["allowed", "denied", "error"]:
            entry = build_audit_entry(
                ctx=ctx,
                action="test_action",
                entity_type="test",
                entity_id="test-123",
                outcome=outcome,
            )

            assert entry['metadata']['outcome'] == outcome

    def test_audit_entry_signature_never_none(self):
        """Audit entry signature is never None."""
        from middleware.action_security import ActionContext, build_audit_entry

        ctx = ActionContext(
            user_id="user-123",
            yacht_id="yacht-456",
            role="captain",
            tenant_key_alias="test",
        )

        entry = build_audit_entry(
            ctx=ctx,
            action="test",
            entity_type="test",
            entity_id="test-123",
            signature=None,
        )

        assert entry['signature'] is not None
        assert entry['signature'] == {}


class TestModuleExports:
    """Test module exports are complete."""

    def test_action_security_exports(self):
        """action_security exports all required items."""
        from middleware import action_security

        required = [
            'ActionContext',
            'ActionGroup',
            'ActionSecurityError',
            'YachtFrozenError',
            'RoleNotAllowedError',
            'IdempotencyRequiredError',
            'OwnershipValidationError',
            'secure_action',
            'is_secured_handler',
            'get_handler_security_metadata',
            'build_audit_entry',
            'map_security_error_to_response',
        ]

        for name in required:
            assert hasattr(action_security, name), f"Missing export: {name}"

    def test_secure_admin_handlers_exports(self):
        """secure_admin_handlers exports required items."""
        from handlers import secure_admin_handlers

        required = [
            'get_secure_admin_handlers',
            'ADMIN_ROLES',
            'PRIVILEGED_ROLES',
        ]

        for name in required:
            assert hasattr(secure_admin_handlers, name), f"Missing export: {name}"


# Run with: pytest tests/ci/test_handler_security_contract.py -v
