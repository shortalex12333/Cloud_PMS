# RAG Architecture & Implementation Plan

**Date**: 2026-02-04
**Author**: Claude (Automated Analysis)
**Status**: Planning Phase
**Depends On**: RAG_DATABASE_GROUND_TRUTH.md

---

## Executive Summary

This document outlines the architecture, critical issues, mitigations, and step-by-step implementation plan for adding document-level RAG to the F1 Search system. The design uses a two-stage retrieval approach (doc → chunk), maintains RLS isolation, leverages the existing 1536-d embedding stack, and reuses the single-round-trip pattern.

**Three critical issues were identified that would cause immediate failure if not addressed:**
1. **Empty Plate Error**: RPC returns chunk locations but not content
2. **Filter Bubble Risk**: Two-stage retrieval can miss documents
3. **Zombie Chunk Problem**: Document updates leave orphaned chunks

---

## 1. Architecture Overview

### 1.1 Two-Stage Retrieval Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        F1 SEARCH RAG FLOW                               │
└─────────────────────────────────────────────────────────────────────────┘

User Query: "What are the valve lash settings for the 3512C?"
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 0: CORTEX (Rewrite + Embed)                                      │
│  - Generate rewrites: ["valve lash 3512C", "3512C valve clearance"]     │
│  - Generate embeddings (1536-d, cached in Redis)                        │
│  - Budget: 150ms                                                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: DOCUMENT RETRIEVAL (search_index)                             │
│  - hyper_search_multi(rewrites, embeddings, org_id, yacht_id)           │
│  - Filter: object_type = 'document'                                     │
│  - Returns: top-20 document IDs                                         │
│  - Budget: 300ms DB time                                                │
│                                                                         │
│  ⚠️  REQUIRES: search_index.search_text contains content keywords       │
│      (not just filename) - see Issue #2 below                           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     │ doc_ids = [uuid1, uuid2, ...]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: CHUNK RETRIEVAL (search_document_chunks)                      │
│  - hyper_search_chunks_for_docs(rewrites, embeddings, doc_ids)          │
│  - Constrained to doc_ids from Stage 1                                  │
│  - Returns: top-10 chunks with content, offsets, metadata               │
│  - Budget: 300ms DB time                                                │
│                                                                         │
│  ⚠️  REQUIRES: RPC returns search_text - see Issue #1 below             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     │ chunks = [{content, offset, doc_id}, ...]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: ANSWER SYNTHESIS (Optional)                                   │
│  - Build grounded answer from chunk content                             │
│  - Include citations: (doc_id, chunk_id, offset)                        │
│  - Never hallucinate - only use retrieved content                       │
│  - Budget: model-dependent                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Latency Budget

| Stage | Cold (Cross-Region) | Warm (Cached) |
|-------|---------------------|---------------|
| Cortex (rewrite + embed) | 150ms | 5ms (Redis hit) |
| Stage 1: Doc retrieval | 300ms | 115ms (Redis hit) |
| Stage 2: Chunk retrieval | 300ms | 60ms (Redis hit) |
| **Total** | **750-900ms** | **180-300ms** |

---

## 2. Critical Issues & Mitigations

### 2.1 Issue #1: Empty Plate Error (CRITICAL)

**Problem:**
The proposed `hyper_search_chunks_for_docs` RPC selects `object_id`, `chunk_id`, `payload`, `start_offset`, `end_offset` but **NOT the actual chunk text (`search_text` / `content`)**.

The LLM receives: "Answer is in Document A, Chunk 5, offset 1234-1567"
The LLM needs: The actual text content to synthesize an answer.

**Impact:**
- RAG system retrieves location but not content
- Cannot build grounded answers
- System is fundamentally broken

**Fix:**
Update the RPC SELECT clause to include `c.search_text` (or `c.content`):

```sql
SELECT
    'document'::text AS object_type,
    c.object_id,
    c.chunk_id,
    c.search_text,  -- ← CRITICAL ADDITION
    COALESCE(c.payload, '{}'::jsonb) AS payload,
    c.start_offset,
    c.end_offset,
    s.fused_score,
    s.ranks,
    s.components
FROM scored s
JOIN search_document_chunks c
    ON c.object_id = s.object_id AND c.chunk_id = s.chunk_id
WHERE s.rn_doc <= chunks_per_doc
ORDER BY s.fused_score DESC
LIMIT page_limit;
```

---

### 2.2 Issue #2: Filter Bubble Risk (CRITICAL)

