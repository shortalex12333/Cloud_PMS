"""
CelesteOS API - Action Security Middleware Tests
=================================================

Tests for the action security middleware.

Tests ensure:
1. Yacht freeze blocks MUTATE/SIGNED/ADMIN actions
2. Role validation works correctly
3. Idempotency key validation works
4. Entity ownership validation integrates correctly
5. Context injection works (yacht_id from ctx, not payload)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from middleware.action_security import (
    ActionContext,
    ActionGroup,
    ActionSecurityError,
    YachtFrozenError,
    RoleNotAllowedError,
    IdempotencyRequiredError,
    secure_action,
    create_action_context,
    check_yacht_not_frozen,
    check_role_allowed,
    check_idempotency_key,
    inject_yacht_context,
    build_audit_entry,
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
    """Test user UUID."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def auth_dict(yacht_id, user_id) -> Dict[str, Any]:
    """Standard auth dict from get_authenticated_user."""
    return {
        'user_id': user_id,
        'yacht_id': yacht_id,
        'role': 'chief_engineer',
        'tenant_key_alias': f'y{yacht_id}',
        'email': 'test@example.com',
        'yacht_name': 'M/Y Test',
        'membership_id': 'mem-123',
        'membership_status': 'ACTIVE',
        'is_frozen': False,
    }


@pytest.fixture
def frozen_auth_dict(auth_dict) -> Dict[str, Any]:
    """Auth dict with frozen yacht."""
    return {**auth_dict, 'is_frozen': True}


@pytest.fixture
def ctx(auth_dict) -> ActionContext:
    """Standard ActionContext."""
    return create_action_context(auth_dict)


@pytest.fixture
def frozen_ctx(frozen_auth_dict) -> ActionContext:
    """ActionContext with frozen yacht."""
    return create_action_context(frozen_auth_dict)


# ============================================================================
# ActionContext Tests
# ============================================================================

class TestActionContext:
    """Tests for ActionContext creation."""

    def test_create_from_auth_dict(self, auth_dict):
        """Creates context from auth dict."""
        ctx = create_action_context(auth_dict)

        assert ctx.user_id == auth_dict['user_id']
        assert ctx.yacht_id == auth_dict['yacht_id']
        assert ctx.role == auth_dict['role']
        assert ctx.tenant_key_alias == auth_dict['tenant_key_alias']
        assert ctx.is_frozen is False

    def test_create_with_idempotency_key(self, auth_dict):
        """Creates context with idempotency key."""
        key = "idem-key-12345678"
        ctx = create_action_context(auth_dict, idempotency_key=key)

        assert ctx.idempotency_key == key

    def test_to_dict_excludes_sensitive(self, auth_dict):
        """to_dict excludes sensitive fields."""
        ctx = create_action_context(auth_dict)
        d = ctx.to_dict()

        assert 'yacht_id' in d
        assert 'role' in d
        assert 'email' not in d  # Not included by default

    def test_frozen_flag_preserved(self, frozen_auth_dict):
        """Frozen flag is preserved in context."""
        ctx = create_action_context(frozen_auth_dict)

        assert ctx.is_frozen is True


# ============================================================================
# Yacht Freeze Tests
# ============================================================================

class TestCheckYachtNotFrozen:
    """Tests for yacht freeze checking."""

    def test_read_allowed_when_frozen(self, frozen_ctx):
        """READ actions allowed when yacht frozen."""
        # Should not raise
        check_yacht_not_frozen(frozen_ctx, ActionGroup.READ)

    def test_mutate_blocked_when_frozen(self, frozen_ctx):
        """MUTATE actions blocked when yacht frozen."""
        with pytest.raises(YachtFrozenError) as exc_info:
            check_yacht_not_frozen(frozen_ctx, ActionGroup.MUTATE)

        assert exc_info.value.status_code == 403
        assert "frozen" in exc_info.value.message.lower()

    def test_signed_blocked_when_frozen(self, frozen_ctx):
        """SIGNED actions blocked when yacht frozen."""
        with pytest.raises(YachtFrozenError):
            check_yacht_not_frozen(frozen_ctx, ActionGroup.SIGNED)

    def test_admin_blocked_when_frozen(self, frozen_ctx):
        """ADMIN actions blocked when yacht frozen."""
        with pytest.raises(YachtFrozenError):
            check_yacht_not_frozen(frozen_ctx, ActionGroup.ADMIN)

    def test_mutate_allowed_when_not_frozen(self, ctx):
        """MUTATE actions allowed when yacht not frozen."""
        # Should not raise
        check_yacht_not_frozen(ctx, ActionGroup.MUTATE)


# ============================================================================
# Role Validation Tests
# ============================================================================

