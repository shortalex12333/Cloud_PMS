# Work Order Lens P1: Show Related — PHASE 8: GAPS & MIGRATIONS

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Identify **missing schema elements** and provide **migration scripts** for P1 Show Related.

---

## Schema Gap Analysis

### ✅ Already Exists (from P0)

- [x] `pms_entity_links` table with RLS
- [x] `pms_work_orders` table with yacht_id, equipment_id, fault_id
- [x] `pms_work_order_parts` join table
- [x] `pms_parts` table
- [x] `pms_equipment` table
- [x] `pms_faults` table
- [x] Helper functions: `is_hod()`, `is_manager()`, `get_user_yacht_id()`
- [x] RLS policies on core tables

### ⏳ Needs Verification

- [ ] `pms_documents` table (or `pms_doc_metadata`)
  - Columns: id, yacht_id, title, doc_type, equipment_id, file_path, mime_type
  - RLS SELECT policy: `yacht_id = get_user_yacht_id()`

- [ ] `pms_work_order_attachments` join table
  - Columns: id, work_order_id, document_id, yacht_id, attached_by, created_at
  - RLS policies: SELECT (all), INSERT/UPDATE/DELETE (HOD/manager)

- [ ] Unique constraint on `pms_entity_links` to prevent duplicates
  - Constraint: UNIQUE (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)

### ❌ Missing (Create in Migrations)

- [ ] Indexes for performance:
  - `pms_work_order_parts(work_order_id, yacht_id)`
  - `pms_documents(equipment_id, doc_type, yacht_id)`
  - `pms_work_order_attachments(work_order_id, yacht_id)`
  - `pms_entity_links(source_entity_type, source_entity_id, yacht_id)`

- [ ] Optional: DB functions for complex queries (if needed)

---

## Required Migrations

### Migration 1: Create pms_documents Table (if missing)

**File:** `supabase/migrations/202601XX_create_pms_documents.sql`

```sql
-- Create documents/attachments metadata table
CREATE TABLE IF NOT EXISTS public.pms_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  title TEXT NOT NULL,
  doc_type TEXT NOT NULL CHECK (doc_type IN ('manual', 'handover', 'attachment', 'other')),
  equipment_id UUID REFERENCES pms_equipment(id),
  file_path TEXT,
  mime_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pms_documents_yacht_id ON pms_documents(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_documents_equipment_doc_type ON pms_documents(equipment_id, doc_type, yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_documents_doc_type ON pms_documents(doc_type, yacht_id);

-- Enable RLS
ALTER TABLE pms_documents ENABLE ROW LEVEL SECURITY;

-- SELECT policy: yacht isolation
CREATE POLICY "documents_select_policy" ON pms_documents
  FOR SELECT
  USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE/DELETE policy: HOD/manager only
CREATE POLICY "documents_modify_policy" ON pms_documents
  FOR ALL
  USING (
    yacht_id = public.get_user_yacht_id()
    AND (public.is_hod() OR public.is_manager())
  )
  WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (public.is_hod() OR public.is_manager())
  );
```

---

### Migration 2: Create pms_work_order_attachments Table (if missing)

**File:** `supabase/migrations/202601XX_create_pms_work_order_attachments.sql`

```sql
-- Create work order attachments join table
CREATE TABLE IF NOT EXISTS public.pms_work_order_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  work_order_id UUID NOT NULL REFERENCES pms_work_orders(id),
  document_id UUID NOT NULL REFERENCES pms_documents(id),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  attached_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pms_work_order_attachments_wo ON pms_work_order_attachments(work_order_id, yacht_id);
CREATE INDEX IF NOT EXISTS idx_pms_work_order_attachments_doc ON pms_work_order_attachments(document_id, yacht_id);

-- Enable RLS
ALTER TABLE pms_work_order_attachments ENABLE ROW LEVEL SECURITY;

-- SELECT policy: yacht isolation
CREATE POLICY "work_order_attachments_select_policy" ON pms_work_order_attachments
  FOR SELECT
  USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE/DELETE policy: HOD/manager only
CREATE POLICY "work_order_attachments_modify_policy" ON pms_work_order_attachments
  FOR ALL
  USING (
    yacht_id = public.get_user_yacht_id()
    AND (public.is_hod() OR public.is_manager())
  )
  WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (public.is_hod() OR public.is_manager())
  );
```

---

### Migration 3: Add Unique Constraint to pms_entity_links

**File:** `supabase/migrations/202601XX_entity_links_unique_constraint.sql`

```sql
-- Prevent duplicate entity links
CREATE UNIQUE INDEX IF NOT EXISTS idx_pms_entity_links_unique
  ON pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type);

COMMENT ON INDEX idx_pms_entity_links_unique IS 'Prevent duplicate entity links';
```

---

### Migration 4: Performance Indexes

**File:** `supabase/migrations/202601XX_show_related_indexes.sql`

