# Production SQL Execution Path Decision

**Date:** 2025-12-26
**Decision:** RENDER PATH (Supabase RPC)
**Status:** RECOMMENDED

---

## Executive Summary

After analyzing both execution paths, **Render/FastAPI with Supabase RPC is recommended as the production default**. The n8n workflow becomes an optional offline/batch processing path.

---

## Path Comparison

### Path A: Render `/v2/search` via Supabase RPC

```
Frontend → POST /v2/search (Render FastAPI)
         → graphrag_query.query()
         → GPT extraction + embedding
         → Supabase RPC: match_documents()
         → Entity resolution via Supabase tables
         → Build cards
         → Return results
```

**SQL Execution:** Supabase RPC function (`match_documents()`) + direct table queries

### Path B: n8n Workflow via Postgres Nodes

```
Trigger → Lane Switch → Table Router
       → Wave 1/2/3 Postgres nodes (parallel SQL)
       → Merge → Scoring Fusion → Format Response
```

**SQL Execution:** n8n Postgres nodes with parameterized queries

---

## Evaluation Criteria

| Criterion | Render Path | n8n Path | Winner |
|-----------|-------------|----------|--------|
| **Maintainability** | Requires deploy for changes | Visual, no-deploy changes | n8n |
| **Performance/Latency** | Single-hop, connection pooling | Multi-hop, node overhead | Render |
| **Observability** | Logs + APM | Visual workflow, execution history | Tie |
| **Failure Modes** | Supabase handles retries | Manual retry config per node | Render |
| **Security** | Supabase RLS + JWT | DB creds in n8n config | Render |
| **Concurrency** | Async Python, handles well | Workflow concurrency limits | Render |
| **Cost** | Supabase included | n8n Pro for production ($) | Render |
| **Streaming** | Native FastAPI support | Harder to implement | Render |
| **Current Status** | Working, tested | Exists, not wired | Render |

**Score: Render 6, n8n 1, Tie 1**

---

## Recommendation: RENDER PATH

### Why Render Wins

1. **Already Working:** The Supabase RPC path via `/v2/search` is functional and tested.

2. **Fewer Moving Parts:**
   - One service (Render) vs two (Render + n8n)
   - One auth flow vs coordinating JWT across services
   - Single point of monitoring

3. **Better Security Model:**
   - Supabase RLS enforces yacht_id scoping at DB level
   - JWT validated once in FastAPI
   - No DB credentials stored in n8n config files

4. **Superior Concurrency:**
   - FastAPI async handles concurrent requests natively
   - Supabase connection pooling via Supavisor
   - n8n has workflow execution limits

5. **Simpler Failure Handling:**
   - Supabase retries internally
   - Single error boundary in Python
   - Clear HTTP status codes to frontend

6. **Cost Effective:**
   - Supabase included in existing plan
   - No n8n Pro license needed for production

### When to Use n8n

The n8n workflow `lane_aware_sql_workflow.json` becomes:

1. **Offline batch processing** - Processing large document sets
2. **Development/testing** - Quick iteration on wave/scoring logic
3. **Future migration path** - If complexity grows, can migrate later
4. **Admin tools** - Manual data operations by ops team

---

## Implementation

### Current State (Already Working)

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION PATH                           │
│                                                              │
│  Frontend                                                    │
│     │                                                        │
│     ▼                                                        │
│  POST /v2/search (Render FastAPI)                           │
│     │                                                        │
│     ├──► GPT-4o-mini: Entity extraction                     │
│     ├──► text-embedding-3-small: Query embedding            │
│     │                                                        │
│     ▼                                                        │
│  graphrag_query.query()                                      │
│     │                                                        │
│     ├──► Supabase RPC: match_documents()                    │
│     │    (pgvector cosine similarity, yacht_id scoped)      │
│     │                                                        │
│     ├──► Entity resolution via Supabase tables              │
│     │                                                        │
│     └──► Build cards + suggested actions                    │
│                                                              │
│  Returns: {situation, cards, recommended_actions, meta}     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              OFFLINE/BATCH PATH (Optional)                   │
│                                                              │
│  Admin/Ops Trigger                                           │
│     │                                                        │
│     ▼                                                        │
│  n8n Workflow: lane_aware_sql_workflow.json                 │
│     │                                                        │
│     ├──► Table Router (bias scoring)                        │
│     ├──► Wave 1/2/3 Postgres nodes                          │
│     ├──► Scoring Fusion                                     │
│     └──► Format Response                                    │
│                                                              │
│  Use Cases: Batch processing, dev iteration, admin tools    │
└─────────────────────────────────────────────────────────────┘
```

### No Code Changes Required

The Render path is already the default. The n8n workflow exists but is not triggered by `/extract` or `/v2/search`. This is the correct architecture.

---

## Risk Mitigation

### If Render Path Has Issues

1. **Connection Pooling:** Supabase Supavisor handles pooling automatically
2. **Timeouts:** Add `statement_timeout` to long queries
3. **Rate Limiting:** Already in place (100 req/min per IP)

### If n8n Path Needed Later

1. **Add webhook endpoint** in FastAPI that triggers n8n
2. **Use n8n for specific use cases** (e.g., batch document reprocessing)
3. **Keep workflows in sync** via shared config files

---

## Answer to Explicit Question

**Where does SQL run in the final system?**

**Answer: Render/Supabase (via RPC)**

- `/v2/search` → `graphrag_query.query()` → `Supabase RPC: match_documents()` → pgvector similarity
- Entity resolution via `Supabase table queries`
- All SQL is yacht_id scoped via Supabase RLS

The n8n workflow is **not in the production hot path** - it's available for offline/batch use but doesn't serve user search requests.

---

## Diagram: Single Source of Truth

```
                    ┌─────────────────┐
                    │    Frontend     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  POST /v2/search │
                    │  (Render FastAPI)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ GPT-4o   │  │ Embed    │  │ Supabase │
        │ Extract  │  │ Query    │  │ RPC      │
        └──────────┘  └──────────┘  └────┬─────┘
                                         │
                                         ▼
                                 ┌───────────────┐
                                 │ match_documents│
                                 │ (pgvector SQL) │
                                 └───────────────┘
                                         │
                                         ▼
                                 ┌───────────────┐
                                 │ Build Cards   │
                                 │ + Actions     │
                                 └───────────────┘
                                         │
                                         ▼
                              { situation, cards,
                                recommended_actions }
```

**Single endpoint:** `POST /v2/search`
**Single SQL execution:** Supabase RPC
**Single auth:** JWT via Supabase
