# Data Model

## Database Schema for Handover Export

This document defines the canonical database schema after Phase 1 cleanup.

---

## Schema Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ACTIVE DATA LAYER                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    FK    ┌─────────────────┐                           │
│  │  handovers  │─────────▶│  handover_items │                           │
│  │  (3 rows)   │          │   (13 rows)     │                           │
│  └─────────────┘          └─────────────────┘                           │
│        │                          │                                      │
│        │                          │ Formal shift handover flow          │
│        └──────────────────────────┘                                      │
│                                                                          │
│  ┌─────────────────┐                                                     │
│  │   pms_handover  │  Quick-add staging (standalone items)               │
│  │   (0 rows)      │                                                     │
│  └─────────────────┘                                                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     UNIFIED VIEW                                 │    │
│  │  v_handover_export_items  (combines both sources)               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                          DRAFT WORKFLOW LAYER                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐                                                    │
│  │  handover_drafts │◀─────────────────┬───────────────────────────┐    │
│  │  (state machine) │                  │                           │    │
│  └────────┬─────────┘                  │                           │    │
│           │                            │                           │    │
│           │ FK                         │ FK                        │ FK │
│           ▼                            ▼                           ▼    │
│  ┌────────────────────┐   ┌────────────────────┐   ┌─────────────────┐ │
│  │ handover_draft_    │   │ handover_draft_    │   │ handover_       │ │
│  │ sections           │   │ items              │   │ signoffs        │ │
│  │ (bucket groups)    │   │ (narrative items)  │   │ (dual sign)     │ │
│  └────────────────────┘   └─────────┬──────────┘   └─────────────────┘ │
│                                     │                                   │
│                                     │ FK                                │
│                                     ▼                                   │
│                           ┌────────────────────┐                        │
│                           │ handover_draft_    │                        │
│                           │ edits              │                        │
│                           │ (audit trail)      │                        │
│                           └────────────────────┘                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                          EXPORT LAYER                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐                                                    │
│  │ handover_exports │  PDF/HTML/Email records with storage paths        │
│  │ (audit + files)  │                                                    │
│  └──────────────────┘                                                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────┐                                              │
│  │  role_handover_buckets │  46 rows: role→bucket visibility config     │
│  │  (per-role buckets)    │                                              │
│  └────────────────────────┘                                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Table: handovers

**Purpose:** Container for a formal shift handover session.

```sql
CREATE TABLE handovers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id        UUID NOT NULL REFERENCES yacht_registry(id),
    title           TEXT NOT NULL,
    shift_date      DATE NOT NULL,
    shift_type      TEXT,  -- 'day', 'night', 'weekly'
    status          TEXT DEFAULT 'draft',  -- 'draft', 'completed', 'cancelled'

    -- Users
    created_by      UUID NOT NULL REFERENCES auth_users_profiles(id),
    from_user_id    UUID REFERENCES auth_users_profiles(id),
    to_user_id      UUID REFERENCES auth_users_profiles(id),
    approved_by     UUID REFERENCES auth_users_profiles(id),

    -- Timestamps
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,

    -- Metadata
    metadata        JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_handovers_yacht ON handovers(yacht_id);
CREATE INDEX idx_handovers_status ON handovers(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_handovers_shift_date ON handovers(shift_date);
```

---

## Table: handover_items

**Purpose:** Individual items within a formal handover.

```sql
CREATE TABLE handover_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    handover_id     UUID NOT NULL REFERENCES handovers(id),
    yacht_id        UUID NOT NULL REFERENCES yacht_registry(id),

    -- Entity reference
    entity_type     TEXT NOT NULL,  -- 'fault', 'work_order', 'equipment', 'document', 'general'
    entity_id       UUID,

    -- Content
    summary         TEXT NOT NULL,
    section         TEXT,           -- 'Engineering', 'Deck', etc.
    priority        INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending',  -- 'pending', 'acknowledged', 'completed', 'deferred'

    -- Acknowledgment
    acknowledged_by UUID REFERENCES auth_users_profiles(id),
    acknowledged_at TIMESTAMPTZ,

    -- Audit
    added_by        UUID NOT NULL REFERENCES auth_users_profiles(id),
    updated_by      UUID REFERENCES auth_users_profiles(id),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,

    metadata        JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_handover_items_handover ON handover_items(handover_id);
CREATE INDEX idx_handover_items_yacht ON handover_items(yacht_id);
CREATE INDEX idx_handover_items_entity ON handover_items(entity_type, entity_id);
CREATE INDEX idx_handover_items_status ON handover_items(status);
CREATE INDEX idx_handover_items_priority ON handover_items(priority);
```

