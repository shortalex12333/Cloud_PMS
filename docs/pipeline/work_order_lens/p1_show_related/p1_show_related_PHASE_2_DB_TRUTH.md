# Work Order Lens P1: Show Related — PHASE 2: DB TRUTH

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Map the **actual database schema** for all tables involved in "Show Related" feature. This is the single source of truth for FK relationships, columns, and constraints.

---

## Core Tables

### pms_work_orders
**Purpose:** Work orders (source entity for related lookups)

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL (FK → yachts)
equipment_id        UUID (FK → pms_equipment)
fault_id            UUID (FK → pms_faults)
assigned_to         UUID (FK → users)
number              TEXT (e.g., "WO-2024-001")
title               TEXT NOT NULL
description         TEXT
priority            TEXT (routine|urgent|critical)
status              TEXT (open|in_progress|completed|cancelled)
due_at              TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ
deleted_at          TIMESTAMPTZ
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id, status, deleted_at)
- INDEX on (equipment_id) -- for equipment-based related queries
- INDEX on (fault_id) -- for fault-based related queries

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_work_order_parts
**Purpose:** Join table linking work orders to parts

**Columns:**
```sql
id                  UUID PRIMARY KEY
work_order_id       UUID NOT NULL (FK → pms_work_orders)
part_id             UUID NOT NULL (FK → pms_parts)
yacht_id            UUID NOT NULL (FK → yachts)
quantity            INTEGER
unit_cost           NUMERIC
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (work_order_id) -- critical for related parts query
- INDEX on (part_id)
- INDEX on (yacht_id)

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_parts
**Purpose:** Parts/inventory items

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL
part_number         TEXT
name                TEXT NOT NULL
description         TEXT
category            TEXT
location            TEXT
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id, part_number)

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_equipment
**Purpose:** Equipment/systems on yacht

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL
name                TEXT NOT NULL
equipment_type      TEXT
location            TEXT
manufacturer        TEXT
model_number        TEXT
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id)

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_faults
**Purpose:** Fault reports (source for work orders)

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL
equipment_id        UUID (FK → pms_equipment)
title               TEXT NOT NULL
description         TEXT
status              TEXT (open|in_progress|resolved|closed)
severity            TEXT (low|medium|high|critical)
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id, status)
- INDEX on (equipment_id)

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_documents (or pms_doc_metadata)
**Purpose:** Document metadata (manuals, handovers, attachments)

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL
title               TEXT NOT NULL
doc_type            TEXT (manual|handover|attachment|other)
equipment_id        UUID (FK → pms_equipment) -- for manuals/handovers
file_path           TEXT (storage path)
mime_type           TEXT
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id, doc_type)
- INDEX on (equipment_id) -- for equipment-based doc queries

**RLS:** `yacht_id = get_user_yacht_id()`

**Note:** Only return metadata. No presigned URLs unless storage policy allows.

---

### pms_work_order_attachments
**Purpose:** Join table linking work orders to document attachments

**Columns:**
```sql
id                  UUID PRIMARY KEY
work_order_id       UUID NOT NULL (FK → pms_work_orders)
document_id         UUID NOT NULL (FK → pms_documents)
yacht_id            UUID NOT NULL
attached_by         UUID (user_id)
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (work_order_id) -- critical for related attachments query
- INDEX on (document_id)

**RLS:** `yacht_id = get_user_yacht_id()`

---

### pms_entity_links
**Purpose:** Explicit links between entities (user-created)

**Columns:**
```sql
id                      UUID PRIMARY KEY
yacht_id                UUID NOT NULL
source_entity_type      TEXT NOT NULL (work_order|part|equipment|manual|...)
source_entity_id        UUID NOT NULL
target_entity_type      TEXT NOT NULL
target_entity_id        UUID NOT NULL
link_type               TEXT DEFAULT 'explicit' (explicit|reference|dependency)
note                    TEXT
created_by              UUID (user_id)
created_at              TIMESTAMPTZ DEFAULT NOW()
```

**Indexes:**
- PRIMARY KEY (id)
- INDEX on (yacht_id, source_entity_type, source_entity_id) -- critical for related queries
- INDEX on (target_entity_type, target_entity_id)
- UNIQUE INDEX on (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type) -- prevent duplicates

**RLS:**
- SELECT: `yacht_id = get_user_yacht_id()`
- INSERT: `(is_hod() OR is_manager()) AND yacht_id = get_user_yacht_id()`
- UPDATE/DELETE: Same as INSERT

**Note:** Deployed in P0 migrations.

---

## FK Relationships (for Related Queries)

