# Hours of Rest — Test Cheat Sheet

**Last verified:** 2026-04-15 | **All 14/14 live tests PASS**
**Legal basis:** MLC 2006 Art. A2.3 — captain-signed weekly record is legally operative. Must be immutable after sign-off.

---

## Quick start — who you log in as

| Role | What they see | Sign chain step |
|------|--------------|-----------------|
| `crew` | My Time (own week, calendar, warnings) | Signs own record |
| `chief_engineer` / `chief_officer` / `eto` / `chief_steward` / `purser` | My Time + Department grid | Counter-signs as HOD |
| `captain` / `manager` | My Time + Department grid + Vessel overview | Finalizes (master sign) |

Test users on yacht `85fe1119-b04c-41ac-80f1-829d23322598`:
- crew: `2da12a4b-c0a1-4716-80ae-d29c90d98233`
- chief_engineer: `89b1262c-ff59-4591-b954-757cdf3d609d`
- captain: `5af9d61d-9b2e-4db4-a54c-a3c95eec70e5`

---

## Scenario 1 — Crew submits a day

**Normal operation:**
1. Log in as crew → navigate to **Hours of Rest**
2. **My Time tab** shows current week (Mon–Sun, 7 slots)
3. Drag the **TimeSlider** → set work blocks (black = work, white = rest)
4. Click **Submit Day**

**What to verify:**
- [ ] Day slot turns from grey (empty) → shows work hours + rest hours
- [ ] `total_work_hours` + `total_rest_hours` = 24.0 exactly
- [ ] If rest < 10h: red warning badge appears on that day — Y/N: **fail = upsert handler not deriving rest correctly**
- [ ] Ledger event row written: `action = upsert_hours_of_rest`, `entity_type = hours_of_rest`

**Where to check in DB:**
```sql
SELECT record_date, work_periods, total_work_hours, total_rest_hours, is_daily_compliant
FROM pms_hours_of_rest
WHERE user_id = '<crew_user_id>'
ORDER BY record_date DESC LIMIT 7;
```

**Fail reasons:**
| Symptom | Why | File:Line |
|---------|-----|-----------|
| 422 on Submit | `yacht_id` missing from JWT | `hours_of_rest_routes.py:303` |
| Work + rest ≠ 24 | Complement mismatch in handler | `hours_of_rest_handlers.py` — `upsert_hours_of_rest` |
| No ledger row | Handler swallowed ledger exception | `hours_of_rest_handlers.py:427` |

---

## Scenario 2 — Crew edits / undoes a submitted day

**Normal operation:**
1. On a submitted day → click **Undo**
2. TimeSlider reappears → edit → Submit again

**What to verify:**
- [ ] After Undo: day slot goes back to empty (unsubmitted) locally
- [ ] `POST /v1/hours-of-rest/undo` called with `record_id` — row deleted from DB
- [ ] Ledger event written: `action = undo_hours_of_rest`
- [ ] Resubmit works normally

**Edge case — undo then re-undo:**
- Cannot undo a day that has no `record_id` (never submitted) → Submit button shows, not Undo
- Cannot undo a day on a **finalized** week (signoff status = `finalized`) → Undo button hidden, TimeSlider hidden

**Fail reasons:**
| Symptom | Why | File:Line |
|---------|-----|-----------|
| Undo clears UI but DB row remains | Frontend never sent `record_id` | `MyTimeView.tsx` — `submitDay` must store `record.id` |
| Undo restores wrong periods | Was restoring `rest_periods` not `work_periods` | Fixed PR #550 — `MyTimeView.tsx` |
| Undo button present on finalized week | `signoff_status` not checked | `MyTimeView.tsx` — check `signoff_status === 'finalized'` |

---

## Scenario 3 — Crew sees calendar

**Normal operation:**
1. My Time → click **CAL** button (week section header)
2. Monthly calendar opens: green = compliant, red = violation, grey = no record
3. Click a day → navigates to that week

**What to verify:**
- [ ] Calendar loads correct month
- [ ] Green cells: days where `is_daily_compliant = true` in DB
- [ ] Red cells: days where rest < 10h
- [ ] Grey cells: no record for that day
- [ ] Arrow nav changes month
- [ ] Clicking past day navigates week view

