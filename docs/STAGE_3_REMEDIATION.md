# Stage 3 Remediation — Handoff Document

> **Date:** 2026-03-16
> **Test Run:** `/tmp/stage3-final.log`
> **Result:** 116 passed, 31 failed, 1 skipped (8.1m)
> **Shards:** 33–47 (15 total)

---

## Before You Touch Anything — Read This First

### Who We Are

**CelesteOS PMS** is maritime yacht-specific planned maintenance software. Crew issue action-based natural language commands through a search bar. The NLP pipeline interprets intent across domains and entities — a PA that opens all drawers at once. Every feature, test, and UI decision flows from this.

The product has three stages:

| Stage | What | Status |
|---|---|---|
| 1 — Search Pipeline | F1 SSE search, intent extraction, Cortex rewrites, RRF fusion | Complete. Signed off. |
| 2 — Entity Lenses | 12 entity types, 12 detail pages, /v1/entity/ endpoints, RouteShell | Complete. Signed off. |
| 3 — Actions / Mutations | 126 actions across 10 domains, audit trail, ledger | **Your work. This document.** |

### Required Reading (in this order)

| # | Document | What it tells you | Where |
|---|----------|-------------------|-------|
| 1 | **This file** | The 31 failures, their fixes, verification steps | You're here |
| 2 | **`docs/STAGE_3_HANDOVER.md`** | Full project context: hardware, two-DB architecture, Stage 1-2 summaries, auth, JWT minting, what Stage 3 is, the action dispatcher model, known bugs | **Start here for context** |
| 3 | **`docs/STAGE_3_ACTION_COVERAGE.md`** | Every action button by lens, what a "pass" means, shard summary, signature types, ledger tracking, known backend bugs | Reference for what each test is testing |
| 4 | **`docs/DB_architecture.md`** | Table relationships, RLS policies, triggers — you will need this for REM-002/003/004/006 | DB schema understanding |
| 5 | **`apps/web/e2e/rbac-fixtures.ts`** | Test infrastructure: how roles work, env vars needed, fixture helpers | Lines 1–60 are the contract |
| 6 | **`apps/web/playwright.config.ts`** | Shard→project mapping (lines 253–460), webServer config (lines 470–473) | Why `--project` not `--grep` |

### Repo Structure

```
BACK_BUTTON_CLOUD_PMS/
├── apps/
│   ├── api/                          # Python FastAPI backend
│   │   ├── pipeline_service.py       # ← Entry point (uvicorn target)
│   │   ├── routes/
│   │   │   └── p0_actions_routes.py  # ← Action dispatcher (1800+ lines)
│   │   │                               All POST /v1/actions/execute go here
│   │   │                               Validation gates per action (line ~900)
│   │   └── handlers/                 # One file per domain
│   │       ├── hours_of_rest_handlers.py  # REM-002, 003, 004
│   │       ├── inventory_handlers.py      # REM-005
│   │       └── ... (26 handler files)
│   │
│   └── web/                          # Next.js 14 frontend
│       ├── e2e/                      # Playwright E2E tests
│       │   ├── rbac-fixtures.ts      # ← Fixtures, env config, RBAC_CONFIG
│       │   ├── global-setup.ts       # Creates empty auth state files (by design)
│       │   ├── shard-33-lens-actions/
│       │   │   └── helpers.ts        # BASE_URL, callAction, assertNoRenderCrash
│       │   ├── shard-34-lens-actions/
│       │   │   └── helpers.ts        # generateFreshJwt, callActionAs, callActionDirect
│       │   └── shard-{35..47}-*/     # One dir per shard
│       ├── playwright.config.ts      # Shard project definitions
│       └── playwright/.auth/         # Auth state files (empty by design)
│
├── docs/                             # You are here
│   ├── STAGE_3_HANDOVER.md           # ← READ THIS FIRST
│   ├── STAGE_3_ACTION_COVERAGE.md
│   ├── STAGE_3_REMEDIATION.md        # ← This file
│   └── DB_architecture.md
│
└── deploy/local/
    └── celeste.sh                    # Docker orchestration script
```

### Two-Database Architecture (Critical — don't mix them up)

Every request touches two Supabase projects:

| Variable | Project | Purpose |
|---|---|---|
| `MASTER_SUPABASE_URL` | `qvzmkaamzaqxpzbewjxe` | Auth, user identity, tenant lookup |
| `SUPABASE_URL` (tenant) | `vzsohavtuotocgrfkfyd` | All PMS data — entities, ledger, audit, actions |

Flow: JWT validated against master → `get_my_bootstrap` RPC → resolves `yacht_id` + `tenant_key_alias` → tenant DB queried → API enforces row isolation via `.eq('yacht_id', yacht_id)` on every query (not Supabase RLS for most tables).

### How Auth Works in the Tests (Non-Obvious)

The E2E tests **do NOT use browser cookies for API auth.** This is the most confusing part of the test architecture:

- `global-setup.ts` creates **empty** auth state files: `{"cookies":[],"origins":[]}` — **this is by design**, not a bug.
- `callActionDirect()` and `callActionAs()` (in `shard-34-lens-actions/helpers.ts`) **self-mint a fresh JWT** using `SUPABASE_JWT_SECRET` at test time. They call the API directly with this JWT in the Authorization header. No browser session involved.
- `callAction()` (in `shard-33-lens-actions/helpers.ts`) uses `page.evaluate()` to make fetch calls from within the browser context, also with a self-minted JWT.
- Browser page navigation (e.g., `page.goto('/certificates/[id]')`) works because Next.js pages in this app render a shell first, then client-side fetch data with the JWT.

**Implication:** If `SUPABASE_JWT_SECRET` env var is missing, ALL API-calling tests fail with `Error: SUPABASE_JWT_SECRET env var is required`. If the JWT secret is wrong (doesn't match the API's signing key), ALL tests get 401.

### Environment Variables Needed

These must be set before running tests:

| Variable | Required By | How to Get It |
|---|---|---|
| `SUPABASE_JWT_SECRET` | Test JWT minting | Same as `TENANT_SUPABASE_JWT_SECRET` in the API container |
| `SUPABASE_SERVICE_KEY` | `supabaseAdmin` fixture (DB verification) | Tenant project service role key |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase client in tests | Tenant project URL |
| `NEXT_PUBLIC_API_URL` | API calls | Default: `http://localhost:8000` |
| `E2E_BASE_URL` | Page navigation | Default: `http://localhost:3000` |
| `TEST_YACHT_ID` | Fixture yacht scoping | Default: `85fe1119-b04c-41ac-80f1-829d23322598` |

### Test Credentials (Hardcoded)

| Field | Value |
|---|---|
| User UUID (`sub`) | `a35cad0b-02ff-4287-b6e4-17c96fa6a424` |
| Email | `x@alex-short.com` |
| Role | `captain` (resolved from tenant DB, not JWT) |
| Yacht ID | `85fe1119-b04c-41ac-80f1-829d23322598` |

### Running Options (Docker vs Bare Metal)

**Option A — Docker (recommended for first run):**
```bash
cd deploy/local
./celeste.sh start        # Starts API (8000) + Web (3000) + support services
./celeste.sh health       # Confirm healthy
```

**Option B — Bare metal (for this remediation work):**
```bash
# API
cd apps/api
source .env
uvicorn pipeline_service:app --host 0.0.0.0 --port 8000

# Frontend (MUST clear .next for REM-001)
cd apps/web
rm -rf .next
pkill -f "next dev" 2>/dev/null; sleep 1
npx next dev -p 3000
```

### Things That Will Waste Your Time (Gotchas)

1. **Port 3000 is sacred.** Tests hardcode `localhost:3000` in two places (`helpers.ts:6`, `playwright.config.ts:472`). Starting on any other port = 0 tests match.

2. **`--grep` silently matches nothing.** Playwright `--grep` matches test *titles*, not project names. `--grep "shard-33"` runs 0 tests and reports "0 passed" — looks like success. Always use `--project=shard-33-lens-actions`.

3. **The `.next` cache will haunt you.** If anyone ran `next build` in `apps/web/`, the `.next/` directory has production SSR chunks that conflict with `next dev`. Symptom: "Server Error: Cannot find module './vendor-chunks/@tanstack.js'". Fix: `rm -rf apps/web/.next`.

4. **Two Supabase projects, two JWT secrets.** The API uses `TENANT_SUPABASE_JWT_SECRET`. The tests use `SUPABASE_JWT_SECRET`. They must be the **same value**. If they differ, every test gets 401.

5. **`p0_actions_routes.py` is the action dispatcher** (~1800 lines). Every `POST /v1/actions/execute` goes through here. Line ~900 has the validation gates (required fields per action). If a test sends the wrong fields, it gets 400 before the handler runs.

6. **Triggers are invisible.** Three of the six bugs (REM-002, 004, 006) are caused by DB triggers that fire on INSERT/UPDATE. The handler code looks correct — the error happens *after* the handler's INSERT succeeds, when a trigger fires. Always check `information_schema.triggers` and `pg_proc` for trigger function source.

7. **`SyncQueryRequestBuilder` doesn't support `.select()` after `.insert()`.** Many handlers have a comment about this. They do INSERT then a separate SELECT to get the created row. This is a Supabase Python SDK limitation, not a bug.

8. **Don't touch Stage 1 (search pipeline).** The NLP is sufficient. Months of curation. Issues are always display/mapping bugs, never pipeline bugs.

---

## Executive Summary

31 E2E test failures across 5 shards trace to **6 root causes**. All are fixable without architectural changes.

| Group | Root Cause | Failures | Fix Type | Effort |
|-------|-----------|----------|----------|--------|
| A | Stale `.next` build cache | 23 | Dev workflow | 5 min |
| B | Missing UNIQUE constraint on `pms_hours_of_rest` | 3 | DB migration | 10 min |
| C | Missing RLS INSERT policy on `pms_crew_normal_hours` | 1 | DB migration | 5 min |
| D | `create_monthly_signoff` INSERT fails silently | 2 | DB investigation | 10 min |
| E | `log_part_usage` — no stock seed in test | 1 | Test fix | 15 min |
| F | Invalid enum value `"closed"` in `work_order_status` | 1 | DB migration | 5 min |

**After all 6 fixes:** 148 tests total — 147 passed, 0 failed, 1 skipped.

---

## Environment Setup (How to Reproduce)

```bash
# 1. Start API server
cd BACK_BUTTON_CLOUD_PMS/apps/api
source .env && uvicorn pipeline_service:app --host 0.0.0.0 --port 8000

# 2. Start frontend dev server (CRITICAL: clean .next first for Group A)
cd BACK_BUTTON_CLOUD_PMS/apps/web
rm -rf .next
npx next dev -p 3000

# 3. Verify env vars (CRITICAL: tests self-mint JWTs — they need these secrets)
# Auth state files in playwright/.auth/ are empty by design (global-setup.ts creates them).
# Tests do NOT use browser cookies — they mint JWTs directly using SUPABASE_JWT_SECRET.
echo "SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:?MISSING — tests will crash}"
echo "SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY:?MISSING — DB verification will crash}"

# 4. Run all shards (use --project, NOT --grep — grep matches test titles, not project names)
cd BACK_BUTTON_CLOUD_PMS/apps/web
npx playwright test \
  --project=shard-33-lens-actions \
  --project=shard-34-lens-actions \
  --project=shard-35-shopping-parts \
  --project=shard-36-receiving \
  --project=shard-37-hours-of-rest \
  --project=shard-38-fault-actions \
  --project=shard-39-wo-equipment \
  --project=shard-40-purchase-handover \
  --project=shard-41-wo-extended \
  --project=shard-42-fault-equipment \
  --project=shard-43-docs-certs \
  --project=shard-44-parts-shopping \
  --project=shard-45-receiving-po \
  --project=shard-46-hor-extended \
  --project=shard-47-handover-misc \
  --retries 1
```

