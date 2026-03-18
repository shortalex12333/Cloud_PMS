# Universal Available Actions Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a populated `available_actions` array to all 12 entity GET endpoints, giving the frontend the complete contract (role-filtered, state-gated, pre-filled, field schema) in a single response.

**Architecture:** Two new modules (`entity_prefill.py` — static VLOOKUP, `entity_actions.py` — discovery engine) are added to `apps/api/action_router/`. The existing `AvailableAction` dataclass is extended additively. All 12 entity route handlers call `get_available_actions()` before returning; the legacy `_determine_available_actions()` function is removed.

**Tech Stack:** Python 3.11, FastAPI, pytest, `unittest.mock.patch` for registry isolation in tests. No new dependencies.

---

## Chunk 1: entity_prefill.py — Context VLOOKUP Layer

### Task 1: Write failing tests for entity_prefill

**Files:**
- Create: `apps/api/tests/test_entity_prefill.py`

- [ ] **Step 1: Create test file**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail (module does not exist yet)**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_prefill.py -v
```

Expected: `ModuleNotFoundError: No module named 'action_router.entity_prefill'`

---

### Task 2: Implement entity_prefill.py

**Files:**
- Create: `apps/api/action_router/entity_prefill.py`

- [ ] **Step 3: Create entity_prefill.py**

```python
# apps/api/action_router/entity_prefill.py
"""
CelesteOS — Entity Context Prefill
====================================
Static VLOOKUP table mapping (entity_type, action_id) to field dot-paths.
Dot-paths resolve against entity data already fetched by the route handler.

No DB calls. No side effects. Pure functions only.

To extend: add entries to CONTEXT_PREFILL_MAP. Missing entries return {}
and never block an action from appearing.
"""
from typing import Any, Dict, Optional, Tuple
# Module-level imports required so patch() can reach these names in tests.
# Lazy import inside get_field_schema() would make them invisible to patch().
from action_router.registry import ACTION_REGISTRY, FieldClassification


ENTITY_TYPE_TO_DOMAIN: Dict[str, Optional[str]] = {
    "work_order":      "work_orders",
    "equipment":       "equipment",
    "fault":           "faults",
    "part":            "parts",
    "document":        "documents",
    "certificate":     "certificates",
    "receiving":       "receiving",
    "shopping_list":   "shopping_list",
    "warranty":        "warranty",
    "hours_of_rest":   "hours_of_rest",
    "purchase_order":  None,      # no registry domain — returns []
    "handover_export": None,      # no registry domain — handover actions have no domain= set
}