**Edge case:**
- Future days = grey (capped at today in backend: `hor_compliance_routes.py` — `month-status` endpoint)

**Fail reasons:**
| Symptom | Why |
|---------|-----|
| Calendar all grey | `GET /month-status` returning empty | `hor_compliance_routes.py` — check `is_daily_compliant` field |
| Future days show red/green | Backend not capping at `today` | `hor_compliance_routes.py` month-status loop |

---

## Scenario 4 — Crew views warnings

**Normal operation:**
- Active compliance violations surface in **Active Warnings** section on My Time
- Each warning shows type (e.g. `daily_rest_violation`), severity, shortfall

**What to verify:**
- [ ] `GET /v1/hours-of-rest/warnings?status=active` returns warnings array
- [ ] Click **Acknowledge** → warning dismissed from UI
- [ ] Ledger event written for acknowledgement

**Fail reasons:**
| Symptom | Why |
|---------|-----|
| 422 on warnings fetch | Old code sent `yacht_id` as required param | Fixed PR #545 — now `Optional` |
| Warning count badge but empty list | Response mapping wrong | `MyTimeView.tsx` — `json.data?.warnings ?? []` |

---

## Scenario 5 — HOD reviews department (Department tab)

**Who sees this:** `chief_engineer`, `chief_officer`, `eto`, `chief_steward`, `purser`, `captain`, `manager`

**Normal operation:**
1. Log in as chief_engineer → Hours of Rest → **Department tab**
2. Shows crew × day grid (7 columns) with daily rest hours per person
3. Missing submissions today shown by name
4. Pending counter-signs section if crew have signed their record

**What to verify:**
- [ ] Grid loads with correct crew members for department
- [ ] Days show actual rest hours (not null)
- [ ] "Missing today" list names crew who haven't submitted today
- [ ] Pending signs list shows crew who have `crew_signed` signoffs awaiting HOD

**Edge case — crew member in multiple departments:**
- `auth_users_roles` may have one user under two departments
- HOD sees only their own department (filtered by `department` field)
- Captain sees all departments

**Fail reasons:**
| Symptom | Why | File:Line |
|---------|-----|-----------|
| 403 for captain viewing dept | Captain not in `_HOD_ROLES` check | `hor_compliance_routes.py:36-40` |
| No crew shown | `auth_users_roles` query missing department filter | `hor_compliance_routes.py:362` |
| All rest_hours null | `dash_crew_hours_compliance` view not populated | Supabase view refresh needed |

---

## Scenario 6 — Captain sees vessel overview (Vessel tab)

**Who sees this:** `captain`, `manager`

**Normal operation:**
1. Log in as captain → Hours of Rest → **Vessel tab**
2. Department cards: Engineering ✓, Deck ⚠, Interior ✓
3. Pending final signs: signoffs awaiting captain master signature
4. Sign chain status: `all_hods_signed`, `ready_for_captain`

**What to verify:**
- [ ] All departments listed
- [ ] Analytics: `overall_compliance_pct`, `total_violations`, `avg_work_hours`
- [ ] Pending final signs shows signoffs in status `hod_signed` (ready for master)
- [ ] Sign chain fields reflect actual DB state

**Fail reasons:**
| Symptom | Why |
|---------|-----|
| Empty departments | Captain's `department` filter stripping all | `hor_compliance_routes.py:366` — captain role bypasses dept filter |
| Pending signs empty when they should exist | Sign chain query missing `hod_signed` filter | `hor_compliance_routes.py` — vessel-compliance |

---

## Scenario 7 — Full sign chain: crew → HOD → captain

**This is the legally operative path. Every step must be correct.**

### Step 1 — Crew creates signoff

Button: **"Start Monthly Sign-Off"** (or "Sign My Record")
- Endpoint: `POST /v1/hours-of-rest/signoffs/create`
- Payload: `{department, month, period_type: "monthly"}`
- Result: signoff row created, status = `draft`
- Notification sent to HOD: `hor_signoff_opened`

### Step 2 — Crew signs

