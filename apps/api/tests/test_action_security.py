"""
CelesteOS API - Action Security Tests
======================================

Comprehensive tests for middleware/action_security.py

Security invariants tested:
1. yacht_id comes from context, never payload
2. Ownership validation returns 404 (not 403)
3. Role checks are enforced
4. Idempotency required for mutations
5. Error messages don't reveal sensitive info
6. Frozen yachts block mutations
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os
import uuid

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


class TestActionContext:
    """Test ActionContext creation and behavior."""

    def test_create_action_context(self):
        """Create ActionContext from auth dict."""
        from middleware.action_security import create_action_context

        auth = {
            'user_id': 'user-123',
            'yacht_id': 'yacht-456',
            'role': 'captain',
            'tenant_key_alias': 'test_yacht',
            'email': 'captain@test.yacht',
            'is_frozen': False,
        }

        ctx = create_action_context(auth, idempotency_key='idem-key')

        assert ctx.user_id == 'user-123'
        assert ctx.yacht_id == 'yacht-456'
        assert ctx.role == 'captain'
        assert ctx.idempotency_key == 'idem-key'
        assert ctx.is_frozen is False

    def test_action_context_to_dict(self):
        """ActionContext.to_dict excludes sensitive fields."""
        from middleware.action_security import ActionContext

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='captain',
            tenant_key_alias='test',
            email='secret@email.com',
        )

        d = ctx.to_dict()

        assert 'yacht_id' in d
        assert 'role' in d
        assert 'email' not in d  # Email excluded from dict


class TestSecureActionDecorator:
    """Test @secure_action decorator."""

    def test_decorator_marks_handler(self):
        """Decorated handler has _secure_action=True."""
        from middleware.action_security import secure_action, is_secured_handler

        @secure_action(action_id="test", action_group="READ")
        async def handler(ctx, **params):
            pass

        assert is_secured_handler(handler) is True
        assert handler._action_id == "test"
        assert handler._action_group == "READ"

    def test_undecorated_handler_not_secured(self):
        """Non-decorated handler is not secured."""
        from middleware.action_security import is_secured_handler

        async def handler(ctx, **params):
            pass

        assert is_secured_handler(handler) is False

    def test_decorator_injects_yacht_id(self):
        """Decorator injects yacht_id from context."""
        from middleware.action_security import secure_action

        received_params = {}

        @secure_action(action_id="test", action_group="READ")
        async def handler(ctx, **params):
            received_params.update(params)
            return {"success": True}

        import asyncio

        auth = {
            'user_id': 'user-123',
            'yacht_id': 'correct-yacht-id',
            'role': 'captain',
            'tenant_key_alias': 'test',
        }

        asyncio.run(handler(
            None,  # db_client
            auth,
            yacht_id='attacker-yacht-id',  # Should be ignored
        ))

        # yacht_id must come from context, not payload
        assert received_params['yacht_id'] == 'correct-yacht-id'


class TestYachtFreezeCheck:
    """Test yacht freeze enforcement."""

    def test_frozen_yacht_blocks_mutate(self):
        """MUTATE blocked on frozen yacht."""
        from middleware.action_security import (
            ActionContext,
            ActionGroup,
            check_yacht_not_frozen,
            YachtFrozenError,
        )

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='captain',
            tenant_key_alias='test',
            is_frozen=True,
        )

        with pytest.raises(YachtFrozenError) as exc_info:
            check_yacht_not_frozen(ctx, ActionGroup.MUTATE)

        assert exc_info.value.status_code == 403

    def test_frozen_yacht_blocks_admin(self):
        """ADMIN blocked on frozen yacht."""
        from middleware.action_security import (
            ActionContext,
            ActionGroup,
            check_yacht_not_frozen,
            YachtFrozenError,
        )

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='captain',
            tenant_key_alias='test',
            is_frozen=True,
        )

        with pytest.raises(YachtFrozenError):
            check_yacht_not_frozen(ctx, ActionGroup.ADMIN)

    def test_frozen_yacht_allows_read(self):
        """READ allowed on frozen yacht."""
        from middleware.action_security import (
            ActionContext,
            ActionGroup,
            check_yacht_not_frozen,
        )

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='captain',
            tenant_key_alias='test',
            is_frozen=True,
        )

        # Should not raise
        check_yacht_not_frozen(ctx, ActionGroup.READ)


class TestRoleCheck:
    """Test role enforcement."""

    def test_role_allowed(self):
        """Allowed role passes check."""
        from middleware.action_security import ActionContext, check_role_allowed

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='captain',
            tenant_key_alias='test',
        )

        # Should not raise
        check_role_allowed(ctx, {'captain', 'manager'})

    def test_role_not_allowed(self):
        """Disallowed role fails check."""
        from middleware.action_security import (
            ActionContext,
            check_role_allowed,
            RoleNotAllowedError,
        )

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='crew',
            tenant_key_alias='test',
        )

        with pytest.raises(RoleNotAllowedError) as exc_info:
            check_role_allowed(ctx, {'captain', 'manager'})

        assert exc_info.value.status_code == 403

    def test_empty_roles_allows_all(self):
        """Empty required_roles allows all."""
        from middleware.action_security import ActionContext, check_role_allowed

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='yacht-456',
            role='guest',
            tenant_key_alias='test',
        )

        # Empty set = no restriction
        check_role_allowed(ctx, set())


class TestIdempotencyCheck:
    """Test idempotency enforcement."""

    def test_read_no_idempotency_required(self):
        """READ actions don't require idempotency."""
        from middleware.action_security import ActionGroup, check_idempotency_key

        result = check_idempotency_key(None, "read_action", ActionGroup.READ)
        assert result is None

    def test_mutate_requires_idempotency(self):
        """MUTATE actions require idempotency."""
        from middleware.action_security import (
            ActionGroup,
            check_idempotency_key,
            IdempotencyRequiredError,
        )

        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(None, "mutate_action", ActionGroup.MUTATE)

    def test_admin_requires_idempotency(self):
        """ADMIN actions require idempotency."""
        from middleware.action_security import (
            ActionGroup,
            check_idempotency_key,
            IdempotencyRequiredError,
        )

        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(None, "admin_action", ActionGroup.ADMIN)

    def test_valid_idempotency_key_passes(self):
        """Valid idempotency key passes."""
        from middleware.action_security import ActionGroup, check_idempotency_key

        key = "valid-idempotency-key-12345"
        result = check_idempotency_key(key, "mutate_action", ActionGroup.MUTATE)
        assert result == key


