# Work Order Lens P1: Show Related — PHASE 8: GAPS & MIGRATIONS

**Feature:** Schema Migrations and Embedding Backfill
**Date:** 2026-01-28
**Time:** 45 minutes

---

## Purpose

Define **required migrations** for P1 Show Related with:
- Unique constraint on `pms_entity_links` (prevent duplicates)
- Optional performance indexes (only if EXPLAIN proves necessity)
- Embedding backfill outline for Week 1 tables
- Acceptance checks for post-migration verification

---

## Schema Gap Analysis

### ✅ Already Exists (from PHASE_2 DB Truth)

**Core Tables:**
- ✅ `pms_work_orders` — Core entity with yacht_id, equipment_id, fault_id, last_activity_at
- ✅ `pms_work_order_parts` — Join table with yacht_id
- ✅ `pms_parts` — **ALREADY HAS embeddings** (search_embedding, embedding_text columns exist!)
- ✅ `pms_equipment` — Referenced via work_orders.equipment_id
- ✅ `pms_faults` — Referenced via work_orders.fault_id
- ✅ `pms_work_order_notes` — Notes with FK to work_orders
- ✅ `doc_metadata` — **Canonical table for ALL attachments, photos, manuals** (entity_type, entity_id, equipment_ids[])
- ✅ `handover_exports` — Exists but empty (schema unknown until data exists)
- ✅ `pms_entity_links` — Explicit links table (created in P0)

**Helper Functions:**
- ✅ `get_user_yacht_id()` — Extract yacht_id from JWT
- ✅ `is_hod()` — Check if user is Head of Department
- ✅ `is_manager()` — Check if user is manager/captain

**RLS Policies:**
- ✅ All core tables have RLS enabled with yacht_id policies

### ❌ Does NOT Exist (Confirmed in PHASE_2)

- ❌ `pms_work_order_attachments` — **Does NOT exist** (use doc_metadata instead)
- ❌ `pms_documents` — **Does NOT exist** (use doc_metadata instead)
- ❌ `pms_inventory_locations` — **Does NOT exist** (404 from API)

### ⏳ Needs Addition (P1 Migrations)

1. **Unique constraint on `pms_entity_links`** — Prevent duplicate links
2. **Optional GIN indexes on `doc_metadata`** — Only if EXPLAIN shows sequential scans
3. **Embedding columns on Week 1 tables** — pms_work_orders, pms_equipment, pms_faults (follow pms_parts pattern)
4. **Optional indexes** — Query-specific, only if profiling demands

---

## Required Migrations

## Link Type Enum (Semantics)

**Accepted link_type Values:**

The `pms_entity_links.link_type` column accepts exactly 4 values:

1. **`related`** — General relationship (default)
2. **`reference`** — Documentation reference (manual, spec sheet)
3. **`evidence`** — Supporting evidence (photo, report)
4. **`manual`** — Manual link override (crew-specified)

**Validation:** Backend must reject any link_type not in this list with **400 Bad Request**.

**Test Coverage:** Docker matrix includes `test_invalid_link_type_400()`.

---

## Migration Safety Notes

**⚠️ CONCURRENTLY and Transactions:**

- `CREATE INDEX CONCURRENTLY` **cannot** be run inside a transaction block
- If using CONCURRENTLY, do NOT wrap in `BEGIN/COMMIT`
- For idempotency in non-transaction context, use `IF NOT EXISTS` clause
- Alternative: Use DO-block with existence check (works in transaction)

**Migration Files Use DO-Blocks:**
- All 4 migrations use DO-blocks with IF NOT EXISTS checks
- Safe to run in transactions
- Idempotent (safe to rerun)

---

### Migration 1: Unique Constraint on pms_entity_links

**Purpose:** Prevent duplicate entity links (enforce idempotence for add_entity_link).

**File:** `supabase/migrations/20260128_1200_unique_entity_links.sql`