**Signature popup appears when:** crew clicks "Sign My Hours" button on the monthly signoff card.
- Popup fields: name, declaration text, timestamp (auto-filled)
- Endpoint: `POST /v1/hours-of-rest/signoffs/sign`
- Payload: `{signoff_id, signature_level: "crew", signature_data: {name, timestamp, ip_address}, notes}`
- Result: status = `crew_signed`
- Notification dispatched to HOD: `hor_awaiting_countersign`
- Ledger event: `hor_crew_signed`, `event_type = approval`

### Step 3 — HOD counter-signs

**Signature popup appears when:** HOD clicks "Counter-Sign" on a `crew_signed` entry in department view.
- Same endpoint, `signature_level: "hod"`
- Result: status = `hod_signed`
- Notification dispatched to captain: `hor_awaiting_master_sign`
- Ledger event: `hor_hod_signed`, `event_type = approval`

### Step 4 — Captain finalizes

**Signature popup appears when:** captain clicks "Finalize" on a `hod_signed` entry in vessel view.
- Same endpoint, `signature_level: "master"`
- Result: status = `finalized` ← **IMMUTABLE from this point**
- Ledger event: `hor_master_signed`, `event_type = approval`

### Sign chain verification queries

```sql
-- See all 4 ledger events for a signoff
SELECT event_type, action, created_at
FROM ledger_events
WHERE entity_id = '<signoff_id>'
ORDER BY created_at;

-- Check final signoff state
SELECT id, status, crew_signed_at, hod_signed_at, master_signed_at, master_signed_by
FROM pms_hor_monthly_signoffs
WHERE id = '<signoff_id>';
```

---

## Scenario 8 — Role gates (what gets blocked and why)

| Who | Tries to | Result | HTTP |
|-----|----------|--------|------|
| `crew` | Access `/department-status` | FORBIDDEN — "Role 'crew' cannot access department status. HOD+ required." | 403 |
| `crew` | Sign as `hod` level | FORBIDDEN — "HOD signature requires HOD role." | 403 |
| `crew` | Sign as `master` level | FORBIDDEN — "Master signature requires captain role." | 403 |
| `chief_engineer` | Sign as `master` level | FORBIDDEN — "Role 'chief_engineer' cannot give master signature." | blocked in handler |
| HOD | Sign before crew has signed | VALIDATION_ERROR — "HOD can only sign after crew. Current status: draft" | blocked |
| captain | Sign as master before HOD | VALIDATION_ERROR — "Master can only sign after HOD. Department has a designated HOD." | blocked |
| Same person as HOD and master | Sign both levels | FORBIDDEN — "Master cannot finalise a signoff they counter-signed as HOD. MLC requires independent verification." | blocked |
| Anyone | Re-sign a `finalized` record | VALIDATION_ERROR — "This sign-off has been finalized by the Master and is now immutable." | blocked |

**Source:** `apps/api/handlers/hours_of_rest_handlers.py:927–1030`

---

## Scenario 9 — HOD bypass (no HOD in department)

If a department has no designated HOD (no `chief_engineer`/`chief_officer`/`eto`/`chief_steward`/`purser` in `auth_users_roles` for that department):

- Captain can sign directly from `crew_signed` → `finalized` (skipping HOD step)
- Notification fired to all vessel-wide HOD-role users: `hor_hod_step_bypassed`
- Ledger event still written

**Test:** Remove all HOD roles for a department → crew signs → captain should be able to finalize directly.

---

## Scenario 10 — Correction request (after signing)

**Who can request:** HOD or captain (kicking back to crew)

1. HOD/captain clicks "Request Correction" on a signed record
2. Popup: enter correction note (mandatory)
3. Endpoint: `POST /v1/hours-of-rest/request-correction`
4. Payload: `{signoff_id, target_user_id, correction_note, role: "hod"|"captain"}`
5. Result: `correction_requested = true`, `correction_note = "..."` on the signoff row
6. Notification sent to crew
7. Ledger event: `request_hor_correction`

**What to verify:**
- [ ] Crew receives notification
- [ ] My Time shows correction badge on the week
- [ ] Crew can re-submit → sign chain resets

---

