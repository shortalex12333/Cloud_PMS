# Hours of Rest — Complete Domain Reference

**For any new engineer touching this feature.** Read this before opening any file.

---

## What this is

Hours of Rest (HoR) is the compliance tracking system for Maritime Labour Convention 2006 (MLC 2006) and STCW Convention. Every seafarer must get **minimum 10 hours rest in any 24-hour period** and **77 hours rest in any 7-day period**, with no more than 2 rest periods per day, and the longest must be ≥ 6 hours.

Port state inspectors can board a vessel and demand HoR records. A violation can result in port detention. The data in this system is legally significant. Corrections and dismissals carry mandatory justification. Everything is signed.

This is **not** a timekeeping tool for payroll. It is a compliance evidence trail.

---

## Role matrix — who sees what

| Role | Tab: My Time | Tab: Department | Tab: All Departments | Tab: Fleet |
|---|---|---|---|---|
| `crew` / `engineer` / most deck ratings | ✓ | — | — | — |
| `chief_engineer` / `chief_officer` / `eto` (HOD) | ✓ | ✓ | — | — |
| `captain` | ✓ | ✓ | ✓ | — |
| `manager` (fleet) | ✓ | — | ✓ | ✓ |

**Important:** The role check in `page.tsx` uses local functions `isHODRole()`, `isCaptainRole()`, `isFleetManagerRole()` — do NOT use the global `AuthContext.isHOD` which is too broad for HoR. The local functions are the single source of truth for tab visibility.

`chief_steward`, `purser` — can counter-sign at HOD level but do NOT get the Department tab (not in `isHODRole()`). This is intentional: they sign in the backend but don't manage a crew grid.

---

## File map — every file you need to know

### Frontend

```
apps/web/src/app/hours-of-rest/page.tsx          ← Entry point. Tab routing. Role guards.
apps/web/src/app/hours-of-rest/[id]/page.tsx     ← Individual record detail (thin, rarely used)
apps/web/src/app/hours-of-rest/signoffs/page.tsx ← Signoff list page
apps/web/src/app/hours-of-rest/signoffs/[id]/page.tsx ← Signoff detail

apps/web/src/components/hours-of-rest/
  MyTimeView.tsx          ← Crew's own week grid + slider + submit + signoff card
  TimeSlider.tsx          ← 24h work-period input widget (exported standalone)
  DepartmentView.tsx      ← HOD grid: all crew × 7 days + counter-sign queue
  VesselComplianceView.tsx ← Captain: dept cards + sign chain + all-crew grid
  FleetView.tsx           ← Fleet manager: per-vessel compliance summary

apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts  ← Next.js catch-all proxy
```

### Backend

```
apps/api/routes/hours_of_rest_routes.py         ← FastAPI router. 19 endpoints. Request models.
apps/api/routes/hor_compliance_routes.py        ← 4 enriched GET endpoints (my-week, dept, vessel, fleet)
apps/api/handlers/hours_of_rest_handlers.py     ← All business logic. ~2430 lines. Single class.
apps/api/routes/handlers/hours_of_rest_handler.py  ← Thin Phase 4 adapter (delegates to the class above)
```

### Tests

```
scripts/hor-integration-test/
  run.py              ← Runner. 9 scenarios in dependency order.
  auth.py             ← Real JWT auth for 4 test roles
  state.py            ← Shared constants (TEST_WEEK_MONDAY = "2025-01-06", yacht_id)
  teardown.py         ← Deletes all test data after run
  scenarios/
    s1_crew_submit.py          ← S1: crew submits a valid day
    s2_hod_submit.py           ← S2: HOD submits their own day
    s3_captain_submit.py       ← S3: captain submits their own day
    s4_hod_countersign.py      ← S4: HOD counter-signs crew's signoff
    s5_captain_sign_all.py     ← S5: captain gives master signature (requires S4)
    s6_fleet_inspect.py        ← S6: fleet manager reads compliance (requires S5)
    s7_violation_notification.py ← S7: submit violation, check HOD notification (requires S1)
    s8_crew_undo.py            ← S8: crew undoes a submitted day (runs AFTER S9)
    s9_correction_flow.py      ← S9: HOD adds correction to crew record (runs BEFORE S8)

scripts/hor-proof/
  hor-proof.spec.ts     ← Playwright screenshots for CEO review (3 roles × 7 proof screenshots)
  playwright.config.ts  ← Config. Set PROOF_DIR env var for output location.
```

