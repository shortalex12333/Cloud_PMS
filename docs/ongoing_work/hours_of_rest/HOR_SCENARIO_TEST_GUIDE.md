# Hours of Rest — Live Scenario Test Guide

> **Supersedes:** `HOR_MANUAL_TEST_GUIDE.md`, `HOR_MANUAL_TEST_STATUS.md`, `HOR_TEST_CHEATSHEET.md`  
> **Status:** CURRENT — reflects PRs #640, #641, #646 merged to main  
> **Live commit:** `63eeeb0f` (hotfix: registry optional_fields)  
> **Vercel:** https://app.celeste7.ai  
> **API:** https://pipeline-core.int.celeste7.ai  
> **Last updated:** 2026-04-19

---

## Test Accounts

| Role | Email | Password |
|------|-------|---------|
| Crew | engineer.test@alex-short.com | Password2! |
| HOD (Chief Engineer) | eto.test@alex-short.com | Password2! |
| Captain | x@alex-short.com | Password2! |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! |

**Yacht:** M/Y Test Vessel — `85fe1119-b04c-41ac-80f1-829d23322598`

---

## Navigation by Role

| Role | Tabs visible |
|------|-------------|
| Crew | My Time |
| HOD (chief_engineer / chief_officer / eto) | My Time · Department |
| Captain | My Time · All Departments |
| Fleet Manager | My Time · All Departments · Fleet |

Source: `apps/web/src/app/hours-of-rest/page.tsx:82–87`

---

## S1 — Submit Day (compliant)

**Login as:** Crew  
**Steps:**  
1. Go to Hours of Rest → My Time
2. Select current week
3. Set work periods totalling < 14h (ensures rest ≥ 10h)
4. Click Submit Day on any unsubmitted day

**Expected:** Day row turns green. `StatusBadge` shows **Compliant**.

**Code citations:**
- Submit button: `MyTimeView.tsx:1167`
- `submitDay()` function: `MyTimeView.tsx:439`
- Payload build: `MyTimeView.tsx:451` — `{ record_date, work_periods }`
- Route: `hours_of_rest_routes.py:291` — `POST /api/v1/hours-of-rest/upsert`
- Model: `hours_of_rest_routes.py:115` — `UpdateHoursRequest`
- Compliance engine: `hours_of_rest_handlers.py:486–501` — `_check_rolling_24h_compliance()` + `is_daily_compliant`
- Badge render: `MyTimeView.tsx:1131` — `ok={displayDay.is_compliant ?? displayDay.is_daily_compliant ?? null}`
- Server-authoritative patch after submit: `MyTimeView.tsx:500` — `is_compliant: record.is_daily_compliant ?? compliance?.is_daily_compliant ?? null`

---

## S2 — Submit Day (non-compliant, no comment → VALIDATION_ERROR)

**Login as:** Crew  
**Steps:**  
1. Set work periods totalling > 14h (rest < 10h)
2. Click Submit Day — do NOT type in any comment box

**Expected:** A red-bordered textarea appears beneath the day row with placeholder text "MLC required: explain why rest requirement could not be met…". Day is NOT submitted.

**Code citations:**
- Backend guard: `hours_of_rest_handlers.py:508–514`
  ```python
  crew_comment = payload.get("crew_comment", "").strip()
  if not is_daily_compliant and not crew_comment:
      builder.set_error("VALIDATION_ERROR", "A crew comment (justification) is required…")
  ```
- Frontend catches VALIDATION_ERROR: `MyTimeView.tsx:480–484`
- `commentRequired` state set: `MyTimeView.tsx:483` — `setCommentRequired(prev => ({ ...prev, [date]: true }))`
- Textarea renders: `MyTimeView.tsx:1214–1238` — `{!isReadOnly && commentRequired[day.date] && (<textarea …>)}`
- Textarea placeholder: `MyTimeView.tsx:1217`

---

## S3 — Submit Day (non-compliant, WITH comment → accepted)

**Login as:** Crew (continue from S2 — textarea now visible)  
**Steps:**  
1. Type a justification in the revealed textarea (e.g. "Emergency manoeuvre required")
2. Click Submit Day again

**Expected:** Day submits. Red **Violation** badge displayed.

**Code citations:**
- Comment read: `MyTimeView.tsx:443` — `const crewComment = crewComments[date] ?? ''`
- Conditional include: `MyTimeView.tsx:452` — `if (crewComment.trim()) body.crew_comment = crewComment.trim()`
- Route receives field: `hours_of_rest_routes.py:130` — `crew_comment: Optional[str] = Field(None, …)`
- Written to DB: `hours_of_rest_handlers.py:528` — `"crew_comment": crew_comment or None`
- Violation badge: `MyTimeView.tsx:1133` — label `'Violation'` when `is_daily_compliant === false`

