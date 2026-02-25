# Search Pipeline Recommendations

**Generated:** 2026-02-20
**Pilot Results:** 10.5% Recall@3 (34/324 hits)
**Target:** 90% Recall@3

---

## Executive Summary

The search pipeline has a critical indexing gap. The `search_index` table contains only **1,000 rows** (713 documents, 287 certificates), while the system has thousands of parts, work orders, faults, and inventory items that are NOT indexed.

**Root Cause:** Entity types are not being indexed in `search_index` table.

| Entity Type | In search_index? | Pilot Recall@3 |
|-------------|------------------|----------------|
| document | ✓ 713 rows | 0% (ID mismatch) |
| certificate | ✓ 287 rows | 0% (ID mismatch) |
| parts | ✗ NOT INDEXED | 55.6% (separate path) |
| work_order | ✗ NOT INDEXED | 33.3% (separate path) |
| fault | ✗ NOT INDEXED | 0% |
| inventory | ✗ NOT INDEXED | 0% |
| receiving | ✗ NOT INDEXED | 0% |
| shopping_list | ✗ NOT INDEXED | 0% |
| work_order_note | ✗ NOT INDEXED | 0% |

---

## Critical Fixes Required

### Fix 1: Index All Entity Types in search_index

**File:** `apps/api/workers/embedding_worker_1536.py`

Add entity types to the worker's scope:

```python
# Current - only some types indexed
INDEXED_TYPES = ['document', 'certificate', 'handover_export']

# Required - add all searchable entities
INDEXED_TYPES = [
    'document', 'certificate', 'handover_export',
    'part', 'work_order', 'fault', 'inventory_item',
    'receiving', 'shopping_list_item', 'work_order_note',
    'equipment'
]
```

### Fix 2: Create Index Population Migration

**New Migration:** `supabase/migrations/YYYYMMDD_populate_search_index.sql`

```sql
-- Populate search_index with pms_parts
INSERT INTO search_index (
    id, yacht_id, object_type, object_id, search_text,
    payload, tsv, embedding, updated_at
)
SELECT
    gen_random_uuid() as id,
    p.yacht_id,
    'part' as object_type,
    p.id as object_id,
    CONCAT_WS(' ', p.name, p.part_number, p.manufacturer, p.description) as search_text,
    jsonb_build_object(
        'label', p.name,
        'part_number', p.part_number,
        'manufacturer', p.manufacturer
    ) as payload,
    to_tsvector('english', CONCAT_WS(' ', p.name, p.part_number, p.manufacturer, p.description)) as tsv,
    p.search_embedding as embedding,
    NOW() as updated_at
FROM pms_parts p
WHERE p.yacht_id IS NOT NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET
    search_text = EXCLUDED.search_text,
    payload = EXCLUDED.payload,
    tsv = EXCLUDED.tsv,
    embedding = EXCLUDED.embedding,
    updated_at = NOW();

-- Similar for work_orders
INSERT INTO search_index (
    id, yacht_id, object_type, object_id, search_text,
    payload, tsv, embedding, updated_at
)
SELECT
    gen_random_uuid() as id,
    wo.yacht_id,
    'work_order' as object_type,
    wo.id as object_id,
    CONCAT_WS(' ', wo.label, wo.description, wo.status) as search_text,
    jsonb_build_object(
        'label', wo.label,
        'status', wo.status,
        'priority', wo.priority
    ) as payload,
    to_tsvector('english', CONCAT_WS(' ', wo.label, wo.description)) as tsv,
    wo.search_embedding as embedding,
    NOW() as updated_at
FROM pms_work_orders wo
WHERE wo.yacht_id IS NOT NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET
    search_text = EXCLUDED.search_text,
    payload = EXCLUDED.payload,
    tsv = EXCLUDED.tsv,
    embedding = EXCLUDED.embedding,
    updated_at = NOW();

-- Add for faults, inventory, receiving, shopping_list_items, work_order_notes
```

### Fix 3: Add Unique Constraint to search_index

```sql
-- Prevent duplicate indexing
CREATE UNIQUE INDEX IF NOT EXISTS idx_search_index_object_unique
ON search_index (object_type, object_id);
```

### Fix 4: Create Triggers for Real-time Index Updates

**New Migration:** `supabase/migrations/YYYYMMDD_search_index_triggers.sql`