---

## How a request travels

```
Browser
  └─ fetch('/api/v1/hours-of-rest/...', { headers: { Authorization: 'Bearer JWT' } })
       │
       └─ Next.js route: apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts
            │  (catch-all proxy — forwards all GET/POST verbatim)
            │  RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL
            │
            └─ Render API: apps/api/routes/hours_of_rest_routes.py (or hor_compliance_routes.py)
                 │  router prefix: /v1/hours-of-rest
                 │  get_authenticated_user() → validates JWT, extracts user_id, yacht_id, role, tenant_key_alias
                 │  resolve_yacht_id(auth, yacht_id) → fleet-aware isolation check
                 │
                 └─ HoursOfRestHandlers (apps/api/handlers/hours_of_rest_handlers.py)
                      │  Instantiated with get_tenant_client(tenant_key_alias)
                      │  Returns ResponseBuilder / JSONResponse
                      │
                      └─ Supabase TENANT DB (vzsohavtuotocgrfkfyd)
                           └─ Tables: pms_hours_of_rest, pms_hor_monthly_signoffs,
                                      pms_crew_hours_warnings, pms_crew_normal_hours,
                                      dash_crew_hours_compliance (view), pms_audit_log,
                                      ledger_events, pms_notifications
```

**Two routers, same prefix.** Both `hours_of_rest_routes.py` and `hor_compliance_routes.py` use `prefix="/v1/hours-of-rest"`. They are registered separately in `main.py`. The compliance routes (`/my-week`, `/department-status`, `/vessel-compliance`, `/fleet-compliance`) are pure GET endpoints that do **not** use `HoursOfRestHandlers` — they query Supabase directly.

---

## The key design decision: crew inputs WORK, backend derives REST

**This is the single most confusing thing about this domain. Read it twice.**

The `TimeSlider` component draws **work blocks** (amber). Crew mark when they are working. The backend receives `work_periods` and computes `rest_periods` as the mathematical complement of 24 hours.

```
work_periods = [{"start": "06:00", "end": "14:00"}, {"start": "18:00", "end": "22:00"}]
→ rest_periods = [{"start": "00:00", "end": "06:00"}, {"start": "14:00", "end": "18:00"}, {"start": "22:00", "end": "24:00"}]
→ total_work_hours = 12.0
→ total_rest_hours = 12.0
```

This inversion happened in April 2026. Prior to that, the system stored rest periods directly. The `UpdateHoursRequest` model still accepts `rest_periods` as a deprecated alias but ignores it. Do not pass `rest_periods` from new code.

`TimeSlider.tsx` exports `invertToRestPeriods(workPeriods)` if you ever need the frontend to compute rest periods for display (e.g. for read-only submitted days).

---

## Database tables

| Table | Purpose |
|---|---|
| `pms_hours_of_rest` | One row per (yacht_id, user_id, record_date). The primary daily record. Unique constraint: `uq_pms_hor_primary_record` on (yacht_id, user_id, record_date). |
| `pms_hor_monthly_signoffs` | Sign-off workflow. One row per sign cycle. Holds crew/HOD/master signatures. Used for both monthly AND weekly periods (`period_type` column). |
| `pms_crew_hours_warnings` | Compliance violations generated by `check_hor_violations` RPC. Status: active / acknowledged / dismissed. |
| `pms_crew_normal_hours` | Schedule templates (4-on/8-off, etc). One row per template per yacht. |
| `dash_crew_hours_compliance` | Materialised/computed view. Weekly summary per (yacht_id, user_id, week_start). Do NOT write to this. It is a read-only aggregation used by `/my-week` and `/department-status`. |
| `pms_audit_log` | Immutable per-action trail. Written by `_write_hor_audit_log()` in handlers. `signature` is NEVER NULL — use `{}` for unsigned actions. |
| `ledger_events` | Evidence bus. Written via `build_ledger_event()` from `routes/handlers/ledger_utils.py`. Every mutating HoR action writes here. |
| `pms_notifications` | Notification bus. Written on violations, sign chain events, corrections. `idempotency_key` column prevents duplicates. |