class TestCheckRoleAllowed:
    """Tests for role validation."""

    def test_role_allowed_in_set(self, ctx):
        """Role in allowed set passes."""
        allowed = {"chief_engineer", "captain", "manager"}
        # Should not raise
        check_role_allowed(ctx, allowed)

    def test_role_not_in_set_raises(self, ctx):
        """Role not in allowed set raises error."""
        allowed = {"captain", "manager"}

        with pytest.raises(RoleNotAllowedError) as exc_info:
            check_role_allowed(ctx, allowed)

        assert exc_info.value.status_code == 403
        assert "chief_engineer" in exc_info.value.message

    def test_empty_allowed_set_passes(self, ctx):
        """Empty allowed set means all roles allowed."""
        # Should not raise
        check_role_allowed(ctx, set())

    def test_crew_role_denied_for_hod_action(self, auth_dict):
        """Crew role denied for HOD-only action."""
        auth_dict['role'] = 'crew'
        ctx = create_action_context(auth_dict)

        with pytest.raises(RoleNotAllowedError):
            check_role_allowed(ctx, {"hod", "captain", "manager"})


# ============================================================================
# Idempotency Key Tests
# ============================================================================

class TestCheckIdempotencyKey:
    """Tests for idempotency key validation."""

    def test_read_action_no_key_required(self):
        """READ actions don't require idempotency key."""
        result = check_idempotency_key(
            idempotency_key=None,
            action_id="list_faults",
            action_group=ActionGroup.READ,
        )

        assert result is None

    def test_mutate_action_requires_key(self):
        """MUTATE actions require idempotency key."""
        with pytest.raises(IdempotencyRequiredError) as exc_info:
            check_idempotency_key(
                idempotency_key=None,
                action_id="create_fault",
                action_group=ActionGroup.MUTATE,
            )

        assert exc_info.value.status_code == 400
        assert "create_fault" in exc_info.value.message

    def test_signed_action_requires_key(self):
        """SIGNED actions require idempotency key."""
        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(
                idempotency_key=None,
                action_id="approve_wo",
                action_group=ActionGroup.SIGNED,
            )

    def test_admin_action_requires_key(self):
        """ADMIN actions require idempotency key."""
        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(
                idempotency_key=None,
                action_id="revoke_user",
                action_group=ActionGroup.ADMIN,
            )

    def test_valid_key_returned(self):
        """Valid key is returned."""
        key = "12345678-1234-1234-1234-123456789012"
        result = check_idempotency_key(
            idempotency_key=key,
            action_id="create_fault",
            action_group=ActionGroup.MUTATE,
        )

        assert result == key

    def test_key_too_short_rejected(self):
        """Key shorter than 8 chars rejected."""
        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(
                idempotency_key="short",
                action_id="create_fault",
                action_group=ActionGroup.MUTATE,
            )

    def test_key_too_long_rejected(self):
        """Key longer than 128 chars rejected."""
        with pytest.raises(IdempotencyRequiredError):
            check_idempotency_key(
                idempotency_key="x" * 200,
                action_id="create_fault",
                action_group=ActionGroup.MUTATE,
            )


# ============================================================================
# Context Injection Tests
# ============================================================================

class TestInjectYachtContext:
    """Tests for yacht context injection."""

    def test_injects_yacht_id_from_context(self, ctx):
        """yacht_id is injected from context."""
        params = {"title": "Test", "severity": "minor"}
        result = inject_yacht_context(params, ctx)

        assert result["yacht_id"] == ctx.yacht_id
        assert result["title"] == "Test"

    def test_overwrites_payload_yacht_id(self, ctx):
        """Payload yacht_id is overwritten by context."""
        malicious_yacht_id = "attacker-yacht-id"
        params = {"yacht_id": malicious_yacht_id, "title": "Test"}

        result = inject_yacht_context(params, ctx)

        # SECURITY: Must use ctx.yacht_id, not payload
        assert result["yacht_id"] == ctx.yacht_id
        assert result["yacht_id"] != malicious_yacht_id

    def test_injects_user_id_from_context(self, ctx):
        """user_id is injected from context."""
        params = {"title": "Test"}
        result = inject_yacht_context(params, ctx)

        assert result["user_id"] == ctx.user_id


# ============================================================================
# Audit Entry Tests
# ============================================================================

