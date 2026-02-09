# Compatibility Bridge

## Legacy Table Migration and Coexistence

This document defines how existing handover data integrates with the new draft workflow.

---

## Current State

### Active Tables

| Table | Rows | Usage | Code References |
|-------|------|-------|-----------------|
| `handovers` | 3 | Shift container | p0_actions_routes.py |
| `handover_items` | 13 | Entity items | fault_mutation_handlers.py |
| `pms_handover` | 0 | Quick-add staging | handover_handlers.py |

### Draft Tables (Ready, Empty)

| Table | Rows | Status |
|-------|------|--------|
| `handover_drafts` | 0 | Ready for use |
| `handover_draft_sections` | 0 | Ready |
| `handover_draft_items` | 0 | Ready |
| `handover_draft_edits` | 0 | Ready |
| `handover_signoffs` | 0 | Ready |
| `handover_exports` | 0 | Ready |

---

## Bridge Strategy

### Phase 1: Parallel Operation (Now → +30 days)

Both systems operate simultaneously:

```
                   ┌─────────────────────────┐
                   │      User Actions       │
                   └───────────┬─────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
    │ add_to_handover │ │ pms_handover│ │ export_handover │
    │ (existing)      │ │ quick-add   │ │ (new draft)     │
    └────────┬────────┘ └──────┬──────┘ └────────┬────────┘
             │                 │                  │
             ▼                 ▼                  │
    ┌─────────────────────────────────────┐      │
    │       v_handover_export_items       │◀─────┘
    │       (unified view)                │
    └─────────────────────────────────────┘
                               │
                               ▼
                   ┌─────────────────────────┐
                   │    Draft Generation     │
                   │    (new workflow)       │
                   └─────────────────────────┘
```

**Key:** The unified view `v_handover_export_items` combines both sources, allowing the new export pipeline to read from all data regardless of origin.

### Phase 2: Gradual Migration (Days 30-60)

Migrate code paths from `pms_handover` to `handover_items`:

| Code Path | Current | Target |
|-----------|---------|--------|
| `add_to_handover` action | Writes to `pms_handover` | Writes to `handover_items` |
| P3 `export_handover_execute` | Reads from `pms_handover` | Reads from unified view |
| Fault mutation handlers | Writes to `handover_items` | No change |

### Phase 3: Deprecation (Days 60-90)

