"""
Handover Role Permission Tests
==============================

Tests for HAND-03: Backend handler tests pass for all user roles.

Covers:
- add_to_handover (crew, HOD, captain)
- edit_handover_item (HOD, captain)
- export_handover (all roles)
- regenerate_handover_summary (all roles)

Role capabilities:
- Crew: Can add to handover, view/export
- HOD: Can add, edit, export, regenerate
- Captain: Full access to all handover operations
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from handlers.handover_handlers import HandoverHandlers


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
    query_builder.is_ = MagicMock(return_value=query_builder)
    query_builder.maybe_single = MagicMock(return_value=query_builder)
    query_builder.execute = MagicMock(return_value=MagicMock(data=[{"id": str(uuid.uuid4())}]))

    db.table = MagicMock(return_value=query_builder)

    return db


@pytest.fixture
def handlers(mock_db):
    """Create handler instance with mock database."""
    return HandoverHandlers(mock_db)


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


# =============================================================================
# ADD TO HANDOVER TESTS - All roles can add
# =============================================================================

class TestAddToHandover:
    """Tests for add_to_handover action - all roles can add items."""

    @pytest.mark.asyncio
    async def test_crew_can_add_to_handover(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Crew role can add items to handover."""
        # Setup mock to return successful insert
        item_id = str(uuid.uuid4())
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": item_id, "summary": "Test item"}]
        )
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"name": "Test Crew Member"}
        )

        result = await handlers.add_to_handover_execute(
            entity_type="note",
            entity_id=None,
            summary="Test handover item from crew",
            category="fyi",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            priority="normal",
        )

        assert result["status"] == "success"
        assert result["action"] == "add_to_handover"
        assert "result" in result
        assert "item_id" in result["result"]

    @pytest.mark.asyncio
    async def test_hod_can_add_to_handover(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """HOD role can add items to handover."""
        item_id = str(uuid.uuid4())
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": item_id, "summary": "Fault report"}]
        )
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"name": "HOD Engineer"}
        )

        result = await handlers.add_to_handover_execute(
            entity_type="fault",
            entity_id=str(uuid.uuid4()),
            summary="Critical fault identified in main engine",
            category="urgent",
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            priority="high",
            is_critical=True,
            requires_action=True,
            action_summary="Inspect within 24 hours",
        )

        assert result["status"] == "success"
        assert result["result"]["handover_item"]["is_critical"] is True
        assert result["result"]["handover_item"]["requires_action"] is True

    @pytest.mark.asyncio
    async def test_captain_can_add_to_handover(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Captain role can add items to handover."""
        item_id = str(uuid.uuid4())
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": item_id, "summary": "Captain's directive"}]
        )
        mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"name": "Captain Smith"}
        )

        result = await handlers.add_to_handover_execute(
            entity_type="note",
            entity_id=None,
            summary="Important notice regarding upcoming inspection",
            category="urgent",
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            priority="high",
            is_critical=True,
        )

        assert result["status"] == "success"
        assert result["result"]["handover_item"]["category"] == "urgent"

    @pytest.mark.asyncio
    async def test_add_requires_valid_category(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Adding handover item requires valid category."""
        result = await handlers.add_to_handover_execute(
            entity_type="note",
            entity_id=None,
            summary="Test item with invalid category",
            category="invalid_category",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "VALIDATION_ERROR"
        assert "category" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_add_requires_minimum_summary_length(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Adding handover item requires minimum summary length."""
        result = await handlers.add_to_handover_execute(
            entity_type="note",
            entity_id=None,
            summary="Short",  # Less than 10 characters
            category="fyi",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "VALIDATION_ERROR"


# =============================================================================
# EDIT HANDOVER ITEM TESTS - HOD and Captain only
# =============================================================================

class TestEditHandoverItem:
    """Tests for edit_handover_item action - HOD and Captain only."""

    @pytest.mark.asyncio
    async def test_hod_can_edit_handover_item(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """HOD can edit handover items."""
        item_id = str(uuid.uuid4())

        # Mock existing item
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": item_id, "summary": "Original summary", "category": "fyi"}
        )
        # Mock successful update
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": item_id, "summary": "Updated summary", "category": "urgent"}]
        )

        result = await handlers.edit_handover_item_execute(
            item_id=item_id,
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            summary="Updated summary by HOD",
            category="urgent",
        )

        assert result["status"] == "success"
        assert "updated_fields" in result["result"]

    @pytest.mark.asyncio
    async def test_captain_can_edit_handover_item(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Captain can edit handover items."""
        item_id = str(uuid.uuid4())

        # Mock existing item
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": item_id, "summary": "Original", "category": "fyi", "is_critical": False}
        )
        # Mock successful update
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": item_id, "summary": "Captain edit", "is_critical": True}]
        )

        result = await handlers.edit_handover_item_execute(
            item_id=item_id,
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            is_critical=True,
            action_summary="Immediate attention required",
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_edit_nonexistent_item_fails(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """Editing non-existent item returns error."""
        # Mock no item found
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await handlers.edit_handover_item_execute(
            item_id="nonexistent-id",
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            summary="Attempting to edit missing item",
        )

        assert result["status"] == "error"
        assert result["error_code"] == "NOT_FOUND"


# =============================================================================
# EXPORT HANDOVER TESTS - All roles can export
# =============================================================================

class TestExportHandover:
    """Tests for export_handover action - all roles can export."""

    @pytest.mark.asyncio
    async def test_crew_can_export_handover(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Crew can export handover (read-only operation)."""
        # Mock items query
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid.uuid4()), "summary": "Item 1", "category": "fyi"},
                {"id": str(uuid.uuid4()), "summary": "Item 2", "category": "urgent"},
            ]
        )
        # Mock export insert
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )

        result = await handlers.export_handover_execute(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
            export_type="pdf",
        )

        assert result["status"] == "success"
        assert result["result"]["export_type"] == "pdf"
        assert "export_id" in result["result"]

    @pytest.mark.asyncio
    async def test_hod_can_export_handover(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """HOD can export handover."""
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4()), "summary": "Engineering item"}]
        )
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )

        result = await handlers.export_handover_execute(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            department="engineering",
            export_type="html",
        )

        assert result["status"] == "success"
        assert result["result"]["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_captain_can_export_handover(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Captain can export handover."""
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid.uuid4())}]
        )

        result = await handlers.export_handover_execute(
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
            export_type="pdf",
        )

        assert result["status"] == "success"
        assert result["result"]["item_count"] == 0  # Empty handover still exports


