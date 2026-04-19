# Hours of Rest — Lens Overview
**What this module is, why it exists, and how it operates**
**Last updated:** 2026-04-17
**Status:** Production (app.celeste7.ai) — all backend and sign chain complete

---

## 1. What It Is (No Jargon)

The Hours of Rest lens is a compliance recording tool for superyacht crew. Every crew member must log how many hours they worked each day. The system derives how many hours of rest they had (24 hours minus work hours), checks whether they met the legal minimum, and routes the record through a three-level approval chain.

It is not a timesheet. It is a legal document. Port State Control can walk aboard any vessel and demand these records. If they are missing, unsigned, or show violations, the vessel can be detained.

---

## 2. The Legal Basis

**MLC 2006 — Maritime Labour Convention, Article A2.3**

Minimum rest requirements:
- At least **10 hours of rest in any 24-hour period**
- At least **77 hours of rest in any 7-day period**
- Rest must not be split into more than **2 periods**, the longer of which must be at least **6 hours**
- Records must be **signed by the crew member and the master** at the end of each month

Violations — insufficient rest, unsigned records — must be flagged, reported to the Head of Department, and retained for inspection for at least 12 months.

---

## 3. How It Works (The Flow)

```
Crew logs WORK hours via slider (each day, Mon–Sun)
           ↓
Backend derives rest = 24h − work, checks compliance
           ↓
If rest < 10h: MLC violation warning created
           ↓
Crew signs their weekly record ("Sign My Hours")
           ↓
Head of Department (HOD) counter-signs
           ↓
Captain master-signs → record is FINALIZED (immutable)
           ↓
Locked: no edits allowed. Audit trail preserved in ledger_events.
```

---

## 4. Who Sees What

| Role | Tab(s) visible | What they can do |
|------|---------------|-----------------|
| Crew | My Time | Log work hours, sign their own record, acknowledge warnings |
| HOD (chief_engineer, eto, chief_officer, chief_steward, purser) | My Time + Department | Counter-sign crew records, dismiss violation warnings |
| Captain / Manager | My Time + Department + All Departments | Master-sign (finalize) records, view vessel-wide compliance |
| Fleet Manager | My Time + Fleet | Read-only across vessels. No signing, no submitting. |

Role gating source: `apps/web/src/app/hours-of-rest/page.tsx`

---

## 5. The Sign Chain

```
draft
  └─ crew signs own record only → crew_signed
        └─ HOD counter-signs → hod_signed
              └─ captain master-signs (must be different person from HOD) → finalized ← IMMUTABLE
```

Rules enforced in backend (`apps/api/handlers/hours_of_rest_handlers.py:927–1030`):
- Crew cannot sign as HOD or master
- HOD cannot sign before crew has signed
- Captain cannot sign before HOD has signed
- The **same person cannot sign as both HOD and master** — MLC 2006 requires independent verification at each level
- Once `finalized`, no further changes are possible — not by crew, not by captain, not by admin

---

## 6. The Slider (How Work Hours Are Entered)

`apps/web/src/components/hours-of-rest/TimeSlider.tsx`

- The slider shows a 24-hour timeline (00:00 → 23:59)
- The crew member drags to mark **WORK blocks** (amber/black)
- Empty slider = 24 hours rest (valid for a day off)
- Overlapping blocks are collapsed by the backend
- The frontend emits `work_periods: [{start: "HH:MM", end: "HH:MM"}]`
- The backend derives `rest_periods` as the complement and stores both
- `total_work_hours + total_rest_hours` must always equal 24.0

---

## 7. Data Storage

Three database tables (all in the tenant Supabase DB — project `vzsohavtuotocgrfkfyd`):

| Table | Purpose |
|-------|---------|
| `pms_hours_of_rest` | One row per crew member per day. Stores `work_periods`, `rest_periods`, `total_rest_hours`, compliance flags |
| `pms_hor_monthly_signoffs` | One row per crew member per month. Tracks sign chain status: `draft → crew_signed → hod_signed → finalized` |
| `pms_crew_hours_warnings` | MLC violation alerts. Created by backend on upsert when rest < 10h. HOD can dismiss with justification |

---

## 8. Backend Files (Where the Logic Lives)

| File | Purpose |
|------|---------|
| `apps/api/handlers/hours_of_rest_handlers.py` | All business logic: upsert, sign chain, lock enforcement, notifications, violation detection |
| `apps/api/routes/hours_of_rest_routes.py` | REST endpoints: upsert, sign, create-signoff, undo, warnings |
| `apps/api/routes/hor_compliance_routes.py` | Read endpoints: `my-week`, `department-status`, `vessel-compliance`, `month-status` |
| `apps/api/pipeline_service.py:454–466` | Route registration — both HoR routers registered here |

---

## 9. Frontend Files

| File | Purpose |
|------|---------|
| `apps/web/src/app/hours-of-rest/page.tsx` | Main page — role gating, tab visibility |
| `apps/web/src/components/hours-of-rest/TimeSlider.tsx` | 24h work-block slider |
| `apps/web/src/components/hours-of-rest/MyTimeView.tsx` | Crew daily view — week grid, submit, sign |
| `apps/web/src/components/hours-of-rest/DepartmentView.tsx` | HOD view — dept crew grid, pending counter-signs |
| `apps/web/src/components/hours-of-rest/VesselComplianceView.tsx` | Captain view — vessel-wide compliance |
| `apps/web/src/components/hours-of-rest/FleetView.tsx` | Fleet Manager view — multi-vessel (skeleton only, API not wired) |
| `apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts` | Next.js proxy — forwards all HoR calls to Python API |

---

## 10. What Is Complete vs What Remains

### Complete
- All backend handlers, sign chain, lock enforcement
- Violation detection and warning system
- Role gating (crew/HOD/captain/fleet manager)
- MLC independence check (same person cannot sign both HOD and master)
- Full ledger trail — every mutation writes to `ledger_events`
- Calendar view (month-level day-by-day compliance colour grid)
- Department and vessel compliance views
- Warning acknowledge (crew) and dismiss (HOD/captain)
- E2E test suite: 20/22 pass, 2 skipped (known: browser auth injection limitation)
- All manual test scenarios verified (see `HOR_MANUAL_TEST_STATUS.md`)

### Not Complete
- `FleetView.tsx` — never calls API, shows loading skeleton only
- `signoffs/page.tsx` — bypasses Next.js proxy, calls backend directly (BFF auth guard not applied)
- HOD self-completion gap — a user with `captain` role can sign all three levels solo (sign chain allows it because "captain" satisfies the master-sign gate)
- `total_rest_hours` backfill — rows inserted before 2026-04-13 have stale stored totals; frontend works around this by computing from periods arrays
- **HoR PDF export (Receipt Layer)** — HMAC01's task. The data is clean and the sign chain is verified. The sealing pipeline and PDF builder are not yet built for this domain. See `docs/ongoing_work/HMAC/` for the Receipt Layer architecture.

---

## 11. Test Credentials

| Role | Email | Password |
|------|-------|----------|
| Crew | engineer.test@alex-short.com | Password2! |
| HOD (ETO) | eto.test@alex-short.com | Password2! |
| Captain | x@alex-short.com | Password2! |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! |

Frontend: https://app.celeste7.ai
API: https://pipeline-core.int.celeste7.ai
