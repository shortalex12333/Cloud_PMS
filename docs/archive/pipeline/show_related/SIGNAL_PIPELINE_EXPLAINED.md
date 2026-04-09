# Show Related Signal Pipeline — Complete Explanation

**Date:** 2026-03-20
**Audience:** Any engineer, zero prior knowledge required
**Status:** Working code, 500 error due to 3 root causes: missing index config, missing trigram index, broken fallback path

---

## What This Feature Does (Business Terms)

When a crew member opens any entity in CelesteOS — a work order, a piece of equipment, a fault report — the system can show them **other entities that are semantically related**, even across different categories. For example, opening a work order about an engine repair might surface:

- The engine manual (document)
- A previous fault report about the same engine (fault)
- Spare parts for that engine (parts)
- An email thread about the repair (email)

This is different from simple "linked items" (which are explicit database relationships). This feature uses **AI-powered semantic similarity** — it reads the entity's text, converts it to a mathematical vector, and finds other entities with similar vectors. It reuses the same search engine that powers the main spotlight search bar.

The feature appears as a **"Show Related" button** in the top-right of every entity detail page. Clicking it opens a right-side panel showing discovered related items, grouped by type.

---

## How It Works (Plain English, 7 Steps)

```
Step 1: USER clicks "Show Related" on a work order
            |
Step 2: FRONTEND sends request to backend API with JWT token
            |
Step 3: BACKEND verifies identity and yacht assignment
            |
Step 4: BACKEND reads the work order's attributes from the database
         and converts them to a text sentence:
         "Fix engine; status: open; priority: high; equipment: Main Engine"
            |
Step 5: BACKEND sends that sentence to OpenAI, which returns
         a 1536-number fingerprint (embedding) representing its meaning
            |
Step 6: BACKEND runs a database search function (f1_search_cards)
         that compares this fingerprint against all 12,730 indexed entities
         to find the most similar ones
            |
Step 7: BACKEND returns the top 10 results to the frontend,
         which displays them in a slide-out panel
```

---

## The Files Involved

### Frontend (What the user sees)

| File | Purpose | Status |
|------|---------|--------|
| `apps/web/src/components/lens/ShowRelatedButton.tsx` | The button in the top-right corner. Shows a network icon, a count badge, and a loading spinner. | Built, working |
| `apps/web/src/components/lens/RelatedDrawer.tsx` | The 480px slide-out panel on the right side. Groups results by type (equipment, faults, work orders, parts, manuals). | Built, working |
| `apps/web/src/components/lens/AddRelatedItemModal.tsx` | A modal for HOD/managers to manually link entities together. | Built, working |
| `apps/web/src/hooks/useSignalRelated.ts` | The data-fetching hook. Calls the backend API, manages loading/error states. Only fires for supported entity types. | Built, working |
| `apps/web/src/hooks/useRelated.ts` | Separate hook for FK-based related items (the non-AI path). Runs in parallel. | Built, working |
| `apps/web/src/hooks/useRelatedDrawer.ts` | UI state management — panel open/close, add modal open/close, permission checks. | Built, working |

### Backend — Route Layer (Where requests arrive)

| File | Purpose | Status |
|------|---------|--------|
| `apps/api/routes/show_related_signal_routes.py` | Defines `GET /v1/show-related-signal/`. Validates input, authenticates user, picks execution path (asyncpg or Supabase fallback). Also has a `/debug/status` health check. | Built, working |

### Backend — Handler Layer (Where the logic lives)

| File | Purpose | Status |
|------|---------|--------|
| `apps/api/handlers/show_related_signal_handlers.py` (660 lines) | **The brain.** Orchestrates the entire flow: serialize entity to text, generate embedding, call search, map results. Contains 12 entity-type serializers for the Supabase fallback path. | Built, 500 error on asyncpg path |
| `apps/api/handlers/related_handlers.py` (994 lines) | **Separate system.** FK-based related items (explicit database links, not AI). Runs in parallel. Not involved in the 500. | Built, working |

### Backend — Services Layer (Shared infrastructure)