CONTEXT_PREFILL_MAP: Dict[Tuple[str, str], Dict[str, str]] = {
    # ── Equipment ─────────────────────────────────────────────────────────────
    ("equipment", "create_work_order_for_equipment"): {
        "equipment_id": "id",
        "title":        "canonical_label",
    },
    ("equipment", "report_fault"): {
        "equipment_id":   "id",
        "equipment_name": "canonical_label",
    },
    ("equipment", "link_part_to_equipment"):        {"equipment_id": "id"},
    ("equipment", "add_equipment_note"):            {"equipment_id": "id"},
    ("equipment", "attach_file_to_equipment"):      {"equipment_id": "id"},
    ("equipment", "flag_equipment_attention"):      {"equipment_id": "id"},
    ("equipment", "record_equipment_hours"):        {"equipment_id": "id"},
    ("equipment", "decommission_equipment"):        {"equipment_id": "id"},
    ("equipment", "set_equipment_status"):          {"equipment_id": "id"},

    # ── Fault ─────────────────────────────────────────────────────────────────
    ("fault", "create_work_order_from_fault"): {
        "fault_id":     "id",
        "equipment_id": "equipment_id",
        "title":        "description",
    },
    ("fault", "add_fault_note"):        {"fault_id": "id"},
    ("fault", "add_fault_photo"):       {"fault_id": "id"},
    ("fault", "acknowledge_fault"):     {"fault_id": "id"},
    ("fault", "diagnose_fault"):        {"fault_id": "id"},
    ("fault", "close_fault"):           {"fault_id": "id"},
    ("fault", "reopen_fault"):          {"fault_id": "id"},
    ("fault", "mark_fault_false_alarm"): {"fault_id": "id"},
    ("fault", "update_fault"):          {"fault_id": "id"},

    # ── Work Order ────────────────────────────────────────────────────────────
    ("work_order", "add_wo_note"):          {"work_order_id": "id"},
    ("work_order", "add_wo_part"):          {"work_order_id": "id"},
    ("work_order", "add_wo_hours"):         {"work_order_id": "id"},
    ("work_order", "add_work_order_photo"): {"work_order_id": "id"},
    ("work_order", "start_work_order"):     {"work_order_id": "id"},
    ("work_order", "cancel_work_order"):    {"work_order_id": "id"},
    ("work_order", "close_work_order"):     {"work_order_id": "id"},
    ("work_order", "assign_work_order"):    {"work_order_id": "id"},
    ("work_order", "reassign_work_order"):  {"work_order_id": "id"},
    ("work_order", "archive_work_order"):   {"work_order_id": "id"},
    ("work_order", "update_work_order"):    {"work_order_id": "id"},

    # ── Part ──────────────────────────────────────────────────────────────────
    ("part", "log_part_usage"):        {"part_id": "id"},
    ("part", "transfer_part"):         {"part_id": "id"},
    ("part", "adjust_stock_quantity"): {"part_id": "id"},
    ("part", "write_off_part"):        {"part_id": "id"},
    ("part", "receive_part"):          {"part_id": "id"},
    ("part", "consume_part"):          {"part_id": "id"},
    ("part", "check_stock_level"):     {"part_id": "id"},
    ("part", "request_label_output"):  {"part_id": "id"},

    # ── Certificate ───────────────────────────────────────────────────────────
    ("certificate", "update_certificate"):          {"certificate_id": "id"},
    ("certificate", "link_document_to_certificate"):{"certificate_id": "id"},
    ("certificate", "supersede_certificate"):       {"certificate_id": "id"},

    # ── Receiving ─────────────────────────────────────────────────────────────
    ("receiving", "add_receiving_item"):                  {"receiving_id": "id"},
    ("receiving", "adjust_receiving_item"):               {"receiving_id": "id"},
    ("receiving", "accept_receiving"):                    {"receiving_id": "id"},
    ("receiving", "reject_receiving"):                    {"receiving_id": "id"},
    ("receiving", "attach_receiving_image_with_comment"): {"receiving_id": "id"},
    ("receiving", "update_receiving_fields"):             {"receiving_id": "id"},
    ("receiving", "link_invoice_document"):               {"receiving_id": "id"},

    # ── Warranty ──────────────────────────────────────────────────────────────
    ("warranty", "submit_warranty_claim"):  {"warranty_id": "id"},
    ("warranty", "approve_warranty_claim"): {"warranty_id": "id"},
    ("warranty", "reject_warranty_claim"):  {"warranty_id": "id"},
    ("warranty", "compose_warranty_email"): {"warranty_id": "id"},
    ("warranty", "draft_warranty_claim"):   {"warranty_id": "id"},

    # ── Document ──────────────────────────────────────────────────────────────
    ("document", "update_document"):         {"document_id": "id"},
    ("document", "add_document_comment"):    {"document_id": "id"},
    ("document", "add_document_tags"):       {"document_id": "id"},
    ("document", "delete_document"):         {"document_id": "id"},
    ("document", "update_document_comment"): {"document_id": "id"},

    # ── Shopping List ─────────────────────────────────────────────────────────
    # shopping_list prefill intentionally empty for Phase 2 — add as needed
    # ── Hours of Rest ─────────────────────────────────────────────────────────
    # hours_of_rest prefill intentionally empty for Phase 2 — add as needed
}


def resolve_prefill(entity_type: str, action_id: str, entity_data: dict) -> dict:
    """
    Resolve prefill values for an (entity_type, action_id) pair.
    Returns a dict of {field_name: resolved_value} from entity_data.
    Returns {} if no mapping exists — safe, never blocks an action.
    """
    mapping = CONTEXT_PREFILL_MAP.get((entity_type, action_id), {})
    result = {}
    for field_name, dot_path in mapping.items():
        value = _resolve_dot_path(entity_data, dot_path)
        if value is not None:
            result[field_name] = value
    return result


