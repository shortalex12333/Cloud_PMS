"""
User / Yacht / Equipment display-name resolver.

Per doc_cert_ux_change.md (2026-04-23), UUIDs must NEVER be rendered in the UI
for users. This module resolves internal UUIDs to human-readable labels that
the frontend can display without leaking identifiers.

All three resolvers share the same characteristics:

    * **Single round-trip per call.** A batch IN-filter replaces N single-row
      look-ups, so a list view with M documents costs O(1) queries per
      resolver kind rather than O(M).

    * **Yacht-scoped.** Every query is constrained by yacht_id so the tenant
      can never read sibling-vessel data even if asked. This is belt-and-
      braces on top of RLS policies.

    * **Null-safe.** If an id is unknown the entry is simply absent from the
      returned map. Callers use `.get(uuid)` and fall back gracefully; we do
      NOT raise on missing ids because audit rows can legitimately reference
      users who were later deleted.

    * **Tenant-only.** `yacht_registry.name` lives in the TENANT DB, so no
      MASTER round-trip is needed (verified via live probe 2026-04-23).

Callers supply a supabase-py client already scoped to the right tenant.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Users (name + role)
# ──────────────────────────────────────────────────────────────────────────


def resolve_users(
    supabase,
    yacht_id: str,
    user_ids: Iterable[str],
) -> dict[str, dict[str, Optional[str]]]:
    """
    Resolve a batch of user UUIDs to ``{user_id: {name, role}}``.

    Performs two queries, both filtered by the same yacht:

        1. ``auth_users_profiles`` — id -> name
        2. ``auth_users_roles``    — user_id -> role (active rows only)

    The role query orders by ``assigned_at DESC`` and keeps the most recent
    *active* row per user; this matches the convention used elsewhere in
    the backend (e.g. list formatters) and tolerates users with multiple
    historical role rows.

    Parameters
    ----------
    supabase : supabase-py client
        Tenant-scoped client.
    yacht_id : str
        Vessel scope — every returned row is constrained to this yacht.
    user_ids : Iterable[str]
        UUIDs to resolve. Deduplicated internally. Empty input returns {}.

    Returns
    -------
    dict[str, dict]
        ``{uuid: {"name": str | None, "role": str | None}}``. Users with a
        profile but no active role have ``role = None``. Users with no
        profile at all are omitted entirely.
    """
    ids = sorted({uid for uid in user_ids if uid})
    if not ids:
        return {}

    out: dict[str, dict[str, Optional[str]]] = {uid: {"name": None, "role": None} for uid in ids}

    # ── Names ──
    try:
        prof = (
            supabase.table("auth_users_profiles")
            .select("id, name")
            .in_("id", ids)
            .eq("yacht_id", yacht_id)
            .execute()
        )
        for row in (prof.data or []):
            uid = row.get("id")
            if uid in out:
                out[uid]["name"] = row.get("name")
    except Exception as exc:  # noqa: BLE001 — non-fatal resolver
        logger.warning("resolve_users: profile lookup failed: %s", exc)

    # ── Roles (active, most recent) ──
    try:
        roles = (
            supabase.table("auth_users_roles")
            .select("user_id, role, assigned_at, is_active")
            .in_("user_id", ids)
            .eq("yacht_id", yacht_id)
            .eq("is_active", True)
            .order("assigned_at", desc=True)
            .execute()
        )
        # First row per user (order already DESC by assigned_at)
        seen: set[str] = set()
        for row in (roles.data or []):
            uid = row.get("user_id")
            if uid in out and uid not in seen:
                out[uid]["role"] = row.get("role")
                seen.add(uid)
    except Exception as exc:  # noqa: BLE001 — non-fatal resolver
        logger.warning("resolve_users: role lookup failed: %s", exc)

    # Drop entries with no name AND no role — callers treat absence as "unknown user"
    return {uid: v for uid, v in out.items() if v["name"] or v["role"]}


# ──────────────────────────────────────────────────────────────────────────
# Yacht name
# ──────────────────────────────────────────────────────────────────────────


def resolve_yacht_name(supabase, yacht_id: str) -> Optional[str]:
    """
    Fetch the human-readable yacht name from ``yacht_registry``.

    A single-row query with an indexed PK lookup — cheap and cached well
    upstream if callers want. Returns ``None`` on any failure (bad id,
    network blip, RLS block) — the frontend degrades to "—" in that case
    rather than erroring.
    """
    if not yacht_id:
        return None
    try:
        r = (
            supabase.table("yacht_registry")
            .select("name")
            .eq("id", yacht_id)
            .maybe_single()
            .execute()
        )
        if r is None or not r.data:
            return None
        return r.data.get("name")
    except Exception as exc:  # noqa: BLE001
        logger.warning("resolve_yacht_name(%s): %s", yacht_id, exc)
        return None


# ──────────────────────────────────────────────────────────────────────────
# Equipment rows (for Related Equipment section)
# ──────────────────────────────────────────────────────────────────────────


def resolve_equipment_batch(
    supabase,
    yacht_id: str,
    equipment_ids: Iterable[str],
) -> list[dict]:
    """
    Fetch a batch of equipment rows in the order requested.

    Output shape per row matches the frontend ``RelatedEquipmentItem`` type:
    ``{id, code, name, manufacturer, description}``. Soft-deleted rows
    (``deleted_at IS NOT NULL``) are excluded — a deleted equipment still
    sitting in a doc's ``equipment_ids`` array just disappears from the
    rendered list, which is the desired behaviour (we don't want ghosts).

    The caller-supplied order is preserved so the UI can rely on a stable
    render ordering even across pagination; internally we fetch once and
    reindex.
    """
    ids = [eid for eid in equipment_ids if eid]
    if not ids:
        return []

    try:
        r = (
            supabase.table("pms_equipment")
            .select("id, code, name, manufacturer, description")
            .in_("id", ids)
            .eq("yacht_id", yacht_id)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("resolve_equipment_batch: fetch failed: %s", exc)
        return []

    by_id = {row["id"]: row for row in (r.data or [])}

    # Preserve caller-supplied order; drop missing ids silently
    return [by_id[eid] for eid in ids if eid in by_id]
