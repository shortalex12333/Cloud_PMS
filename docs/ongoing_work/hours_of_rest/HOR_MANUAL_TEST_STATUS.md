# Hours of Rest — Manual Test Status

> **RETIRED 2026-04-19** — Superseded by `HOR_SCENARIO_TEST_GUIDE.md` (reflects PRs #640, #641, #646).

> Generated: 2026-04-16 · All 9 PRs (#567–#596) merged and verified
> **Frontend**: https://app.celeste7.ai — **API**: https://pipeline-core.int.celeste7.ai

---

## Credentials

| Role | Email | Password |
|------|-------|----------|
| Crew | engineer.test@alex-short.com | Password2! |
| HOD (ETO) | eto.test@alex-short.com | Password2! |
| Captain | x@alex-short.com | Password2! |
| Fleet Manager | fleet-test-1775570624@celeste7.ai | Password2! |

---

## Already Verified — Do Not Re-Test

| # | Scenario | How verified | Result |
|---|----------|-------------|--------|
| S1 | Crew week grid loads, layout fills screen | Browser headless Playwright | ✅ PASS |
| S1 | No 680px width cap | Browser: 1317px measured at 1440 viewport | ✅ PASS |
| S1 | Scroll area bounded to viewport (not full page scroll) | Browser: overflowY=auto container, window.scrollY=0 | ✅ PASS |
| S1 | No tab nav for crew (single column only) | Browser: 0 role=tab elements | ✅ PASS |
| S1 | Submit Day inline error on failure (PR #569a) | Route-mock: 400 injected → error under day card | ✅ PASS (route-mock) |
| S2 | Crew creates monthly signoff via "Submit Week" | API: create_monthly_signoff → success=true, status=draft | ✅ PASS (API) |
| S3 | Crew signs own signoff (draft → crew_signed) | API + forensic chain on signoff 7722c206 | ✅ PASS (API) |
| S3 | BUG-HOR-6: crew cannot re-sign a progressed signoff | API: VALIDATION_ERROR returned | ✅ PASS (PR #584) |
| S3 | BUG-HOR-7: crew cannot sign another user's signoff | API: FORBIDDEN returned | ✅ PASS (PR #584) |
| S4 | HOD countersigns (crew_signed → hod_signed) | API: sign_monthly_signoff level=hod → success=true, hod_signed_by=81c239df | ✅ PASS (API) |
| S4 | HOD Department tab visible + ENGINEERING dept loads | Browser: DEPARTMENT 9+ tab, 48 crew rows, View buttons | ✅ PASS (browser) |
| S5 | Captain master-signs (hod_signed → finalized) | API: sign_monthly_signoff level=master → success=true, new_status=finalized | ✅ PASS (API) |
| S5 | All Departments tab visible for captain | Browser: ALL DEPARTMENTS tab + VESSEL OVERVIEW analytics strip | ✅ PASS (browser) |
| S5 | Finalized signoff shows no sign button | Browser: green "Finalized" badge, zero sign buttons | ✅ PASS (browser) |
| S6 | Vessel compliance overview loads for captain | API: GET /vessel-compliance → all crew, per-dept breakdown, analytics | ✅ PASS (API) |
| S6 | Compliance analytics visible in browser | Browser: 0.0%, 19 violations, 3 crew, HOD 0/2 | ✅ PASS (browser) |
| S7 | Fleet manager can read signoff list | API + browser: 20 signoffs returned | ✅ PASS |
| S7 | Fleet manager — zero Sign/Countersign/Finalize buttons | Browser: 0 write action buttons across all tabs | ✅ PASS (browser) |
| S7 | Fleet manager cannot create signoff (backend FORBIDDEN) | API: FORBIDDEN from dispatcher (PR #580) | ✅ PASS (API) |
| S7 | Fleet manager Submit Week button hidden (PR #588) | Browser + headless: 0 submit buttons on My Time tab | ✅ PASS (browser) |
| S8 | Finalized signoff immutable — sign attempt returns error | API: VALIDATION_ERROR "immutable, no further signatures" | ✅ PASS (API) |
| S8 | LOCKED error on upsert of a finalized week | API: error.code=LOCKED returned | ✅ PASS (API) |
| S9 | Warning list loads (crew) | API: 7 warnings returned with severity + violation_data | ✅ PASS (API) |
| S9 | Crew acknowledges warning | API: status=acknowledged, DB row confirmed acknowledged_by + timestamp | ✅ PASS (API) |
| S10 | HOD/captain dismisses warning with justification | API: status=dismissed, dismissed_by_role=captain, hod_justification persisted, DB confirmed | ✅ PASS (API) |
| S10 | Invalid warning ID → NOT_FOUND (not DATABASE_ERROR) | API: clean 404 error response | ✅ PASS (API) |
| S11 | MLC independence: same captain cannot sign both HOD and master | API: FORBIDDEN + "MLC 2006 requires independent verification at each level" | ✅ PASS (API) |
| Ledger | Sign actions write correct user_role + entity_type | TENANT DB: forensic chain on 7722c206 (crew/HOD/master all correct) | ✅ PASS (DB, PR #578) |
| Ledger | Warning actions write correct user_role | TENANT DB: acknowledge=crew, dismiss=captain at 20:24 UTC | ✅ PASS (DB, PR #586) |
| Ledger | create_monthly_signoff writes entity_type + user_role + correct entity_id | TENANT DB: row f11cb2fa at 20:36 UTC — entity_type=hours_of_rest_signoff, user_role=crew, entity_id=signoff UUID | ✅ PASS (DB, PR #596) |

---

## Remaining — Manual Browser Testing Required

All items below are **data-state gaps only**. The code is correct and API-verified. You are testing UI rendering only.

---

### MT-1 — Submit Day button and inline error surfacing

**Role**: Crew (`engineer.test`)
**Scenario**: S1 — real browser submit, not route-mock

**What to check**:
- After clicking the timeline track to add a work period, Submit Day button appears below the day cell
- On success: cell updates without page reload
- On failure: error appears **inline under the day cell** (not a silent revert, not a toast)

**Blocker**: All 7 days on engineer.test are submitted + April 2026 finalized.

**Setup**:
1. Log in as engineer.test → navigate to Hours of Rest
2. Use ← week arrow to find a **past week that is not finalized**
3. If all weeks are finalized: ask for DB deletion of one day record, or use a fresh crew account

**Steps**:
1. Click the timeline bar for that day to add a work period
2. Click "Submit Day"
3. ✅ Expected: cell updates, ✓ Compliant badge appears, no page reload
4. For error path: ask for API mock or network block on submit, then retry

---

### MT-2 — Crew sign button on signoff card (signature popup)

**Role**: Crew (`engineer.test`)
**Scenario**: S3 UI path

**What to check**:
- A draft monthly signoff card has a "Sign" button
- Clicking Sign shows a **signature popup inline below the signoff card** (not a floating modal)
- Popup contains: name field, declaration text, timestamp
- After confirming: card status changes to crew_signed, Sign button disappears

**Setup**:
1. Log in as engineer.test → My Time tab
2. Look for a month that shows "Submit Week For Approval" button — click it to create a draft signoff
3. The monthly signoff card should now be visible with a Sign button
4. If no Submit Week button visible (week not fully submitted): complete MT-1 first

**Steps**:
1. Click Sign on the draft signoff card
2. ✅ Expected: popup appears **below the card**, not floating elsewhere
3. Fill declaration, confirm
4. ✅ Expected: card status → crew_signed, Sign button hidden

---

### MT-3 — HOD countersign button on signoff card

**Role**: HOD (`eto.test`)
**Scenario**: S4 UI path

**What to check**:
- After crew signs, HOD sees a Countersign/HOD Sign button on the signoff card
- The button is inside the crew member's **signoff card view** (accessed via "View" from the dept grid — NOT on the daily crew-hours grid itself)
- After signing: status → hod_signed

**Requires**: MT-2 complete (a crew_signed signoff must exist)

**Steps**:
1. Log in as eto.test → Hours of Rest → Department tab
2. Find the ENGINEERING dept → locate Engineer Test in the crew grid
3. Click "View" on Engineer Test's row
4. Inside that view, find the crew_signed monthly signoff card
5. ✅ Expected: HOD Sign / Countersign button visible on the card
6. Click it, fill signature, confirm
7. ✅ Expected: status → hod_signed

---

### MT-4 — Captain master-sign button on signoff card

**Role**: Captain (`x@alex-short.com`)
**Scenario**: S5 UI path

**What to check**:
- After HOD signs, captain sees a Finalize/Master Sign button on the signoff card
- After signing: status → finalized, button disappears, card shows green "Finalized" badge

**Requires**: MT-3 complete (a hod_signed signoff must exist)

**Steps**:
1. Log in as captain → Hours of Rest → All Departments tab
2. Find the department card that has a hod_signed signoff
3. Click into the crew view for that department
4. ✅ Expected: Master Sign / Finalize button visible on the signoff card
5. Click it, fill signature, confirm
6. ✅ Expected: status → finalized, button gone, green "Finalized" badge shown

---

### MT-5 — Signature popup placement (observe during MT-2/3/4)

**What to check**: Every signature popup (crew sign, HOD countersign, master sign) must appear **inline below the signoff card** — not a floating modal, not a separate page, not a page-level dialog.

**No extra setup needed** — just observe during MT-2, MT-3, MT-4.

---

## Recommended Order

```
1. MT-1  →  find unsubmitted day, Submit Day (crew)
2. MT-2  →  Submit Week → sign draft signoff card (crew)
3. MT-3  →  HOD countersign from dept View (eto)
4. MT-4  →  Captain master-sign (captain)
5. MT-5  →  note popup placement throughout
```

---

## Not Testing (low priority / cannot synthesize without DB work)

| Item | Reason |
|------|--------|
| LOCKED error inline on Submit Day for finalized month | Requires an unsubmitted day inside an already-finalized month — contradictory state |
| HOD bypass when no dept HOD exists | No test data for a department with zero HOD-class users |
| Second captain for MLC independence positive control | Only one captain test account — API path fully verified in S11 |

---

## Sign Chain Reference

```
draft
  └─ crew signs (own signoff only) → crew_signed
        └─ HOD countersigns → hod_signed
              └─ captain master-signs (different person from HOD) → finalized  ← IMMUTABLE
```

**Roles and what they can do**:
- **Crew**: signs `draft` → `crew_signed` (own signoff only, cannot re-sign if progressed)
- **HOD** (chief_engineer, eto, chief_officer, captain, manager): `crew_signed` → `hod_signed`
- **Captain**: `hod_signed` → `finalized` (cannot be same person as HOD signer — MLC 2006)
- **Fleet Manager**: read-only. No sign, no submit, no create.
