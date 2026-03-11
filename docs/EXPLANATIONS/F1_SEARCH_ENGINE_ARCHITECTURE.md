# F1 Cortex Search Engine - Definitive Architecture

> **Status**: GOSPEL - This document is the authoritative reference for the F1 Search Engine
> **Last Updated**: 2026-02-27
> **Maintainer**: Engineering Team

---

## Executive Summary

The F1 Search Engine is a hybrid search system that combines multiple retrieval strategies through Reciprocal Rank Fusion (RRF). It operates on a **two-layer architecture** that separates data preparation from query execution, enabling sub-200ms search latency across millions of indexed entities.

---

## 1. The Two-Layer Architecture

### The Critical Distinction

The F1 engine operates on **two completely separate lifecycles**:

| Layer | Type | Purpose | When It Runs |
|-------|------|---------|--------------|
| **Data Preparation** | Asynchronous | Keeps `search_index` hot and ready | 24/7 background daemons |
| **Query Execution** | Synchronous | Finds results in real-time | On every user keystroke |

**These are not the same thing.** Conflating them leads to architectural misunderstanding.

---

## 2. Data Preparation Layer ("The Factory Floor")

### 2.1 The Five Background Workers

These are **asynchronous daemons** that run 24/7, waking up when the database changes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATA PREPARATION LAYER (Async)                           │
│                         "The Factory Floor"                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Source Tables ──trigger──► Queue ──poll──► WORKERS                       │
│   (pms_*)                                                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Worker 1: DETECTIVE     │  Intent classification                  │  │
│   │  [celeste-backend inline]│  Classifies incoming entities           │  │
│   ├──────────────────────────┼──────────────────────────────────────────┤  │
│   │  Worker 2: SNIPER        │  Exact match preparation                │  │
│   │  [celeste-backend inline]│  Indexes deterministic lookups          │  │
│   ├──────────────────────────┼──────────────────────────────────────────┤  │
│   │  Worker 3: LIBRARIAN     │  BM25 full-text preparation             │  │
│   │  [database RPC]          │  match_link_targets_v2                  │  │
│   ├──────────────────────────┼──────────────────────────────────────────┤  │
│   │  Worker 4: PROJECTIONIST │  CDC projection to search_index         │  │
│   │  [projection-worker]     │  Watches source tables, updates index   │  │
│   ├──────────────────────────┼──────────────────────────────────────────┤  │
│   │  Worker 5: EMBEDDER      │  1536-dim vector generation             │  │
│   │  [embedding-worker]      │  OpenAI text-embedding-3-small          │  │
│   └──────────────────────────┴──────────────────────────────────────────┘  │
│                                                                             │
│   OUTPUT: Hot, ready search_index with:                                    │
│           • tsv (tsvector for BM25)                                        │
│           • embedding_1536 (semantic vector)                               │
│           • learned_keywords (yacht-specific vocabulary)                   │
│           • search_text (raw text for trigram)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Supporting Services

| Service | Render Deployment | Purpose |
|---------|-------------------|---------|
| **cache-invalidation-listener** | Background Worker | Listens to PostgreSQL NOTIFY, invalidates Redis cache on entity changes |
| **nightly-feedback-loop** | Cron Job (3 AM UTC) | Aggregates search clicks → learns yacht-specific vocabulary |

### 2.3 Worker File Locations

| Worker | File Path | Render Service |
|--------|-----------|----------------|
| Detective | `celeste-backend` inline | `srv-d5fr5hre5dus73d3gdn0` |
| Sniper | `celeste-backend` inline | `srv-d5fr5hre5dus73d3gdn0` |
| Librarian | Database RPC `match_link_targets_v2` | N/A (database) |
| Projectionist | `apps/api/workers/projection_worker.py` | `srv-d62i0fu3jp1c73bnul70` |
| Embedder | `apps/api/workers/embedding_worker_1536.py` | `srv-d61l5rfgi27c73cc36gg` |

---

## 3. Query Execution Layer ("The Racing Competition")

