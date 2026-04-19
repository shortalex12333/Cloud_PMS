# Hours of Rest — Live Scenario Test Guide

> **Status:** CURRENT — reflects PRs #640, #641, #646 + post-live-test bug fixes  
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

Source: `apps/web/src/app/hours-of-rest/page.tsx:84–87`

---

## S1 — Submit Day (compliant, empty = full rest day)

**Login as:** Crew  
**Steps:**
1. Go to Hours of Rest → My Time
2. Select any week with an unsubmitted day
3. Leave the day empty (no work periods) OR add work periods totalling < 14h
4. Click **Submit Day**

**Expected:** Day submits. Empty day = 24h rest = Compliant badge.

**Code citations:**
- Submit button: `MyTimeView.tsx:1024` — `{!isSubmitted && (` — no draft length gate (fixed)
- `submitDay()`: `MyTimeView.tsx:445`
- Work periods default to `[]` if none entered: `hours_of_rest_routes.py:316` — `work_periods = request.work_periods if request.work_periods is not None else []`
- Empty day yields 24h rest: `hours_of_rest_handlers.py:304–320` — `_complement([])` → `[{start:"00:00", end:"24:00", hours:24.0}]`
- `is_daily_compliant = total_rest_hours >= 10`: `hours_of_rest_handlers.py:328`
- Badge render: `MyTimeView.tsx:1136` — `ok={displayDay.is_compliant ?? displayDay.is_daily_compliant ?? null}`

---

## S2 — Submit Day (non-compliant — rest period structure violation)

**Login as:** Crew  
**Steps:**
1. Add 3+ separate work periods (e.g. 00:00–02:00, 06:00–08:00, 14:00–16:00) — this creates 3+ rest windows
2. Click Submit Day

**Expected:** Red **Violation** badge. Day submits.

**Why it's a violation:** MLC 2006 A2.3 requires ≤2 rest periods, with the longer ≥6h.

**Code citations:**
- Period count check: `hours_of_rest_handlers.py:332–335`
  ```python
  has_valid_rest_periods = (
      rest_period_count <= 2 and
      longest_rest_period >= 6
  )
  ```
- `is_daily_compliant` stored: `hours_of_rest_handlers.py:346` — `is_daily_compliant and has_valid_rest_periods`
- Violation badge: `MyTimeView.tsx:1138` — `label='Violation'` when `is_daily_compliant === false`

**Known warning message issue:** `check_hor_violations` SQL RPC creates a warning row. If the only violation is period structure (not total hours), the warning message will say "Daily rest violation: 12.00 hours (minimum 10h required)" — misleading because 12h > 10h. Root is in the Supabase `check_hor_violations` function (not in Python layer). HOD notification body was fixed: `hours_of_rest_handlers.py:511–515`.

---

## S3 — Submit Day (insufficient total rest)

**Login as:** Crew  
**Steps:**
1. Add work periods totalling > 14h (rest < 10h)
2. Click Submit Day

**Expected:** Red **Violation** badge. Warning generated.

**Code citations:**
- `is_daily_compliant = total_rest_hours >= 10`: `hours_of_rest_handlers.py:328`
- Notification body (accurate for this case): `hours_of_rest_handlers.py:511–515`

---

## S4 — Daily compliance badge accuracy

**Login as:** Crew  
**Steps:**
1. Submit a compliant day (rest ≥ 10h, ≤2 periods). Confirm badge says **Compliant**.
2. Submit a non-compliant day. Confirm badge says **Violation**.

**Expected:** Badge reflects server `is_daily_compliant`, not client recalculation.

**Code citations:**
- Load-time remap: `MyTimeView.tsx:66–68`
  ```ts
  const is_compliant = d.is_compliant ?? d.is_daily_compliant ?? null;
  return { ...d, date, label, is_compliant };
  ```

---

## S5 — Apply Template (populates unsubmitted days)

**Login as:** Crew (must have at least one saved personal template)  
**Steps:**
1. Select a template from the dropdown in the Templates section
2. Click **Insert My Template**
3. Verify unsubmitted days show template work blocks

**Expected:** Unsubmitted days populated. Already-submitted days unchanged.

**Code citations:**
- `applyTemplate()`: `MyTimeView.tsx:501`
- Route: `hours_of_rest_routes.py:671` — `POST /templates/apply`
- Handler: `hours_of_rest_handlers.py:1430–1500` — `apply_crew_template()`
- Templates query (user-scoped only): `hor_compliance_routes.py:225–227` — `.eq("user_id", user_id)`

**Note:** The Templates section only appears if the user has saved templates (`data.templates.length > 0`). See S6 to create one.

---

## S6 — Create Template (crew only; fleet manager blocked)

**Login as:** Crew  
**Steps:**
1. In Hours of Rest → My Time, scroll to **My Templates** section
2. Click **+ New Template**
3. Enter a name, click **Save Template**

**Login as:** Fleet Manager  
**Steps:**
1. Go to Hours of Rest → My Time
2. Confirm **My Templates** section / **+ New Template** button is absent

**Expected (crew):** Template saved. Appears in Templates dropdown.  
**Expected (fleet):** Section not rendered.

**Code citations:**
- Gate: `MyTimeView.tsx:204` — `const canCreateTemplate = user?.role !== 'manager'`
- Section gated render: `MyTimeView.tsx` — `{canCreateTemplate && (<SectionCard>…+ New Template…</SectionCard>)}`
- `saveAsTemplate()`: `MyTimeView.tsx` — builds 7-day `schedule_template` from draftPeriods → `POST /templates/create`
- Route: `hours_of_rest_routes.py:634` — `POST /templates/create`
- Handler: `hours_of_rest_handlers.py:1326` — `create_crew_template()` — inserts with `user_id` (not global)

