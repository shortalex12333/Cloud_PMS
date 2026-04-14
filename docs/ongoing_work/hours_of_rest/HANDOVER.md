# Hours of Rest — Worker Handover Document
**Date:** 2026-04-13
**Written by:** FRONTEND02 (Claude Code instance)
**For:** Next worker — assume zero prior context

---

## 1. WHAT THIS MODULE IS AND WHY IT EXISTS

Cloud PMS is a vessel management system for superyachts. One of its legal requirements under **MLC 2006** (Maritime Labour Convention) is that every crew member must:

1. Log their **daily working hours** (rest is calculated as the complement — 24h minus work)
2. Have those records **countersigned by their Head of Department (HOD)**
3. Have them **approved by the Captain**
4. Be **locked and archived monthly**

Violations — too little rest, unsigned records — can result in port detention, flag state fines, or loss of operating licence. This is not optional compliance. It is a hard legal obligation.

The Hours of Rest module is the UI and backend system that handles all of this.

---

## 2. WHAT WAS BUILT THIS SPRINT (BUSINESS TERMS)

| What | Status |
|---|---|
| Backend: daily record creation, update, sign chain, locking | Done |
| Backend: monthly sign-off flow (crew → HOD → Captain) | Done |
| Backend: lock enforcement (finalized month blocks new entries) | Done |
| Backend: warning dismissal (HOD dismisses MLC violation alerts) | Done |
| E2E test suite: 20/22 tests passing, 2 skipped (known reason) | Done |
| Frontend: slider now collects WORK hours (not rest) | Done |
| Frontend: real API wired (no more hardcoded mock data) | Done |
| Frontend: department vs all-departments visually distinct | Done |
| Frontend: hours computed from periods (not stale DB totals) | Done |

---

## 3. FILES INVOLVED — WHAT EACH ONE DOES

### Backend — Python (FastAPI), runs in Docker on port 8000

| File | Created/Edited | Purpose |
|---|---|---|
| `apps/api/handlers/hours_of_rest_handlers.py` | Edited (major) | Core business logic. Handles upsert, sign chain, warning dismissal, lock enforcement. This is the single most important backend file. |
| `apps/api/routes/hours_of_rest_routes.py` | Edited | HTTP route definitions: upsert, sign, list signoffs, create signoff, warnings. These are the REST endpoints the frontend calls directly. |
| `apps/api/routes/hor_compliance_routes.py` | Edited | Three read-only endpoints: `GET /my-week`, `GET /department-status`, `GET /vessel-compliance`. These power the three main views in the UI. |
| `apps/api/routes/handlers/hours_of_rest_handler.py` | Reviewed | Action bus dispatch layer. Routes action bus calls (from `POST /v1/actions/execute`) to the handler class above. |
| `apps/api/routes/p0_actions_routes.py` | Reviewed | The action bus router. Required fields validation happens here. `yacht_id` and `user_id` must be in the payload (not just context) for `create_monthly_signoff`. |

### Frontend — Next.js / TypeScript, runs on port 3000

| File | Created/Edited | Purpose |
|---|---|---|
| `apps/web/src/app/hours-of-rest/page.tsx` | Edited | Main page. Controls which tab is shown per role: crew sees "My Time", HOD adds "Department", Captain adds "All Departments", Fleet Manager adds "Fleet". Role gating logic lives here. |
| `apps/web/src/components/hours-of-rest/TimeSlider.tsx` | Edited | The 24-hour visual slider. User draws WORK blocks (amber). Backend calculates rest as the complement. Empty slider = 24h rest (valid day off, not a violation). |
| `apps/web/src/components/hours-of-rest/MyTimeView.tsx` | Edited (major) | The main crew view. Shows Mon–Sun week grid, one slider per day. Handles submit, undo, sign week, sign monthly. Wired to real API. |
| `apps/web/src/components/hours-of-rest/DepartmentView.tsx` | Edited | HOD view. Shows all crew in their department, who has submitted, pending counter-signs. Wired to `GET /department-status`. Distinct header added (teal badge). |
| `apps/web/src/components/hours-of-rest/VesselComplianceView.tsx` | Edited | Captain/Fleet view. All departments, vessel-wide compliance grid. Wired to `GET /vessel-compliance`. Distinct header added (purple badge). |
| `apps/web/src/components/hours-of-rest/FleetView.tsx` | Created | Fleet Manager view. Multi-vessel overview. Skeleton implementation — not fully wired yet. |
| `apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts` | Created | Next.js proxy. All frontend calls to `/api/v1/hours-of-rest/*` are forwarded to the Python backend at `NEXT_PUBLIC_API_URL`. Without this file, every API call would fail with 404. |

