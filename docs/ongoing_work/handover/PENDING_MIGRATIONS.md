# Handover domain — pending manual migrations

Per `feedback_migration_convention.md`: SQL migration files are temporary — apply to TENANT, verify, then delete from this doc.

**Target DB:** TENANT `vzsohavtuotocgrfkfyd`. Do **not** run against MASTER.

## HANDOVER08-M01 — drop orphaned `handover_draft_edits`

**Status:** pending CEO manual apply
**Evidence:**
- `SELECT count(*) FROM handover_draft_edits` → **0** (probe 2026-04-23)
- Code grep across `apps/api`, `apps/web`, `supabase/migrations` → **0** readers, **0** writers
- Table was provisioned but never wired. Snapshot-log design was left incomplete; the surviving write path uses `handover_entries` (7,270 rows) as the immutable audit layer.

**Pre-apply checks (re-run before DDL):**
```sql
SELECT count(*) FROM handover_draft_edits;             -- must still be 0
SELECT count(*) FROM pg_trigger t
  JOIN pg_class c ON c.oid = t.tgrelid
 WHERE c.relname = 'handover_draft_edits';             -- must be 0 (no triggers)
SELECT count(*) FROM information_schema.view_column_usage
 WHERE table_name = 'handover_draft_edits';            -- must be 0 (no views depend on it)
```

**DDL (run as service_role):**
```sql
BEGIN;
-- Drop RLS policies first so DROP TABLE doesn't error on policy dependencies.
DROP POLICY IF EXISTS handover_draft_edits_service_all ON handover_draft_edits;
DROP POLICY IF EXISTS handover_draft_edits_owner_read  ON handover_draft_edits;
-- (add any other policy names the probe surfaced.)

DROP TABLE IF EXISTS public.handover_draft_edits CASCADE;
COMMIT;
```

**Post-apply verify:**
```sql
SELECT to_regclass('public.handover_draft_edits');     -- must return NULL
```

**Rollback plan:** none needed — table was empty and unreferenced. If regret surfaces, re-create from original migration (check git log for the CREATE TABLE DDL).

---

## HANDOVER08-M02 — documented, NOT dropping

`handover_draft_sections` (274 rows) and `handover_draft_items` (7,235 rows) have **live data** from the microservice-snapshot write path (`handover_export_routes.py:270, 284`) but **0 readers** in current code. Do **not** drop.

**Action:** document in `docs/ongoing_work/handover/ARCHITECTURE.md` as *microservice-snapshot reserved — read path is a planned feature, do not repurpose, do not truncate.*

Documentation update will ship alongside the B10 doc pass.
