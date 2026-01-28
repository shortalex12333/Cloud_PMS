"""
CelesteOS API - Ownership Validation Tests
==========================================

Unit tests for the ownership validation library.

Tests ensure:
1. ensure_owned returns entity on success
2. ensure_owned returns 404 on miss (not 403)
3. ensure_all_owned validates all entities
4. Batch validation fails atomically (all or nothing)
5. Safe fields returned (no sensitive data)
"""

import pytest
import uuid
from unittest.mock import Mock, MagicMock

from validators.ownership import (
    OwnershipValidator,
    ensure_owned,
    ensure_all_owned,
    NotFoundError,
    OwnershipValidationError,
    ENTITY_TABLE_MAP,
    SAFE_RETURN_FIELDS,
    hash_for_audit,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def yacht_id() -> str:
    """Test yacht UUID."""
    return "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def mock_db_success(yacht_id):
    """Mock DB that returns successful results."""
    mock = MagicMock()

    def create_execute(return_data):
        def execute():
            result = MagicMock()
            result.data = return_data
            return result
        return execute

    # Default: return single entity
    mock._default_data = [{"id": "test-id", "yacht_id": yacht_id, "label": "Test"}]

    def mock_table(table_name):
        table_mock = MagicMock()

        def mock_select(*args):
            select_mock = MagicMock()

            def mock_eq(field, value):
                eq_mock = MagicMock()
                eq_mock.eq = lambda f, v: MagicMock(
                    execute=create_execute(mock._default_data)
                )
                eq_mock.execute = create_execute(mock._default_data)
                return eq_mock

            def mock_in_(field, values):
                in_mock = MagicMock()
                in_mock.eq = lambda f, v: MagicMock(
                    execute=create_execute(
                        [{"id": id, "yacht_id": yacht_id} for id in values]
                    )
                )
                return in_mock

            select_mock.eq = mock_eq
            select_mock.in_ = mock_in_
            return select_mock

        table_mock.select = mock_select
        return table_mock

    mock.table = mock_table
    return mock


@pytest.fixture
def mock_db_empty():
    """Mock DB that returns empty results."""
    mock = MagicMock()

    def empty_execute():
        result = MagicMock()
        result.data = []
        return result

    def mock_table(table_name):
        table_mock = MagicMock()
        table_mock.select.return_value.eq.return_value.eq.return_value.execute = empty_execute
        table_mock.select.return_value.in_.return_value.eq.return_value.execute = empty_execute
        return table_mock

    mock.table = mock_table
    return mock


@pytest.fixture
def mock_db_error():
    """Mock DB that raises exceptions."""
    mock = MagicMock()

    def error_execute():
        raise Exception("Database connection failed")

    def mock_table(table_name):
        table_mock = MagicMock()
        table_mock.select.return_value.eq.return_value.eq.return_value.execute = error_execute
        return table_mock

    mock.table = mock_table
    return mock


# ============================================================================
# OwnershipValidator Tests
# ============================================================================

class TestOwnershipValidator:
    """Tests for OwnershipValidator class."""

    def test_init_requires_db_client(self, yacht_id):
        """Constructor requires db_client."""
        with pytest.raises(ValueError, match="db_client is required"):
            OwnershipValidator(None, yacht_id)

    def test_init_requires_yacht_id(self, mock_db_success):
        """Constructor requires yacht_id."""
        with pytest.raises(ValueError, match="yacht_id is required"):
            OwnershipValidator(mock_db_success, None)

        with pytest.raises(ValueError, match="yacht_id is required"):
            OwnershipValidator(mock_db_success, "")

    def test_validate_returns_entity_on_success(self, mock_db_success, yacht_id):
        """validate() returns entity data on success."""
        validator = OwnershipValidator(mock_db_success, yacht_id)
        result = validator.validate("equipment", "test-id")

        assert result is not None
        assert result["id"] == "test-id"
        assert result["yacht_id"] == yacht_id

    def test_validate_raises_not_found_on_miss(self, mock_db_empty, yacht_id):
        """validate() raises NotFoundError when entity not found."""
        validator = OwnershipValidator(mock_db_empty, yacht_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate("equipment", "missing-id")

        assert exc_info.value.entity_type == "equipment"
        assert exc_info.value.entity_id == "missing-id"

    def test_validate_raises_not_found_for_empty_id(self, mock_db_success, yacht_id):
        """validate() raises NotFoundError for empty ID."""
        validator = OwnershipValidator(mock_db_success, yacht_id)

        with pytest.raises(NotFoundError):
            validator.validate("equipment", "")

    def test_validate_raises_validation_error_on_db_error(
        self, mock_db_error, yacht_id
    ):
        """validate() raises OwnershipValidationError on DB error."""
        validator = OwnershipValidator(mock_db_error, yacht_id)

        with pytest.raises(OwnershipValidationError) as exc_info:
            validator.validate("equipment", "test-id")

        assert "Database connection failed" in exc_info.value.reason

    def test_validate_multiple_returns_all_on_success(self, mock_db_success, yacht_id):
        """validate_multiple() returns all entities on success."""
        validator = OwnershipValidator(mock_db_success, yacht_id)
        ids = ["id1", "id2", "id3"]

        result = validator.validate_multiple("equipment", ids)

        assert len(result) == 3
        assert all(r["yacht_id"] == yacht_id for r in result)

    def test_validate_multiple_empty_list_returns_empty(self, mock_db_success, yacht_id):
        """validate_multiple() with empty list returns empty."""
        validator = OwnershipValidator(mock_db_success, yacht_id)
        result = validator.validate_multiple("equipment", [])

        assert result == []

    def test_validate_multiple_deduplicates_ids(self, mock_db_success, yacht_id):
        """validate_multiple() deduplicates IDs."""
        validator = OwnershipValidator(mock_db_success, yacht_id)

        # Same ID repeated
        result = validator.validate_multiple("equipment", ["id1", "id1", "id1"])

        # Should only query for unique IDs
        assert len(result) == 1

    def test_validate_multiple_fails_on_any_missing(self, yacht_id):
        """validate_multiple() fails if any entity missing."""
        mock = MagicMock()

        # Return only 2 of 3 requested
        def partial_execute():
            result = MagicMock()
            result.data = [
                {"id": "id1", "yacht_id": yacht_id},
                {"id": "id2", "yacht_id": yacht_id},
            ]
            return result

        mock.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = partial_execute

        validator = OwnershipValidator(mock, yacht_id)

        with pytest.raises(NotFoundError) as exc_info:
            validator.validate_multiple("equipment", ["id1", "id2", "id3"])

        # Should identify missing entity
        assert exc_info.value.entity_id == "id3"

    def test_validate_pairs_validates_different_types(self, mock_db_success, yacht_id):
        """validate_pairs() validates entities of different types."""
        validator = OwnershipValidator(mock_db_success, yacht_id)

        pairs = [
            ("equipment", "eq-id"),
            ("fault", "fault-id"),
            ("work_order", "wo-id"),
        ]

        result = validator.validate_pairs(pairs)

        assert "equipment:eq-id" in result
        assert "fault:fault-id" in result
        assert "work_order:wo-id" in result


# ============================================================================
# Entity Table Mapping Tests
# ============================================================================

class TestEntityTableMapping:
    """Tests for entity type to table mapping."""

    def test_all_entity_types_mapped(self):
        """All expected entity types have table mappings."""
        expected_types = [
            "equipment", "fault", "work_order", "part", "note",
            "attachment", "checklist", "document", "email_thread",
        ]

        for entity_type in expected_types:
            assert entity_type in ENTITY_TABLE_MAP, f"Missing mapping for {entity_type}"

    def test_table_names_prefixed_correctly(self):
        """PMS tables have pms_ prefix."""
        pms_entities = ["equipment", "fault", "work_order", "part", "note", "attachment"]

        for entity_type in pms_entities:
            table = ENTITY_TABLE_MAP[entity_type]
            assert table.startswith("pms_"), f"{entity_type} should map to pms_ table"

    def test_unknown_entity_type_raises_error(self, mock_db_success, yacht_id):
        """Unknown entity type raises ValueError."""
        validator = OwnershipValidator(mock_db_success, yacht_id)

        with pytest.raises(ValueError, match="Unknown entity type"):
            validator.validate("unknown_type", "some-id")

    def test_direct_table_name_accepted(self, mock_db_success, yacht_id):
        """Direct pms_ table names are accepted."""
        validator = OwnershipValidator(mock_db_success, yacht_id)

        # Should not raise
        result = validator.validate("pms_equipment", "test-id")
        assert result is not None


# ============================================================================
# Safe Return Fields Tests
# ============================================================================

class TestSafeReturnFields:
    """Tests for safe field selection."""

    def test_safe_fields_defined_for_main_tables(self):
        """Safe fields defined for main tables."""
        main_tables = [
            "pms_equipment", "pms_faults", "pms_work_orders",
            "pms_parts", "documents",
        ]

        for table in main_tables:
            assert table in SAFE_RETURN_FIELDS, f"Missing safe fields for {table}"

    def test_safe_fields_include_id_and_yacht(self):
        """Safe fields always include id and yacht_id."""
        for table, fields in SAFE_RETURN_FIELDS.items():
            assert "id" in fields, f"{table} safe fields missing 'id'"
            assert "yacht_id" in fields, f"{table} safe fields missing 'yacht_id'"

    def test_safe_fields_exclude_sensitive_data(self):
        """Safe fields exclude sensitive data."""
        sensitive_patterns = ["password", "secret", "token", "key", "credential"]

        for table, fields in SAFE_RETURN_FIELDS.items():
            fields_lower = fields.lower()
            for pattern in sensitive_patterns:
                assert pattern not in fields_lower, \
                    f"{table} safe fields may contain sensitive: {pattern}"


# ============================================================================
# Direct Function Tests
# ============================================================================

class TestEnsureOwned:
    """Tests for ensure_owned function."""

    def test_returns_entity_data(self, yacht_id):
        """ensure_owned returns entity data."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "eq1", "yacht_id": yacht_id, "label": "Test"}]
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        result = ensure_owned(mock_db, "pms_equipment", "eq1", yacht_id)

        assert result["id"] == "eq1"
        assert result["label"] == "Test"

    def test_raises_not_found_on_miss(self, yacht_id):
        """ensure_owned raises NotFoundError when not found."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = lambda: mock_result

        with pytest.raises(NotFoundError):
            ensure_owned(mock_db, "pms_equipment", "missing", yacht_id)

    def test_requires_record_id(self, yacht_id):
        """ensure_owned requires record_id."""
        mock_db = MagicMock()

        with pytest.raises(NotFoundError):
            ensure_owned(mock_db, "pms_equipment", "", yacht_id)

    def test_requires_yacht_id(self):
        """ensure_owned requires yacht_id."""
        mock_db = MagicMock()

        with pytest.raises(NotFoundError):
            ensure_owned(mock_db, "pms_equipment", "id1", "")


class TestEnsureAllOwned:
    """Tests for ensure_all_owned function."""

    def test_returns_all_entities(self, yacht_id):
        """ensure_all_owned returns all entities."""
        mock_db = MagicMock()
        ids = ["id1", "id2", "id3"]
        mock_result = MagicMock()
        mock_result.data = [{"id": id, "yacht_id": yacht_id} for id in ids]
        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = lambda: mock_result

        result = ensure_all_owned(mock_db, "pms_equipment", ids, yacht_id)

        assert len(result) == 3

    def test_empty_list_returns_empty(self, yacht_id):
        """Empty list returns empty list."""
        mock_db = MagicMock()
        result = ensure_all_owned(mock_db, "pms_equipment", [], yacht_id)

        assert result == []

    def test_fails_if_any_missing(self, yacht_id):
        """Fails if any entity missing."""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "id1", "yacht_id": yacht_id}]  # id2 missing
        mock_db.table.return_value.select.return_value.in_.return_value.eq.return_value.execute = lambda: mock_result

        with pytest.raises(NotFoundError):
            ensure_all_owned(mock_db, "pms_equipment", ["id1", "id2"], yacht_id)


# ============================================================================
# Hash for Audit Tests
# ============================================================================

class TestHashForAudit:
    """Tests for hash_for_audit helper."""

    def test_returns_consistent_hash(self):
        """Same data produces same hash."""
        data = {"key": "value", "num": 123}

        hash1 = hash_for_audit(data)
        hash2 = hash_for_audit(data)

        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Different data produces different hash."""
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}

        assert hash_for_audit(data1) != hash_for_audit(data2)

    def test_hash_is_truncated(self):
        """Hash is truncated to 16 chars."""
        data = {"large": "payload" * 1000}
        hash_value = hash_for_audit(data)

        assert len(hash_value) == 16

    def test_handles_nested_data(self):
        """Handles nested data structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }

        # Should not raise
        hash_value = hash_for_audit(data)
        assert len(hash_value) == 16