**Problem:**
Two-stage retrieval (docs → chunks) can miss relevant documents if the document-level `search_text` doesn't contain the query terms.

**Scenario:**
```
Query: "3512C valve lash settings"
Document: "Caterpillar Maintenance Manual" (filename)
Content: Contains "valve lash clearance 0.020 inch for 3512C"

Stage 1 searches search_index.search_text = "Caterpillar Maintenance Manual"
→ No match for "valve lash" or "3512C"
→ Document filtered out
→ Stage 2 never runs
→ Answer is missed
```

**Impact:**
- Relevant documents filtered before chunk search
- Recall drops significantly
- Users get "no results" for queries that have answers

**Fix:**
Propagate keywords from chunks to parent document:

1. **On chunk ingestion**, extract Top-50 TF-IDF keywords from all chunks
2. **Update parent `search_index.search_text`** with:
   - Filename
   - Document title (from metadata)
   - Top-50 keywords from chunks
   - System tags

```sql
-- Update document search_text with keyword bag
UPDATE search_index si
SET search_text = (
    SELECT string_agg(DISTINCT keyword, ' ')
    FROM (
        SELECT unnest(
            array_cat(
                ARRAY[si.payload->>'filename'],
                (SELECT array_agg(DISTINCT word)
                 FROM search_document_chunks sdc,
                      ts_stat('SELECT to_tsvector(''english'', sdc.content)') AS stat
                 WHERE sdc.document_id = si.object_id
                 ORDER BY stat.nentry DESC
                 LIMIT 50)
            )
        ) AS keyword
    ) kw
)
WHERE si.object_type = 'document'
  AND si.object_id = $1;
```

**Alternative (simpler):**
On chunk insert, concatenate first 500 chars of each chunk into parent `search_text` (crude but effective).

---

### 2.3 Issue #3: Zombie Chunk Problem (CRITICAL)

**Problem:**
Documents change. When a PDF is re-uploaded and re-chunked:
- Old version: 10 chunks (chunk_index 0-9)
- New version: 15 chunks (chunk_index 0-14)

If using UPSERT, chunks 0-9 get updated, but chunks 10-14 from the old version remain as "zombies" - they match queries but point to content that no longer exists.

**Impact:**
- Stale/incorrect content returned
- Citations point to non-existent passages
- Data integrity compromised

**Fix:**
**Atomic Replacement** - wrap chunk writes in a transaction:

```python
async def replace_document_chunks(conn, document_id: str, new_chunks: List[dict]):
    """
    Atomically replace all chunks for a document.
    DELETE old chunks, INSERT new ones in single transaction.
    """
    async with conn.transaction():
        # Step 1: Delete ALL existing chunks for this document
        await conn.execute(
            "DELETE FROM search_document_chunks WHERE document_id = $1",
            document_id
        )

        # Step 2: Insert new chunks
        await conn.executemany(
            """
            INSERT INTO search_document_chunks
                (document_id, yacht_id, chunk_index, content, embedding, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [(document_id, c['yacht_id'], c['chunk_index'],
              c['content'], c['embedding'], c['metadata'])
             for c in new_chunks]
        )

        # Step 3: Update parent search_index with new keywords
        await update_document_keywords(conn, document_id)
```

**Key Principle**: DELETE before INSERT, in a transaction.

---

### 2.4 Issue #4: Citation Offset Alignment (IMPORTANT)

**Problem:**
`start_offset` and `end_offset` may be relative to chunk (0 to ~1000) or relative to full document (e.g., 50402 to 51200).

For PDF highlighting, the frontend needs **global offsets** (position in the full document).

**Fix:**
Store `global_offset_start` in `search_document_chunks`:

```sql
ALTER TABLE search_document_chunks
ADD COLUMN global_offset_start INT;

-- On chunk insert, calculate:
-- global_offset_start = sum of lengths of all previous chunks
```

Or compute at chunking time:
```python
offset = 0
for i, chunk in enumerate(chunks):
    chunk['global_offset_start'] = offset
    chunk['global_offset_end'] = offset + len(chunk['content'])
    offset = chunk['global_offset_end'] - overlap  # account for overlap
```

---

## 3. Database Schema Changes

### 3.1 Migration 010: Enhance search_document_chunks