```sql
-- Migration: Add unique constraint to pms_entity_links
-- Prevents duplicate links for same source, target, and link_type
-- Idempotent: Uses IF NOT EXISTS pattern

DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'unique_entity_link'
          AND conrelid = 'public.pms_entity_links'::regclass
    ) THEN
        -- Add unique constraint
        ALTER TABLE public.pms_entity_links
        ADD CONSTRAINT unique_entity_link UNIQUE (
            yacht_id,
            source_entity_type,
            source_entity_id,
            target_entity_type,
            target_entity_id,
            link_type
        );

        RAISE NOTICE 'Added unique constraint: unique_entity_link';
    ELSE
        RAISE NOTICE 'Constraint unique_entity_link already exists, skipping';
    END IF;
END $$;

-- Verify constraint exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unique_entity_link'
    ) THEN
        RAISE EXCEPTION 'Failed to create unique_entity_link constraint';
    END IF;
END $$;

COMMENT ON CONSTRAINT unique_entity_link ON pms_entity_links IS
'Prevents duplicate entity links for same source, target, and link_type per yacht';
```

**Expected Behavior:**
- First run: Creates constraint, raises NOTICE "Added unique constraint"
- Subsequent runs: Skips creation, raises NOTICE "already exists"
- Prevents: Two identical links (same source, target, link_type)

**Test Case:**
```sql
-- Should succeed (first insert)
INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
VALUES ('yacht-a-uuid', 'work_order', 'wo-uuid', 'part', 'part-uuid', 'related');

-- Should fail with 409 (unique constraint violation)
INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
VALUES ('yacht-a-uuid', 'work_order', 'wo-uuid', 'part', 'part-uuid', 'related');
```

---

### Migration 2: Optional Indexes on doc_metadata (Deferred)

**Purpose:** Optimize JSONB metadata queries and array containment queries.

**File:** `supabase/migrations/20260128_1300_indexes_doc_metadata.sql`

**IMPORTANT:** This migration is **commented out by default**. Only uncomment if EXPLAIN ANALYZE shows sequential scans.

```sql
-- Migration: Optional indexes for doc_metadata
-- COMMENTED OUT BY DEFAULT
-- Only uncomment if EXPLAIN ANALYZE shows sequential scans on these columns

-- =============================================================================
-- PERFORMANCE TESTING REQUIRED BEFORE UNCOMMENTING
-- =============================================================================
-- Run these EXPLAIN ANALYZE queries first:
--
-- 1. Test equipment_ids[] array containment:
--    EXPLAIN ANALYZE
--    SELECT id, filename FROM doc_metadata
--    WHERE equipment_ids @> ARRAY['<test-equipment-id>']::uuid[]
--      AND yacht_id = '<test-yacht-id>';
--
-- 2. Test metadata JSONB query:
--    EXPLAIN ANALYZE
--    SELECT id, filename FROM doc_metadata
--    WHERE metadata @> jsonb_build_object('entity_type', 'work_order', 'entity_id', '<test-wo-id>')
--      AND yacht_id = '<test-yacht-id>';
--
-- If you see "Seq Scan" with cost > 1000, uncomment relevant index below.
-- =============================================================================

-- Index 1: GIN index on equipment_ids[] array
-- Uncomment if querying equipment_ids[] array frequently

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_metadata_equipment_ids_gin
-- ON doc_metadata USING GIN (equipment_ids);
--
-- COMMENT ON INDEX idx_doc_metadata_equipment_ids_gin IS
-- 'Optimizes queries: WHERE equipment_ids @> ARRAY[...]';

-- Index 2: GIN index on metadata JSONB
-- Uncomment if querying metadata JSONB frequently

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_metadata_metadata_gin
-- ON doc_metadata USING GIN (metadata jsonb_path_ops);
--
-- COMMENT ON INDEX idx_doc_metadata_metadata_gin IS
-- 'Optimizes queries: WHERE metadata @> jsonb_build_object(...)';

-- Index 3: Composite btree index on entity_type + entity_id
-- Uncomment if metadata JSONB query is slow despite GIN index

-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_metadata_entity_type_id
-- ON doc_metadata (
--     (metadata->>'entity_type'),
--     (metadata->>'entity_id'),
--     yacht_id
-- )
-- WHERE deleted_at IS NULL;
--
-- COMMENT ON INDEX idx_doc_metadata_entity_type_id IS
-- 'Optimizes queries extracting entity_type and entity_id from JSONB metadata';

-- =============================================================================
-- DECISION TREE
-- =============================================================================
-- If EXPLAIN shows:
-- - Seq Scan + cost < 100 → No index needed (table is small or query is efficient)
-- - Bitmap Heap Scan + GIN → Index 1 or 2 is working (good)
-- - Seq Scan + cost > 1000 → Uncomment relevant index and retest
-- =============================================================================
```

