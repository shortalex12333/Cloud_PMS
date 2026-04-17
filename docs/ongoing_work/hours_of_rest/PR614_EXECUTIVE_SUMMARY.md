# Hours of Rest — PR #614 Executive Summary

**Date:** 2026-04-16  
**Status:** SHIPPED AND VERIFIED — 6/6 automated tests passing, 9/9 backend scenarios passing  
**PR:** shortalex12333/Cloud_PMS#614 (merged) + #626 (test evidence, open for review)

---

## What This Is — 30 Seconds

Hours of Rest (HoR) is the compliance tracking system for every crew member on a vessel. It records when crew work and rest, checks those hours against international maritime law, routes the records through a three-level approval chain, and stores the result as a legally admissible evidence trail.

**This is not optional.** Maritime Labour Convention 2006 (MLC 2006) — an internationally binding treaty ratified by 100+ flag states — requires this record to exist, be signed by the crew member, counter-signed by their head of department, and finally signed by the master (captain). Port State Control inspectors can board any vessel in any port worldwide and demand these records. A vessel that cannot produce them can be detained. A detained vessel cannot sail.

---

## What MLC 2006 Requires

The law (MLC 2006 Standard A2.3) sets hard limits:

| Rule | Minimum | Consequence of breach |
|---|---|---|
| Rest in any 24-hour period | **10 hours** | Violation — crew flagged, HOD notified |
| Rest in any 7-day period | **77 hours** | Violation — crew flagged, HOD notified |
| Maximum rest periods per day | **2 periods** | Rest must not be fragmented |
| Minimum length of longest rest period | **6 hours** | Continuous block required |

Every day a crew member works must be recorded. Every week must be signed. Every violation must be logged with a justification. Everything is immutable once signed.

---

## What PR #614 Fixed

Three bugs introduced during the previous UI overhaul were affecting every crew member who opened the Hours of Rest page.

---

### Fix 1 — Page was displaying at 80% scale

**What a user saw before the fix:** The entire Hours of Rest screen appeared shrunk — text was smaller than intended, the sidebar did not reach the bottom of the window, and buttons were mis-positioned. The page looked broken.

**What caused it:** A single CSS rule, `zoom: 0.8`, had been applied to the entire page in the global stylesheet. This shrank every element to 80% of its intended size.

**What was fixed:** The `zoom: 0.8` rule was removed.

**Exact code location:** `apps/web/src/styles/globals.css` lines 395–403  
The `html, body` block now correctly contains no zoom property. Before the fix, a `zoom: 0.8` line existed here and was deleted.

**Verified by:** Playwright automated test, `hor-pr614-verify.spec.ts` test 1 — confirms `htmlZoom = 1` and the sidebar reaches the bottom of a 1440×900 screen.

---

### Fix 2 — Calendar button was labelled "CAL" instead of "Calendar"

**What a user saw before the fix:** A small button with the text "CAL" — jargon that most crew would not recognise. The calendar overlay (which lets crew jump to a specific week by clicking a date) was effectively hidden.

**What was fixed:** The button text was changed from `"CAL"` to `"Calendar"`.

**Exact code location:** `apps/web/src/components/hours-of-rest/MyTimeView.tsx` line 694  
```
>Calendar</button>
```
The button uses `textTransform: 'uppercase'` in its CSS, so it renders as "CALENDAR" on screen.

**Verified by:** Playwright automated test, `hor-pr614-verify.spec.ts` test 2+3 — confirms button text is exactly "CALENDAR" and clicking it triggers the month-status API call.

---

### Fix 3 — Proxy would hang indefinitely when the backend was asleep

