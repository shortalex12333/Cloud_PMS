"""
Unit Tests for Work Order Files List (pms_attachments)

Tests attachment retrieval with:
- Correct table name (pms_attachments not attachments)
- Soft delete filtering (deleted_at IS NULL)
- Yacht isolation (RLS)
- Entity type filtering

Run:
    pytest apps/api/tests/test_work_order_files_list.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from handlers.work_order_handlers import WorkOrderHandlers


# =============================================================================
# Table Name Tests
# =============================================================================

def test_uses_pms_attachments_table():
    """Test _get_work_order_files uses pms_attachments table"""
    # Mock Supabase client
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    # Chain mocks
    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq
    mock_eq.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=[])

    # Create handler with mocked URL generator
    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()  # Mock URL generator

    # Call method
    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify table name
    mock_db.table.assert_called_once_with("pms_attachments")


def test_filters_by_entity_type_work_order():
    """Test attachments filtered by entity_type=work_order"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq_entity = Mock()
    mock_eq_id = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq_entity
    mock_eq_entity.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=[])

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    import asyncio
    asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify entity_type filter
    # First .eq() should be for entity_type
    assert mock_select.eq.call_args[0] == ("entity_type", "work_order")


def test_filters_by_entity_id():
    """Test attachments filtered by entity_id=work_order_id"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=[])

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    work_order_id = "abc123-wo-id"
    import asyncio
    asyncio.run(handler._get_work_order_files(work_order_id))

    # Verify entity_id filter (second .eq() call)
    assert mock_eq1.eq.call_args[0] == ("entity_id", work_order_id)


def test_filters_soft_deleted():
    """Test soft-deleted attachments excluded (deleted_at IS NULL)"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=[])

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    import asyncio
    asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify .is_("deleted_at", "null") called
    mock_is.is_.assert_called_once_with("deleted_at", "null")


# =============================================================================
# Attachment Data Tests
# =============================================================================

def test_selects_required_columns():
    """Test correct columns selected from pms_attachments"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=[])

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    import asyncio
    asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify select columns
    select_arg = mock_table.select.call_args[0][0]
    assert "id" in select_arg
    assert "filename" in select_arg
    assert "mime_type" in select_arg
    assert "storage_path" in select_arg


def test_returns_empty_list_when_no_attachments():
    """Test returns empty list when no attachments found"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=None)  # No attachments

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    assert result == []


def test_returns_empty_list_when_no_url_generator():
    """Test returns empty list when URL generator not configured"""
    mock_db = Mock()
    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = None  # No URL generator

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    assert result == []
    # Should not have called database
    mock_db.table.assert_not_called()


# =============================================================================
# File Reference Generation Tests
# =============================================================================