### E2E Tests — Playwright

| File | Created/Edited | Purpose |
|---|---|---|
| `apps/web/e2e/shard-37-hours-of-rest/hor-rbac-ui.spec.ts` | Created | 22 RBAC tests covering all phases: upsert, sign chain, dismiss warning, locking. 20 pass, 2 skipped (see bugs). |
| `apps/web/e2e/global-setup.ts` | Edited | Generates JWT tokens for all test roles before tests run. Required for auth. |
| `apps/web/e2e/rbac-fixtures.ts` | Edited | Provides `crewPage`, `hodPage`, `captainPage` etc. browser contexts. Also provides `supabaseAdmin` for direct DB setup/cleanup. |

### Database

| Object | Status | Purpose |
|---|---|---|
| `pms_hours_of_rest` | Exists | One row per crew member per day. Stores rest_periods, work_periods, total hours, compliance flags. |
| `pms_hor_monthly_signoffs` | Exists | One row per crew/month. Tracks sign chain status: draft → crew_signed → hod_signed → finalized. |
| `pms_crew_hours_warnings` | Exists | MLC violation alerts generated by the backend on upsert. HOD can dismiss these. |
| `work_periods` column on `pms_hours_of_rest` | **JUST ADDED** | Added 2026-04-13. Stores work blocks alongside rest blocks. Old rows have `NULL` here — they will populate on next upsert. |

---

## 4. HOW THE SYSTEM WORKS (OPERATIONAL)

### The sign chain (MLC requirement)
```
Crew logs work hours → Backend stores rest as complement
→ Crew signs their week → HOD counter-signs → Captain finalises
→ Month is locked → No more edits allowed
```

### Two ways to call the backend
The backend has two entry points. This caused confusion and wasted time:

1. **Action Bus** — `POST /v1/actions/execute` with `{action: "upsert_hours_of_rest", context: {...}, payload: {...}}`. Used by E2E tests.
2. **Direct REST routes** — `POST /v1/hours-of-rest/upsert`. Used by the frontend.

Both exist. Both work. The frontend uses the direct REST routes. The E2E tests use the action bus. This duality is intentional but confusing to new workers.

### The lock
When a monthly signoff reaches status `finalized`, `locked`, or `captain_signed`, any attempt to upsert a new record for that month returns `{success: false, error: {code: "LOCKED"}}`. The frontend then shows a locked state. This is enforced in `hours_of_rest_handlers.py`.

---

## 5. BUG STATUS (updated 2026-04-14)

All bugs below were verified against the live DB and source code by HOURSOFREST01. BUG-HOR-1 and BUG-HOR-2 were test artifacts, not real bugs. BUG-HOR-3 is fixed.

### BUG-HOR-1 — NOT A BUG (verified 2026-04-14)
**Original claim:** Unique constraint on `pms_hours_of_rest` was missing `user_id`.

**Reality:** Constraint `uq_pms_hor_primary_record UNIQUE (yacht_id, user_id, record_date) WHERE is_correction = FALSE` already exists. Two users can correctly insert for the same date. The original observation was based on E2E test data using the same `SESSION_USER_ID` for all calls — not a schema gap.

---

### BUG-HOR-2 — NOT A BUG (verified 2026-04-14)
**Original claim:** `create_monthly_signoff` always assigns a hardcoded test UUID as `user_id`.

**Reality:** Route passes `user_id_from_jwt` at `hours_of_rest_routes.py:524`. Handler uses `target_user_id = payload.get("target_user_id") or user_id`. Correct — uses JWT sub. The test observation was an artifact of all E2E calls using the same test JWT sub (`a35cad0b`).

---

### BUG-HOR-3 — FIXED (PR #515, 2026-04-13)
**What:** `sign_monthly_signoff` crashed with DATABASE_ERROR on invalid `signoff_id`. Root cause: `.maybe_single()` throws `APIError(204)` in supabase-py 2.12.0 on 0 rows.

**Fix:** Changed to list-mode `.execute()` with explicit `NOT_FOUND` check. Also fixed same pattern in `create_monthly_signoff` duplicate check.

---

### BUG-HOR-4 — UI — Known, Deferred
**What:** The E2E tests inject a self-signed JWT into the browser's localStorage. The Supabase JS client re-validates the session on page load and rejects any token it did not issue itself. The HoR page redirects to login.