### 3.1 The Five Search Strategies

When a user types a query, these **synchronous execution paths** race in parallel:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    QUERY EXECUTION LAYER (Sync)                             │
│                      "The Racing Competition"                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Query ──► f1_search_cards() ──► 5 STRATEGIES (parallel)             │
│                                                                             │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐  │
│   │   TRIGRAM     │ │  TSV (BM25)   │ │    VECTOR     │ │    EXACT      │  │
│   │   pg_trgm     │ │   tsvector    │ │   pgvector    │ │   string =    │  │
│   │               │ │               │ │               │ │               │  │
│   │ Fuzzy match   │ │ Keyword match │ │ Semantic match│ │ Deterministic │  │
│   │ GiST index    │ │ GIN index     │ │ HNSW index    │ │ win condition │  │
│   │ ~0.15 thresh  │ │ ts_rank_cd    │ │ cosine dist   │ │               │  │
│   └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘  │
│           │                 │                 │                 │          │
│           └─────────────────┴─────────────────┴─────────────────┘          │
│                                       │                                     │
│                             ┌─────────▼─────────┐                          │
│   ┌───────────────┐         │   RRF FUSION      │                          │
│   │    CORTEX     │         │   K = 60          │                          │
│   │    Query      │────────►│                   │                          │
│   │    Rewrites   │         │ score = Σ 1/(60+r)│                          │
│   │               │         └─────────┬─────────┘                          │
│   │ 3 variations  │                   │                                     │
│   │ per query     │                   ▼                                     │
│   └───────────────┘           Ranked Results                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Strategy Details

| Strategy | Index | Threshold | What It Finds |
|----------|-------|-----------|---------------|
| **Trigram** | pg_trgm GiST | 0.07-0.15 dynamic | Typos, partial matches, fuzzy strings |
| **TSV (BM25)** | PostgreSQL GIN | ts_rank_cd | Keyword phrases, stemmed words |
| **Vector** | pgvector HNSW | cosine similarity | Semantic meaning, synonyms |
| **Exact** | Direct comparison | 100% match | Deterministic win (bypasses RRF) |
| **Cortex** | Query expansion | N/A | Generates 3 query variations |

### 3.3 Execution File Locations

| Component | File Path |
|-----------|-----------|
| F1 SSE Endpoint | `apps/api/routes/f1_search_streaming.py` |
| Cortex Rewrites | `apps/api/cortex/rewrites.py` |
| Hybrid Search RPC | `database/migrations/40_create_f1_search_cards.sql` |
| Vector Search RPC | `database/migrations/44_match_search_index_rpc.sql` |
| Frontend Hook | `apps/web/src/hooks/useCelesteSearch.ts` |

---

## 4. Cortex: The Pre-Processing Intelligence Layer

### 4.1 Scope of Cortex

**Cortex is not just `cortex/rewrites.py`** — it is the architectural term for the entire pre-processing intelligence layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CORTEX - Pre-Processing Intelligence                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   QUERY-TIME (cortex/rewrites.py)          LEARNING-TIME (nightly cron)    │
│   ┌─────────────────────────────┐          ┌─────────────────────────────┐ │
│   │ Stopword bypass             │          │ Click aggregation           │ │
│   │   "part" → "parts"          │          │   (yacht-isolated, LAW 8)   │ │
│   │                             │          │                             │ │
│   │ Abbreviation expansion      │          │ Vocabulary learning         │ │
│   │   "wo" → "work order"       │          │   "dirty water" + click     │ │
│   │                             │          │   "Bilge Pump" → inject     │ │
│   │ Embedding generation        │          │   into learned_keywords     │ │
│   │   query → 1536-dim vector   │          │                             │ │
│   └─────────────────────────────┘          │ Re-embedding trigger        │ │
│                                            │   content_hash change →     │ │
│                                            │   Worker 5 re-processes     │ │
│                                            └─────────────────────────────┘ │
│                                                                             │
│   THE FEEDBACK LOOP:                                                        │
│   User searches "dirty water" → Clicks "Bilge Pump" → Cortex learns →      │
│   Next search "dirty water" → Bilge Pump ranks higher                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Cortex Responsibilities

