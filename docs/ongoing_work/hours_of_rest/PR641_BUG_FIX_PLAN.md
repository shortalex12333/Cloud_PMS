# PR #641 — HoR Bug Fix Plan
**Date:** 2026-04-18  
**Owner:** HOURSOFREST04  
**Status:** COMPLETE — all 8 bugs implemented, 2 SQL migrations pending DB apply

---

## Root Cause Summary (verified against live DB + source)

### BUG-641-1 — crew_comment guard not enforcing on frontend
- **Location:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx:176`
- **Root cause:** `handlePrimary` calls `executeAction('upsert_hours_of_rest', {})` with an empty object — `crew_comment` is **never sent** in the payload. Backend guard at `handlers/hours_of_rest_handlers.py:L507-515` is correctly coded but the payload field is absent, so for non-compliant entries there is no comment to enforce against.
- **Fix:** `executeAction` for submit must pass `crew_comment` from a state field. When API returns `VALIDATION_ERROR` (action bus HTTP 200, `data.error.code = "VALIDATION_ERROR"`), frontend must surface it.

### BUG-641-2 — Daily violation fires for compliant days
- **Location:** `apps/api/handlers/hours_of_rest_handlers.py:L501-505`
- **Root cause:** `is_daily_compliant` requires `has_valid_rest_periods` (≤2 rest periods AND longest ≥6h). A user entering work in 3 segments creates 3 rest periods → `rest_period_count = 3 > 2` → `is_daily_compliant = false` even if total rest = 12h. The client badge checks `is_compliant` (a separate field), while the SQL `check_hor_violations` uses `is_daily_compliant`. Mismatch = badge shows ✓ but warning fires.
- **Fix:** Align the daily compliance badge in frontend to use `is_daily_compliant` from the record, not `is_compliant`. Also evaluate whether the `has_valid_rest_periods` rule is correctly applied — MLC A2.3 allows ≤2 rest periods per day, so flagging >2 periods as non-compliant is CORRECT. The badge is wrong, not the rule.

### BUG-641-3 — Weekly violation fires on every day submission with wrong amount
- **Location:** `apps/api/handlers/hours_of_rest_handlers.py:L517-530` (upsert_data), `supabase DB function check_hor_violations`
- **Root cause (CRITICAL):** Python handler **never writes `is_weekly_compliant` or `weekly_rest_hours`** to `upsert_data`. DB column defaults are `is_weekly_compliant = false`, `weekly_rest_hours = 0`. So every record has `is_weekly_compliant = false` after insert/update. `check_hor_violations` SQL function fires `NOT v_record.is_weekly_compliant = NOT false = true` → creates WEEKLY_REST warning on every single submission.
- **Fix:** Add weekly calculation to Python handler:
  1. After upsert, query the 7-day rolling window (6 prior days + current day) summing `total_rest_hours`
  2. Compute `weekly_total`, `is_weekly_compliant = (weekly_total >= 77)`
  3. Add both to `upsert_data` before write
  4. Weekly warnings only meaningful at end of rolling window — suppress or flag as "partial" if < 7 days submitted

### BUG-641-4 — Template apply clears draft on page refresh
- **Location:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx` (apply template handler)
- **Root cause:** After `apply_template` action executes, the component refreshes from server state. Draft work_periods are in component state, not persisted. Refresh wipes them.
- **Fix:** After template apply response, write applied work_periods to `localStorage` keyed by `yacht_id + user_id + record_date`. On component mount, rehydrate from localStorage if no submitted record exists.

### BUG-641-5 — No custom template creation UI
- **Location:** Frontend — HoR page template section
- **Root cause:** The `create_hor_template` action exists on backend but no frontend form to invoke it.
- **Fix:** Add "Create Template" button in template list view that opens action popup with fields: `name`, `description`, `work_periods` (time-range inputs). Wire to `create_hor_template` action.

### BUG-641-6 — 5 duplicate "4-on/8-off Watch" templates + weak quality
- **Location:** `supabase/seeds/seed_hours_of_rest.sql` + live DB `pms_hor_templates`
- **Root cause:** Seed ran multiple times OR duplicate INSERT without dedup. Templates lack `start_time`.
- **Fix:**
  1. Run cleanup SQL (delete all but one 4-on/8-off, and delete entirely if still weak)
  2. Insert 4 quality templates: Standard Day Watch (06:00-18:00 work), Standard Night Watch (18:00-06:00 work), 4-on/8-off Morning Start (06:00 start), 4-on/8-off Night Start (18:00 start)
  3. Fix seed to use `ON CONFLICT DO NOTHING` to prevent future duplicates

### BUG-641-7 — No HOD per-crew sign-off UI / captain sees wrong tabs
- **Location:** `apps/web/src/components/hours-of-rest/VesselComplianceView.tsx` (HOD/captain view)
- **Root cause:** Per-crew "Sign off for approval" flow was never built. Captain sees Department tab which is HOD-only scope.
- **Fix (HOD):**
  1. In HOD Department view: each crew row "View" link opens a modal with crew weekly summary + "Sign Off" button
  2. Sign-off modal: name print field (required), signature confirms HOD approval for that crew+week
  3. Calls `create_monthly_signoff` or a new `hod_sign_crew_week` action
  4. Show HOD signature confirmed badge before captain can sign
