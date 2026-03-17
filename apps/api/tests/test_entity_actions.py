# apps/api/tests/test_entity_actions.py
"""
Unit tests for action_router.entity_actions.
All tests mock get_actions_for_domain and ACTION_REGISTRY — no real registry needed.

NOTE: The spec lists the following tests under test_entity_actions.py, but they
are already covered in test_entity_prefill.py (Chunk 1) and are intentionally
excluded here to avoid duplication:
  - test_prefill_resolves_entity_id
  - test_prefill_nested_dot_path
  - test_prefill_missing_mapping_returns_empty
  - test_field_schema_excludes_backend_auto
  - test_field_schema_no_metadata_returns_empty
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_action_def(
    action_id: str,
    label: str = "Test Action",
    allowed_roles: list = None,
    variant: str = "MUTATE",
    field_metadata: list = None,
):
    """Build a minimal mock ActionDefinition."""
    mock = MagicMock()
    mock.action_id = action_id
    mock.label = label
    mock.allowed_roles = allowed_roles or ["captain", "hod", "crew"]
    mock.variant = MagicMock()
    mock.variant.value = variant
    mock.field_metadata = field_metadata or []
    return mock


def _make_domain_dict(action_id: str) -> dict:
    """Minimal dict as returned by get_actions_for_domain."""
    return {"action_id": action_id}


# ── Role filtering ─────────────────────────────────────────────────────────────

class TestRoleFiltering:
    def test_omits_actions_where_role_not_in_allowed(self):
        from action_router.entity_actions import get_available_actions

        hod_only_def = _make_action_def("hod_action", allowed_roles=["hod"])
        crew_def = _make_action_def("crew_action", allowed_roles=["crew", "captain", "hod"])

        mock_registry = {"hod_action": hod_only_def, "crew_action": crew_def}
        domain_list = [_make_domain_dict("hod_action"), _make_domain_dict("crew_action")]

        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("equipment", {"id": "eq-1", "status": "operational"}, "crew")

        action_ids = [a["action_id"] for a in result]
        assert "hod_action" not in action_ids
        assert "crew_action" in action_ids

    def test_includes_actions_where_role_permitted(self):
        from action_router.entity_actions import get_available_actions

        action_def = _make_action_def("captain_action", allowed_roles=["captain", "hod"])
        mock_registry = {"captain_action": action_def}
        domain_list = [_make_domain_dict("captain_action")]

        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("equipment", {"id": "eq-1"}, "captain")

        assert len(result) == 1
        assert result[0]["action_id"] == "captain_action"

    def test_unknown_entity_type_returns_empty_list(self):
        from action_router.entity_actions import get_available_actions
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=[]):
            result = get_available_actions("purchase_order", {"id": "po-1"}, "captain")
        assert result == []

    def test_handover_export_returns_empty_list(self):
        from action_router.entity_actions import get_available_actions
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=[]):
            result = get_available_actions("handover_export", {"id": "he-1"}, "captain")
        assert result == []


# ── State gates — work_order ───────────────────────────────────────────────────

class TestWorkOrderStateGate:
    def _get_wo_result(self, status: str, action_id: str, role: str = "captain"):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def(action_id, allowed_roles=["captain", "hod", "crew"])
        mock_registry = {action_id: action_def}
        domain_list = [_make_domain_dict(action_id)]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("work_order", {"id": "wo-1", "status": status}, role)
        return result[0] if result else None

    def test_planned_disables_close_work_order(self):
        action = self._get_wo_result("planned", "close_work_order")
        assert action is not None
        assert action["disabled"] is True
        assert "started" in action["disabled_reason"]

    def test_planned_enables_start_work_order(self):
        action = self._get_wo_result("planned", "start_work_order")
        assert action is not None
        assert action["disabled"] is False

    def test_draft_disables_close_work_order(self):
        action = self._get_wo_result("draft", "close_work_order")
        assert action is not None
        assert action["disabled"] is True

    def test_open_disables_close_work_order(self):
        action = self._get_wo_result("open", "close_work_order")
        assert action is not None
        assert action["disabled"] is True

    def test_in_progress_disables_start_work_order(self):
        action = self._get_wo_result("in_progress", "start_work_order")
        assert action is not None
        assert action["disabled"] is True
        assert "already in progress" in action["disabled_reason"]

    def test_pending_parts_disables_start_work_order(self):
        action = self._get_wo_result("pending_parts", "start_work_order")
        assert action is not None
        assert action["disabled"] is True

    def test_completed_disables_add_wo_hours(self):
        action = self._get_wo_result("completed", "add_wo_hours")
        assert action is not None
        assert action["disabled"] is True
        assert "completed" in action["disabled_reason"]

    def test_cancelled_disables_add_wo_part(self):
        action = self._get_wo_result("cancelled", "add_wo_part")
        assert action is not None
        assert action["disabled"] is True

    def test_closed_disables_start_work_order(self):
        action = self._get_wo_result("closed", "start_work_order")
        assert action is not None
        assert action["disabled"] is True


# ── State gates — fault ────────────────────────────────────────────────────────

class TestFaultStateGate:
    def _get_fault_result(self, status: str, action_id: str):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def(action_id, allowed_roles=["captain", "hod", "crew"])
        mock_registry = {action_id: action_def}
        domain_list = [_make_domain_dict(action_id)]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("fault", {"id": "fault-1", "status": status}, "captain")
        return result[0] if result else None

    def test_resolved_disables_acknowledge_fault(self):
        action = self._get_fault_result("resolved", "acknowledge_fault")
        assert action is not None
        assert action["disabled"] is True
        assert "resolved" in action["disabled_reason"]

    def test_closed_disables_diagnose_fault(self):
        action = self._get_fault_result("closed", "diagnose_fault")
        assert action is not None
        assert action["disabled"] is True

    def test_resolved_keeps_reopen_fault_enabled(self):
        """reopen_fault is the escape hatch — must stay enabled in terminal state."""
        action = self._get_fault_result("resolved", "reopen_fault")
        assert action is not None
        assert action["disabled"] is False

    def test_resolved_keeps_add_fault_note_enabled(self):
        """add_fault_note is documentation — intentionally unrestricted."""
        action = self._get_fault_result("resolved", "add_fault_note")
        assert action is not None
        assert action["disabled"] is False

    def test_open_fault_all_actions_enabled(self):
        action = self._get_fault_result("open", "acknowledge_fault")
        assert action is not None
        assert action["disabled"] is False


# ── State gates — receiving ────────────────────────────────────────────────────

class TestReceivingStateGate:
    def _get_receiving_result(self, status: str, action_id: str):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def(action_id, allowed_roles=["captain", "hod"])
        mock_registry = {action_id: action_def}
        domain_list = [_make_domain_dict(action_id)]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("receiving", {"id": "rec-1", "status": status}, "captain")
        return result[0] if result else None

    def test_accepted_disables_add_receiving_item(self):
        action = self._get_receiving_result("accepted", "add_receiving_item")
        assert action is not None
        assert action["disabled"] is True
        assert "finalised" in action["disabled_reason"]

    def test_rejected_disables_accept_receiving(self):
        action = self._get_receiving_result("rejected", "accept_receiving")
        assert action is not None
        assert action["disabled"] is True

    def test_draft_enables_add_receiving_item(self):
        action = self._get_receiving_result("draft", "add_receiving_item")
        assert action is not None
        assert action["disabled"] is False


# ── Flat entities (no state gate) ─────────────────────────────────────────────

class TestFlatEntities:
    def test_equipment_has_no_state_gate(self):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def("add_equipment_note", allowed_roles=["captain"])
        mock_registry = {"add_equipment_note": action_def}
        domain_list = [_make_domain_dict("add_equipment_note")]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("equipment", {"id": "eq-1", "status": "decommissioned"}, "captain")
        assert result[0]["disabled"] is False


# ── SIGNED variant ─────────────────────────────────────────────────────────────

class TestSignedVariant:
    def test_signed_action_sets_requires_signature_true(self):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def("write_off_part", variant="SIGNED", allowed_roles=["hod"])
        mock_registry = {"write_off_part": action_def}
        domain_list = [_make_domain_dict("write_off_part")]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("part", {"id": "part-1"}, "hod")
        assert result[0]["requires_signature"] is True
        assert result[0]["variant"] == "SIGNED"

    def test_mutate_action_does_not_set_requires_signature(self):
        from action_router.entity_actions import get_available_actions
        action_def = _make_action_def("log_part_usage", variant="MUTATE", allowed_roles=["captain"])
        mock_registry = {"log_part_usage": action_def}
        domain_list = [_make_domain_dict("log_part_usage")]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", mock_registry):
            result = get_available_actions("part", {"id": "part-1"}, "captain")
        assert result[0]["requires_signature"] is False


# ── Registry safety ────────────────────────────────────────────────────────────

class TestRegistrySafety:
    def test_missing_action_in_registry_skipped_no_keyerror(self):
        """get_actions_for_domain returns an action_id not in ACTION_REGISTRY — must skip, not crash."""
        from action_router.entity_actions import get_available_actions
        domain_list = [_make_domain_dict("ghost_action")]
        with patch("action_router.entity_actions.get_actions_for_domain", return_value=domain_list), \
             patch("action_router.entity_actions.ACTION_REGISTRY", {}):
            result = get_available_actions("equipment", {"id": "eq-1"}, "captain")
        assert result == []