1. Stop writing to `pms_handover`
2. Migrate any remaining `pms_handover` rows to `handover_items`
3. Update RLS policies
4. Archive `pms_handover` (don't drop immediately)

---

## Import Functions

### Import from Legacy Handover

```python
async def import_legacy_handover(
    handover_id: str,
    yacht_id: str,
    user_id: str
) -> str:
    """
    Import existing handovers + handover_items into draft workflow.

    Args:
        handover_id: Legacy handover to import
        yacht_id: Yacht context
        user_id: User performing import

    Returns:
        draft_id: New draft ID

    Flow:
        1. Fetch handover record
        2. Fetch all handover_items for this handover
        3. Create handover_drafts record
        4. Create handover_draft_sections (group by section)
        5. Create handover_draft_items (from items)
        6. Link source_entry_ids back to original
    """

    # 1. Fetch legacy handover
    handover = await db.table("handovers").select("*").eq("id", handover_id).single().execute()
    if not handover.data:
        raise ValueError(f"Handover {handover_id} not found")

    # 2. Fetch items
    items = await db.table("handover_items").select("*").eq("handover_id", handover_id).execute()

    # 3. Create draft
    draft_id = str(uuid4())
    await db.table("handover_drafts").insert({
        "id": draft_id,
        "yacht_id": yacht_id,
        "period_start": handover.data["shift_date"],
        "period_end": handover.data["shift_date"],
        "title": f"Imported: {handover.data['title']}",
        "generated_by_user_id": user_id,
        "generation_method": "import",
        "state": "DRAFT",
        "total_entries": len(items.data or []),
        "metadata": {"imported_from": handover_id}
    }).execute()

    # 4. Group items by section
    sections = {}
    for item in items.data or []:
        section = item.get("section") or "General"
        if section not in sections:
            sections[section] = []
        sections[section].append(item)

    # 5. Create sections and items
    section_order = 1
    for section_name, section_items in sections.items():
        section_id = str(uuid4())
        await db.table("handover_draft_sections").insert({
            "id": section_id,
            "draft_id": draft_id,
            "bucket_name": map_section_to_bucket(section_name),
            "section_order": section_order
        }).execute()

        item_order = 1
        for item in section_items:
            await db.table("handover_draft_items").insert({
                "id": str(uuid4()),
                "draft_id": draft_id,
                "section_id": section_id,
                "summary_text": item["summary"],
                "domain_code": item.get("entity_type", "").upper(),
                "is_critical": item.get("priority", 0) >= 3,
                "source_entry_ids": [item["id"]],
                "item_order": item_order
            }).execute()
            item_order += 1

        section_order += 1

    return draft_id


def map_section_to_bucket(section: str) -> str:
    """Map legacy section names to standard buckets."""
    mapping = {
        "Engineering": "Engineering",
        "Equipment Status": "Engineering",
        "Outstanding Issues": "Command",
        "In Progress": "Engineering",
        "Notes": "Admin_Compliance",
        "Deck": "Deck",
        "Issues": "Command",
    }
    return mapping.get(section, "Command")
```

---

### Import from Quick-Add

```python
async def import_quickadd_items(
    yacht_id: str,
    user_id: str,
    date_from: date,
    date_to: date,
    draft_id: str = None
) -> dict:
    """
    Import pms_handover items into draft workflow.

    If draft_id provided, adds to existing draft.
    Otherwise creates new draft.

    Returns:
        {"draft_id": str, "imported_count": int}
    """

    # Fetch quick-add items
    items = await db.table("pms_handover").select("*") \
        .eq("yacht_id", yacht_id) \
        .gte("added_at", date_from.isoformat()) \
        .lte("added_at", date_to.isoformat()) \
        .execute()

    if not items.data:
        raise ValueError("No items found in date range")

    # Create or use existing draft
    if not draft_id:
        draft_id = str(uuid4())
        await db.table("handover_drafts").insert({
            "id": draft_id,
            "yacht_id": yacht_id,
            "period_start": date_from.isoformat(),
            "period_end": date_to.isoformat(),
            "title": f"Handover {date_from} - {date_to}",
            "generated_by_user_id": user_id,
            "generation_method": "import_quickadd",
            "state": "DRAFT",
            "total_entries": len(items.data)
        }).execute()

    # Group by category → bucket
    category_to_bucket = {
        "urgent": "Command",
        "in_progress": "Engineering",
        "completed": "Admin_Compliance",
        "watch": "Engineering",
        "fyi": "Admin_Compliance",
    }

    sections = {}
    for item in items.data:
        bucket = category_to_bucket.get(item.get("category"), "Command")
        if bucket not in sections:
            sections[bucket] = []
        sections[bucket].append(item)

    # Create sections and items
    imported = 0
    for bucket, bucket_items in sections.items():
        section = await get_or_create_section(draft_id, bucket)

        for item in bucket_items:
            await db.table("handover_draft_items").insert({
                "id": str(uuid4()),
                "draft_id": draft_id,
                "section_id": section["id"],
                "summary_text": item["summary_text"],
                "domain_code": item.get("entity_type", "").upper(),
                "is_critical": item.get("priority", 0) >= 3,
                "source_entry_ids": [item["id"]],
                "item_order": await get_next_item_order(section["id"])
            }).execute()
            imported += 1

    return {"draft_id": draft_id, "imported_count": imported}
```

---

## Unified View Definition

The `v_handover_export_items` view enables reading from all sources:

```sql
CREATE OR REPLACE VIEW v_handover_export_items AS

-- Source 1: Formal shift handover items (handovers + handover_items)
SELECT
    hi.id,
    hi.yacht_id,
    h.id as handover_id,
    h.title as handover_title,
    h.shift_date,
    h.shift_type,
    hi.entity_type,
    hi.entity_id,
    hi.summary as summary_text,
    hi.section as category,
    hi.priority,
    hi.status,
    hi.added_by,
    hi.created_at as added_at,
    hi.acknowledged_by,
    hi.acknowledged_at,
    hi.metadata,
    'handover_items' as source_table,
    COALESCE(h.status, 'draft') as handover_status
FROM handover_items hi
JOIN handovers h ON hi.handover_id = h.id
WHERE hi.deleted_at IS NULL AND h.deleted_at IS NULL

UNION ALL

-- Source 2: Quick-add staging items (pms_handover - standalone)
SELECT
    ph.id,
    ph.yacht_id,
    NULL::uuid as handover_id,
    NULL as handover_title,
    ph.added_at::date as shift_date,
    NULL as shift_type,
    ph.entity_type,
    ph.entity_id,
    ph.summary_text,
    ph.category,
    ph.priority,
    'pending' as status,
    ph.added_by,
    ph.added_at,
    NULL::uuid as acknowledged_by,
    NULL::timestamptz as acknowledged_at,
    ph.metadata,
    'pms_handover' as source_table,
    'quick_add' as handover_status
FROM pms_handover ph;

-- Grant access
GRANT SELECT ON v_handover_export_items TO authenticated;
GRANT SELECT ON v_handover_export_items TO service_role;
```

---

## Migration Timeline

| Week | Action | Risk | Rollback |
|------|--------|------|----------|
| 1 | Deploy unified view | Low | Drop view |
| 2 | Deploy new export endpoints | Low | Feature flag off |
| 3 | Enable export for beta users | Medium | Revert to old handler |
| 4 | Update add_to_handover to use handover_items | Medium | Revert handler |
| 6 | Stop writing to pms_handover | High | Re-enable writes |
| 8 | Migrate remaining pms_handover data | Medium | SQL rollback |
| 10 | Archive pms_handover table | Low | Restore from archive |

---

## Coexistence Rules

During parallel operation:

1. **Reading:** Always use `v_handover_export_items` for export
2. **Writing:** Continue writing to existing paths (no disruption)
3. **New exports:** Use draft workflow (handover_drafts chain)
4. **Legacy exports:** Old handler continues working (reads pms_handover directly)

---