- **Fix (Captain):** 
  1. Remove "Department" tab from captain role — captain sees "My Time" + "All Vessel" only
  2. "All Vessel" shows all crew HOD signature status before captain can sign off

### BUG-641-8 — Active warning acknowledge → ledger_events not wired
- **Location:** `apps/api/handlers/hours_of_rest_handlers.py` — `acknowledge_warning` handler
- **Root cause:** `acknowledge_warning` updates `pms_crew_hours_warnings.status = 'acknowledged'` but does NOT insert to `ledger_events`.
- **Fix:** After status update, call `build_ledger_event(event_type="update", entity_type="hor_warning", action="acknowledge_warning", ...)` + insert.

---

## Execution Order

| # | Bug | Priority | File(s) | Status |
|---|-----|----------|---------|--------|
| 1 | **BUG-641-3** Weekly violation | P0 | `20260418_fix_hor_compliance_functions.sql` (migration pending apply) | ✅ SQL WRITTEN |
| 2 | **BUG-641-2** Daily badge mismatch | P0 | `MyTimeView.tsx:1128-1132` + L497-498 | ✅ DONE |
| 3 | **BUG-641-1** crew_comment frontend | P0 | `MyTimeView.tsx:L250-252,L450,L478-481` | ✅ DONE |
| 4 | **BUG-641-6** Duplicate templates + cleanup SQL | P1 | `20260418_fix_hor_template_cleanup.sql` (migration pending apply) | ✅ SQL WRITTEN |
| 5 | **BUG-641-4** Template draft persistence | P1 | `MyTimeView.tsx:applyTemplate` | ✅ DONE |
| 6 | **BUG-641-5** Custom template creation UI | P1 | `MyTimeView.tsx:createTemplate` + templates section | ✅ DONE |
| 7 | **BUG-641-7** HOD sign-off flow + captain tabs | P1 | `page.tsx:L85`, `DepartmentView.tsx`, `VesselComplianceView.tsx` | ✅ DONE |
| 8 | **BUG-641-8** Warning ack → ledger | P2 | `hours_of_rest_handlers.py:L1893-1916` | ✅ ALREADY DONE |

**Additional deliverable**: `GET /v1/hours-of-rest/templates/{template_id}` endpoint added (required by BUG-641-4 fix).

**Pending DB actions** (network issue preventing apply):
- Apply `supabase/migrations/20260418_fix_hor_compliance_functions.sql` to TENANT (`vzsohavtuotocgrfkfyd`) 
- Apply `supabase/migrations/20260418_fix_hor_template_cleanup.sql` to TENANT
- Delete both files after applying (per project convention)

---

## Step 1 — BUG-641-3: Weekly compliance calculation (Python backend)

**File:** `apps/api/handlers/hours_of_rest_handlers.py`

After computing `is_daily_compliant` (L~505) and before building `upsert_data` (L~517), add:

```python
# Calculate 7-day rolling weekly rest
week_start = (
    datetime.strptime(record_date, "%Y-%m-%d") - timedelta(days=6)
).strftime("%Y-%m-%d")
weekly_rows = self.db.table("pms_hours_of_rest").select(
    "total_rest_hours, record_date"
).eq("yacht_id", yacht_id).eq("user_id", user_id).gte(
    "record_date", week_start
).lte("record_date", record_date).eq("is_correction", False).execute()

# Build map of existing daily totals (exclude today — we'll add today's value)
existing_days = {r["record_date"]: float(r["total_rest_hours"]) for r in (weekly_rows.data or [])}
existing_days[record_date] = total_rest_hours  # today's computed value

weekly_rest_hours_val = round(sum(existing_days.values()), 2)
days_in_window = len(existing_days)
# Only flag violation if we have a full 7-day window (or end of period)
is_weekly_compliant = (weekly_rest_hours_val >= 77) if days_in_window >= 7 else True
```

Then add to `upsert_data`:
```python
"weekly_rest_hours": weekly_rest_hours_val,
"is_weekly_compliant": is_weekly_compliant,
```

**Rationale:** Weekly MLC violation only meaningful with 7 days of data. Partial weeks must not fire violation.

---

## Step 2 — BUG-641-2: Fix daily badge to use `is_daily_compliant`

**File:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx:L123`

Current: `const complianceStatus = is_compliant ? 'compliant' : 'non_compliant';`

The field `is_compliant` is an older denormalised field. Replace with `is_daily_compliant` from entity payload. Check what `payload` exposes.

Also check `VesselComplianceView.tsx` — any client-side recompute of `rest_hours >= 10` needs to be removed in favour of server-authoritative `is_daily_compliant`.

---

## Step 3 — BUG-641-1: crew_comment field in submit

**File:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx`

1. Add `crewComment` state: `const [crewComment, setCrewComment] = React.useState('')`
2. When `is_daily_compliant === false` (or unknown, default to showing field), show textarea for crew comment
3. `handlePrimary` passes `{ crew_comment: crewComment }`
4. Parse `data.error` from action bus response and surface `VALIDATION_ERROR` message to user

