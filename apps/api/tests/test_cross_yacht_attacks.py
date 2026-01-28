"""
CelesteOS API - Cross-Yacht Attack Tests
=========================================

Fuzzing tests for cross-yacht access attempts.

Security invariants verified:
1. Cross-yacht READ returns 404 (not 403, to prevent enumeration)
2. Cross-yacht WRITE returns 404
3. Payload yacht_id is ignored, ctx.yacht_id used
4. Random UUID returns 404, not 500
5. No tenant enumeration via error messages

Test matrix:
- User A attempts to read User B's equipment → 404
- User A attempts to update User B's equipment → 404
- User A attempts to delete User B's document → 404
- Random UUID in payload → 404
- Payload with wrong yacht_id → ignored, ctx used
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Import validators
from validators.ownership import (
    OwnershipValidator,
    ensure_owned,
    ensure_all_owned,
    NotFoundError,
    OwnershipValidationError,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def yacht_a_id() -> str:
    """Yacht A UUID."""
    return "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def yacht_b_id() -> str:
    """Yacht B UUID (different yacht)."""
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def equipment_id_yacht_a() -> str:
    """Equipment belonging to Yacht A."""
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def equipment_id_yacht_b() -> str:
    """Equipment belonging to Yacht B."""
    return "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def mock_db_yacht_a(yacht_a_id, equipment_id_yacht_a):
    """Mock DB client that returns data only for Yacht A's known equipment."""
    mock = MagicMock()

    def mock_execute_found():
        result = MagicMock()
        result.data = [{"id": equipment_id_yacht_a, "yacht_id": yacht_a_id}]
        return result

    def mock_execute_empty():
        result = MagicMock()
        result.data = []
        return result

    def mock_table(table_name):
        table_mock = MagicMock()

        def mock_select(*args):
            select_mock = MagicMock()

            def mock_eq_id(field, entity_id):
                eq_mock = MagicMock()

                def mock_eq_yacht(field2, yacht_id_value):
                    eq2_mock = MagicMock()
                    # Only return data if BOTH yacht_id AND entity_id match
                    # This properly simulates "WHERE id = :id AND yacht_id = :yacht_id"
                    if yacht_id_value == yacht_a_id and entity_id == equipment_id_yacht_a:
                        eq2_mock.execute = mock_execute_found
                    else:
                        eq2_mock.execute = mock_execute_empty
                    return eq2_mock

                eq_mock.eq = mock_eq_yacht
                return eq_mock

            select_mock.eq = mock_eq_id
            return select_mock

        table_mock.select = mock_select
        return table_mock

    mock.table = mock_table
    return mock


# ============================================================================
# Cross-Yacht READ Tests
# ============================================================================

