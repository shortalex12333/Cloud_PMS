# RAG Database Ground Truth & Gap Analysis

**Date**: 2026-02-04
**Author**: Claude (Automated Analysis)
**Status**: Planning Phase

---

## Executive Summary

This document provides a comprehensive analysis of the current database state for implementing document-level RAG (Retrieval-Augmented Generation) in the F1 Search system. The analysis reveals a **critical gap**: documents in `search_index` contain only filenames (~48 chars avg), not content, while the actual chunked content exists in a separate `search_document_chunks` table with only 6 documents chunked out of 963 active documents.

---

## 1. Current Database State

### 1.1 Table Inventory

| Table | Status | Row Count | Purpose |
|-------|--------|-----------|---------|
| `doc_metadata` | EXISTS | 1,000 | Source of truth for document metadata |
| `search_document_chunks` | EXISTS | 1,000 | Chunked document content with embeddings |
| `search_index` | EXISTS | 1,000 | Unified hybrid search surface |
| `documents` | EXISTS | ~300 | Legacy document table (superseded by doc_metadata) |
| `embedding_jobs` | EXISTS | ~1,000 | Async embedding job queue |
| `equipment` | EXISTS | - | GraphRAG canonical entities |
| `parts` | EXISTS | - | Parts inventory (also in search_index) |
| `graph_nodes` | EXISTS | - | GraphRAG extracted entities |
| `graph_edges` | EXISTS | - | GraphRAG relationships |

### 1.2 doc_metadata (Document Source of Truth)

**Schema:**
```
id              UUID PRIMARY KEY
yacht_id        UUID NOT NULL
source          TEXT (e.g., 'document_lens', 'nas')
filename        TEXT
content_type    TEXT (MIME type)
storage_path    TEXT (Supabase Storage path)
equipment_ids   UUID[]
tags            TEXT[]
indexed         BOOLEAN (default false)
indexed_at      TIMESTAMPTZ
metadata        JSONB
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
deleted_at      TIMESTAMPTZ (soft delete)
deleted_by      UUID
deleted_reason  TEXT
```

**Statistics:**
- Total: 1,000 documents
- Active (not deleted): 963
- Indexed (indexed=true): 853
- Actually chunked: **6** (0.6%)

**Key Observations:**
1. `indexed=true` does NOT mean chunks exist - it's metadata-only
2. Soft delete support exists (deleted_at, deleted_by, deleted_reason)
3. No `content` or `text` column - documents are stored in Supabase Storage

### 1.3 search_document_chunks (Chunked Content)

**Schema:**
```
id                    UUID PRIMARY KEY
yacht_id              UUID NOT NULL
document_id           UUID NOT NULL (FK to doc_metadata.id)
chunk_index           INT NOT NULL
content               TEXT NOT NULL (actual chunk text)
embedding             VECTOR(1536)
equipment_ids         UUID[]
fault_codes           TEXT[]
tags                  TEXT[]
metadata              JSONB (loc, line, source info)
created_at            TIMESTAMPTZ
graph_extracted       BOOLEAN
graph_extract_status  TEXT
is_section_entry      BOOLEAN
```

**Statistics:**
- Total chunks: 1,000
- Unique documents: 6 (avg ~167 chunks/doc)
- With embeddings: 1,000 (100%)
- With content: 1,000 (100%)
- Content length: min=3, avg=759, max=1,000 chars

**Key Observations:**
1. Chunking uses ~1000 char chunks with 200 char overlap
2. 100% embedding coverage (OpenAI text-embedding-3-small, 1536-d)
3. Metadata includes line numbers for citation
4. GraphRAG extraction status tracked but mostly `pending`

### 1.4 search_index (Hybrid Search Surface)

**Schema:**
```
id                  BIGSERIAL PRIMARY KEY
object_type         TEXT NOT NULL ('part', 'document', 'inventory', etc.)
object_id           UUID NOT NULL
org_id              UUID NOT NULL
yacht_id            UUID
search_text         TEXT (indexed for trigram + FTS)
tsv                 TSVECTOR GENERATED
embedding           VECTOR(1536)
payload             JSONB
embedding_version   SMALLINT
updated_at          TIMESTAMPTZ
popularity_score    FLOAT
filters             JSONB
```

