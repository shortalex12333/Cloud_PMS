# Hours of Rest — Current State + Test Status

> **Last live tested:** 2026-04-19 on https://app.celeste7.ai  
> **Pending commit (NOT deployed):** `55749db6` on local branch `fix/hor-live-bugs-post-test` — network was down, push blocked  
> **Pending DB migration (NOT applied):** `DELETE FROM pms_crew_normal_hours WHERE user_id IS NULL` against TENANT DB  
> **API:** https://pipeline-core.int.celeste7.ai

---

## ⚠ Read This First

Local branch `fix/hor-live-bugs-post-test` (commit `55749db6`) contains 5 bug fixes that are **not yet on production**. All statuses below reflect **what is live right now** on app.celeste7.ai + Render backend.

To unblock: push the branch and open the PR.

```bash
git push -u origin fix/hor-live-bugs-post-test
```

---

## Test Accounts

| Role | Email | Password |
|------|-------|---------|
| Crew | engineer.test@alex-short.com | Password2! |
| HOD | eto.test@alex-short.com | Password2! |
| Captain | x@alex-short.com | Password2! |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! |

**Yacht:** `85fe1119-b04c-41ac-80f1-829d23322598`

---

## Scenario Status

| # | Scenario | Status | Notes |
|---|----------|--------|-------|
| S1 | Submit Day — compliant day with work periods | ✅ WORKING | Verified live |
| S1 | Submit Day — empty day (no work periods = full rest) | ❌ BROKEN on prod | Button hidden. **Fixed in `55749db6`** (`MyTimeView.tsx:1024`) — not deployed |
| S2 | Non-compliant day — period-structure violation (3+ rest windows) | ⚠ UNTESTED | Code path exists. Violation badge expected. Warning message will be inaccurate (see open bugs) |
| S3 | Non-compliant day — total rest < 10h | ⚠ UNTESTED | Code path exists. Needs >14h work periods |
| S4 | Badge accuracy (Compliant vs Violation) | ✅ WORKING | Server-authoritative, verified live |
| S5 | Apply Template to week | ❌ BROKEN on prod | Template dropdown shows generic seeded templates (not crew-owned). Fixed by user_id filter in `55749db6` + DB migration not yet applied |
| S6 | Create Template | ❌ BROKEN on prod | UI does not exist on current production. **Added in `55749db6`** — not deployed |
| S7 | Submit Week For Approval (crew) | ✅ WORKING | Verified live. Gated correctly |
| S7 | Submit Week button absent for fleet manager | ✅ WORKING | Verified live |
| S8 | HOD countersign from Department tab | ✅ WORKING | Browser + API verified. Department tab shows for HOD roles, not captain |
| S9 | Captain sees My Time + All Departments only (no Dept tab) | ✅ WORKING | Verified live |
| S10 | Captain Sign All disabled until all HODs signed | ✅ WORKING | Verified live. Greyed with correct tooltip |
| S11 | Fleet Manager: read-only across all tabs | ✅ WORKING | No sign/submit/create buttons. Verified live |
| Warnings | Violation warning created after non-compliant submit | ✅ WORKING (fires) | Warning row created. Message may be wrong — see open bugs |
| Warnings | Crew acknowledges warning | ✅ WORKING | API + DB verified |
| Warnings | HOD/captain dismisses warning | ✅ WORKING | API + DB verified |
| Sign chain | crew_signed → hod_signed → finalized progression | ✅ WORKING | Full chain API-verified. Immutable after finalized |
| MLC S11 | Same person cannot sign HOD + master | ✅ WORKING | API returns FORBIDDEN + correct MLC message |

---

## Open Bugs (unresolved on production)

### BUG-1 — Submit Day hidden for empty days
- **Where:** `MyTimeView.tsx:1024`
- **Current behaviour:** `(draft?.length ?? 0) > 0` hides the button when no work periods are drafted. Empty day (crew did not work = 24h rest) cannot be submitted.
- **Fix:** Remove draft length condition. Already in `55749db6`.
- **Status:** Fixed locally, not deployed.

### BUG-2 — Warning message wrong for period-structure violations
- **Where:** `check_hor_violations` — Supabase PostgreSQL function (not in Python layer)
- **Current behaviour:** When crew has ≥ 10h rest but split into 3+ periods, warning message says `"Daily rest violation: 12.00 hours (minimum 10h required)"` — the hours figure is correct but the label is wrong. 12h > 10h is not an hours violation; it's a period-structure violation.
- **Fix required:** Update `check_hor_violations` SQL function in TENANT Supabase to distinguish violation type in the message. Cannot be fixed from Python layer (the message is written by the SQL function, not the handler).
- **Python HOD notification body:** Fixed in `55749db6` — now says "X periods — MLC A2.3 requires ≤2". But the warning row seen by crew still has the wrong message.
- **Status:** Partially fixed, SQL function needs update.

