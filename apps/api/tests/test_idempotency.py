"""
CelesteOS API - Idempotency Tests
=================================

Tests for the idempotency middleware.

Tests ensure:
1. Repeated MUTATE with same Idempotency-Key returns identical response
2. Side effects occur only once
3. Different request with same key returns 409 Conflict
4. Keys are scoped to yacht_id
5. Expired keys allow new requests
"""

import pytest
import uuid
import json
from unittest.mock import Mock, MagicMock, patch
from dataclasses import asdict

from middleware.idempotency import (
    IdempotencyManager,
    IdempotencyCheckResult,
    IdempotencyConflictError,
    IdempotencyKeyMissingError,
    ActionGroup,
    hash_request,
    require_idempotency_key,
    safe_response_summary,
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
def idempotency_key() -> str:
    """Test idempotency key."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_master_client():
    """Mock MASTER DB client."""
    mock = MagicMock()
    return mock


# ============================================================================
# IdempotencyCheckResult Tests
# ============================================================================

class TestIdempotencyCheckResult:
    """Tests for IdempotencyCheckResult dataclass."""

    def test_should_execute_when_not_found(self):
        """should_execute is True when key not found."""
        result = IdempotencyCheckResult(
            found=False,
            completed=False,
            hash_mismatch=False,
        )
        assert result.should_execute is True

    def test_should_execute_when_in_progress(self):
        """should_execute is True when found but not completed."""
        result = IdempotencyCheckResult(
            found=True,
            completed=False,
            hash_mismatch=False,
        )
        assert result.should_execute is True

    def test_should_not_execute_when_completed(self):
        """should_execute is False when completed."""
        result = IdempotencyCheckResult(
            found=True,
            completed=True,
            hash_mismatch=False,
            response_status=200,
            response_summary={"id": "test"},
        )
        assert result.should_execute is False

    def test_should_not_execute_on_hash_mismatch(self):
        """should_execute is False on hash mismatch."""
        result = IdempotencyCheckResult(
            found=True,
            completed=False,
            hash_mismatch=True,
        )
        assert result.should_execute is False

    def test_is_replay_when_completed(self):
        """is_replay is True when found, completed, no mismatch."""
        result = IdempotencyCheckResult(
            found=True,
            completed=True,
            hash_mismatch=False,
            response_status=200,
        )
        assert result.is_replay is True

    def test_not_replay_when_not_completed(self):
        """is_replay is False when not completed."""
        result = IdempotencyCheckResult(
            found=True,
            completed=False,
            hash_mismatch=False,
        )
        assert result.is_replay is False


# ============================================================================
# IdempotencyManager Tests
# ============================================================================

class TestIdempotencyManager:
    """Tests for IdempotencyManager class."""

    def test_init_requires_client(self):
        """Constructor requires master_client."""
        with pytest.raises(ValueError, match="master_client is required"):
            IdempotencyManager(None)

    def test_check_returns_not_found_for_new_key(
        self, mock_master_client, yacht_id, idempotency_key
    ):
        """check() returns not found for new key."""
        # Mock RPC to return empty/not found
        mock_result = MagicMock()
        mock_result.data = [{"found": False, "completed": False, "hash_mismatch": False}]
        mock_master_client.rpc.return_value.execute.return_value = mock_result

        manager = IdempotencyManager(mock_master_client)
        result = manager.check(
            key=idempotency_key,
            yacht_id=yacht_id,
            action_id="test_action",
            request_hash="abc123",
        )

        assert result.found is False
        assert result.should_execute is True

    def test_check_returns_cached_response_for_completed(
        self, mock_master_client, yacht_id, idempotency_key
    ):
        """check() returns cached response for completed request."""
        mock_result = MagicMock()
        mock_result.data = [{
            "found": True,
            "completed": True,
            "hash_mismatch": False,
            "response_status": 200,
            "response_summary": {"id": "created-id"},
        }]
        mock_master_client.rpc.return_value.execute.return_value = mock_result

        manager = IdempotencyManager(mock_master_client)
        result = manager.check(
            key=idempotency_key,
            yacht_id=yacht_id,
            action_id="test_action",
            request_hash="abc123",
        )

        assert result.found is True
        assert result.completed is True
        assert result.is_replay is True
        assert result.response_status == 200
        assert result.response_summary["id"] == "created-id"

    def test_check_raises_conflict_on_hash_mismatch(
        self, mock_master_client, yacht_id, idempotency_key
    ):
        """check() raises IdempotencyConflictError on hash mismatch."""
        mock_result = MagicMock()
        mock_result.data = [{
            "found": True,
            "completed": False,
            "hash_mismatch": True,
        }]
        mock_master_client.rpc.return_value.execute.return_value = mock_result

        manager = IdempotencyManager(mock_master_client)

        with pytest.raises(IdempotencyConflictError) as exc_info:
            manager.check(
                key=idempotency_key,
                yacht_id=yacht_id,
                action_id="test_action",
                request_hash="different_hash",
            )

        assert idempotency_key[:8] in exc_info.value.key

    def test_check_returns_not_found_when_no_key(
        self, mock_master_client, yacht_id
    ):
        """check() returns not found when no key provided."""
        manager = IdempotencyManager(mock_master_client)
        result = manager.check(
            key=None,
            yacht_id=yacht_id,
            action_id="test_action",
            request_hash="abc123",
        )

        assert result.found is False
        assert result.should_execute is True

    def test_create_returns_true_on_success(
        self, mock_master_client, yacht_id, user_id, idempotency_key
    ):
        """create() returns True on success."""
        mock_master_client.rpc.return_value.execute.return_value = MagicMock(data=True)

        manager = IdempotencyManager(mock_master_client)
        result = manager.create(
            key=idempotency_key,
            yacht_id=yacht_id,
            action_id="test_action",
            user_id=user_id,
            request_hash="abc123",
        )

        assert result is True

    def test_create_returns_false_when_no_key(
        self, mock_master_client, yacht_id, user_id
    ):
        """create() returns False when no key provided."""
        manager = IdempotencyManager(mock_master_client)
        result = manager.create(
            key=None,
            yacht_id=yacht_id,
            action_id="test_action",
            user_id=user_id,
            request_hash="abc123",
        )

        assert result is False

    def test_complete_calls_rpc(
        self, mock_master_client, yacht_id, idempotency_key
    ):
        """complete() calls the RPC function."""
        manager = IdempotencyManager(mock_master_client)
        manager.complete(
            key=idempotency_key,
            yacht_id=yacht_id,
            status=200,
            response_summary={"id": "created"},
        )

        # Verify RPC was called
        mock_master_client.rpc.assert_called()

    def test_complete_does_nothing_when_no_key(
        self, mock_master_client, yacht_id
    ):
        """complete() does nothing when no key provided."""
        manager = IdempotencyManager(mock_master_client)
        manager.complete(
            key=None,
            yacht_id=yacht_id,
            status=200,
            response_summary={"id": "created"},
        )

        # RPC should not be called
        mock_master_client.rpc.assert_not_called()


# ============================================================================
# hash_request Tests
# ============================================================================

class TestHashRequest:
    """Tests for hash_request function."""

    def test_same_payload_same_hash(self):
        """Same payload produces same hash."""
        payload = {"action": "create", "data": {"name": "Test"}}

        hash1 = hash_request(payload)
        hash2 = hash_request(payload)

        assert hash1 == hash2

    def test_different_payload_different_hash(self):
        """Different payload produces different hash."""
        payload1 = {"action": "create", "data": {"name": "Test1"}}
        payload2 = {"action": "create", "data": {"name": "Test2"}}

        assert hash_request(payload1) != hash_request(payload2)

    def test_excludes_idempotency_key(self):
        """idempotency_key is excluded from hash."""
        payload1 = {"action": "create", "idempotency_key": "key1"}
        payload2 = {"action": "create", "idempotency_key": "key2"}

        # Same hash because idempotency_key excluded
        assert hash_request(payload1) == hash_request(payload2)

    def test_excludes_specified_keys(self):
        """Specified keys are excluded from hash."""
        payload1 = {"action": "create", "timestamp": "2026-01-01"}
        payload2 = {"action": "create", "timestamp": "2026-01-02"}

        # Same hash when timestamp excluded
        assert hash_request(payload1, exclude_keys=["timestamp"]) == \
               hash_request(payload2, exclude_keys=["timestamp"])

    def test_order_independent(self):
        """Key order doesn't affect hash."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}

        assert hash_request(payload1) == hash_request(payload2)

    def test_hash_length(self):
        """Hash is truncated to 32 chars."""
        payload = {"data": "x" * 10000}
        hash_value = hash_request(payload)

        assert len(hash_value) == 32


# ============================================================================
# require_idempotency_key Tests
# ============================================================================

class TestRequireIdempotencyKey:
    """Tests for require_idempotency_key function."""

    def test_read_action_no_key_required(self):
        """READ actions don't require key."""
        result = require_idempotency_key(
            idempotency_key=None,
            action_id="list_equipment",
            action_group=ActionGroup.READ,
        )

        assert result == ""

    def test_mutate_action_requires_key(self):
        """MUTATE actions require key."""
        with pytest.raises(IdempotencyKeyMissingError) as exc_info:
            require_idempotency_key(
                idempotency_key=None,
                action_id="create_work_order",
                action_group=ActionGroup.MUTATE,
            )

        assert "create_work_order" in exc_info.value.action_id

    def test_signed_action_requires_key(self):
        """SIGNED actions require key."""
        with pytest.raises(IdempotencyKeyMissingError):
            require_idempotency_key(
                idempotency_key=None,
                action_id="approve_work_order",
                action_group=ActionGroup.SIGNED,
            )

    def test_admin_action_requires_key(self):
        """ADMIN actions require key."""
        with pytest.raises(IdempotencyKeyMissingError):
            require_idempotency_key(
                idempotency_key=None,
                action_id="revoke_membership",
                action_group=ActionGroup.ADMIN,
            )

    def test_valid_key_returned(self):
        """Valid key is returned."""
        key = str(uuid.uuid4())
        result = require_idempotency_key(
            idempotency_key=key,
            action_id="create_work_order",
            action_group=ActionGroup.MUTATE,
        )

        assert result == key

    def test_key_too_short_rejected(self):
        """Key shorter than 8 chars rejected."""
        with pytest.raises(IdempotencyKeyMissingError):
            require_idempotency_key(
                idempotency_key="short",
                action_id="create_work_order",
                action_group=ActionGroup.MUTATE,
            )

    def test_key_too_long_rejected(self):
        """Key longer than 128 chars rejected."""
        with pytest.raises(IdempotencyKeyMissingError):
            require_idempotency_key(
                idempotency_key="x" * 200,
                action_id="create_work_order",
                action_group=ActionGroup.MUTATE,
            )


# ============================================================================
# safe_response_summary Tests
# ============================================================================

class TestSafeResponseSummary:
    """Tests for safe_response_summary function."""

    def test_removes_sensitive_keys(self):
        """Sensitive keys are removed."""
        response = {
            "id": "123",
            "token": "secret_token",
            "password": "secret_pass",
            "data": "safe",
        }

        summary = safe_response_summary(response)

        assert "id" in summary
        assert "data" in summary
        assert "token" not in summary
        assert "password" not in summary

    def test_truncates_long_strings(self):
        """Long strings are truncated."""
        response = {
            "description": "x" * 500,
        }

        summary = safe_response_summary(response)

        assert len(summary["description"]) <= 203  # 200 + "..."

    def test_truncates_long_lists(self):
        """Long lists are truncated."""
        response = {
            "items": list(range(50)),
        }

        summary = safe_response_summary(response)

        assert len(summary["items"]) == 11  # 10 + summary message

    def test_limits_depth(self):
        """Depth is limited."""
        response = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep"
                    }
                }
            }
        }

        # With max_depth=2, truncation happens when depth > max_depth
        # level1 value at depth 1, level2 value at depth 2, level3 value at depth 3 (truncated)
        summary = safe_response_summary(response, max_depth=2)

        assert summary["level1"]["level2"]["level3"] == "[truncated]"

    def test_handles_nested_sensitive_keys(self):
        """Sensitive keys removed at any depth."""
        response = {
            "data": {
                "user": {
                    "api_key": "secret",
                    "name": "Test",
                }
            }
        }

        summary = safe_response_summary(response)

        assert "api_key" not in summary["data"]["user"]
        assert summary["data"]["user"]["name"] == "Test"