| File | Purpose | Status |
|------|---------|--------|
| `apps/api/services/entity_serializer.py` (358 lines) | Converts any entity into a text sentence for embedding. Supports 14 entity types. Used by both the signal handler and the projection worker. | Built, working |
| `apps/api/services/hyper_search.py` (181 lines) | Manages the PostgreSQL connection pool and calls the `f1_search_cards` database function. Sets statement timeout to 3000ms. | Built, **this is where the timeout originates** |
| `apps/api/cortex/rewrites.py` (621 lines) | Generates embeddings via OpenAI API (`text-embedding-3-small`). Caches results in Redis (30-min TTL). Handles budget/timeout management. | Built, working |
| `apps/api/middleware/auth.py` (801 lines) | JWT validation, tenant lookup, role verification. Caches lookups for 15 minutes. | Built, working |
| `apps/api/integrations/supabase.py` (639 lines) | Creates Supabase HTTP clients for the fallback path. | Built, working |

### Tests

| File | Lines | What it tests |
|------|-------|---------------|
| `e2e/shard-33-lens-actions/show-related.spec.ts` | 120 | Button visibility, panel open/close, group rendering |
| `e2e/shard-34-lens-actions/show-related-signal.spec.ts` | 534 | Signal endpoint response shape, self-exclusion, cross-domain results |
| `e2e/shard-34-lens-actions/show-related-signal-ui.spec.ts` | 581 | "Also Related" section rendering, pagination |
| `e2e/shard-34-lens-actions/show-related-link-creation.spec.ts` | 339 | HOD manual link creation workflow |
| `apps/api/tests/test_related_handlers.py` | 518 | FK traversal logic, role-based access |
| `apps/api/tests/test_show_related_entity_serializer.py` | 375 | Entity serialization and embedding mock tests |
| `apps/web/src/components/lens/__tests__/RelatedDrawer.test.tsx` | — | Component unit tests |

### Documentation

| File | Description |
|------|-------------|
| `docs/SHOW_RELATED/summary.md` | Executive summary (partially outdated — written before signal layer existed) |
| `docs/SHOW_RELATED_FRONTEND.md` | 837-line frontend implementation spec |
| `docs/SHOW_RELATED_BACKEND.md` | 548-line backend spec with 8 known gaps |
| `docs/SHOW_RELATED/SIGNAL_PIPELINE_EXPLAINED.md` | **This file** |

---

## The Two Parallel Systems

CelesteOS has **two independent systems** for finding related entities. Both run when the user clicks "Show Related":

| System | Endpoint | How it finds relationships | Speed | Quality |
|--------|----------|---------------------------|-------|---------|
| **FK-based** (V1) | `GET /v1/related` | Follows database foreign keys (work order → equipment → faults) | Fast (<200ms) | High precision, low recall — only finds things explicitly linked |
| **Signal-based** (V1.5) | `GET /v1/show-related-signal` | AI semantic similarity — same engine as spotlight search | Slower (1.5–5s) | Lower precision, high recall — finds things that are conceptually related |

The frontend merges both result sets. Items found by both systems get "signal" added to their `match_reasons`. Items found only by the signal system appear in a separate "Also Related" section.

---

## The Request Journey (Technical Detail)

### 1. Authentication (`middleware/auth.py`)

```
Frontend sends: Authorization: Bearer <JWT>
    |
Backend decodes JWT using MASTER Supabase secret
    |
Extracts user_id from JWT
    |
Queries MASTER DB: user_accounts → gets yacht_id
    |
Queries MASTER DB: fleet_registry → gets tenant_key_alias (e.g. "yTEST_YACHT_001")
    |
Queries TENANT DB: auth_users_roles → gets role (captain, engineer, crew)
    |
Returns: { user_id, yacht_id, role, tenant_key_alias, email }
```

Cached for 15 minutes per user. After warmup, ~95% of requests hit cache.

### 2. Entity Serialization (`services/entity_serializer.py`)

Each entity type has its own serializer that reads specific columns and produces a text sentence:

| Entity Type | Database Table | Serialized Output Example |
|-------------|---------------|--------------------------|
| work_order | pms_work_orders | `"Fix engine; status: open; priority: high; equipment: Main Engine"` |
| equipment | pms_equipment | `"Main Engine; manufacturer: Caterpillar; model: 3512C; location: Engine Room"` |
| fault | pms_faults | `"Engine overheating; severity: high; equipment: Main Engine"` |
| part | pms_parts | `"Fuel filter; part_number: CAT-1234; category: consumables"` |
| manual | doc_metadata | `"C32 Engine Manual; doc_type: manual; equipment: Main Engine"` |
| email | email_messages | `"Engine maintenance request; from: Chief Engineer; folder: Inbox"` |
| certificate | pms_vessel_certificates | `"Class Certificate; type: DNV; authority: DNV GL; status: active"` |
| receiving | pms_receiving | `"Receiving from Caterpillar; ref: ORD-9876; status: pending"` |
| shopping_item | pms_shopping_list_items | `"Fuel filter; urgency: high; status: pending"` |
| handover | handover_exports | `"Night Shift Handover; [content preview]"` |
| handover_item | handover_items | `"Check engine oil; section: engines; category: preventive"` |

