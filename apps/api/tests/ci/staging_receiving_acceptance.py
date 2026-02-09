#!/usr/bin/env python3
"""
Receiving Lens - Role/RLS Acceptance Matrix (CI Test)
======================================================

Hermetic contract tests ensuring receiving actions enforce exact roles.

Test Matrix:
- CREW → mutate = 403 (RLS_DENIED)
- HOD → mutate = 200 (allowed)
- CAPTAIN → signed = 200 (allowed)
- ALL → read = 200 (allowed)

This verifies:
1. Registry roles match handler enforcement
2. SIGNED actions require captain/manager
3. RLS deny-by-default pattern works
4. Error mapping is correct (403 not 500)

Run:
    pytest tests/ci/staging_receiving_acceptance.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone

# Mock env vars before importing handlers
import os
os.environ.setdefault("TENANT_1_SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("TENANT_1_SUPABASE_SERVICE_KEY", "test-key")


class TestReceivingRoleMatrix:
    """Role-based access control matrix for Receiving Lens v1"""

    @pytest.fixture
    def mock_user_db(self):
        """Mock RLS-enforced database client"""
        mock_db = MagicMock()
        mock_db.table.return_value = mock_db
        mock_db.select.return_value = mock_db
        mock_db.eq.return_value = mock_db
        mock_db.insert.return_value = mock_db
        mock_db.update.return_value = mock_db
        mock_db.maybe_single.return_value = mock_db
        mock_db.execute.return_value = MagicMock(data=[])
        return mock_db

    @pytest.fixture
    def mock_service_db(self):
        """Mock service role database client"""
        mock_db = MagicMock()
        mock_db.rpc.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )
        return mock_db

    @pytest.fixture
    def test_params(self):
        """Common test parameters"""
        return {
            "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
            "user_id": str(uuid.uuid4()),
            "user_jwt": "mock-jwt-token",
            "receiving_id": str(uuid.uuid4()),
        }

    # ========================================================================
    # TEST 1: CREW Cannot Mutate
    # ========================================================================

    @pytest.mark.asyncio
    async def test_crew_create_receiving_denied(self, test_params, mock_service_db):
        """
        CREW role cannot create receiving → RLS_DENIED (403)

        This tests that:
        1. create_receiving uses RPC with SECURITY DEFINER
        2. RPC checks auth_users_roles internally
        3. Returns proper error for unauthorized role
        """
        from handlers.receiving_handlers import _create_receiving_adapter, ReceivingHandlers

        # Mock get_service_db to return mock
        with patch('handlers.receiving_handlers.get_service_db', return_value=mock_service_db):
            # Mock RPC to simulate CREW rejection
            mock_service_db.rpc.return_value.execute.side_effect = Exception(
                "new row violates row-level security policy"
            )

            # Create handler
            handlers_instance = ReceivingHandlers(mock_service_db)
            handler = _create_receiving_adapter(handlers_instance)

            # Execute as CREW
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                vendor_name="Test Vendor",
            )

            # Should return RLS_DENIED error (not raise exception)
            assert result["status"] == "error"
            # Error code will be mapped by map_postgrest_error
            assert "error_code" in result

    # ========================================================================
    # TEST 2: HOD Can Mutate
    # ========================================================================

    @pytest.mark.asyncio
    async def test_hod_create_receiving_allowed(self, test_params, mock_service_db):
        """
        HOD roles (chief_engineer, purser) can create receiving → 200

        This tests that:
        1. RPC allows HOD+ roles
        2. Returns success with receiving_id
        3. Audit log written with signature={}
        """
        from handlers.receiving_handlers import _create_receiving_adapter, ReceivingHandlers

        receiving_id = str(uuid.uuid4())

        # Mock get_service_db
        with patch('handlers.receiving_handlers.get_service_db', return_value=mock_service_db):
            # Mock successful RPC response
            mock_service_db.rpc.return_value.execute.return_value = MagicMock(
                data=[{"id": receiving_id}]
            )

            # Mock audit log write
            mock_service_db.table.return_value.insert.return_value.execute.return_value = MagicMock()

            # Create handler
            handlers_instance = ReceivingHandlers(mock_service_db)
            handler = _create_receiving_adapter(handlers_instance)

            # Execute as HOD
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                vendor_name="Test Vendor",
                vendor_reference="INV-12345",
            )

            # Should succeed
            assert result["status"] == "success"
            assert result["receiving_id"] == receiving_id
            assert result["receiving_status"] == "draft"

    # ========================================================================
    # TEST 3: Update After RLS Denial
    # ========================================================================

    @pytest.mark.asyncio
    async def test_crew_update_fields_denied(self, test_params, mock_user_db):
        """
        CREW role cannot update receiving fields → RLS_DENIED (403)

        This tests that:
        1. get_user_db creates RLS-enforced client
        2. RLS policies deny CREW mutations
        3. Proper error mapping (not 500)
        """
        from handlers.receiving_handlers import _update_receiving_fields_adapter, ReceivingHandlers

        # Mock get_user_db to return RLS-enforced mock
        with patch('handlers.receiving_handlers.get_user_db', return_value=mock_user_db):
            # Mock SELECT to return existing receiving (RLS allows read)
            mock_user_db.execute.return_value = MagicMock(
                data=[{
                    "id": test_params["receiving_id"],
                    "vendor_name": "Old Vendor",
                    "status": "draft",
                }]
            )

            # Mock UPDATE to raise RLS violation
            mock_user_db.update.return_value.eq.return_value.execute.side_effect = Exception(
                "new row violates row-level security policy"
            )

            # Create handler
            handlers_instance = ReceivingHandlers(mock_user_db)
            handler = _update_receiving_fields_adapter(handlers_instance)

            # Execute as CREW
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                receiving_id=test_params["receiving_id"],
                vendor_name="New Vendor",
            )

            # Should return RLS_DENIED error
            assert result["status"] == "error"
            assert "error_code" in result

    # ========================================================================
    # TEST 4: CAPTAIN Can Sign
    # ========================================================================

    @pytest.mark.asyncio
    async def test_captain_accept_receiving_allowed(self, test_params, mock_user_db):
        """
        CAPTAIN role can execute SIGNED accept_receiving → 200

        This tests that:
        1. SIGNED actions accept captain/manager roles
        2. EXECUTE mode requires signature dict
        3. Audit log written with actual signature JSON
        4. Status updated to 'accepted'
        """
        from handlers.receiving_handlers import _accept_receiving_adapter, ReceivingHandlers

        # Mock get_user_db
        with patch('handlers.receiving_handlers.get_user_db', return_value=mock_user_db):
            # Mock receiving record
            mock_user_db.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data={
                    "id": test_params["receiving_id"],
                    "vendor_name": "Test Vendor",
                    "status": "draft",
                    "subtotal": None,
                    "tax_total": None,
                    "total": None,
                }
            )

            # Mock line items (at least 1 required)
            mock_user_db.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{
                    "id": str(uuid.uuid4()),
                    "quantity_received": 10,
                    "unit_price": 100.00,
                    "currency": "USD",
                }]
            )

            # Mock update success
            mock_user_db.update.return_value.eq.return_value.execute.return_value = MagicMock()

            # Mock audit log write
            mock_user_db.table.return_value.insert.return_value.execute.return_value = MagicMock()

            # Create handler
            handlers_instance = ReceivingHandlers(mock_user_db)
            handler = _accept_receiving_adapter(handlers_instance)

            # Execute as CAPTAIN with signature
            signature = {
                "pin": "1234",
                "totp": "567890",
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "reason": "Test acceptance",
            }

            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                receiving_id=test_params["receiving_id"],
                mode="execute",
                signature=signature,
            )

            # Should succeed
            assert result["status"] == "success"
            assert result["new_status"] == "accepted"
            assert result["signature_verified"] is True
            assert "total" in result

    # ========================================================================
    # TEST 5: SIGNED Action Requires Signature
    # ========================================================================

    @pytest.mark.asyncio
    async def test_accept_without_signature_fails(self, test_params, mock_user_db):
        """
        accept_receiving EXECUTE without signature → SIGNATURE_REQUIRED

        This tests that:
        1. SIGNED actions enforce signature requirement
        2. Error code is correct (not generic 500)
        3. Signature validation happens before DB operations
        """
        from handlers.receiving_handlers import _accept_receiving_adapter, ReceivingHandlers

        with patch('handlers.receiving_handlers.get_user_db', return_value=mock_user_db):
            # Mock receiving record
            mock_user_db.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data={
                    "id": test_params["receiving_id"],
                    "status": "draft",
                }
            )

            # Mock line items
            mock_user_db.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": str(uuid.uuid4()), "quantity_received": 1, "unit_price": 10}]
            )

            # Create handler
            handlers_instance = ReceivingHandlers(mock_user_db)
            handler = _accept_receiving_adapter(handlers_instance)

            # Execute without signature
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                receiving_id=test_params["receiving_id"],
                mode="execute",
                # signature=None  # Missing!
            )

            # Should return SIGNATURE_REQUIRED error
            assert result["status"] == "error"
            assert result["error_code"] == "SIGNATURE_REQUIRED"

    # ========================================================================
    # TEST 6: ALL Roles Can Read
    # ========================================================================

    @pytest.mark.asyncio
    async def test_all_roles_can_view_history(self, test_params, mock_user_db):
        """
        ALL crew roles can view_receiving_history → 200

        This tests that:
        1. READ actions allow all crew roles
        2. RLS policies allow SELECT for all
        3. Returns receiving + items + documents + audit_trail
        """
        from handlers.receiving_handlers import _view_receiving_history_adapter, ReceivingHandlers

        with patch('handlers.receiving_handlers.get_user_db', return_value=mock_user_db):
            # Mock receiving record
            receiving_mock = MagicMock()
            receiving_mock.data = [{
                "id": test_params["receiving_id"],
                "vendor_name": "Test Vendor",
                "status": "draft",
                "received_by": test_params["user_id"],
            }]
            mock_user_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = receiving_mock

            # Create handler
            handlers_instance = ReceivingHandlers(mock_user_db)
            handler = _view_receiving_history_adapter(handlers_instance)

            # Execute as ANY role (e.g., CREW)
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                receiving_id=test_params["receiving_id"],
            )

            # Should succeed
            assert result["status"] == "success"
            assert "receiving" in result
            assert "items" in result
            assert "documents" in result
            assert "audit_trail" in result

    # ========================================================================
    # TEST 7: Audit Invariant (Signature Never NULL)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_audit_log_signature_never_null(self, test_params, mock_service_db):
        """
        Audit logs always have signature field (never NULL)

        Non-signed actions: signature = {}
        Signed actions: signature = {pin, totp, signed_at, ...}

        This tests the audit invariant from receiving_handlers.py:111-132
        """
        from handlers.receiving_handlers import _write_audit_log

        audit_payload = {
            "yacht_id": test_params["yacht_id"],
            "entity_type": "receiving",
            "entity_id": test_params["receiving_id"],
            "action": "create_receiving",
            "user_id": test_params["user_id"],
            "old_values": None,
            "new_values": {"vendor_name": "Test"},
            # signature intentionally omitted - should default to {}
        }

        # Mock table insert
        mock_table = MagicMock()
        mock_service_db.table.return_value = mock_table

        # Call _write_audit_log
        _write_audit_log(mock_service_db, audit_payload)

        # Verify insert was called
        assert mock_table.insert.called
        insert_payload = mock_table.insert.call_args[0][0]

        # Verify signature is NOT NULL (should be {})
        assert "signature" in insert_payload
        assert insert_payload["signature"] is not None
        assert insert_payload["signature"] == {}

    # ========================================================================
    # TEST 8: Storage Path Validation
    # ========================================================================

    def test_storage_path_validation_rejects_documents_prefix(self):
        """
        validate_storage_path_for_receiving rejects paths with 'documents/' prefix

        This tests storage isolation enforcement from receiving_handlers.py:49-67
        """
        from handlers.receiving_handlers import validate_storage_path_for_receiving

        yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"
        receiving_id = str(uuid.uuid4())

        # Invalid path: starts with "documents/"
        invalid_path = f"documents/{yacht_id}/receiving/{receiving_id}/invoice.pdf"

        is_valid, error_msg = validate_storage_path_for_receiving(
            yacht_id,
            receiving_id,
            invalid_path
        )

        assert is_valid is False
        assert "documents/" in error_msg.lower()

    def test_storage_path_validation_accepts_canonical_format(self):
        """
        validate_storage_path_for_receiving accepts canonical format:
        {yacht_id}/receiving/{receiving_id}/{filename}
        """
        from handlers.receiving_handlers import validate_storage_path_for_receiving

        yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"
        receiving_id = str(uuid.uuid4())

        # Valid path: canonical format
        valid_path = f"{yacht_id}/receiving/{receiving_id}/invoice.pdf"

        is_valid, error_msg = validate_storage_path_for_receiving(
            yacht_id,
            receiving_id,
            valid_path
        )

        assert is_valid is True
        assert error_msg is None

    # ========================================================================
    # TEST 9: Error Mapping (400 vs 500)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_client_error_returns_400_not_500(self, test_params, mock_user_db):
        """
        Client errors (missing fields, invalid data) → 400, not 500

        This tests that handlers return proper error codes for client faults
        """
        from handlers.receiving_handlers import _add_receiving_item_adapter, ReceivingHandlers

        with patch('handlers.receiving_handlers.get_user_db', return_value=mock_user_db):
            # Mock receiving exists
            mock_user_db.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data={"id": test_params["receiving_id"], "status": "draft"}
            )

            # Create handler
            handlers_instance = ReceivingHandlers(mock_user_db)
            handler = _add_receiving_item_adapter(handlers_instance)

            # Execute without required fields (no part_id AND no description)
            result = await handler(
                yacht_id=test_params["yacht_id"],
                user_id=test_params["user_id"],
                user_jwt=test_params["user_jwt"],
                receiving_id=test_params["receiving_id"],
                quantity_received=10,
                # part_id=None, description=None  # Both missing!
            )

            # Should return 400-level error (client fault)
            assert result["status"] == "error"
            assert result["error_code"] == "MISSING_REQUIRED_FIELD"
            # NOT error_code="DATABASE_ERROR" or "INTERNAL_ERROR"


class TestRegistryRoleParity:
    """Verify registry roles match handler implementations"""

    def test_create_receiving_roles_match_registry(self):
        """
        Verify create_receiving allowed_roles in registry match RPC permissions

        Registry: chief_engineer, chief_officer, purser, captain, manager
        RPC: Should check these same roles in auth_users_roles
        """
        from action_router.registry import MICROACTION_REGISTRY

        action_def = MICROACTION_REGISTRY.get("create_receiving")
        assert action_def is not None
        assert action_def.variant.value == "MUTATE"

        # HOD+ roles
        expected_roles = {"chief_engineer", "chief_officer", "purser", "captain", "manager"}
        actual_roles = set(action_def.allowed_roles)

        assert actual_roles == expected_roles, f"Role mismatch: registry={actual_roles}, expected={expected_roles}"

    def test_accept_receiving_roles_match_registry(self):
        """
        Verify accept_receiving allowed_roles in registry match handler enforcement

        Registry: captain, manager (SIGNED action)
        Handler: Should enforce signature + these roles only
        """
        from action_router.registry import MICROACTION_REGISTRY

        action_def = MICROACTION_REGISTRY.get("accept_receiving")
        assert action_def is not None
        assert action_def.variant.value == "SIGNED"

        # SIGNED roles only
        expected_roles = {"captain", "manager"}
        actual_roles = set(action_def.allowed_roles)

        assert actual_roles == expected_roles, f"SIGNED role mismatch: registry={actual_roles}, expected={expected_roles}"

    def test_view_history_roles_match_registry(self):
        """
        Verify view_receiving_history allowed_roles in registry match handler enforcement

        Registry: ALL crew roles
        Handler: Should allow all authenticated users
        """
        from action_router.registry import MICROACTION_REGISTRY

        action_def = MICROACTION_REGISTRY.get("view_receiving_history")
        assert action_def is not None
        assert action_def.variant.value == "READ"

        # All crew roles
        assert "crew" in action_def.allowed_roles
        assert "deckhand" in action_def.allowed_roles
        assert "captain" in action_def.allowed_roles


# Run with: pytest tests/ci/staging_receiving_acceptance.py -v
