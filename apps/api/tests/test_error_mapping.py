"""
CelesteOS API - Error Mapping Tests
====================================

Tests for standardized error mapping in middleware/action_security.py

Security invariants tested:
1. Ownership errors return 404 (not 403) to prevent enumeration
2. Error messages don't reveal implementation details
3. All error codes have consistent HTTP status mapping
4. Audit entries are properly built for all outcomes
"""

import pytest
from unittest.mock import MagicMock
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


class TestSecurityErrorClasses:
    """Test security error classes."""

    def test_action_security_error_base(self):
        """ActionSecurityError has code, message, status_code."""
        from middleware.action_security import ActionSecurityError

        error = ActionSecurityError("TEST_ERROR", "Test message", 400)

        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.status_code == 400
        assert str(error) == "Test message"

    def test_yacht_frozen_error(self):
        """YachtFrozenError returns 403."""
        from middleware.action_security import YachtFrozenError

        error = YachtFrozenError("yacht-123")

        assert error.code == "YACHT_FROZEN"
        assert error.status_code == 403
        assert error.yacht_id == "yacht-123"

    def test_role_not_allowed_error(self):
        """RoleNotAllowedError returns 403."""
        from middleware.action_security import RoleNotAllowedError

        error = RoleNotAllowedError("crew", ["captain", "manager"])

        assert error.code == "ROLE_NOT_ALLOWED"
        assert error.status_code == 403
        assert "crew" in error.message
        assert "captain" in error.message

    def test_idempotency_required_error(self):
        """IdempotencyRequiredError returns 400."""
        from middleware.action_security import IdempotencyRequiredError

        error = IdempotencyRequiredError("update_fault")

        assert error.code == "IDEMPOTENCY_REQUIRED"
        assert error.status_code == 400
        assert "update_fault" in error.message

    def test_ownership_validation_error_returns_404(self):
        """OwnershipValidationError MUST return 404 (prevents enumeration)."""
        from middleware.action_security import OwnershipValidationError

        error = OwnershipValidationError("fault", "fault-123-uuid")

        assert error.code == "NOT_FOUND"
        assert error.status_code == 404
        # Message should NOT include entity ID
        assert "fault-123-uuid" not in error.message
        assert "fault" in error.message.lower()

    def test_membership_inactive_error(self):
        """MembershipInactiveError returns 403."""
        from middleware.action_security import MembershipInactiveError

        error = MembershipInactiveError("user-123", "REVOKED")

        assert error.code == "MEMBERSHIP_INACTIVE"
        assert error.status_code == 403
        assert error.membership_status == "REVOKED"

    def test_payload_validation_error(self):
        """PayloadValidationError returns 400."""
        from middleware.action_security import PayloadValidationError

        error = PayloadValidationError("email", "Invalid format")

        assert error.code == "VALIDATION_ERROR"
        assert error.status_code == 400
        assert error.field == "email"

    def test_step_up_required_error(self):
        """StepUpRequiredError returns 403."""
        from middleware.action_security import StepUpRequiredError

        error = StepUpRequiredError("delete_document")

        assert error.code == "STEP_UP_REQUIRED"
        assert error.status_code == 403

    def test_signature_required_error(self):
        """SignatureRequiredError returns 400."""
        from middleware.action_security import SignatureRequiredError

        error = SignatureRequiredError("delete_document")

        assert error.code == "SIGNATURE_REQUIRED"
        assert error.status_code == 400


