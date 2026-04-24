# apps/api/actions/add_to_handover_gating.py
"""
CelesteOS — Add-to-Handover role matrix (HANDOVER08 task B6)
============================================================

Single source of truth for which `auth_users_profiles.role` values may surface
the canonical `add_to_handover` button on each entity lens.

Background
----------
The registry entry at apps/api/action_router/registry.py:948-973 declares
`add_to_handover.allowed_roles` as the UNION of every role that might
legitimately hand an entity over on SOME lens:

    ["crew", "engineer", "eto", "purser",
     "chief_engineer", "chief_officer", "chief_steward",
     "captain", "manager"]

That union is correct for the handler-level authorisation gate — any of those
roles can POST /v1/handover/add-item on SOME entity. But it is too permissive
for discovery: a `crew` member should NOT see "Add to Handover" on a
certificate, and a `chief_steward` should not see it on a work_order.

This module expresses the narrower per-entity-type matrix from CEO's
Issue 4/6/7/8/14 spec (2026-04-23) and is consulted by
`entity_actions._inject_cross_domain_actions` — see
apps/api/action_router/entity_actions.py:207-255.

Role names
----------
Source of truth: `auth_users_profiles.role` enum.
Observed in-use values across the registry (grep registry.py):
  crew, engineer, eto, purser,
  chief_engineer, chief_officer, chief_steward,
  captain, manager

"HOD+" in the CEO matrix maps to the chief_* roles plus captain + manager.
"""
from __future__ import annotations

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Role cohorts — composed below into the per-entity matrix.
# Any reshuffling should be done here; the matrix reads them by reference.
# ─────────────────────────────────────────────────────────────────────────────
_ENGINEERING_AND_DECK: frozenset[str] = frozenset({
    "crew",
    "eto",
    "engineer",
    "chief_engineer",
    "chief_officer",
    "captain",
})
# Engineering/deck crew who can add equipment/fault/work_order/part to handover.
# Stewards/pursers are deliberately excluded — they do not operate engineering
# equipment, so surfacing the button for them would be noise.

_HOD_PLUS: frozenset[str] = frozenset({
    "chief_engineer",
    "chief_officer",
    "chief_steward",
    "captain",
    "manager",
})
# HOD+ band. Owns certificate / warranty / document handover per CEO spec.
# `purser` intentionally EXCLUDED: purser is a function role, not HOD —
# the registry already distinguishes them (see registry.py:803, 830, 849).

_PURSER_BAND: frozenset[str] = frozenset({
    "purser",
    "chief_engineer",
    "chief_officer",
    "chief_steward",
    "captain",
    "manager",
})
# Purser + HOD+ band — procurement/receiving context.

_EVERYONE_ON_BOARD: frozenset[str] = frozenset({
    "crew",
    "engineer",
    "eto",
    "purser",
    "chief_engineer",
    "chief_officer",
    "chief_steward",
    "captain",
    "manager",
})
# Anyone on board who might add a shopping-list note for the incoming watch.


# ─────────────────────────────────────────────────────────────────────────────
# The matrix — entity_type → set of roles permitted to see "Add to Handover".
# Missing key ⇒ action hidden for everyone on that entity type.
# ─────────────────────────────────────────────────────────────────────────────
ADD_TO_HANDOVER_ROLE_MATRIX: dict[str, frozenset[str]] = {
    # Engineering / deck bucket
    "equipment":   _ENGINEERING_AND_DECK,
    "fault":       _ENGINEERING_AND_DECK,
    "work_order":  _ENGINEERING_AND_DECK,
    "part":        _ENGINEERING_AND_DECK,

    # Procurement bucket
    "purchase_order": _PURSER_BAND,
    "receiving":      _PURSER_BAND,

    # HOD+ compliance bucket
    "certificate": _HOD_PLUS,
    "warranty":    _HOD_PLUS,
    "document":    _HOD_PLUS,

    # Open to everyone on board
    "shopping_list": _EVERYONE_ON_BOARD,

    # `hours_of_rest` intentionally omitted — per CEO spec, a crew member
    # viewing their own HoR row has no obvious reason to add it to handover.
    # Revisit if a concrete workflow emerges.
}


def user_can_add_entity_type_to_handover(
    user_role: str,
    entity_type: str,
    department: Optional[str] = None,  # noqa: ARG001 — reserved for future dept scoping
) -> bool:
    """
    Return True iff a user with ``user_role`` may see the "Add to Handover"
    button on the lens for ``entity_type``.

    Parameters
    ----------
    user_role
        Role string from ``auth_users_profiles.role``. Falsy / unknown roles
        are treated as unauthorised.
    entity_type
        Lens entity type (``equipment``, ``fault``, ...). Missing from the
        matrix ⇒ False (fail closed).
    department
        Reserved. Department scoping (e.g. engineering HOD may add engineering
        work orders but not deck ones) is deferred for MVP. The engineer/deck
        cohort in ``_ENGINEERING_AND_DECK`` already covers the intended 99%
        case. TODO: if per-department scoping is required, look up the entity's
        department via a column read in entity_routes.py and compare here.

    No I/O. Pure function over the matrix.
    """
    if not user_role:
        return False
    allowed = ADD_TO_HANDOVER_ROLE_MATRIX.get(entity_type)
    if allowed is None:
        return False
    return user_role in allowed