---

## S4 — Daily compliance badge accuracy

**Login as:** Crew  
**Steps:**  
1. Submit a compliant day (rest ≥ 10h). Confirm badge says **Compliant**.
2. Submit a non-compliant day with comment (rest < 10h). Confirm badge says **Violation**.

**Expected:** Badge reflects server `is_daily_compliant`, not client recalculation. No mismatch.

**Code citations:**
- Load-time remap: `MyTimeView.tsx:66–68`
  ```ts
  const is_compliant = d.is_compliant ?? d.is_daily_compliant ?? null;
  return { ...d, date, label, is_compliant };
  ```
- Badge: `MyTimeView.tsx:1131–1136` — uses `displayDay.is_compliant ?? displayDay.is_daily_compliant`

---

## S5 — Apply Template (draft persists without page reload)

**Login as:** Crew  
**Steps:**  
1. Select a template from the dropdown (e.g. "Day Watch (06:00–18:00)")
2. Click Apply
3. Verify the time slider populates for all unsubmitted days
4. Navigate away and back — confirm slider still shows template hours

**Expected:** All unsubmitted days show the template work blocks. Already-submitted days unchanged. No blank state.

**Code citations:**
- `applyTemplate()`: `MyTimeView.tsx:556`
- New GET endpoint for fetching template work_periods before apply: `MyTimeView.tsx:566–572` → `GET /api/v1/hours-of-rest/templates/{template_id}`
- Route: `hours_of_rest_routes.py:636` — `@router.get("/templates/{template_id}")`
- Handler: `hours_of_rest_handlers.py` — `get_crew_template()` method
- Draft state set directly (no reload): `MyTimeView.tsx:590–600`
  ```ts
  for (const day of (data as any).days ?? []) {
    if (day && !day.submitted && !submittedDays[day.date]) {
      newDraft[day.date] = templateWorkPeriods;
    }
  }
  setDraftPeriods(prev => ({ ...prev, ...newDraft }));
  ```

---

## S6 — Create Template (crew/HOD only; fleet manager blocked)

**Login as:** Crew  
**Steps:**  
1. In Templates section, see `+ Create Template` button
2. Click → form opens: name, description, work start/end
3. Fill in and submit

**Login as:** Fleet Manager  
**Steps:**  
1. Go to Hours of Rest → My Time → Templates section
2. Confirm `+ Create Template` button is **absent**

**Expected (crew):** Template created, appears in dropdown.  
**Expected (fleet):** Button does not exist in DOM.

**Code citations:**
- Gate constant: `MyTimeView.tsx:212`
  ```ts
  const canCreateTemplate = user?.role !== 'manager';
  // MLC 2006 Reg 2.3 independence: fleet managers must not write crew schedule data
  ```
- Conditional render: `MyTimeView.tsx:1254` — `{canCreateTemplate && (<button>+ Create Template</button>)}`
- Form section: `MyTimeView.tsx:1328–1418`
- Submit: `MyTimeView.tsx:616` — `createTemplate()` → `POST /api/v1/hours-of-rest/templates/create`

---

## S7 — Submit Week For Approval (crew only; fleet blocked)

**Login as:** Crew  
**Steps:**  
1. Submit all 7 days of the current week
2. "Submit Week For Approval" button appears — click it

**Login as:** Fleet Manager  
**Steps:**  
1. Go to My Time — confirm "Submit Week For Approval" button is **absent**

**Expected (crew):** Week signed off, status updates.  
**Expected (fleet):** Button absent entirely.

**Code citations:**
- Gate: `MyTimeView.tsx:210` — `const canSubmitWeek = user?.role !== 'manager'`
- Conditional render: `MyTimeView.tsx:866` — `isCurrentWeek && canSubmitWeek ? (…button…) : null`
- Button label: `MyTimeView.tsx:885` — `Submit Week For Approval`
- Sign week calls `create_monthly_signoff` via action bus: `MyTimeView.tsx:660` — `signWeek()`

---

## S8 — HOD: Sign Off for Approval (per-crew)

**Login as:** HOD (eto.test)  
**Pre-condition:** Crew must have submitted a week (run S7 first as crew)  
**Steps:**  
1. Go to Hours of Rest → Department tab
2. Find a crew member row — click View
3. See their weekly grid and "Sign Off for Approval" button
4. Click it → enter signed name → confirm

**Expected:** HOD signature recorded. Crew row shows HOD-signed badge.

**Code citations:**
- Department tab gating: `page.tsx:85` — `const showDept = isHODRole(role)`
- `isHODRole()`: `page.tsx:29–33` — `['chief_engineer', 'chief_officer', 'eto']`
- Sign Off button: `DepartmentView.tsx:779` — gated on `data.pending_counter_signs.find(p => p.crew_user_id === viewingUserId)`
- Sign popup: `DepartmentView.tsx:715–750`
- Pending sign-offs data shape: `DepartmentView.tsx:65` — `pending_counter_signs: PendingSignoff[]`

