# apps/api/tests/test_entity_prefill.py
"""
Unit tests for action_router.entity_prefill.
All tests are pure — no DB, no FastAPI, no fixtures required.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResolveDotPath:
    def test_simple_key(self):
        from action_router.entity_prefill import _resolve_dot_path
        assert _resolve_dot_path({"id": "abc"}, "id") == "abc"

    def test_nested_path(self):
        from action_router.entity_prefill import _resolve_dot_path
        data = {"equipment": {"id": "eq-1"}}
        assert _resolve_dot_path(data, "equipment.id") == "eq-1"

    def test_missing_key_returns_none(self):
        from action_router.entity_prefill import _resolve_dot_path
        assert _resolve_dot_path({"id": "abc"}, "nonexistent") is None

    def test_missing_nested_key_returns_none(self):
        from action_router.entity_prefill import _resolve_dot_path
        assert _resolve_dot_path({"a": {}}, "a.b") is None

    def test_non_dict_intermediate_returns_none(self):
        from action_router.entity_prefill import _resolve_dot_path
        assert _resolve_dot_path({"a": "string"}, "a.b") is None


class TestResolvePrefill:
    def test_mapped_pair_returns_resolved_values(self):
        from action_router.entity_prefill import resolve_prefill
        entity_data = {"id": "eq-uuid-1", "canonical_label": "Main Engine"}
        result = resolve_prefill("equipment", "create_work_order_for_equipment", entity_data)
        assert result == {"equipment_id": "eq-uuid-1", "title": "Main Engine"}

    def test_unmapped_pair_returns_empty_dict(self):
        from action_router.entity_prefill import resolve_prefill
        result = resolve_prefill("equipment", "nonexistent_action", {"id": "x"})
        assert result == {}

    def test_missing_entity_field_omitted_from_result(self):
        from action_router.entity_prefill import resolve_prefill
        # entity_data missing 'canonical_label' — only equipment_id should be present
        entity_data = {"id": "eq-uuid-1"}
        result = resolve_prefill("equipment", "create_work_order_for_equipment", entity_data)
        assert result == {"equipment_id": "eq-uuid-1"}
        assert "title" not in result

    def test_fault_cross_entity_prefill(self):
        from action_router.entity_prefill import resolve_prefill
        entity_data = {"id": "fault-1", "equipment_id": "eq-1", "description": "Overheating"}
        result = resolve_prefill("fault", "create_work_order_from_fault", entity_data)
        assert result == {"fault_id": "fault-1", "equipment_id": "eq-1", "title": "Overheating"}

    def test_purchase_order_entity_type_returns_empty(self):
        # purchase_order has None domain — no prefill mappings
        from action_router.entity_prefill import resolve_prefill
        result = resolve_prefill("purchase_order", "any_action", {"id": "po-1"})
        assert result == {}


class TestGetFieldSchema:
    def test_required_and_optional_split(self):
        from action_router.entity_prefill import get_field_schema

        mock_fm_required = MagicMock()
        mock_fm_required.name = "notes"
        mock_fm_required.classification = "REQUIRED"

        mock_fm_optional = MagicMock()
        mock_fm_optional.name = "priority"
        mock_fm_optional.classification = "OPTIONAL"

        mock_fm_backend = MagicMock()
        mock_fm_backend.name = "yacht_id"
        mock_fm_backend.classification = "BACKEND_AUTO"

        mock_def = MagicMock()
        mock_def.field_metadata = [mock_fm_required, mock_fm_optional, mock_fm_backend]

        with patch("action_router.entity_prefill.ACTION_REGISTRY", {"my_action": mock_def}):
            with patch("action_router.entity_prefill.FieldClassification") as mock_fc:
                mock_fc.REQUIRED = "REQUIRED"
                mock_fc.OPTIONAL = "OPTIONAL"
                required, optional = get_field_schema("my_action")

            assert required == ["notes"]
            assert optional == ["priority"]
            assert "yacht_id" not in required
            assert "yacht_id" not in optional

    def test_unknown_action_returns_empty_lists(self):
        from action_router.entity_prefill import get_field_schema
        with patch("action_router.entity_prefill.ACTION_REGISTRY", {}):
            required, optional = get_field_schema("nonexistent_action")
        assert required == []
        assert optional == []

    def test_action_with_no_field_metadata_returns_empty_lists(self):
        from action_router.entity_prefill import get_field_schema
        mock_def = MagicMock()
        mock_def.field_metadata = []
        with patch("action_router.entity_prefill.ACTION_REGISTRY", {"some_action": mock_def}):
            required, optional = get_field_schema("some_action")
        assert required == []
        assert optional == []