```sql
-- Migration 010: Enhance search_document_chunks for RAG
-- Add missing columns and indexes for hybrid search

-- Add search_text column (copy of content for trigram matching)
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS search_text TEXT;

-- Populate search_text from content
UPDATE search_document_chunks
SET search_text = content
WHERE search_text IS NULL;

-- Make search_text non-null going forward
ALTER TABLE search_document_chunks
ALTER COLUMN search_text SET NOT NULL;

-- Add tsvector column for FTS
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS tsv TSVECTOR
GENERATED ALWAYS AS (to_tsvector('english', coalesce(search_text, ''))) STORED;

-- Add global offset for PDF citations
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS global_offset_start INT DEFAULT 0;

ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS global_offset_end INT DEFAULT 0;

-- Add org_id for RLS (if not exists)
ALTER TABLE search_document_chunks
ADD COLUMN IF NOT EXISTS org_id UUID;

-- Populate org_id from yacht mapping (yacht_id → org_id)
-- This depends on your org/yacht relationship

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_sdc_tsv
ON search_document_chunks USING gin (tsv);

CREATE INDEX IF NOT EXISTS ix_sdc_trigram
ON search_document_chunks USING gin (search_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_sdc_vector
ON search_document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m=16, ef_construction=64);

CREATE INDEX IF NOT EXISTS ix_sdc_doc_id
ON search_document_chunks (document_id);

CREATE INDEX IF NOT EXISTS ix_sdc_yacht
ON search_document_chunks (yacht_id);

-- RLS (if not already enabled)
ALTER TABLE search_document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY sdc_yacht_isolation ON search_document_chunks
FOR SELECT USING (
    yacht_id = (current_setting('request.jwt.claims', true)::jsonb ->> 'yacht_id')::uuid
);
```

### 3.2 Migration 011: hyper_search_chunks_for_docs RPC