class TestErrorResponseMapping:
    """Test error to response mapping."""

    def test_maps_action_security_error(self):
        """ActionSecurityError is properly mapped."""
        from middleware.action_security import (
            ActionSecurityError,
            map_security_error_to_response,
        )

        error = ActionSecurityError("TEST_CODE", "Test message", 400)
        response = map_security_error_to_response(error)

        assert response['error'] is True
        assert response['code'] == "TEST_CODE"
        assert response['message'] == "Test message"
        assert response['status_code'] == 400

    def test_maps_yacht_frozen_error(self):
        """YachtFrozenError is properly mapped."""
        from middleware.action_security import (
            YachtFrozenError,
            map_security_error_to_response,
        )

        error = YachtFrozenError("yacht-123")
        response = map_security_error_to_response(error)

        assert response['code'] == "YACHT_FROZEN"
        assert response['status_code'] == 403

    def test_maps_unknown_error_to_500(self):
        """Unknown errors are mapped to 500."""
        from middleware.action_security import map_security_error_to_response

        error = ValueError("Something went wrong")
        response = map_security_error_to_response(error)

        assert response['code'] == "INTERNAL_ERROR"
        assert response['status_code'] == 500
        # Should NOT include original error message
        assert "Something went wrong" not in response['message']


class TestStandardErrorCodes:
    """Test standard error code mapping."""

    def test_standard_error_codes_exist(self):
        """Standard error codes are defined."""
        from middleware.action_security import get_standard_error_codes

        codes = get_standard_error_codes()

        required_codes = [
            "VALIDATION_ERROR",
            "IDEMPOTENCY_REQUIRED",
            "YACHT_FROZEN",
            "ROLE_NOT_ALLOWED",
            "MEMBERSHIP_INACTIVE",
            "NOT_FOUND",
            "INTERNAL_ERROR",
        ]

        for code in required_codes:
            assert code in codes
            assert 'status_code' in codes[code]
            assert 'message' in codes[code]

    def test_ownership_errors_are_404(self):
        """Ownership errors (NOT_FOUND) must be 404."""
        from middleware.action_security import get_standard_error_codes

        codes = get_standard_error_codes()

        assert codes["NOT_FOUND"]["status_code"] == 404

    def test_permission_errors_are_403(self):
        """Permission errors must be 403."""
        from middleware.action_security import get_standard_error_codes

        codes = get_standard_error_codes()

        permission_codes = ["YACHT_FROZEN", "ROLE_NOT_ALLOWED", "MEMBERSHIP_INACTIVE", "PERMISSION_DENIED"]

        for code in permission_codes:
            assert codes[code]["status_code"] == 403

    def test_validation_errors_are_400(self):
        """Validation errors must be 400."""
        from middleware.action_security import get_standard_error_codes

        codes = get_standard_error_codes()

        validation_codes = ["VALIDATION_ERROR", "IDEMPOTENCY_REQUIRED", "INVALID_PAYLOAD"]

        for code in validation_codes:
            assert codes[code]["status_code"] == 400