# =============================================================================
# REGENERATE SUMMARY TESTS - All roles can regenerate
# =============================================================================

class TestRegenerateHandoverSummary:
    """Tests for regenerate_handover_summary action."""

    @pytest.mark.asyncio
    async def test_crew_can_regenerate_summary(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Crew can regenerate handover summary."""
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "1", "entity_type": "fault", "is_critical": True, "requires_action": True},
                {"id": "2", "entity_type": "work_order", "is_critical": False, "requires_action": False},
            ]
        )

        result = await handlers.regenerate_handover_summary_execute(
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "success"
        assert "summary" in result["result"]
        assert result["result"]["critical_count"] == 1
        assert result["result"]["action_required_count"] == 1

    @pytest.mark.asyncio
    async def test_hod_can_regenerate_summary_by_department(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """HOD can regenerate summary filtered by department."""
        # Mock with department filter
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "1", "entity_type": "equipment", "is_critical": False, "requires_action": False},
            ]
        )

        result = await handlers.regenerate_handover_summary_execute(
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
            department="engineering",
        )

        assert result["status"] == "success"
        assert result["result"]["department"] == "engineering"

    @pytest.mark.asyncio
    async def test_captain_can_regenerate_summary(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Captain can regenerate handover summary."""
        mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = await handlers.regenerate_handover_summary_execute(
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
        )

        assert result["status"] == "success"
        assert "no items" in result["result"]["summary"].lower()


# =============================================================================
# PREFILL TESTS - Tests for add_to_handover prefill from entities
# =============================================================================

class TestAddToHandoverPrefill:
    """Tests for add_to_handover_prefill action."""

    @pytest.mark.asyncio
    async def test_prefill_from_fault(self, handlers, mock_db, test_yacht_id, hod_user_id):
        """Prefill handover item from fault entity."""
        fault_id = str(uuid.uuid4())
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "id": fault_id,
                "fault_code": "ENG-001",
                "title": "Engine overheat warning",
                "description": "Temperature exceeded threshold",
                "severity": "critical",
                "equipment": {"name": "Main Engine", "location": "Engine Room"},
            }
        )

        result = await handlers.add_to_handover_prefill(
            entity_type="fault",
            entity_id=fault_id,
            yacht_id=test_yacht_id,
            user_id=hod_user_id,
        )

        assert result["status"] == "success"
        assert "prefill_data" in result
        assert result["prefill_data"]["category"] == "ongoing_fault"
        assert result["prefill_data"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_prefill_from_work_order(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Prefill handover item from work order entity."""
        wo_id = str(uuid.uuid4())
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "id": wo_id,
                "number": "WO-2024-001",
                "title": "Generator maintenance",
                "description": "Scheduled 500-hour service",
                "status": "in_progress",
                "priority": "normal",
                "equipment": {"name": "Generator #1", "location": "Engine Room"},
            }
        )

        result = await handlers.add_to_handover_prefill(
            entity_type="work_order",
            entity_id=wo_id,
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "success"
        assert result["prefill_data"]["category"] == "work_in_progress"

    @pytest.mark.asyncio
    async def test_prefill_from_equipment(self, handlers, mock_db, test_yacht_id, captain_user_id):
        """Prefill handover item from equipment entity."""
        eq_id = str(uuid.uuid4())
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={
                "id": eq_id,
                "name": "Anchor Windlass",
                "model": "AW-500",
                "manufacturer": "Maxwell",
                "location": "Foredeck",
                "status": "operational",
            }
        )

        result = await handlers.add_to_handover_prefill(
            entity_type="equipment",
            entity_id=eq_id,
            yacht_id=test_yacht_id,
            user_id=captain_user_id,
        )

        assert result["status"] == "success"
        assert result["prefill_data"]["category"] == "equipment_status"

    @pytest.mark.asyncio
    async def test_prefill_invalid_entity_type(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Prefill with invalid entity type returns error."""
        result = await handlers.add_to_handover_prefill(
            entity_type="invalid_type",
            entity_id=str(uuid.uuid4()),
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_ENTITY_TYPE"

    @pytest.mark.asyncio
    async def test_prefill_entity_not_found(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Prefill with non-existent entity returns error."""
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        result = await handlers.add_to_handover_prefill(
            entity_type="fault",
            entity_id="nonexistent-id",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "ENTITY_NOT_FOUND"


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestHandoverValidation:
    """Tests for handover input validation."""

    @pytest.mark.asyncio
    async def test_summary_max_length(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Summary must be less than 2000 characters."""
        long_summary = "x" * 2001

        result = await handlers.add_to_handover_execute(
            entity_type="note",
            entity_id=None,
            summary=long_summary,
            category="fyi",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_entity_id_required_for_non_note_types(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """entity_id is required for non-note entity types."""
        result = await handlers.add_to_handover_execute(
            entity_type="fault",
            entity_id=None,  # Missing entity_id for fault type
            summary="Fault without entity ID",
            category="urgent",
            yacht_id=test_yacht_id,
            user_id=crew_user_id,
        )

        assert result["status"] == "error"
        assert result["error_code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_valid_categories(self, handlers, mock_db, test_yacht_id, crew_user_id):
        """Test all valid categories work."""
        valid_categories = ["urgent", "in_progress", "completed", "watch", "fyi"]

        for category in valid_categories:
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(uuid.uuid4())}]
            )
            mock_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
                data={"name": "Test User"}
            )

            result = await handlers.add_to_handover_execute(
                entity_type="note",
                entity_id=None,
                summary=f"Test item with category: {category}",
                category=category,
                yacht_id=test_yacht_id,
                user_id=crew_user_id,
            )

            assert result["status"] == "success", f"Category '{category}' should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