**Decision Criteria:**
- **Uncomment Index 1** if: Query "WHERE equipment_ids @> ARRAY[...]" shows Seq Scan with cost > 1000
- **Uncomment Index 2** if: Query "WHERE metadata @> jsonb_build_object(...)" shows Seq Scan with cost > 1000
- **Uncomment Index 3** if: Need faster lookups on extracted entity_type/entity_id fields

**Why Deferred:**
- PHASE_2 confirmed doc_metadata exists with these columns
- Actual query patterns unknown until production traffic
- Premature indexing wastes space and slows writes
- EXPLAIN-driven approach ensures indexes are only added when proven necessary

---

### Migration 3: Indexes for FK Joins (Standard, Always Apply)

**Purpose:** Optimize FK joins and yacht_id filters.

**File:** `supabase/migrations/20260128_1400_indexes_fk_joins.sql`

```sql
-- Migration: Standard indexes for Show Related FK joins
-- Safe to apply; these optimize common query patterns

-- Index on pms_work_order_parts for parts query (Group 1)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wop_work_order_yacht
ON pms_work_order_parts(work_order_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wop_work_order_yacht IS
'Optimizes: SELECT parts FROM pms_work_order_parts WHERE work_order_id = ? AND yacht_id = ?';

-- Index on pms_work_orders for equipment-based queries (Group 2, 3)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wo_equipment_yacht
ON pms_work_orders(equipment_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wo_equipment_yacht IS
'Optimizes: SELECT work_orders WHERE equipment_id = ? AND yacht_id = ?';

-- Index on pms_work_orders for last_activity_at sorting (Group 3)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wo_last_activity
ON pms_work_orders(last_activity_at DESC NULLS LAST, created_at DESC)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_wo_last_activity IS
'Optimizes: ORDER BY last_activity_at DESC NULLS LAST for previous_work sorting';

-- Index on pms_entity_links for source lookups (Group 6)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_links_source
ON pms_entity_links(source_entity_type, source_entity_id, yacht_id);

COMMENT ON INDEX idx_entity_links_source IS
'Optimizes: SELECT explicit_links WHERE source_entity_type = ? AND source_entity_id = ?';

-- Index on pms_entity_links for target lookups (Group 6, bidirectional)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_links_target
ON pms_entity_links(target_entity_type, target_entity_id, yacht_id);

COMMENT ON INDEX idx_entity_links_target IS
'Optimizes: SELECT explicit_links WHERE target_entity_type = ? AND target_entity_id = ?';

-- Index on pms_work_order_notes for notes query (Group 4)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_won_work_order_yacht
ON pms_work_order_notes(work_order_id, yacht_id)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_won_work_order_yacht IS
'Optimizes: SELECT notes WHERE work_order_id = ? AND yacht_id = ?';
```

**Why Always Apply:**
- These indexes optimize FK joins used in every Show Related query
- Small overhead on writes, large benefit on reads
- No risk of wasted space (indexes are query-aligned)

---

### Migration 4: Embedding Columns for Week 1 Tables

**Purpose:** Add search_embedding and embedding_text columns to Week 1 tables (follow pms_parts pattern).

**File:** `supabase/migrations/20260128_1500_embeddings_week1.sql`

**IMPORTANT:** This migration adds columns but does NOT backfill data. Backfill is separate (see "Embedding Backfill" section).