**Port mapping (hardcoded in tests — do not change):**
- `helpers.ts:6` — `BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000'`
- `playwright.config.ts:472` — `url: 'http://localhost:3000'`
- API: port 8000

**Playwright command syntax (critical — easy to get wrong):**
- Use `--project=shard-33-lens-actions`, NOT `--grep "shard-33"`.
- `--grep` matches test *titles* (the `test('...')` strings), not project names or file paths.
- Using `--grep "shard-33"` silently runs **0 tests** and reports "0 passed" — which looks like success.
- `playwright.config.ts:470-473` configures `webServer` with `reuseExistingServer: !IS_CI` — if you already have a dev server running on port 3000, Playwright reuses it. If you DON'T have one, Playwright starts `npm run dev` automatically. Either way, the server must be on port 3000.

**Prerequisites:**
- Docker running (Supabase local or remote)
- JWT token at `/tmp/jwt_token.txt` (see MEMORY: JWT Auth for Testing)
- `.env` loaded with `MASTER_SUPABASE_JWT_SECRET`, `SUPABASE_URL`, etc.
- `SUPABASE_JWT_SECRET` and `SUPABASE_SERVICE_KEY` env vars set (tests self-mint JWTs — see "How Auth Works" above)

---

## Issue Registry

---

### REM-001: Stale `.next` Build Cache (Group A — 23 failures)

**Shard:** 33 (all 23 failures are in this shard)

**Symptom:**
Every HOD and Captain lens page (certificates, documents, equipment, faults, inventory, work orders) shows a Next.js "Server Error" dialog instead of rendering content. Tests timeout waiting for page elements.

**Affected Tests (23):**

| # | Test File | Line | Test Name |
|---|-----------|------|-----------|
| 1 | `certificate-actions.spec.ts` | 17 | [HOD] renders certificate detail + action button visible |
| 2 | `certificate-actions.spec.ts` | 41 | [Captain] renders certificate detail + action button visible |
| 3 | `document-actions.spec.ts` | 35 | [HOD] renders document detail + Archive button visible |
| 4 | `document-actions.spec.ts` | 56 | [Captain] renders document detail + Archive button visible |
| 5 | `equipment-actions.spec.ts` | 22 | [HOD] renders equipment detail without crash |
| 6 | `equipment-actions.spec.ts` | 36 | [HOD] add-equipment-note → 200 + pms_equipment_notes write |
| 7 | `equipment-actions.spec.ts` | 88 | [Captain] renders equipment detail without crash |
| 8 | `equipment-actions.spec.ts` | 102 | [Captain] add-equipment-note → 200 + DB write |
| 9 | `fault-actions.spec.ts` | 21 | [HOD] renders fault detail without crash |
| 10 | `fault-actions.spec.ts` | 32 | [HOD] acknowledge-fault → 200 + status=investigating |
| 11 | `fault-actions.spec.ts` | 93 | [Captain] renders fault detail without crash |
| 12 | `fault-actions.spec.ts` | 104 | [Captain] acknowledge-fault → 200 + status=investigating |
| 13 | `inventory-actions.spec.ts` | 20 | [HOD] renders inventory detail without crash |
| 14 | `inventory-actions.spec.ts` | 34 | [HOD] check_stock_level → 200 + valid stock_status in JSON |
| 15 | `inventory-actions.spec.ts` | 64 | [Captain] renders inventory detail without crash |
| 16 | `inventory-actions.spec.ts` | 78 | [Captain] check_stock_level → 200 + valid stock_status |
| 17 | `inventory-actions.spec.ts` | 115 | [Crew] check_stock_level → 200 (read action, all roles) |
| 18 | `work-order-actions.spec.ts` | 29 | [HOD] renders work-order detail without crash |
| 19 | `work-order-actions.spec.ts` | 40 | [HOD] add-note via UI → 200 + pms_work_order_notes write |
| 20 | `work-order-actions.spec.ts` | 89 | [HOD] mark-complete → 200 + status=completed |
| 21 | `work-order-actions.spec.ts` | 125 | [HOD] start-work-order → 200 + status=in_progress |
| 22 | `work-order-actions.spec.ts` | 161 | [Captain] renders work-order detail without crash |
| 23 | `work-order-actions.spec.ts` | 172 | [Captain] add-note → 200 + DB write |

All test files are in: `apps/web/e2e/shard-33-lens-actions/`

**Root Cause:**
`next build` was run before `next dev`, and both share the `.next/` directory. The production build chunks SSR vendor modules differently than dev mode expects. When dev mode SSR tries to `require('./vendor-chunks/@tanstack.js')`, the file doesn't exist — only `@swc.js` and `next.js` are present in `.next/server/vendor-chunks/`.

**Evidence:**
```
# Error from page snapshot (error-context.md):
dialog "Server Error"
  paragraph: "Error: Cannot find module './vendor-chunks/@tanstack.js'
    Require stack:
    - .next/server/webpack-runtime.js
    - .next/server/app/certificates/[id]/page.js
    - node_modules/next/dist/server/require.js
    ..."

# Directory listing (.next/server/vendor-chunks/):
@swc.js    (18,162 bytes)
next.js    (2,171,428 bytes)
# @tanstack.js — MISSING
```