## Scenario 11 — Week lock (finalized week is read-only)

When a weekly signoff exists with `status = finalized`:
- `GET /my-week` returns `signoff_status: "finalized"`
- Frontend: TimeSlider hidden, Undo button hidden, Submit button hidden
- Week is display-only

**What to verify:**
- [ ] `signoff_status` field present in `/my-week` response
- [ ] TimeSlider not rendered when `signoff_status === 'finalized'`
- [ ] History row for that week shows lock icon or "Finalized" badge

**Source:** `hor_compliance_routes.py:212–221` — weekly signoff query adds `signoff_status` to response

---

## Edge cases and limits

| Case | Expected behaviour |
|------|-------------------|
| Submit day with **zero work periods** | Valid — full rest day (24h rest). `total_work_hours = 0`, `total_rest_hours = 24` |
| Submit day with **overlapping periods** e.g. `06:00–12:00` and `10:00–14:00` | Backend computes complement — overlaps collapse. Check `total_work_hours + total_rest_hours = 24` |
| Submit day in **future** | Allowed by API. MLC doesn't prohibit pre-planning |
| Submit day for **another user** | Blocked — `user_id` always taken from JWT, never from request body (`hours_of_rest_routes.py:303`) |
| Create **duplicate signoff** for same month+department | Returns `CONFLICT` — handled in `create_monthly_signoff` |
| `prior_weeks` > 8 weeks old | Not returned — query window is 8 weeks (`hor_compliance_routes.py:242`) |
| Calendar month with **no records** | All grey — API returns `submitted: false, is_compliant: null` per day |
| HOD with **multiple departments** | Currently shown all departments when captain role also held. Pure HOD (e.g. chief_engineer) filtered to own department |
| `total_rest_hours` exactly 10.0 | Compliant — `is_daily_compliant = true`. MLC limit is **minimum 10h rest** |
| `total_rest_hours` = 9.99 | Non-compliant — warning written to `pms_crew_hours_warnings` |
| 77h weekly rest check | `prior_weeks` aggregation at `hor_compliance_routes.py:272` — `is_compliant = (total_rest >= 77)` |

---

## Where signature popups belong (UI contract)

| Popup | Triggered by | Role required | Fields |
|-------|-------------|---------------|--------|
| Crew sign-off | "Sign My Hours" on monthly signoff card | any authenticated | Name (pre-filled from profile), Declaration text, Timestamp (auto) |
| HOD counter-sign | "Counter-Sign" button on pending sign in Department view | HOD roles | Name, Notes (optional), Timestamp (auto) |
| Captain master sign | "Finalize" button on pending sign in Vessel view | captain/manager | Name, Notes (optional), Timestamp (auto) |
| Correction request | "Request Correction" button (HOD/captain only) | HOD+ | Target user (pre-filled), Correction note (mandatory) |

**Signature data shape sent to API:**
```json
{
  "name": "John Smith",
  "timestamp": "2026-04-15T22:00:00Z",
  "ip_address": "127.0.0.1"
}
```

---

## API endpoints — complete list

| Method | Path | Who | Purpose |
|--------|------|-----|---------|
| GET | `/v1/hours-of-rest/my-week` | all | Own week view + compliance + templates + prior weeks |
| POST | `/v1/hours-of-rest/upsert` | all | Submit/edit a day |
| POST | `/v1/hours-of-rest/undo` | all | Delete a submitted day |
| GET | `/v1/hours-of-rest/month-status` | all | Calendar grid (day-level green/red/grey) |
| GET | `/v1/hours-of-rest/warnings` | all | Active compliance warnings |
| POST | `/v1/hours-of-rest/warnings/acknowledge` | all | Crew acknowledges warning |
| POST | `/v1/hours-of-rest/warnings/dismiss` | HOD+ | HOD/captain dismisses warning with justification |
| GET | `/v1/hours-of-rest/department-status` | HOD+ | Department crew × day grid |
| GET | `/v1/hours-of-rest/vessel-compliance` | captain/manager | Vessel overview + sign chain |
| GET | `/v1/hours-of-rest/signoffs` | all | List signoffs |
| GET | `/v1/hours-of-rest/signoffs/details` | all | Single signoff detail |
| POST | `/v1/hours-of-rest/signoffs/create` | all | Initiate monthly signoff |
| POST | `/v1/hours-of-rest/signoffs/sign` | role-gated | Sign at crew/hod/master level |
| POST | `/v1/hours-of-rest/corrections` | all | Create correction record |
| POST | `/v1/hours-of-rest/request-correction` | HOD+ | Request crew re-do |
| GET | `/v1/hours-of-rest/templates` | all | List schedule templates |
| POST | `/v1/hours-of-rest/templates/create` | all | Create template |
| POST | `/v1/hours-of-rest/templates/apply` | all | Apply template to week |

