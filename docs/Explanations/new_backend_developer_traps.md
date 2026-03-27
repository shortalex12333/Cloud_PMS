# New Backend Developer: Things That Will Bite You

> **Purpose:** Real traps, real files, real consequences. Everything here has caused actual bugs, wasted sessions, or near-production incidents in this codebase. Read before writing code.

---

## 1. "Healthy" Does Not Mean "Working"

**The trap:** Docker says all containers are "healthy" with green status. You assume everything works.

**The reality:** Docker healthcheck only proves the process is alive. It does NOT prove the worker is processing data, connecting to the database, or doing its job.

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
```

This checks if the HTTP server responds. It does not check if the database connection works, if the OpenAI API key is valid, or if Redis is reachable.

**What you must do instead:**
```bash
docker logs cloud_pms-projection-worker-1 --tail 20
docker logs cloud_pms-embedding-worker-1 --tail 20
docker logs cloud_pms-cache-listener-1 --tail 20
docker logs cloud_pms-email-watcher-1 --tail 20
```

Read the actual logs. Every time. "Healthy" is a lie.

---

## 2. Two Supabase Projects — You WILL Query the Wrong One

**The trap:** You see `SUPABASE_URL` in `.env` and start querying it. Your queries return empty results or hit the wrong tables.

**The reality:** There are TWO Supabase projects with completely different purposes:

| Project | URL contains | Purpose | What's in it |
|---------|-------------|---------|-------------|
| **Master** | `qvzmkaamzaqxpzbewjxe` | Auth & fleet registry ONLY | User login, yacht routing, subscription status |
| **Tenant** | `vzsohavtuotocgrfkfyd` | ALL PMS data | Work orders, faults, equipment, parts, certificates, everything |

**File:** `apps/api/middleware/auth.py:80`
```python
MASTER_SUPABASE_URL = os.getenv('MASTER_SUPABASE_URL', 'https://qvzmkaamzaqxpzbewjxe.supabase.co')
```

**The mistake:** A developer writes a handler that queries `SUPABASE_URL` (which defaults to tenant) for user auth data. Auth data is on Master. Empty result. Silent failure. Action returns 500.

**Rule:** Auth/login → Master. Everything else → Tenant. Check which client you're using.

---

## 3. The `source_version` Guard — Silent Data Loss

**The trap:** You run the projection worker, it processes items, marks them "done" — but nothing appears in `search_index`.

**The reality:** The upsert has a WHERE clause that silently rejects writes:

**File:** `apps/api/workers/projection_worker.py:606`
```sql
ON CONFLICT (object_type, object_id)
DO UPDATE SET ...
WHERE search_index.source_version < EXCLUDED.source_version
```

If the existing row has `source_version = 5` and you write `source_version = 5` (same version), the WHERE clause evaluates to `5 < 5` = false. **The upsert silently does nothing.** The worker marks the item as processed anyway.

**How you hit this:** Re-running the projection worker after a crash, or manually re-processing items. The worker thinks it succeeded. The data never updated.

**Fix:** Increment `source_version` before re-processing, or delete the existing row first.

---

## 4. Column Ownership — Workers Must Not Cross Lanes

**The trap:** You're fixing the projection worker and decide to also update `embedding_1536` while you're at it, since you already have the row.

**The reality:** Each worker owns specific columns. Writing to another worker's column causes race conditions and data corruption.

| Worker | Owns these columns | Must NEVER write |
|--------|-------------------|-----------------|
| projection-worker | `search_text`, `filters`, `payload` | `embedding_1536`, `learned_keywords` |
| embedding-worker | `embedding_1536`, `embedding_hash` | `search_text`, `filters` |
| nightly-feedback | `learned_keywords`, `learned_at` | Everything else |

**File:** `apps/api/workers/projection_worker.py:579` (comment documents this)

**Why it matters:** Workers run concurrently. If projection-worker writes `embedding_1536 = NULL` while embedding-worker is computing the new embedding, the embedding gets overwritten with NULL. Search breaks. No error logged.

---

## 5. Role Capitalization — The Silent 403

**The trap:** You register a new action with `allowed_roles=["Engineer", "Captain"]`. It works in your test. Production users get 403 Forbidden.

**The reality:** Roles in the auth system are **lowercase**. Roles in the registry must match exactly.

**File:** `apps/api/action_router/registry.py:98`
```python
self.allowed_roles = allowed_roles or ["engineer", "eto", "chief_engineer", "captain", "manager"]
```

The auth middleware returns `role = "captain"` (lowercase). If your action has `"Captain"`, the string comparison fails silently. The user sees 403 with no explanation.

**Rule:** Always lowercase. Never capitalize roles. The default list in the registry is correct — follow its pattern.

---

## 6. Two Migration Directories — No Convention

**The trap:** You create a migration file. Where does it go?

**The reality:** There are two migration directories with different naming conventions and different purposes:

| Directory | Convention | Purpose |
|-----------|-----------|---------|
| `database/migrations/` | Numeric prefix (`00_`, `01_`, `02_`) | Core schema — fleet registry, auth, security |
| `supabase/migrations/` | Timestamp prefix (`20260313_001_`) | Operational — tenant features, RLS policies, triggers |

There is no documented rule for which directory to use. There are also **duplicate-numbered files** in `database/migrations/` (two `02_*` files, two `03_*` files). The numbering is not enforced.

**What you should do:** Ask before creating a migration. Check what already exists. If it's tenant PMS data (tables, RLS, triggers), use `supabase/migrations/` with timestamp format. If it's core auth/fleet infrastructure, use `database/migrations/` with numeric format.

---

## 7. Render Env Vars — `sync: false` Means Manual

**The trap:** You add a new env var to `render.yaml` and deploy. The service starts but crashes because the env var is empty.

**The reality:**

**File:** `render.yaml`
```yaml
- key: yTEST_YACHT_001_SUPABASE_URL
  sync: false
