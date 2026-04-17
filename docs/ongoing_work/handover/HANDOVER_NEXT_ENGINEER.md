# Handover Domain -- Read This First

Last updated: 2026-04-14

This is a practical onboarding guide for any engineer or Claude agent picking up the handover domain.
It covers what will actually bite you, not what is theoretically interesting.

---

## Read these files first

1. `docs/explanations/LENS_DOMAINS/handover.md` -- 726-line complete feature explanation.
   Covers the data model, export lifecycle, LLM summarisation, and every table involved.

2. `docs/ongoing_work/handover/HANDOVER_FINAL_STATUS.md` -- test status and known bug list.
   Check this before assuming anything works.

3. `docs/ongoing_work/handover/HANDOVER_PLAYWRIGHT_AGENT_RUNBOOK.md` -- how to browser-test
   the handover UI end-to-end with Playwright.

---

## The 10 things I wish I knew at the start

### 1. Two code paths for add_to_handover

`internal_dispatcher.py:714` AND `handover_handlers.py:237`. Both insert into `handover_items`.
The dispatcher path is the legacy inline implementation. The handler path is the refactored
version that delegates to `HandoverHandlers.add_to_handover_execute`. If you fix a bug in
one, the other stays broken. Always fix both, or confirm which path is actually being hit
by checking the action router registry entry at `registry.py:905`.

### 2. Frontend supabase client = MASTER only

`supabaseClient.ts:4` uses `NEXT_PUBLIC_SUPABASE_URL` which resolves to the MASTER project
(`qvzmkaamzaqxpzbewjxe`). All PMS data lives in the TENANT database (`vzsohavtuotocgrfkfyd`).
Never call `supabase.from('any_pms_table')` from frontend code -- it will silently return
empty results or fail with a missing-table error. Always go through `fetch(RENDER_API_URL/...)`.

### 3. auth_users_profiles has no role column

Role lives in `auth_users_roles`. The two tables:

| Table | Columns |
|-------|---------|
| `auth_users_profiles` | id, yacht_id, email, name, is_active |
| `auth_users_roles` | id, user_id, yacht_id, role, department, is_active |

If you need role for an RLS policy or a backend query, join on `auth_users_roles.user_id`.
Querying `auth_users_profiles.role` will fail silently (column does not exist, Supabase
returns null).

### 4. p0_actions_routes.py prefix is /v1/actions

So `GET /handover` in that file is actually `/v1/actions/handover` at runtime. The handover
export routes live at `/v1/handover` (defined in `handover_export_routes.py`). Different
prefixes, different routers. Put new handover endpoints in `handover_export_routes.py`
unless they are action-framework endpoints (prefill, execute).

### 5. status vs export_status

Two separate columns on `handover_items`:

- `status` -- check constraint: `pending`, `acknowledged`, `completed`, `deferred`.
  This tracks the item lifecycle within a single watch period.
- `export_status` -- tracks `pending` or `exported`.
  This tracks whether the item has been included in a generated export document.

Using the wrong one in an UPDATE will hit a check constraint violation. The error message
from Supabase is unhelpful ("new row violates check constraint") with no column name.

### 6. LLM export takes 30-120 seconds

The microservice calls an LLM to generate narrative summaries for each handover section.
Any timeout under 120s will cause a partial or failed export. Playwright's default
`actionTimeout` is 15s -- set it to at least 150000ms for export tests. The backend
endpoint itself has a 300s timeout configured on Render.

### 7. Render Starter tier (512MB) cannot handle heavy deploy churn

10+ deploys in a day causes connection pool exhaustion, container cycling, and CORS
headers disappearing mid-transition. If tests start failing with network errors or
CORS violations after a deploy-heavy day, wait 5-10 minutes for the container to
stabilise. This is a platform limitation, not a code bug.

### 8. Test user MASTER vs TENANT ID mismatch