---

## S7 — Submit Week For Approval (crew only; fleet blocked)

**Login as:** Crew  
**Steps:**
1. Submit all 7 days of the current week
2. **Submit Week For Approval** button appears — click it

**Login as:** Fleet Manager  
**Steps:**
1. Go to My Time — confirm button absent

**Expected (crew):** Week signed off.  
**Expected (fleet):** Button absent.

**Code citations:**
- Gate: `MyTimeView.tsx:204` — `const canSubmitWeek = user?.role !== 'manager'`
- Conditional render: `MyTimeView.tsx:927` — `isCurrentWeek && canSubmitWeek`
- Two-step flow (create signoff + sign at crew level): `MyTimeView.tsx:529–558` — `handleSignWeek()`

---

## S8 — HOD: Sign Off for Approval (per-crew)

**Login as:** HOD (eto.test)  
**Pre-condition:** Crew must have submitted a week (run S7 first as crew)  
**Steps:**
1. Go to Hours of Rest → Department tab
2. Find a crew member row — click View
3. See weekly grid and **Sign Off for Approval** button
4. Click → enter signed name → confirm

**Expected:** HOD signature recorded.

**Code citations:**
- Department tab gating: `apps/web/src/app/hours-of-rest/page.tsx:84` — `const showDept = isHODRole(role)`
- `isHODRole()`: `page.tsx:29–33` — `['chief_engineer', 'chief_officer', 'eto']`
- Sign Off button: `DepartmentView.tsx:779` — gated on `pending_counter_signs.find`

---

## S9 — Captain: Department tab absent

**Login as:** Captain  
**Steps:**
1. Go to Hours of Rest
2. Confirm tabs: **My Time** and **All Departments** only
3. Confirm **Department** tab is absent

**Expected:** Captain does not see the HOD-only Department tab.

**Code citations:**
- Tab routing: `page.tsx:84–87`
  ```ts
  const showDept    = isHODRole(role);    // false for captain
  const showVessel  = isCaptainRole(role) || isFleetManagerRole(role);
  ```

---

## S10 — Captain: Sign All blocked until all HODs signed

**Login as:** Captain → All Departments  
**Steps:**
1. Observe Sign All button before all departments are HOD-signed
2. Confirm button is disabled with tooltip

**Expected:** Greyed with tooltip "All departments must be HOD-signed before captain sign-off".

**Code citations:**
- `all_hods_signed` source: `VesselComplianceView.tsx:185`
- Disable gate: `VesselComplianceView.tsx:448–449`

---

## S11 — Fleet Manager: All Departments read-only

**Login as:** Fleet Manager  
**Steps:**
1. Verify tabs: My Time · All Departments · Fleet
2. On My Time: Submit Week For Approval absent, + New Template absent
3. On All Departments: vessel overview only, no sign buttons

**Expected:** Fleet sees but cannot write.

**Code citations:**
- `canSubmitWeek` false for fleet: `MyTimeView.tsx:204`
- `canCreateTemplate` false for fleet: `MyTimeView.tsx:205`
- Fleet tab visible: `page.tsx:86–87`

---

## Known Data State Gaps

| Scenario | Gap | How to unblock |
|----------|-----|---------------|
| S5 template dropdown visible | Requires user to have saved templates (S6 must run first) | Run S6 to create a template |
| S8 HOD Sign Off button visible | Requires crew to have a pending signoff in `pending_counter_signs` | Complete S7 as crew first |
| S10 Captain Sign All enabled | Requires all departments HOD-signed | Complete S8 as HOD across all departments |

---

## Known Open Bugs (not yet fixed in SQL layer)

| Bug | Source | Status |
|-----|--------|--------|
| Warning message "Daily rest violation: 12.00 hours (minimum 10h required)" fires when rest ≥ 10h but period structure violated | `check_hor_violations` Supabase SQL function uses total_rest_hours in message regardless of violation type | HOD notification body fixed in Python; SQL warning message needs DB-level fix |
| Weekly violation warnings may still accumulate if `check_hor_violations` SQL uses daily `record_date` as key | `check_hor_violations` SQL function | Python-layer pre-delete dedup added at `hours_of_rest_handlers.py:432–444` — covers non-DAILY_REST types |

---

## DB Writes Reference

| Table | Written by | Handler location |
|-------|-----------|-----------------|
| `pms_hours_of_rest` | submitDay | `hours_of_rest_handlers.py:369–389` |
| `pms_crew_hours_warnings` | check_hor_violations RPC | `hours_of_rest_handlers.py:434–457` |
| `pms_hor_monthly_signoffs` | create_monthly_signoff | `hours_of_rest_handlers.py:726–850` |
| `pms_crew_normal_hours` | createTemplate | `hours_of_rest_handlers.py:1370–1387` |
| `ledger_events` | every sign / warning / signoff action | `hours_of_rest_handlers.py` — `_write_hor_audit_log()` + `build_ledger_event()` |

---

## SQL Migration Needed

Run on TENANT DB to remove generic seeded templates (no user_id):

```sql
DELETE FROM pms_crew_normal_hours WHERE user_id IS NULL;
```

File: `supabase/migrations/20260419_delete_seeded_global_templates.sql`