---

## Step 4 — BUG-641-6: Template cleanup

**SQL (apply to TENANT, then delete):**
```sql
-- Delete duplicate 4-on/8-off entries (keep none, they're weak)
DELETE FROM pms_hor_templates WHERE name ILIKE '%4-on%8-off%';

-- Insert quality templates
INSERT INTO pms_hor_templates (yacht_id, name, description, work_periods, is_global, created_at)
SELECT 
  NULL, -- global
  t.name, t.description, t.work_periods::jsonb, true, NOW()
FROM (VALUES
  ('Day Watch (06:00–18:00)', '12h day watch, standard deck/engineering rotation',
   '[{"start":"06:00","end":"18:00"}]'),
  ('Night Watch (18:00–06:00)', '12h night watch, standard deck/engineering rotation',
   '[{"start":"18:00","end":"24:00"},{"start":"00:00","end":"06:00"}]'),
  ('4-on/8-off Morning (06:00 start)', '4h work, 8h rest cycling from 06:00',
   '[{"start":"06:00","end":"10:00"},{"start":"18:00","end":"22:00"}]'),
  ('4-on/8-off Night (18:00 start)', '4h work, 8h rest cycling from 18:00',
   '[{"start":"18:00","end":"22:00"},{"start":"06:00","end":"10:00"}]')
) AS t(name, description, work_periods)
ON CONFLICT DO NOTHING;
```

---

## Step 5 — BUG-641-4: Template draft persistence

**File:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx`

After receiving template apply response with `work_periods`:
```typescript
const draftKey = `hor_draft_${yachtId}_${userId}_${recordDate}`;
localStorage.setItem(draftKey, JSON.stringify(work_periods));
```

On mount, if no submitted record:
```typescript
const saved = localStorage.getItem(draftKey);
if (saved && !hasSubmittedRecord) {
  setWorkPeriods(JSON.parse(saved));
}
```

Clear on successful submit.

---

## Step 6 — BUG-641-5: Custom template creation

**File:** `apps/web/src/components/lens-v2/entity/HoursOfRestContent.tsx` or `VesselComplianceView.tsx`

Add "Create Template" button in template section. Opens `ActionPopup` for action `create_hor_template` with fields: `name` (text), `description` (textarea), `work_periods` (time-range array builder). The action already exists in backend — this is frontend wire-up only.

---

## Step 7 — BUG-641-7: HOD sign-off flow + captain tab removal

**File:** `apps/web/src/components/hours-of-rest/VesselComplianceView.tsx`

### Captain tab fix:
- Find the tabs array — remove "Department" tab for captain role
- Captain should only see "My Time" and "All Vessel"

### HOD per-crew sign-off:
- In Department view crew list: add "Sign Off" button per crew member
- Opens modal: shows crew weekly summary + `signed_name` text input
- On confirm: calls `create_monthly_signoff` with `{ user_id: crewMemberId, signed_name, period_type: "weekly" }`
- Shows HOD signature badge on crew row after sign

### Captain all-vessel view:
- Show per-crew HOD sign status
- Captain "Sign All" only enabled when all crew have HOD signature

---

## Step 8 — BUG-641-8: Warning acknowledge → ledger_events

**File:** `apps/api/handlers/hours_of_rest_handlers.py` — `acknowledge_warning` handler

After the `pms_crew_hours_warnings` status update, add:
```python
build_ledger_event(
    yacht_id=yacht_id,
    user_id=user_id,
    event_type="update",
    entity_type="hor_warning",
    entity_id=str(warning_id),
    action="acknowledge_warning",
    change_summary=f"Warning acknowledged by {user_id}",
    metadata={"warning_type": warning_type, "acknowledged_at": now_iso},
    event_category="write",
)
self.db.table("ledger_events").insert(ledger_event).execute()
```

---

## Verification Protocol

Each bug fix requires:
1. Docker rebuild (`docker compose up --build api`)
2. Manual curl or browser test confirming the specific scenario passes
3. No regressions on shard-46 (`apps/web/e2e/shard-46-hor-extended/`)

**P0 bugs verified via:**
- BUG-641-3: Submit 3 days with 10h rest each → no weekly violation after each day; submit 7 days with 5h rest each → weekly violation fires only on day 7
- BUG-641-2: 12h rest / 1 work period → badge AND DB both show compliant, no warning row in `pms_crew_hours_warnings`
- BUG-641-1: Submit non-compliant day with no comment → VALIDATION_ERROR surfaces in UI

---

## PR Structure

Single PR #641. Commits:
1. `fix: weekly compliance calculation in upsert_hours_of_rest handler`
2. `fix: daily compliance badge uses is_daily_compliant from record`
3. `fix: crew_comment field wired into submit payload + error surface`
4. `fix: template cleanup SQL + improved seed templates`
5. `fix: template draft state persisted to localStorage`
6. `feat: custom template creation UI`
7. `feat: HOD per-crew sign-off flow + captain tab scoping`
8. `fix: warning acknowledge writes to ledger_events`