```

`sync: false` means **Render will NOT read this value from the YAML file**. You must set it manually in the Render dashboard. Every secret in this project has `sync: false`. None of them auto-deploy.

**What breaks:** `DATABASE_URL`, `OPENAI_API_KEY`, `REDIS_URL`, `SUPABASE_URL`, `JWT_SECRET` — all manual. Deploy without setting them → service starts → first request → crash.

---

## 8. The Handler Layer Confusion

**The trap:** You need to add a new action handler. You see `apps/api/handlers/equipment_handlers.py` and `apps/api/routes/handlers/equipment_handler.py`. You pick one at random.

**The reality:** These are TWO DIFFERENT LAYERS that work together:

```
routes/handlers/equipment_handler.py  →  Dispatch (thin function, maps action name to call)
handlers/equipment_handlers.py        →  Logic (stateful class, actual business implementation)
```

Dispatch calls Logic. Both are required. See `docs/Explanations/action_handler_tiers_P0_P3.md` for the full flow.

**The mistake:** Writing business logic in `routes/handlers/` (the dispatch layer). Or writing a dispatch function in `handlers/` (the logic layer). Each has a specific job.

**For new actions:** Write a dispatch function in `routes/handlers/*_handler.py`, add it to that file's `HANDLERS` dict. It will be included in the dispatch table automatically.

---

## 9. The Wrong Supabase Import (Frontend)

**The trap:** You need to call Supabase from a frontend component. You Google it and write:

```typescript
import { createClient } from '@/lib/supabase/server';  // WRONG
```

**The reality:** This path doesn't exist. The correct import:

```typescript
import { supabase } from '@/lib/supabaseClient';  // CORRECT
```

**File:** `apps/web/src/lib/supabaseClient.ts`

This has caused build failures in at least 3 previous sessions. The client is a Proxy-wrapped singleton that defers creation until first access (to avoid SSR issues).

---

## 10. Docker Desktop macOS — Network Throttling

**The trap:** You run the email-watcher or any worker that calls external APIs (Microsoft Graph, OpenAI) inside Docker. It hangs or times out intermittently.

**The reality:** Docker Desktop on macOS throttles outbound HTTPS connections. OAuth token refresh and file downloads to `graph.microsoft.com` fail silently or timeout after 30s.

**Rule:** Workers that call external APIs (email-watcher, embedding-worker with OpenAI) should be tested natively, not inside Docker, during development on macOS.

---

## 11. Tenant Isolation — LAW 8

**The trap:** You write a query that joins across all work orders to generate a report.

**The reality:** Every query MUST be scoped to a single `yacht_id`. There is no admin super-query. RLS enforces this at the database level, but if you bypass RLS (service role key), you can accidentally leak data across tenants.

**The law:** Workers never cross yacht boundaries. Handlers never cross yacht boundaries. If your query doesn't have `WHERE yacht_id = $1`, it's wrong.

---

## 12. The `entity_id` vs Domain-Specific ID Confusion

**The trap:** An action's `required_fields` includes `entity_id`. You pass the work order UUID as `entity_id`. The handler can't find it.

**The reality:** Some actions use generic `entity_id`, others use domain-specific IDs like `work_order_id`, `equipment_id`, `fault_id`. The naming is inconsistent across the 207 registered actions.

**File:** `apps/api/action_router/registry.py` — check `required_fields` for the exact field name the action expects.

**What to do:** Always read the action's `required_fields` list before calling it. Don't assume `entity_id` works everywhere.

---

## 13. The `internal_adapter.py` Bridge

**The trap:** You find an action in `internal_dispatcher.py` and try to call its handler directly. It fails with a different function signature.

**The reality:** 71 actions use the legacy calling convention (class-based handlers in P1/P2/P3). They're bridged to the Phase 4 convention by `routes/handlers/internal_adapter.py`. The adapter translates between:

```python
# Phase 4 convention (new):
async def handler(payload, context, yacht_id, user_id, user_context, db_client) -> dict

# Legacy convention (P1-P3):
async def handler_execute(self, action, context, payload) -> dict
```

**The mistake:** Calling a P2 handler directly with Phase 4 arguments. Or calling a Phase 4 handler with legacy arguments. The adapter exists for a reason — use the dispatch table, not direct calls.

---

## 14. Claiming Something Works When It Doesn't

**The most dangerous trap.** This has burned the project owner across 5+ sessions with previous developers/AI assistants.

Signs you're about to make this mistake:
- You say "it should work" without running it
- You say "tests pass" without actually running tests
- You say "deployed" without checking the deployment logs
- You say "fixed" without verifying the fix in a browser

**The rule:** Prove it. Run it. Screenshot it. If you can't prove it, say "I haven't verified this yet."

---

## Quick Reference: Files That Bite

| File | Trap |
|------|------|
| `workers/projection_worker.py:606` | source_version WHERE clause silently rejects writes |
| `middleware/auth.py:80` | Master vs Tenant Supabase — wrong one = empty results |
| `action_router/registry.py:98` | Role case sensitivity — "Captain" ≠ "captain" |
| `render.yaml` (any `sync: false`) | Env vars not auto-deployed — set manually in dashboard |
| `docker-compose.yml` healthcheck | "Healthy" only means process alive, not working |
| `routes/handlers/__init__.py` | Dispatch table — don't confuse with `handlers/` logic layer |
| `supabaseClient.ts` | Only correct Supabase import — `createClient` path doesn't exist |
| `database/migrations/` vs `supabase/migrations/` | Two dirs, no convention, duplicate numbering |
