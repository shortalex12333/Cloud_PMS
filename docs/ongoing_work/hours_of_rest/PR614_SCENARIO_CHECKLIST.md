# Hours of Rest — PR #614 Scenario Checklist

**PR:** shortalex12333/Cloud_PMS#614 (merged) + #626 (test files)  
**Date:** 2026-04-16  
**Overall status: 6/6 automated · 9/9 backend · ALL PASS**

---

## How To Use This Document

- **Section A** — Automated tests. Already run by the test suite. Tick the box to confirm you've seen the passing result. No browser needed.
- **Section B** — Manual browser steps. Follow the steps yourself to verify the sign chain works end-to-end. Complete in order — each step depends on the previous.
- **Section C** — Role gate spot checks. Open the app in a browser with each role's login and confirm the correct tabs appear.
- **Section D** — Backend integration. Run by the engineering team. Tick to confirm you've seen the passing output.

---

## Login Credentials

| Role | Email | Password | Notes |
|---|---|---|---|
| Crew | engineer.test@alex-short.com | Password2! | Deck/engine rating |
| HOD (ETO) | eto.test@alex-short.com | Password2! | Head of Department — Electrical |
| Captain | x@alex-short.com | Password2! | Vessel master |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! | Shore-side / fleet oversight |

**Site:** https://app.celeste7.ai  
**HoR page:** https://app.celeste7.ai/hours-of-rest

---

## Section A — Automated Tests (Playwright)

All 6 run automatically on every deploy against the live production site.  
Test file: `apps/web/e2e/shard-37-hours-of-rest/hor-pr614-verify.spec.ts`  
Config: `apps/web/e2e/shard-37-hours-of-rest/pr614.config.ts`

To run manually:
```
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
node_modules/.bin/playwright test --config e2e/shard-37-hours-of-rest/pr614.config.ts --reporter=line
```

---

**[ ] AT-1 — Page fills the full viewport (zoom removed)**  
Status: **PASS** · `hor-pr614-verify.spec.ts` test 1  
What was fixed: `zoom: 0.8` removed from `apps/web/src/styles/globals.css` lines 395–403  
Evidence: `[PR614-1] htmlZoom=1 vp=1440x900 sidebarBot=900`  
What it means: the page fills the entire 1440×900 window, sidebar reaches the bottom

---

**[ ] AT-2 — "CALENDAR" button exists on the My Time view**  
Status: **PASS** · `hor-pr614-verify.spec.ts` test 2+3  
What was fixed: button text changed from `"CAL"` to `"Calendar"` at `MyTimeView.tsx:694`  
Evidence: `[PR614-2] button raw="Calendar" norm="CALENDAR"`  
What it means: crew can find and identify the calendar button

---

**[ ] AT-3 — CALENDAR button opens the month grid**  
Status: **PASS** · (same test as AT-2)  
Evidence: `[PR614-3] month-status hits: [200]`  
What it means: clicking the button successfully loads month data from the backend

---

**[ ] AT-4 — Month navigation (‹ previous) changes the displayed month**  
Status: **PASS** · `hor-pr614-verify.spec.ts` test 4  
Evidence: `[PR614-4] "April 2026" → "March 2026"`  
What it means: crew can navigate backward to see past weeks in the calendar

---

**[ ] AT-5 — Clicking a day in the calendar reloads the week view for that week**  
Status: **PASS** · `hor-pr614-verify.spec.ts` test 5  
Evidence: `[PR614-5] day target: {"text":"10","x":984,"y":250.25}` → `new my-week calls: 1`  
What it means: clicking any day in the calendar loads the correct week's data

---

**[ ] AT-6a — HOD role sees the "Department" tab**  
Status: **PASS** · `hor-pr614-verify.spec.ts` test S5  
Evidence: `[S5] HOD dept-tab count: 1`  
What it means: users with head-of-department roles (chief_engineer, chief_officer, eto) can access their department crew grid for counter-signing

---

**[ ] AT-6b — Captain sees "Submit Week For Approval" button**  
Status: **PASS** · `hor-pr614-verify.spec.ts` (positive control)  
Evidence: `[ctrl] captain Submit Week: true` · buttons: `["My Time","Department","All Departments","‹","›","Calendar","Submit Week For Approval"]`  
What it means: captain can submit their own week AND has access to all tabs (My Time, Department, All Departments)

---

## Section B — Manual Sign Chain Verification

Complete these in order. Use the login credentials above.  
Each step depends on the previous. Allow 2–3 minutes per step.

---

**[ ] MT-1 — Crew logs and submits a working day**

Login as: `engineer.test@alex-short.com` (crew)

Steps:
1. Go to https://app.celeste7.ai/hours-of-rest
2. You should see the **My Time** view with a week grid (Mon–Sun)
3. Find a day that shows no hours logged (a blank timeline bar)
4. Click anywhere on the timeline bar to add a work block — two handles appear
5. Drag the handles to set start/end time (e.g. 08:00–17:00)
6. Click **Submit Day** below that day's row

Expected outcome:
- The day updates to show e.g. "9h work / 15h rest"
- A green "Compliant ✓" indicator appears (if rest ≥ 10h)
- The timeline bar turns solid (submitted state)
- Total work + total rest = 24h

