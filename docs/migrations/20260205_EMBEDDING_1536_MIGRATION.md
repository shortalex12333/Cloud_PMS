# Migration: 1536-dim Embedding (OpenAI text-embedding-3-small)

**Date:** 2026-02-05
**Author:** Claude
**Decision:** Canonical retrieval model = OpenAI text-embedding-3-small (1536-dim)

## Rationale

- **Consistency > everything**: One embedding space eliminates edge mismatches
- **Quality margin**: 1536 recall on abstract/longer contexts helps yacht ops
- **Cost**: Acceptable (~$0.02/1M tokens), mitigated by caching

---

## Phase 0: Config Flags

```python
# apps/api/config/embedding.py or environment
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536
EMBEDDING_VERSION = 3  # Recorded per row for migration tracking
```

---

## Phase 1: Schema (Add, Don't Break)

### SQL Migration

```sql
-- =============================================================================
-- 1536-DIM EMBEDDING MIGRATION
-- =============================================================================
-- Run in transaction, indexes CONCURRENTLY outside transaction

BEGIN;

-- 1. search_index: Add 1536-dim column and metadata
ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_1536 vector(1536),
    ADD COLUMN IF NOT EXISTS embedding_model text,
    ADD COLUMN IF NOT EXISTS embedding_version int,
    ADD COLUMN IF NOT EXISTS embedding_hash text;

COMMENT ON COLUMN public.search_index.embedding_1536 IS '1536-dim OpenAI text-embedding-3-small vector';
COMMENT ON COLUMN public.search_index.embedding_model IS 'Model name (text-embedding-3-small)';
COMMENT ON COLUMN public.search_index.embedding_version IS 'Schema version (3 = 1536-dim OpenAI)';
COMMENT ON COLUMN public.search_index.embedding_hash IS 'SHA256 of search_text for delta embedding';

-- 2. search_document_chunks: Add 1536-dim column and metadata
ALTER TABLE public.search_document_chunks
    ADD COLUMN IF NOT EXISTS embedding_1536 vector(1536),
    ADD COLUMN IF NOT EXISTS embedding_model text,
    ADD COLUMN IF NOT EXISTS embedding_version int,
    ADD COLUMN IF NOT EXISTS embedding_hash text;

COMMENT ON COLUMN public.search_document_chunks.embedding_1536 IS '1536-dim OpenAI text-embedding-3-small vector';

COMMIT;

-- 3. HNSW Indexes (run outside transaction with CONCURRENTLY)
-- search_index
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_si_vec1536_hnsw
    ON public.search_index
    USING hnsw (embedding_1536 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- search_document_chunks
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sdc_vec1536_hnsw
    ON public.search_document_chunks
    USING hnsw (embedding_1536 vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### Verification

```sql
-- Check columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('search_index', 'search_document_chunks')
  AND column_name LIKE 'embedding%'
ORDER BY table_name, column_name;

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('search_index', 'search_document_chunks')
  AND indexname LIKE '%vec1536%';
```

---

## Phase 2: RPC Updates

### hyper_search Changes

```sql
-- In hyper_search RPC, change:
-- OLD: ORDER BY si.embedding <=> query_embedding
-- NEW: ORDER BY si.embedding_1536 <=> query_embedding

-- Vector similarity CTE becomes:
vec AS (
    SELECT
        r.idx,
        si.object_type,
        si.object_id,
        1 - (si.embedding_1536 <=> r.v) AS vector_sim,
        row_number() OVER (PARTITION BY r.idx ORDER BY si.embedding_1536 <=> r.v ASC) AS vector_rank
    FROM rewrites r
    JOIN search_index si
        ON si.yacht_id = filter_yacht_id
    WHERE si.embedding_1536 IS NOT NULL
      AND r.v IS NOT NULL
    LIMIT 200
)
```

### hyper_search_docs_by_chunks Changes

```sql
-- Similar update for chunk search
vec AS (
    SELECT
        r.idx,
        c.document_id,
        c.chunk_index,
        CASE WHEN r.v IS NULL THEN NULL ELSE 1 - (c.embedding_1536 <=> r.v) END AS vector_sim,
        ...
    FROM rewrites r
    JOIN search_document_chunks c
        ON c.yacht_id = filter_yacht_id
        AND c.document_id = ANY(doc_ids)
    WHERE c.embedding_1536 IS NOT NULL
      AND r.v IS NOT NULL
    LIMIT 200
)
```

---

## Phase 3: Embedding Worker

See: `apps/api/workers/embedding_worker_1536.py`

Key features:
- Batch processing (100-200 per batch)
- Concurrency 4-8 workers
- Delta embedding: only when `embedding_hash != content_hash OR embedding_version <> 3`
- Writes: `embedding_1536`, `embedding_model`, `embedding_version=3`, `embedding_hash`
- Uses Supavisor port 6543

---

## Phase 4: Cleanup

After coverage ≥ 95%:

```sql
-- Verify coverage
SELECT
    COUNT(*) AS total,
    COUNT(embedding_1536) AS with_1536,
    COUNT(CASE WHEN embedding_version = 3 THEN 1 END) AS version_3,
    ROUND(100.0 * COUNT(embedding_1536) / COUNT(*), 1) AS pct_coverage
FROM search_index;

-- Optional: Drop old embedding column after 100% migration
-- ALTER TABLE public.search_index DROP COLUMN embedding;

-- Enforce version 3 on new writes (via RPC or trigger)
-- Already handled by embedding_worker and admin_upsert_search_index
```

---

## Acceptance Gates

| Metric | Target |
|--------|--------|
| Coverage | ≥ 95% rows with embedding_1536 + version=3 |
| Quality | Canary NDCG@10 ≥ current |
| Latency | hyper_search ≤ 200ms, chunks ≤ 300ms |
| Security | RLS clean, anon sees 0 |

---

## Cost Estimate

- Current: 13,271 rows × ~500 tokens avg = ~6.6M tokens
- Chunks: ~10K chunks × ~300 tokens = ~3M tokens
- Total: ~10M tokens × $0.02/1M = **~$0.20**
- With caching: negligible ongoing cost