### 3. Embedding Generation (`cortex/rewrites.py`)

```
Serialized text: "Fix engine; status: open; equipment: Main Engine"
    |
Check Redis cache (key = sha256 of text)
    |
Cache hit? → Return cached 1536-number vector
Cache miss? → Call OpenAI text-embedding-3-small API
    |
Returns: [0.0234, -0.0891, 0.0456, ... ] (1536 floating-point numbers)
    |
Cache the result for 30 minutes
```

Budget: 8000ms for signal search (generous — panel opens on demand, not time-critical).

### 4. Database Search (`services/hyper_search.py` → `f1_search_cards` RPC)

```
Input:
  - Text array: ["Fix engine; status: open; equipment: Main Engine"]
  - Embedding array: [[0.0234, -0.0891, ...]]  (or NULL if embedding failed)
  - yacht_id: "85fe1119-..."  (tenant isolation)
  - org_id: "85fe1119-..."
  - rrf_k: 60 (fusion constant)
  - page_limit: 10
  - trgm_limit: 0.15 (trigram similarity threshold)

f1_search_cards runs THREE searches simultaneously:
  1. Vector ANN search (pgvector) — finds entities with similar embeddings
  2. Full-text search (tsvector) — finds entities with matching keywords
  3. Trigram search (pg_trgm) — finds entities with similar character patterns

Results are fused using Reciprocal Rank Fusion (RRF):
  fused_score = sum(1 / (k + rank_in_each_search))

Output: Top 10 results ranked by fused_score
```

### 5. Result Mapping (`handlers/show_related_signal_handlers.py`)

Each raw database result is mapped to a display-ready format:

```json
{
  "entity_id": "uuid",
  "entity_type": "manual",
  "title": "C18 Engine Manual",
  "subtitle": "manual",
  "match_reasons": ["signal:entity_embedding"],
  "fused_score": 0.72,
  "weight": 50,
  "open_action": "focus"
}
```

Title extraction is type-aware (work orders use `label` field, equipment uses `name`, emails use `subject`, etc.).

### 6. Final Response

```json
{
  "status": "success",
  "entity_type": "work_order",
  "entity_id": "339b1fbc-...",
  "entity_text": "Fix engine; status: open; equipment: Main Engine",
  "items": [ ... ],
  "count": 7,
  "signal_source": "entity_embedding",
  "metadata": {
    "limit": 10,
    "embedding_generated": true
  }
}
```

---

## The Two Execution Paths

The signal handler has a **preferred path** and a **fallback path**:

```
Does READ_DB_DSN exist?
    |
    YES → asyncpg path (direct PostgreSQL)
    |      - Faster (connection pooling)
    |      - Supports vector search (pgvector ANN)
    |      - Statement timeout: 3000ms
    |      - THIS IS WHERE THE 500 OCCURS
    |
    NO → Supabase HTTP fallback
           - Slower (HTTP overhead)
           - Text-only search (no vectors — avoids timeout)
           - HTTP timeout: 30s
           - Works in all environments
```

The Supabase fallback deliberately skips vector search because the REST/PostgREST path cannot set `statement_timeout` per-request, and vector searches with pgvector can take 10-15 seconds on cold start.

**Critical design flaw:** The fallback only triggers when `READ_DB_DSN` is missing (`ValueError`). When the asyncpg path **times out** (the actual failure mode), it throws `QueryCanceledError` which hits the generic `except Exception` handler at line 157 and returns a 500. The Supabase text-only path — which exists and works — is never reached on the real failure. The "graceful degradation" described in the architecture does not actually happen.

---

## The Current Problem — Three Root Causes

**Visible symptom:** `500 Internal Server Error` with `canceling statement due to statement timeout`

**What happens:**
1. User clicks "Show Related" on a work order
2. Authentication succeeds (captain role confirmed)
3. Entity serialized to text successfully
4. Embedding generated successfully (Redis cache hit)
5. `call_hyper_search()` calls `f1_search_cards` via asyncpg
6. The database query exceeds the **3000ms safety timer**
7. PostgreSQL kills the query
8. Backend returns 500 (fallback path is not reached — see design flaw above)

