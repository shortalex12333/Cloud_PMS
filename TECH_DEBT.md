# Tech Debt Register

Tracked items that need future attention. Each item includes context, risk, and recommended approach.

---

## TD-001: validate_jwt consolidation (hours_of_rest + part_routes)

**Files:** `routes/hours_of_rest_routes.py`, `routes/part_routes.py`, `action_router/validators/jwt_validator.py`
**Impact:** 21 endpoints across 2 route files
**Risk:** LOW (security is intact, fleet fan-out is limited)

**Problem:** These routes use `validate_jwt()` instead of `get_authenticated_user()`. The JWT validator does not query `fleet_vessel_ids` from `user_accounts`, so fleet users can only access their primary yacht through HoR and part endpoints.

**Why it matters:** All other routes use `get_authenticated_user()` which populates `vessel_ids` from `fleet_vessel_ids`. These two files are the only ones using the non-standard auth path.

**Fix:** Update `validate_jwt()` in `jwt_validator.py` to query `user_accounts.fleet_vessel_ids` and populate `vessel_ids` in the JWT context. Or migrate these routes to use `get_authenticated_user` + `resolve_yacht_id` like all other routes.

**Added:** 2026-04-08

---

## TD-002: Migration 30 — search queue consolidation

**File:** `database/migrations/30_consolidate_search_queues.sql`
**Impact:** search_index table (13,340 rows)
**Risk:** LOW (optimization, not a blocker)

**Problem:** ALTER TABLE on `search_index` is blocked by the embedding worker's `FOR UPDATE SKIP LOCKED` transactions. The migration adds 6 columns (embedding_priority, embedding_error, embedding_attempts, embedding_queued_at, embedding_started_at, embedding_completed_at) and a queue polling index.

**Why it matters:** Without these columns, the worker uses a separate polling pattern. The consolidation simplifies the embedding pipeline.

**Fix:** Apply during a maintenance window with the embedding worker paused. Steps:
1. Stop embedding-worker container
2. Run migration 30
3. Verify columns exist
4. Restart embedding-worker

**Added:** 2026-04-08

---

## TD-003: Render deployment configuration

**Files:** `render.yaml`, `render-combined.yaml`, `docker-compose.combined.yml`
**Impact:** Production deployment
**Risk:** MEDIUM (deployment strategy undecided)

**Problem:** Two competing Render configs exist:
- `render.yaml` — Multi-service ($56/month), 6 separate services
- `render-combined.yaml` + `docker-compose.combined.yml` — Unified free tier, single service

The unified service has timeout issues. Current staging runs on Docker locally.

**Decision needed:** Which deployment strategy for production? Multi-service is more reliable but costs more. Unified is free but memory-constrained (512MB for all services).

**Added:** 2026-04-08

---

## TD-004: CI test user account cleanup

**Impact:** Master DB `user_accounts` table
**Risk:** LOW (no production impact, data hygiene)

**Problem:** 102 of 104 user accounts are CI test accounts (`captain.ci+*`, `crew.ci+*`, `hod.ci+*`). Only 2 are real: `x@alex-short.com` (captain) and `fleet-test-*@celeste7.ai` (manager).

**Fix:** Batch delete CI test accounts or move to a separate test tenant.

**Added:** 2026-04-08

---

## TD-005: supabase/ vs database/ migration sync

**Impact:** Database schema reproducibility
**Risk:** MEDIUM (can't rebuild tenant DB from database/migrations alone)

**Problem:** 14 migrations in `supabase/migrations/` have no equivalent in `database/migrations/`. These cover: receiving ledger triggers, yacht_id on work_order_notes, HoR constraints, crew RLS, work order status, worker locks, Microsoft auth tokens, cache invalidation, email features, soft delete, handover RLS, import sessions.

**Decision needed:** Which directory is authoritative? Consolidate into one system.

**Added:** 2026-04-08

---

## TD-006: Retire lens/ folder — migrate AddNoteModal and HistorySection to lens-v2

**Files:** `apps/web/src/components/lens/actions/AddNoteModal.tsx`, `apps/web/src/components/lens/sections/HistorySection.tsx`
**Impact:** Frontend component organisation
**Risk:** LOW (mechanical move, no logic change)

**Problem:** The `lens/` folder was the original entity lens system, superseded by `lens-v2/`. Dead code removal (2026-04-09) eliminated 18 files. Two remain:
- `lens/actions/AddNoteModal.tsx` — imported by `lens-v2/entity/WorkOrderContent.tsx`. Cross-namespace dependency. AddNoteModal belongs in `lens-v2/` alongside the component that uses it.
- `lens/sections/HistorySection.tsx` — imported by `lens/EntityLensPage.tsx`. Once moved to `lens-v2/sections/`, the `lens/sections/` folder can be deleted entirely.

Once both are migrated: `lens/actions/`, `lens/sections/`, and both index.ts stubs can be deleted, leaving only `EntityLensPage.tsx`, `RelatedDrawer.tsx`, and their test in `lens/`.

**Fix:**
1. Move `AddNoteModal.tsx` → `lens-v2/actions/AddNoteModal.tsx`, update import in WorkOrderContent
2. Move `HistorySection.tsx` → `lens-v2/sections/HistorySection.tsx`, update export in `lens-v2/sections/index.ts`, update import in EntityLensPage
3. Delete `lens/actions/` and `lens/sections/` folders

**Added:** 2026-04-09