```sql
-- Migration: Add embedding columns to Week 1 tables
-- Follows pms_parts pattern (search_embedding vector(1536), embedding_text TEXT)
-- Idempotent: Uses IF NOT EXISTS via ALTER TABLE ... ADD COLUMN IF NOT EXISTS

-- Table 1: pms_work_orders
DO $$
BEGIN
    -- Add search_embedding column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_work_orders'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_work_orders
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_work_orders.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.search_embedding already exists, skipping';
    END IF;

    -- Add embedding_text column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_work_orders'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_work_orders
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_work_orders.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.embedding_text already exists, skipping';
    END IF;
END $$;

-- Table 2: pms_equipment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_equipment'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_equipment
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_equipment.search_embedding';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_equipment'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_equipment
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_equipment.embedding_text';
    END IF;
END $$;

-- Table 3: pms_faults
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_faults'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_faults.search_embedding';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_faults'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_faults.embedding_text';
    END IF;
END $$;

-- Table 4: pms_work_order_notes
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_work_order_notes'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_work_order_notes.search_embedding';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_work_order_notes'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_work_order_notes.embedding_text';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_orders.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; combines title + description + completion_notes';

COMMENT ON COLUMN pms_work_orders.embedding_text IS
'Concatenated text used to generate search_embedding; updated when title/description/completion_notes change';

-- Note: pms_parts ALREADY has these columns (confirmed in PHASE_2)
-- No need to alter pms_parts
```

**Week 1 Tables (Prioritized):**
1. ✅ `pms_parts` — ALREADY has embeddings (no action needed)
2. ⏳ `pms_work_orders` — Add embeddings (title + description + completion_notes)
3. ⏳ `pms_equipment` — Add embeddings (name + model + manufacturer + location)
4. ⏳ `pms_faults` — Add embeddings (title + description + diagnosis)
5. ⏳ `pms_work_order_notes` — Add embeddings (note_text)

**Week 2 Tables (Deferred):**
- `doc_metadata` — Manuals (filename + oem + model + system_type + OCR chunks)
- `handover_exports` — When data exists
- `pms_shopping_list_items` — Part requests (part_name + part_number + source_notes)

---

## Embeddings Roadmap (Ranking-Only, RLS-Safe)

### Critical Constraint: Similarity Cannot Expand RLS Scope

**🔒 SECURITY RULE:**
Embedding-based similarity search **MUST NOT** add rows that are not already RLS-visible via FK relationships.

**What This Means:**
- ✅ Embeddings can **re-rank** items already returned by FK queries
- ✅ Embeddings can **boost** weights of FK-returned items based on semantic similarity
- ❌ Embeddings **CANNOT** add new items beyond FK results
- ❌ Embeddings **CANNOT** be used to "discover" entities in other yachts

**Example (Correct):**
```python
# Step 1: Get FK-visible items (RLS-enforced)
fk_items = query_previous_work(wo_id, yacht_id)  # Returns 10 work orders

# Step 2: Re-rank using embeddings (ranking-only)
query_embedding = get_embedding(wo.title)
for item in fk_items:
    similarity_score = cosine_similarity(query_embedding, item.search_embedding)
    item.weight += similarity_score * 10  # Boost weight, don't add new items

# Step 3: Sort by weight and return
return sorted(fk_items, key=lambda x: x.weight, reverse=True)
```

**Example (INCORRECT - Security Violation):**
```python
# ❌ WRONG: Using pgvector to find similar items without RLS filter
similar_items = supabase.rpc('match_documents', {
    'query_embedding': query_embedding,
    'match_threshold': 0.7,
    'match_count': 20
}).execute()  # Missing yacht_id filter - RLS LEAK!
```

**Week 1 P1 Scope:**
- Embeddings are **optional** (only for re-ranking)
- All queries use deterministic FK relationships first
- Similarity never returns items outside FK scope

**Week 2+ Roadmap:**
- Add embeddings to re-rank `previous_work` (same equipment)
- Add embeddings to boost `parts` with similar usage patterns
- **Always** filter by `yacht_id` before applying similarity

**Department Scope Clarification:**
- "Department scope" for handovers/docs means RLS controls visibility
- Embedding similarity can only re-rank visible items
- Never use embeddings to bypass RLS policies

---

## Embedding Backfill Outline

### Backfill Strategy

**Important:** Embedding generation is DEFERRED until Week 2+. Migration only adds columns.

**Why Defer:**
- Week 1: Show Related works with FK queries only (no embeddings needed)
- Week 2+: Add embeddings for re-ranking previous_work, parts, etc.
- Cost control: Embeddings cost $0.02 per 1M tokens; backfill = large one-time cost