```sql
-- Indexes for Show Related performance

-- pms_work_order_parts: optimize FK join for parts
CREATE INDEX IF NOT EXISTS idx_pms_work_order_parts_wo_yacht
  ON pms_work_order_parts(work_order_id, yacht_id);

-- pms_work_orders: optimize equipment-based queries
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_equipment
  ON pms_work_orders(equipment_id, yacht_id, deleted_at);

-- pms_documents: optimize equipment-based doc queries
CREATE INDEX IF NOT EXISTS idx_pms_documents_equipment_type
  ON pms_documents(equipment_id, doc_type, yacht_id)
  WHERE deleted_at IS NULL;

-- pms_entity_links: optimize source lookups
CREATE INDEX IF NOT EXISTS idx_pms_entity_links_source
  ON pms_entity_links(source_entity_type, source_entity_id, yacht_id);

-- pms_entity_links: optimize target lookups (for reverse queries)
CREATE INDEX IF NOT EXISTS idx_pms_entity_links_target
  ON pms_entity_links(target_entity_type, target_entity_id, yacht_id);
```

---

### Optional Migration 5: DB Functions (if needed)

**File:** `supabase/migrations/202601XX_show_related_functions.sql`

```sql
-- Optional: Create Postgres function for complex related queries
-- Only create if Python handler queries >500ms

CREATE OR REPLACE FUNCTION public.get_all_related_entities(
  p_work_order_id UUID,
  p_yacht_id UUID
)
RETURNS TABLE (
  group_key TEXT,
  entity_id UUID,
  entity_type TEXT,
  title TEXT,
  subtitle TEXT,
  match_reasons TEXT[],
  weight INTEGER
) AS $$
BEGIN
  -- Parts
  RETURN QUERY
  SELECT
    'parts'::TEXT AS group_key,
    p.id AS entity_id,
    'part'::TEXT AS entity_type,
    p.name AS title,
    'Part #: ' || COALESCE(p.part_number, 'N/A') AS subtitle,
    ARRAY['FK:wo_part']::TEXT[] AS match_reasons,
    100 AS weight
  FROM pms_work_order_parts wop
  JOIN pms_parts p ON p.id = wop.part_id
  WHERE wop.work_order_id = p_work_order_id
    AND wop.yacht_id = p_yacht_id
  LIMIT 10;

  -- Manuals (similar pattern for each group)
  -- ... (add other groups)

END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

**Decision:** Only create if needed. Prefer app-level logic for flexibility.

---

## Migration Execution Plan

### Phase 1: Schema Verification
1. Check if `pms_documents` exists: `SELECT * FROM information_schema.tables WHERE table_name = 'pms_documents'`
2. Check if `pms_work_order_attachments` exists
3. Check if indexes exist: `SELECT * FROM pg_indexes WHERE tablename LIKE 'pms_%'`

### Phase 2: Apply Missing Migrations
1. Run migrations in order (if tables/indexes missing)
2. Apply to TENANT_1 first
3. Verify with `SELECT * FROM pms_entity_links LIMIT 1` (check unique constraint)

### Phase 3: Verify RLS Policies
1. Query `pg_policies` to confirm all policies exist
2. Test with Docker: cross-yacht isolation, role gating

---

## Data Migration (if needed)

### Scenario: Existing doc_metadata table
If documents already exist in a different table (e.g., `doc_metadata`):

```sql
-- Migrate existing documents to pms_documents
INSERT INTO pms_documents (id, yacht_id, title, doc_type, equipment_id, file_path, mime_type, created_at)
SELECT id, yacht_id, title, doc_type, equipment_id, file_path, mime_type, created_at
FROM doc_metadata
WHERE yacht_id = 'target-yacht-uuid'
ON CONFLICT (id) DO NOTHING;
```

**Note:** Only run if consolidating schemas. Otherwise, adapt queries to existing table.

---

## Rollback Plan

### If Migration Fails

1. **Drop tables (if created):**
```sql
DROP TABLE IF EXISTS pms_work_order_attachments CASCADE;
DROP TABLE IF EXISTS pms_documents CASCADE;
```

2. **Drop indexes:**
```sql
DROP INDEX IF EXISTS idx_pms_work_order_parts_wo_yacht;
DROP INDEX IF EXISTS idx_pms_entity_links_unique;
-- ... (drop all created indexes)
```

3. **Restore from backup if needed**

### If Performance Degrades

1. Drop newly created indexes
2. Revert to app-level queries without DB functions
3. Monitor query performance with `EXPLAIN ANALYZE`

---

## Verification Checklist

After migrations:

- [ ] `pms_documents` table exists with RLS
- [ ] `pms_work_order_attachments` table exists with RLS
- [ ] Unique constraint on `pms_entity_links`
- [ ] All performance indexes created
- [ ] RLS policies verified with `pg_policies` query
- [ ] Docker tests pass (cross-yacht isolation)
- [ ] No 500 errors in staging CI

---

## Deployment Steps

1. **Create migration files** in `supabase/migrations/`
2. **Test migrations locally** against Docker Supabase
3. **Apply to TENANT_1** (staging database)
4. **Run verification queries** to confirm schema
5. **Run Docker tests** to confirm RLS and queries work
6. **Document migration** in deployment summary

---

**GAPS & MIGRATIONS STATUS:** ✅ IDENTIFIED & SCRIPTED