---

## The 19 endpoints

### Compliance endpoints (hor_compliance_routes.py) — READ ONLY

| Endpoint | Who calls it | Frontend consumer |
|---|---|---|
| `GET /v1/hours-of-rest/my-week` | All roles | `MyTimeView.tsx` |
| `GET /v1/hours-of-rest/department-status` | HOD+ only (403 otherwise) | `DepartmentView.tsx` |
| `GET /v1/hours-of-rest/vessel-compliance` | captain/manager only | `VesselComplianceView.tsx` |
| `GET /v1/hours-of-rest/fleet-compliance` | manager only | `FleetView.tsx` |

These four endpoints return **enriched, composed responses** — they JOIN multiple tables in a single request and return a single shaped JSON object. They are NOT generic CRUD. The shape they return is documented in the interface types at the top of each frontend component.

### Mutation endpoints (hours_of_rest_routes.py) — HoursOfRestHandlers

| Endpoint | Action | Notes |
|---|---|---|
| `POST /v1/hours-of-rest/upsert` | `upsert_hours_of_rest` | Creates or updates daily record. Checks week/month lock first. Calls `check_hor_violations` RPC. |
| `POST /v1/hours-of-rest/undo` | `undo_hours_of_rest` | Clears a submitted day. Only works if week is not finalized. Resets `work_periods` to `[]`. |
| `POST /v1/hours-of-rest/corrections` | `create_hor_correction` | Creates a correction record linked to original. `reason` is mandatory (legal field). |
| `POST /v1/hours-of-rest/request-correction` | `request_hor_correction` | HOD/captain sends kick-back to crew requesting a correction. |
| `POST /v1/hours-of-rest/signoffs/create` | `create_monthly_signoff` | Opens a sign-off period. HOD can open one for a crew member (`target_user_id`). |
| `POST /v1/hours-of-rest/signoffs/sign` | `sign_monthly_signoff` | Adds crew/hod/master signature. Enforces sequential workflow. |
| `POST /v1/hours-of-rest/templates/create` | `create_crew_template` | Creates a named schedule template. |
| `POST /v1/hours-of-rest/templates/apply` | `apply_crew_template` | Applies template to a week (bulk-creates daily records). |
| `POST /v1/hours-of-rest/warnings/acknowledge` | `acknowledge_warning` | Crew acknowledges a violation. Notifies HODs. |
| `POST /v1/hours-of-rest/warnings/dismiss` | `dismiss_warning` | HOD/captain dismisses a warning. `hod_justification` is mandatory (legally significant). |
| `GET /v1/hours-of-rest/notifications/unread` | — | Unread count badge on Department tab. |
| `POST /v1/hours-of-rest/notifications/mark-read` | — | Marks notifications read. |

### Read endpoints (hours_of_rest_routes.py) — HoursOfRestHandlers

| Endpoint | Action |
|---|---|
| `GET /v1/hours-of-rest` | `get_hours_of_rest` — basic date-range query, used by Phase 4 action router |
| `POST /v1/hours-of-rest/export` | Export to JSON/PDF/CSV |
| `GET /v1/hours-of-rest/signoffs` | `list_monthly_signoffs` |
| `GET /v1/hours-of-rest/signoffs/details` | `get_monthly_signoff` |
| `GET /v1/hours-of-rest/templates` | `list_crew_templates` |
| `GET /v1/hours-of-rest/warnings` | `list_crew_warnings` |
| `GET /v1/hours-of-rest/sign-chain` | `get_hor_sign_chain` — fleet manager view |

---

## The sign chain — exactly how it works