### Backfill Script (Python, Future)

**File:** `scripts/backfill_embeddings_week1.py`

```python
#!/usr/bin/env python3
"""
Backfill embeddings for Week 1 tables
Run AFTER migration 4 (embedding columns exist)
"""

import openai
from supabase import create_client
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai.api_key = OPENAI_API_KEY

def generate_embedding(text: str):
    """Generate embedding using text-embedding-3-small."""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def backfill_work_orders(yacht_id: str):
    """Backfill embeddings for pms_work_orders."""
    # Get all work orders without embeddings
    wos = supabase.table('pms_work_orders') \
        .select('id, title, description, completion_notes') \
        .eq('yacht_id', yacht_id) \
        .is_('search_embedding', 'null') \
        .limit(1000) \
        .execute()

    for wo in wos.data:
        # Concatenate fields
        embedding_text = f"{wo['title']} {wo.get('description', '')} {wo.get('completion_notes', '')}".strip()

        # Generate embedding
        embedding = generate_embedding(embedding_text)

        # Update row
        supabase.table('pms_work_orders') \
            .update({
                'embedding_text': embedding_text,
                'search_embedding': embedding
            }) \
            .eq('id', wo['id']) \
            .execute()

        print(f"Backfilled WO: {wo['id']}")

# Similar functions for equipment, faults, notes
# ...

if __name__ == '__main__':
    yacht_id = input('Enter yacht_id to backfill: ')
    backfill_work_orders(yacht_id)
    # backfill_equipment(yacht_id)
    # backfill_faults(yacht_id)
    # backfill_notes(yacht_id)
```

**Backfill Parameters:**
- **Chunk Size:** 100 rows per batch (prevents memory spikes)
- **Rate Limit:** 50 requests/minute to OpenAI (avoid rate limit errors)
- **Model:** `text-embedding-3-small` (1536 dimensions, $0.02 per 1M tokens)
- **Retry Strategy:** Exponential backoff on 429/500 errors (3 retries max)

**Estimated Cost:**
- 1000 work orders × 200 tokens avg = 200k tokens = $0.004
- 500 equipment × 100 tokens avg = 50k tokens = $0.001
- Total Week 1 backfill per yacht: **~$0.01**

**Implementation Notes:**
- Process one yacht at a time (isolate failures)
- Log progress every 100 rows
- Store failed row IDs for manual retry

### Embedding Update Triggers (Future)

**When to update embeddings:**
- Work order completed → regenerate embedding (title + description + completion_notes changed)
- Equipment updated → regenerate embedding (name/model/manufacturer changed)
- Note added → generate embedding for new note

**Implementation:** Supabase Edge Function triggered on UPDATE (Week 2+)

---

## Acceptance Checks (Post-Migration)

### Check 1: Unique Constraint Exists

```sql
-- Verify unique_entity_link constraint exists
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname = 'unique_entity_link'
  AND conrelid = 'public.pms_entity_links'::regclass;

-- Expected: 1 row with contype = 'u' (unique)
```

### Check 2: Indexes Exist

```sql
-- Verify all FK join indexes exist
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN (
    'pms_work_order_parts',
    'pms_work_orders',
    'pms_entity_links',
    'pms_work_order_notes'
)
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;

-- Expected: At least 6 indexes (from migration 3)
```

### Check 3: Embedding Columns Exist

```sql
-- Verify embedding columns exist on Week 1 tables
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults', 'pms_work_order_notes')
  AND column_name IN ('search_embedding', 'embedding_text')
ORDER BY table_name, column_name;

-- Expected: 8 rows (4 tables × 2 columns)
```

### Check 4: Duplicate Link Prevention

```sql
-- Test: Attempt to create duplicate link
BEGIN;

INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
VALUES ('test-yacht-uuid', 'work_order', 'test-wo-uuid', 'part', 'test-part-uuid', 'related');

-- Second insert should fail with unique constraint violation
INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
VALUES ('test-yacht-uuid', 'work_order', 'test-wo-uuid', 'part', 'test-part-uuid', 'related');

ROLLBACK;

-- Expected: Second INSERT fails with ERROR: duplicate key value violates unique constraint "unique_entity_link"
```