class TestAuditEntryBuilder:
    """Test audit entry building."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock ActionContext."""
        from middleware.action_security import ActionContext

        return ActionContext(
            user_id="user-123-uuid",
            yacht_id="yacht-456-uuid",
            role="captain",
            tenant_key_alias="test_yacht",
            request_id="req-789",
            idempotency_key="idem-abc",
        )

    def test_build_audit_entry_allowed(self, mock_ctx):
        """Audit entry for allowed action."""
        from middleware.action_security import build_audit_entry

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="update_fault",
            entity_type="fault",
            entity_id="fault-123",
            outcome="allowed",
        )

        assert entry['yacht_id'] == mock_ctx.yacht_id
        assert entry['user_id'] == mock_ctx.user_id
        assert entry['action'] == "update_fault"
        assert entry['entity_type'] == "fault"
        assert entry['entity_id'] == "fault-123"
        assert entry['metadata']['outcome'] == "allowed"
        assert entry['metadata']['role'] == "captain"
        assert entry['metadata']['request_id'] == "req-789"
        assert entry['metadata']['idempotency_key'] == "idem-abc"

    def test_build_audit_entry_denied(self, mock_ctx):
        """Audit entry for denied action."""
        from middleware.action_security import build_audit_entry

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="delete_document",
            entity_type="document",
            entity_id="doc-456",
            outcome="denied",
        )

        assert entry['metadata']['outcome'] == "denied"

    def test_build_audit_entry_error(self, mock_ctx):
        """Audit entry for error action."""
        from middleware.action_security import build_audit_entry

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="create_fault",
            entity_type="fault",
            entity_id=None,
            outcome="error",
        )

        assert entry['metadata']['outcome'] == "error"

    def test_audit_entry_signature_never_none(self, mock_ctx):
        """Signature in audit entry is never None (invariant)."""
        from middleware.action_security import build_audit_entry

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="signed_action",
            entity_type="document",
            entity_id="doc-123",
            signature=None,  # Explicitly pass None
        )

        # Signature should be {} not None
        assert entry['signature'] is not None
        assert entry['signature'] == {}

    def test_audit_entry_includes_payload_hash(self, mock_ctx):
        """Audit entry includes payload hash (not raw payload)."""
        from middleware.action_security import build_audit_entry

        payload = {
            "title": "Test Fault",
            "description": "Some description",
            "sensitive_data": "should_not_appear",
        }

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="create_fault",
            entity_type="fault",
            entity_id="fault-new",
            payload=payload,
        )

        # Should have hash, not raw payload
        assert 'payload_hash' in entry['metadata']
        assert entry['metadata']['payload_hash'] is not None
        assert "Test Fault" not in str(entry['metadata'])  # Raw data not in metadata

    def test_audit_entry_includes_affected_records(self, mock_ctx):
        """Audit entry includes affected record IDs."""
        from middleware.action_security import build_audit_entry

        entry = build_audit_entry(
            ctx=mock_ctx,
            action="batch_update",
            entity_type="fault",
            entity_id="batch",
            affected_record_ids=["fault-1", "fault-2", "fault-3"],
        )

        assert entry['metadata']['affected_record_ids'] == ["fault-1", "fault-2", "fault-3"]


class TestPayloadHashComputation:
    """Test payload hash computation."""

    def test_compute_payload_hash_deterministic(self):
        """Same payload produces same hash."""
        from middleware.action_security import compute_payload_hash

        payload = {"field_a": "value1", "field_b": "value2"}

        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)

        assert hash1 == hash2

    def test_compute_payload_hash_excludes_sensitive(self):
        """Sensitive fields are excluded from hash."""
        from middleware.action_security import compute_payload_hash

        payload1 = {"title": "Test", "password": "secret123"}
        payload2 = {"title": "Test", "password": "different_secret"}

        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)

        # Hashes should be same since password is excluded
        assert hash1 == hash2

    def test_compute_payload_hash_excludes_signature(self):
        """Signature field is excluded from hash."""
        from middleware.action_security import compute_payload_hash

        payload1 = {"action": "test", "signature": "sig_abc"}
        payload2 = {"action": "test", "signature": "sig_xyz"}

        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)

        assert hash1 == hash2


class TestEnumerationPrevention:
    """Test that error handling prevents enumeration attacks."""

    def test_ownership_error_hides_entity_id(self):
        """OwnershipValidationError does not expose entity ID."""
        from middleware.action_security import (
            OwnershipValidationError,
            map_security_error_to_response,
        )

        error = OwnershipValidationError("document", "doc-12345-secret-uuid")
        response = map_security_error_to_response(error)

        # Response should not contain the entity ID
        assert "doc-12345-secret-uuid" not in response['message']
        assert "doc-12345-secret-uuid" not in str(response)

    def test_ownership_error_same_message_different_ids(self):
        """Different entity IDs produce same error message."""
        from middleware.action_security import OwnershipValidationError

        error1 = OwnershipValidationError("fault", "fault-aaa")
        error2 = OwnershipValidationError("fault", "fault-bbb")

        # Same message prevents enumeration
        assert error1.message == error2.message
        assert error1.status_code == error2.status_code


# Run with: pytest tests/test_error_mapping.py -v