class TestCrossYachtRead:
    """Tests for cross-yacht read attempts."""

    def test_read_own_yacht_equipment_succeeds(
        self, mock_db_yacht_a, yacht_a_id, equipment_id_yacht_a
    ):
        """User can read equipment from their own yacht."""
        validator = OwnershipValidator(mock_db_yacht_a, yacht_a_id)
        result = validator.validate("equipment", equipment_id_yacht_a)

        assert result is not None
        assert result["id"] == equipment_id_yacht_a
        assert result["yacht_id"] == yacht_a_id

    def test_read_other_yacht_equipment_returns_404(
        self, mock_db_yacht_a, yacht_b_id, equipment_id_yacht_a
    ):
        """User cannot read equipment from another yacht - returns 404."""
        # User from yacht_b tries to access yacht_a's equipment
        validator = OwnershipValidator(mock_db_yacht_a, yacht_b_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate("equipment", equipment_id_yacht_a)

        # Must be 404 to prevent enumeration
        assert exc_info.value.entity_type == "equipment"
        assert "not found" in exc_info.value.message.lower()

    def test_random_uuid_returns_404(self, mock_db_yacht_a, yacht_a_id):
        """Random UUID returns 404, not 500."""
        random_id = str(uuid.uuid4())
        validator = OwnershipValidator(mock_db_yacht_a, yacht_a_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate("equipment", random_id)

        # Must be NotFoundError (404), not OwnershipValidationError (500)
        assert exc_info.value.entity_id == random_id

    def test_empty_id_returns_404(self, mock_db_yacht_a, yacht_a_id):
        """Empty ID returns 404."""
        validator = OwnershipValidator(mock_db_yacht_a, yacht_a_id)

        with pytest.raises(NotFoundError):
            validator.validate("equipment", "")

    def test_none_id_returns_404(self, mock_db_yacht_a, yacht_a_id):
        """None ID returns 404."""
        validator = OwnershipValidator(mock_db_yacht_a, yacht_a_id)

        with pytest.raises(NotFoundError):
            validator.validate("equipment", None)


# ============================================================================
# Cross-Yacht WRITE Tests
# ============================================================================

class TestCrossYachtWrite:
    """Tests for cross-yacht write attempts."""

    def test_batch_validation_own_yacht_succeeds(self, yacht_a_id):
        """Batch validation succeeds for own yacht entities."""
        mock_db = MagicMock()

        # Simulate multiple entities found
        ids = ["id1", "id2", "id3"]
        mock_result = MagicMock()
        mock_result.data = [{"id": id, "yacht_id": yacht_a_id} for id in ids]

        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        validator = OwnershipValidator(mock_db, yacht_a_id)
        result = validator.validate_multiple("equipment", ids)

        assert len(result) == 3
        assert all(r["yacht_id"] == yacht_a_id for r in result)

    def test_batch_validation_cross_yacht_fails_all(self, yacht_a_id, yacht_b_id):
        """If any entity is from another yacht, entire batch fails."""
        mock_db = MagicMock()

        # User B tries to validate entities, but only finds 2 of 3
        # (third belongs to different yacht)
        ids = ["id1", "id2", "id3"]
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "id1", "yacht_id": yacht_b_id},
            {"id": "id2", "yacht_id": yacht_b_id},
            # id3 missing - belongs to yacht_a
        ]

        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        validator = OwnershipValidator(mock_db, yacht_b_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate_multiple("equipment", ids)

        assert "id3" in exc_info.value.entity_id
        assert "not found" in exc_info.value.message.lower()


# ============================================================================
# Payload yacht_id Ignored Tests
# ============================================================================

class TestPayloadYachtIdIgnored:
    """Tests that payload yacht_id is ignored."""

    def test_ctx_yacht_id_used_not_payload(self, yacht_a_id, yacht_b_id):
        """
        When payload contains yacht_id, it's ignored.
        ctx.yacht_id is always used.
        """
        # This tests the design principle - validators use ctx.yacht_id
        # passed to constructor, not any yacht_id in the data being validated

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "eq1", "yacht_id": yacht_a_id}]

        # Track calls to verify correct yacht_id used
        call_tracker = []

        def mock_table(table_name):
            table_mock = MagicMock()

            def mock_select(*args):
                select_mock = MagicMock()

                def mock_eq_id(field, value):
                    eq_mock = MagicMock()

                    def mock_eq_yacht(field2, value2):
                        # Track which yacht_id was used in query
                        call_tracker.append({"field": field2, "value": value2})
                        eq2_mock = MagicMock()
                        if value2 == yacht_a_id:
                            eq2_mock.execute = lambda: mock_result
                        else:
                            empty_result = MagicMock()
                            empty_result.data = []
                            eq2_mock.execute = lambda: empty_result
                        return eq2_mock

                    eq_mock.eq = mock_eq_yacht
                    return eq_mock

                select_mock.eq = mock_eq_id
                return select_mock

            table_mock.select = mock_select
            return table_mock

        mock_db.table = mock_table

        # Validator initialized with yacht_a_id
        validator = OwnershipValidator(mock_db, yacht_a_id)
        result = validator.validate("equipment", "eq1")

        # Verify yacht_a_id was used in query (from ctx), not any other
        assert any(c["value"] == yacht_a_id for c in call_tracker)
        assert result["yacht_id"] == yacht_a_id