### Check 5: RLS Policies Still Active

```sql
-- Verify RLS policies still exist after migrations
SELECT schemaname, tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename IN (
    'pms_work_orders',
    'pms_work_order_parts',
    'pms_entity_links',
    'doc_metadata'
)
ORDER BY tablename, policyname;

-- Expected: At least 1 SELECT policy per table
```

---

## Migration Execution Order

**Run migrations in this exact order:**

1. ✅ **Migration 1:** Unique constraint on pms_entity_links (blocks duplicates)
2. ✅ **Migration 3:** FK join indexes (safe, always beneficial)
3. ⏳ **Migration 4:** Embedding columns Week 1 (adds columns, no data)
4. ⏸️ **Migration 2:** Optional doc_metadata indexes (ONLY if EXPLAIN shows need)

**Why This Order:**
- Unique constraint first → prevents bad data from being inserted during testing
- FK indexes second → queries fast immediately
- Embedding columns third → schema ready for future backfill
- Optional indexes last → only add if proven necessary

---

## Rollback Plan

### Rollback Migration 1 (Unique Constraint)

```sql
-- Remove unique constraint
ALTER TABLE pms_entity_links
DROP CONSTRAINT IF EXISTS unique_entity_link;

-- Note: This allows duplicate links; only rollback if constraint causes issues
```

### Rollback Migration 3 (FK Indexes)

```sql
-- Drop all FK join indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_wop_work_order_yacht;
DROP INDEX CONCURRENTLY IF EXISTS idx_wo_equipment_yacht;
DROP INDEX CONCURRENTLY IF EXISTS idx_wo_last_activity;
DROP INDEX CONCURRENTLY IF EXISTS idx_entity_links_source;
DROP INDEX CONCURRENTLY IF EXISTS idx_entity_links_target;
DROP INDEX CONCURRENTLY IF EXISTS idx_won_work_order_yacht;

-- Note: Rollback only if indexes cause write performance issues (unlikely)
```

### Rollback Migration 4 (Embedding Columns)

```sql
-- Remove embedding columns
ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS search_embedding;
ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS embedding_text;

ALTER TABLE pms_equipment DROP COLUMN IF EXISTS search_embedding;
ALTER TABLE pms_equipment DROP COLUMN IF EXISTS embedding_text;

ALTER TABLE pms_faults DROP COLUMN IF EXISTS search_embedding;
ALTER TABLE pms_faults DROP COLUMN IF EXISTS embedding_text;

ALTER TABLE pms_work_order_notes DROP COLUMN IF EXISTS search_embedding;
ALTER TABLE pms_work_order_notes DROP COLUMN IF EXISTS embedding_text;

-- Note: Rollback only if embeddings are never used (unlikely)
```

---

## Deployment Checklist

Before deploying migrations to TENANT_1:

- [ ] Migrations reviewed by technical lead
- [ ] Migration files are idempotent (safe to rerun)
- [ ] Rollback plan documented and tested locally
- [ ] EXPLAIN ANALYZE run on staging to verify index necessity
- [ ] Docker tests pass with unique constraint in place
- [ ] Backup of pms_entity_links table taken (before migration 1)
- [ ] Migration applied to local Docker Supabase first
- [ ] Acceptance checks run and all pass
- [ ] No breaking changes to existing queries

---

## Next Steps

**After PHASE 8 Completion:**
1. Create migration SQL files (separate files for each migration)
2. Create Docker test matrix (tests/docker/run_work_orders_show_related_tests.py)
3. Create Staging CI skeleton (tests/ci/staging_work_orders_show_related.py)

---

**PHASE 8 COMPLETE** ✅

**Key Deliverables:**
- Migration 1: Unique constraint on pms_entity_links (prevents duplicates)
- Migration 2: Optional GIN indexes on doc_metadata (commented out, EXPLAIN-driven)
- Migration 3: Standard FK join indexes (always apply)
- Migration 4: Embedding columns on Week 1 tables (schema ready, backfill deferred)
- Embedding backfill outline (Week 2+, cost estimate included)
- Acceptance checks (5 verification queries)
- Rollback plan for all migrations
- Deployment checklist