### Parts Related to Work Order
```sql
SELECT p.*
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = :work_order_id
  AND wop.yacht_id = get_user_yacht_id();
```

### Manuals Related to Work Order (via Equipment)
```sql
SELECT d.*
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE wo.id = :work_order_id
  AND d.doc_type = 'manual'
  AND wo.yacht_id = get_user_yacht_id();
```

### Previous Work on Same Equipment
```sql
SELECT wo2.*
FROM pms_work_orders wo1
JOIN pms_work_orders wo2 ON wo2.equipment_id = wo1.equipment_id
WHERE wo1.id = :work_order_id
  AND wo2.id != :work_order_id
  AND wo2.deleted_at IS NULL
  AND wo1.yacht_id = get_user_yacht_id()
ORDER BY wo2.created_at DESC
LIMIT 10;
```

### Attachments for Work Order
```sql
SELECT d.*
FROM pms_work_order_attachments woa
JOIN pms_documents d ON d.id = woa.document_id
WHERE woa.work_order_id = :work_order_id
  AND woa.yacht_id = get_user_yacht_id();
```

### Explicit Links (User-Created)
```sql
SELECT *
FROM pms_entity_links
WHERE source_entity_type = 'work_order'
  AND source_entity_id = :work_order_id
  AND yacht_id = get_user_yacht_id();
```

---

## Optional Views (Simplify Queries)

### v_related_parts_for_wo
**Purpose:** Pre-join work_order_parts with parts

```sql
CREATE OR REPLACE VIEW public.v_related_parts_for_wo AS
SELECT
  wop.work_order_id,
  wop.yacht_id,
  p.id AS part_id,
  p.part_number,
  p.name AS part_name,
  p.description,
  wop.quantity,
  'FK:wo_part' AS match_reason
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id;
```

**RLS:** Same as base tables (`yacht_id = get_user_yacht_id()`)

### v_related_docs_for_wo
**Purpose:** Pre-join work orders with manuals/handovers via equipment

```sql
CREATE OR REPLACE VIEW public.v_related_docs_for_wo AS
SELECT
  wo.id AS work_order_id,
  wo.yacht_id,
  d.id AS doc_id,
  d.title AS doc_title,
  d.doc_type,
  d.equipment_id,
  CASE
    WHEN d.doc_type = 'manual' THEN 'FK:equipment'
    WHEN d.doc_type = 'handover' THEN 'FK:equipment'
    ELSE 'FK:other'
  END AS match_reason
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE d.doc_type IN ('manual', 'handover');
```

**RLS:** Same as base tables

**Decision:** Create views **only if** handler queries become complex. Otherwise, keep logic in app code using Supabase client queries.

---

## RLS Policy Summary

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| pms_work_orders | yacht_id | yacht_id + role | yacht_id + role | yacht_id + role |
| pms_work_order_parts | yacht_id | yacht_id + HOD/manager | yacht_id + HOD/manager | yacht_id + HOD/manager |
| pms_parts | yacht_id | yacht_id + HOD/manager | yacht_id + HOD/manager | yacht_id + HOD/manager |
| pms_equipment | yacht_id | yacht_id + HOD/manager | yacht_id + HOD/manager | No |
| pms_documents | yacht_id | yacht_id + role | yacht_id + role | yacht_id + role |
| pms_entity_links | yacht_id | yacht_id + HOD/manager | yacht_id + HOD/manager | yacht_id + HOD/manager |

**Key Helper:** `get_user_yacht_id()` - Returns yacht_id from JWT claim or session

---

## Audit Log

### pms_audit_log
**Purpose:** Record all mutations (add_entity_link)

**Columns:**
```sql
id                  UUID PRIMARY KEY
yacht_id            UUID NOT NULL
user_id             UUID NOT NULL
action              TEXT (e.g., 'add_entity_link')
entity_type         TEXT (e.g., 'entity_link')
entity_id           UUID (link_id)
signature           JSONB ({} for non-signed actions)
metadata            JSONB (source/target entity info)
created_at          TIMESTAMPTZ DEFAULT NOW()
```

**Entry Example:**
```json
{
  "action": "add_entity_link",
  "entity_type": "entity_link",
  "entity_id": "link-uuid",
  "signature": {},
  "metadata": {
    "source_entity_type": "work_order",
    "source_entity_id": "wo-uuid",
    "target_entity_type": "manual",
    "target_entity_id": "manual-uuid"
  }
}
```

---

## Next Phase

**PHASE 3: ENTITY GRAPH** - Map entity relationships and match reason taxonomy.

---

**DB TRUTH STATUS:** ✅ MAPPED