---

## S9 — Captain: Department tab absent

**Login as:** Captain (x@alex-short.com)  
**Steps:**  
1. Go to Hours of Rest
2. Confirm tabs visible: **My Time** and **All Departments** only
3. Confirm **Department** tab is absent

**Expected:** Captain does not see the HOD-only Department tab. BUG-641-7 fix.

**Code citations:**
- Tab routing: `page.tsx:84–87`
  ```ts
  // Captain sees My Time + All Departments only. Department tab is HOD-only.
  const showDept    = isHODRole(role);          // false for captain
  const showVessel  = isCaptainRole(role) || isFleetManagerRole(role);
  ```
- `isCaptainRole()`: `page.tsx:35–37` — `role === 'captain'`

---

## S10 — Captain: Sign All blocked until all HODs signed

**Login as:** Captain  
**Navigate to:** All Departments  
**Steps:**  
1. Observe Sign All button when departments are NOT all HOD-signed
2. Confirm button is disabled (greyed) with tooltip

**Expected:** Button disabled with tooltip: "All departments must be HOD-signed before captain sign-off". Only enables once `all_hods_signed = true`.

**Code citations:**
- `all_hods_signed` source: `VesselComplianceView.tsx:185` — `all_hods_signed: raw.sign_chain?.all_hods_signed ?? false`
- Disable gate: `VesselComplianceView.tsx:448–449`
  ```ts
  disabled={signingAll || !sc.all_hods_signed}
  title={sc.all_hods_signed ? undefined : 'All departments must be HOD-signed before captain sign-off'}
  ```
- Colour token: `VesselComplianceView.tsx:453–455` — `var(--green-strong)` when ready, `var(--txt-ghost)` when not

---

## S11 — Fleet Manager: All Departments read-only

**Login as:** Fleet Manager  
**Steps:**  
1. Go to Hours of Rest
2. Verify tabs: My Time · All Departments · Fleet
3. On My Time: Submit Week For Approval absent, + Create Template absent
4. On All Departments: vessel-level overview only, no sign buttons

**Expected:** Fleet sees but cannot write. All crew write actions gated away.

**Code citations:**
- Fleet gets Vessel view: `page.tsx:87` — `const showFleet = isFleetManagerRole(role)`
- Fleet tab: `page.tsx:86` — `const showVessel = isCaptainRole(role) || isFleetManagerRole(role)`
- `canSubmitWeek` false for fleet: `MyTimeView.tsx:210`
- `canCreateTemplate` false for fleet: `MyTimeView.tsx:212`
- Sign All unavailable: captain-only button path in `VesselComplianceView.tsx`

---

## Known Data State Gaps (Not Code Bugs)

| Scenario | Gap | How to unblock |
|----------|-----|---------------|
| S8 HOD Sign Off button visible | Requires crew to have a pending signoff in `pending_counter_signs` | Complete S7 as crew first, then log in as HOD |
| S10 Captain Sign All enabled | Requires all departments HOD-signed | Complete S8 as HOD across all departments |
| Weekly violation warning | Requires 7 days with cumulative rest < 77h | Submit 7 low-rest days as crew (< 11h rest/day each) |
| Second captain sign-chain test | Only one captain test account | Not testable — S7 API chain proven in previous session |

---

## DB Writes Reference

| Table | Written by | Handler location |
|-------|-----------|-----------------|
| `pms_hours_of_rest` | submitDay | `hours_of_rest_handlers.py:527–533` |
| `pms_crew_hours_warnings` | non-compliant upsert | same handler, post-upsert |
| `pms_hor_monthly_signoffs` | create_monthly_signoff | sign handler |
| `ledger_events` | every sign / warning / signoff action | `_write_hor_audit_log()` |
| `pms_crew_normal_hours` | createTemplate | template handler |

---

## PR History (what each PR fixed)

| PR | Merged | Summary |
|----|--------|---------|
| #567–#596 | 2026-04-16 | Initial MLC 2006 HoR domain — 11 scenarios, database schema, sign chain |
| #640 | 2026-04-19T00:13Z | MLC compliance engine, crew comment, forward scheduling, weekly calc, template persistence, HOD sign-off UI, captain tab fix, fleet gates, cleanup |
| #641 | 2026-04-19T00:15Z | Certificate 10-bug fix batch (rebased on #640) |
| #646 | 2026-04-19T01:14Z | Hotfix: `registry.py:1643` invalid `optional_fields=[]` kwarg removed — action bus P0 routes restored |