MLC 2006 requires a three-tier weekly attestation: **crew → HOD → Master (captain)**. This is enforced as a state machine in `sign_monthly_signoff`.

```
draft
  └─(crew signs)→ crew_signed
       └─(HOD signs)→ hod_signed
            └─(master signs)→ finalized
```

**Rules enforced in code:**

1. HOD can only sign from `crew_signed`. Attempting from any other status → 400.
2. Master can only sign from `hod_signed` (normal path) OR from `crew_signed` if no designated HOD exists for the department (bypass path — notifies all vessel HODs).
3. **The same person cannot sign at both HOD and master level on the same signoff.** `hod_signed_by == user_id` check at master signature → 403. This is an MLC requirement for independent verification.
4. `_DEPT_HOD_ROLES = ["chief_engineer", "chief_officer", "chief_steward", "eto", "purser"]` — these are the roles that qualify as a "designated HOD" for the bypass check. captain/manager are excluded intentionally.

**Known gap:** A single captain with no HOD on the vessel can currently sign all three levels (crew, hod, master) on their own signoff because the HOD role check queries `auth_users_roles` for dept-specific HODs, not the signing user themselves. This requires a CEO decision before fixing.

---

## MLC 2006 compliance logic

Located in `upsert_hours_of_rest` (handlers, line ~327):

```python
is_daily_compliant = total_rest_hours >= 10      # ≥10h rest per 24h

has_valid_rest_periods = (
    rest_period_count <= 2 and                    # ≤2 rest periods
    longest_rest_period >= 6                      # longest ≥6h
)

record_is_compliant = is_daily_compliant and has_valid_rest_periods
```

After upsert, the Supabase RPC `check_hor_violations` is called with the new record ID. It creates rows in `pms_crew_hours_warnings`. If the record is a violation, a notification is sent to the crew member's HOD (found via `auth_users_roles` by department).

**Weekly rule (77h)** is tracked in `dash_crew_hours_compliance.is_weekly_compliant`. This is a computed column/view — the backend does not compute it directly during upsert.

---

## Lock / immutability system

Once a week is signed off, the daily records for that week are locked. `upsert_hours_of_rest` checks this before writing:

1. If a **weekly** `pms_hor_monthly_signoffs` row with `status IN ("finalized", "locked")` exists for this user/week → reject with `LOCKED` error.
2. If a **monthly** signoff with `status IN ("finalized", "locked", "captain_signed")` exists for this user/month → reject with `LOCKED` error.

To modify a locked record, a correction must be raised. Corrections create a new linked row in `pms_hours_of_rest` (or a note-only row) and are permanently preserved alongside the original.

---

## Notification hierarchy

Every significant action notifies the appropriate rank level. All notifications are **non-fatal** (try/except, failure never blocks the action).

| Action | Who is notified |
|---|---|
| Violation submitted (upsert) | HOD of crew's department |
| Warning acknowledged | All HOD/captain/manager in crew's department |
| Warning dismissed | The crew member whose warning was dismissed |
| Monthly signoff opened by HOD | The crew member (target_user_id) |
| Weekly signoff signed (crew) | → cascades to HOD on counter-sign queue |
| Undo submitted day | HOD/captain/manager (weekly tally changed) |
| Correction note added by HOD/captain | The crew member whose record was corrected |
| HOD step bypassed (no dept HOD) | All vessel HODs notified |

Notifications use `idempotency_key` on `(yacht_id, user_id, idempotency_key)` to prevent duplicates on retry.

---

## Audit and ledger coverage (as of 2026-04-14)

Every mutating action writes to **both** `pms_audit_log` and `ledger_events`. This is the evidence trail for MLC inspections.

`pms_audit_log` — written by `_write_hor_audit_log()`:
- `upsert_hours_of_rest` (action: `upsert_hours_of_rest:created` or `upsert_hours_of_rest:updated`)
- `sign_monthly_signoff` (action: `sign_monthly_signoff:{level}`)
- `undo_hours_of_rest` (action: `undo_hours_of_rest`, old_values includes prior work_periods)
- `create_hor_correction` (action: `create_hor_correction`)

