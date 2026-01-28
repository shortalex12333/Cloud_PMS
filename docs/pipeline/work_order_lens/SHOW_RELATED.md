# Show Related — Deterministic Context Panel (Work Orders)

What it is
- Side panel (not navigation) that expands context for the focused entity (WO/equipment/fault/part).
- Deterministic retrieval only; no guesses, no severity banners, no invented actions.

Inputs (from focused entity + DB)
- Focused: `entity_type`, `entity_id`, `yacht_id`.
- Facts (for WO): `title`, `description`, `equipment_id`, `fault_id`, `priority`, `status`, metadata (system tags, model, vendor), linked (parts lines, attachments, notes).
- Derived tokens: equipment name/model, system name, part numbers, canonical title keywords.

Retrieval (ranked buckets)
1) FK joins (strongest): WO→parts, equipment, fault, notes, attachments.
2) Similarity (entity‑fields only): embedding built from known fields (no user text), used to rank within each bucket.
3) Heuristic boosts: same equipment, same system tag, same manufacturer+part_number, recent handovers.

Output contract
```
{
  "focused": {"entity_type": "work_order", "entity_id": "..."},
  "groups": [
    {"type": "parts", "items": [{"entity_type":"part","entity_id":"...","title":"...","match_reasons":["FK:wo_part"],"open_action":"focus"}]},
    {"type": "manuals", "items": [...]},
    {"type": "previous_work", "items": [...]},
    {"type": "handovers", "items": [...]},
    {"type": "attachments", "items": [...]}
  ],
  "add_related_enabled": true,
  "missing_signals": ["no equipment_id on WO"]
}
```

Add related items (user‑driven)
- Opens global search in selection mode; user selects items; backend writes `pms_entity_links` rows.

Storage
- Respect storage policies: reading doc/file requires independent Storage RLS; if not allowed, show metadata only.

RLS & actions
- Results already filtered by RLS; no actions are surfaced here unless user intent is explicit.

DB support table (see migration 20260127_105_create_pms_entity_links.sql)
- `pms_entity_links`: id, yacht_id, source_entity_type/id, target_entity_type/id, link_type, created_by, created_at, note.
- RLS: yacht‑scoped; writes require HOD/manager.