class TestBuildAuditEntry:
    """Tests for audit entry building."""

    def test_builds_complete_entry(self, ctx):
        """Builds complete audit entry."""
        entry = build_audit_entry(
            ctx=ctx,
            action="create_fault",
            entity_type="fault",
            entity_id="fault-123",
            new_values={"title": "Test"},
        )

        assert entry["yacht_id"] == ctx.yacht_id
        assert entry["user_id"] == ctx.user_id
        assert entry["action"] == "create_fault"
        assert entry["entity_type"] == "fault"
        assert entry["entity_id"] == "fault-123"
        assert entry["new_values"]["title"] == "Test"

    def test_signature_never_none(self, ctx):
        """Signature is never None in audit entry."""
        entry = build_audit_entry(
            ctx=ctx,
            action="create_fault",
            entity_type="fault",
            entity_id="fault-123",
            signature=None,
        )

        # INVARIANT: signature must be {}, never None
        assert entry["signature"] == {}
        assert entry["signature"] is not None

    def test_includes_role_in_metadata(self, ctx):
        """Role is included in metadata."""
        entry = build_audit_entry(
            ctx=ctx,
            action="create_fault",
            entity_type="fault",
            entity_id="fault-123",
        )

        assert entry["metadata"]["role"] == ctx.role

    def test_includes_idempotency_key(self, auth_dict):
        """Idempotency key is included in metadata."""
        ctx = create_action_context(auth_dict, idempotency_key="test-key-123")

        entry = build_audit_entry(
            ctx=ctx,
            action="create_fault",
            entity_type="fault",
            entity_id="fault-123",
        )

        assert entry["metadata"]["idempotency_key"] == "test-key-123"


# ============================================================================
# secure_action Decorator Tests
# ============================================================================

class TestSecureActionDecorator:
    """Tests for the secure_action decorator."""

    @pytest.mark.asyncio
    async def test_read_action_passes_without_idempotency(self, auth_dict):
        """READ action works without idempotency key."""
        mock_db = MagicMock()

        @secure_action(action_id="list_faults", action_group="READ")
        async def handler(ctx, **params):
            return {"status": "success", "yacht_id": ctx.yacht_id}

        result = await handler(mock_db, auth_dict, idempotency_key=None)

        assert result["status"] == "success"
        assert result["yacht_id"] == auth_dict["yacht_id"]

    @pytest.mark.asyncio
    async def test_mutate_requires_idempotency(self, auth_dict):
        """MUTATE action requires idempotency key."""
        mock_db = MagicMock()

        @secure_action(action_id="create_fault", action_group="MUTATE")
        async def handler(ctx, **params):
            return {"status": "success"}

        with pytest.raises(IdempotencyRequiredError):
            await handler(mock_db, auth_dict, idempotency_key=None)

    @pytest.mark.asyncio
    async def test_mutate_blocked_when_frozen(self, frozen_auth_dict):
        """MUTATE blocked when yacht frozen."""
        mock_db = MagicMock()

        @secure_action(action_id="create_fault", action_group="MUTATE")
        async def handler(ctx, **params):
            return {"status": "success"}

        with pytest.raises(YachtFrozenError):
            await handler(
                mock_db,
                frozen_auth_dict,
                idempotency_key="test-key-123456"
            )

    @pytest.mark.asyncio
    async def test_role_validation_enforced(self, auth_dict):
        """Role validation is enforced."""
        mock_db = MagicMock()
        auth_dict['role'] = 'crew'  # Not allowed

        @secure_action(
            action_id="approve_wo",
            action_group="SIGNED",
            required_roles=["captain", "manager"],
        )
        async def handler(ctx, **params):
            return {"status": "success"}

        with pytest.raises(RoleNotAllowedError):
            await handler(
                mock_db,
                auth_dict,
                idempotency_key="test-key-123456"
            )

    @pytest.mark.asyncio
    async def test_injects_yacht_id_from_context(self, auth_dict):
        """yacht_id is injected from context, not payload."""
        mock_db = MagicMock()
        captured_params = {}

        @secure_action(action_id="list_faults", action_group="READ")
        async def handler(ctx, **params):
            captured_params.update(params)
            return {"status": "success"}

        # Pass malicious yacht_id in params
        await handler(
            mock_db,
            auth_dict,
            idempotency_key=None,
            yacht_id="attacker-yacht",  # Should be overwritten
        )

        # SECURITY: yacht_id must come from auth, not params
        assert captured_params["yacht_id"] == auth_dict["yacht_id"]


# ============================================================================
# Error Classes Tests
# ============================================================================

class TestErrorClasses:
    """Tests for error classes."""

    def test_yacht_frozen_error(self):
        """YachtFrozenError has correct attributes."""
        error = YachtFrozenError("yacht-123")

        assert error.status_code == 403
        assert error.code == "YACHT_FROZEN"
        assert "frozen" in error.message.lower()

    def test_role_not_allowed_error(self):
        """RoleNotAllowedError has correct attributes."""
        error = RoleNotAllowedError("crew", ["captain", "manager"])

        assert error.status_code == 403
        assert error.code == "ROLE_NOT_ALLOWED"
        assert "crew" in error.message

    def test_idempotency_required_error(self):
        """IdempotencyRequiredError has correct attributes."""
        error = IdempotencyRequiredError("create_fault")

        assert error.status_code == 400
        assert error.code == "IDEMPOTENCY_REQUIRED"
        assert "create_fault" in error.message