---

## Table: pms_handover

**Purpose:** Quick-add staging for standalone handover notes (no parent handover required).

```sql
CREATE TABLE pms_handover (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id        UUID NOT NULL,

    -- Entity reference
    entity_type     TEXT NOT NULL,
    entity_id       UUID,

    -- Content
    summary_text    TEXT NOT NULL,
    category        TEXT,           -- 'urgent', 'in_progress', 'completed', 'watch', 'fyi'
    priority        INTEGER DEFAULT 0,

    -- Audit
    added_by        UUID NOT NULL REFERENCES auth_users_profiles(id),
    added_at        TIMESTAMPTZ DEFAULT now(),

    metadata        JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_pms_handover_yacht ON pms_handover(yacht_id, added_at DESC);
CREATE INDEX idx_pms_handover_entity ON pms_handover(entity_type, entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_pms_handover_urgent ON pms_handover(yacht_id, priority DESC, added_at DESC)
    WHERE category = 'urgent';
```

---

## View: v_handover_export_items

**Purpose:** Unified view combining both data sources for export pipeline.

```sql
CREATE OR REPLACE VIEW v_handover_export_items AS

-- Source 1: Formal shift handover items
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

-- Source 2: Quick-add staging items
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
```

---

## Table: handover_drafts

**Purpose:** Assembled draft document with state machine.

```sql
CREATE TABLE handover_drafts (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id                UUID NOT NULL,

    -- Period
    period_start            TIMESTAMPTZ NOT NULL,
    period_end              TIMESTAMPTZ NOT NULL,
    title                   TEXT,
    department              TEXT,  -- 'engineering', 'deck', 'all', etc.

    -- Generation
    generated_by_user_id    UUID,
    generation_method       TEXT DEFAULT 'manual',  -- 'manual', 'auto', 'import'

    -- State machine
    state                   TEXT NOT NULL DEFAULT 'DRAFT',
    -- CHECK (state IN ('DRAFT', 'IN_REVIEW', 'ACCEPTED', 'SIGNED', 'EXPORTED'))

    -- Counters
    total_entries           INTEGER DEFAULT 0,
    critical_count          INTEGER DEFAULT 0,

    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT now(),
    updated_at              TIMESTAMPTZ,

    metadata                JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_handover_drafts_yacht ON handover_drafts(yacht_id);
CREATE INDEX idx_handover_drafts_state ON handover_drafts(state);
CREATE INDEX idx_handover_drafts_period ON handover_drafts(period_start, period_end);
```

---

## Table: handover_draft_sections

**Purpose:** Presentation bucket sections within a draft.

```sql
CREATE TABLE handover_draft_sections (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id        UUID NOT NULL REFERENCES handover_drafts(id),

    bucket_name     TEXT NOT NULL,
    -- CHECK (bucket_name IN ('Command', 'Engineering', 'ETO_AVIT', 'Deck', 'Interior', 'Galley', 'Security', 'Admin_Compliance'))

    section_order   INTEGER NOT NULL,

    created_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE(draft_id, bucket_name)
);

CREATE INDEX idx_handover_draft_sections_draft ON handover_draft_sections(draft_id);
```

---

## Table: handover_draft_items

**Purpose:** Narrative items within a draft section.

```sql
CREATE TABLE handover_draft_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id            UUID NOT NULL REFERENCES handover_drafts(id),
    section_id          UUID REFERENCES handover_draft_sections(id),

    -- Content
    summary_text        TEXT NOT NULL,
    domain_code         TEXT,
    section_bucket      TEXT,
    item_order          INTEGER DEFAULT 0,

    -- Classification
    is_critical         BOOLEAN DEFAULT false,
    confidence_level    TEXT DEFAULT 'HIGH',  -- 'LOW', 'MEDIUM', 'HIGH'

    -- Source traceability
    source_entry_ids    UUID[],      -- References to handover_items/pms_handover
    source_event_ids    UUID[],      -- References to ledger events

    -- Edit tracking
    edit_count          INTEGER DEFAULT 0,

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ
);

CREATE INDEX idx_handover_draft_items_draft ON handover_draft_items(draft_id);
CREATE INDEX idx_handover_draft_items_section ON handover_draft_items(section_id);
CREATE INDEX idx_handover_draft_items_critical ON handover_draft_items(is_critical) WHERE is_critical = true;
```