---

**[ ] MT-2 — Crew submits the week for HOD approval**

Login as: `engineer.test@alex-short.com` (crew)  
Requires: MT-1 complete

Steps:
1. On the Hours of Rest page (My Time view)
2. Find the **Submit Week For Approval** button in the week header
3. Click it — a sign-off card appears below the week grid
4. In the sign-off card, click **Sign My Hours**
5. A signature panel appears — enter your name or initials and confirm

Expected outcome:
- The sign-off card status changes to "Crew Signed"
- The "Sign" button disappears or becomes greyed out
- The week is now locked for crew editing — the Submit Day buttons are disabled

---

**[ ] MT-3 — HOD counter-signs the crew submission**

Login as: `eto.test@alex-short.com` (HOD / ETO)  
Requires: MT-2 complete

Steps:
1. Go to https://app.celeste7.ai/hours-of-rest
2. Click the **Department** tab (visible only to HOD roles)
3. Find **Engineer Test** in the crew grid
4. The sign-off card for this crew member should show status "Crew Signed"
5. Click **Counter-Sign** on that card
6. Enter your name/initials, confirm

Expected outcome:
- Sign-off card status → "HOD Signed"
- A notification is sent to the captain (visible in their notification bell)
- Counter-sign button disappears

---

**[ ] MT-4 — Captain gives master (final) signature**

Login as: `x@alex-short.com` (captain)  
Requires: MT-3 complete

Steps:
1. Go to https://app.celeste7.ai/hours-of-rest
2. Click the **All Departments** tab (visible only to captain/fleet manager)
3. Find the department containing Engineer Test — it should show a HOD-signed pending item
4. Click into the crew view for that department
5. Find the sign-off card with status "HOD Signed"
6. Click **Finalize** / **Master Sign**
7. Enter your name/initials, confirm

Expected outcome:
- Sign-off card status → "Finalized" with a green badge
- No further sign, submit, or undo buttons visible on this week
- The record is now locked — an MLC-compliant signed chain exists

---

**[ ] MT-5 — Verify the finalized record is immutable**

(Observe during or immediately after MT-4)

Expected outcome:
- On the finalized week: no **Submit Day** buttons
- No **Undo** option on any day in the week
- No **Sign** button on the sign-off card
- A "Finalized" or "Locked" badge is visible
- Attempting to edit a submitted day should be blocked

This immutability is the MLC compliance guarantee — finalized records cannot be altered, only corrected with a written justification.

---

## Section C — Role Gate Spot Checks

Quick in-browser checks. Not required if AT-6a and AT-6b passed.

---

**[ ] RC-1 — Crew cannot see the Department tab**

Login as: `engineer.test@alex-short.com` (crew)  
Steps: Go to https://app.celeste7.ai/hours-of-rest  
Expected: Only **My Time** tab is visible. No "Department", "All Departments", or "Fleet" tab.

---

**[ ] RC-2 — Fleet manager has no submit or sign buttons**

Login as: `fleet-test-1775570624@celeste7.ai` (fleet manager)  
Steps: Go to https://app.celeste7.ai/hours-of-rest  
Expected:
- The **Fleet** tab is visible
- On **My Time** view: no **Submit Day**, **Submit Week**, or **Sign** buttons visible
- Fleet manager can view compliance data but cannot modify or sign any record

---

**[ ] RC-3 — HOD cannot see All Departments tab**

Login as: `eto.test@alex-short.com` (HOD/ETO)  
Steps: Go to https://app.celeste7.ai/hours-of-rest  
Expected: **My Time** and **Department** tabs visible. **All Departments** tab is NOT visible. Only captains and fleet managers can see the full vessel overview.

---

## Section D — Backend Integration Scenarios

Run by engineering. Not manual browser steps.  
Location: `scripts/hor-integration-test/`  
Run command: `cd scripts/hor-integration-test && python3 run.py`  
Expected: `9/9 scenarios passed · 92/92 checks passed`

| # | Scenario | Status |
|---|---|---|
| **[ ]** S1 | Crew submits a valid working day — record created, rest calculated automatically | PASS |
| **[ ]** S2 | HOD submits their own day | PASS |
| **[ ]** S3 | Captain submits their own day | PASS |
| **[ ]** S4 | HOD counter-signs crew's weekly signoff | PASS |
| **[ ]** S5 | Captain gives master signature (requires S4 complete) | PASS |
| **[ ]** S6 | Fleet manager reads vessel compliance data (requires S5 complete) | PASS |
| **[ ]** S7 | Submitting a violation triggers an HOD notification | PASS |
| **[ ]** S8 | Crew undoes a submitted day (before finalisation) | PASS |
| **[ ]** S9 | HOD adds a correction note to a crew record | PASS |

---

## Overnight Regression Watch

The automated tests were run every 30 minutes from 01:01 to 09:47 UTC on 2026-04-17 (18 consecutive runs). All 10/10 tests passed on every run. No regressions. The keep-warm cron and mock-based test isolation both performed as designed.

Full infrastructure incident log: `RENDER_OVERNIGHT_REPORT.md`