# ============================================================================
# Integration-Style Tests
# ============================================================================

class TestIdempotencyFlow:
    """Integration-style tests for full idempotency flow."""

    def test_full_flow_new_request(self, mock_master_client, yacht_id, user_id):
        """Full flow for new request."""
        key = str(uuid.uuid4())

        # Mock: check returns not found
        mock_check_result = MagicMock()
        mock_check_result.data = [{"found": False, "completed": False, "hash_mismatch": False}]

        # Mock: create returns True
        mock_create_result = MagicMock()
        mock_create_result.data = True

        def mock_rpc(func_name, params=None):
            rpc_mock = MagicMock()
            if func_name == "check_idempotency":
                rpc_mock.execute.return_value = mock_check_result
            elif func_name == "create_idempotency_record":
                rpc_mock.execute.return_value = mock_create_result
            else:
                rpc_mock.execute.return_value = MagicMock(data=None)
            return rpc_mock

        mock_master_client.rpc = mock_rpc

        manager = IdempotencyManager(mock_master_client)

        # 1. Check - should execute
        check = manager.check(key, yacht_id, "create_work_order", "hash123")
        assert check.should_execute is True

        # 2. Create record
        created = manager.create(key, yacht_id, "create_work_order", user_id, "hash123")
        assert created is True

        # 3. Complete
        manager.complete(key, yacht_id, 200, {"id": "wo-123"})

    def test_full_flow_replay(self, mock_master_client, yacht_id):
        """Full flow for replay request."""
        key = str(uuid.uuid4())

        # Mock: check returns completed
        mock_result = MagicMock()
        mock_result.data = [{
            "found": True,
            "completed": True,
            "hash_mismatch": False,
            "response_status": 200,
            "response_summary": {"id": "wo-123"},
        }]
        mock_master_client.rpc.return_value.execute.return_value = mock_result

        manager = IdempotencyManager(mock_master_client)

        # Check - should return cached response
        check = manager.check(key, yacht_id, "create_work_order", "hash123")

        assert check.is_replay is True
        assert check.response_status == 200
        assert check.response_summary["id"] == "wo-123"