**Effect:** The 2 UI tab visibility tests (crew and captain navigating to `/hours-of-rest`) cannot be automated without a real Supabase login session.

**Fix needed:** Real browser login flow in E2E tests using `supabase.auth.signInWithPassword()`, not JWT injection. This is infrastructure work, not a product bug. Deferred.

---

### BUG-HOR-5 — DATA — Existing rows
**What:** All rows inserted before 2026-04-13 have `total_rest_hours: 0.0` and `total_work_hours: 24.0` regardless of what rest_periods they contain. This is because test data was inserted directly into the database, bypassing the backend handler that computes those totals.

**Effect:** The UI shows "24h work / 0h rest — VIOLATION" for every historical row.

**Fix applied (frontend):** The frontend now computes hours from `rest_periods` / `work_periods` arrays directly, ignoring the stored totals. This makes the display correct even for historically broken rows.

**Fix still needed (backend):** The backend should recompute and update `total_rest_hours` / `total_work_hours` when a row already exists and the stored totals are 0 but periods are non-empty. Or a one-off migration script to backfill.

---

## 6. WHAT WENT WRONG — HONEST ACCOUNT

### Problem 1: Slider was built backwards
The slider was originally built to collect REST periods (user draws rest blocks). MLC compliance should be entered as WORK hours — rest is what remains. This was caught late during manual testing. The fix required changing the slider colour, semantics, and the submit payload. Time lost: ~2 hours.

**Why it happened:** The original brief said "hours of rest module" so rest blocks were the intuitive choice. The correct model (enter work, derive rest) was not specified until after the component was built.

---

### Problem 2: Frontend was never connected to the API
The frontend components had `MOCK_MY_WEEK` hardcoded as the data source. The API was built and tested, but the join between frontend and backend was never made. The page appeared to work (it showed data) but was showing fiction.

Additionally, the `my-week` and `department-status` endpoints existed on the backend but their existence was not known to the frontend worker. The frontend worker assumed they were missing and was about to rebuild them.

**Why it happened:** Frontend and backend work was split across sessions without a clear integration checkpoint. Each part looked complete in isolation.

---

### Problem 3: `maybe_single()` silently swallowed the monthly lock check
The lock enforcement code (prevents editing a finalised month) was built correctly, but the weekly lock check above it used `.maybe_single().execute()`. In `supabase-py` version 2.12.0, `maybe_single()` throws an `APIError` with code `204` when zero rows are found (instead of returning `None`). This exception was caught by a broad `except Exception` block that logged it at DEBUG level and proceeded. The monthly lock check immediately below never ran.

**Effect:** Lock enforcement appeared to work in Python unit tests but failed completely during E2E browser tests. Two Phase 7 tests failed for this reason across multiple sessions.

**Fix:** Changed weekly lock check to `.execute()` (returns a list, empty list when no rows). Changed the `except` to fail closed (return LOCKED/DATABASE_ERROR) rather than silently proceeding.

**Why it happened:** supabase-py 2.12.0 changed the behaviour of `maybe_single()`. The original developer wrote defensively (`try/except: pass`) assuming the exception was harmless. It was not.

---

### Problem 4: Docker container was not being rebuilt
Changes to the Python backend were made to source files on disk, but the Docker container running the API was not rebuilt. Some tests were passing against stale container code, others failing against new code. It was not always clear which version was running.

**Fix:** Must run `docker compose up -d --build api` after every backend change. The container does not hot-reload Python source files.

---

### Problem 5: `auth.users.id` vs `auth_users_profiles.id`
The system has two user ID spaces:
- `auth.users.id` — the UUID issued by Supabase Auth when a user logs in. This is what JWTs contain as the `sub` claim.
- `auth_users_profiles.id` — a separate UUID in the tenant database profile table.

These are different values for many users. Some legacy data (signoff rows, hours records) was written using `auth_users_profiles.id`. New code uses `auth.users.id`. Lock checks and cross-table joins silently returned empty results because the IDs never matched.

**Fix:** All new code uses the JWT sub (`auth.users.id`). Legacy poisoned rows in the DB cannot be fixed without a migration.

---

### Problem 6: Wrong API base URL in local development
The Next.js proxy (`route.ts`) defaults to `https://pipeline-core.int.celeste7.ai` (the production/staging backend) when `NEXT_PUBLIC_API_URL` is not set. This meant local frontend changes were hitting a remote server. The fix is already in `.env.local` (`NEXT_PUBLIC_API_URL=http://localhost:8000`) but if this file is missing (new machine, fresh clone), every local API call silently goes to production.