### Root Cause 1: Vector index searches 1% of the data (the primary cause)

The vector similarity index (`IVFFlat`) divides all 12,730 entity embeddings into 100 clusters. At query time, it needs to know **how many clusters to search**. This is controlled by the `ivfflat.probes` setting.

**This setting was never configured.** It defaults to 1.

With `probes = 1`, the database searches a single cluster (~127 entities out of 12,730). If the best match isn't in that one cluster, PostgreSQL abandons the index entirely and falls back to scanning **every row sequentially**. A sequential scan of 12,730 rows of 1536-dimensional vectors takes several seconds.

**Where:** `apps/api/services/hyper_search.py`, lines 48-54. The connection initialiser sets `statement_timeout` but never sets `ivfflat.probes`.

**Fix:** Add `SET ivfflat.probes = 10` to the connection initialiser. This searches 10 clusters (~1,270 entities) — still fast, but 10x more likely to find a good match without falling back to sequential scan.

### Root Cause 2: Trigram index was never created (hidden second bottleneck)

The `f1_search_cards` RPC runs three search methods. One of them — trigram matching — uses the `%` operator to compare the query text against the `search_text` column. This operator requires a **GiST index** on `search_text` to be fast.

**This index was commented out in the migration file.** Line 306-307 of `database/migrations/40_create_f1_search_cards.sql` has the `CREATE INDEX` statement commented out.

Without this index, every trigram search does a **sequential scan** of 12,730 rows of serialised text. This is a hidden cost that compounds with Root Cause 1 — even after fixing probes, trigram search will still be slower than it should be.

**Where:** `database/migrations/40_create_f1_search_cards.sql`, lines 306-307.

**Fix:** Uncomment and apply the GiST index on `search_text`.

### Root Cause 3: Timeout doesn't trigger the fallback path (design flaw)

The code at `show_related_signal_routes.py:122-159` has a fallback to Supabase text-only search. But this fallback only activates when `READ_DB_DSN` is missing (a `ValueError`). When the query **times out** — which is the actual failure — it throws `asyncpg.exceptions.QueryCanceledError`, which falls through to the generic `except Exception` at line 157 and returns a 500.

The Supabase text-only path exists, works, and would return results. It is simply never reached on the real failure mode.

**Where:** `apps/api/routes/show_related_signal_routes.py`, lines 122-159.

**Fix:** Catch `QueryCanceledError` (and other transient database errors) and retry via the Supabase text-only fallback before returning 500.

---

## Under-Optimised (4 items)

These are not broken, but they make the system slower than necessary:

| Issue | Current | Optimal | Impact | Where |
|-------|---------|---------|--------|-------|
| Signal pool keeps 1 warm connection | `min_size=1` | `min_size=2` | First query after restart pays ~200-500ms connection cost on top of cold-cache cost | `hyper_search.py:69` |
| Per-signal candidate LIMIT is 100 x 3 | `LIMIT 100` per search method = 300 candidates | `LIMIT 30` = 90 candidates | 70% less work for the ranking step, and we only return 10 results | `40_create_f1_search_cards.sql` (hardcoded in SQL) |
| No result cache for signal path | Every panel open runs the full pipeline | Cache for 120s (same as spotlight) | Repeated opens of the same entity re-run embedding + RPC unnecessarily | Not implemented |
| Port 6543 (Supavisor pooler) forced | All signal connections route through pooler | Use port 5432 (direct) for signal | Pooler overhead exists to protect against SSE streaming exhaustion, but signal is one-shot request/response — doesn't need pooler protection | `hyper_search.py:43` |

---

## Dials vs Outputs — A Key Distinction

Query latency (the time a search takes) is an **output** — a measurement of our process, not a dial we can tune to optimise.

The **safety timer** (`statement_timeout = 3000ms`) is a guard rail. Raising it from 3s to 10s would let the query eventually complete, but the query would still take 5-8 seconds. That is unacceptable for a UI interaction. Raising the timeout masks the problem. Lowering it reveals it sooner.

The **actual dials** that determine how fast or slow the query runs are:

