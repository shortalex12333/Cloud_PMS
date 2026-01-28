# SCHEMA GAPS — Required Migrations (Architecture)

**Date:** 2026-01-22
**Purpose:** Authoritative list of schema gaps identified by cross-referencing ACTION_IO_MATRIX with DB_TRUTH_PACK
**Status:** Ready for DB migration planning

---

## METHODOLOGY

Cross-referenced ACTION_IO_MATRIX.md (action contracts) against DB_TRUTH_PACK.md (actual schema).

For each mismatch, categorized as:
- **(A) RESOLVE** - Change action contract to use existing table/columns
- **(B) MIGRATE** - Schema migration required (exact columns specified)

---

## SUMMARY STATISTICS

**Total Actions Audited:** 63
**Actions with Verified Schema:** 39 (62%)
**Actions Requiring Resolution:** 12 (19%)
**Actions Requiring Migration:** 12 (19%)

---

## CATEGORY A: RESOLVE (Change Action Contract)

These actions reference tables/columns that don't exist, BUT can be resolved by using existing schema.

### A1: diagnose_fault — Use `metadata` JSONB

**Current Contract (ACTION_IO_MATRIX):**
```
Writes: pms_faults(~diagnosis, ~diagnosis_notes, ~diagnosed_by, ~diagnosed_at)
```

**DB Truth:**
- `pms_faults` table exists
- Columns `diagnosis`, `diagnosis_notes`, `diagnosed_by`, `diagnosed_at` do NOT exist
- Column `metadata` JSONB DEFAULT '{}' EXISTS

**Resolution:**
```
Writes: pms_faults(~metadata->'diagnosis', ~updated_at, ~updated_by)
```

**Pattern:**
Store diagnosis in `metadata.diagnosis = {notes, diagnosed_by, diagnosed_at, findings}`

---

### A2: add_fault_note — Use Fault Notes in `metadata`

**Current Contract:**
```
Writes: pms_faults(~updated_at, ~updated_by)
Assumption: Separate fault_notes table (not found)
```

**DB Truth:**
- No `fault_notes` table exists (work_order_notes exists, but not fault_notes)
- `pms_faults.metadata` JSONB exists

**Resolution:**
```
Writes: pms_faults(~metadata->'notes'[], ~updated_at, ~updated_by)
```

**Pattern:**
Store notes array in `metadata.notes = [{note_text, created_by, created_at}, ...]`

**Alternative:** Create `pms_fault_notes` table mirroring `work_order_notes` structure.

---

### A3: start_work_order — Use `metadata` or Accept Missing

**Current Contract:**
```
Writes: pms_work_orders(~status, ~started_at, ~started_by)
```

**DB Truth:**
- `started_at`, `started_by` columns do NOT exist
- `pms_work_orders.metadata` JSONB exists

**Resolution Option 1 (Use existing):**
```
Writes: pms_work_orders(~status='in_progress', ~updated_at, ~updated_by)
```
Accept that "started" is implied by status change to 'in_progress'.

**Resolution Option 2 (Use metadata):**
```
Writes: pms_work_orders(~status, ~metadata->'started_at', ~metadata->'started_by', ~updated_at)
```

**Recommended:** Option 1 (use status transition only).

---

### A4: add_wo_hours — Use `metadata` for Hours Tracking

**Current Contract:**
```
Writes: pms_work_orders(~hours_logged, ~updated_at, ~updated_by)
```

**DB Truth:**
- `hours_logged` column does NOT exist
- `pms_work_orders.metadata` JSONB exists

**Resolution:**
```
Writes: pms_work_orders(~metadata->'hours_logged', ~updated_at, ~updated_by)
```

**Alternative:** Create separate `work_order_time_log` table for detailed time tracking.

---

### A5: close_fault — Use `resolved_at` as Proxy

**Current Contract:**
```
Writes: pms_faults(~status='closed', ~closed_at, ~closed_by)
```

**DB Truth:**
- `closed_at`, `closed_by` columns do NOT exist
- `resolved_at` column EXISTS

**Resolution:**
```
Writes: pms_faults(~status='closed', ~updated_at, ~updated_by)
```

**Interpretation:** "Closed" is a status after "resolved". Use `resolved_at` for timestamp, status for lifecycle stage.

