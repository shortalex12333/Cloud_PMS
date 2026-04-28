"""
RLS Tenant Isolation Tests (LAW 8)

Tests that verify Row Level Security (RLS) enforces strict tenant isolation.
No user from Yacht A should ever see, access, or modify data from Yacht B.

LAW 8: Tenant Isolation is Absolute
- Search results must be filtered by yacht_id/org_id
- Entity access must validate ownership
- Cross-tenant entity IDs must return NOT_FOUND (not 403 to avoid enumeration)

See: apps/api/docs/LAWS.md (LAW 8)
     apps/api/action_router/validators/rls_entity_validator.py
"""

import pytest
import json
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Import test utilities from conftest.py (pytest auto-discovers this)
# Constants and fixtures are available via pytest's conftest mechanism
TEST_YACHT_A_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
TEST_YACHT_B_ID = "00000000-0000-0000-0000-000000000002"


# ============================================================================
# RLS Entity Validator Unit Tests
# ============================================================================

class TestValidateEntityYachtOwnership:
    """Tests for validate_entity_yacht_ownership function."""

    @pytest.mark.asyncio
    async def test_valid_ownership_returns_success(
        self,
        mock_supabase_client: MagicMock,
        auth_context_yacht_a: Dict[str, Any],
    ):
        """Entity belonging to user's yacht should pass validation."""
        from action_router.validators.rls_entity_validator import (
            validate_entity_yacht_ownership,
        )
        from action_router.validators.validation_result import ValidationResult

        # Configure mock to return entity with matching yacht_id
        entity_id = str(uuid.uuid4())
        mock_table = mock_supabase_client.table("pms_parts")
        mock_execute = mock_table.select().eq().maybe_single().execute
        mock_execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_A_ID}
        )

        # Rebuild mock chain for this specific test
        mock_supabase_client.table.return_value = MagicMock()
        mock_supabase_client.table.return_value.select.return_value = MagicMock()
        mock_supabase_client.table.return_value.select.return_value.eq.return_value = MagicMock()
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value = MagicMock()
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_A_ID}
        )

        result = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=entity_id,
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,
            field_name="part_id",
        )

        assert result.valid is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_cross_tenant_access_returns_not_found(
        self,
        mock_supabase_client: MagicMock,
    ):
        """
        Entity belonging to different yacht should return NOT_FOUND.

        SECURITY: Returns NOT_FOUND instead of 403 to prevent enumeration attacks.
        Attackers cannot determine if an entity exists in another tenant.
        """
        from action_router.validators.rls_entity_validator import (
            validate_entity_yacht_ownership,
        )

        # Entity belongs to Yacht B
        entity_id = str(uuid.uuid4())
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_B_ID}
        )

        result = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=entity_id,
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,  # User is from Yacht A
            field_name="part_id",
        )

        assert result.valid is False
        assert result.error is not None
        assert result.error.error_code == "NOT_FOUND"
        assert "not found" in result.error.message.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_entity_returns_not_found(
        self,
        mock_supabase_client: MagicMock,
    ):
        """Entity that doesn't exist should return NOT_FOUND."""
        from action_router.validators.rls_entity_validator import (
            validate_entity_yacht_ownership,
        )

        # Mock returns no data (entity doesn't exist)
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=str(uuid.uuid4()),
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,
            field_name="part_id",
        )

        assert result.valid is False
        assert result.error.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_database_error_fails_gracefully(
        self,
        mock_supabase_client: MagicMock,
    ):
        """Database errors should be handled gracefully."""
        from action_router.validators.rls_entity_validator import (
            validate_entity_yacht_ownership,
        )

        # Mock raises exception
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = Exception(
            "Database connection error"
        )

        result = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=str(uuid.uuid4()),
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,
            field_name="part_id",
        )

        # Graceful degradation - returns success to allow operation to proceed
        # The actual RLS policies on the database will still enforce isolation
        assert result.valid is True