**Statistics by object_type:**
| Type | Count | Embeddings | Avg search_text |
|------|-------|------------|-----------------|
| part | 709 | 100% | 60 chars |
| document | 291 | 100% | 48 chars |

**CRITICAL FINDING - Document search_text Analysis:**
```
filename: test.pdf
search_text: 'test.pdf    '
MATCH: filename == search_text ✓

filename: Generic_guest_amenities_Document_3.pdf
search_text: 'Generic_guest_amenities_Document_3.pdf general   general'
CONTENT: filename + tags only
```

**Documents in search_index contain ONLY:**
- Filename
- Tags (sometimes)
- NO document content
- NO keywords from chunks

---

## 2. Data Flow Analysis

### 2.1 Current Document Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LOCAL AGENT (NAS/Device)                                               │
│  - Monitors filesystem for changes                                       │
│  - Pushes files to celeste-digest-index service                         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  celeste-digest-index (Render Service)                                  │
│  Endpoint: POST /webhook/ingest-docs-nas-cloud                          │
│                                                                         │
│  1. Check duplicate (filename + yacht_id)                               │
│  2. Upload to Supabase Storage (bucket: documents)                      │
│  3. Insert metadata → doc_metadata table                                │
│  4. Trigger indexing webhook (async)                                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  INDEXING WORKFLOW                                                      │
│  Endpoint: POST /webhook/index-documents                                │
│                                                                         │
│  1. Call extraction service (celeste-file-type.onrender.com/extract)    │
│  2. Chunk text (1000 chars, 200 overlap)                                │
│  3. Generate embeddings (OpenAI text-embedding-3-small)                 │
│  4. Insert chunks → search_document_chunks table                        │
│  5. Update doc_metadata.indexed = true                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current Search Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  F1 SEARCH STREAMING (/api/f1/search/stream)                            │
│                                                                         │
│  1. Generate rewrites (Cortex) - cached in Redis                        │
│  2. Generate embeddings (OpenAI) - cached in Redis                      │
│  3. Call hyper_search_multi RPC on search_index                         │
│     - Trigram search (% operator)                                       │
│     - FTS search (websearch_to_tsquery)                                 │
│     - Vector search (cosine via <=>)                                    │
│     - RRF fusion (k=60)                                                 │
│  4. Return results via SSE                                              │
└─────────────────────────────────────────────────────────────────────────┘

                    ↓ PROBLEM ↓

Documents in search_index have NO CONTENT, only filenames.
Query "valve lash settings" will NOT match document titled
"Caterpillar Maintenance Manual" even if content contains the answer.
```

---

## 3. Gap Analysis

### 3.1 Critical Gaps

| Gap | Impact | Severity |
|-----|--------|----------|
| Documents in search_index lack content | Search misses relevant documents | **CRITICAL** |
| Only 6/963 documents chunked | 99.4% of documents have no searchable content | **CRITICAL** |
| No chunk-level search RPC | Cannot ground answers in specific passages | **HIGH** |
| No parent-child keyword propagation | Filter Bubble problem | **HIGH** |
| search_document_chunks lacks tsv/trigram indexes | No FTS/trigram on chunks | **MEDIUM** |

### 3.2 Detailed Gap Analysis

#### Gap 1: Document Content in search_index

**Current State:**
- `search_index.search_text` for documents = filename only (~48 chars)
- No document content propagated to search surface

**Required State:**
- `search_index.search_text` should include:
  - Filename
  - Document title (from metadata)
  - Top 50-100 TF-IDF keywords from all chunks
  - System tags

**Impact:**
- Without content keywords, document-level search fails for content queries
- "3512C valve lash" won't find "Caterpillar Maintenance Manual"

#### Gap 2: Chunk Coverage

**Current State:**
- 963 active documents in doc_metadata
- Only 6 documents have chunks in search_document_chunks
- 0.6% coverage

**Required State:**
- 100% of active documents should be chunked
- Backfill job needed for existing documents

**Impact:**
- 99.4% of documents have no searchable content
- RAG cannot provide grounded answers from most documents

#### Gap 3: Chunk-Level Search

**Current State:**
- `hyper_search_multi` searches `search_index` only
- No RPC for searching `search_document_chunks`

**Required State:**
- `hyper_search_chunks_for_docs` RPC for chunk-level search
- Constrained by doc_ids from stage 1

**Impact:**
- Cannot retrieve specific passages for grounding
- Cannot provide citations with offsets

#### Gap 4: Chunk Index Structure

**Current State (`search_document_chunks`):**
- Has: embedding (vector), content (text), metadata (jsonb)
- Missing: tsv (tsvector), trigram index

**Required State:**
- Add `tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`
- Add GIN index on tsv
- Add trigram index on content (or create search_text column)

---

## 4. Table Relationships

```
                            ┌─────────────────────┐
                            │    doc_metadata     │
                            │   (1,000 records)   │
                            │   Source of truth   │
                            └──────────┬──────────┘
                                       │
                                       │ 1:1 (should exist)
                                       │ Currently: 291/963
                                       ▼