---

### A6: defer_fault — Use `metadata` for Deferral Tracking

**Current Contract:**
```
Writes: pms_faults(~status='deferred', ~deferred_until, ~deferral_reason)
```

**DB Truth:**
- `deferred_until`, `deferral_reason` columns do NOT exist
- `pms_faults.metadata` JSONB exists

**Resolution:**
```
Writes: pms_faults(~status='deferred', ~metadata->'deferral', ~updated_at, ~updated_by)
```

**Pattern:**
`metadata.deferral = {deferred_until: "2026-02-15", reason: "Awaiting parts delivery", deferred_by: user_id}`

---

### A7: reopen_work_order — Use Status + `metadata`

**Current Contract:**
```
Writes: pms_work_orders(~status='in_progress', ~reopened_at, ~reopened_by, ~reopen_reason)
```

**DB Truth:**
- `reopened_at`, `reopened_by`, `reopen_reason` columns do NOT exist
- `pms_work_orders.metadata` JSONB exists

**Resolution:**
```
Writes: pms_work_orders(~status='in_progress', ~metadata->'reopened', ~updated_at, ~updated_by)
```

**Pattern:**
`metadata.reopened = {reopened_at, reopened_by, reason}`

---

### A8: cancel_work_order — Use Status + `metadata`

**Current Contract:**
```
Writes: pms_work_orders(~status='cancelled', ~cancelled_at, ~cancelled_by, ~cancellation_reason)
```

**DB Truth:**
- `cancelled_at`, `cancelled_by`, `cancellation_reason` columns do NOT exist
- `pms_work_orders.metadata` JSONB exists

**Resolution:**
```
Writes: pms_work_orders(~status='cancelled', ~metadata->'cancellation', ~updated_at, ~updated_by)
```

**Pattern:**
`metadata.cancellation = {cancelled_at, cancelled_by, reason}`

---

### A9: add_document_section_to_handover — Use Existing Columns

**Current Contract:**
```
Writes: handover_items(+entity_type='document_section', +document_page, +document_snippet)
```

**DB Truth:**
- `handover_items` table exists
- `document_page`, `document_snippet` columns do NOT exist
- `metadata` JSONB column exists

**Resolution:**
```
Writes: handover_items(+entity_type='document_section', +entity_id=document_id, +metadata->'page', +metadata->'snippet', +summary)
```

**Pattern:**
`metadata = {page: 47, snippet: "1. Drain coolant from system..."}`

---

### A10: edit_handover_section — Use `summary` Column Only

**Current Contract:**
```
Writes: handover_items(~summary, ~details, ~priority, ~updated_at)
```

**DB Truth:**
- `handover_items.summary` TEXT exists
- `handover_items.details` column does NOT exist (not in schema)
- Can use `metadata` for additional details

**Resolution:**
```
Writes: handover_items(~summary, ~metadata->'details', ~priority, ~updated_at, ~updated_by)
```

---

### A11: complete_checklist — Use Status Only

**Current Contract:**
```
Writes: pms_checklists(~status='completed', ~completed_at, ~completed_by)
```

**DB Truth:**
- `pms_checklists.status` exists
- `completed_at`, `completed_by` columns do NOT exist in pms_checklists
- Can use `metadata` or accept status transition only

**Resolution:**
```
Writes: pms_checklists(~status='completed', ~updated_at, ~updated_by)
```

**Alternative:** Add columns via migration (see Category B).

---

### A12: decommission_equipment — Use Status + `metadata`

**Current Contract:**
```
Writes: pms_equipment(~status='decommissioned', ~decommissioned_at, ~decommissioned_by, ~decommission_reason)
```

**DB Truth:**
- `pms_equipment.status` enum includes 'decommissioned'
- `decommissioned_at`, `decommissioned_by`, `decommission_reason` columns do NOT exist
- `metadata` JSONB exists

**Resolution:**
```
Writes: pms_equipment(~status='decommissioned', ~metadata->'decommissioning', ~updated_at, ~updated_by)
```

**Pattern:**
`metadata.decommissioning = {decommissioned_at, decommissioned_by, reason}`

---

## CATEGORY B: MIGRATE (Schema Migration Required)

These actions require new tables or columns that cannot be resolved with existing schema.