```sql
-- Migration 011: Chunk-level hybrid search RPC
-- Constrained to specific document IDs from Stage 1

CREATE OR REPLACE FUNCTION hyper_search_chunks_for_docs(
    rewrite_texts       text[],
    rewrite_embeddings  vector(1536)[],
    doc_ids             uuid[],
    filter_org_id       uuid,
    filter_yacht_id     uuid,
    rrf_k               int DEFAULT 60,
    page_limit          int DEFAULT 10,
    chunks_per_doc      int DEFAULT 3,
    trigram_limit       float DEFAULT 0.15
) RETURNS TABLE (
    object_type       text,
    object_id         uuid,
    chunk_id          int,
    search_text       text,      -- ← CRITICAL: actual content
    payload           jsonb,
    start_offset      int,
    end_offset        int,
    global_offset_start int,
    fused_score       double precision,
    ranks             jsonb,
    components        jsonb
) SECURITY INVOKER LANGUAGE plpgsql AS $$
BEGIN
    -- Set trigram threshold
    PERFORM set_limit(trigram_limit);

    RETURN QUERY
    WITH rewrites AS (
        SELECT generate_subscripts(rewrite_texts, 1) AS idx,
               rewrite_texts[generate_subscripts(rewrite_texts, 1)] AS q,
               rewrite_embeddings[generate_subscripts(rewrite_embeddings, 1)] AS v
    ),
    -- Trigram matches
    trigram AS (
        SELECT r.idx, c.document_id AS object_id, c.chunk_index AS chunk_id,
               similarity(c.search_text, r.q) AS trigram_score,
               row_number() OVER (PARTITION BY r.idx ORDER BY similarity(c.search_text, r.q) DESC) AS trigram_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.search_text % r.q
        LIMIT 200
    ),
    -- FTS matches
    fts AS (
        SELECT r.idx, c.document_id AS object_id, c.chunk_index AS chunk_id,
               ts_rank(c.tsv, websearch_to_tsquery('english', r.q)) AS fts_score,
               row_number() OVER (PARTITION BY r.idx ORDER BY ts_rank(c.tsv, websearch_to_tsquery('english', r.q)) DESC) AS fts_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.tsv @@ websearch_to_tsquery('english', r.q)
        LIMIT 200
    ),
    -- Vector matches
    vec AS (
        SELECT r.idx, c.document_id AS object_id, c.chunk_index AS chunk_id,
               CASE WHEN r.v IS NULL THEN NULL ELSE 1 - (c.embedding <=> r.v) END AS vector_sim,
               CASE WHEN r.v IS NULL THEN NULL ELSE row_number() OVER (PARTITION BY r.idx ORDER BY c.embedding <=> r.v ASC) END AS vector_rank
        FROM rewrites r
        JOIN search_document_chunks c
            ON c.yacht_id = filter_yacht_id
            AND c.document_id = ANY(doc_ids)
        WHERE c.embedding IS NOT NULL
        LIMIT 200
    ),
    -- Union and aggregate
    unioned AS (
        SELECT idx, object_id, chunk_id,
               MIN(trigram_rank) AS trigram_rank,
               MIN(fts_rank) AS fts_rank,
               MIN(vector_rank) AS vector_rank,
               MAX(trigram_score) AS trigram_score,
               MAX(fts_score) AS fts_score,
               MAX(vector_sim) AS vector_sim
        FROM (
            SELECT idx, object_id, chunk_id, trigram_rank, NULL::bigint AS fts_rank, NULL::bigint AS vector_rank,
                   trigram_score, NULL::real AS fts_score, NULL::double precision AS vector_sim FROM trigram
            UNION ALL
            SELECT idx, object_id, chunk_id, NULL, fts_rank, NULL,
                   NULL, fts_score, NULL FROM fts
            UNION ALL
            SELECT idx, object_id, chunk_id, NULL, NULL, vector_rank,
                   NULL, NULL, vector_sim FROM vec
        ) u
        GROUP BY 1, 2, 3
    ),
    -- Score and rank
    scored AS (
        SELECT u.object_id, u.chunk_id,
               (COALESCE(1.0/(rrf_k + u.trigram_rank), 0) +
                COALESCE(1.0/(rrf_k + u.fts_rank), 0) +
                COALESCE(1.0/(rrf_k + u.vector_rank), 0)) AS fused_score,
               jsonb_build_object('trigram', u.trigram_rank, 'fts', u.fts_rank, 'vector', u.vector_rank) AS ranks,
               jsonb_build_object('trigram', u.trigram_score, 'fts', u.fts_score, 'vector', u.vector_sim) AS components,
               row_number() OVER (PARTITION BY u.object_id ORDER BY
                   (COALESCE(1.0/(rrf_k + u.trigram_rank), 0) +
                    COALESCE(1.0/(rrf_k + u.fts_rank), 0) +
                    COALESCE(1.0/(rrf_k + u.vector_rank), 0)) DESC) AS rn_doc
        FROM unioned u
    )
    SELECT 'document'::text AS object_type,
           c.document_id AS object_id,
           c.chunk_index AS chunk_id,
           c.search_text,                    -- ← ACTUAL CONTENT
           COALESCE(c.metadata, '{}'::jsonb) AS payload,
           0 AS start_offset,                -- or c.start_offset if exists
           length(c.search_text) AS end_offset,
           COALESCE(c.global_offset_start, 0) AS global_offset_start,
           s.fused_score,
           s.ranks,
           s.components
    FROM scored s
    JOIN search_document_chunks c
        ON c.document_id = s.object_id AND c.chunk_index = s.chunk_id
    WHERE s.rn_doc <= chunks_per_doc
    ORDER BY s.fused_score DESC
    LIMIT page_limit;
END;
$$;

COMMENT ON FUNCTION hyper_search_chunks_for_docs IS
'Chunk-level hybrid search constrained to specific documents. Returns actual content for RAG grounding.';
```

---

## 4. Implementation Plan

### Phase 1: Schema & Backfill (Week 1)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Apply migration 010 (enhance chunks table) | DBA | 1 day | None |
| Apply migration 011 (chunk search RPC) | DBA | 1 day | 010 |
| Backfill chunks for all 963 documents | Worker | 2-3 days | 010 |
| Update document keywords in search_index | Worker | 1 day | Backfill |

### Phase 2: API Integration (Week 2)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Add chunk-stage call to f1_search_streaming.py | Backend | 2 days | Phase 1 |
| Add chunk result cache (Redis) | Backend | 1 day | None |
| Update SSE events for chunk citations | Backend | 1 day | API changes |
| Test end-to-end RAG flow | QA | 2 days | API changes |

### Phase 3: Answer Synthesis (Week 3, Optional)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Create /api/f1/rag/answer endpoint | Backend | 2 days | Phase 2 |
| Implement citation formatting | Backend | 1 day | Endpoint |
| Add faithfulness validation | Backend | 1 day | Endpoint |

---

## 5. Caching Strategy

### 5.1 Cache Keys

| Cache | Key Pattern | TTL | Purpose |
|-------|-------------|-----|---------|
| Result (Doc) | `rs_doc:{query_hash}:{org}:{yacht}:{ver}` | 120s | Doc-stage results |
| Result (Chunk) | `rs_chunk:{query_hash}:{doc_ids_hash}:{org}:{yacht}` | 60s | Chunk-stage results |
| Rewrite | `rw:{query_hash}:{org}:{yacht}:{role}` | 15min | Query rewrites |
| Embedding | `emb:{text_hash}:{org}` | 30min | Text embeddings |