| Phase | Component | Responsibility |
|-------|-----------|----------------|
| Query-Time | `cortex/rewrites.py` | Stopword bypass, abbreviation expansion, embedding generation |
| Learning-Time | `nightly_feedback_loop.py` | Click aggregation, vocabulary injection, re-embedding triggers |
| Caching | Redis | 15-min TTL per query, tenant-isolated (org_id, yacht_id, role) |

---

## 5. Reciprocal Rank Fusion (RRF)

### 5.1 The Formula

```
RRF Score = Σ  1/(K + rank_i)  for each strategy i
```

Where:
- `K = 60` (the smoothing constant)
- `rank_i` = the position of the result in strategy i's ranking

### 5.2 Why K=60?

**K=60 is not arbitrary** — it is the mathematical gold standard from the original University of Waterloo paper.

The researchers tested K values from 1 to 100 across massive datasets and proved that K=60 provides the optimal balance:

| K Value | Problem |
|---------|---------|
| K=1-10 | Single exact keyword match dominates; vectors can't compete |
| K=100+ | All strategies converge to equal weight; loses signal |
| **K=60** | Sweet spot where semantic matches fairly compete with keyword matches |

### 5.3 Example Calculation

```
Query: "generator maintenance"

Strategy Rankings:
  Trigram: Generator-1 → rank 2
  TSV:     Generator-1 → rank 1
  Vector:  Generator-1 → rank 3

RRF Score for Generator-1:
  = 1/(60+2) + 1/(60+1) + 1/(60+3)
  = 1/62 + 1/61 + 1/63
  = 0.0161 + 0.0164 + 0.0159
  = 0.0484
```

---

## 6. Data Flow: Complete Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE F1 DATA FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [1] SOURCE TABLES                                                         │
│       pms_equipment, pms_work_orders, pms_faults, pms_parts, ...           │
│              │                                                              │
│              │ (triggers on INSERT/UPDATE)                                  │
│              ▼                                                              │
│   [2] PROJECTION WORKER (Worker 4)                                          │
│       Polls queue, writes to search_index:                                  │
│       - object_type, object_id                                              │
│       - search_text (denormalized for display)                              │
│       - payload (JSONB for UI)                                              │
│              │                                                              │
│              ▼                                                              │
│   [3] EMBEDDING WORKER (Worker 5)                                           │
│       Claims rows where embedding_1536 IS NULL:                             │
│       - Generates 1536-dim OpenAI vector                                    │
│       - Writes to search_index.embedding_1536                               │
│              │                                                              │
│              ▼                                                              │
│   [4] SEARCH_INDEX (hot and ready)                                          │
│       ┌─────────────────────────────────────────────────────────────────┐  │
│       │ object_type │ object_id │ search_text │ tsv │ embedding_1536 │  │  │
│       │ payload │ learned_keywords │ org_id │ yacht_id │              │  │  │
│       └─────────────────────────────────────────────────────────────────┘  │
│              │                                                              │
│              │ (user searches)                                              │
│              ▼                                                              │
│   [5] CORTEX REWRITES                                                       │
│       Input:  "generator maintenance"                                       │
│       Output: ["generator maintenance", "generators maintenance", ...]      │
│       + 1536-dim embeddings per rewrite                                     │
│              │                                                              │
│              ▼                                                              │
│   [6] f1_search_cards() RPC                                                 │
│       Executes 4 strategies in parallel:                                    │
│       - Trigram (pg_trgm GiST)                                              │
│       - TSV (tsvector GIN)                                                  │
│       - Vector (pgvector HNSW)                                              │
│       - Exact match                                                         │
│              │                                                              │
│              ▼                                                              │
│   [7] RRF FUSION (K=60)                                                     │
│       Combines ranks from all strategies                                    │
│       score = Σ 1/(60 + rank)                                               │
│              │                                                              │
│              ▼                                                              │
│   [8] SSE STREAM                                                            │
│       Events: diagnostics → result_batch → finalized                        │
│       L1 fast path: 150ms budget                                            │
│       L2 deep path: 800ms escalation if text results < 3                    │
│              │                                                              │
│              ▼                                                              │
│   [9] FRONTEND (useCelesteSearch.ts)                                        │
│       Parses SSE, renders in SpotlightSearch                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. LAW Compliance

