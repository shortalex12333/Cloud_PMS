# Work Order Lens P1: Show Related — PHASE 3: ENTITY GRAPH

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Define the **entity relationship graph** and **match reason taxonomy** for deterministic related entity discovery.

---

## Entity Types

```
work_order → Central entity
  ├─ part (via pms_work_order_parts)
  ├─ equipment (via FK work_orders.equipment_id)
  ├─ fault (via FK work_orders.fault_id)
  ├─ document (via pms_work_order_attachments)
  └─ entity_link (via pms_entity_links, user-created)

equipment
  ├─ document (manuals, handovers via doc.equipment_id)
  └─ work_order (other WOs on same equipment)

fault
  └─ work_order (other WOs from same fault)
```

---

## Match Reason Taxonomy

### FK-Based (Highest Priority)

**FK:wo_part**
- **Source:** `pms_work_order_parts` join table
- **Description:** Part is directly linked to this work order via parts list
- **Weight:** 100

**FK:equipment**
- **Source:** `pms_documents.equipment_id = pms_work_orders.equipment_id`
- **Description:** Document (manual/handover) is linked to the same equipment
- **Weight:** 90

**FK:wo_attachment**
- **Source:** `pms_work_order_attachments` join table
- **Description:** Document is attached to this work order
- **Weight:** 100

### Derived Relationships (Medium Priority)

**same_equipment**
- **Source:** `pms_work_orders` where `equipment_id` matches
- **Description:** Another work order on the same equipment
- **Weight:** 80

**same_fault**
- **Source:** `pms_work_orders` where `fault_id` matches
- **Description:** Another work order created from the same fault report
- **Weight:** 75

### Explicit Links (User-Created)

**explicit_link**
- **Source:** `pms_entity_links` where user manually added link
- **Description:** Manually linked by HOD/manager
- **Weight:** 70

### Optional: Mentions (Future)

**mentions:WO-123**
- **Source:** Full-text search in descriptions (Phase 2+)
- **Description:** Document or WO description mentions this work order number
- **Weight:** 50
- **Status:** Out of scope for P1

---

## Relationship Queries (Deterministic)

### 1. Parts for Work Order
**Match Reason:** `FK:wo_part`

```sql
SELECT
  p.id AS entity_id,
  'part' AS entity_type,
  p.name AS title,
  p.part_number AS subtitle,
  ARRAY['FK:wo_part'] AS match_reasons,
  100 AS weight
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = :work_order_id
  AND wop.yacht_id = get_user_yacht_id()
ORDER BY p.name
LIMIT 10;
```

### 2. Manuals for Work Order (via Equipment)
**Match Reason:** `FK:equipment`

```sql
SELECT
  d.id AS entity_id,
  'manual' AS entity_type,
  d.title,
  e.name AS subtitle,  -- Equipment name
  ARRAY['FK:equipment'] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE wo.id = :work_order_id
  AND d.doc_type = 'manual'
  AND wo.yacht_id = get_user_yacht_id()
ORDER BY d.title
LIMIT 10;
```

### 3. Previous Work Orders (Same Equipment)
**Match Reason:** `same_equipment`

```sql
SELECT
  wo2.id AS entity_id,
  'work_order' AS entity_type,
  wo2.number || ': ' || wo2.title AS title,
  TO_CHAR(wo2.created_at, 'YYYY-MM-DD') AS subtitle,
  ARRAY['same_equipment'] AS match_reasons,
  80 AS weight
FROM pms_work_orders wo1
JOIN pms_work_orders wo2 ON wo2.equipment_id = wo1.equipment_id
WHERE wo1.id = :work_order_id
  AND wo2.id != :work_order_id
  AND wo2.deleted_at IS NULL
  AND wo1.yacht_id = get_user_yacht_id()
ORDER BY wo2.created_at DESC
LIMIT 10;
```

### 4. Handovers (via Equipment)
**Match Reason:** `FK:equipment`

```sql
SELECT
  d.id AS entity_id,
  'handover' AS entity_type,
  d.title,
  e.name AS subtitle,
  ARRAY['FK:equipment'] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE wo.id = :work_order_id
  AND d.doc_type = 'handover'
  AND wo.yacht_id = get_user_yacht_id()
ORDER BY d.created_at DESC
LIMIT 10;
```

### 5. Attachments
**Match Reason:** `FK:wo_attachment`