`ledger_events` — written via `build_ledger_event()`:
- `upsert_hours_of_rest` (event_type: create/update)
- `sign_monthly_signoff` (event_type: approval)
- `create_monthly_signoff` (event_type: create)
- `create_crew_template` (event_type: create)
- `apply_crew_template` (event_type: update)
- `acknowledge_warning` (event_type: status_change)
- `dismiss_warning` (event_type: status_change — includes hod_justification in metadata)

`pms_audit_log` invariant: `signature` column is **NEVER NULL**. Use `{}` for unsigned actions. This is enforced in `_write_hor_audit_log`.

---

## The TimeSlider widget

**File:** `apps/web/src/components/hours-of-rest/TimeSlider.tsx`

Standalone 24-hour work-period input. Can be used independently of the HoR domain.

```typescript
<TimeSlider
  value={workPeriods}           // existing work periods from saved data
  onChange={(periods) => ...}   // called on every change, emits work_periods
  readOnly={day.submitted}      // true = display only, no interaction
/>
```

Interaction model:
- **Click empty track** → creates new 1-hour work block
- **Drag left/right handle** → resize block (snaps to 15-minute increments)
- **Drag block body** → move block
- **× button** → remove block

Internal state uses minutes (0–1440). Exported periods use `"HH:MM"` strings.

`invertToRestPeriods(workPeriods: RestPeriod[]): RestPeriod[]` — exported utility. Converts work blocks to rest gaps. Empty work array returns `[{start: "00:00", end: "24:00"}]` (full rest day, valid MLC).

The `readOnly` prop hides all drag handles and the × button. The submitted day track is shown in a dimmed style.

---

## Response normalization — the gap between API and component

The API responses are not perfectly shaped for the frontend. Each view component has a `normalize*` function that translates API output to component-expected types.

**`MyTimeView.tsx` — `normalizeMyWeekResponse(json)`:**
- `record_date` → `date` (backend field name mismatch)
- Adds `label` (Mon/Tue/..) computed from week_start index
- Maps `is_daily_compliant` → `is_compliant`
- `compliance` object is flat from backend — `mlc_status`, `min_24h`, `min_7d`, `violations_this_month`, `rolling_7d_work` are not always present. The normalizer fills them with defaults.
- `prior_weeks` may be absent (backend feature not fully implemented). Normalizer returns `[]`.