| LAW | Requirement | Implementation |
|-----|-------------|----------------|
| **LAW 8** | Tenant isolation | `yacht_id` extracted from JWT server-side; never trusted from client |
| **LAW 9** | Learned keywords ownership | Only `nightly_feedback_loop` writes to `learned_keywords`; Worker 4 preserves |
| **LAW 19** | No hardcoded synonyms | Vectors handle semantics; no synonym dictionaries |
| **LAW 22** | No threshold amputation | RRF handles ranking; no arbitrary score cutoffs |
| **LAW 23** | Dynamic timeout escalation | L1: 150ms fast path; L2: 800ms if results < 3 |

---

## 8. File Reference

### 8.1 Backend (apps/api)

| Directory | Files | Purpose |
|-----------|-------|---------|
| `cortex/` | `rewrites.py` | Query rewriting, embedding generation |
| `routes/` | `f1_search_streaming.py` | SSE endpoint, RRF fusion |
| `workers/` | `projection_worker.py` | CDC → search_index |
| `workers/` | `embedding_worker_1536.py` | OpenAI vector generation |
| `workers/` | `nightly_feedback_loop.py` | Click aggregation, vocabulary learning |
| `cache/` | `invalidation_listener.py` | Redis cache coherence |
| `orchestration/` | `search_orchestrator.py` | Intent parsing, retrieval planning |

### 8.2 Database (database/migrations)

| File | Purpose |
|------|---------|
| `01_create_search_index.sql` | Core table schema |
| `40_create_f1_search_cards.sql` | Hybrid search RPC |
| `41_f1_search_deterministic_ordering.sql` | Tie-breaking |
| `42_counterfactual_feedback_loop.sql` | Click tracking |
| `44_match_search_index_rpc.sql` | Vector-only search |
| `45_f1_search_cards_with_search_text.sql` | Snippet generation |

### 8.3 Frontend (apps/web)

| File | Purpose |
|------|---------|
| `src/hooks/useCelesteSearch.ts` | SSE parsing, action intent detection |
| `src/components/spotlight/SpotlightSearch.tsx` | Result rendering |
| `src/components/spotlight/FilterChips.tsx` | Quick filter suggestions |
| `src/components/SuggestedActions.tsx` | Action button rendering |

---

## 9. Render Deployments

| Service | Render ID | Workers Included |
|---------|-----------|------------------|
| `celeste-backend` | `srv-d5fr5hre5dus73d3gdn0` | Workers 1-3 (Detective, Sniper, Librarian) |
| `projection-worker` | `srv-d62i0fu3jp1c73bnul70` | Worker 4 (Projectionist) |
| `embedding-worker` | `srv-d61l5rfgi27c73cc36gg` | Worker 5 (Embedder) |
| `cache-invalidation-listener` | `srv-d61l5a94tr6s73enf4gg` | Redis CDC sync |
| `nightly-feedback-loop` | (pending) | Counterfactual learning |

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Cortex** | The pre-processing intelligence layer (query rewrites + learning) |
| **RRF** | Reciprocal Rank Fusion — algorithm for combining multiple rankings |
| **K=60** | The smoothing constant in RRF, mathematically optimal |
| **search_index** | The hot, denormalized table for search queries |
| **Projection** | CDC-based copying from source tables to search_index |
| **Embedding** | 1536-dimensional vector representation of text |
| **L1/L2** | Timeout escalation levels (150ms fast, 800ms deep) |
| **learned_keywords** | Yacht-specific vocabulary from click feedback |

---

*This document is the authoritative reference for the F1 Search Engine architecture. All engineering decisions should align with the principles documented here.*