### BUG-3 — Weekly violation warnings create 7 duplicate rows per week
- **Where:** `check_hor_violations` SQL function, called from `hours_of_rest_handlers.py:449`
- **Current behaviour:** Each day-submission triggers the RPC. For weekly violations (< 77h/7 days), the function likely creates a warning row per day submitted, each with that day's `record_date`. Result: up to 7 warning rows for one non-compliant week.
- **Fix attempt in `55749db6`:** Pre-delete non-`DAILY_REST` warnings for the 7-day window before calling the RPC (`hours_of_rest_handlers.py:434–447`). Effectiveness depends on whether the SQL function uses `warning_type = 'DAILY_REST'` for daily warnings (assumed, not confirmed).
- **Status:** Fix in `55749db6`, not deployed. If the SQL function uses a different type name the fix won't catch it.

### BUG-4 — Generic seeded templates visible to all crew
- **Where:** `hor_compliance_routes.py:225–227`
- **Current behaviour:** Query has no `user_id` filter — returns all templates with `is_active = True` for the yacht including 3 seeded generic templates (`user_id IS NULL`).
- **Fix:** Added `.eq("user_id", user_id)` in `55749db6`. Also requires DB migration: `DELETE FROM pms_crew_normal_hours WHERE user_id IS NULL`.
- **Status:** Fixed locally, not deployed. DB migration not applied.

### BUG-5 — Create Template UI missing
- **Where:** `MyTimeView.tsx` — frontend only
- **Current behaviour:** No **+ New Template** button or form exists in production. The `POST /templates/create` backend endpoint works correctly. The `list_crew_templates` handler also works. Only the UI is missing.
- **Fix:** Added `canCreateTemplate` gate + **My Templates** section with inline popup form in `55749db6`. `saveAsTemplate()` builds 7-day `schedule_template` from current week's draft and calls the backend.
- **Status:** Added locally, not deployed.

### BUG-6 — NoneType.strip() error on some date entries (S1)
- **Reported:** "NoneType.strip() error on random date entry" during live test
- **Where:** Unknown. Not found in any current Python code. Searched: `hours_of_rest_handlers.py`, `hours_of_rest_routes.py`, `hor_compliance_routes.py`. All `.strip()` calls are on Pydantic-required fields (protected from null by model validation) or correction handlers.
- **Possible cause:** Could be inside `check_hor_violations` Supabase SQL function. Could be from a previous deploy version no longer in code.
- **Status:** Unresolved. If it recurs, capture the full server error trace from Render logs.

---

## What Must Happen Before Next Test Run

1. **Push + merge `fix/hor-live-bugs-post-test`** — fixes BUG-1, BUG-4, BUG-5, partial BUG-3
   ```bash
   git push -u origin fix/hor-live-bugs-post-test
   gh pr create --base main --head fix/hor-live-bugs-post-test --title "fix(hor): post-live-test bugs — submit day, templates, violations"
   ```

2. **Apply DB migration on TENANT Supabase** (`vzsohavtuotocgrfkfyd`):
   ```sql
   DELETE FROM pms_crew_normal_hours WHERE user_id IS NULL;
   ```

3. **Wait for Render deploy** to pick up backend changes from the merged PR.

4. **Fix `check_hor_violations` SQL function** (BUG-2, BUG-3) — requires Supabase access to update the function body. This is the root cause of both the misleading warning message and the weekly duplicate rows.

---

## Code Locations (verified from current files)

| Feature | File | Line |
|---------|------|------|
| Submit Day button gate | `MyTimeView.tsx` | 1024 |
| `canSubmitWeek` / `canCreateTemplate` gates | `MyTimeView.tsx` | 204–206 |
| `saveAsTemplate()` function | `MyTimeView.tsx` | ~535 |
| `applyTemplate()` function | `MyTimeView.tsx` | 501 |
| Upsert handler — compliance calc | `hours_of_rest_handlers.py` | 328–335 |
| `has_valid_rest_periods` (period count rule) | `hours_of_rest_handlers.py` | 332–335 |
| Weekly warning dedup pre-delete | `hours_of_rest_handlers.py` | 434–447 |
| `check_hor_violations` RPC call | `hours_of_rest_handlers.py` | 449–456 |
| HOD notification body (fixed) | `hours_of_rest_handlers.py` | 511–518 |
| Template query — user_id filter | `hor_compliance_routes.py` | 225–227 |
| Tab routing by role | `hours-of-rest/page.tsx` | 84–87 |
| HOD sign button gate | `DepartmentView.tsx` | 779 |
| Captain Sign All disabled gate | `VesselComplianceView.tsx` | 448–449 |