def get_field_schema(action_id: str) -> tuple[list[str], list[str]]:
    """
    Return (required_fields, optional_fields) for an action.

    Reads ActionDefinition.field_metadata from ACTION_REGISTRY.
    Uses ACTION_REGISTRY.get() — never get_action() — to safely handle
    missing action_ids without raising KeyError.

    BACKEND_AUTO and CONTEXT fields (yacht_id, user_id, etc.) are excluded
    — they are server-injected and must not appear in the frontend form.

    Returns ([], []) if action not found or has no field_metadata.
    """
    # ACTION_REGISTRY and FieldClassification are module-level imports (top of file).
    action_def = ACTION_REGISTRY.get(action_id)
    if not action_def or not action_def.field_metadata:
        return [], []
    required = [
        f.name for f in action_def.field_metadata
        if f.classification in ("REQUIRED", FieldClassification.REQUIRED)
    ]
    optional = [
        f.name for f in action_def.field_metadata
        if f.classification in ("OPTIONAL", FieldClassification.OPTIONAL)
    ]
    return required, optional


def _resolve_dot_path(data: dict, path: str) -> Any:
    """
    Resolve a dot-notation path against a dict.
    Returns None if any key in the path is missing or the value is None.
    Example: _resolve_dot_path({"a": {"b": "x"}}, "a.b") -> "x"
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_prefill.py -v
```

Expected: All 13 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/action_router/entity_prefill.py apps/api/tests/test_entity_prefill.py
git commit -m "feat: add entity_prefill VLOOKUP layer for action context prefill"
```

---

## Chunk 2: entity_actions.py — Action Discovery Engine

### Task 3: Write failing tests for entity_actions

**Files:**
- Create: `apps/api/tests/test_entity_actions.py`

- [ ] **Step 1: Create test file**

```python
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
        result = get_available_actions("purchase_order", {"id": "po-1"}, "captain")
        assert result == []

    def test_handover_export_returns_empty_list(self):
        from action_router.entity_actions import get_available_actions
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
        assert action["disabled"] is True

    def test_open_disables_close_work_order(self):
        action = self._get_wo_result("open", "close_work_order")
        assert action["disabled"] is True

    def test_in_progress_disables_start_work_order(self):
        action = self._get_wo_result("in_progress", "start_work_order")
        assert action["disabled"] is True
        assert "already in progress" in action["disabled_reason"]

    def test_pending_parts_disables_start_work_order(self):
        action = self._get_wo_result("pending_parts", "start_work_order")
        assert action["disabled"] is True

    def test_completed_disables_add_wo_hours(self):
        action = self._get_wo_result("completed", "add_wo_hours")
        assert action["disabled"] is True
        assert "completed" in action["disabled_reason"]

    def test_cancelled_disables_add_wo_part(self):
        action = self._get_wo_result("cancelled", "add_wo_part")
        assert action["disabled"] is True

    def test_closed_disables_start_work_order(self):
        action = self._get_wo_result("closed", "start_work_order")
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
        assert action["disabled"] is True
        assert "resolved" in action["disabled_reason"]

    def test_closed_disables_diagnose_fault(self):
        action = self._get_fault_result("closed", "diagnose_fault")
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
        assert action["disabled"] is True
        assert "finalised" in action["disabled_reason"]

    def test_rejected_disables_accept_receiving(self):
        action = self._get_receiving_result("rejected", "accept_receiving")
        assert action["disabled"] is True

    def test_draft_enables_add_receiving_item(self):
        action = self._get_receiving_result("draft", "add_receiving_item")
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_actions.py -v
```

Expected: `ModuleNotFoundError: No module named 'action_router.entity_actions'`

---

### Task 4: Implement entity_actions.py

**Files:**
- Create: `apps/api/action_router/entity_actions.py`

- [ ] **Step 3: Create entity_actions.py**

```python
# apps/api/action_router/entity_actions.py
"""
CelesteOS — Entity Action Discovery
=====================================
get_available_actions(entity_type, entity_data, user_role) -> list[dict]

Role filtering: actions where user_role not in allowed_roles are OMITTED entirely.
State gating: stateful entities (work_order, fault, receiving) get inline disabled/reason.
Flat entities (equipment, part, certificate, etc.): role filter only, no state gate.