### 5.2 Invalidation

On document update/delete:
1. Delete chunks: `DELETE FROM search_document_chunks WHERE document_id = $1`
2. Invalidate cache: `DEL rs_doc:*:{org}:*` (or use pg_notify)
3. Re-chunk document
4. Update parent keywords

---

## 6. Success Criteria

### 6.1 Retrieval Quality

| Metric | Target | Measurement |
|--------|--------|-------------|
| Doc Recall@50 | ≥ 0.95 | Canary gold set |
| Chunk Recall@20 | ≥ 0.90 | Answerable queries |
| NDCG@10 | ≥ 0.80 | Relevance ranking |
| Precision@5 | ≥ 0.85 | Top results quality |

### 6.2 Latency

| Metric | Target (Warm) | Target (Cold) |
|--------|---------------|---------------|
| first_event_ms | ≤ 150ms | ≤ 250ms |
| finalized_ms | ≤ 300ms | ≤ 900ms |

### 6.3 Faithfulness

| Metric | Target |
|--------|--------|
| Grounded answers | ≥ 90% |
| Citation coverage | 100% (all claims have citation) |

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Backfill takes too long | Medium | Delays launch | Parallelize, prioritize active docs |
| Chunk search latency exceeds budget | Low | User experience | Tighten limits, add caching |
| Filter Bubble persists | Medium | Missed results | Monitor recall, adjust keyword propagation |
| Zombie chunks after updates | Low (with fix) | Data integrity | Atomic DELETE+INSERT pattern |

---

## 8. Appendix: Ingestion Worker Changes

### 8.1 Atomic Chunk Replacement

```python
async def index_document(document_id: str, yacht_id: str):
    """
    Index a document: extract, chunk, embed, store.
    Uses atomic replacement to avoid zombie chunks.
    """
    # 1. Extract text from storage
    text = await extract_text(document_id)

    # 2. Chunk with overlap
    chunks = chunk_text(text, chunk_size=1000, overlap=200)

    # 3. Generate embeddings
    embeddings = await generate_embeddings([c['content'] for c in chunks])

    # 4. Calculate global offsets
    offset = 0
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i]
        chunk['chunk_index'] = i
        chunk['global_offset_start'] = offset
        chunk['global_offset_end'] = offset + len(chunk['content'])
        offset = chunk['global_offset_end'] - 200  # overlap

    # 5. Atomic replace (DELETE + INSERT in transaction)
    async with db.transaction():
        await db.execute(
            "DELETE FROM search_document_chunks WHERE document_id = $1",
            document_id
        )
        await db.executemany(
            """INSERT INTO search_document_chunks
               (document_id, yacht_id, chunk_index, search_text, content,
                embedding, metadata, global_offset_start, global_offset_end)
               VALUES ($1, $2, $3, $4, $4, $5, $6, $7, $8)""",
            [(document_id, yacht_id, c['chunk_index'], c['content'],
              c['embedding'], c.get('metadata', {}),
              c['global_offset_start'], c['global_offset_end'])
             for c in chunks]
        )

    # 6. Update parent keywords
    await update_document_keywords(document_id)

    # 7. Mark as indexed
    await db.execute(
        "UPDATE doc_metadata SET indexed = true, indexed_at = now() WHERE id = $1",
        document_id
    )
```

### 8.2 Keyword Propagation

```python
async def update_document_keywords(document_id: str):
    """
    Update search_index.search_text with keywords from chunks.
    Solves the Filter Bubble problem.
    """
    # Get top keywords from chunks
    keywords = await db.fetch("""
        SELECT word, nentry
        FROM search_document_chunks sdc,
             ts_stat(format('SELECT tsv FROM search_document_chunks WHERE document_id = %L', $1))
        WHERE sdc.document_id = $1
        ORDER BY nentry DESC
        LIMIT 50
    """, document_id)

    keyword_text = ' '.join(kw['word'] for kw in keywords)

    # Update parent search_index
    await db.execute("""
        UPDATE search_index
        SET search_text = concat_ws(' ',
            payload->>'filename',
            payload->>'title',
            $2
        )
        WHERE object_type = 'document' AND object_id = $1
    """, document_id, keyword_text)
```

---

*End of Document*