┌─────────────────────┐         ┌─────────────────────┐
│   search_index      │◄────────│    documents        │
│   (1,000 records)   │         │   (legacy table)    │
│   709 parts         │         │   May be deprecated │
│   291 documents     │         └─────────────────────┘
└─────────────────────┘
         │
         │ object_type='document'
         │ object_id = document_id
         │
         │ CURRENTLY: No FK, no content
         │
         ▼
┌─────────────────────────────────┐
│   search_document_chunks        │
│   (1,000 records from 6 docs)   │
│   document_id → doc_metadata.id │
│   HAS content + embeddings      │
└─────────────────────────────────┘
```

---

## 5. Recommendations

### 5.1 Immediate Actions (Before RAG Implementation)

1. **Backfill Chunks**: Run chunking pipeline on all 963 active documents
2. **Update search_index Documents**: Propagate TF-IDF keywords from chunks to parent
3. **Add Indexes**: Create tsv/trigram indexes on search_document_chunks

### 5.2 Schema Changes Required

1. **search_document_chunks** - Add columns:
   ```sql
   search_text     TEXT GENERATED (copy of content for trigram)
   tsv             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
   global_offset   INT (for PDF highlighting)
   ```

2. **search_index** - For documents:
   - Update `search_text` to include content keywords
   - Add trigger to refresh on chunk changes

### 5.3 New RPCs Required

1. **hyper_search_chunks_for_docs** - Chunk-level hybrid search constrained to doc_ids
2. **update_document_keywords** - Propagate TF-IDF keywords from chunks to parent

---

## 6. Data Quality Metrics

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Documents in doc_metadata | 963 active | 963 | 0% |
| Documents in search_index | 291 | 963 | 70% gap |
| Documents chunked | 6 | 963 | 99.4% gap |
| Chunk embedding coverage | 100% | 100% | 0% |
| Document keyword propagation | 0% | 100% | 100% gap |
| Chunk tsv/trigram indexes | 0% | 100% | 100% gap |

---

## Appendix A: Sample Data

### A.1 doc_metadata Sample
```json
{
  "id": "9c16cf55-e5f8-449b-b86f-08658e2914b5",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "source": "document_lens",
  "filename": "staging-doc-1769657455.pdf",
  "content_type": "application/pdf",
  "storage_path": "85fe1119-b04c-41ac-80f1-829d23322598/documents/...",
  "indexed": false,
  "tags": ["ci", "engine", "test"]
}
```

### A.2 search_document_chunks Sample
```json
{
  "id": "29e30038-2515-4f0e-a288-9ab07f61e9e0",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "document_id": "98825878-d5bd-4415-996b-0627bf0b44f4",
  "chunk_index": 0,
  "content": "FM 55-509-1\ncircuit current, the bimetallic element does not bend...",
  "embedding": "[0.00430319, 0.003501455, ...]",
  "metadata": {
    "loc": {"lines": {"to": 9164, "from": 9144}},
    "line": 14,
    "source": "blob"
  }
}
```

### A.3 search_index Document Sample
```json
{
  "object_type": "document",
  "object_id": "50113c1e-3cd1-426a-bba7-b9dae79f206e",
  "search_text": "test.pdf    ",  // ← ONLY FILENAME
  "payload": {
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "storage_path": "..."
  }
}
```

---

## Appendix B: Existing Services

| Service | URL | Purpose |
|---------|-----|---------|
| celeste-digest-index | digest-local.int.celeste7.ai | Document ingestion/indexing |
| celeste-file-type | celeste-file-type.onrender.com | PDF/doc text extraction |
| pipeline-core | pipeline-core.int.celeste7.ai | F1 Search API |

---

*End of Document*