### B1: Shopping List Items — **NEW TABLE REQUIRED**

**Current Contract:**
```
add_to_shopping_list writes to shopping_list_items table
remove_from_shopping_list writes to shopping_list_items table
```

**DB Truth:**
- Table `shopping_list_items` does NOT exist
- No alternative table structure exists

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.shopping_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    part_id UUID NOT NULL REFERENCES public.pms_parts(id),
    quantity_requested INTEGER NOT NULL DEFAULT 1,
    priority TEXT CHECK (priority IN ('low', 'normal', 'high', 'urgent')) DEFAULT 'normal',
    notes TEXT,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT CHECK (status IN ('pending', 'ordered', 'cancelled')) DEFAULT 'pending',
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id),

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_shopping_list_yacht_status ON shopping_list_items(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_shopping_list_part ON shopping_list_items(part_id);

ALTER TABLE shopping_list_items ENABLE ROW LEVEL SECURITY;
```

**Justification:** Shopping list is separate concern from inventory (parts). Junction between user intent and purchase orders.

---

### B2: Purchase Order Items — **NEW TABLE REQUIRED**

**Current Contract:**
```
create_purchase_order writes to purchase_order_items table
add_item_to_purchase writes to purchase_order_items table
```

**DB Truth:**
- Table `purchase_order_items` does NOT exist
- `pms_purchase_orders` exists but no line items table

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.purchase_order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    purchase_order_id UUID NOT NULL REFERENCES public.pms_purchase_orders(id) ON DELETE CASCADE,
    part_id UUID REFERENCES public.pms_parts(id),
    description TEXT NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_received INTEGER DEFAULT 0,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    notes TEXT,

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

CREATE INDEX idx_po_items_purchase_order ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_po_items_part ON purchase_order_items(part_id);

ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
```

**Justification:** PO line items are distinct from PO header. Needed for multi-item orders.

---

### B3: Receiving Sessions — **NEW TABLE REQUIRED**

**Current Contract:**
```
receive_items (start session) writes to receiving_sessions table
check_in_item writes to receiving_sessions table
commit_session reads from receiving_sessions table
cancel_session writes to receiving_sessions table
```

**DB Truth:**
- Table `receiving_sessions` does NOT exist

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.receiving_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    purchase_order_id UUID NOT NULL REFERENCES public.pms_purchase_orders(id),
    status TEXT CHECK (status IN ('active', 'committed', 'cancelled')) DEFAULT 'active',
    session_data JSONB DEFAULT '{}', -- {checked_items: [{po_item_id, quantity_received, notes}], discrepancies: [...]}
    started_by UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    committed_by UUID,
    committed_at TIMESTAMPTZ,
    cancelled_by UUID,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_receiving_sessions_po ON receiving_sessions(purchase_order_id);
CREATE INDEX idx_receiving_sessions_status ON receiving_sessions(status);

ALTER TABLE receiving_sessions ENABLE ROW LEVEL SECURITY;
```

**Justification:** Receiving is multi-step process. Session state needed for resumability.

---

### B4: Documents Table — **NEW TABLE REQUIRED**

**Current Contract:**
```
upload_document writes to documents table
link_document_to_equipment writes to equipment_documents junction
search_documents reads from documents table
```

**DB Truth:**
- Table `documents` does NOT exist
- `pms_attachments` table exists but is polymorphic (entity_type + entity_id), not standalone documents

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.pms_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    title TEXT NOT NULL,
    document_type TEXT CHECK (document_type IN ('manual', 'procedure', 'schematic', 'certificate', 'report', 'other')) NOT NULL,
    file_path TEXT NOT NULL, -- Supabase storage path
    file_size INTEGER,
    mime_type TEXT,
    indexed_content TEXT, -- For full-text search
    metadata JSONB DEFAULT '{}',

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    deletion_reason TEXT
);

CREATE INDEX idx_documents_yacht_type ON pms_documents(yacht_id, document_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_search ON pms_documents USING gin(to_tsvector('english', indexed_content));

ALTER TABLE pms_documents ENABLE ROW LEVEL SECURITY;
```

**Justification:** Documents are first-class entities, not just attachments to other entities. Need standalone table for manuals, procedures, certs.

---

### B5: Equipment-Document Junction — **NEW TABLE REQUIRED**

**Current Contract:**
```
link_document_to_equipment writes to equipment_documents junction
view_equipment_manual reads from equipment_documents junction
```

**DB Truth:**
- No junction table exists for equipment ↔ documents

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.equipment_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    equipment_id UUID NOT NULL REFERENCES public.pms_equipment(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.pms_documents(id) ON DELETE CASCADE,
    relationship_type TEXT CHECK (relationship_type IN ('manual', 'schematic', 'procedure', 'certificate')) DEFAULT 'manual',
    notes TEXT,

    -- Standard timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,

    -- Prevent duplicates
    UNIQUE(equipment_id, document_id, deleted_at),

    -- Soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

CREATE INDEX idx_equipment_documents_equipment ON equipment_documents(equipment_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_equipment_documents_document ON equipment_documents(document_id) WHERE deleted_at IS NULL;

ALTER TABLE equipment_documents ENABLE ROW LEVEL SECURITY;
```

**Justification:** M:M relationship between equipment and documents (one manual covers multiple equipment, one equipment has multiple docs).

---

### B6: Purchase Order Approval Columns — **ADD COLUMNS**

**Current Contract:**
```
approve_purchase_order writes: pms_purchase_orders(~status='approved', ~approved_by, ~approved_at)
```

**DB Truth:**
- `pms_purchase_orders` table exists
- `approved_by`, `approved_at` columns do NOT exist

**Migration Required:**
```sql
ALTER TABLE public.pms_purchase_orders
ADD COLUMN IF NOT EXISTS approved_by UUID,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS approval_notes TEXT;

COMMENT ON COLUMN pms_purchase_orders.approved_by IS 'User ID who approved the purchase order (HOD)';
COMMENT ON COLUMN pms_purchase_orders.approved_at IS 'Timestamp when PO was approved';
```

**Justification:** Approval is critical milestone requiring explicit tracking (not just status change).

---

### B7: Purchase Order Ordered Tracking — **ADD COLUMNS**

**Current Contract:**
```
mark_po_ordered writes: pms_purchase_orders(~status='ordered', ~ordered_at, ~ordered_by)
```

**DB Truth:**
- `ordered_at`, `ordered_by` columns do NOT exist

**Migration Required:**
```sql
ALTER TABLE public.pms_purchase_orders
ADD COLUMN IF NOT EXISTS ordered_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS ordered_by UUID,
ADD COLUMN IF NOT EXISTS supplier_order_reference TEXT;

COMMENT ON COLUMN pms_purchase_orders.ordered_at IS 'Timestamp when order was placed with supplier';
COMMENT ON COLUMN pms_purchase_orders.ordered_by IS 'User who placed the order';
COMMENT ON COLUMN pms_purchase_orders.supplier_order_reference IS 'Supplier confirmation/tracking number';
```

---

### B8: Purchase Order Receiving Tracking — **ADD COLUMNS**

**Current Contract:**
```
commit_session writes: pms_purchase_orders(~status='received', ~received_at, ~received_by)
```

**DB Truth:**
- `received_at`, `received_by` columns do NOT exist

**Migration Required:**
```sql
ALTER TABLE public.pms_purchase_orders
ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS received_by UUID,
ADD COLUMN IF NOT EXISTS receiving_notes TEXT;

COMMENT ON COLUMN pms_purchase_orders.received_at IS 'Timestamp when delivery was received and committed';
COMMENT ON COLUMN pms_purchase_orders.received_by IS 'User who committed the receiving session';
```

---

### B9: Fault Diagnosis Columns — **ADD COLUMNS** (Alternative to A1)

**Alternative to using `metadata` JSONB:**

**Migration Required:**
```sql
ALTER TABLE public.pms_faults
ADD COLUMN IF NOT EXISTS diagnosis TEXT,
ADD COLUMN IF NOT EXISTS diagnosis_notes TEXT,
ADD COLUMN IF NOT EXISTS diagnosed_by UUID,
ADD COLUMN IF NOT EXISTS diagnosed_at TIMESTAMPTZ;

COMMENT ON COLUMN pms_faults.diagnosis IS 'Primary diagnosis/root cause';
COMMENT ON COLUMN pms_faults.diagnosis_notes IS 'Detailed diagnostic findings';
COMMENT ON COLUMN pms_faults.diagnosed_by IS 'Engineer who performed diagnosis';
COMMENT ON COLUMN pms_faults.diagnosed_at IS 'Timestamp of diagnosis';

CREATE INDEX idx_faults_diagnosed ON pms_faults(diagnosed_at DESC) WHERE diagnosed_at IS NOT NULL AND deleted_at IS NULL;
```

**Justification:** Diagnosis is frequently queried (reports, analytics). Explicit columns better than JSONB for performance.

---

### B10: Work Order Time Tracking — **NEW TABLE** (Alternative to A4)

**Alternative to using `metadata` for hours_logged:**

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.work_order_time_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
    crew_member_id UUID NOT NULL,
    crew_member_name TEXT NOT NULL,
    hours_worked NUMERIC(5,2) NOT NULL,
    work_date DATE NOT NULL,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ,
    updated_by UUID,

    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

CREATE INDEX idx_wo_time_log_wo ON work_order_time_log(work_order_id);
CREATE INDEX idx_wo_time_log_crew ON work_order_time_log(crew_member_id, work_date);

ALTER TABLE work_order_time_log ENABLE ROW LEVEL SECURITY;
```

**Justification:** Time tracking is audit-critical for labor cost reporting. Needs granular log, not summary field.

---

### B11: Fault Notes Table — **NEW TABLE** (Alternative to A2)

**Alternative to using `metadata` for notes:**

**Migration Required:**
```sql
CREATE TABLE IF NOT EXISTS public.pms_fault_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fault_id UUID NOT NULL REFERENCES public.pms_faults(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT CHECK (note_type IN ('general', 'diagnosis', 'observation', 'resolution')) DEFAULT 'general',
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fault_notes_fault ON pms_fault_notes(fault_id, created_at DESC);

ALTER TABLE pms_fault_notes ENABLE ROW LEVEL SECURITY;
```

**Justification:** Mirrors `work_order_notes` table structure. Better for queries than JSONB array.

---

### B12: Checklist Completion Tracking — **ADD COLUMNS**

**Current Contract:**
```
complete_checklist writes: pms_checklists(~status='completed', ~completed_at, ~completed_by)
```

**DB Truth:**
- `completed_at`, `completed_by` columns do NOT exist in `pms_checklists`

**Migration Required:**
```sql
ALTER TABLE public.pms_checklists
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS completed_by UUID,
ADD COLUMN IF NOT EXISTS completion_signature JSONB;

COMMENT ON COLUMN pms_checklists.completed_at IS 'Timestamp when checklist was marked complete';
COMMENT ON COLUMN pms_checklists.completed_by IS 'User who completed the checklist';
COMMENT ON COLUMN pms_checklists.completion_signature IS 'Digital signature data {user_id, timestamp, signature_hash}';
```

---

## MIGRATION PRIORITY

### P0 (MVP Blockers)
1. **shopping_list_items table** - Required for purchasing flow
2. **purchase_order_items table** - Required for PO creation
3. **Purchase Order approval/ordered/received columns** - Required for PO lifecycle

### P1 (High Value, Not MVP Blockers)
4. **pms_documents table** - Enables manual linking (workaround: use pms_attachments)
5. **receiving_sessions table** - Enables receiving flow (workaround: direct commit)
6. **Fault diagnosis columns** - Improves query performance (workaround: use metadata)

### P2 (Nice to Have)
7. **work_order_time_log table** - Better time tracking (workaround: use metadata)
8. **pms_fault_notes table** - Consistent with WO notes (workaround: use metadata)
9. **equipment_documents junction** - Better document linking (workaround: metadata references)

---

## DECISION MATRIX

For each schema gap, choose:
- **Use existing (metadata JSONB)** if:
  - Action is low-frequency (<10% of operations)
  - Data is unstructured or variable
  - Not queried in reports/analytics

- **Add columns** if:
  - Action is high-frequency (>50% of operations)
  - Data is structured and queryable
  - Needed for indexes/performance

- **Create table** if:
  - One-to-many relationship (e.g., fault → notes)
  - Separate lifecycle (e.g., receiving sessions)
  - Complex querying needed

---

**Status:** Schema gaps identified. 12 resolved via existing schema (metadata), 12 require migrations. Ready for DB migration planning.