class TestErrorClasses:
    """Test error class behavior."""

    def test_ownership_error_404(self):
        """OwnershipValidationError returns 404."""
        from middleware.action_security import OwnershipValidationError

        error = OwnershipValidationError("fault", "fault-123")

        assert error.status_code == 404
        assert error.code == "NOT_FOUND"
        # Entity ID should NOT be in message
        assert "fault-123" not in error.message

    def test_yacht_frozen_error_403(self):
        """YachtFrozenError returns 403."""
        from middleware.action_security import YachtFrozenError

        error = YachtFrozenError("yacht-123")
        assert error.status_code == 403

    def test_role_not_allowed_403(self):
        """RoleNotAllowedError returns 403."""
        from middleware.action_security import RoleNotAllowedError

        error = RoleNotAllowedError("crew", ["captain", "manager"])
        assert error.status_code == 403

    def test_idempotency_required_400(self):
        """IdempotencyRequiredError returns 400."""
        from middleware.action_security import IdempotencyRequiredError

        error = IdempotencyRequiredError("test_action")
        assert error.status_code == 400


class TestPayloadHashComputation:
    """Test payload hash for audit."""

    def test_deterministic_hash(self):
        """Same payload = same hash."""
        from middleware.action_security import compute_payload_hash

        payload = {"a": 1, "b": 2}

        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)

        assert hash1 == hash2

    def test_excludes_sensitive_keys(self):
        """Sensitive keys excluded from hash."""
        from middleware.action_security import compute_payload_hash

        payload1 = {"data": "test", "password": "secret1"}
        payload2 = {"data": "test", "password": "secret2"}

        # Hashes should match since password is excluded
        assert compute_payload_hash(payload1) == compute_payload_hash(payload2)


class TestErrorResponseMapping:
    """Test error to response mapping."""

    def test_maps_security_error(self):
        """ActionSecurityError maps correctly."""
        from middleware.action_security import (
            ActionSecurityError,
            map_security_error_to_response,
        )

        error = ActionSecurityError("TEST", "Test message", 400)
        response = map_security_error_to_response(error)

        assert response['error'] is True
        assert response['code'] == "TEST"
        assert response['status_code'] == 400

    def test_maps_unknown_error_to_500(self):
        """Unknown errors map to 500."""
        from middleware.action_security import map_security_error_to_response

        response = map_security_error_to_response(ValueError("oops"))

        assert response['status_code'] == 500
        assert "oops" not in response['message']  # Don't leak


class TestCrossYachtAttackPrevention:
    """Fuzz tests for cross-yacht attack prevention."""

    @pytest.fixture
    def random_yacht_ids(self):
        """Generate random yacht IDs for fuzz testing."""
        return [str(uuid.uuid4()) for _ in range(5)]

    def test_yacht_id_injection_blocked(self, random_yacht_ids):
        """Payload yacht_id should be ignored."""
        from middleware.action_security import ActionContext, inject_yacht_context

        ctx = ActionContext(
            user_id='user-123',
            yacht_id='correct-yacht-id',
            role='captain',
            tenant_key_alias='test',
        )

        for attacker_yacht_id in random_yacht_ids:
            params = {
                'yacht_id': attacker_yacht_id,
                'other_param': 'value',
            }

            result = inject_yacht_context(params, ctx)

            # yacht_id MUST come from ctx
            assert result['yacht_id'] == 'correct-yacht-id'
            assert result['yacht_id'] != attacker_yacht_id


# Run with: pytest tests/test_action_security.py -v