```sql
-- Function to sync to search_index
CREATE OR REPLACE FUNCTION sync_to_search_index()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO search_index (
        id, yacht_id, object_type, object_id,
        search_text, payload, tsv, embedding, updated_at
    )
    VALUES (
        gen_random_uuid(),
        NEW.yacht_id,
        TG_ARGV[0],  -- object_type passed as argument
        NEW.id,
        -- Build search_text based on entity type
        CASE TG_ARGV[0]
            WHEN 'part' THEN CONCAT_WS(' ', NEW.name, NEW.part_number, NEW.manufacturer)
            WHEN 'work_order' THEN CONCAT_WS(' ', NEW.label, NEW.description)
            WHEN 'fault' THEN CONCAT_WS(' ', NEW.description, NEW.severity)
            ELSE NEW.name
        END,
        to_jsonb(NEW),
        to_tsvector('english', COALESCE(NEW.name, '') || ' ' || COALESCE(NEW.description, '')),
        NEW.search_embedding,
        NOW()
    )
    ON CONFLICT (object_type, object_id) DO UPDATE SET
        search_text = EXCLUDED.search_text,
        payload = EXCLUDED.payload,
        tsv = EXCLUDED.tsv,
        embedding = EXCLUDED.embedding,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for each entity table
CREATE TRIGGER trg_pms_parts_search_index
AFTER INSERT OR UPDATE ON pms_parts
FOR EACH ROW EXECUTE FUNCTION sync_to_search_index('part');

CREATE TRIGGER trg_pms_work_orders_search_index
AFTER INSERT OR UPDATE ON pms_work_orders
FOR EACH ROW EXECUTE FUNCTION sync_to_search_index('work_order');

-- Add similar triggers for: pms_faults, pms_inventory, etc.
```

---

## Ranking Improvements

### Improvement 1: Adjust RRF Weights

**File:** `apps/api/services/scoring_engine.py`

Current weights favor text too heavily:
```python
# Current
FUSION_WEIGHTS = {
    'text': 0.45,
    'vector': 0.35,
    'recency': 0.15,
    'bias': 0.05
}
```

Recommended for semantic search improvement:
```python
# Recommended
FUSION_WEIGHTS = {
    'text': 0.35,    # Reduce text weight
    'vector': 0.45,  # Increase vector weight
    'recency': 0.12,
    'bias': 0.08     # Increase bias for role-based boosting
}
```

### Improvement 2: Lower Vector Similarity Threshold

**File:** `apps/api/services/candidate_finder.py`

```python
# Current
'p_min_vector': 0.50  # Too strict

# Recommended
'p_min_vector': 0.35  # Allow more semantic matches
```

### Improvement 3: Add Query Expansion

**File:** `apps/api/services/query_processor.py` (new)

```python
# Synonym expansion for maritime terms
SYNONYMS = {
    'filter': ['element', 'cartridge'],
    'pump': ['impeller', 'motor'],
    'generator': ['genset', 'gen'],
    'wo': ['work order', 'workorder'],
    'cert': ['certificate', 'certification'],
}

def expand_query(query: str) -> str:
    """Expand query with synonyms for better recall."""
    words = query.lower().split()
    expanded = []
    for word in words:
        expanded.append(word)
        if word in SYNONYMS:
            expanded.extend(SYNONYMS[word])
    return ' '.join(expanded)
```

---

## Implementation Priority

| Priority | Fix | Impact | Effort |
|----------|-----|--------|--------|
| **P0** | Index all entity types in search_index | +60% Recall | High |
| **P1** | Add search_index triggers | Keeps index fresh | Medium |
| **P2** | Lower vector threshold | +10% Recall | Low |
| **P3** | Adjust RRF weights | +5% Recall | Low |
| **P4** | Add query expansion | +5% Recall | Medium |

---

## Verification Plan

After implementing fixes:

1. **Run full indexing migration** - populate search_index with all entities
2. **Verify index counts:** Should see 5,000+ rows (not 1,000)
3. **Re-run pilot test:** `npx tsx test/pilot/pilot_test.ts`
4. **Target metrics:**
   - Recall@3 > 60% (immediate)
   - Recall@3 > 80% (with tuning)
   - Recall@3 > 90% (with query expansion)

---

## Workers to Enable

Ensure these background services are running on Render:

1. **Embedding Worker** - generates embeddings for new entities
2. **Search Index Sync Worker** - keeps search_index updated
3. **Cortex** - query rewriting and intent classification

Check Render dashboard for:
- `celeste-embedding-worker` - should be RUNNING
- `celeste-search-sync` - should be RUNNING
- `celeste-cortex` - should be RUNNING

---

*Generated by GSD Analysis Agent*