`captain.tenant@alex-short.com` had different UUIDs in the MASTER and TENANT databases.
The FK on `handover_items.added_by` references the TENANT `auth_users_profiles.id`. If
you create a test user, the UUID must match in both databases. The error message when
this is wrong is a generic FK violation that does not mention which user ID failed.

### 9. handover_entries has no DELETE policy

`handover_entries` are immutable truth seeds -- the raw items added to a handover queue
before they get exported. There is no RLS DELETE policy and no soft-delete column.
You cannot clean them up in tests. Design your test fixtures to use unique identifiers
and filter by them, rather than assuming a clean table.

### 10. The microservice is feature-flagged

`HANDOVER_USE_MICROSERVICE=true` is set on Render. Without it, the export endpoint
falls back to basic HTML generation (no LLM summaries, no narrative sections). The
microservice lives in a separate repo at `/Users/celeste7/Documents/handover_export/`
and runs on port 10000 in Docker. Check the flag before debugging why summaries are
missing.

---

## Key files quick reference

| What | File |
|------|------|
| Handover page (tabs) | `apps/web/src/app/handover-export/page.tsx` |
| Queue component | `apps/web/src/components/handover/HandoverQueueView.tsx` |
| Draft panel (CRUD) | `apps/web/src/components/handover/HandoverDraftPanel.tsx` |
| Document viewer | `apps/web/src/components/lens-v2/entity/HandoverContent.tsx` |
| Backend CRUD routes | `apps/api/routes/handover_export_routes.py` |
| Action dispatcher | `apps/api/action_router/dispatchers/internal_dispatcher.py:714` |
| Entity handler | `apps/api/routes/entity_routes.py:634` |
| Action registry | `apps/api/action_router/registry.py:905` |
| Handler (refactored) | `apps/api/routes/handlers/handover_handler.py` |
| Handler (class-based) | `apps/api/handlers/handover_handlers.py` |
| Ledger helpers | `apps/api/routes/handlers/ledger_utils.py` |
| Microservice | `/Users/celeste7/Documents/handover_export/` (separate repo) |
| DB architecture | `docs/explanations/DB_architecture.md` |

---

## Test credentials

| Role | Email | Password |
|------|-------|----------|
| crew | crew.test@alex-short.com | Password2! |
| chief_engineer | hod.test@alex-short.com | Password2! |
| captain | captain.tenant@alex-short.com | Password2! |
| manager | fleet-test-1775570624@celeste7.ai | Password2! (BROKEN -- TENANT JWT) |

The manager account authenticates against MASTER but the JWT it receives does not have
a valid TENANT user_id. Any endpoint that resolves `added_by` or checks yacht-scoped
RLS will fail. Use captain for full-privilege testing.

---

## How to run the test suite

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598 \
SUPABASE_JWT_SECRET=wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw== \
npx playwright test shard-47-handover-misc shard-49-handover-export-e2e shard-54-handover-tester-ui \
  --reporter=line
```

Expected: 39/39 PASS.

If any fail, check Render health first:

```bash
curl https://pipeline-core.int.celeste7.ai/healthz
```

If healthz returns 200 but tests still fail:

1. Check if the failure is a timeout (likely LLM export -- see point 6).
2. Check if the failure is CORS (likely deploy churn -- see point 7).
3. Check if the failure is an FK violation (likely user ID mismatch -- see point 8).
4. Read the test file -- each shard has comments at the top explaining what it covers.

---

## Common mistakes to avoid

- Do not add handover routes to `p0_actions_routes.py`. Use `handover_export_routes.py`.
- Do not query PMS tables from frontend code via the Supabase client.
- Do not assume `handover_items` and `handover_entries` are the same table. Items are
  queue entries that can be modified. Entries are immutable truth seeds.
- Do not set Playwright timeouts below 150s for export tests.
- Do not create test users in only one database. Both MASTER and TENANT must have
  matching UUIDs.
