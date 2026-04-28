# apps/api/tests/test_add_to_handover_gating.py
"""
HANDOVER08 task B6 — unit tests for the add-to-handover role matrix and the
entity_actions cross-domain injection path that consults it.

No DB, no HTTP. Pure function tests + a small patch-based integration test
that drives `get_available_actions` through the real registry entry.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# Role × entity_type truth table straight from CEO's Issue 4/6/7/8/14 spec
# (2026-04-23) — kept here (not imported) so a matrix drift in the production
# module will make these tests fail loudly.
# ─────────────────────────────────────────────────────────────────────────────
_ALL_ROLES = [
    "crew", "engineer", "eto", "purser",
    "chief_engineer", "chief_officer", "chief_steward",
    "captain", "manager",
]

_EXPECTED: dict[str, set[str]] = {
    "equipment":      {"crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain"},
    "fault":          {"crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain"},
    "work_order":     {"crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain"},
    "part":           {"crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain"},
    "purchase_order": {"purser", "chief_engineer", "chief_officer", "chief_steward", "captain", "manager"},
    "receiving":      {"purser", "chief_engineer", "chief_officer", "chief_steward", "captain", "manager"},
    "certificate":    {"chief_engineer", "chief_officer", "chief_steward", "captain", "manager"},
    "warranty":       {"chief_engineer", "chief_officer", "chief_steward", "captain", "manager"},
    "document":       {"chief_engineer", "chief_officer", "chief_steward", "captain", "manager"},
    "shopping_list":  set(_ALL_ROLES),
    # hours_of_rest intentionally omitted — fails closed for every role.
    "hours_of_rest":  set(),
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Role matrix — parametrised sweep across every (role, entity) combo.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "entity_type,role",
    [(et, r) for et in _EXPECTED for r in _ALL_ROLES],
)
def test_role_matrix(entity_type: str, role: str) -> None:
    from actions.add_to_handover_gating import user_can_add_entity_type_to_handover

    expected = role in _EXPECTED[entity_type]
    actual = user_can_add_entity_type_to_handover(role, entity_type)
    assert actual is expected, (
        f"add_to_handover gating mismatch: entity_type={entity_type!r} role={role!r} "
        f"expected={expected} got={actual}"
    )


def test_unknown_entity_type_denies() -> None:
    from actions.add_to_handover_gating import user_can_add_entity_type_to_handover
    assert user_can_add_entity_type_to_handover("captain", "spaceship") is False


def test_empty_role_denies() -> None:
    from actions.add_to_handover_gating import user_can_add_entity_type_to_handover
    assert user_can_add_entity_type_to_handover("", "equipment") is False
    assert user_can_add_entity_type_to_handover(None, "equipment") is False  # type: ignore[arg-type]


def test_hours_of_rest_always_denies() -> None:
    from actions.add_to_handover_gating import user_can_add_entity_type_to_handover
    for role in _ALL_ROLES:
        assert user_can_add_entity_type_to_handover(role, "hours_of_rest") is False


def test_department_param_is_accepted_but_ignored_for_mvp() -> None:
    """Signature accepts the ``department`` kwarg; MVP does not scope on it."""
    from actions.add_to_handover_gating import user_can_add_entity_type_to_handover
    # engineering HOD on a 'deck'-department work order still passes today —
    # department scoping is deferred per module TODO.
    assert user_can_add_entity_type_to_handover(
        "chief_engineer", "work_order", department="deck"
    ) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. End-to-end through get_available_actions — asserts the gating module is
#    actually consulted by the cross-domain injection path.
# ─────────────────────────────────────────────────────────────────────────────

def _action_ids(result: list[dict]) -> set[str]:
    return {a["action_id"] for a in result}


def test_availableActions_includes_add_to_handover_for_crew_on_equipment() -> None:
    from action_router.entity_actions import get_available_actions

    result = get_available_actions(
        "equipment",
        {"id": "eq-1", "name": "Main Engine", "status": "operational"},
        "crew",
    )
    assert "add_to_handover" in _action_ids(result)


def test_availableActions_includes_add_to_handover_for_captain_on_purchase_order() -> None:
    from action_router.entity_actions import get_available_actions

    result = get_available_actions(
        "purchase_order",
        {"id": "po-1", "po_number": "PO-0001", "status": "draft", "department": "engineering"},
        "captain",
    )
    assert "add_to_handover" in _action_ids(result)


def test_availableActions_hides_add_to_handover_for_chief_steward_on_work_order() -> None:
    """Steward is not in the engineering/deck cohort for work_order."""
    from action_router.entity_actions import get_available_actions

    result = get_available_actions(
        "work_order",
        {"id": "wo-1", "title": "Fix pump", "status": "open"},
        "chief_steward",
    )
    assert "add_to_handover" not in _action_ids(result)


def test_availableActions_hides_add_to_handover_for_crew_on_certificate() -> None:
    """Crew is not in HOD+ — must not see it on certificate."""
    from action_router.entity_actions import get_available_actions

    result = get_available_actions(
        "certificate",
        {"id": "cert-1", "name": "SOLAS", "status": "active"},
        "crew",
    )
    assert "add_to_handover" not in _action_ids(result)


def test_availableActions_hides_add_to_handover_on_hours_of_rest_for_everyone() -> None:
    from action_router.entity_actions import get_available_actions

    for role in _ALL_ROLES:
        result = get_available_actions(
            "hours_of_rest",
            {"id": "hor-1", "status": "draft"},
            role,
        )
        assert "add_to_handover" not in _action_ids(result), (
            f"hours_of_rest should not expose add_to_handover to {role}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Prefill regression — new equipment / fault / work_order context fields.
# ─────────────────────────────────────────────────────────────────────────────

def test_equipment_add_to_handover_prefill_surfaces_context_fields() -> None:
    from action_router.entity_prefill import resolve_prefill

    # PR-EQ-5: equipment entity now emits the full 10-field context set.
    # `system_type` is the canonical top-level key (entity_routes.py equipment
    # branch also retains `equipment_type` as a backward-compat alias).
    # `code` and `running_hours` are the two fields surfaced by this PR.
    entity = {
        "id": "eq-1",
        "name": "Main Engine",
        "code": "ME-01",
        "manufacturer": "MTU",
        "model": "16V 4000 M73",
        "serial_number": "MTU-12345",
        "criticality": "high",
        "status": "operational",
        "running_hours": 12345,
        "location": "Engine Room",
        "system_type": "main_engine",
    }

    prefill = resolve_prefill("equipment", "add_to_handover", entity)

    # Identity + context — full 10-field surface
    assert prefill["entity_id"] == "eq-1"
    assert prefill["title"] == "Main Engine"
    assert prefill["code"] == "ME-01"
    assert prefill["name"] == "Main Engine"
    assert prefill["manufacturer"] == "MTU"
    assert prefill["model"] == "16V 4000 M73"
    assert prefill["serial_number"] == "MTU-12345"
    assert prefill["criticality"] == "high"
    assert prefill["status"] == "operational"
    assert prefill["running_hours"] == 12345
    assert prefill["location"] == "Engine Room"
    assert prefill["system_type"] == "main_engine"


def test_fault_add_to_handover_prefill_surfaces_context_fields() -> None:
    from action_router.entity_prefill import resolve_prefill

    entity = {
        "id": "fault-1",
        "title": "F-0042",
        "severity": "critical",
        "status": "open",
        "equipment_id": "eq-1",
        "equipment_name": "Main Engine",
    }

    prefill = resolve_prefill("fault", "add_to_handover", entity)
    assert prefill["entity_id"] == "fault-1"
    assert prefill["title"] == "F-0042"
    assert prefill["severity"] == "critical"
    assert prefill["status"] == "open"
    assert prefill["equipment_id"] == "eq-1"
    assert prefill["equipment_name"] == "Main Engine"


def test_work_order_add_to_handover_prefill_surfaces_context_fields() -> None:
    from action_router.entity_prefill import resolve_prefill

    entity = {
        "id": "wo-1",
        "title": "Replace impeller",
        "wo_number": "WO-0099",
        "priority": "high",
        "status": "in_progress",
        "equipment_id": "eq-1",
        "equipment_name": "Main Engine",
    }

    prefill = resolve_prefill("work_order", "add_to_handover", entity)
    assert prefill["wo_number"] == "WO-0099"
    assert prefill["priority"] == "high"
    assert prefill["equipment_id"] == "eq-1"
    assert prefill["equipment_name"] == "Main Engine"
    assert prefill["status"] == "in_progress"


def test_prefill_missing_keys_are_dropped_silently() -> None:
    """Lenses that do not emit a given key must not raise or inject None."""
    from action_router.entity_prefill import resolve_prefill

    prefill = resolve_prefill("equipment", "add_to_handover", {"id": "eq-1", "name": "Pump"})
    # Extras absent from entity_data must not appear.
    assert "manufacturer" not in prefill
    assert "serial_number" not in prefill
    assert prefill["entity_id"] == "eq-1"
    assert prefill["title"] == "Pump"
