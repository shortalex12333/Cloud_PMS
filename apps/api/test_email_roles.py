"""
Email Role Permission Tests
===========================

Tests for EMAIL-04: Backend handler tests pass for all user roles.

Covers:
- search_emails (all roles)
- view_email_thread (all roles)
- extract_entities (all roles)
- link_to_work_order (HOD, captain)
- link_to_equipment (HOD, captain)

Role capabilities:
- Crew: Can search and view emails
- HOD: Can search, view, extract, and link emails
- Captain: Full access to all email operations
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from handlers.email_handlers import EmailHandlers


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Create mock Supabase client with chainable methods."""
    db = MagicMock()

    # Setup chainable query builder
    query_builder = MagicMock()
    query_builder.select = MagicMock(return_value=query_builder)
    query_builder.insert = MagicMock(return_value=query_builder)
    query_builder.update = MagicMock(return_value=query_builder)
    query_builder.eq = MagicMock(return_value=query_builder)
    query_builder.ilike = MagicMock(return_value=query_builder)
    query_builder.is_ = MagicMock(return_value=query_builder)
    query_builder.order = MagicMock(return_value=query_builder)
    query_builder.range = MagicMock(return_value=query_builder)
    query_builder.limit = MagicMock(return_value=query_builder)
    query_builder.maybe_single = MagicMock(return_value=query_builder)
    query_builder.execute = MagicMock(return_value=MagicMock(data=[{"id": str(uuid.uuid4())}]))

    db.table = MagicMock(return_value=query_builder)

    return db


@pytest.fixture
def handlers(mock_db):
    """Create handler instance with mock database."""
    return EmailHandlers(mock_db)


@pytest.fixture
def test_yacht_id():
    """Test yacht ID."""
    return "85fe1119-b04c-41ac-80f1-829d23322598"


@pytest.fixture
def crew_user_id():
    """Crew role user ID."""
    return f"crew-user-{uuid.uuid4()}"


@pytest.fixture
def hod_user_id():
    """HOD role user ID."""
    return f"hod-user-{uuid.uuid4()}"


@pytest.fixture
def captain_user_id():
    """Captain role user ID."""
    return f"captain-user-{uuid.uuid4()}"


@pytest.fixture
def test_thread_id():
    """Test thread ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_work_order_id():
    """Test work order ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_equipment_id():
    """Test equipment ID."""
    return str(uuid.uuid4())


# =============================================================================
# SEARCH EMAILS TESTS - All roles can search
# =============================================================================