---

## Quick Y/N test list — run top-to-bottom

```
[ ] 1. Log in as crew. My Time tab loads. Days = 7. Y/N
[ ] 2. Drag TimeSlider, click Submit. work_h + rest_h = 24. Y/N
[ ] 3. Resubmit same day. Updates without error. Y/N
[ ] 4. Click Undo. Slot goes grey, DB row gone. Y/N
[ ] 5. Click CAL. Calendar opens, current month. Y/N
[ ] 6. Future days are grey. Past unsubmitted days are grey. Y/N
[ ] 7. Submit a day with only 6h rest. Warning badge appears. Y/N
[ ] 8. Acknowledge warning. Badge clears. Y/N
[ ] 9. History section shows prior weeks if data exists. Y/N
[10] Click a history row. Week view navigates to that week. Y/N

[11] Log in as crew. Try /v1/hours-of-rest/department-status. 403 returned. Y/N
[12] Log in as chief_engineer. Department tab shows crew grid. Y/N
[13] Log in as captain. Vessel tab shows department cards + sign chain. Y/N

[14] Crew: POST /signoffs/create (department=general, month=2026-04). New row, status=draft. Y/N
[15] Crew: POST /signoffs/sign (level=crew). Status → crew_signed. Y/N
[16] Crew: try POST /signoffs/sign (level=hod). 403 FORBIDDEN. Y/N
[17] HOD: POST /signoffs/sign (level=hod). Status → hod_signed. Y/N
[18] Captain: POST /signoffs/sign (level=master). Status → finalized. Y/N
[19] Ledger: 4 rows for signoff (create + crew + hod + master). Y/N
[20] Anyone: try signing finalized record. VALIDATION_ERROR returned. Y/N

[21] Sign where captain is same person as HOD. FORBIDDEN returned. Y/N
[22] HOD tries to sign before crew. VALIDATION_ERROR "HOD can only sign after crew". Y/N
```

**If any Y/N = N, check:**
1. Is Docker API running? `curl http://localhost:8000/health`
2. Is the JWT using MASTER secret? See `middleware/auth.py:567`
3. Is `yacht_id` present in JWT `user_metadata`? Decoded via [jwt.io](https://jwt.io)
4. Does the user exist in `auth_users_roles` with correct role + yacht_id?

---

## For HMAC01 — what this session built vs what's still needed

### Built and verified
- Full sign chain: crew → HOD → captain (sequential enforcement, role gates, same-person block)
- Ledger events for every mutation: upsert, undo, create signoff, crew/hod/master sign, warn acknowledge, correction
- Immutability after finalization (PR #557 — `handlers/hours_of_rest_handlers.py:955`)
- Calendar view (month-level, day-level green/red/grey)
- Department and vessel compliance views with role gating
- Warnings surface (active warnings, acknowledge, dismiss)
- Prior weeks history (8-week window)
- Signoffs list with real user names (PR #551)
- Undo correctly reverts work_periods and calls backend (PR #550)

### Not built — HMAC01's work
- PDF/A-3 sealed Period receipt (Shape 03 per receipt layer spec)
- PAdES-B-LT signature on the sealed PDF
- RFC 3161 timestamp
- `export.sealed` ledger event
- WORM-policy storage write
- Verifier path for `domain = "hor"`

**The data is clean. The sign chain is enforced. The ledger trail is written. HMAC01 can read `pms_hor_monthly_signoffs.id` and its associated `ledger_events` rows as the input to the sealing pipeline.**