---

## Table: handover_draft_edits

**Purpose:** Audit trail of human edits to draft items.

```sql
CREATE TABLE handover_draft_edits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id            UUID NOT NULL REFERENCES handover_drafts(id),
    draft_item_id       UUID NOT NULL REFERENCES handover_draft_items(id),

    -- Edit details
    edited_by_user_id   UUID NOT NULL,
    original_text       TEXT NOT NULL,
    edited_text         TEXT NOT NULL,
    edit_reason         TEXT,

    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_handover_draft_edits_draft ON handover_draft_edits(draft_id);
CREATE INDEX idx_handover_draft_edits_item ON handover_draft_edits(draft_item_id);
```

---

## Table: handover_signoffs

**Purpose:** Dual sign-off for responsibility transfer.

```sql
CREATE TABLE handover_signoffs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id            UUID NOT NULL REFERENCES handover_drafts(id) UNIQUE,
    yacht_id            UUID NOT NULL,

    -- Outgoing officer
    outgoing_user_id    UUID NOT NULL,
    outgoing_signed_at  TIMESTAMPTZ NOT NULL,

    -- Incoming officer
    incoming_user_id    UUID,
    incoming_signed_at  TIMESTAMPTZ,

    -- Integrity
    document_hash       TEXT NOT NULL,

    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_handover_signoffs_draft ON handover_signoffs(draft_id);
CREATE INDEX idx_handover_signoffs_yacht ON handover_signoffs(yacht_id);
```

---

## Table: handover_exports

**Purpose:** Tracks exported artifacts (PDF/HTML/Email).

```sql
CREATE TABLE handover_exports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    draft_id            UUID NOT NULL REFERENCES handover_drafts(id),
    yacht_id            UUID NOT NULL,

    -- Export details
    export_type         TEXT NOT NULL,  -- 'pdf', 'html', 'email'
    export_status       TEXT DEFAULT 'pending',  -- 'pending', 'completed', 'failed'

    -- Storage
    storage_path        TEXT,
    file_name           TEXT,
    file_size_bytes     INTEGER,

    -- Email-specific
    recipients          TEXT[],
    email_sent_at       TIMESTAMPTZ,

    -- Integrity
    document_hash       TEXT NOT NULL,

    -- Audit
    exported_by_user_id UUID NOT NULL,
    exported_at         TIMESTAMPTZ DEFAULT now(),

    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_handover_exports_draft ON handover_exports(draft_id);
CREATE INDEX idx_handover_exports_yacht ON handover_exports(yacht_id);
CREATE INDEX idx_handover_exports_type ON handover_exports(export_type);
```

---

## Table: role_handover_buckets

**Purpose:** Configuration for which buckets each role sees.

```sql
-- Already exists with 46 rows configured
-- Defines per-role bucket visibility and ordering

SELECT role_id, department, array_agg(bucket_name ORDER BY bucket_order) as buckets
FROM role_handover_buckets
GROUP BY role_id, department;

-- Example output:
-- chief_engineer | engineering | {Active Faults, Work Orders In Progress, Pending Parts, ...}
-- captain        | command     | {Safety & Compliance, Department Summaries, Critical Faults, ...}
-- bosun          | deck        | {Deck Status, Tender Operations, Scheduled Activities, ...}
```

---

## Tables Dropped (Phase 1 Cleanup)

The following tables were removed as orphaned/unused:

| Table | Reason |
|-------|--------|
| `dash_handover_records` | yacht_id was TEXT not UUID, broken schema |
| `dash_handover_items` | Orphaned, code blocked |
| `handover_entries` | No FKs, no production usage |
| `handover_sources` | No code references (backup retained for future email provenance) |

Backups available: `_bkp_dash_handover_records`, `_bkp_dash_handover_items`, `_bkp_handover_entries`, `_bkp_handover_sources`

---

## Enums (CHECK Constraints)

```sql
-- Draft state machine
handover_draft_state: DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED

-- Export types
export_type: pdf | html | email

-- Item status
handover_item_status: pending | acknowledged | completed | deferred

-- Presentation buckets
presentation_bucket: Command | Engineering | ETO_AVIT | Deck | Interior | Galley | Security | Admin_Compliance

-- Risk tags
risk_tags: Safety_Critical | Compliance_Critical | Guest_Impacting | Cost_Impacting | Operational_Debt | Informational
```

---