| Dial | Controls | Current Value | Where |
|------|----------|---------------|-------|
| `ivfflat.probes` | How many index clusters to search | 1 (default, never set) | Connection init |
| `ivfflat.lists` | How many clusters the index is divided into | 100 | Index DDL |
| GiST index on `search_text` | Whether trigram search uses an index or sequential scan | Missing (commented out) | Migration SQL |
| Per-signal LIMIT | How many candidates each search method fetches before ranking | 100 | RPC function SQL |
| Pool `min_size` | How many connections are pre-warmed | 1 | `hyper_search.py` |
| Connection routing (port) | Whether queries go through pooler or direct | 6543 (pooler) | `hyper_search.py` |
| Embedding dimension | Size of vectors being compared | 1536 (fixed by model) | OpenAI model choice |

Time is the **result** of these settings. Fix the settings, and the time fixes itself.

---

## Timeout Strategy (Safety Rails Only)

These are guard rails, not performance controls. They exist to kill runaway queries, not to make queries faster.

| Layer | Timeout | Set Where | Purpose |
|-------|---------|-----------|---------|
| OpenAI embedding | 8000ms | `show_related_signal_handlers.py:101` | Kill slow AI API calls |
| PostgreSQL statement | 3000ms | `hyper_search.py:50` | Kill slow DB queries |
| asyncpg command | 5000ms | `hyper_search.py:68` | Kill stuck connections |
| Supabase HTTP (fallback) | 30000ms | `show_related_signal_handlers.py:539` | Kill stuck REST calls |

---

## Security Model

| Protection | How | Where |
|------------|-----|-------|
| User identity | JWT verified using master Supabase secret | `auth.py` |
| Yacht isolation | `yacht_id` passed to `f1_search_cards` RPC — results scoped to one vessel | `hyper_search.py:159` |
| Organization isolation | `org_id` passed to RPC — enforced by RLS policies | `hyper_search.py:158` |
| Role verification | Tenant DB queried for active role assignment | `auth.py:343-360` |
| Self-link prevention | Source entity excluded from search results | `hyper_search.py:169-171` |
| Data leak prevention | NULL `yacht_id` rejected with 403 (would return all vessels) | `show_related_signal_handlers.py:83-87` |

---

## Naming Convention Assessment

| Layer | Convention | Quality | Examples |
|-------|-----------|---------|----------|
| React components | PascalCase | Excellent | `ShowRelatedButton`, `RelatedDrawer`, `AddRelatedItemModal` |
| React hooks | camelCase with `use` prefix | Excellent | `useRelated`, `useRelatedDrawer`, `useSignalRelated` |
| API endpoints | kebab-case | Excellent | `/v1/related`, `/v1/show-related-signal` |
| Python handlers | snake_case | Excellent | `related_handlers.py`, `show_related_signal_handlers.py` |
| Test files | Descriptive shard naming | Excellent | `shard-34-lens-actions/show-related-signal.spec.ts` |
| Legacy code | Vague | Poor | `related_expansion.py` (marked "do not use") |

---

## What Remains To Be Done

### Must fix (3 items — the query will not work without these):

1. **Set `ivfflat.probes = 10`** — Add one line to `hyper_search.py:48-54` connection init. This is the primary cause of the timeout. Without it, the vector index is effectively unused.
2. **Create the trigram GiST index** — Uncomment lines 306-307 in `40_create_f1_search_cards.sql` and apply to the database. Without it, trigram search does a sequential scan on 12,730 rows.
3. **Fix the fallback path** — Catch `QueryCanceledError` in `show_related_signal_routes.py:122-159` and retry via Supabase text-only search instead of returning 500. The fallback code exists and works — it just isn't reached on the actual failure mode.

### Should optimise (4 items — the query will work but slower than necessary):

4. **Increase signal pool `min_size` from 1 to 2** — Avoids cold-connection cost on first query after restart.
5. **Reduce per-signal LIMIT from 100 to 30** — 300 candidates to rank for 10 results is excessive. 90 candidates is sufficient.
6. **Add result cache for signal path** — Spotlight caches for 120s. Signal runs the full pipeline every time.
7. **Use direct PostgreSQL (port 5432) instead of Supavisor pooler (6543)** — Pooler overhead is for SSE streaming protection. Signal is one-shot request/response.

### Housekeeping:

8. **Update `docs/SHOW_RELATED/summary.md`** — Currently outdated; doesn't mention the signal layer.
9. **Archive legacy code** — `context_nav/related_expansion.py` is dead code, should be moved to `docs/archive/`.
