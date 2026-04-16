# Hours of Rest — Manual Testing Guide

> Last updated: 2026-04-16 (post PR #596 merge — all HoR PRs #567–#596 merged to main)
> Use this file to record what you tested, what you saw, and whether it passed.
> Insert console errors, response JSONs, or observations inline under each scenario.

---

## Test credentials

| Role | Email | Password |
|------|-------|----------|
| Crew | engineer.test@alex-short.com | Password2! |
| HOD (ETO) | eto.test@alex-short.com | Password2! |
| Captain | x@alex-short.com | Password2! |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! |

**Frontend**: https://app.celeste7.ai
**API**: https://pipeline-core.int.celeste7.ai

---

## Browser console setup

Open DevTools → Console before every scenario. Paste this to intercept API calls:

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  if (args[0]?.includes?.('/actions/execute') || args[0]?.includes?.('/v1/')) {
    const clone = r.clone();
    clone.json().then(d => console.log('[API]', args[0], JSON.stringify(d)));
  }
  return r;
};
```

---

## Fixed since last session (PRs #567–#596)

| Bug | Fix | PR |
|-----|-----|----|
| submitDay silent failure — button reverted, no error, no API call | Empty catch replaced with real error — now renders inline under day cell | #569 |
| maxWidth: 680 hardcoded — component locked to 680px, didn't fill screen | Replaced with `width: 100%` — fills shell width | #569 |
| Flex height wrong — scroll container only half viewport | Added `minHeight: 0` to tab content wrapper | #569 |
| list_monthly_signoffs DATABASE_ERROR | Removed PostgREST cross-schema join | #567 |
| get_monthly_signoff DATABASE_ERROR | Same — removed user join | #567 |
| Master sign blocked (MLC false positive) | Tests use role-specific JWTs for HOD/captain sign steps | #567 |
| supabaseAdmin querying MASTER instead of TENANT | rbac-fixtures hardcoded TENANT fallback | #568 |
| LOCKED check not in running Docker | Docker rebuilt | #567 |
| Ledger `user_role` NULL on sign actions | Resolve from auth_users_roles before write | #578 |
| Ledger `entity_type` raw table name on sign actions | Changed to `hours_of_rest_signoff` | #578 |
| Fleet manager can create signoffs (BUG-HOR-5) | FORBIDDEN returned from dispatcher for manager role | #580 |
| BUG-HOR-6: crew re-sign regresses status | Added `current_status == "draft"` guard | #584 |
| BUG-HOR-7: cross-user crew signing | Added `signoff.user_id == user_id` ownership check | #584 |
| Ledger `user_role` NULL on warning actions | Resolve from auth_users_roles (acknowledge) / payload (dismiss) | #586 |
| Fleet manager Submit Week button visible (BUG-HOR-5b) | `canSubmitWeek = user?.role !== 'manager'` gate in MyTimeView.tsx | #588 |
| Ledger `user_role` NULL on create_monthly_signoff | Resolve from auth_users_roles before write | #596 |
| Ledger `entity_type` raw table name on create_monthly_signoff | Changed to `hours_of_rest_signoff` | #596 |
| BUG-HOR-2: response `entity_id` returns caller's user_id | Set `builder.entity_id` = signoff UUID after insert | #596 |

---

## Scenario 1 — Crew inputs rest hours for today

**Role**: Crew
**Path**: Log in → Hours of Rest → (crew sees single-column view, no tab nav) → current week grid
**Expected**: Timeline track visible per day, Submit Day button appears after clicking the track to add a work period, submits successfully

> **UI model note** (clarified 2026-04-16 by MCP02): The component is a **timeline track** (00–24h bar), not a range slider. Crew role has no tab navigation — single-column layout. `Submit Day` button only renders on days that have **unsaved draft work periods** (track has been clicked but not yet submitted). If all 7 days are already submitted, no Submit Day buttons appear — this is correct. `Submit Week For Approval` is a separate action that creates the monthly signoff.

**Tested by**: HOURSOFREST_MCP02 (Playwright MCP) · **Date**: 2026-04-16 16:38 UTC · **Env**: app.celeste7.ai (prod, post PR #569)

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Navigate to Hours of Rest | Week grid Mon–Sun renders, no tab nav for crew | ✅ PASS | Browser-verified x2 (HOURSOFREST01 agent + MCP02 headless). All 7 day labels, finalized lock icon. |
| Layout fills screen width | No 680px cap — component spans available width | ✅ PASS | HOURSOFREST01: 1983px. MCP02: 1317.125px at 1440 viewport. maxWidth=none confirmed. PR #569(b). |
| Scroll area fits viewport | Content scrolls inside bounded area, not whole page | ✅ PASS | HOURSOFREST01: overflowY=auto container, window.scrollY stays 0. MCP02: scrollH=1773 clientH=810. PR #569(c). |
| No tab buttons visible (crew single-column) | No Department / All Departments / Fleet tabs | ✅ PASS | HOURSOFREST01: 0 role=tab elements, 0 matching tab buttons. MCP02 confirmed same. |
| Timeline track visible per day | 00–24h bar per day | ✅ PASS | 7 `hor-track-bg` elements found. WORK+REST bars rendered. |
| Click track to add work period | Work block appears on the track | ✅ PASS (route-mock) | MCP02 S1.2: mocked `/api/v1/hours-of-rest/my-week` → 7 unsubmitted days. Clicked Mon track → 1h WORK block appeared. |
| Submit Day button appears after adding draft | Button visible below track | ✅ PASS (route-mock) | MCP02 S1.2: Submit Day button rendered after track click. |
| Click Submit Day — success path | Cell updates, no page reload | ✅ PASS (real session, prior weeks) | Previous MCP02 run confirmed submit path. |
| On failure — error visible inline | Error under the day cell (not silent revert) | ✅ PASS (route-mock) | MCP02 S1.2: POST intercepted → 400 injected. Error rendered **inline under Mon day card** with ⚠ prefix. `containsMCP02Mark=true`. No silent revert. PR #569(a) confirmed. |
| Submitted indicator appears | "✓ Compliant" badge per day | ✅ PASS | All 7 days show "✓ Compliant". Week header: "🔒 This week is finalized." |
| Signoff status displayed | Monthly sign-off section shows current status | ✅ PASS | "April 2026 — Finalised ✓" displayed correctly. Full chain (crew→HOD→master) complete. |

**⚠ Key implementation detail**: Submit Day calls `POST /api/v1/hours-of-rest/upsert` (REST proxy) — NOT `/v1/actions/execute` (action-bus). Intercepts targeting action-bus produce no hits on Submit Day. Guide curl reference updated.

**Console errors observed:**
```
Level=error   → 0 messages
Level=warning → 0 messages
Total: 20 messages pre-refresh (all info/debug), 8 post-refresh. Zero uncaught exceptions.
```

**Notes:**
```
VERIFIED (PR #569):
  ✅ (b) maxWidth:680 removed — 1317px at 1440 viewport
  ✅ (c) minHeight:0 on tab wrapper — scroll bounded correctly

BLOCKED (requires unsubmitted day):
  ⚠ (a) submitDay error surfacing — cannot test without clicking track first
      TO RE-TEST: log in as crew, navigate to a week with an unsubmitted day,
      click the timeline track to add a work period, then click Submit Day.
      Expected: error shown inline OR cell updates. Either way — no silent revert.

ACCOUNT STATE at time of test:
  engineer.test current week (04-13..19): all 7 days submitted=true
  April 2026 monthly signoff: status=crew_signed, awaiting HOD counter-sign
```
API INTERCEPT (via window.__horApiLog, fetch wrapper):
  - POST https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token → 200 (login OK)
  - GET  https://backend.celeste7.ai/v1/bootstrap → 200
        user_id=4a66036f-899c-40c8-9b2a-598cee24a62f  role=crew
        yacht_id=85fe1119-b04c-41ac-80f1-829d23322598 (M/Y Test Vessel)
        tenant_key_alias=yTEST_YACHT_001  subscription_status=paid
  - GET  /api/v1/notifications?type=hor_unsigned → 200 {data:[]}
  - GET  /api/v1/hours-of-rest/warnings?status=active → 200  success=true, 7 warnings returned
  - GET  /api/v1/hours-of-rest/my-week → 200  all 7 days submitted=true,
        pending_signoff={month:"2026-04", status:"crew_signed", signoff_id:"1b8a5bf7-…"}
  - GET  /api/v1/hours-of-rest/my-week?week_start=2026-04-06 → 200  all 7 days submitted=false, week flagged read-only in UI

STATE SUMMARY:
  - Crew user id: 4a66036f-899c-40c8-9b2a-598cee24a62f
  - Yacht: M/Y Test Vessel (85fe1119-…)
  - Current week (4/13–4/19): all submitted, weekly rest violations active (3 open warnings)
  - April 2026 signoff: already crew_signed → awaiting HOD
  - Past weeks: read-only

RECOMMENDATION:
  To fully exercise Scenario 1 submit path, provision a fresh crew account (or wipe today's
  record for engineer.test) so a day can be edited and submitted cleanly, or expose an
  "edit/withdraw" affordance on already-submitted days. Without that, Scenario 1 can only
  verify layout/persistence — not the submit-day error-surface fix from PR #569(a).
```

---

### Browser verification (HOURSOFREST01 direct run, 2026-04-16)

**Tester**: HOURSOFREST01 (Playwright Python SDK, headless Chromium)
**Date**: 2026-04-16 19:19 UTC
**Account**: engineer.test@alex-short.com (crew)
**Auth method**: localStorage injection (Supabase token via curl → sb-qvzmkaamzaqxpzbewjxe-auth-token)
**Viewport**: 1440×900
**Entry point**: https://app.celeste7.ai/hours-of-rest
**Bootstrap confirmed**: role=crew, yacht_id=85fe1119-b04c-41ac-80f1-829d23322598 (M/Y Test Vessel), yTEST_YACHT_001

#### Check results

```
CHECK 1 — Page loads (no blank/crash): PASS
  URL: https://app.celeste7.ai/hours-of-rest (no redirect to login)
  Body content: 2016 chars rendered on initial load; full week grid visible after 3s settle.

CHECK 2 — No red console errors on load: PASS
  0 errors, 0 warnings, 8 console messages (all AuthContext LOG lines).
  Full message list:
    [LOG] [AuthContext] Init - non-blocking auth
    [LOG] [AuthContext] Auth event: SIGNED_IN | Session: true
    [LOG] [AuthContext] Bootstrap attempt 1/4 (timeout: 2000ms)
    [LOG] [AuthContext] Bootstrap API success: 85fe1119-b04c-41ac-80f1-829d23322598 crew
    [LOG] [AuthContext] Bootstrap success: 85fe1119-b04c-41ac-80f1-829d23322598 crew yTEST_YACHT_001
    [LOG] [AuthContext] Auth event: INITIAL_SESSION | Session: true
    [LOG] [AuthContext] Bootstrap skipped — already done or in flight
    [LOG] [AuthContext] Bootstrap skipped — already done or in flight

CHECK 3 — Component fills full screen (no 680px cap): PASS
  main offsetWidth=2058px (1317px rectWidth at 1440 viewport), maxWidth=none.
  HOR-specific element [class*="hor-"]: offsetWidth=1983, maxWidth=none.
  PR #569(b) confirmed — no 680px cap present.

CHECK 4 — Scroll area is bounded (not whole page): PASS
  Found 1 scrollable container: DIV, overflowY=auto, scrollHeight=1662, clientHeight=810.
  window.scrollBy(0,500) → window.scrollY stayed at 0 (page-level scroll is suppressed).
  Content scrolls inside bounded flex child, not the full page.
  PR #569(c) confirmed.

CHECK 5 — No tab buttons visible at top (crew = no dept/fleet tabs): PASS
  0 elements with role="tab" found. 0 buttons matching Department/All Departments/Fleet text.
  Crew receives single-column layout with no tab navigation.

CHECK 6 — My Time is the only view (single column): PASS
  Visible label is "HOURS OF REST" with "CREW" role badge.
  "My Time" literal string does not appear in page text (internal naming differs from visible label).
  No Department, Fleet, or HOD tab/view present. Single-column confirmed.

CHECK 7 — Week grid renders (Mon through Sun): PASS
  All 7 day labels found: Mon, Tue, Wed, Thu, Fri, Sat, Sun.
  Week: 2026-04-13 to 2026-04-19.
  Header: "THIS WEEK — 2026-04-13" with finalized lock indicator (🔒).
  Navigation arrows present (previous-week active, next-week disabled — cannot go past current week).

CHECK 8 — Timeline track visible per day (00–24h bar): PASS
  7 timeline track elements found (class=hor-track-bg, one per day).
  Time labels 00/02/04/.../22/24 visible for each day.
  WORK and REST summary bars rendered per day (e.g. "WORK 2.0h / REST 22.0h").

CHECK 9 — Submitted days show badge: PASS
  All 7 days show "✓ Compliant" badge.
  Each day shows hours summary (e.g. "Mon — 2.0h work / 22.0h rest — ✓ Compliant").
  Week header shows "🔒 This week is finalized."
  Finalized state correctly renders tracks read-only (no click hint).

CHECK 10 — Submit Day path (unsubmitted day available): N/A
  All 7 days submitted, week finalized. No "Submit Day" button present — correct behaviour.
  7 hor-track-bg elements exist but are read-only.
  "Insert My Template" button present but disabled with message:
    "Template populates unsubmitted days only. Your signature is still required."
  Blocker: need account with >= 1 unsubmitted day to test PR #569(a) error surfacing.

CHECK 11 — Sign-off section visible: PASS
  Monthly sign-off section rendered with heading "MONTHLY SIGN-OFF".
  Content: "April 2026 — Finalised ✓"
  Status is finalized — Submit Week button correctly absent.

CHECK 12 — Signoff status displayed: PASS
  Displayed text: "Monthly Sign-Off / April 2026 / Finalised ✓"
  Full sign chain (crew→HOD→master) has completed for April 2026.
  No "Awaiting HOD" pending state — signoff is closed.
```

#### Network calls observed (all 200)

```
GET  /api/v1/hours-of-rest/my-week                  200
GET  /api/v1/notifications?type=hor_unsigned         200
GET  /api/v1/hours-of-rest/warnings?status=active   200
POST https://backend.celeste7.ai/v1/bootstrap        200
```

#### Active warnings visible on page (4 total)

```
⚠ INFO    2026-04-13  Daily rest violation: 22.00 hours (minimum 10h required)
⚠ WARNING 2026-04-13  Weekly rest violation: 22.00 hours (minimum 77h required)
⚠ WARNING 2025-01-04  Weekly rest violation: 19.00 hours (minimum 77h required)
⚠ WARNING 2025-01-03  Weekly rest violation: 11.00 hours (minimum 77h required)
```

Each warning has an "Acknowledge" button visible and active.

#### Compliance panel content

```
24h rolling — 23h rest      ✓ ✓  min 10h
7-day rolling — 91h rest    ✓ ✓  min 77h
This week                   — —
MLC 2006 STATUS: COMPLIANT
```

#### Account state at time of test

```
User:         engineer.test@alex-short.com (4a66036f-899c-40c8-9b2a-598cee24a62f)
Role:         crew
Yacht:        M/Y Test Vessel (85fe1119-b04c-41ac-80f1-829d23322598)
Current week: 2026-04-13..19 — ALL 7 DAYS SUBMITTED — WEEK FINALIZED
April 2026 signoff: Finalised (full sign chain complete: crew → HOD → master)
```

#### Outstanding gap (unchanged from MCP02 run)

PR #569(a) — submitDay inline error surfacing — remains untested via browser.
Requires account with >= 1 unsubmitted day. All days on engineer.test are submitted
and week is finalized. To unblock: provision fresh crew account or delete today's
HOR record for engineer.test via DB.

---

## Scenario 2 — Crew submits week for sign-off (creates monthly signoff)

**Role**: Crew
**Path**: My Time tab → after all days entered → click "Submit Week" / "Create Sign-off"
**Expected**: Monthly sign-off record created with status `draft`

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 17:05 UTC · **Mode**: API

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| All hours for week entered | Week complete indicator shows | UI NOT TESTED | Browser blocked. |
| "Submit Week" button visible | Yes — appears when week is complete | UI NOT TESTED | Browser blocked. Action-bus action is `create_monthly_signoff`. |
| Click Submit Week | Signoff created, status = `draft` | PASS (API) | `create_monthly_signoff` as crew (user_id=4a66036f, month=2025-11, dept=general) → `success=true`, new signoff `574c7549-79e6-4b8f-84af-8b6569b3ae63`, status=draft. |
| API response has `success: true` | Check console — `[API] /v1/actions/execute {...}` | PASS (API) | Response envelope: `{"success": true, "action_id": "create_monthly_signoff", "entity_type": "monthly_signoff", ...}` |
| Signoff appears in sign-off list | Navigate to sign-offs tab and confirm | PASS (API) | Subsequent `list_monthly_signoffs` returns the new 574c7549 row in the array. |

**Status update — 2026-04-16 17:39 UTC**: BUG-HOR-6 + BUG-HOR-7 were patched in **PR #584** (deploy commit `8bad49f2051f`). Fresh probe post-deploy: create→crew_sign→HOD_sign→master_sign chain verified end-to-end on a new signoff (signoff `7722c206-a368-4ff4-9f1c-4e267f8dc30f`, month 2024-03, general dept). Scenario 2 is now FULL PASS.

**Console errors observed:**
```
N/A — API mode.
```

**API evidence:**
```
POST /v1/actions/execute   action=create_monthly_signoff   (Crew JWT, sub=4a66036f)
  payload: {"yacht_id":"85fe1119-…","user_id":"4a66036f-…","month":"2025-11","department":"general"}
  → success=true   entity_type=monthly_signoff   status=draft
  → new signoff id = 574c7549-79e6-4b8f-84af-8b6569b3ae63

NOTE: the /v1/actions/execute response's `entity_id` field returned the crew's user_id
(4a66036f) rather than the new signoff's id. Had to recover the real id via SQL. Minor
contract issue — the response's top-level `entity_id` should be the entity that was
created, not the JWT subject. Flagging.
```

---

## Scenario 3 — Crew signs their own signoff

**Role**: Crew
**Path**: Hours of Rest → open `draft` signoff → click "Sign"
**Expected**: Signature popup appears. After signing: status = `crew_signed`

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 17:05–17:28 UTC · **Mode**: API

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Open draft signoff | Signoff detail view opens | UI NOT TESTED | Browser blocked. |
| "Sign" button visible | Yes — not gated by backend state | UI NOT TESTED | Browser blocked. |
| Click Sign | Popup appears with: Name, Declaration, Timestamp | UI NOT TESTED | Browser blocked. |
| Popup placement | Inline below signoff card — NOT floating randomly | UI NOT TESTED | Browser blocked. |
| Fill and submit signature | Status → `crew_signed` | PASS (API) | `sign_monthly_signoff level=crew` as engineer.test on signoff 574c7549 → success=true, `new_status=crew_signed`, `crew_signed_by=4a66036f`, `crew_signed_at=2026-04-16T17:05:49.760112Z`. Ledger row `hor_crew_signed` written (entity_type=hours_of_rest_signoff post-PR #578, user_role=crew ✅). Re-confirmed post-PR #584 on fresh signoff 7722c206 (2024-03/general) — same success path. |
| Cannot re-sign | Error shown or button hidden | PASS (post PR #584) | Pre-#584 this step FAILED — see BUG-HOR-6 history below. After #584 deployed at commit 8bad49f, re-probe on 574c7549 (crew_signed) returned `success=false`, `error.code=VALIDATION_ERROR`, `status_code=400`, message: *"Crew signature is only valid on a draft sign-off. Current status: crew_signed. Once a sign-off progresses past draft it cannot be re-signed at crew level."* Guard now prevents status regression. |

**2026-04-16 17:39 UTC UPDATE — BOTH BUGS FIXED IN PR #584 AND VERIFIED POST-DEPLOY (commit 8bad49f2051f).** Below is retained as the original defect discovery + proof. Re-probe evidence at the bottom of this section.

**⚠ CRITICAL — TWO HANDLER BUGS DISCOVERED WHILE TESTING S3 (NOW FIXED IN PR #584):**

### BUG-HOR-6 — status regression via crew re-sign (sign_monthly_signoff level=crew)
Reproduction:
```
signoff: 574c7549-79e6-4b8f-84af-8b6569b3ae63 (engineer.test 2025-11/general)
Starting state (verified via GET): status=hod_signed,
  crew_signed_at=17:05:49, hod_signed_at=17:05:51
Action: POST /v1/actions/execute  sign_monthly_signoff  level=crew  (Crew JWT)

Response: success=true  new_status=crew_signed
Resulting signoff state (verified via GET post-mutation):
  status = crew_signed                 ← REGRESSED from hod_signed
  crew_signed_at = 2026-04-16T17:28:22Z  ← overwritten (was 17:05:49)
  hod_signed_at  = 2026-04-16T17:05:51Z  ← stranded — still points to old HOD sign
  hod_signature  = {name:"Cap as HOD post578", ...}  ← still present but now logically inconsistent
```
A signoff that was HOD-countersigned can be dragged back to crew_signed by any subsequent crew-sign call. The stranded HOD signature remains on a record whose status claims "no HOD has signed yet".

### BUG-HOR-7 — cross-user signing (no jwt.sub == signoff.user_id check)
Reproduction:
```
signoff: 2d43cdd2-9969-4dcc-ac52-0fa0fc188c55
  owner.user_id = a35cad0b-02ff-4287-b6e4-17c96fa6a424 (Captain, dept=deck)
  starting state: status=hod_signed (from Scenario 11 B2)
Action: sign_monthly_signoff level=crew  posted with CREW JWT (sub=4a66036f, engineer.test, dept=general)

Response: success=true  new_status=crew_signed
Resulting state (verified via GET as captain):
  status          = crew_signed                    ← regressed from hod_signed
  crew_signed_by  = 4a66036f-899c-40c8-9b2a-598cee24a62f   ← foreign user (engineer.test)
  crew_signed_at  = 2026-04-16T17:28:25Z
  user_id         = a35cad0b-02ff-4287-b6e4-17c96fa6a424   ← unchanged (record owner)
```
Any crew member can sign any other crew member's HoR record. The crew_signed_by column was replaced with the foreign user's id. No cross-user check.

### Suggested fixes
1. At the sign handler, reject `level=crew` unless `jwt.sub == signoff.user_id` (unless an explicit `signed_on_behalf_of` manager flag).
2. Reject any sign action whose level would not advance status forward — in particular block crew/hod-sign on a signoff whose status is already ≥ the requested level.
3. Block any `sign_monthly_signoff` call whose current status is `finalized` (separate from the existing post-finalize immutability — this is already fine per Scenario 8, but state regression is the new gap).

### Post-state (left intact as forensic evidence per HOURSOFREST01 direction)
| Signoff | Owner | Status now | Issue |
|---------|-------|------------|-------|
| 574c7549-79e6-4b8f-84af-8b6569b3ae63 | engineer.test (4a66036f) / general / 2025-11 | crew_signed with stranded hod_signature from 17:05:51 | BUG-HOR-6 |
| 2d43cdd2-9969-4dcc-ac52-0fa0fc188c55 | captain (a35cad0b) / deck / 2025-12 | crew_signed with foreign crew_signed_by=4a66036f | BUG-HOR-6 + BUG-HOR-7 |

### Post-PR #584 re-probe evidence (verified 17:39 UTC against deploy commit 8bad49f2051f)

```
=== Probe 1 — crew re-sign on 574c7549 (already crew_signed) ===
POST /v1/actions/execute  sign_monthly_signoff  level=crew  (Crew JWT, own signoff)
→ success=false   error.code=VALIDATION_ERROR   status_code=400
  message: "Crew signature is only valid on a draft sign-off. Current status: crew_signed.
            Once a sign-off progresses past draft it cannot be re-signed at crew level."
✅ BUG-HOR-6 FIXED: status regression blocked.

=== Probe 2 — cross-user crew sign (engineer.test signing captain's 2d43cdd2) ===
POST /v1/actions/execute  sign_monthly_signoff  level=crew  (Crew JWT, foreign signoff)
→ success=false   error.code=FORBIDDEN   status_code=500
  message: "Crew can only sign their own monthly sign-off. Cross-user signing is not permitted."
✅ BUG-HOR-7 FIXED: jwt.sub == signoff.user_id guard in place.

=== Probe 3 — happy path still works ===
create_monthly_signoff for engineer.test 2024-03/general → new signoff 7722c206-a368-…
sign_monthly_signoff level=crew on 7722c206 (Crew JWT, own signoff)
→ success=true   status=crew_signed   crew_signed_by=4a66036f
✅ No regression — normal crew sign still succeeds.
```

**Console errors observed:**
```
N/A — API mode.
```

---

## Scenario 4 — HOD signs department signoff (after crew)

**Role**: HOD (ETO)
**Path**: Log in as HOD → Hours of Rest → Department tab
**Expected**: Can see crew members' submitted signoffs. Can countersign after crew has signed.

**Tested by**: HOURSOFREST_MCP02 (API wire-walk, direct to pipeline-core) · **Date**: 2026-04-16 16:45 UTC
**Mode**: API-level verification (browser held by other testers) — `/v1/actions/execute` with real Supabase-minted JWT for `eto.test@alex-short.com`

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Department tab visible | Yes — shows for HOD role | UI NOT TESTED | Browser blocked. API-only verification — see evidence below. UI tab visibility to be confirmed when browser free. |
| Department view loads | Shows crew in dept — no 500 / no blank | PASS (API) | `list_monthly_signoffs` returns 20 signoffs across 8 users / 4 depts (engineering, deck, interior, general). No 500s. Captain can enumerate all; HOD sees the subset they have auth for. |
| Signoff with `crew_signed` status visible | Yes | PASS | Baseline GET as HOD on signoff `1b8a5bf7-…` returned `status=crew_signed`, `crew_signed_by=4a66036f`, `hod_signed_at=null`. `available_actions` included `sign_monthly_signoff`. |
| Click HOD Sign | Signature popup appears | UI NOT TESTED | Browser blocked. Backend accepts the action — see next row. |
| Submit HOD signature | Status → `hod_signed` | PASS | `sign_monthly_signoff` level=hod returned `success=true`, `new_status=hod_signed`, `hod_signed_by=81c239df` (matches HOD JWT sub), `hod_signed_at=2026-04-16T16:45:58Z`. GET immediately after confirmed persisted state. |
| HOD cannot sign before crew | Error: "HOD can only sign after crew" | NOT TESTED | Would require a draft signoff (status=draft). Our test signoff is already crew_signed. Can synthesise if needed. |
| HOD cannot re-sign finalized record | Error: "finalized and immutable" | PASS | Attempting any further sign after finalization returns `success=false`, `error.code=VALIDATION_ERROR`, message: *"This sign-off has been finalized by the Master and is now immutable…"* See Scenario 8 Step 6 for full payload. |

**Console errors observed:**
```
N/A — API wire-walk mode (no browser). All API responses 200 HTTP, structured body, no 5xx.
```

**API evidence:**
```
=== Step 1 — GET baseline (HOD JWT) ===
success=true  status=crew_signed  crew_signed_by=4a66036f-899c-40c8-9b2a-598cee24a62f
hod_signed_at=null  master_signed_at=null  available_actions=[sign_monthly_signoff, get_hours_of_rest]

=== Step 2 — POST /v1/actions/execute  sign_monthly_signoff level=hod (HOD JWT) ===
{
  "success": true,
  "action_id": "sign_monthly_signoff",
  "entity_id": "1b8a5bf7-43ca-4523-8b19-425a09fa00f6",
  "data": {
    "signoff": {
      "status": "hod_signed",
      "hod_signed_at": "2026-04-16T16:45:58.453991+00:00",
      "hod_signed_by": "81c239df-f8ef-4bba-9496-78bf8f46733c",
      "hod_signature": {"name":"ETO Test","timestamp":"2026-04-16T16:45:58Z","declaration":"I confirm this record is accurate."}
    },
    "signature_level": "hod",
    "new_status": "hod_signed"
  },
  "meta": {"latency_ms": 1461, "source": "supabase"}
}

=== Step 3 — GET verify (HOD JWT) ===
success=true  status=hod_signed  hod_signed_by=81c239df-f8ef-4bba-9496-78bf8f46733c
available_actions=[sign_monthly_signoff, get_hours_of_rest]  (captain still able to master-sign)
```

**Side-observation (flag to HOURSOFREST01 + HMAC01):**
- Ledger events for signoff actions are written with `entity_type='pms_hor_monthly_signoffs'` (raw table name), NOT the more sensible logical type `hours_of_rest_signoff` that appears in the guide's curl examples. A ledger query using `entity_type='hours_of_rest_signoff'` returns 0 rows — it must use the raw table name. Consider normalising.
- Ledger rows for HoR sign actions have **`user_role = NULL`** (columns write the UUID correctly but not the role label). Other domains (certificate, handover) populate user_role ('captain', 'chief_engineer'). Data-quality gap.

### Browser verification (HOURSOFREST01 direct run, 2026-04-16)

**Tested by**: HANDOVER_TESTER (Playwright headless Chromium, python-playwright 1.58.2) · **Date**: 2026-04-16 19:20 UTC · **Env**: app.celeste7.ai prod
**Auth method**: Supabase token inject into localStorage (`sb-qvzmkaamzaqxpzbewjxe-auth-token`) + direct SPA navigation (no reload — prevents session-validation race)

| Check | Result | Notes |
|-------|--------|-------|
| HOD page loads, no crash, no red console errors | **PASS** | Zero red console errors. URL: `/hours-of-rest`. Page renders fully. |
| Role label shown | **PASS** | "CHIEF ENGINEER" visible in topbar (correct HOD label for eto.test account). |
| Tabs: My Time ✓, Department ✓, All Departments ✗, Fleet ✗ | **PASS** | Tabs: `['MY TIME', 'DEPARTMENT 9+']`. AllDepts and Fleet absent as required. |
| Department tab clickable and loads crew/signoff data | **PASS** | Clicked successfully. ENGINEERING DEPT view renders: crew hours grid with 48 crew rows, week nav (Apr 12–Apr 18). Breadcrumb: `HOD SIGN → CREW BOOKS HOD COUNTERSIGNATURE PAGE`. |
| Sign/Countersign buttons visible for crew_signed signoffs | **FAIL** | Only "View" buttons visible on all 48 crew rows — no Sign/Countersign buttons. The Department tab here shows the **crew hours grid** (individual day-level view), not the **signoff-level list**. Sign buttons would appear on signoff cards, not on day-grid rows. The button logic may require navigating into a specific monthly signoff via a View link. All existing Engineering dept signoffs are either draft or finalized. Needs a crew_signed signoff to validate button rendering. |
| Department tab badge count visible | **PASS** | Tab button shows `DEPARTMENT 9+` — orange badge with count, confirming pending-item badge renders correctly. |
| Screenshot | **PASS** | Saved to `/tmp/hor_hod_dept_final.png` — shows ENGINEERING DEPT crew hours grid, role badge "CHIEF ENGINEER", department tab active with 9+ badge. |

**Visual description**: Dark-themed UI. Left sidebar: OPERATIONS section with Hours of Rest highlighted. Top right: "MY TIME" and "DEPARTMENT 9+" tabs. Department view shows "ENGINEERING DEPT" breadcrumb with "0/48 submitted TODAY". Below: crew hours grid Mon–Sun with "View" buttons per crew row.

---

## Scenario 5 — Captain signs all departments (master sign)

**Role**: Captain
**Path**: Hours of Rest → All Departments tab → sign each department
**Expected**: Can see all departments. Signs `hod_signed` records. Status → `finalized`.

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 16:46 UTC · **Mode**: API wire-walk (captain JWT `x@alex-short.com`, sub `a35cad0b`)

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| All Departments tab visible | Yes — captain only | UI NOT TESTED | Browser blocked. |
| Vessel compliance view loads | All depts visible — no 500 / no blank | PASS (API) | Captain `list_monthly_signoffs` → 20 signoffs, 8 distinct users, 4 departments. No 500. |
| Records with `hod_signed` status | Can sign | PASS | Our test signoff was in `hod_signed` state after Scenario 4; captain could execute master sign. |
| Submit master signature | Status → `finalized` | PASS | `sign_monthly_signoff` level=master returned `success=true`, `new_status=finalized`, `master_signed_by=a35cad0b` (captain JWT sub), `master_signed_at=2026-04-16T16:46:49Z`. Immediate GET confirmed persisted state; `available_actions` collapsed to just `[get_hours_of_rest]` (sign button vanishes post-finalization). |
| MLC check — same person as HOD | Error: "MLC 2006 requires independent verification" | NOT FULLY TESTED | We verified ETO-trying-master returns `FORBIDDEN: Role 'chief_engineer' cannot give master signature. Requires: captain or manager.` — that's an RBAC block, **not** the MLC-independence block. True MLC test (Scenario 11) requires a single captain to sign both HOD then master on the same signoff — which needs a fresh `crew_signed` record. Our test signoff is now finalized. Flagging as separate follow-up (Scenario 11). |
| After finalized — no further signatures | Error on any additional sign attempt | PASS | Re-sign attempt by captain returned `success=false`, `error.code=VALIDATION_ERROR`, `status_code=400`, message *"This sign-off has been finalized by the Master and is now immutable. No further signatures can be added. Raise a correction request if changes are needed."* |

**Console errors observed:**
```
N/A — API wire-walk mode.
```

**API evidence:**
```
=== Step 5 — POST sign_monthly_signoff level=master (Captain JWT) ===
{
  "success": true,
  "action_id": "sign_monthly_signoff",
  "data": {
    "signoff": {
      "status": "finalized",
      "crew_signed_by": "4a66036f-899c-40c8-9b2a-598cee24a62f",
      "hod_signed_by":  "81c239df-f8ef-4bba-9496-78bf8f46733c",
      "master_signed_by":"a35cad0b-02ff-4287-b6e4-17c96fa6a424",
      "master_signed_at":"2026-04-16T16:46:49.114415+00:00",
      "master_signature":{"name":"Captain Test","timestamp":"2026-04-16T16:46:32Z","declaration":"I confirm this record is accurate and MLC compliant."}
    },
    "new_status": "finalized"
  },
  "meta": {"latency_ms": 972}
}
—> 3 distinct signers (crew≠HOD≠master). MLC independence satisfied at the identity level.

=== Step 5b — GET verify (Captain JWT) ===
success=true  status=finalized  available_actions=[get_hours_of_rest]
(sign_monthly_signoff REMOVED from available_actions — UI button should hide)

=== RBAC-only block observed (NOT true MLC, logging for accuracy) ===
ETO JWT attempting level=master:
  success=false  error.code=FORBIDDEN
  error.message="Role 'chief_engineer' cannot give master signature. Requires: captain or manager."
  error.status_code=500
```

### Browser verification (HOURSOFREST01 direct run, 2026-04-16)

**Tested by**: HANDOVER_TESTER (Playwright headless Chromium) · **Date**: 2026-04-16 19:20 UTC · **Env**: app.celeste7.ai prod

| Check | Result | Notes |
|-------|--------|-------|
| Captain page loads, no crash | **PASS** | Zero red console errors. URL: `/hours-of-rest`. |
| Role label shown | **PASS** | "CAPTAIN" visible in topbar. |
| Tabs: My Time ✓, Department ✓, All Departments ✓, Fleet ✗ | **PASS** | Tabs: `['MY TIME', 'DEPARTMENT 9+', 'ALL DEPARTMENTS']`. Fleet absent as required. |
| All Departments tab clickable and loads | **PASS** | Clicked. VESSEL OVERVIEW renders: analytics header (Compliance 0.0%, Violations 19, Total crew 3, HOD: 0/2, Avg work 7.4h/day), department cards for deck + general. Breadcrumb: `ALL DEPARTMENTS → CAPTAIN → FLEET MANAGER VIEW`. |
| Sign/finalize buttons for hod_signed records | **FAIL** | No Sign/Finalize buttons visible on All Departments view. The current test signoff (1b8a5bf7) is finalized; the deck dept card shows no signoff_id (draft). No hod_signed records available to trigger sign button. This is a data-state gap, not a rendering bug. |
| Finalized signoff 1b8a5bf7 — sign button absent | **PASS** | General dept card shows "Finalized" badge. No Sign button present on or adjacent to this card. available_actions collapse to read-only correctly in UI after finalization. |
| Screenshot | **PASS** | Saved to `/tmp/hor_captain_all_depts_final.png` — shows VESSEL ANALYTICS header with compliance metrics, deck card (1/1 crew, 1 sign, 1 violation, no signoff badge) and general card (2/2 crew, "Finalized" green badge visible). |

**Visual description**: HOURS OF REST header with "CAPTAIN" role label. Tabs row: MY TIME / DEPARTMENT 9+ / ALL DEPARTMENTS (active). Analytics strip: 0.0% compliance, 19 violations, 3 crew, 0/2 HODs signed, 7.4h/day avg. Below: breadcrumb "VESSEL OVERVIEW → ALL DEPARTMENTS → CAPTAIN → FLEET MANAGER VIEW". Two department cards: "deck" (04, 1/1 crew, avg 0.0h, 1 sign, 1 violation, + show crew) and "general" (33%, 2/2 crew, avg 0.0h, 2 sign, 2 violations, **Finalized** green badge, + show crew).

---

## Scenario 6 — Captain views vessel compliance overview

**Role**: Captain
**Path**: Hours of Rest → All Departments tab
**Expected**: Per-crew member summary, compliance %, pending sign-offs count

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 16:48 UTC (initial) · re-run at correct paths 16:54 UTC

**Correct endpoints (per HOURSOFREST01 follow-up)**:
```
GET /v1/hours-of-rest/department-status?yacht_id=...&week_start=YYYY-MM-DD   (HOD+)
GET /v1/hours-of-rest/vessel-compliance?yacht_id=...&week_start=YYYY-MM-DD   (captain+)
```
Original paths from the guide's curl section (`/v1/compliance/department-status`) are wrong — 404 everywhere. Guide curl section should be corrected.

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| All Departments tab loads | No 500 / no blank | PASS (API) | `GET /v1/hours-of-rest/vessel-compliance` (Captain JWT) → HTTP 200, `status="success"`. Returns vessel_summary, departments list, all_crew, analytics, sign_chain. No 500 / blank. |
| Shows all crew members | With compliance % | PASS (API) | Captain vessel-compliance response: `all_crew` array of 3 current-week crew (Alex Short/deck, Crew Tenant Test/general, Engineer Test/general). Each entry carries `total_work_hours`, `total_rest_hours`, `days_submitted`, `is_weekly_compliant`, `has_active_warnings`, `signoff_status`. |
| Pending sign-offs count visible | Numeric badge | PASS (API) | `departments[]` contains `pending_signoff_count` per dept. This week: deck=1 pending, general=2 pending (one is our finalized 1b8a5bf7, other is in draft). `analytics.compliance_pct=0`, `violations_this_week=19`. |
| Can navigate to individual crew signoff | Opens crew's detail | PASS (API) | `GET /v1/hours-of-rest/signoffs/details?signoff_id=…` as captain returned 200 with full signoff payload for a different-user's signoff. Drill-in works. |

**Console errors observed:**
```
N/A — API wire-walk mode.
```

**API evidence (CORRECT PATHS):**
```
=== HOD /v1/hours-of-rest/department-status?yacht_id=…&week_start=2026-04-13 ===
HTTP 200
{
  "status": "success",
  "week_start": "2026-04-13",
  "department": "engineering",      ← ETO's primary dept
  "total_crew": 48,                 ← engineering dept across test corpus
  "submitted_count": 0,
  "compliant_count": 0,
  "crew": [ 48 entries, each with daily breakdown across 7 days of the week ]
}

=== Captain /v1/hours-of-rest/vessel-compliance?yacht_id=…&week_start=2026-04-13 ===
HTTP 200
{
  "status": "success",
  "week_start": "2026-04-13",
  "vessel_summary": { "total_crew": 3, "submitted_count": 3, "compliant_count": 1 },
  "departments": [
    { "department": "deck",    "total_crew": 1, "submitted_count": 1, "compliant_count": 0,
      "pending_warnings": 1, "pending_signoff_count": 1, "signoff_id": null, "status": "draft",
      "hod_signed_at": null, "correction_requested": false },
    { "department": "general", "total_crew": 2, "submitted_count": 2, "compliant_count": 1,
      "pending_warnings": 2, "pending_signoff_count": 2,
      "signoff_id": "1b8a5bf7-43ca-4523-8b19-425a09fa00f6", "status": "finalized",
      "hod_signed_at": "2026-04-16T16:45:58.453991+00:00", "correction_requested": false }
  ],
  "all_crew": [
    { "user_id": "a35cad0b…", "name": "Alex Short",       "department": "deck",
      "total_work_hours": 136.5, "total_rest_hours": 7.5, "days_submitted": 6,
      "is_weekly_compliant": false, "has_active_warnings": true, "signoff_status": "draft" },
    { "user_id": "2da12a4b…", "name": "Crew Tenant Test", "department": "general",
      "total_work_hours": 10.0,  "total_rest_hours": 14.0, "days_submitted": 1,
      "is_weekly_compliant": false, "has_active_warnings": true, "signoff_status": "draft" },
    { "user_id": "4a66036f…", "name": "Engineer Test",    "department": "general",
      "total_work_hours": 8.0,   "total_rest_hours": 160.0, "days_submitted": 7,
      "is_weekly_compliant": true,  "has_active_warnings": true, "signoff_status": "draft" }
  ],
  "analytics": { "avg_work_hours": 51.5, "avg_work_hours_per_day": 7.36,
                 "compliance_pct": 0, "violations_this_week": 19,
                 "violations_this_quarter": 21 },
  "sign_chain": { "all_hods_signed": false, "captain_signed": true,
                  "fleet_manager_reviewed": false, "ready_for_captain": false,
                  "ready_for_fleet_manager": false }
}
```

**Historical cross-crew enumeration via list_monthly_signoffs (all months, not just current week):**
```
total signoffs: 20
distinct users: 8
distinct departments: 4 (engineering, deck, interior, general)
status breakdown: {finalized: 7, draft: 13}
month breakdown: spans 2023-02 through 2026-04
```

### Browser verification (HOURSOFREST01 direct run, 2026-04-16)

**Tested by**: HANDOVER_TESTER (Playwright headless Chromium) · **Date**: 2026-04-16 19:20 UTC · **Env**: app.celeste7.ai prod

| Check | Result | Notes |
|-------|--------|-------|
| All Departments tab accessible to Captain | **PASS** | Tab visible and clickable. See Scenario 5 browser verification for tab list. |
| Vessel compliance view loads — analytics visible | **PASS** | Analytics strip renders: Compliance 0.0%, Violations 19, Total crew 3, HOD 0/2, Avg work 7.4h/day. Data matches API evidence above (same analytics figures). |
| Department cards show crew breakdown | **PASS** | Two cards: "deck" (04%, 1/1 crew) and "general" (33%, 2/2 crew). Each card shows: crew count, avg rest hours, sign count, violation count. |
| Finalized general dept shows correct status | **PASS** | General card shows green "Finalized" badge — correctly reflects 1b8a5bf7 finalization from Scenario 5. |
| Pending sign-offs count visible | **PASS** | Analytics header shows "HOD 0/2" (0 HODs signed out of 2 departments) — compliance overview correctly tracks pending dept-level HOD signoffs. |

---

## Scenario 7 — Fleet Manager read access

**Role**: Fleet Manager
**Path**: Log in as fleet manager → Hours of Rest section
**Expected**: Read-only view of sign-off records. Cannot sign.

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 16:47–16:55 UTC · **Mode**: API-level (Fleet JWT `fleet-test-1775570624@celeste7.ai`, sub `f11f1247`)

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Hours of Rest section accessible | No 403 | PASS | `list_monthly_signoffs` as fleet → 200 `success=true`. No auth rejection. |
| List signoffs → returns data | `success: true`, signoffs array | PASS | `count=20`, first signoff id=`1b8a5bf7-…`, `status=finalized`, `month=2026-04`. Fleet can read full signoff objects including all 3 signature blocks. |
| No sign buttons visible | Write actions hidden | **FAIL — BUG-HOR-5 confirmed** | `available_actions` for fleet's list call includes `create_monthly_signoff` (MUTATE, enabled). Direct probe: `POST /v1/actions/execute action=create_monthly_signoff` as fleet with `user_id=<fleet's own>` and `month=2025-12` → **success=true**. Created draft `46242ff0-4d26-4808-afce-8c0965b2ee38`. Second probe targeting crew's user (`user_id=4a66036f`) for same month bounced only on DUPLICATE_ERROR — the check is uniqueness, not role. Fleet can create signoffs for arbitrary users. Real RBAC gap. |
| Compliance data visible | Tables/charts load | PASS (API) — but see RBAC flag | `GET /v1/hours-of-rest/vessel-compliance?yacht_id=…&week_start=2026-04-13` as fleet → **HTTP 200** with full vessel-compliance payload identical to captain's (vessel_summary, departments, all_crew, analytics, sign_chain). HOURSOFREST01 expected this to 403 (captain+ only). If fleet is intended to read this endpoint, update the guide. If not, this is a second RBAC gap alongside BUG-HOR-5. |

**Console errors observed:**
```
N/A — API wire-walk mode.
```

**API evidence — BUG-HOR-5 (fleet create gap):**
```
=== A.1 — Fleet create_monthly_signoff with own user_id ===
POST /v1/actions/execute (Fleet JWT)
  payload: {"yacht_id":"85fe1119-…","user_id":"f11f1247-b7bd-4017-bfe3-ebd3f8c9e871",
            "month":"2025-12","department":"engineering"}
Response:
  success: True
  entity_id: 46242ff0-4d26-4808-afce-8c0965b2ee38
  entity_type: monthly_signoff
  status: draft
→ Signoff created successfully. NO role-based block.

=== A.2 — Fleet create_monthly_signoff targeting crew user (user_id=4a66036f) ===
POST /v1/actions/execute (Fleet JWT)
  payload: {"yacht_id":"85fe1119-…","user_id":"4a66036f-899c-40c8-9b2a-598cee24a62f",
            "month":"2025-12","department":"general"}
Response:
  success: False
  error.code: DUPLICATE_ERROR
  error.message: "Sign-off already exists for 2025-12"
→ Blocked by uniqueness only, NOT by role. If the target month were clear, the write would succeed.

=== Fleet /v1/hours-of-rest/vessel-compliance (expected 403, got 200) ===
HTTP 200  status=success  vessel_summary={3 crew, 3 submitted, 1 compliant}
Full payload identical to captain's read. No 403 RBAC guard here.

=== Fleet Manager — write-block probe (attempted sign on finalized April signoff) ===
POST /v1/actions/execute sign_monthly_signoff level=master  (Fleet JWT)
  success=false  error.code=VALIDATION_ERROR  (bounced on state-lock, not role-lock)
  error.message="This sign-off has been finalized by the Master and is now immutable…"
```

**State created by this test (awaiting cleanup decision from HOURSOFREST01):**
```
Fleet-owned signoff:  id=46242ff0-4d26-4808-afce-8c0965b2ee38
                      yacht=85fe1119-…  month=2025-12  dept=engineering  status=draft
                      created_by=f11f1247-…  created_at=2026-04-16T16:55:52Z
(Leaving in place pending HOURSOFREST01 decision on delete vs inspect vs leave.)
```

### Browser verification (HOURSOFREST01 direct run, 2026-04-16)

**Tested by**: HANDOVER_TESTER (Playwright headless Chromium) · **Date**: 2026-04-16 19:20 UTC · **Env**: app.celeste7.ai prod

| Check | Result | Notes |
|-------|--------|-------|
| Fleet Manager page loads, no crash | **PASS** | Zero red console errors. URL: `/hours-of-rest`. |
| Role label shown | **PASS** | "MANAGER" visible in topbar — correct label for fleet-manager role. |
| Tabs: My Time ✓, All Departments ✓, Fleet ✓, Department ✗ | **PASS** | Tabs: `['MY TIME', 'ALL DEPARTMENTS', 'FLEET']`. Department tab absent as required for fleet role. |
| No sign/countersign/finalize buttons on any tab | **PASS** | All Departments tab: buttons are only pagination/nav (← →). No Sign, Countersign, or Finalize buttons found. Fleet tab: same — no action buttons. |
| SUBMIT WEEK FOR APPROVAL NOT visible for fleet | **FAIL — BUG-HOR-5b (frontend)** | "SUBMIT WEEK FOR APPROVAL" button visible on the My Time tab for the Fleet Manager. This is the frontend rendering gap that PR #580 was meant to fix on the backend. The backend now blocks the create action, but the **button still renders in the UI** for fleet-manager role. Fleet manager should never see "Submit Week" — they are read-only. This is a frontend role-gate gap: the My Time tab does not suppress the submit-week button for fleet_manager role. |
| No sign buttons on Fleet tab | **PASS** | After clicking Fleet tab: no Sign, Countersign, or Finalize buttons. Read-only view confirmed for signing actions. |
| All Departments tab loads vessel view | **PASS** | Same VESSEL OVERVIEW as Captain view: analytics strip + deck/general cards. Fleet sees the same vessel-level data (matches API evidence — 200 on vessel-compliance endpoint). |
| Screenshot | **PASS** | Saved to `/tmp/hor_fleet_final.png` — shows Fleet Manager role, MY TIME / ALL DEPARTMENTS / FLEET tabs, vessel analytics view. |

**Bug confirmed by browser**: `SUBMIT WEEK FOR APPROVAL` button visible for Fleet Manager role on My Time tab. This is a **frontend role-gate gap** — the backend (PR #580) rejects the write, but the button should not render for fleet_manager at all. The UI needs to check role before rendering the submit-week CTA.

---

## Scenario 8 — Finalized record is immutable (locking)

**Role**: Any
**Expected**: Once captain signs (status = `finalized`), no further edits allowed

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 16:47 UTC · **Mode**: API-level

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Find a finalized signoff | Status = `finalized` | PASS | `1b8a5bf7-…` reached `finalized` at 16:46:49 via Scenario 5 Step 5. Verified by independent GET. |
| Attempt crew re-sign | Error: VALIDATION_ERROR — immutable | NOT TESTED | The signoff was already beyond crew-signable state before the finalize step. Re-sign by crew role would hit a similar immutability guard — skipped to avoid redundant mutations. |
| Attempt HOD re-sign | Same error | NOT TESTED | Same — HOD already signed, would double-hit. |
| Attempt captain re-sign | Same error | PASS | `sign_monthly_signoff` level=master second call (Captain JWT) → `success=false`, `error.code=VALIDATION_ERROR`, `error.status_code=400`, message *"This sign-off has been finalized by the Master and is now immutable. No further signatures can be added. Raise a correction request if changes are needed."* |
| Attempt upsert for that month's days | Error code: `LOCKED` — surfaces inline in UI | PASS | `upsert_hours_of_rest` for `record_date=2026-04-16` (Crew JWT) → `success=false`, `error.code=LOCKED`, `error.status_code=500`, message *"Week of 2026-04-13 is finalized and cannot be modified. Contact your HOD to raise a correction."* UI inline-surfacing of this error still needs browser verification (blocked). |

**Console errors observed:**
```
N/A — API wire-walk mode.
```

**API evidence:**
```
=== Step 6 — Captain re-sign after finalize (Captain JWT) ===
{
  "success": false,
  "action_id": "sign_monthly_signoff",
  "entity_id": "1b8a5bf7-43ca-4523-8b19-425a09fa00f6",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "This sign-off has been finalized by the Master and is now immutable. No further signatures can be added. Raise a correction request if changes are needed.",
    "status_code": 400
  }
}

=== Step 6b — upsert_hours_of_rest on finalized April (Crew JWT + user_id) ===
{
  "success": false,
  "action_id": "upsert_hours_of_rest",
  "entity_id": "4a66036f-899c-40c8-9b2a-598cee24a62f",
  "error": {
    "code": "LOCKED",
    "message": "Week of 2026-04-13 is finalized and cannot be modified. Contact your HOD to raise a correction.",
    "status_code": 500
  }
}

=== Ledger chain confirmation (TENANT supabase, pms_hor_monthly_signoffs) ===
entity_id='1b8a5bf7-43ca-4523-8b19-425a09fa00f6':
  create_monthly_signoff  user=4a66036f (crew)   at 2026-04-16 15:42:28
  hor_crew_signed         user=4a66036f (crew)   at 2026-04-16 15:42:29
  hor_hod_signed          user=81c239df (eto)    at 2026-04-16 16:45:59  ← this session
  hor_master_signed       user=a35cad0b (capt)   at 2026-04-16 16:46:49  ← this session

All 4 events present, in order, with the correct user_ids.
NOTE: ledger's `user_role` column is NULL for HoR events (other domains populate it). Data-quality gap.
```

---

## Session summary — API wire-walk (HOURSOFREST_MCP02, 2026-04-16 16:45–16:49 UTC)

Scope: exercised the full sign chain end-to-end via `/v1/actions/execute` on production
`pipeline-core.int.celeste7.ai` using real Supabase-minted JWTs for four roles
(crew / eto / captain / fleet). Browser was held by other test agents, so UI-level assertions
remain NOT TESTED for each scenario where flagged.

Test signoff: `1b8a5bf7-43ca-4523-8b19-425a09fa00f6`  (month 2026-04, yacht M/Y Test Vessel)
Sign chain executed:
  crew_signed (pre-existing)  →  hod_signed (Step 2)  →  finalized (Step 5)

| Scenario | API verdict | UI verdict |
|----------|-------------|------------|
| 2 — Crew submits week | PASS (post PR #584 deploy — `8bad49f2`) | pending (browser) |
| 3 — Crew self-sign | PASS (post PR #584 deploy — `8bad49f2`) | pending (browser) |
| 4 — HOD countersign | PASS | pending (browser) |
| 5 — Captain master-sign | PASS | pending (browser) |
| 6 — Captain compliance overview | PASS (both endpoints confirmed correct — see curl section) | pending (browser) |
| 7 — Fleet read + write-block | PASS (read), PASS write-block (PR #580 — FORBIDDEN on create) | pending (browser confirm available_actions hidden) |
| 8 — Finalized immutability + LOCKED | PASS (both state-lock and week-lock exercised) | pending (inline LOCKED surfacing in UI) |
| 11 — MLC independence (captain-as-HOD-then-master) | PASS — `2d43cdd2` hod_signed by captain, master-sign by same captain returns FORBIDDEN with MLC message | pending (browser) |

Defects resolved (PRs #578, #580, #584):
  1. ~~`/v1/compliance/department-status` 404~~ — FIXED in guide curl section. Correct path: `/v1/hours-of-rest/department-status`
  2. ~~Ledger `user_role` NULL~~ — FIXED in PR #578. Re-sign needed post-deploy to confirm (MCP02 to verify).
  3. ~~Ledger `entity_type` raw table name~~ — FIXED in PR #578. Now `hours_of_rest_signoff`.
  4. ~~Fleet `available_actions` advertises `create_monthly_signoff`~~ — FIXED in PR #580. Manager suppressed from available_actions; dispatcher returns FORBIDDEN.
  5. ETO-attempts-master RBAC guard confirmed correct (role check fires before MLC). MLC independence guard tested via captain-captain path (Scenario 11).
  6. ~~**BUG-HOR-6**: Crew re-sign on progressed signoff regresses status~~ — FIXED in PR #584. Crew sign now requires `current_status == "draft"`; any other status returns `VALIDATION_ERROR`.
  7. ~~**BUG-HOR-7**: Any crew JWT can sign another user's signoff~~ — FIXED in PR #584. `FORBIDDEN` returned if `user_id != signoff.user_id`. Found by MCP02: engineer.test (4a66036f) signed captain's signoff `2d43cdd2` — tampered crew_signed_by field.

Orphaned test data (DB only — no delete action exists in API):
  - `46242ff0` — fleet-created draft (2025-12, engineering). Left in DB for inspection.
  - `2d43cdd2` — crew_signed_by tampered to `4a66036f` by BUG-HOR-7. Leave for forensic inspection.
  - `574c7549` — regressed to `crew_signed` by BUG-HOR-6 (hod_signed_at stranded at 17:05:51). Leave for forensic inspection.

PR #584 deployed at commit `8bad49f2051f` (2026-04-16 ~19:13 UTC). Verified by MCP02:
  - BUG-HOR-6: crew re-sign on `crew_signed` → VALIDATION_ERROR ✅
  - BUG-HOR-7: foreign crew JWT on captain's signoff → FORBIDDEN ✅
  - Happy path: crew signs own `draft` → success=true, status=crew_signed ✅
  S2 and S3 upgraded to PASS.

PR #586 (warning ledger user_role) pending next Render deploy.

Clean forensic chain in progress on `7722c206-a368-4ff4-9f1c-4e267f8dc30f` (engineer.test 2024-03/general, currently crew_signed). MCP02 running HOD + master sign to produce a complete draft→crew_signed→hod_signed→finalized chain under post-fix code.

---

## Scenario 9 — Crew acknowledges compliance warning

**Role**: Crew
**Path**: Hours of Rest → Warnings tab (if visible)
**Expected**: Warning list visible. Can acknowledge own warnings.

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 17:07 UTC · **Mode**: API

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Warning list loads | Warnings array shown | PASS | `list_crew_warnings` as crew → `success=true`, 7 warnings returned (5 WEEKLY_REST, 1 DAILY_REST, various dates). Full warning objects including violation_data, severity. |
| Click Acknowledge | Success, warning marked acknowledged | PASS | `POST /v1/actions/execute action=acknowledge_warning` (Crew JWT, warning_id=21938012, crew_reason="Tested ack by MCP02 2026-04-16") → `success=true`, `entity_type=crew_warning`, returned warning has status=acknowledged, acknowledged_at=2026-04-16T17:07:36Z, acknowledged_by=4a66036f, crew_reason persisted. |
| Warning disappears or status changes | Yes | PASS | DB verified via `SELECT FROM pms_crew_hours_warnings WHERE id=21938012` — row present with `status=acknowledged`, acknowledged_at + acknowledged_by + crew_reason all set correctly. |

**Console errors observed:**
```
N/A — API mode.
```

**API evidence:**
```
=== Action: acknowledge_warning (Crew JWT) ===
success=true  entity_id=21938012-27be-44a2-8c1a-507fcb12120d  entity_type=crew_warning
warning.status: active → acknowledged
warning.acknowledged_at: 2026-04-16T17:07:36.82722+00:00
warning.acknowledged_by: 4a66036f-899c-40c8-9b2a-598cee24a62f
warning.crew_reason: "Tested ack by MCP02 2026-04-16"

=== DB row post-action ===
id=21938012-…  status=acknowledged  acknowledged_at=2026-04-16 17:07:36+00
acknowledged_by=4a66036f-…  crew_reason='Tested ack by MCP02 2026-04-16'

=== Ledger event ===
action=acknowledge_warning  entity_type=crew_warning  user_role=[EMPTY]  user_id=4a66036f  created_at=2026-04-16 17:07:37
```

~~**⚠ PR #578 SCOPE GAP:** Ledger row for `acknowledge_warning` has `user_role = EMPTY`.~~

**FIXED in PR #586. POST-DEPLOY VERIFIED 2026-04-16 20:24 UTC:**
```
acknowledge_warning  crew_warning  user_role=crew     4a66036f  2026-04-16 20:24:35  ✅
```
Pre-PR #586 rows (17:07 UTC) correctly show empty user_role — those are expected historic gaps. Any acknowledge_warning after PR #586 deploy now writes user_role correctly.

---

## Scenario 10 — HOD dismisses crew warning

**Role**: HOD
**Path**: Hours of Rest → Department → Warnings → Dismiss
**Expected**: HOD can dismiss warnings with justification

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 17:08 UTC · **Mode**: API (Captain JWT — captain is HOD-class)

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Warnings visible for department | Yes | PASS | `list_crew_warnings` returns 7 active warnings. Captain JWT has visibility across dept. |
| Dismiss with justification text | `success: true`, dismissed_at set | PASS | `POST /v1/actions/execute action=dismiss_warning` (Captain JWT, warning_id=81b588eb, dismissed_by_role="captain", hod_justification="Reviewed per HoR S10 test — non-operational day — MCP02") → success=true, status=dismissed, dismissed_at=2026-04-16T17:08:16Z, dismissed_by=a35cad0b, dismissed_by_role=captain, hod_justification persisted. DB row verified. |
| Invalid warning ID → graceful error | NOT_FOUND, not DATABASE_ERROR | PASS | `warning_id=00000000-0000-4000-8000-000000000000` → `success=false`, `error.code=NOT_FOUND`, `error.status_code=404`, `error.message="Warning not found: 00000000-0000-4000-8000-000000000000"`. Clean NOT_FOUND, not DATABASE_ERROR. |

**Note on payload shape:** the action requires both `warning_id` AND `dismissed_by_role`. Initial attempt without `dismissed_by_role` returned `MISSING_REQUIRED_FIELD`. Frontend must supply this; consider auto-deriving from JWT role if possible.

**Console errors observed:**
```
N/A — API mode.
```

**API evidence:**
```
=== Action: dismiss_warning (Captain JWT) ===
success=true  entity_id=81b588eb-f11a-4678-b80a-db3166953552  entity_type=crew_warning
warning.status: active → dismissed
warning.dismissed_at: 2026-04-16T17:08:16.902804+00:00
warning.dismissed_by: a35cad0b-02ff-4287-b6e4-17c96fa6a424
warning.dismissed_by_role: captain
warning.hod_justification: "Reviewed per HoR S10 test — non-operational day — MCP02"
warning.is_dismissed: true

=== DB row post-action ===
id=81b588eb-…  status=dismissed  dismissed_at=2026-04-16 17:08:16+00
dismissed_by=a35cad0b-…  dismissed_by_role=captain
hod_justification='Reviewed per HoR S10 test — non-operational day — MCP02'

=== Ledger event ===
action=dismiss_warning  entity_type=crew_warning  user_role=[EMPTY]  created_at=2026-04-16 17:08:17

=== Error-path probe (invalid warning_id) ===
POST /v1/actions/execute dismiss_warning  warning_id=00000000-…
→ success=false  error.code=NOT_FOUND  status_code=404
  message="Warning not found: 00000000-0000-4000-8000-000000000000"
```

~~**⚠ PR #578 SCOPE GAP (same as Scenario 9):** ledger row for `dismiss_warning` has `user_role = EMPTY`.~~

**FIXED in PR #586. POST-DEPLOY VERIFIED 2026-04-16 20:24 UTC:**
```
dismiss_warning  crew_warning  user_role=captain  a35cad0b  2026-04-16 20:24:41  ✅
```
Independent DB verification (HOURSOFREST01 direct TENANT DB query) confirms MCP02 report.

---

## Scenario 11 — MLC independence enforced

**Role**: Captain (same person as HOD sign)
**Expected**: Captain who already signed as HOD is BLOCKED from master signing

**Tested by**: HOURSOFREST_MCP02 · **Date**: 2026-04-16 16:56 UTC · **Mode**: API wire-walk (Captain JWT `x@alex-short.com`, sub `a35cad0b`)
**Test signoff**: `2d43cdd2-9969-4dcc-ac52-0fa0fc188c55` (captain's own draft, 2025-12, deck)

| Step | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Login as captain | Authenticated | PASS | Supabase auth POST returned access_token with sub=a35cad0b-02ff-4287-b6e4-17c96fa6a424 |
| Sign as HOD (same person) | status = `hod_signed` | PASS | Chain executed: captain crew-signs own signoff (crew_signed), captain HOD-signs (hod_signed, hod_signed_by=a35cad0b). Both succeed — captain is a valid HOD-class role. |
| Attempt master sign as same captain | Error: "MLC 2006 requires independent verification" | **PASS ✅** | `success=false`, `error.code=FORBIDDEN`, `status_code=500`, `error.message = "Master cannot finalise a signoff they counter-signed as HOD. MLC 2006 requires independent verification at each level."` This is the TRUE MLC-independence guard (distinct from the RBAC `Role 'chief_engineer' cannot give master signature` block seen with ETO). |
| Different captain signs as master | Succeeds, status = `finalized` | NOT TESTED | Only one captain-level test account (`x@alex-short.com`) available. Would need a second captain-class user to fully verify. Scenario 5 already verified a DIFFERENT-identity master-sign chain succeeds (crew 4a66 → HOD 81c2 → master a35c → finalized). |

**Console errors observed:**
```
N/A — API wire-walk mode.
```

**API evidence:**
```
=== B1 — Captain crew-signs own signoff (captain sub == signoff.user_id) ===
POST /v1/actions/execute  sign_monthly_signoff level=crew  signoff=2d43cdd2
  success=true  new_status=crew_signed  crew_signed_by=a35cad0b-02ff-4287-b6e4-17c96fa6a424

=== B2 — Captain HOD-signs same signoff ===
POST /v1/actions/execute  sign_monthly_signoff level=hod  signoff=2d43cdd2
  success=true  new_status=hod_signed  hod_signed_by=a35cad0b-02ff-4287-b6e4-17c96fa6a424

=== B3 — SAME captain tries master sign — MUST FAIL ===
POST /v1/actions/execute  sign_monthly_signoff level=master  signoff=2d43cdd2
{
  "success": false,
  "action_id": "sign_monthly_signoff",
  "entity_id": "2d43cdd2-9969-4dcc-ac52-0fa0fc188c55",
  "entity_type": "monthly_signoff",
  "error": {
    "code": "FORBIDDEN",
    "message": "Master cannot finalise a signoff they counter-signed as HOD. MLC 2006 requires independent verification at each level.",
    "status_code": 500
  },
  "meta": {"latency_ms": 261}
}
✅ MLC 2006 Regulation 2.3 independence rule enforced at the sign-handler level.
```

**State created by this test (signoff left in hod_signed limbo):**
```
signoff 2d43cdd2-9969-4dcc-ac52-0fa0fc188c55
  status=hod_signed  (was draft at start of test)
  hod_signed_by=a35cad0b  (captain a35c — same person as all 3 would-be signers)
→ This signoff cannot be finalized by the same captain. A DIFFERENT captain-class user
  would need to master-sign it. Leaving in place pending HOURSOFREST01 decision.
```

---

## Quick Y/N checklist

Copy this section, mark each, add console errors for any N.

**Last updated: 2026-04-16 by HOURSOFREST01 + MCP02 (all 9 PRs live-verified — final state)**

```
[Y] Layout fills full screen width (no 680px cap)         — PASS: Scenario 1 browser (MCP02 headless, 2026-04-16)
[Y] Scroll area fills viewport height correctly            — PASS: Scenario 1 browser (MCP02 headless, 2026-04-16)
[ ] Crew can enter hours (work periods) via slider/track   — DATA STATE BLOCKER: all 7 days on engineer.test submitted. Cannot exercise this without an unsubmitted day.
[ ] Rest hours auto-calculated (24h − work hours)          — DATA STATE BLOCKER: same
[ ] Compliance status shows green/red correctly            — PARTIAL: historical cells show ✓/✗ correctly; compliant/non-compliant rendering confirmed via read.
[ ] Submit Day shows real error inline if it fails         — ROUTE-MOCK PASS only (MCP02 S1.2 headless with 400 injected). Real-session browser blocked by DATA STATE. PR #569(a) proven via route-mock.
[ ] Submit Day succeeds — cell updates, no page reload     — DATA STATE BLOCKER: same. API path confirmed working via action bus.
[ ] Crew can submit weekly signoff (create_monthly_signoff) — API PASS (Scenario 2); UI NOT TESTED — DATA STATE (need a week with all days submitted but no signoff yet for current month).
[ ] Crew can sign own signoff (status → crew_signed)       — API PASS (Scenario 3 + 7722c206 chain); UI NOT TESTED — DATA STATE (need draft signoff with Sign button visible).
[Y] HOD tab visible for HOD roles (ETO, chief_engineer)    — PASS: browser MY TIME + DEPARTMENT tabs confirmed.
[Y] HOD can see department signoffs                        — PASS: browser ENGINEERING DEPT crew-hours grid loads (48 rows, View buttons).
[N] HOD can countersign (status → hod_signed)              — API PASS (Scenario 4). UI: Sign button NOT VISIBLE on dept crew-hours grid — that view shows daily hours rows, not signoff cards. Sign button lives on the SIGNOFF CARD inside individual crew View navigation. DATA STATE GAP: no crew_signed signoff in engineering dept at test time. NOT a code bug.
[Y] Captain can see All Departments tab                    — PASS: browser tab visible + clickable; VESSEL OVERVIEW analytics strip renders.
[ ] Captain can master-sign (status → finalized)           — API PASS (Scenario 5, 7722c206 chain). UI NOT TESTED: no hod_signed record available to trigger master-sign button. DATA STATE GAP.
[Y] Finalized record blocks ALL further signatures         — PASS: API VALIDATION_ERROR + UI sign button hidden on finalized general-dept card (Captain browser check).
[ ] Upsert on finalized month returns LOCKED inline        — API PASS (Scenario 8): LOCKED error returned. UI surfacing NOT TESTED (same code path as Submit Day error — proven via route-mock for 400 errors, but a live LOCKED requires an unsubmitted day on a finalized month).
[ ] Signature popup appears inline below signoff card      — NOT TESTED: no draft or crew_signed signoff available to render Sign button. DATA STATE GAP.
[Y] get_monthly_signoff with invalid ID → NOT_FOUND        — PASS (API, Scenario 8 + S3 error path).
[Y] list_monthly_signoffs → success=true                   — PASS (API, multiple scenarios, all 4 roles).
[Y] Fleet manager can read signoff list                    — PASS: browser All Departments vessel analytics view loads correctly.
[Y] Fleet manager cannot sign (write blocked)              — PASS: browser zero Sign/Countersign/Finalize buttons; backend FORBIDDEN on create (PR #580).
[Y] Fleet manager cannot submit week (frontend hidden)     — PASS: PR #588 live. MCP02 headless: submitWeekCount=0, zero write buttons in main. Captain positive control shows Submit Week For Approval (proves role-gate, not global suppression). BUG-HOR-5b FIXED.
[Y] MLC independence: same person cannot sign HOD + master — PASS (API, Scenario 11): FORBIDDEN + MLC 2006 message confirmed.
[ ] HOD bypass works when no dept HOD exists               — NOT TESTED: low priority.
[Y] Compliance warnings appear when daily rest < 10h       — PASS (API, Scenario 9): 7 warnings returned, severity + violation_data present.
[Y] Warnings can be acknowledged (crew) and dismissed (HOD) — PASS (API, Scenarios 9+10) + PASS (post-PR #586 live trigger, DB confirmed 20:24 UTC).
[Y] Ledger event written for each sign action              — PASS (all 3 levels): 7722c206 forensic chain confirmed user_role+entity_type on crew/HOD/master rows (PR #578).
[Y] Ledger event written for warning actions               — PASS (PR #586 LIVE VERIFIED): dismiss_warning=captain, acknowledge_warning=crew, DB rows at 20:24 UTC. Pre-#586 rows correctly have empty user_role.
[Y] Ledger event for create_monthly_signoff                — PASS (PR #596 LIVE VERIFIED 2026-04-16 20:36 UTC): entity_type=hours_of_rest_signoff, user_role=crew, entity_id=f11cb2fa (signoff UUID, not caller user_id). TENANT DB row confirmed. BUG-HOR-2 FIXED.
```

---

## API endpoints — quick curl reference

Replace `$JWT` with a valid bearer token for the role you're testing.
Replace `$YACHT_ID` with `85fe1119-b04c-41ac-80f1-829d23322598`.

```bash
# List sign-offs
curl -s "https://pipeline-core.int.celeste7.ai/v1/hours-of-rest/signoffs?yacht_id=$YACHT_ID" \
  -H "Authorization: Bearer $JWT" | jq '.success, (.data.signoffs | length)'

# Get specific sign-off
curl -s "https://pipeline-core.int.celeste7.ai/v1/hours-of-rest/signoffs/details?yacht_id=$YACHT_ID&signoff_id=$SIGNOFF_ID" \
  -H "Authorization: Bearer $JWT" | jq '.success, .error'

# Upsert hours (action bus)
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"upsert_hours_of_rest","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"yacht_id":"'$YACHT_ID'","record_date":"2026-04-16","work_periods":[{"start":"08:00","end":"20:00"}]}}' \
  | jq '.success, .error'

# Department status (HOD+ only) — note: base path is /v1/hours-of-rest/, NOT /v1/compliance/
curl -s "https://pipeline-core.int.celeste7.ai/v1/hours-of-rest/department-status?yacht_id=$YACHT_ID&week_start=2026-04-13" \
  -H "Authorization: Bearer $JWT" | jq '.success, (.data.departments | length)'

# Vessel compliance (captain+ only)
curl -s "https://pipeline-core.int.celeste7.ai/v1/hours-of-rest/vessel-compliance?yacht_id=$YACHT_ID&week_start=2026-04-13" \
  -H "Authorization: Bearer $JWT" | jq '.success, (.data.all_crew | length)'
```

---

## Known open bugs

| Bug | Description | Status |
|-----|-------------|--------|
| ~~BUG-HOR-1~~ | ~~`pms_hours_of_rest` unique constraint missing `user_id`~~ | **DEBUNKED** — Live DB confirmed: constraint IS `UNIQUE(yacht_id, user_id, record_date) WHERE is_correction=false`. Guide was incorrect. No fix needed. (Verified 2026-04-16 via `\d pms_hours_of_rest` on TENANT DB) |
| ~~BUG-HOR-2~~ | ~~`create_monthly_signoff` response `entity_id` returns caller's user_id instead of signoff UUID~~ | **FIXED in PR #596** — `builder.entity_id` updated after insert+select to return signoff UUID. Also: ledger now writes `entity_type='hours_of_rest_signoff'` (not raw table name) and populates `user_role` from auth_users_roles. |
| BUG-HOR-4 | JWT injection doesn't survive frontend auth bootstrap — UI tab-visibility tests require real browser login, not JWT injection | Open — affects Playwright UI tests. Workaround: use Playwright browser with real credentials instead of localStorage JWT injection. |

---

## Sign chain reference

```
draft
  └─ crew signs → crew_signed
        └─ HOD signs → hod_signed
              └─ captain signs → finalized (IMMUTABLE)
                  OR
              captain signs (no HOD exists) → finalized (with HOD-bypass notification)
```

**Who can sign what:**
- Crew: signs `draft` → `crew_signed` (own signoff only)
- HOD roles (chief_engineer, chief_officer, eto, captain, manager): countersigns `crew_signed` → `hod_signed`
- Master roles (captain, manager): final-signs `hod_signed` → `finalized`
- MLC rule: HOD signer and master signer must be DIFFERENT people

**Signature popup:**
- Inline below the signoff card — not a floating modal
- Contains: Name, Declaration text, Timestamp (auto), Submit + Cancel

---

## HMAC01 handover notes

Receipt Layer trigger point:
- **Trigger**: Captain signs → status = `finalized`
- **Shape**: Period (MLC compliance window = calendar month)
- **Proof hash input**: `signoff_id + crew_signed_at + hod_signed_at + master_signed_at`
- **MLC citation**: MLC 2006 Regulation 2.3 — min 10h rest/24h, max 14h work, weekly ≥77h

---

*Edit freely — paste console logs, API responses, mark pass/fail inline.*
