"""
Decision Audit Service Unit Tests
==================================

Phase 11.3 Evidence: Tests proving:
1. Audit entries are created with correct structure
2. Decision types (show/hide/disable) are mapped correctly
3. Context snapshot is sanitized
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import uuid

# Add api dir to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

from services.decision_audit_service import (
    DecisionAuditService,
    DecisionAuditEntry,
    get_decision_audit_service,
)


class TestDecisionAuditEntry:
    """Test DecisionAuditEntry dataclass."""

    def test_entry_has_required_fields(self):
        """Audit entry has all E021 required fields."""
        entry = DecisionAuditEntry(
            execution_id="exec-123",
            timestamp="2026-01-21T12:00:00Z",
            user_id="user-456",
            yacht_id="yacht-789",
            session_id=None,
            action="diagnose_fault",
            decision="show",
            confidence_total=0.88,
            confidence_intent=0.7,
            confidence_entity=1.0,
            confidence_situation=1.0,
            reasons=["Intent match", "Entity confirmed"],
            blocked_by=None,
            blocked_by_type=None,
            detected_intents=["diagnose"],
            entities=[{"type": "fault", "id": "f-123"}],
            situation={},
            environment="at_sea",
            user_role="engineer",
        )

        assert entry.execution_id == "exec-123"
        assert entry.action == "diagnose_fault"
        assert entry.decision == "show"
        assert entry.confidence_total == 0.88


class TestDecisionAuditService:
    """Test DecisionAuditService."""

    def test_decision_type_mapping_allowed(self):
        """Allowed actions map to 'show'."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        decisions = [
            {"action": "diagnose_fault", "allowed": True, "confidence": 0.88, "breakdown": {"intent": 0.7, "entity": 1.0, "situation": 1.0}, "reasons": [], "tier": "primary"}
        ]

        service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=["diagnose"],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        # Verify insert was called
        mock_db.table.assert_called_with("decision_audit_log")
        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]

        assert len(entries) == 1
        assert entries[0]["decision"] == "show"

    def test_decision_type_mapping_blocked_threshold(self):
        """Blocked by threshold maps to 'hide'."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        decisions = [
            {
                "action": "close_work_order",
                "allowed": False,
                "confidence": 0.40,
                "breakdown": {"intent": 0.0, "entity": 1.0, "situation": 0.0},
                "reasons": ["Confidence too low"],
                "tier": "conditional",
                "blocked_by": {"type": "threshold", "detail": "Score 0.40 < 0.60"}
            }
        ]

        service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]

        assert entries[0]["decision"] == "hide"
        assert entries[0]["blocked_by"] == "Score 0.40 < 0.60"
        assert entries[0]["blocked_by_type"] == "threshold"

    def test_decision_type_mapping_blocked_permission(self):
        """Blocked by permission maps to 'disable'."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        decisions = [
            {
                "action": "cancel_work_order",
                "allowed": False,
                "confidence": 0.75,
                "breakdown": {"intent": 0.7, "entity": 1.0, "situation": 0.5},
                "reasons": ["User not HOD"],
                "tier": "rare",
                "blocked_by": {"type": "permission", "detail": "Requires supervisor permissions"}
            }
        ]

        service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="deckhand",
            detected_intents=["cancel"],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]

        assert entries[0]["decision"] == "disable"
        assert entries[0]["blocked_by_type"] == "permission"

    def test_decision_type_mapping_blocked_state_guard(self):
        """Blocked by state_guard maps to 'disable'."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        decisions = [
            {
                "action": "start_work_order",
                "allowed": False,
                "confidence": 0.80,
                "breakdown": {"intent": 0.7, "entity": 1.0, "situation": 0.5},
                "reasons": ["WO already started"],
                "tier": "conditional",
                "blocked_by": {"type": "state_guard", "detail": "Work order must be open"}
            }
        ]

        service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=["start"],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]

        assert entries[0]["decision"] == "disable"
        assert entries[0]["blocked_by_type"] == "state_guard"

    def test_sanitize_entities(self):
        """Entities are sanitized to remove large fields."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        # Entity with extra fields that should be removed
        entities = [
            {
                "type": "work_order",
                "id": "wo-123",
                "name": "Fix Generator",
                "status": "open",
                "large_field": "x" * 10000,  # Should not be stored
                "nested": {"deep": "data"},  # Should not be stored
            }
        ]

        sanitized = service._sanitize_entities(entities)

        assert len(sanitized) == 1
        assert sanitized[0]["type"] == "work_order"
        assert sanitized[0]["id"] == "wo-123"
        assert "large_field" not in sanitized[0]
        assert "nested" not in sanitized[0]

    def test_log_decisions_batch_insert(self):
        """Multiple decisions are inserted in a single batch."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        decisions = [
            {"action": f"action_{i}", "allowed": True, "confidence": 0.8, "breakdown": {"intent": 0.8, "entity": 0.8, "situation": 0.8}, "reasons": [], "tier": "primary"}
            for i in range(30)
        ]

        logged = service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        # Should batch all 30 decisions in one insert
        assert logged == 30
        assert mock_db.table.return_value.insert.call_count == 1

        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]
        assert len(entries) == 30

    def test_log_decisions_handles_db_error(self):
        """DB errors don't crash the service."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        service = DecisionAuditService(mock_db)

        decisions = [
            {"action": "test_action", "allowed": True, "confidence": 0.8, "breakdown": {"intent": 0.8, "entity": 0.8, "situation": 0.8}, "reasons": [], "tier": "primary"}
        ]

        # Should not raise, should return 0
        logged = service.log_decisions(
            execution_id="exec-123",
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        assert logged == 0

    def test_entry_has_execution_id_grouping(self):
        """All entries from same evaluation share execution_id."""
        mock_db = Mock()
        mock_db.table.return_value.insert.return_value.execute.return_value = None

        service = DecisionAuditService(mock_db)

        execution_id = str(uuid.uuid4())
        decisions = [
            {"action": f"action_{i}", "allowed": True, "confidence": 0.8, "breakdown": {"intent": 0.8, "entity": 0.8, "situation": 0.8}, "reasons": [], "tier": "primary"}
            for i in range(5)
        ]

        service.log_decisions(
            execution_id=execution_id,
            yacht_id="yacht-456",
            user_id="user-789",
            user_role="engineer",
            detected_intents=[],
            entities=[],
            situation={},
            environment="at_sea",
            decisions=decisions,
        )

        insert_call = mock_db.table.return_value.insert.call_args
        entries = insert_call[0][0]

        # All entries should have same execution_id
        for entry in entries:
            assert entry["execution_id"] == execution_id


class TestGetDecisionAuditService:
    """Test service factory function."""

    def test_caches_service_per_client(self):
        """Same client returns same service instance."""
        mock_db = Mock()

        service1 = get_decision_audit_service(mock_db)
        service2 = get_decision_audit_service(mock_db)

        assert service1 is service2

    def test_different_clients_get_different_services(self):
        """Different clients get different service instances."""
        mock_db1 = Mock()
        mock_db2 = Mock()

        service1 = get_decision_audit_service(mock_db1)
        service2 = get_decision_audit_service(mock_db2)

        assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
