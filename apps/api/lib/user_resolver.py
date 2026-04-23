"""
User / yacht / equipment resolvers — UUID → human-readable metadata.

The cert + document lenses (and other lens entity routes) need to render
actor names, roles, yacht names, and linked equipment without exposing
raw UUIDs to the frontend. These helpers centralise the batch-lookup
logic so each entity route does ONE round-trip per table.

All lookups hit the TENANT supabase client (the same client the caller
passes in). Role data lives in `auth_users_roles` (106 rows as of
2026-04-23), NOT `auth_role_assignments` (only 2 rows; legacy).
Yacht names live in TENANT `yacht_registry.name` — MASTER DB is NOT
required despite older doc comments suggesting otherwise.

See: docs/ongoing_work/certificates/CERTIFICATE_LENS_REDESIGN_2026_04_23.md
"""
from __future__ import annotations

from typing import Iterable, Optional
import logging

logger = logging.getLogger(__name__)


def resolve_users(supabase, yacht_id: str, user_ids: Iterable[str]) -> dict[str, dict]:
    """Batch-resolve user_ids to `{name, role}`.

    Strategy:
      - single `IN` query on `auth_users_profiles (id, name, email)` for name
      - single `IN` query on `auth_users_roles (user_id, role, is_active, assigned_at)`
        scoped to the yacht, newest active role wins if multiple present

    Returns `{user_id: {"name": str|None, "role": str|None}}`. Missing
    user_ids still appear in the result dict with both values None so
    callers can safely `.get(user_id, {}).get("name")`.
    """
    clean_ids: list[str] = sorted({uid for uid in user_ids if uid})
    if not clean_ids:
        return {}

    # Name lookup
    names: dict[str, str] = {}
    try:
        r = supabase.table("auth_users_profiles").select("id, name, email").in_("id", clean_ids).execute()
        for row in (getattr(r, "data", None) or []):
            uid = row.get("id")
            if uid:
                names[uid] = row.get("name") or row.get("email") or None
    except Exception as e:
        logger.warning("resolve_users: name lookup failed: %s", e)

    # Role lookup (scoped to this yacht, active only, newest)
    roles: dict[str, str] = {}
    try:
        r = (
            supabase.table("auth_users_roles")
            .select("user_id, role, assigned_at, is_active")
            .in_("user_id", clean_ids)
            .eq("yacht_id", yacht_id)
            .eq("is_active", True)
            .order("assigned_at", desc=True)
            .execute()
        )
        for row in (getattr(r, "data", None) or []):
            uid = row.get("user_id")
            # order desc → first row per user_id is newest; skip if already captured
            if uid and uid not in roles:
                roles[uid] = row.get("role")
    except Exception as e:
        logger.warning("resolve_users: role lookup failed: %s", e)

    return {
        uid: {"name": names.get(uid), "role": roles.get(uid)}
        for uid in clean_ids
    }


def resolve_yacht_name(supabase, yacht_id: str) -> Optional[str]:
    """Resolve a yacht_id to its display name from TENANT yacht_registry.

    Returns None on miss or error. Safe to call with an empty / None id."""
    if not yacht_id:
        return None
    try:
        r = (
            supabase.table("yacht_registry")
            .select("id, name")
            .eq("id", yacht_id)
            .limit(1)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        if rows:
            return rows[0].get("name")
    except Exception as e:
        logger.warning("resolve_yacht_name: lookup failed for %s: %s", yacht_id, e)
    return None


def resolve_equipment_batch(
    supabase, yacht_id: str, equipment_ids: Iterable[str]
) -> list[dict]:
    """Hydrate an equipment-id array into frontend-friendly rows.

    One round-trip; filters soft-deleted rows. Returns a list shaped for
    RelatedEquipmentSection:
      `{id, equipment_id, code, name, manufacturer, description}`.
    Preserves the order of `equipment_ids` that survives the filter."""
    clean_ids: list[str] = [eid for eid in equipment_ids if eid]
    if not clean_ids:
        return []
    try:
        r = (
            supabase.table("pms_equipment")
            .select("id, code, name, manufacturer, description, deleted_at")
            .in_("id", clean_ids)
            .eq("yacht_id", yacht_id)
            .is_("deleted_at", None)
            .execute()
        )
        by_id = {row["id"]: row for row in (getattr(r, "data", None) or []) if row.get("id")}
    except Exception as e:
        logger.warning("resolve_equipment_batch: lookup failed: %s", e)
        return []

    out: list[dict] = []
    for eid in clean_ids:
        row = by_id.get(eid)
        if not row:
            continue
        out.append({
            "id": row["id"],
            "equipment_id": row["id"],
            "code": row.get("code") or "",
            "name": row.get("name") or "Equipment",
            "manufacturer": row.get("manufacturer") or "",
            "description": row.get("description") or "",
        })
    return out