No DB calls. Read-only with respect to entity_data input.
"""
from typing import Optional

from action_router.registry import ACTION_REGISTRY, get_actions_for_domain
from action_router.entity_prefill import (
    ENTITY_TYPE_TO_DOMAIN,
    resolve_prefill,
    get_field_schema,
)

# ── Work Order status sets ─────────────────────────────────────────────────────
_PRE_START_STATUSES = {"draft", "open", "planned"}
_ACTIVE_STATUSES = {"in_progress", "pending_parts"}
_TERMINAL_STATUSES = {"completed", "cancelled", "closed"}

_WO_PRE_START_DISABLED = {
    "close_work_order", "complete_work_order", "add_wo_hours",
    "reassign_work_order", "cancel_work_order",
}
_WO_ACTIVE_DISABLED = {"start_work_order"}
_WO_TERMINAL_DISABLED = {
    "start_work_order", "add_wo_part", "add_wo_hours",
    "log_part_usage", "add_work_order_photo", "assign_work_order",
}

# ── Fault status sets ──────────────────────────────────────────────────────────
_FAULT_TERMINAL_STATUSES = {"resolved", "closed"}
_FAULT_TERMINAL_DISABLED = {
    "acknowledge_fault", "diagnose_fault", "create_work_order_from_fault",
    "add_fault_photo", "close_fault",
    # reopen_fault intentionally EXCLUDED — escape hatch for terminal states
    # add_fault_note intentionally EXCLUDED — documentation, not a mutation
}

# ── Receiving status sets ──────────────────────────────────────────────────────
_RECEIVING_TERMINAL_STATUSES = {"accepted", "rejected"}
_RECEIVING_TERMINAL_DISABLED = {
    "add_receiving_item", "adjust_receiving_item", "accept_receiving",
    "reject_receiving", "attach_receiving_image_with_comment", "update_receiving_fields",
}


def get_available_actions(
    entity_type: str,
    entity_data: dict,
    user_role: str,
) -> list[dict]:
    """
    Return available actions for an entity, filtered by role and state.

    Read-only — never mutates entity_data.
    Returns [] for unknown entity types or types with no registry domain.
    """
    domain = ENTITY_TYPE_TO_DOMAIN.get(entity_type)
    if domain is None:
        return []

    domain_action_dicts = get_actions_for_domain(domain)  # List[Dict] — summaries only

    result = []
    for action_summary in domain_action_dicts:
        action_id = action_summary.get("action_id") or action_summary.get("id")
        if not action_id:
            continue

        # Full ActionDefinition — use .get() to safely skip missing IDs
        action_def = ACTION_REGISTRY.get(action_id)
        if not action_def:
            continue

        # Role gate: omit entirely if not permitted
        allowed = action_def.allowed_roles or []
        if user_role not in allowed:
            continue

        # State gate: inline for stateful entities only
        disabled, disabled_reason = _apply_state_gate(entity_type, entity_data, action_id)

        # Prefill + field schema (pure functions, no DB)
        prefill = resolve_prefill(entity_type, action_id, entity_data)
        required_fields, optional_fields = get_field_schema(action_id)

        # Variant → string; SIGNED sets requires_signature
        variant_str = (
            action_def.variant.value
            if hasattr(action_def.variant, "value")
            else str(action_def.variant)
        )
        requires_signature = (variant_str == "SIGNED")

        result.append({
            "action_id":           action_id,
            "label":               action_def.label,
            "variant":             variant_str,
            "icon":                "",
            "is_primary":          False,
            "requires_signature":  requires_signature,
            "confirmation_message": None,
            "disabled":            disabled,
            "disabled_reason":     disabled_reason,
            "prefill":             prefill,
            "required_fields":     required_fields,
            "optional_fields":     optional_fields,
        })

    return result


def _apply_state_gate(
    entity_type: str,
    entity_data: dict,
    action_id: str,
) -> tuple[bool, Optional[str]]:
    """
    Returns (disabled: bool, disabled_reason: str | None).
    disabled=False, disabled_reason=None means the action is enabled.
    Only work_order, fault, and receiving entities have state gates.
    """
    status = (entity_data.get("status") or "").lower()

    if entity_type == "work_order":
        if status in _PRE_START_STATUSES and action_id in _WO_PRE_START_DISABLED:
            return True, "Work order must be started first"
        if status in _ACTIVE_STATUSES and action_id in _WO_ACTIVE_DISABLED:
            return True, "Work order is already in progress"
        if status in _TERMINAL_STATUSES and action_id in _WO_TERMINAL_DISABLED:
            reason_map = {
                "completed": "Work order is completed",
                "cancelled":  "Work order is cancelled",
                "closed":     "Work order is closed",
            }
            return True, reason_map.get(status, "Work order is finalised")

    elif entity_type == "fault":
        if status in _FAULT_TERMINAL_STATUSES and action_id in _FAULT_TERMINAL_DISABLED:
            return True, "Fault is already resolved"

    elif entity_type == "receiving":
        if status in _RECEIVING_TERMINAL_STATUSES and action_id in _RECEIVING_TERMINAL_DISABLED:
            return True, "Receiving record is finalised"

    return False, None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_actions.py apps/api/tests/test_entity_prefill.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/action_router/entity_actions.py apps/api/tests/test_entity_actions.py
git commit -m "feat: add entity_actions discovery engine with role filter and state gates"
```

---

## Chunk 3: Wire Up — Schema Extension + Route Handlers

### Task 5: Extend AvailableAction + fix stub in action_response_schema.py

**Files:**
- Modify: `apps/api/actions/action_response_schema.py`

> **Context:** `AvailableAction` is a dataclass at the top of this 928-line file.
> The existing `get_available_actions_for_entity()` stub has a dead import:
> `from action_registry import get_registry` — this module does not exist.

- [ ] **Step 1: Extend the AvailableAction dataclass**

In `apps/api/actions/action_response_schema.py`, find the `AvailableAction` dataclass
(look for `class AvailableAction`). Change the `variant` Literal and add 3 fields:

**Find:**
```python
@dataclass
class AvailableAction:
    action_id: str
    label: str
    variant: Literal["READ", "MUTATE"]
    icon: str = ""
    is_primary: bool = False
    requires_signature: bool = False
    confirmation_message: Optional[str] = None
    disabled: bool = False
    disabled_reason: Optional[str] = None
```

**Replace with:**
```python
@dataclass
class AvailableAction:
    action_id: str
    label: str
    variant: Literal["READ", "MUTATE", "SIGNED"]   # SIGNED added for PIN+TOTP actions
    icon: str = ""
    is_primary: bool = False
    requires_signature: bool = False
    confirmation_message: Optional[str] = None
    disabled: bool = False
    disabled_reason: Optional[str] = None
    # Phase 2 additions — additive, all callers unaffected (default values provided)
    prefill: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
```

- [ ] **Step 2: Update to_dict() to include the 3 new fields**

Find the `to_dict` method inside `AvailableAction` and add the new fields:

**Find:**
```python
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "variant": self.variant,
            "icon": self.icon,
            "is_primary": self.is_primary,
            "requires_signature": self.requires_signature,
            "confirmation_message": self.confirmation_message,
            "disabled": self.disabled,
            "disabled_reason": self.disabled_reason
        }
```

**Replace with:**
```python
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "variant": self.variant,
            "icon": self.icon,
            "is_primary": self.is_primary,
            "requires_signature": self.requires_signature,
            "confirmation_message": self.confirmation_message,
            "disabled": self.disabled,
            "disabled_reason": self.disabled_reason,
            "prefill": self.prefill,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
        }
```

- [ ] **Step 3: Fix the broken stub get_available_actions_for_entity()**

Find the function `get_available_actions_for_entity` near the bottom of
`action_response_schema.py` (look for `from action_registry import get_registry`
— this is the dead import that causes ImportError if called).

**Replace the entire function body** with:

```python
def get_available_actions_for_entity(
    entity_type: str,
    entity_id: str,         # retained for backward-compat signature only; NOT used for lookup
    user_role: str = "crew",
    entity_data: dict = None,
) -> List[dict]:
    """
    Wrapper retained for backward compatibility.
    entity_id is kept in the signature only — entity_data already contains the ID.
    Callers passing entity_id without entity_data will receive empty prefill dicts.
    """
    from action_router.entity_actions import get_available_actions
    return get_available_actions(entity_type, entity_data or {}, user_role)
```

- [ ] **Step 4: Verify no syntax errors**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -c "from actions.action_response_schema import AvailableAction; a = AvailableAction('x','y','MUTATE'); print(a.to_dict())"
```

Expected output includes `prefill`, `required_fields`, `optional_fields` keys.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/actions/action_response_schema.py
git commit -m "feat: extend AvailableAction with prefill/field schema + fix broken stub"
```

---

### Task 6: Update all 12 entity route handlers

**Files:**
- Modify: `apps/api/routes/entity_routes.py`

> **Context:** The file is ~900 lines. Auth is `auth: dict = Depends(get_authenticated_user)`.
> Role is accessed as `auth.get("role", "crew")`. All handlers return bare dicts.
> `_determine_available_actions()` is at lines 612–628 — it will be removed.
> The work_order handler calls `_determine_available_actions()` somewhere in its body.
> All other 11 handlers do NOT currently have an `available_actions` key.

- [ ] **Step 1: Add import at the top of entity_routes.py**

At line ~17 (after the existing imports), add:

```python
from action_router.entity_actions import get_available_actions
```

Full import block should become:
```python
from fastapi import APIRouter, HTTPException, Depends
import logging
from typing import List, Dict

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client, get_supabase_client
from action_router.entity_actions import get_available_actions
```

- [ ] **Step 1b: Pre-flight — check for variable name collisions**

Before transforming any handler, verify `_response` and `response` are not already
used as variable names in entity_routes.py (shadowing would produce silent bugs):

```bash
grep -n "_response\|response =" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/routes/entity_routes.py
```

If any matches are found inside a handler body (not just in comments), use a
different variable name for that handler (e.g. `_entity_response`). If no matches,
proceed with `_response` as shown below.

- [ ] **Step 2: Update each handler — pattern to follow**

For EVERY handler, find the final `return {` statement and convert it to capture
the response, inject `available_actions`, then return. The entity_type string for
each handler is hardcoded below.

**Pattern (apply to all 12):**

BEFORE:
```python
        return {
            "id": data.get("id"),
            ...all existing fields...
        }
```

AFTER:
```python
        _response = {
            "id": data.get("id"),
            ...all existing fields...  # UNCHANGED
        }
        _response["available_actions"] = get_available_actions(
            "ENTITY_TYPE_HERE", _response, auth.get("role", "crew")
        )
        return _response
```

**Entity type strings by handler:**

| Handler function | entity_type string |
|---|---|
| `get_certificate_entity` | `"certificate"` |
| `get_document_entity` | `"document"` |
| `get_hours_of_rest_entity` | `"hours_of_rest"` |
| `get_shopping_list_entity` | `"shopping_list"` |
| `get_warranty_entity` | `"warranty"` |
| `get_handover_export_entity` | `"handover_export"` |
| `get_purchase_order_entity` | `"purchase_order"` |
| `get_fault_entity` | `"fault"` |
| `get_work_order_entity` | `"work_order"` |
| `get_equipment_entity` | `"equipment"` |
| `get_part_entity` | `"part"` |
| `get_receiving_entity` | `"receiving"` |

> **Note for get_work_order_entity:** This handler also has a legacy call to
> `_determine_available_actions()`. Find and REMOVE that call and any variable
> it assigns to (e.g., `actions = _determine_available_actions(...)`).
> The `available_actions` key is now populated by `get_available_actions()` above.

- [ ] **Step 3: Remove _determine_available_actions() function**

Delete lines 612–628 (the entire `_determine_available_actions` function body and definition).
Confirm no other callers remain:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && grep -n "_determine_available_actions" apps/api/routes/entity_routes.py
```

Expected: no output (zero matches)

- [ ] **Step 4: Run existing entity endpoint tests**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_endpoints.py -v
```

Expected: same pass rate as before. No regressions.
If tests fail with import errors, check the `get_available_actions` import path.

- [ ] **Step 5: Run all new unit tests**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS && python -m pytest apps/api/tests/test_entity_actions.py apps/api/tests/test_entity_prefill.py -v
```

Expected: All pass.

- [ ] **Step 6: Smoke-test one entity endpoint manually (optional but recommended)**

```bash
# Start the API locally if not already running:
# cd apps/api && uvicorn pipeline_service:app --reload --port 8000

curl -s -H "Authorization: Bearer $CAPTAIN_JWT" \
  http://localhost:8000/v1/entity/equipment/<any-equipment-id> \
  | python3 -m json.tool | grep -A 20 '"available_actions"'
```

Expected: `available_actions` array with at least one entry containing
`action_id`, `label`, `variant`, `disabled`, `prefill` keys.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/routes/entity_routes.py
git commit -m "feat: add available_actions to all 12 entity endpoints, remove legacy _determine_available_actions"
```

---

## Final verification

- [ ] All new unit tests pass: `pytest apps/api/tests/test_entity_actions.py apps/api/tests/test_entity_prefill.py -v`
- [ ] Existing entity endpoint tests pass: `pytest apps/api/tests/test_entity_endpoints.py -v`
- [ ] No `_determine_available_actions` references remain: `grep -r "_determine_available_actions" apps/api/`
- [ ] No `from action_registry import` dead imports remain: `grep -r "from action_registry import" apps/api/`
- [ ] `AvailableAction.to_dict()` includes `prefill`, `required_fields`, `optional_fields`
