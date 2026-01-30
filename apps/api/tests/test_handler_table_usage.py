"""
Test Handler Table Usage - Prevent Regression to Wrong Table Names

CRITICAL: These tests ensure handlers use correct table names after linter reverts.

Context:
- Linters have repeatedly reverted "pms_attachments" to "attachments"
- This breaks queries because the real table is pms_attachments
- These tests fail if handlers use wrong table names

Table Name Ground Truth (from soft delete migration):
- pms_work_orders ✓
- pms_equipment ✓
- pms_faults ✓
- pms_parts ✓
- pms_attachments ✓ (NOT "attachments")
- pms_work_order_parts ✓
- doc_metadata ✓

Tables WITHOUT "pms_" prefix:
- auth_users_roles
- pms_audit_log (has pms_ but different pattern)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from handlers.work_order_handlers import WorkOrderHandlers
from handlers.equipment_handlers import EquipmentHandlers
from handlers.fault_handlers import FaultHandlers


class TestWorkOrderHandlerTableUsage:
    """Ensure work_order_handlers uses pms_attachments (not attachments)"""

    def test_get_work_order_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()
        mock_execute = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = WorkOrderHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_work_order_files("test-wo-id"))

        # Assert: MUST use pms_attachments table
        mock_db.table.assert_called_once()
        table_name_used = mock_db.table.call_args[0][0]

        assert table_name_used == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name_used}') but should use "
            f"table('pms_attachments'). Linters may have reverted this fix."
        )

    def test_get_work_order_files_applies_soft_delete_filter(self):
        """CRITICAL: Must filter deleted_at is null for pms_attachments"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()
        mock_execute = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = WorkOrderHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_work_order_files("test-wo-id"))

        # Assert: MUST call .is_("deleted_at", "null")
        mock_eq2.is_.assert_called_once_with("deleted_at", "null")


class TestEquipmentHandlerTableUsage:
    """Ensure equipment_handlers uses pms_attachments (not attachments)"""

    def test_get_equipment_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()
        mock_execute = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = EquipmentHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_equipment_files("test-eq-id", "test-yacht-id"))

        # Assert
        mock_db.table.assert_called_once()
        table_name_used = mock_db.table.call_args[0][0]

        assert table_name_used == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name_used}') but should use "
            f"table('pms_attachments'). Linters may have reverted this fix."
        )

    def test_get_equipment_files_applies_soft_delete_filter(self):
        """CRITICAL: Must filter deleted_at is null"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = EquipmentHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_equipment_files("test-eq-id", "test-yacht-id"))

        # Assert
        mock_eq2.is_.assert_called_once_with("deleted_at", "null")


class TestFaultHandlerTableUsage:
    """Ensure fault_handlers uses pms_attachments (not attachments)"""

    def test_get_fault_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = FaultHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_fault_files("test-fault-id"))

        # Assert
        mock_db.table.assert_called_once()
        table_name_used = mock_db.table.call_args[0][0]

        assert table_name_used == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name_used}') but should use "
            f"table('pms_attachments'). Linters may have reverted this fix."
        )

    def test_get_fault_files_applies_soft_delete_filter(self):
        """CRITICAL: Must filter deleted_at is null"""
        # Setup
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        # Chain mocks
        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = FaultHandlers(mock_db)
        handler.url_generator = Mock()  # Set mock to prevent early return

        # Execute
        import asyncio
        asyncio.run(handler._get_fault_files("test-fault-id"))

        # Assert
        mock_eq2.is_.assert_called_once_with("deleted_at", "null")


class TestBucketStrategyExists:
    """Ensure handlers have _get_bucket_for_attachment method"""

    def test_work_order_handler_has_bucket_method(self):
        """Work order handler must have bucket strategy method"""
        mock_db = Mock()
        handler = WorkOrderHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment"), (
            "WorkOrderHandlers missing _get_bucket_for_attachment method"
        )

    def test_equipment_handler_has_bucket_method(self):
        """Equipment handler must have bucket strategy method"""
        mock_db = Mock()
        handler = EquipmentHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment"), (
            "EquipmentHandlers missing _get_bucket_for_attachment method"
        )

    def test_fault_handler_has_bucket_method(self):
        """Fault handler must have bucket strategy method"""
        mock_db = Mock()
        handler = FaultHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment"), (
            "FaultHandlers missing _get_bucket_for_attachment method"
        )

    def test_bucket_strategy_returns_correct_buckets(self):
        """Bucket strategy must return pms-work-order-photos for work order photos"""
        mock_db = Mock()
        handler = WorkOrderHandlers(mock_db)

        # Work order photo should go to pms-work-order-photos
        bucket = handler._get_bucket_for_attachment("work_order", "photo", "image/jpeg")
        assert bucket == "pms-work-order-photos", (
            f"Work order photos should use 'pms-work-order-photos' bucket, got '{bucket}'"
        )

        # Manual should go to documents
        bucket = handler._get_bucket_for_attachment("work_order", "manual", "application/pdf")
        assert bucket == "documents", (
            f"Manuals should use 'documents' bucket, got '{bucket}'"
        )

        # Default should be attachments
        bucket = handler._get_bucket_for_attachment("work_order", "other", "text/plain")
        assert bucket == "attachments", (
            f"Other files should use 'attachments' bucket, got '{bucket}'"
        )