**Why 10 of 33 shard-33 tests passed despite the broken server:** The passing tests fall into two categories: (1) render-check tests like "renders page without 500 crash" — these use `assertNoRenderCrash()` (`e2e/shard-33-lens-actions/helpers.ts:91`) which checks for exact text `'500'` and `'Failed to Load'`, neither of which matches the "Server Error" dialog title, so the negative assertion passes even though the page is broken; (2) RBAC tests in `equipment-actions.spec.ts`, `fault-actions.spec.ts`, and `work-order-actions.spec.ts` that import `callActionAs()` from `../shard-34-lens-actions/helpers` (defined at `shard-34-lens-actions/helpers.ts:112`) — these self-mint a fresh JWT and make direct API calls, bypassing page rendering entirely. The failing Crew test (#17, `[Crew] check_stock_level`) uses `callAction()` which navigates to the page first, so it fails when the page can't render.

**Remedy:**
```bash
rm -rf apps/web/.next
# Then restart: npx next dev -p 3000
```

No code changes. No migrations. Just clear the stale cache before starting the dev server.

**Pre-flight: verify env vars** (tests self-mint JWTs — browser auth files are empty by design):
```bash
# These env vars MUST be set — tests will crash without them:
echo "SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:?MISSING}"
echo "SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY:?MISSING}"
```

**Verification:**
```bash
rm -rf apps/web/.next
pkill -f "next dev" 2>/dev/null; sleep 1  # stop any existing dev server
npx next dev -p 3000 &
sleep 8  # Wait for dev server compilation
npx playwright test --project=shard-33-lens-actions --retries 1
# Expect: 23 previously-failing tests now pass (plus existing 10 = all 33 in shard)
```

**Regression Check:** None. Deleting `.next` only affects dev mode startup; production builds are done fresh in CI.

---

### REM-002: Missing UNIQUE Constraint on `pms_hours_of_rest` (Group B — 3 failures)

**Shards:** 37, 46

**Symptom:**
`upsert_hours_of_rest` action returns HTTP 500 with Postgres error 42P10.

**Affected Tests (3):**

| # | Shard | Test File | Line | Test Name |
|---|-------|-----------|------|-----------|
| 1 | 37 | `hor-actions.spec.ts` | 33 | [Captain] upsert_hours_of_rest → 200 + pms_hours_of_rest row |
| 2 | 37 | `hor-actions.spec.ts` | 59 | [Captain] upsert_hours_of_rest (second date) → 200 + compliance fields |
| 3 | 46 | `hor-extended-actions.spec.ts` | 220 | [Captain] upsert_hours_of_rest — ADVISORY (bug re-check) |

**Root Cause:**
The handler at `apps/api/handlers/hours_of_rest_handlers.py:195` implements upsert via a manual check-then-insert/update pattern (lines 267–300). Postgres error `42P10` means "there is no unique or exclusion constraint matching the ON CONFLICT specification" — something in the INSERT chain uses `ON CONFLICT` against columns `(yacht_id, user_id, record_date)` without a matching UNIQUE index. This is most likely a DB trigger on `pms_hours_of_rest` (confirmed by the error occurring at INSERT time, not in the handler's own code which doesn't use ON CONFLICT).

**Evidence:**
```json
// Log line 398:
{"code":"DATABASE_ERROR","message":"{'code': '42P10', 'details': None, 'hint': None, 'message': 'there is no unique or exclusion constraint matching the ON CONFLICT specification'}","status_code":500}
```

**Handler code chain:**
1. `hours_of_rest_handlers.py:267-278` — checks for existing record via SELECT
2. `hours_of_rest_handlers.py:295` — INSERT into `pms_hours_of_rest`
3. DB trigger fires on INSERT → internally uses `ON CONFLICT (yacht_id, user_id, record_date)` → crash

**Remedy: Diagnose trigger, then apply migration**

**Step 1 — Confirm the trigger exists and uses ON CONFLICT:**
```sql
-- Identify triggers on pms_hours_of_rest:
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_table = 'pms_hours_of_rest';

-- Inspect trigger function source (look for ON CONFLICT):
SELECT p.proname, p.prosrc
FROM pg_trigger t
JOIN pg_proc p ON t.tgfnoid = p.oid
WHERE t.tgrelid = 'pms_hours_of_rest'::regclass;
```

**Step 2 — Apply the migration (after confirming the trigger references these columns):**
```sql
-- REM-002: Add unique constraint for ON CONFLICT in triggers
CREATE UNIQUE INDEX IF NOT EXISTS uq_pms_hours_of_rest_yacht_user_date
  ON pms_hours_of_rest (yacht_id, user_id, record_date);
```

**Verification:**
```bash
# Apply migration, then:
npx playwright test --project=shard-37-hours-of-rest --retries 1
# Expect: upsert_hours_of_rest tests pass (tests #94, #96, #98, #100 in log)
```

**Regression Check:**
- `get_hours_of_rest` (shard-37:87) — already passes, unaffected by index addition
- Any trigger that fires on `pms_hours_of_rest` INSERT — the unique index ENABLES the ON CONFLICT, so triggers should now succeed

---

### REM-003: Missing RLS INSERT Policy on `pms_crew_normal_hours` (Group C — 1 failure)

**Shard:** 46

**Symptom:**
`create_crew_template` action returns HTTP 500 with Postgres error 42501 (RLS violation).

**Affected Tests (1):**

| # | Shard | Test File | Line | Test Name |
|---|-------|-----------|------|-----------|
| 1 | 46 | `hor-extended-actions.spec.ts` | 57 | [Captain] create_crew_template → 200 + template created |

**Root Cause:**
The handler at `apps/api/handlers/hours_of_rest_handlers.py:809` calls `self.db.table("pms_crew_normal_hours").insert(insert_data).execute()` at line 866. The `pms_crew_normal_hours` table has RLS enabled but lacks an INSERT policy for the `authenticated` role. The SELECT and UPDATE policies exist (proven by `list_crew_templates` passing), but INSERT is blocked.

**Evidence:**
```json
// Log line 535:
{"code":"DATABASE_ERROR","message":"{'code': '42501', 'details': None, 'hint': None, 'message': 'new row violates row-level security policy for table \"pms_crew_normal_hours\"'}","status_code":500}
```

**Handler code:**
- `hours_of_rest_handlers.py:853-863` — builds `insert_data` dict
- `hours_of_rest_handlers.py:866` — `self.db.table("pms_crew_normal_hours").insert(insert_data).execute()`

**Remedy: Check existing policy pattern, then add INSERT policy**

**Step 1 — Check existing policies to match the pattern:**
```sql
-- IMPORTANT: Use whatever WITH CHECK pattern the existing SELECT/UPDATE policies use.
-- Do NOT blindly copy the example below — run this first:
SELECT policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'pms_crew_normal_hours';
```

**Step 2 — Add INSERT policy (adjust WITH CHECK to match Step 1 output):**
```sql
-- REM-003: Add RLS INSERT policy for crew schedule templates
-- Replace the WITH CHECK clause below with the pattern from Step 1
CREATE POLICY insert_crew_normal_hours ON pms_crew_normal_hours
  FOR INSERT
  TO authenticated
  WITH CHECK (
    yacht_id IN (
      SELECT yacht_id FROM user_yacht_roles
      WHERE user_id = auth.uid()
    )
  );
```

**Verification:**
```bash
npx playwright test --project=shard-46-hor-extended --retries 1
# Expect: create_crew_template test passes (test #155 in log)
```

**Regression Check:**
- `list_crew_templates` (shard-46:34) — read-only, unaffected
- `apply_crew_template` (shard-46) — if it also inserts into `pms_crew_normal_hours`, this fix helps it too

---

### REM-004: `create_monthly_signoff` INSERT Fails with Error "0" (Group D — 2 failures)

**Shards:** 37, 46

**Symptom:**
`create_monthly_signoff` action returns HTTP 500 with `{"code":"DATABASE_ERROR","message":"0","status_code":500}`. The error message "0" is the integer 0 (default value) coerced to a string.

**Affected Tests (2):**

| # | Shard | Test File | Line | Test Name |
|---|-------|-----------|------|-----------|
| 1 | 37 | `hor-actions.spec.ts` | 110 | [Captain] create_monthly_signoff → 200 + pms_monthly_signoffs row |
| 2 | 46 | `hor-extended-actions.spec.ts` | 242 | [Captain] create_monthly_signoff — ADVISORY (bug re-check) |

**Root Cause (HYPOTHESIS — requires trigger inspection to confirm):**
The handler at `apps/api/handlers/hours_of_rest_handlers.py:515` builds `insert_data` at lines 575-587. The code at line 584 has a comment `# compliance_percentage removed — column doesn't exist in DB schema`, indicating a previous fix attempt. The error `"message":"0"` is unusual — the integer `0` (a default value somewhere) is being coerced to a string error message. The most likely chain: a DB trigger on `pms_hor_monthly_signoffs` references `NEW.compliance_percentage`, which is `NULL` (column doesn't exist), and some expression evaluates to `0` which gets `RAISE`d as an error. **This is an inference — the trigger source must be inspected before applying a fix.**

**Evidence:**
```json
// Log line 415:
{"code":"DATABASE_ERROR","message":"0","status_code":500}

// Log line 419 (retry):
{"code":"DATABASE_ERROR","message":"0","status_code":500}
```

**Handler code:**
```python
# hours_of_rest_handlers.py:568 — summary defaults to {}
summary = summary_result.data[0] if (...) else {}

# hours_of_rest_handlers.py:572 — compliance_pct defaults to 0
compliance_pct = summary.get("compliance_pct", 0)

# hours_of_rest_handlers.py:575-587 — insert_data (compliance_percentage removed)
insert_data = {
    "yacht_id": yacht_id,
    "user_id": user_id,
    "department": department,
    "month": month,
    "status": "draft",
    "total_rest_hours": total_rest,       # 0 (from empty summary)
    "total_work_hours": total_work,       # 0 (from empty summary)
    "violation_count": violations,         # 0 (from empty summary)
    "created_at": ...,
    "updated_at": ...,
}

# hours_of_rest_handlers.py:590 — INSERT executes
self.db.table("pms_hor_monthly_signoffs").insert(insert_data).execute()
# → Trigger fires → raises error "0"
```

**Remedy: Investigate trigger FIRST, then apply fix**

**Step 1 (MANDATORY) — Identify the trigger and read its source:**
```sql
-- Find all triggers on pms_hor_monthly_signoffs:
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_table = 'pms_hor_monthly_signoffs';

-- Read trigger function source (look for compliance_percentage, RAISE, or NEW.* references):
SELECT p.proname, p.prosrc
FROM pg_trigger t
JOIN pg_proc p ON t.tgfnoid = p.oid
WHERE t.tgrelid = 'pms_hor_monthly_signoffs'::regclass;
```

**Step 2 — Apply the fix that matches what the trigger expects.** Three options, in order of likelihood:

*Option A — Add the column (if the trigger reads `NEW.compliance_percentage`):*
```sql
ALTER TABLE pms_hor_monthly_signoffs
  ADD COLUMN IF NOT EXISTS compliance_percentage NUMERIC DEFAULT 0;
```

*Option B — Fix the trigger (if the column is truly unwanted and the trigger is wrong):*
```sql
-- Alter the trigger function to not reference compliance_percentage
-- (exact SQL depends on Step 1 output)
```

*Option C — Add compliance_percentage to the INSERT payload (code fix, if column exists but handler omits it):*
```python
# hours_of_rest_handlers.py:575 — add compliance_percentage back
insert_data = {
    ...
    "compliance_percentage": compliance_pct,  # Re-add: trigger expects this column
    ...
}
```

**Recommended:** Option A (add column) is the most likely fix — the trigger probably reads `NEW.compliance_percentage` — but **do not apply without running Step 1 first.**

**Verification:**
```bash
npx playwright test --project=shard-37-hours-of-rest --retries 1
# Expect: create_monthly_signoff test passes (test #103 — HTTP 200 or 409)
```

**Regression Check:**
- `sign_monthly_signoff` (shard-37:138) — reads the signoff row; adding a column doesn't break reads
- `list_monthly_signoffs` (shard-46:174) — SELECT *, will include new column harmlessly
- `get_monthly_signoff` (shard-46:197) — same

---

### REM-005: `log_part_usage` — No Active Stock Records (Group E — 1 failure)

**Shard:** 34

**Symptom:**
Captain's `log_part_usage` test returns HTTP 500 with Postgres error 45000: "Cannot log usage — no active stock records for this part."

**Affected Tests (1):**

| # | Shard | Test File | Line | Test Name |
|---|-------|-----------|------|-----------|
| 1 | 34 | `inventory-actions-full.spec.ts` | 93 | [Captain] log_part_usage → 200 + ledger row + quantity_on_hand decreased |

**Root Cause:**
The test uses `getPartWithStock()` fixture (line 101) which finds a part where `pms_parts.quantity_on_hand >= 2`. However, the `deduct_part_inventory()` Postgres function (called at `inventory_handlers.py:403-415`) checks for rows in `pms_part_stock` — a separate stock-tracking table. The fixture checks the wrong table: `pms_parts.quantity_on_hand` can be >= 2 while `pms_part_stock` has zero active rows. Regardless of why the stock rows are missing, the fix is the same: the Captain test must seed its own `pms_part_stock` rows before calling `log_part_usage`.

**Evidence:**
```json
// Log lines 291-296:
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "Failed to log part usage: {'code': '45000', 'details': None, 'hint': None, 'message': 'Cannot log usage - no active stock records for this part.'}"
}
```

**Handler code:**
```python
# inventory_handlers.py:402-415 — calls Postgres function
deduct_result = self.db.rpc(
    "deduct_part_inventory",
    {
        "p_yacht_id": yacht_id,
        "p_part_id": part_id,
        "p_quantity": int(quantity),
        "p_work_order_id": work_order_id,
        "p_equipment_id": equipment_id,
        "p_usage_reason": usage_reason,
        "p_notes": notes,
        "p_used_by": user_id
    }
).execute()
```

**Test code:**
```typescript
// inventory-actions-full.spec.ts:101
part = await getPartWithStock();  // finds pms_parts.quantity_on_hand >= 2
// But pms_part_stock may have no rows for this part
```

**Remedy: Test Fix**

The Captain test must seed its own `pms_part_stock` rows before consuming. Insert directly via `supabaseAdmin` (already available as a fixture in the test):

```typescript
// inventory-actions-full.spec.ts — before line 112, add:
// Seed stock to ensure pms_part_stock has active rows for this part
await supabaseAdmin.from('pms_part_stock').insert({
  yacht_id: RBAC_CONFIG.yachtId,  // from '../rbac-fixtures'
  part_id: partId,
  location: 'main_store',
  quantity: 5,
  status: 'active',
});
```

**Alternative** (via `receive_part` action — note the required fields differ from `pms_part_stock` columns):
```typescript
// receive_part requires: part_id, to_location_id (UUID), quantity, idempotency_key
// (see p0_actions_routes.py:919 for the validation gate)
const seedResult = await callActionDirect(captainPage, 'receive_part', {
  part_id: partId,
  to_location_id: '<UUID of a valid pms_locations row>',  // NOT a text string — must be a UUID
  quantity: 5,
  idempotency_key: `seed-captain-${Date.now()}`,
});
if (seedResult.status !== 200) {
  test.skip(true, 'Could not seed stock via receive_part — skipping');
  return;
}
```
> The admin INSERT is preferred because it doesn't require a valid `pms_locations` UUID and has no side effects (no receiving record, no audit log).

**Verification:**
```bash
npx playwright test --project=shard-34-lens-actions --retries 1
# Expect: Captain log_part_usage test passes (HTTP 200 + ledger row + quantity decreased)
```

**Regression Check:**
- HOD `log_part_usage` test (shard-34, earlier in file) — already passes; seeding extra stock doesn't affect it
- `transfer_part` test (shard-34:143) — uses its own fixture; independent

---

### REM-006: `update_equipment_status` — Invalid Enum Value "closed" (Group F — 1 failure)

**Shard:** 39

**Symptom:**
`update_equipment_status` action returns HTTP 500 with Postgres error 22P02: `invalid input value for enum work_order_status: "closed"`.

**Affected Tests (1):**

| # | Shard | Test File | Line | Test Name |
|---|-------|-----------|------|-----------|
| 1 | 39 | `wo-equipment-actions.spec.ts` | 117 | [Captain] update_equipment_status → 200 + pms_equipment status updated |

**Root Cause:**
A DB trigger on `pms_equipment` fires on **any** equipment status change (not just inactive/decommissioned — the test sends `new_status: 'operational'` and still triggers it). The trigger cascades the change to related work orders, attempting to set their status to `"closed"`. But `"closed"` is not a valid value in the `work_order_status` enum. The existing enum likely has values like: `planned`, `in_progress`, `completed`, `cancelled`.

**Evidence:**
```json
// Log line 435:
{"error":"Database error: {'code': '22P02', 'details': None, 'hint': None, 'message': 'invalid input value for enum work_order_status: \"closed\"'}","status_code":500,"path":"http://localhost:8000/v1/actions/execute"}
```

The error appears twice (lines 435 and 439 — original + retry), confirming it's deterministic.

**Remedy: DB Migration**

> **IMPORTANT: Transaction restriction.** `ALTER TYPE ... ADD VALUE` cannot run inside a multi-statement transaction in Postgres < 12. In Supabase SQL Editor this works fine (auto-commits). In CI migration pipelines that wrap multiple statements in `BEGIN/COMMIT`, this statement must run separately **outside** the transaction block. If your migration runner wraps in transactions, split this into its own migration file.

```sql
-- REM-006: Add 'closed' to work_order_status enum
-- Must run OUTSIDE a transaction block in Postgres < 12 (see note above)
ALTER TYPE work_order_status ADD VALUE IF NOT EXISTS 'closed';
```

**Alternative** (if `"closed"` is semantically wrong): Fix the trigger to use `"completed"` instead:
```sql
-- Find the trigger function:
SELECT p.proname, p.prosrc
FROM pg_trigger t
JOIN pg_proc p ON t.tgfnoid = p.oid
WHERE t.tgrelid = 'pms_equipment'::regclass;

-- Then ALTER the function to use 'completed' instead of 'closed'
```

**Recommended:** Add `'closed'` to the enum. It's a legitimate status distinct from `'completed'` (equipment-triggered closure vs normal completion).

**Verification:**
```bash
npx playwright test --project=shard-39-wo-equipment --retries 1
# Expect: update_equipment_status test passes (HTTP 200 + equipment status updated)
```

**Regression Check:**
- `complete_work_order` (shard-39:33) — already passes, sets `status=completed`; adding `closed` to enum doesn't affect it
- Any query filtering by `status` — adding a new enum value doesn't affect existing queries
- UI dropdowns showing WO status — verify `"closed"` is handled or hidden as appropriate

---

## Combined Migration Script

Run REM-002, REM-003, and REM-004 together. **REM-006 must be in a separate file** — see note below.

> **Migration runner warning:** `ALTER TYPE ... ADD VALUE` (REM-006) cannot execute inside a `BEGIN/COMMIT` block in Postgres < 12. Most migration runners (including Supabase CLI) auto-wrap each file in a transaction. If REM-006 is in the same file as the other statements, the runner wraps all four in one transaction and REM-006 fails. Keep REM-006 as its own migration file — Supabase runs each file as a separate transaction boundary, which is exactly what `ADD VALUE` needs.

**File 1: `migrations/stage3_rem_002_003_004.sql`** (can run in a transaction)
```sql
-- =============================================================================
-- STAGE 3 REMEDIATION — File 1 of 2
-- Date: 2026-03-16
-- Fixes: REM-002, REM-003, REM-004
-- =============================================================================

-- REM-002: Unique constraint for ON CONFLICT in pms_hours_of_rest triggers
CREATE UNIQUE INDEX IF NOT EXISTS uq_pms_hours_of_rest_yacht_user_date
  ON pms_hours_of_rest (yacht_id, user_id, record_date);

-- REM-003: RLS INSERT policy for crew schedule templates
-- ⚠ BEFORE RUNNING: Check existing policy pattern with:
--   SELECT policyname, cmd, qual, with_check FROM pg_policies
--   WHERE tablename = 'pms_crew_normal_hours';
-- Then adjust the WITH CHECK below to match the existing SELECT/UPDATE pattern.
CREATE POLICY insert_crew_normal_hours ON pms_crew_normal_hours
  FOR INSERT
  TO authenticated
  WITH CHECK (
    yacht_id IN (
      SELECT yacht_id FROM user_yacht_roles
      WHERE user_id = auth.uid()
    )
  );

-- REM-004: Add compliance_percentage column (trigger likely expects it)
-- ⚠ BEFORE RUNNING: Confirm trigger reads NEW.compliance_percentage with:
--   SELECT p.proname, p.prosrc FROM pg_trigger t
--   JOIN pg_proc p ON t.tgfnoid = p.oid
--   WHERE t.tgrelid = 'pms_hor_monthly_signoffs'::regclass;
-- If the trigger does NOT reference compliance_percentage, skip this and
-- fix the trigger function instead (see REM-004 in Issue Registry).
ALTER TABLE pms_hor_monthly_signoffs
  ADD COLUMN IF NOT EXISTS compliance_percentage NUMERIC DEFAULT 0;
```

**File 2: `migrations/stage3_rem_006_enum.sql`** (MUST be a separate file — cannot run inside a transaction)
```sql
-- =============================================================================
-- STAGE 3 REMEDIATION — File 2 of 2
-- Date: 2026-03-16
-- Fix: REM-006
--
-- ⚠ This file MUST be separate from File 1.
-- ALTER TYPE ... ADD VALUE cannot run inside BEGIN/COMMIT in Postgres < 12.
-- Migration runners (including Supabase CLI) wrap each file in its own
-- transaction boundary. Keeping this as its own file ensures it auto-commits
-- independently.
-- =============================================================================

ALTER TYPE work_order_status ADD VALUE IF NOT EXISTS 'closed';
```

**After running the migration, verify:**
```sql
-- Check REM-002
SELECT indexname FROM pg_indexes WHERE tablename = 'pms_hours_of_rest' AND indexdef LIKE '%yacht_id%user_id%record_date%';

-- Check REM-003
SELECT policyname FROM pg_policies WHERE tablename = 'pms_crew_normal_hours' AND cmd = 'INSERT';

-- Check REM-004
SELECT column_name FROM information_schema.columns WHERE table_name = 'pms_hor_monthly_signoffs' AND column_name = 'compliance_percentage';

-- Check REM-006
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'work_order_status'::regtype AND enumlabel = 'closed';
```

---

## Verification Runbook

Execute fixes in this order. Each step is independently verifiable.

### Step 1: Group A — Clear `.next` cache (REM-001)
```bash
cd apps/web
rm -rf .next

# Verify env vars (tests self-mint JWTs — auth state files are empty by design):
echo "SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:?MISSING — set this first}"
echo "SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY:?MISSING — set this first}"

pkill -f "next dev" 2>/dev/null; sleep 1  # stop any existing dev server (avoids EADDRINUSE)
npx next dev -p 3000 &
sleep 8  # Wait for dev server compilation
npx playwright test --project=shard-33-lens-actions --retries 1
# EXPECTED: 33 tests, 0 failures
```

### Step 2: Groups B + C + D + F — Apply DB migrations (REM-002, 003, 004, 006)
```bash
# Apply combined migration script above via Supabase SQL Editor or psql
# IMPORTANT: Run REM-002/003/004 diagnostic queries FIRST (see each REM section)
# Then re-run affected shards:
npx playwright test \
  --project=shard-37-hours-of-rest \
  --project=shard-39-wo-equipment \
  --project=shard-46-hor-extended \
  --retries 1
# EXPECTED:
#   shard-37: upsert_hours_of_rest passes, create_monthly_signoff passes
#   shard-39: update_equipment_status passes
#   shard-46: create_crew_template passes, upsert + signoff re-checks pass
```

### Step 3: Group E — Fix test seed (REM-005)
```bash
# Edit apps/web/e2e/shard-34-lens-actions/inventory-actions-full.spec.ts
# Add receive_part seed before Captain's log_part_usage call (see REM-005 remedy)
npx playwright test --project=shard-34-lens-actions --retries 1
# EXPECTED: all shard-34 tests pass including Captain log_part_usage
```

### Step 4: Full Regression
```bash
npx playwright test \
  --project=shard-33-lens-actions \
  --project=shard-34-lens-actions \
  --project=shard-35-shopping-parts \
  --project=shard-36-receiving \
  --project=shard-37-hours-of-rest \
  --project=shard-38-fault-actions \
  --project=shard-39-wo-equipment \
  --project=shard-40-purchase-handover \
  --project=shard-41-wo-extended \
  --project=shard-42-fault-equipment \
  --project=shard-43-docs-certs \
  --project=shard-44-parts-shopping \
  --project=shard-45-receiving-po \
  --project=shard-46-hor-extended \
  --project=shard-47-handover-misc \
  --retries 1
# EXPECTED: 148 tests total — 147 passed, 0 failed, 1 skipped
```

---

## Appendix A: Failure Summary from Test Log

```
31 failed
  [shard-33] certificate-actions.spec.ts:17   — [HOD] renders certificate detail
  [shard-33] certificate-actions.spec.ts:41   — [Captain] renders certificate detail
  [shard-33] document-actions.spec.ts:35      — [HOD] renders document detail
  [shard-33] document-actions.spec.ts:56      — [Captain] renders document detail
  [shard-33] equipment-actions.spec.ts:22     — [HOD] renders equipment detail
  [shard-33] equipment-actions.spec.ts:36     — [HOD] add-equipment-note
  [shard-33] equipment-actions.spec.ts:88     — [Captain] renders equipment detail
  [shard-33] equipment-actions.spec.ts:102    — [Captain] add-equipment-note
  [shard-33] fault-actions.spec.ts:21         — [HOD] renders fault detail
  [shard-33] fault-actions.spec.ts:32         — [HOD] acknowledge-fault
  [shard-33] fault-actions.spec.ts:93         — [Captain] renders fault detail
  [shard-33] fault-actions.spec.ts:104        — [Captain] acknowledge-fault
  [shard-33] inventory-actions.spec.ts:20     — [HOD] renders inventory detail
  [shard-33] inventory-actions.spec.ts:34     — [HOD] check_stock_level
  [shard-33] inventory-actions.spec.ts:64     — [Captain] renders inventory detail
  [shard-33] inventory-actions.spec.ts:78     — [Captain] check_stock_level
  [shard-33] inventory-actions.spec.ts:115    — [Crew] check_stock_level
  [shard-33] work-order-actions.spec.ts:29    — [HOD] renders work-order detail
  [shard-33] work-order-actions.spec.ts:40    — [HOD] add-note via UI
  [shard-33] work-order-actions.spec.ts:89    — [HOD] mark-complete
  [shard-33] work-order-actions.spec.ts:125   — [HOD] start-work-order
  [shard-33] work-order-actions.spec.ts:161   — [Captain] renders work-order detail
  [shard-33] work-order-actions.spec.ts:172   — [Captain] add-note
  [shard-34] inventory-actions-full.spec.ts:93 — [Captain] log_part_usage
  [shard-37] hor-actions.spec.ts:33            — [Captain] upsert_hours_of_rest
  [shard-37] hor-actions.spec.ts:59            — [Captain] upsert_hours_of_rest (2nd date)
  [shard-37] hor-actions.spec.ts:110           — [Captain] create_monthly_signoff
  [shard-39] wo-equipment-actions.spec.ts:117  — [Captain] update_equipment_status
  [shard-46] hor-extended-actions.spec.ts:57   — [Captain] create_crew_template
  [shard-46] hor-extended-actions.spec.ts:220  — [Captain] upsert_hours_of_rest (re-check)
  [shard-46] hor-extended-actions.spec.ts:242  — [Captain] create_monthly_signoff (re-check)
1 skipped
116 passed (8.1m)
```

## Appendix B: Key Source Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `apps/api/handlers/hours_of_rest_handlers.py` | 195–345 | `upsert_hours_of_rest` handler |
| `apps/api/handlers/hours_of_rest_handlers.py` | 515–618 | `create_monthly_signoff` handler |
| `apps/api/handlers/hours_of_rest_handlers.py` | 809–888 | `create_crew_template` handler |
| `apps/api/handlers/inventory_handlers.py` | 354–453 | `log_part_usage_execute` handler |
| `apps/api/routes/p0_actions_routes.py` | 135, 1673–1687 | `log_part_usage` dispatcher |
| `apps/api/pipeline_service.py` | — | API entry point (uvicorn target) |
| `apps/web/e2e/shard-33-lens-actions/helpers.ts` | 6, 91 | `BASE_URL`, `assertNoRenderCrash()` |
| `apps/web/e2e/shard-34-lens-actions/helpers.ts` | 112 | `callActionAs()` (self-minted JWT) |
| `apps/web/e2e/rbac-fixtures.ts` | 21–22 | `RBAC_CONFIG.yachtId` |
| `apps/web/e2e/shard-34-lens-actions/inventory-actions-full.spec.ts` | 93–137 | Captain log_part_usage test |
| `apps/web/e2e/shard-37-hours-of-rest/hor-actions.spec.ts` | 33, 59, 110 | HoR + signoff tests |
| `apps/web/e2e/shard-39-wo-equipment/wo-equipment-actions.spec.ts` | 117 | Equipment status test |
| `apps/web/e2e/shard-46-hor-extended/hor-extended-actions.spec.ts` | 57, 220, 242 | Extended HoR tests |
| `apps/web/playwright.config.ts` | 253–460, 470–473 | Shard project definitions, webServer config |