class TestSearchEmails:
    """Tests for search_emails action - all roles can search."""

    @pytest.mark.asyncio
    async def test_crew_can_search_emails(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Crew role can search emails."""
        # Setup mock to return thread results
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid.uuid4()), "latest_subject": "Test maintenance email"},
                {"id": str(uuid.uuid4()), "latest_subject": "Engine parts invoice"},
            ]
        )

        result = await handlers.search_emails(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            query="maintenance",
            folder="inbox",
            limit=20,
        )

        assert result["status"] == "success"
        assert result["action"] == "search_emails"
        assert "threads" in result["result"]

    @pytest.mark.asyncio
    async def test_hod_can_search_emails(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """HOD role can search emails."""
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4()), "latest_subject": "Supplier quote"}]
        )

        result = await handlers.search_emails(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            query="supplier",
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_captain_can_search_emails(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Captain role can search emails."""
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = await handlers.search_emails(
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            query="nonexistent",
        )

        assert result["status"] == "success"
        assert result["result"]["count"] == 0

    @pytest.mark.asyncio
    async def test_search_with_limit_cap(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Search respects limit cap of 100."""
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = await handlers.search_emails(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            limit=500,  # Exceeds max
        )

        assert result["status"] == "success"
        assert result["result"]["limit"] == 100  # Capped


# =============================================================================
# VIEW EMAIL THREAD TESTS - All roles can view
# =============================================================================

class TestViewEmailThread:
    """Tests for view_email_thread action - all roles can view."""

    @pytest.mark.asyncio
    async def test_crew_can_view_thread(self, handlers, mock_db, test_yacht_id, crew_user_id, test_thread_id):
        """Crew role can view email threads."""
        # Setup thread mock
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Maintenance request"}
        )
        # Setup messages mock
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4()), "subject": "Maintenance request"}]
        )

        result = await handlers.view_email_thread(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            thread_id=test_thread_id,
        )

        assert result["status"] == "success"
        assert result["action"] == "view_email_thread"

    @pytest.mark.asyncio
    async def test_view_nonexistent_thread_returns_error(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Viewing nonexistent thread returns error."""
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await handlers.view_email_thread(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            thread_id="nonexistent-id",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "NOT_FOUND"


# =============================================================================
# EXTRACT ENTITIES TESTS - All roles can extract
# =============================================================================

class TestExtractEntities:
    """Tests for extract_entities action - all roles can extract."""

    @pytest.mark.asyncio
    async def test_crew_can_extract_entities(self, handlers, mock_db, test_yacht_id, crew_user_id, test_thread_id):
        """Crew role can extract entities from emails."""
        # Setup thread with subject containing patterns
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "RE: WO-12345 Generator repair P/N ABC123"}
        )
        # Setup work order lookup
        mock_db.table.return_value.select.return_value.eq.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4()), "wo_number": "WO-12345", "title": "Generator repair"}]
        )

        result = await handlers.extract_entities(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            thread_id=test_thread_id,
        )

        assert result["status"] == "success"
        assert result["action"] == "extract_entities"
        assert "suggestions" in result["result"]

    @pytest.mark.asyncio
    async def test_extract_from_nonexistent_thread_returns_error(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """Extracting from nonexistent thread returns error."""
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await handlers.extract_entities(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            thread_id="nonexistent",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "NOT_FOUND"


# =============================================================================
# LINK TO WORK ORDER TESTS - HOD and Captain can link
# =============================================================================

class TestLinkToWorkOrder:
    """Tests for link_to_work_order action - HOD and captain can link."""

    @pytest.mark.asyncio
    async def test_hod_can_link_to_work_order(self, handlers, mock_db, test_yacht_id, hod_user_id, test_thread_id, test_work_order_id):
        """HOD role can link emails to work orders."""
        link_id = str(uuid.uuid4())

        # Setup thread exists
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Parts order"}
        )
        # Setup work order exists (second call)
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_work_order_id, "wo_number": "WO-99999", "title": "Engine maintenance"}
        )
        # Setup no existing link
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        # Setup insert success
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": link_id}]
        )

        result = await handlers.link_to_work_order(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            thread_id=test_thread_id,
            work_order_id=test_work_order_id,
        )

        assert result["status"] == "success"
        assert result["action"] == "link_to_work_order"

    @pytest.mark.asyncio
    async def test_captain_can_link_to_work_order(self, handlers, mock_db, test_yacht_id, captain_user_id, test_thread_id, test_work_order_id):
        """Captain role can link emails to work orders."""
        link_id = str(uuid.uuid4())

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Budget approval"}
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": link_id}]
        )

        result = await handlers.link_to_work_order(
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            thread_id=test_thread_id,
            work_order_id=test_work_order_id,
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_link_nonexistent_thread_returns_error(self, handlers, mock_db, test_yacht_id, hod_user_id, test_work_order_id):
        """Linking nonexistent thread returns error."""
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await handlers.link_to_work_order(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            thread_id="nonexistent",
            work_order_id=test_work_order_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "THREAD_NOT_FOUND"


# =============================================================================
# LINK TO EQUIPMENT TESTS - HOD and Captain can link
# =============================================================================

class TestLinkToEquipment:
    """Tests for link_to_equipment action - HOD and captain can link."""

    @pytest.mark.asyncio
    async def test_hod_can_link_to_equipment(self, handlers, mock_db, test_yacht_id, hod_user_id, test_thread_id, test_equipment_id):
        """HOD role can link emails to equipment."""
        link_id = str(uuid.uuid4())

        # Setup thread exists
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Generator specs"}
        )
        # Setup equipment exists
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_equipment_id, "name": "Main Generator", "serial_number": "GEN-001"}
        )
        # Setup no existing link
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        # Setup insert success
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": link_id}]
        )

        result = await handlers.link_to_equipment(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            thread_id=test_thread_id,
            equipment_id=test_equipment_id,
        )

        assert result["status"] == "success"
        assert result["action"] == "link_to_equipment"

    @pytest.mark.asyncio
    async def test_captain_can_link_to_equipment(self, handlers, mock_db, test_yacht_id, captain_user_id, test_thread_id, test_equipment_id):
        """Captain role can link emails to equipment."""
        link_id = str(uuid.uuid4())

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Equipment manual"}
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": link_id}]
        )

        result = await handlers.link_to_equipment(
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            thread_id=test_thread_id,
            equipment_id=test_equipment_id,
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_link_nonexistent_equipment_returns_error(self, handlers, mock_db, test_yacht_id, hod_user_id, test_thread_id):
        """Linking to nonexistent equipment returns error."""
        # Thread exists
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = [
            MagicMock(data={"id": test_thread_id, "latest_subject": "Test"}),
            MagicMock(data=None),  # Equipment not found
        ]

        result = await handlers.link_to_equipment(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            thread_id=test_thread_id,
            equipment_id="nonexistent",
        )

        assert result["status"] == "error"


# =============================================================================
# AUDIT LOG VERIFICATION TESTS
# =============================================================================

class TestAuditLogging:
    """Tests that all actions create audit logs."""

    @pytest.mark.asyncio
    async def test_search_creates_audit_log(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """search_emails creates audit log entry."""
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[]
        )

        await handlers.search_emails(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            query="test",
        )

        # Verify audit log table was accessed
        table_calls = [call[0][0] for call in mock_db.table.call_args_list]
        assert "pms_audit_log" in table_calls

    @pytest.mark.asyncio
    async def test_view_thread_creates_audit_log(self, handlers, mock_db, test_yacht_id, crew_user_id, test_thread_id):
        """view_email_thread creates audit log entry."""
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": test_thread_id, "latest_subject": "Test"}
        )
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[]
        )

        await handlers.view_email_thread(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            thread_id=test_thread_id,
        )

        table_calls = [call[0][0] for call in mock_db.table.call_args_list]
        assert "pms_audit_log" in table_calls


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