```sql
SELECT
  d.id AS entity_id,
  'attachment' AS entity_type,
  d.title,
  d.mime_type AS subtitle,
  ARRAY['FK:wo_attachment'] AS match_reasons,
  100 AS weight
FROM pms_work_order_attachments woa
JOIN pms_documents d ON d.id = woa.document_id
WHERE woa.work_order_id = :work_order_id
  AND woa.yacht_id = get_user_yacht_id()
ORDER BY woa.created_at DESC
LIMIT 10;
```

### 6. Explicit Links (User-Created)
**Match Reason:** `explicit_link`

```sql
SELECT
  el.target_entity_id AS entity_id,
  el.target_entity_type AS entity_type,
  el.note AS title,
  'Manually linked' AS subtitle,
  ARRAY['explicit_link'] AS match_reasons,
  70 AS weight
FROM pms_entity_links el
WHERE el.source_entity_type = 'work_order'
  AND el.source_entity_id = :work_order_id
  AND el.yacht_id = get_user_yacht_id()
ORDER BY el.created_at DESC;
```

---

## Merge & Rank Strategy

### 1. Collect All Results
Run all 6 queries in parallel (or sequentially if DB load is low)

### 2. Group by Entity Type
```python
groups = {
  "parts": [],
  "manuals": [],
  "previous_work": [],
  "handovers": [],
  "attachments": []
}
```

### 3. Deduplicate
If an entity appears in multiple result sets (e.g., explicit link + FK), merge match_reasons:

```python
# Example: Part appears in both FK and explicit link
{
  "entity_id": "part-uuid",
  "entity_type": "part",
  "title": "MTU Oil Filter",
  "match_reasons": ["FK:wo_part", "explicit_link"],  # Merged
  "weight": 100  # Take highest weight
}
```

### 4. Sort Within Group
Sort by weight (descending), then by title (ascending)

### 5. Limit Results
Top 10 per group (prevent unbounded result sets)

---

## Response Structure

```json
{
  "status": "success",
  "groups": [
    {
      "group_key": "parts",
      "label": "Parts",
      "count": 3,
      "items": [
        {
          "entity_type": "part",
          "entity_id": "uuid",
          "title": "MTU Oil Filter",
          "subtitle": "Part #: 12345-ABC",
          "match_reasons": ["FK:wo_part"],
          "weight": 100,
          "open_action": "focus"
        }
      ]
    },
    {
      "group_key": "manuals",
      "label": "Manuals",
      "count": 2,
      "items": [...]
    },
    {
      "group_key": "previous_work",
      "label": "Previous Work Orders",
      "count": 5,
      "items": [...]
    },
    {
      "group_key": "handovers",
      "label": "Handovers",
      "count": 1,
      "items": [...]
    },
    {
      "group_key": "attachments",
      "label": "Attachments",
      "count": 4,
      "items": [...]
    }
  ],
  "add_related_enabled": true,  # HOD/manager check
  "missing_signals": []          # Optional: hints for empty groups
}
```

---

## Edge Cases

### Empty Groups
If a group has no results, still include it with `count: 0, items: []`

### Equipment-less Work Order
If `work_orders.equipment_id IS NULL`, skip manuals/handovers/previous_work queries

### Deleted Entities
Filter out `deleted_at IS NOT NULL` in all queries

### Cross-Yacht Entities
**Never return.** All queries enforced with `yacht_id = get_user_yacht_id()`

---

## Performance Considerations

### Indexes Required
- `pms_work_order_parts(work_order_id, yacht_id)`
- `pms_work_orders(equipment_id, yacht_id)`
- `pms_documents(equipment_id, doc_type, yacht_id)`
- `pms_work_order_attachments(work_order_id, yacht_id)`
- `pms_entity_links(source_entity_type, source_entity_id, yacht_id)`

### Query Optimization
- Use `LIMIT 10` on all sub-queries
- Use indexed columns in WHERE clauses
- Avoid full table scans (filter by yacht_id + entity_id)
- Consider materialized views if queries >500ms

### Result Set Size
- Max 5 groups × 10 items = 50 entities per response
- Typical payload: ~5-15 KB JSON

---

## Next Phase

**PHASE 4: ACTIONS** - Define registry entries and handler signatures.

---

**ENTITY GRAPH STATUS:** ✅ DEFINED