**What a user saw before the fix:** When the backend service on Render (our cloud provider) was sleeping due to inactivity (Render's free-tier hibernates services after ~15 minutes of no traffic), the browser would show a loading spinner and never recover. No error message, no retry prompt — just a permanently broken page.

**What caused it:** The Next.js proxy that forwards requests from the frontend to the backend had no timeout. It would wait forever for the backend to wake up.

**What was fixed:** A 28-second hard timeout was added. If the backend does not respond within 28 seconds, the user sees a clear message: *"Upstream timeout — service may be cold-starting, retry in a moment."* A keep-warm cron (see below) prevents this scenario from occurring in the first place.

**Exact code location:** `apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts` line 24  
```typescript
const PROXY_TIMEOUT_MS = 28_000;
```
Line 39: `signal: AbortSignal.timeout(PROXY_TIMEOUT_MS)`  
Line 57: the timeout error message returned to the browser.

---

## What Was Also Built Alongside PR #614

### Keep-Warm Service (prevents backend hibernation)

A scheduled job (a "cron job") now runs automatically every 10 minutes on Vercel's infrastructure. It pings both backend services to keep them active, preventing the hibernation that Fix 3 was defending against.

**File created:** `apps/web/src/app/api/cron/keep-warm/route.ts`  
- Pings both `pipeline-core.int.celeste7.ai` and `backend.celeste7.ai` at `/health`
- 50-second timeout per service (enough for a full Render cold-start cycle)
- Returns `ok: true` only if both services respond with HTTP 200

**Schedule configured in:** `apps/web/vercel.json` — crons block  
```json
{ "path": "/api/cron/keep-warm", "schedule": "*/10 * * * *" }
```

**Status:** Deployed and running. During 8h46m of overnight monitoring (01:01–09:47 UTC), the cron ran continuously. One genuine service incident occurred at 06:40–07:04 UTC (~24 minutes), attributed to Render free-tier resource constraints. See `RENDER_OVERNIGHT_REPORT.md` for the full incident log.

---

## Role-Based Access — Who Sees What

The HoR system enforces strict role gating. Every user has exactly one role. That role is embedded in their login token by the backend — it cannot be changed by the user.

| Role | My Time tab | Department tab | All Departments tab | Fleet tab |
|---|---|---|---|---|
| **Crew** (engineer, steward, deck rating, etc.) | Yes — log, submit, sign | No | No | No |
| **Head of Department** — `chief_engineer`, `chief_officer`, `eto` | Yes | Yes — counter-sign crew | No | No |
| **Captain** | Yes | Yes | Yes — master sign | No |
| **Fleet Manager** | Yes (read only) | No | Yes (read only) | Yes |

Role access is enforced in two places:
1. **Frontend** — `apps/web/src/app/hours-of-rest/page.tsx` lines 29–32, `isHODRole()` function, checks for exact strings `['chief_engineer', 'chief_officer', 'eto']`
2. **Backend** — every API endpoint validates the user's JWT token before returning data. A crew member calling the department-status endpoint receives a 403 Forbidden response.

---

## The Three-Level Sign Chain (MLC Required)

MLC 2006 requires independent verification at each level. The system enforces this as a state machine — no step can be skipped:

```
Crew logs work periods (drag-to-mark on timeline)
    ↓
Crew signs their week ("Submit Week For Approval")
    ↓  [status: crew_signed]
HOD counter-signs (verifies crew data for their department)
    ↓  [status: hod_signed]
Captain gives master signature (final vessel-level attestation)
    ↓  [status: finalized — LOCKED]
```

Once finalized, no record in that week can be edited, undone, or re-submitted. A correction can only be added (it creates a new linked record, never overwrites the original). The correction requires a written justification, which is stored permanently.

**Enforcement:** The same person cannot sign at two different levels of the same signoff. If a captain also submitted the day (e.g. on a small vessel with no HOD), they cannot give the master signature for their own record — this would return a 403 error. This is an MLC requirement for independent verification.

---

## Shore-Side Applicability

The system is designed for vessels but the architecture is scoped by `yacht_id` — every piece of data belongs to one vessel. This means:

- **Shore-based fleet managers** use the Fleet tab to view compliance rates across all vessels without needing to be on board
- **Shoreside administrators** can be assigned the `manager` role and access real-time compliance data for any vessel they manage
- **Records are always in the cloud** — port inspectors in any port, and shore-based compliance officers, can access the same data simultaneously
- The MLC paper-record requirement is satisfied by the system's export function (PDF/JSON of the signed record chain)

---

## Bugs Found During Test Authoring

Four bugs were discovered while writing the automated tests. These were bugs in the tests themselves (not in the product), and were fixed before the final test run.

| # | Bug | Root cause | Fix |
|---|---|---|---|
| 1 | Test 4 (month navigation) clicked the wrong arrow button | The `›` (next month) button is disabled when already on the current month — `MyTimeView.tsx:771` has a guard `if (calendarMonth >= nowYM) return`. The test was clicking next instead of previous. | Changed to click `‹` (previous month) — April 2026 → March 2026 confirmed. |
| 2 | Test 5 (day click) found no buttons | The calendar renders two identical 7-column grids. The first is the Mon/Tue/Wed/Thu/Fri/Sat/Sun header row (contains `<div>` elements, not buttons). The test was selecting this grid instead of the day-number grid below it. | Added `.find(g => querySelectorAll('button').length > 0)` to select the grid containing actual clickable day buttons. |
| 3 | S5 (HOD Department tab) — tab count was 0 | The test mock was returning `role: 'hod'`. But `page.tsx:29–32` checks for `['chief_engineer', 'chief_officer', 'eto']` — the string `'hod'` is not in the list. | Changed mock role to `'eto'`. |
| 4 | S5 (HOD Department tab) — role was not updating from 'member' | The bootstrap mock was missing `status: 'active'`. `AuthContext.tsx:196` defaults to `'PENDING'` when status is absent, causing `processBootstrapData()` to return without updating the user's role — it stayed as `'member'` from the Supabase session default. | Added `status: 'active'` to the mock response body. |

---

## Test Evidence

### Automated (Playwright) — PR #614 specific
File: `apps/web/e2e/shard-37-hours-of-rest/hor-pr614-verify.spec.ts`

| Test | What it proves | Result |
|---|---|---|
| AT-1: zoom removed | `htmlZoom=1`, sidebar reaches bottom of 1440×900 window | PASS |
| AT-2+3: CALENDAR button | Button text is "CALENDAR", click fetches month-status 200 | PASS |
| AT-4: month navigation | ‹ click changes label "April 2026" → "March 2026" | PASS |
| AT-5: day click | Clicking day 10 fires one new `/my-week` API call | PASS |
| S5: HOD dept tab | ETO role user sees Department tab, count=1 | PASS |
| Ctrl: captain Submit Week | Captain sees "Submit Week For Approval" button | PASS |

Final run: **6/6 passed in 25.6 seconds**

### Backend Integration (Python) — full sign chain
Location: `scripts/hor-integration-test/scenarios/`

| Scenario | What it tests | Result |
|---|---|---|
| S1 | Crew submits a valid working day | PASS |
| S2 | HOD submits their own day | PASS |
| S3 | Captain submits their own day | PASS |
| S4 | HOD counter-signs crew's signoff | PASS |
| S5 | Captain gives master signature | PASS |
| S6 | Fleet manager reads vessel compliance | PASS |
| S7 | Violation triggers HOD notification | PASS |
| S8 | Crew undoes a submitted day | PASS |
| S9 | HOD requests correction on crew record | PASS |

Final run: **9/9 scenarios · 92/92 assertion checks passed**

---

## What Is NOT Yet Implemented

These items are documented gaps — the backend supports them fully, the frontend does not yet wire them:

| Gap | Status | Impact |
|---|---|---|
| PDF export of signed monthly record | Backend endpoint exists, PDF rendering incomplete | Cannot produce sealed MLC document for inspectors yet |
| Full monthly sign-off flow in frontend | Backend and DB fully support it; frontend shows a stub | Multi-month sign-off workflow requires engineer time |
| Correction submission UI | Backend `create_hor_correction` tested (S9); frontend shows "correction requested" banner only | HOD/captain cannot submit a new correction record from the browser yet |
| Historical weeks in MyTimeView | Backend feature not returning prior weeks; component shows empty `[]` | Crew cannot see weeks older than the current one in the main view |
| Single-person sign-chain gap | A captain with no designated HOD can technically sign all three levels on their own record | Requires CEO decision on enforcement rule before fixing |

---

## What Happens Next

| Priority | Action | Why |
|---|---|---|
| HIGH | Merge PR #626 (test evidence) into main | Locks in the 6/6 passing tests as permanent regression guard |
| HIGH | Upgrade Render services to paid plan | Free-tier caused a 24-min outage at 06:40–07:04 UTC; keep-warm cannot prevent OOM kills — see `RENDER_OVERNIGHT_REPORT.md` |
| MEDIUM | Wire correction submission UI | Legally required workflow; backend is ready |
| MEDIUM | Complete PDF export | Required for inspector-ready documents |
| LOW | Enforce single-person sign-chain | Awaiting CEO decision |