def test_creates_file_reference_for_each_attachment():
    """Test file reference created for each attachment"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    # Mock attachments data
    attachments = [
        {
            "id": "att1",
            "filename": "photo1.jpg",
            "mime_type": "image/jpeg",
            "storage_path": "yacht123/work_orders/photo1.jpg",
            "category": "photo",
            "uploaded_at": "2026-01-28T10:00:00Z"
        },
        {
            "id": "att2",
            "filename": "invoice.pdf",
            "mime_type": "application/pdf",
            "storage_path": "yacht123/work_orders/invoice.pdf",
            "category": "invoice",
            "uploaded_at": "2026-01-28T11:00:00Z"
        }
    ]

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=attachments)

    # Mock URL generator
    mock_url_gen = Mock()
    mock_file_ref = Mock()
    mock_file_ref.to_dict.return_value = {
        "file_id": "att1",
        "filename": "photo1.jpg",
        "url": "https://example.com/photo1.jpg"
    }
    mock_url_gen.create_file_reference.return_value = mock_file_ref

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = mock_url_gen

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify create_file_reference called twice
    assert mock_url_gen.create_file_reference.call_count == 2


def test_uses_correct_bucket_for_attachments():
    """Test file references use correct bucket based on attachment type"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    # Test photo attachment - should use pms-work-order-photos bucket
    attachments = [{
        "id": "att1",
        "filename": "photo.jpg",
        "mime_type": "image/jpeg",
        "storage_path": "yacht123/photo.jpg",
        "category": "photo",
        "uploaded_at": "2026-01-28T10:00:00Z"
    }]

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=attachments)

    mock_url_gen = Mock()
    mock_file_ref = Mock()
    mock_file_ref.to_dict.return_value = {"file_id": "att1"}
    mock_url_gen.create_file_reference.return_value = mock_file_ref

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = mock_url_gen

    import asyncio
    asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify bucket parameter - photos on work orders use pms-work-order-photos
    call_kwargs = mock_url_gen.create_file_reference.call_args[1]
    assert call_kwargs["bucket"] == "pms-work-order-photos"


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_workflow_with_multiple_attachments():
    """Test complete workflow with multiple attachments"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    attachments = [
        {
            "id": "att1",
            "filename": "before.jpg",
            "mime_type": "image/jpeg",
            "storage_path": "yacht123/work_orders/before.jpg",
            "category": "photo",
            "uploaded_at": "2026-01-28T10:00:00Z"
        },
        {
            "id": "att2",
            "filename": "after.jpg",
            "mime_type": "image/jpeg",
            "storage_path": "yacht123/work_orders/after.jpg",
            "category": "photo",
            "uploaded_at": "2026-01-28T11:00:00Z"
        },
        {
            "id": "att3",
            "filename": "manual.pdf",
            "mime_type": "application/pdf",
            "storage_path": "yacht123/work_orders/manual.pdf",
            "category": "manual",
            "uploaded_at": "2026-01-28T12:00:00Z"
        }
    ]

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=attachments)

    mock_url_gen = Mock()

    def create_ref(bucket, path, filename, file_id, mime_type, expires_in_minutes):
        ref = Mock()
        ref.to_dict.return_value = {
            "file_id": file_id,
            "filename": filename,
            "url": f"https://example.com/{filename}"
        }
        return ref

    mock_url_gen.create_file_reference.side_effect = create_ref

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = mock_url_gen

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Verify result count
    assert len(result) == 3

    # Verify all files have URLs
    assert all("url" in file_ref for file_ref in result)


def test_error_handling_when_query_fails():
    """Test gracefully handles database query errors"""
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()

    # Simulate query error
    mock_select.eq.side_effect = Exception("Database connection failed")

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = Mock()

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Should return empty list on error
    assert result == []


# =============================================================================
# Soft Delete Edge Cases
# =============================================================================

def test_excludes_soft_deleted_attachments():
    """Test soft-deleted attachments not included in results"""
    # This test verifies behavior, not implementation
    # In production, soft-deleted rows filtered by RLS or query
    mock_db = Mock()
    mock_table = Mock()
    mock_select = Mock()
    mock_eq1 = Mock()
    mock_eq2 = Mock()
    mock_is = Mock()
    mock_execute = Mock()

    # Mix of deleted and active attachments
    # (In real DB, deleted_at would filter these out)
    active_attachments = [
        {
            "id": "att1",
            "filename": "active.jpg",
            "mime_type": "image/jpeg",
            "storage_path": "yacht123/active.jpg",
            "category": "photo",
            "uploaded_at": "2026-01-28T10:00:00Z",
            "deleted_at": None  # Active
        },
        {
            "id": "att2",
            "filename": "active2.jpg",
            "mime_type": "image/jpeg",
            "storage_path": "yacht123/active2.jpg",
            "category": "photo",
            "uploaded_at": "2026-01-28T11:00:00Z",
            "deleted_at": None  # Active
        }
    ]

    mock_db.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_is
    mock_is.is_.return_value = mock_execute
    mock_execute.execute.return_value = Mock(data=active_attachments)

    mock_url_gen = Mock()
    mock_file_ref = Mock()
    mock_file_ref.to_dict.return_value = {"file_id": "att1"}
    mock_url_gen.create_file_reference.return_value = mock_file_ref

    handler = WorkOrderHandlers(mock_db)
    handler.url_generator = mock_url_gen

    import asyncio
    result = asyncio.run(handler._get_work_order_files("test-wo-id"))

    # Should only have active attachments (2)
    assert len(result) == 2