---

## 7. WHAT WORKS RIGHT NOW (AS OF 2026-04-13)

- `GET /v1/hours-of-rest/my-week` — returns current user's week: 7 days (Mon–Sun), rest_periods, work_periods, compliance, pending monthly signoff, templates
- `POST /v1/hours-of-rest/upsert` — creates/updates a daily record from work_periods. Derives rest. Checks lock. Returns updated record.
- `POST /v1/hours-of-rest/signoffs/create` — creates a monthly signoff (but assigns wrong user_id — see BUG-HOR-2)
- `POST /v1/hours-of-rest/signoffs/sign` — signs a signoff (crew → HOD → Captain)
- `GET /v1/hours-of-rest/department-status` — HOD view: crew grid, pending counter-signs
- `GET /v1/hours-of-rest/vessel-compliance` — Captain/Fleet view: all departments
- `POST /v1/hours-of-rest/warnings/dismiss` — HOD dismisses an MLC warning
- Frontend slider — draws work blocks (amber), empty = 24h rest
- Frontend My Time view — loads real data from API, Mon–Sun grid, submit per day works
- E2E suite — 20/22 tests pass, 2 skipped (BUG-HOR-4)

---

## 8. WHAT MUST HAPPEN NEXT (updated 2026-04-14)

**All P0 and P1 items are resolved as of 2026-04-14.** Verified by HOURSOFREST01 against live DB and source (9/9 integration scenarios, 92/92 checks, two clean runs).

### Remaining items
1. **E2E BUG-HOR-4** — The 2 skipped UI tab tests need real Supabase login in E2E setup (not JWT injection). Infrastructure work, not a product bug. Deferred.

2. **Backfill `total_rest_hours`/`total_work_hours`** for test rows where stored values are 0 despite non-empty periods. Frontend workaround (compute from periods) hides the display problem, but stored values remain dirty. One-off backend migration if needed.

3. **HOD self-completion gap** — If an HOD's role is literally "captain", they can sign all three levels (crew→hod→master) on the same signoff unblocked. The role check passes because "captain" satisfies the master-sign gate. Fix: add a "signer already appears in this signoff" guard in `sign_monthly_signoff` to prevent one person completing the full chain. Not a blocker for MVP.

---

## 9. KEY CONFIGURATION — DO NOT LOSE

| Variable | Value | Where |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `apps/web/.env.local` |
| `TEST_YACHT_ID` | `85fe1119-b04c-41ac-80f1-829d23322598` | `apps/web/.env.e2e` |
| `SUPABASE_JWT_SECRET` | (in `.env.e2e`) | Used by E2E tests to mint JWTs |
| Docker API container name | `cloud_pms-api-1` | `docker ps` |
| Supabase project | `vzsohavtuotocgrfkfyd` | Tenant DB |

To rebuild the backend after any Python change:
```bash
cd /Users/celeste7/Documents/Cloud_PMS
docker compose up -d --build api
```

To run the HoR E2E tests:
```bash
cd apps/web
export $(grep -v '^#' .env.e2e | xargs)
npx playwright test shard-37-hours-of-rest/hor-rbac-ui.spec.ts
# Expected: 20 passed, 2 skipped
```

---

## 10. AUTH UUIDs FOR TESTING

These are `auth.users.id` values (not profile IDs — they are different):

| Role | Email | UUID |
|---|---|---|
| Crew | engineer.test@alex-short.com | `4a66036f-899c-40c8-9b2a-598cee24a62f` |
| HOD | eto.test@alex-short.com | `81c239df-f8ef-4bba-9496-78bf8f46733c` |
| Captain | captain.tenant@alex-short.com | `5af9d61d-9b2e-4db4-a54c-a3c95eec70e5` |
| Fleet Manager | fleet-test@celeste7.ai | `f11f1247-b7bd-4017-bfe3-ebd3f8c9e871` |
| Legacy test user (ghost) | x@alex-short.com | `a35cad0b-02ff-4287-b6e4-17c96fa6a424` |

The "legacy test user" (`a35cad0b`) appears throughout the DB as the owner of old test records. It is not a real crew member. BUG-HOR-2 causes all new signoffs to also be owned by this UUID.

---

*End of handover. Next worker: read Section 8 first. Fix P0 bugs before touching anything else.*
