"""
Test Handler pms_attachments Table Usage - Prevent Linter Regression

CRITICAL: These tests ensure handlers use pms_attachments (NOT attachments).

Context:
- Linters repeatedly revert "pms_attachments" to "attachments"
- This breaks queries because the real table is pms_attachments
- These tests fail immediately if reverted

Table Ground Truth (from soft delete migration):
- pms_attachments ✓ (correct table name)
- "attachments" ✗ (wrong - does not exist)
"""

import pytest
from unittest.mock import Mock
from handlers.work_order_handlers import WorkOrderHandlers
from handlers.equipment_handlers import EquipmentHandlers
from handlers.fault_handlers import FaultHandlers


class TestWorkOrderHandlerUsesCorrectTable:
    """Ensure work_order_handlers uses pms_attachments"""

    def test_get_work_order_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
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

        handler = WorkOrderHandlers(mock_db)
        handler.url_generator = Mock()

        # Execute
        import asyncio
        asyncio.run(handler._get_work_order_files("test-wo-id"))

        # Assert
        mock_db.table.assert_called_once()
        table_name = mock_db.table.call_args[0][0]

        assert table_name == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name}') but MUST use "
            f"table('pms_attachments'). Linters may have reverted this fix. "
            f"See soft delete migration for table name ground truth."
        )

    def test_applies_soft_delete_filter(self):
        """CRITICAL: Must filter deleted_at is null"""
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = WorkOrderHandlers(mock_db)
        handler.url_generator = Mock()

        import asyncio
        asyncio.run(handler._get_work_order_files("test-wo-id"))

        # Assert soft delete filter
        mock_eq2.is_.assert_called_once_with("deleted_at", "null")


class TestEquipmentHandlerUsesCorrectTable:
    """Ensure equipment_handlers uses pms_attachments"""

    def test_get_equipment_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = EquipmentHandlers(mock_db)
        handler.url_generator = Mock()

        import asyncio
        asyncio.run(handler._get_equipment_files("test-eq-id", "test-yacht-id"))

        mock_db.table.assert_called_once()
        table_name = mock_db.table.call_args[0][0]

        assert table_name == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name}') but MUST use "
            f"table('pms_attachments')"
        )


class TestFaultHandlerUsesCorrectTable:
    """Ensure fault_handlers uses pms_attachments"""

    def test_get_fault_files_uses_pms_attachments_table(self):
        """CRITICAL: Must use table("pms_attachments") not table("attachments")"""
        mock_db = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_eq1 = Mock()
        mock_eq2 = Mock()
        mock_is = Mock()

        mock_db.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq1
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.is_.return_value = mock_is
        mock_is.execute.return_value = Mock(data=[])

        handler = FaultHandlers(mock_db)
        handler.url_generator = Mock()

        import asyncio
        asyncio.run(handler._get_fault_files("test-fault-id"))

        mock_db.table.assert_called_once()
        table_name = mock_db.table.call_args[0][0]

        assert table_name == "pms_attachments", (
            f"REGRESSION: Handler uses table('{table_name}') but MUST use "
            f"table('pms_attachments')"
        )


class TestBucketStrategyExists:
    """Ensure handlers have bucket strategy method"""

    def test_work_order_handler_has_bucket_method(self):
        """Handler must have _get_bucket_for_attachment method"""
        mock_db = Mock()
        handler = WorkOrderHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment"), (
            "WorkOrderHandlers missing _get_bucket_for_attachment method"
        )

        # Test bucket logic
        bucket = handler._get_bucket_for_attachment("work_order", "photo", "image/jpeg")
        assert bucket == "pms-work-order-photos"

    def test_equipment_handler_has_bucket_method(self):
        """Handler must have _get_bucket_for_attachment method"""
        mock_db = Mock()
        handler = EquipmentHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment")

    def test_fault_handler_has_bucket_method(self):
        """Handler must have _get_bucket_for_attachment method"""
        mock_db = Mock()
        handler = FaultHandlers(mock_db)

        assert hasattr(handler, "_get_bucket_for_attachment")