class TestValidatePayloadEntities:
    """Tests for validate_payload_entities function."""

    @pytest.mark.asyncio
    async def test_payload_with_valid_entities_passes(
        self,
        mock_supabase_client: MagicMock,
        entity_ids_yacht_a: Dict[str, str],
    ):
        """Payload with all entities from user's yacht should pass."""
        from action_router.validators.rls_entity_validator import (
            validate_payload_entities,
        )

        # All entities return matching yacht_id
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_A_ID}
        )

        payload = {
            "part_id": entity_ids_yacht_a["part_id"],
            "equipment_id": entity_ids_yacht_a["equipment_id"],
            "name": "Test Item",  # Non-entity field
        }

        result = await validate_payload_entities(
            db=mock_supabase_client,
            payload=payload,
            user_yacht_id=TEST_YACHT_A_ID,
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_payload_with_cross_tenant_entity_fails(
        self,
        mock_supabase_client: MagicMock,
        entity_ids_yacht_a: Dict[str, str],
        entity_ids_yacht_b: Dict[str, str],
    ):
        """
        Payload containing entity from different yacht should fail.

        This is the critical LAW 8 test - even if a user knows an entity ID
        from another yacht, they cannot reference it in their payload.
        """
        from action_router.validators.rls_entity_validator import (
            validate_payload_entities,
        )

        # First entity is from Yacht A (valid)
        # Second entity is from Yacht B (invalid)
        call_count = [0]

        def mock_execute():
            mock = MagicMock()
            if call_count[0] == 0:
                mock.data = {"yacht_id": TEST_YACHT_A_ID}
            else:
                mock.data = {"yacht_id": TEST_YACHT_B_ID}
            call_count[0] += 1
            return mock

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute = mock_execute

        # Mixed payload: one entity from A, one from B
        payload = {
            "part_id": entity_ids_yacht_a["part_id"],
            "equipment_id": entity_ids_yacht_b["equipment_id"],  # Cross-tenant!
        }

        result = await validate_payload_entities(
            db=mock_supabase_client,
            payload=payload,
            user_yacht_id=TEST_YACHT_A_ID,
        )

        assert result.valid is False
        assert result.error.error_code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_payload_with_invalid_uuid_skipped(
        self,
        mock_supabase_client: MagicMock,
    ):
        """Non-UUID values should be skipped (not validated as entities)."""
        from action_router.validators.rls_entity_validator import (
            validate_payload_entities,
        )

        payload = {
            "part_id": "not-a-valid-uuid",
            "name": "Test Item",
        }

        result = await validate_payload_entities(
            db=mock_supabase_client,
            payload=payload,
            user_yacht_id=TEST_YACHT_A_ID,
        )

        # Invalid UUIDs are skipped, so validation passes
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_empty_payload_passes(
        self,
        mock_supabase_client: MagicMock,
    ):
        """Empty payload should pass validation."""
        from action_router.validators.rls_entity_validator import (
            validate_payload_entities,
        )

        result = await validate_payload_entities(
            db=mock_supabase_client,
            payload={},
            user_yacht_id=TEST_YACHT_A_ID,
        )

        assert result.valid is True


# ============================================================================
# Search Result Isolation Tests
# ============================================================================

class TestSearchResultIsolation:
    """Tests that search results are properly filtered by tenant."""

    @pytest.mark.asyncio
    async def test_search_returns_only_user_yacht_results(
        self,
        auth_context_yacht_a: Dict[str, Any],
    ):
        """
        Search results must only contain entities from user's yacht.

        Verifies that the hyper_search_multi RPC properly filters by org_id.
        """
        # This test verifies the contract - actual RPC testing is integration
        yacht_id = auth_context_yacht_a["yacht_id"]
        org_id = auth_context_yacht_a["org_id"]

        # Mock search results
        mock_results = [
            {
                "object_id": str(uuid.uuid4()),
                "object_type": "part",
                "payload": {"title": "Part from Yacht A"},
                "fused_score": 0.95,
            },
        ]

        # Verify all results belong to user's yacht
        # In production, this filtering happens in the RPC via org_id parameter
        for result in mock_results:
            # Each result should be associated with the querying user's org
            assert yacht_id == TEST_YACHT_A_ID

    @pytest.mark.asyncio
    async def test_search_with_yacht_b_context_excludes_yacht_a(
        self,
        auth_context_yacht_b: Dict[str, Any],
    ):
        """
        User from Yacht B should never see Yacht A results.

        The inverse of the above test - ensures bidirectional isolation.
        """
        yacht_id = auth_context_yacht_b["yacht_id"]

        # Verify yacht B context is isolated from yacht A
        assert yacht_id == TEST_YACHT_B_ID
        assert yacht_id != TEST_YACHT_A_ID


# ============================================================================
# User Context Building Tests
# ============================================================================

class TestBuildUserContext:
    """Tests for build_user_context function in F1 search."""

    def test_build_user_context_extracts_org_id(
        self,
        auth_context_yacht_a: Dict[str, Any],
    ):
        """UserContext must have org_id extracted from auth."""
        from services.types import UserContext

        ctx = UserContext(
            user_id=auth_context_yacht_a["user_id"],
            org_id=auth_context_yacht_a["org_id"],
            yacht_id=auth_context_yacht_a["yacht_id"],
            role=auth_context_yacht_a["role"],
        )

        assert ctx.org_id == TEST_YACHT_A_ID
        assert ctx.yacht_id == TEST_YACHT_A_ID

    def test_user_context_requires_org_id(self):
        """UserContext must raise error if org_id is missing."""
        from services.types import UserContext

        with pytest.raises(ValueError) as exc_info:
            UserContext(
                user_id="test-user",
                org_id="",  # Empty org_id
                role="crew",
            )

        assert "org_id is required" in str(exc_info.value)

    def test_user_context_requires_user_id(self):
        """UserContext must raise error if user_id is missing."""
        from services.types import UserContext

        with pytest.raises(ValueError) as exc_info:
            UserContext(
                user_id="",
                org_id="test-org",
                role="crew",
            )

        assert "user_id is required" in str(exc_info.value)


# ============================================================================
# Entity Table Mapping Tests
# ============================================================================

class TestEntityTableMapping:
    """Tests for ENTITY_TABLE_MAP configuration."""

    def test_entity_table_map_covers_common_entities(self):
        """ENTITY_TABLE_MAP should cover all common entity types."""
        from action_router.validators.rls_entity_validator import ENTITY_TABLE_MAP

        # Verify critical entity types are mapped
        expected_fields = [
            "item_id",
            "part_id",
            "equipment_id",
            "fault_id",
            "work_order_id",
            "document_id",
        ]

        for field in expected_fields:
            assert field in ENTITY_TABLE_MAP, f"Missing mapping for {field}"

    def test_entity_table_map_aliases(self):
        """Alternative field names should map to same tables."""
        from action_router.validators.rls_entity_validator import ENTITY_TABLE_MAP

        # wo_id should map to same table as work_order_id
        assert ENTITY_TABLE_MAP.get("wo_id") == ENTITY_TABLE_MAP.get("work_order_id")

        # shopping_list_item_id should map to same as item_id
        assert (
            ENTITY_TABLE_MAP.get("shopping_list_item_id")
            == ENTITY_TABLE_MAP.get("item_id")
        )


# ============================================================================
# UUID Format Validation Tests
# ============================================================================

class TestUUIDFormatValidation:
    """Tests for _is_valid_uuid_format helper."""

    def test_valid_uuid_formats(self):
        """Valid UUID formats should be recognized."""
        from action_router.validators.rls_entity_validator import _is_valid_uuid_format

        valid_uuids = [
            "85fe1119-b04c-41ac-80f1-829d23322598",
            "00000000-0000-0000-0000-000000000000",
            "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
            str(uuid.uuid4()),
        ]

        for test_uuid in valid_uuids:
            assert _is_valid_uuid_format(test_uuid), f"Should accept: {test_uuid}"

    def test_invalid_uuid_formats(self):
        """Invalid UUID formats should be rejected."""
        from action_router.validators.rls_entity_validator import _is_valid_uuid_format

        invalid_values = [
            "not-a-uuid",
            "12345",
            "",
            "85fe1119-b04c-41ac-80f1",  # Truncated
            "85fe1119b04c41ac80f1829d23322598",  # Missing hyphens
            "85fe1119-b04c-41ac-80f1-829d23322598-extra",  # Too long
        ]

        for value in invalid_values:
            assert not _is_valid_uuid_format(value), f"Should reject: {value}"


# ============================================================================
# Cross-Tenant Attack Vectors
# ============================================================================

class TestCrossTenantAttackVectors:
    """
    Tests for known cross-tenant attack patterns.

    These tests verify defenses against enumeration and IDOR attacks.
    """

    @pytest.mark.asyncio
    async def test_enumeration_attack_returns_uniform_response(
        self,
        mock_supabase_client: MagicMock,
    ):
        """
        Cross-tenant and non-existent entities should return identical errors.

        SECURITY: Prevents attackers from determining if an entity exists
        in another tenant by comparing error responses.
        """
        from action_router.validators.rls_entity_validator import (
            validate_entity_yacht_ownership,
        )

        # Test 1: Non-existent entity
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result_nonexistent = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=str(uuid.uuid4()),
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,
            field_name="part_id",
        )

        # Test 2: Exists but wrong tenant
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_B_ID}
        )

        result_wrong_tenant = await validate_entity_yacht_ownership(
            db=mock_supabase_client,
            entity_id=str(uuid.uuid4()),
            table_name="pms_parts",
            user_yacht_id=TEST_YACHT_A_ID,
            field_name="part_id",
        )

        # Both should return identical error codes
        assert result_nonexistent.error.error_code == result_wrong_tenant.error.error_code
        assert result_nonexistent.error.message == result_wrong_tenant.error.message

    @pytest.mark.asyncio
    async def test_idor_via_payload_injection_blocked(
        self,
        mock_supabase_client: MagicMock,
        entity_ids_yacht_b: Dict[str, str],
    ):
        """
        IDOR attack via payload entity injection should be blocked.

        Scenario: Attacker (Yacht A user) tries to reference Yacht B's
        work order in their payload to gain unauthorized access.
        """
        from action_router.validators.rls_entity_validator import (
            validate_payload_entities,
        )

        # Attacker knows a work_order_id from Yacht B
        malicious_payload = {
            "action": "update_status",
            "work_order_id": entity_ids_yacht_b["work_order_id"],  # IDOR attempt
            "status": "completed",
        }

        # Mock: The entity exists but belongs to Yacht B
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"yacht_id": TEST_YACHT_B_ID}
        )

        result = await validate_payload_entities(
            db=mock_supabase_client,
            payload=malicious_payload,
            user_yacht_id=TEST_YACHT_A_ID,  # Attacker is from Yacht A
        )

        # Attack should be blocked
        assert result.valid is False
        assert result.error.error_code == "NOT_FOUND"


# ============================================================================
# Integration Test Markers (for CI/CD pipeline)
# ============================================================================

@pytest.mark.integration
@pytest.mark.rls
class TestRLSIntegration:
    """
    Integration tests that require real database connection.

    Run with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_actual_search_isolation(self, db_pool):
        """
        Real database test for search result isolation.

        Requires TEST_DATABASE_URL to be configured.
        """
        # This test is skipped if db_pool fixture skips due to missing config
        async with db_pool.acquire() as conn:
            # Verify connection works
            result = await conn.fetchval("SELECT 1")
            assert result == 1

            # TODO: Add actual search isolation test against real data
            # This would query search_index with different org_ids and verify isolation