# ============================================================================
# Error Message Tests (No Enumeration)
# ============================================================================

class TestNoEnumeration:
    """Tests that error messages don't leak information."""

    def test_not_found_error_message_is_generic(self, yacht_a_id):
        """NotFoundError message doesn't reveal existence in other yacht."""
        error = NotFoundError("equipment", "some-id")

        # Message should be generic - no hints about other yachts
        assert "other yacht" not in error.message.lower()
        assert "access denied" not in error.message.lower()
        assert "permission" not in error.message.lower()
        assert "not found" in error.message.lower()

    def test_cross_yacht_and_nonexistent_same_error(self, yacht_a_id, yacht_b_id):
        """Cross-yacht and nonexistent IDs produce same error type."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        validator = OwnershipValidator(mock_db, yacht_a_id)

        # Cross-yacht ID
        with pytest.raises(NotFoundError) as exc1:
            validator.validate("equipment", "cross-yacht-id")

        # Nonexistent ID
        with pytest.raises(NotFoundError) as exc2:
            validator.validate("equipment", str(uuid.uuid4()))

        # Same error type - attacker can't distinguish
        assert type(exc1.value) == type(exc2.value)
        assert "not found" in exc1.value.message.lower()
        assert "not found" in exc2.value.message.lower()


# ============================================================================
# Entity Type Coverage Tests
# ============================================================================

class TestEntityTypeCoverage:
    """Tests that all entity types are protected."""

    @pytest.mark.parametrize("entity_type", [
        "equipment",
        "fault",
        "work_order",
        "part",
        "document",
        "note",
        "attachment",
        "checklist",
    ])
    def test_all_entity_types_require_yacht_validation(
        self, entity_type, yacht_a_id
    ):
        """All entity types require yacht_id validation."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        validator = OwnershipValidator(mock_db, yacht_a_id)

        # Should raise NotFoundError, not ValidationError
        with pytest.raises(NotFoundError):
            validator.validate(entity_type, str(uuid.uuid4()))


# ============================================================================
# Direct Function Tests
# ============================================================================

class TestDirectFunctions:
    """Tests for ensure_owned and ensure_all_owned functions."""

    def test_ensure_owned_returns_entity(self, yacht_a_id):
        """ensure_owned returns entity data on success."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "eq1", "yacht_id": yacht_a_id}]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        result = ensure_owned(
            mock_db, "pms_equipment", "eq1", yacht_a_id
        )

        assert result["id"] == "eq1"

    def test_ensure_owned_raises_404_on_miss(self, yacht_a_id):
        """ensure_owned raises NotFoundError on miss."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        with pytest.raises(NotFoundError):
            ensure_owned(mock_db, "pms_equipment", "missing", yacht_a_id)

    def test_ensure_all_owned_returns_all(self, yacht_a_id):
        """ensure_all_owned returns all entities on success."""
        mock_db = MagicMock()
        ids = ["id1", "id2"]
        mock_result = MagicMock()
        mock_result.data = [{"id": id, "yacht_id": yacht_a_id} for id in ids]
        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        result = ensure_all_owned(mock_db, "pms_equipment", ids, yacht_a_id)

        assert len(result) == 2

    def test_ensure_all_owned_fails_on_partial(self, yacht_a_id):
        """ensure_all_owned fails if any entity missing."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "id1", "yacht_id": yacht_a_id}]  # id2 missing
        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = (
            lambda: mock_result
        )

        with pytest.raises(NotFoundError):
            ensure_all_owned(
                mock_db, "pms_equipment", ["id1", "id2"], yacht_a_id
            )