**`DepartmentView.tsx` — normalizer in component body:**
- `submitted_count` from backend → maps to `today_submitted`
- `total_crew` from backend → maps to `today_total`
- Crew names for pending counter-signs are looked up from `crew[]` array by `user_id`, not from `crew_names[]` (which doesn't exist)
- `days[].submitted` is a bool from backend — not `days[].status`. Normalizer maps `submitted: true → status: 'submitted'`
- Compliance summary (`compliant_days`, `total_days`, `violations`, `avg_rest_hours`) are computed from `crew[]` aggregates, not from a `compliance` sub-object

**`VesselComplianceView.tsx` — normalizer in component body:**
- `compliance_pct` per dept: computed as `compliant_count / total_crew * 100`
- `violations` per dept: mapped from `pending_warnings`
- Crew filter uses `d.department` (correct backend field), not `d.name`

**`FleetView.tsx` — `normalizeFleetCompliance(json, fallbackVessels)`:**
- `yacht_name` falls back to `user.fleet_vessels` lookup if backend omits it
- `error: "unavailable"` → maps to `error: true` on the vessel summary

---

## `MyTimeView` is still on mock data

As of 2026-04-14, `MyTimeView.tsx` has a `MOCK_MY_WEEK` constant at the top of the file. This is used as fallback when the API call fails, but the component does wire to the real API (`/api/v1/hours-of-rest/my-week`). The mock is there for development without a running API.

When the API returns successfully, the real data is normalised via `normalizeMyWeekResponse`. If you see a static week showing Apr 7–13 2026, you're seeing the mock.

---

## Handler cache — singleton per tenant

`hours_of_rest_routes.py` caches handler instances:

```python
_hor_handlers_cache = {}

def get_hor_handlers(tenant_key_alias: str):
    if tenant_key_alias not in _hor_handlers_cache:
        ...
    return _hor_handlers_cache[tenant_key_alias]
```

This is a module-level dict. In a multi-worker Uvicorn deployment, each worker has its own cache. In practice, the first request per worker per tenant initialises the handler. This is not a problem but worth knowing if you're debugging "first request slow" issues.

---

## Things I wish I knew at the start

**1. Two separate route files, same URL prefix.**
`hours_of_rest_routes.py` AND `hor_compliance_routes.py` both use `prefix="/v1/hours-of-rest"`. They are registered separately in `main.py`. The compliance routes are purely GET and hit Supabase directly. The main routes delegate to `HoursOfRestHandlers`. If an endpoint returns an unexpected response shape, check which file it's actually in.

**2. `maybe_single()` throws on 0 rows in supabase-py 2.12.0.**
This burned the team multiple times. `result.maybe_single().execute()` raises `APIError(204)` if the query returns 0 rows. Always use `.limit(1).execute()` and check `result.data[0] if result.data else None`. This pattern is now consistently used throughout the HoR handlers. If you see a 500 on a record lookup and the record doesn't exist, this is the bug.

**3. `work_periods` → `rest_periods` inversion.**
Crew inputs work. Backend derives rest. The `rest_periods` field on the request model is ignored. Many assumptions in early code assumed rest was the input. The TimeSlider widget draws work blocks (amber), not rest gaps. `invertToRestPeriods()` exists but is only needed for display of existing records.

**4. `pms_hor_monthly_signoffs` is used for BOTH weekly and monthly sign-offs.**
The `period_type` column (`weekly` | `monthly`) distinguishes them. The frontend primarily uses weekly signoffs for the lock signal. Monthly signoffs are the formal compliance document. Both flow through the same sign chain (crew → hod → master).

**5. `yacht_id` on request bodies is deprecated.**
All mutation request models have `yacht_id` marked `DEPRECATED`. The yacht_id now comes from the JWT auth context, extracted in the route handler. If you send `yacht_id` in the request body it is ignored (not an error). This was a security fix to prevent cross-vessel writes.

**6. The lock check is FATAL on failure.**
In `upsert_hours_of_rest`, the weekly/monthly lock check failure returns a `DATABASE_ERROR`, not a silent pass. This was a deliberate choice: it is better to block a submission than to allow an unchecked write to a potentially locked week. If you see `"Lock check failed"` errors, investigate the DB connection, not the lock logic.

**7. `dash_crew_hours_compliance` is a view, not a table.**
Multiple endpoints read from it to get weekly summaries. Do not INSERT or UPDATE it. It aggregates from `pms_hours_of_rest`. If a crew member's weekly summary looks wrong, check the underlying `pms_hours_of_rest` rows.

**8. The RPC `check_hor_violations` is a DB-side function.**
After every upsert, the backend calls `supabase.rpc("check_hor_violations", {"p_hor_id": record_id})`. This function lives in the Supabase DB (TENANT project). It checks the inserted record against MLC rules and inserts rows into `pms_crew_hours_warnings`. If violations are not being created, check the RPC exists and is working in the tenant DB.

**9. HOD counter-sign queue badge.**
The red badge on the "Department" tab comes from `useHoRUnreadCount()` — a 60-second polling hook that calls `GET /v1/hours-of-rest/notifications/unread`. It only runs if `showDept` is true (i.e., HOD role or above). The count reflects `pms_notifications` unread count, not the pending counter-sign queue directly.

**10. Integration tests use a fixed past date.**
`TEST_WEEK_MONDAY = "2025-01-06"` in `scripts/hor-integration-test/state.py`. This date was chosen as a clean past date with no production data. Do not change it — all 9 scenarios chain their data from this week. The test yacht_id is `85fe1119-b04c-41ac-80f1-829d23322598`.

---

## Common bugs and how to diagnose them

| Symptom | Likely cause | Where to look |
|---|---|---|
| 500 on record fetch | `maybe_single()` on 0 rows | Check if the record exists; look for `.maybe_single()` in the handler |
| Week shows mock data always | API call failing, component falling back | Check browser Network tab for the `/my-week` call |
| "LOCKED" on upsert | Weekly or monthly signoff is finalized | Query `pms_hor_monthly_signoffs` for this user/week |
| Violation not creating warning | `check_hor_violations` RPC issue | Test the RPC directly in Supabase SQL editor |
| Department tab not showing for HOD | Role check in `page.tsx` | `isHODRole()` covers `chief_engineer`, `chief_officer`, `eto` only |
| Counter-sign fails "not yet signed" | Wrong status in `pms_hor_monthly_signoffs` | Check `status` column — HOD can only sign from `crew_signed` |
| HOD and master same person | MLC enforcement | This is intentional — system blocks it with 403 |
| Notifications not arriving | `pms_notifications` idempotency | Check if an identical `idempotency_key` row already exists |
| Compliance summary all zeros | Normalizer not mapping backend fields | Check `normalizeMyWeekResponse` — `mlc_status` may be absent from API |

---

## Interaction with other domains

**Ledger domain** — `ledger_events` table. Every HoR mutation writes a ledger event via `build_ledger_event()` from `routes/handlers/ledger_utils.py`. The ledger panel on entity views reads these events to show HoR activity.

**Notification domain** — `pms_notifications` table. HODs, captains, and crew receive notifications for violations, sign chain events, corrections. The notification centre reads `pms_notifications`. HoR is the heaviest writer.

**Auth domain** — `auth_users_roles` table. Role and department data for every user. The HOD lookup for violation notifications queries this table. The counter-sign role enforcement queries this table. Errors here cascade to HoR silently (try/except guards notifications).

**Audit/Compliance domain** — `pms_audit_log` table. Every mutation writes here. Port state inspectors may request these records. The `signature` column must never be NULL.

**Fleet domain** — `auth_users_roles.vessel_ids` array. Fleet managers manage multiple vessels. `resolve_yacht_id(auth, yacht_id)` validates the requested yacht_id against the user's `vessel_ids`. The `FleetView` iterates `user.fleet_vessels` from the auth context.

---

## Running the integration tests

```bash
# Requires real API and real DB credentials
export SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
export SUPABASE_SERVICE_KEY=...
export HOR_TEST_API_BASE=http://localhost:8000  # or Render URL

cd scripts/hor-integration-test
python3 run.py
```

Expected: `9/9 scenarios passed · 92/92 checks passed`

Teardown runs automatically after every run and deletes all test data for `week_start = 2025-01-06` on yacht `85fe1119`.

---

## Running the Playwright proof screenshots

```bash
export SUPABASE_JWT_SECRET=...
export PROOF_DIR=/tmp/hor-proof  # defaults to ~/hor-proof

cd scripts/hor-proof
npx playwright test --config playwright.config.ts
```

Produces 7–10 screenshots showing each role's view. Used for CEO review and compliance documentation. The spec mints real JWTs and injects them as Supabase localStorage session state.

---

## What is NOT implemented

- **`prior_weeks` in MyTimeView** — the backend doesn't return historical week summaries. The component has a stub UI for it. Returns empty array.
- **Monthly signoff sign-off flow in the frontend** — the signoff cards are present but the full monthly sign-off workflow (multi-month view, bulk signing) is not wired in the frontend. The backend supports it fully.
- **Correction flow in the frontend** — `create_hor_correction` and `request_hor_correction` are implemented in the backend and tested in S9. The frontend shows a "correction requested" banner but doesn't yet wire the full correction submission UI.
- **PDF export** — `export_hours_of_rest` with `format: "pdf"` is an endpoint but the PDF rendering is not fully implemented.
- **The single-person sign-chain gap** — a captain with no designated HOD can technically sign all three levels on their own signoff. Awaiting CEO decision on how to enforce this.
