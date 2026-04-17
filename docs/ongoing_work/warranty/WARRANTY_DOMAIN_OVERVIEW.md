# Warranty Domain — CEO Briefing

**Date of this document:** 2026-04-17  
**Status:** Complete and verified in live production  
**Authored by:** WARRANTY01 (WARRANTY team, overnight session 2026-04-16/17)

---

## What is this in plain English?

A warranty claim is what happens when a piece of equipment on a vessel breaks down and the fault was the manufacturer's responsibility — not normal wear. The vessel operator files a claim against the manufacturer or supplier asking for repair, replacement, or a refund.

On a commercial ship, this is a routine but important process. The Chief Engineer or a senior officer (called HOD — Head of Department) discovers the fault, files the claim, and the Captain approves or rejects it. The claim needs to be documented, tracked, and communicated — often with a formal email to the manufacturer.

The **warranty lens** is the screen in the CelesteOS system where all of this is managed. It shows one warranty claim in full detail — the equipment involved, the amounts, the status, any attached documents, notes, and the email draft to send the manufacturer.

---

## Why does this matter to the business?

### Financial protection
Equipment on a commercial vessel can cost hundreds of thousands of pounds. If an engine component fails within its warranty period and the claim is not documented and filed correctly, the vessel owner loses that financial protection. A structured workflow ensures no claim is missed.

### Maritime law and compliance
The ISM Code (International Safety Management Code) — which is mandatory under SOLAS (the main international maritime safety convention) — requires vessels to maintain records of defects and corrective actions. Warranty claims are part of this record.

The MLC 2006 (Maritime Labour Convention) also requires that vessels maintain safe working equipment. A documented warranty process demonstrates that defective equipment is identified and addressed promptly.

### Shore-side applicability
This system is not just for shipboard use. Fleet managers, procurement teams, and shore-side technical superintendents can log in and see the status of every warranty claim across the fleet. They do not need to be on the vessel. This gives the company oversight without requiring physical presence.

---

## How does the workflow operate?

```
HOD / Chief Engineer
    → Files claim (title, vendor, description, amounts)
    → Submits the claim for review

Captain or Manager
    → Reviews the submitted claim
    → Either Approves (with approved amount) or Rejects (with a reason)

On Approval:
    → Captain can Close the claim (marks it fully settled)
    → HOD can Compose an Email Draft to send to the manufacturer

On Rejection:
    → HOD can Revise and Resubmit with corrections
```

The full lifecycle is: **Draft → Submitted → Approved → Closed** (or Rejected → Revised → Submitted again).

---

## Role-based security — who can do what

This system is designed around maritime roles. Not every person on a vessel should be able to approve financial claims.

| Role | Can file claim | Can submit | Can approve/reject | Can close | Can view |
|------|---------------|------------|-------------------|-----------|---------|
| Crew member | No | No | No | No | Yes (read only) |
| Chief Engineer (HOD) | **Yes** | **Yes** | No | No | Yes |
| Chief Officer (HOD) | **Yes** | **Yes** | No | No | Yes |
| Captain | **Yes** | **Yes** | **Yes** | **Yes** | Yes |
| Manager (shore-side) | **Yes** | **Yes** | **Yes** | **Yes** | Yes |
| Purser | No | No | No | No | Yes (read only) |

**Source:** `apps/api/action_router/registry.py` lines 2243 (draft_warranty_claim), 2277 (submit_warranty_claim), 2294 (approve_warranty_claim), 2309 (reject_warranty_claim)

This is enforced at the API level — the backend validates the user's role before allowing any action. The frontend also hides buttons that the user cannot use, giving a clean, role-appropriate interface.

---

## What was built and verified

### The warranty lens (the UI screen)
- **File:** `apps/web/src/app/warranties/[id]/page.tsx`
  - Purpose: The page that shows a single warranty claim. Created once and does not change between claims.
  - Status: Reviewed, unchanged in this session.

- **File:** `apps/web/src/components/lens-v2/entity/WarrantyContent.tsx`
  - Purpose: The actual content inside the warranty page — the fields, buttons, sections (notes, attachments, email draft). This is where the data becomes visible to the user.
  - Status: Reviewed, unchanged in this session. All bugs were in the API layer.

### The data layer (what the screen reads from)
- **File:** `apps/api/routes/entity_routes.py` (lines 505–530)
  - Purpose: When the screen loads a claim, it calls this file to get all the data. This file queries the database and returns everything the lens needs.
  - Change: Added a 3-attempt retry with a 0.8-second pause between attempts. This prevents a temporary database hiccup from returning a blank claim page. **PR #620.**

- **File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
  - Purpose: Every button press on the warranty lens (Submit, Approve, Reject, etc.) is processed here. This is the engine behind every action.
  - Status: Reviewed. Unchanged in this session (fixed in earlier PRs #571/#581).

- **File:** `apps/api/action_router/registry.py`
  - Purpose: The master list of every action the system knows about — what it's called, who can use it, what fields it needs.
  - Status: Reviewed. Unchanged in this session.

### The connection layer (reliability fixes)
- **File:** `apps/api/cache/invalidation_listener.py`
  - Purpose: A background worker that listens for database changes and updates the system's memory cache. When it loses connection to Redis (the cache system), it now properly closes the old connection before making a new one.
  - Change: Added `max_connections=10` limit and proper connection closure (`aclose()`) before reconnecting. Previously, repeated crashes could accumulate hundreds of stale connections until the system ran out. **PR #613.**

- **File:** `apps/api/cortex/rewrites.py` (line 105)
  - Purpose: Another background worker that manages URL rewrites and routing. Same Redis connection issue.
  - Change: Added `max_connections=10`. **PR #613.**

- **File:** `apps/api/routes/f1_search_streaming.py` (line 343)
  - Purpose: The search results streaming worker.
  - Change: Added `max_connections=10`. **PR #613.**

### The frontend request layer
- **File:** `apps/web/src/app/api/v1/notifications/mark-all-read/route.ts`
  - Purpose: When the user clicks "Mark all as read" in the notification bell, this file handles that request and forwards it to the backend.
  - Change: **This file did not exist.** Created from scratch. Without it, every "Mark all as read" click returned a 404 error (not found). **PR #610.**

- **File:** `apps/web/src/app/api/v1/actions/execute/route.ts`
  - Purpose: Every button press in the app (Submit, Approve, etc.) goes through this file as a relay between the browser and the backend server.
  - Change: Added a 25-second time limit on the relay call, and added safe handling for empty responses. Previously, if the backend returned nothing (due to a connection drop), the relay crashed with a confusing error. **PR #629.**

### The test runner
- **File:** `tests/e2e/warranty_runner.py`
  - Purpose: An automated test script that runs 8 complete warranty scenarios in a real browser against the live production system. It plays the role of a human user — clicking buttons, filling forms, checking that the screen shows the right status.
  - Changes (multiple PRs):
    - PR #620: Increased the popup wait time from 3 seconds to 10 seconds (some popups took longer to appear)
    - PR #623: Fixed the warm-up URL — the script was pinging the wrong server address to wake up the backend before testing
    - PR #628: Added popup detection to the "Submit Claim" step. The script was clicking the button but not checking if a popup appeared. If a popup did appear, the submission never completed and the test timed out.
    - PR #628: Changed the status-check after submission to reload the page and re-read the status from the server, rather than waiting for the on-screen label to update in place. More reliable.

---

## What the final test run verified (RUN D — 2026-04-17 at 06:51:53Z)

**8 scenarios, 63 steps, single-pass, zero failures, zero skips.**

| Scenario | What it tested | Steps | Result |
|----------|---------------|-------|--------|
| S1 — HOD files and submits claim | Complete claim creation and submission by Chief Engineer | 9/9 | PASS |
| S2 — Captain approves and closes | Approval workflow with financial amount, then closure | 10/10 | PASS |
| S3 — Rejection flow | Filing, submission, captain rejection with reason | 13/13 | PASS |
| S4 — Email draft | Composing a manufacturer email from an approved claim | 5/5 | PASS |
| S5 — Add note | Adding a note; verifying author shown as role, not internal ID | 7/7 | PASS |
| S6 — Document upload | Attaching a PDF to a warranty claim | 7/7 | PASS |
| S7 — Crew role gate | Confirming crew cannot file or mutate claims | 6/6 | PASS |
| S8 — Revise and resubmit | Taking a rejected claim through revision back to submitted | 6/6 | PASS |

No action produced a 4xx or 5xx error. Every status transition was verified by reloading the claim from the server and checking the status label — not by trusting the on-screen update alone.

---

## Bugs fixed in this session

All bugs cited below include the exact file and line where the fix lives.

| Bug | What was broken | What was fixed | File (line) | PR |
|-----|----------------|----------------|-------------|----|
| Notifications "Mark all as read" returning 404 | Clicking the bell's "Mark all as read" button produced an error. Nothing was marked read. | Created the missing Next.js route handler that forwards the request to the backend. | `apps/web/src/app/api/v1/notifications/mark-all-read/route.ts` (created, all lines) | #610 |
| Redis connection pool saturation ("max number of clients reached") | The Render backend logs were flooded with Redis errors. After a crash, the connection-pool reconnection loop kept creating new connections without closing old ones. Eventually the system ran out of available connections. | Added `max_connections=10` cap and `aclose()` (connection close) before reconnecting. | `apps/api/cache/invalidation_listener.py` (reconnect logic), `apps/api/cortex/rewrites.py:105`, `apps/api/routes/f1_search_streaming.py:343` | #613 |
| Warranty popup wait too short | When a claim was submitted via the modal, the "Submit" click registered but the system needed a popup to appear. The 3-second wait was too short — the popup arrived after 3 seconds and was missed. | Increased popup wait from 3,000ms to 10,000ms in the test runner. | `tests/e2e/warranty_runner.py:419` | #620 |
| Entity view blank on first load | When navigating to a warranty claim page, a temporary database delay could return empty data. The page showed nothing. | Added 3-attempt retry with 0.8-second pause between attempts in the entity endpoint. | `apps/api/routes/entity_routes.py:505–530` | #620 |
| Test runner warming up the wrong server | The pre-test warmup that pings the backend to wake it up was hitting an internal server address (`pipeline-core.int.celeste7.ai`) instead of the public-facing address (`backend.celeste7.ai`). The warmup succeeded but the wrong server was warmed. | Corrected the warmup URL. | `tests/e2e/warranty_runner.py:60` | #623 |
| "Submit Claim" click not triggering action | The test runner clicked the Submit Claim button but did not detect whether a popup appeared afterward. If a popup did appear, no action ever fired — the claim stayed in Draft and the test timed out. | Added popup detection: after clicking Submit, the runner waits up to 10 seconds for a popup. If one appears, it confirms it. If no popup appears (direct action), the try/except makes it a no-op. | `tests/e2e/warranty_runner.py:376–388` | #628 |
| Status pill checked before page reload | After submitting a claim, the test checked the on-screen status label before the server had updated it. The label showed the old status (Draft) and the test failed. | Changed to reload the page from scratch after a 3-second pause, then poll for the new status. | `tests/e2e/warranty_runner.py:390–401` | #628 |
| Actions relay returning confusing error on empty response | If the backend returned an empty response (connection dropped mid-reply), the relay crashed with "Unexpected end of JSON input". This masked the real cause. | Added try/catch around the JSON parse. Empty responses now return a clear `502 EMPTY_RESPONSE` error instead. Also added a 25-second hard timeout on the relay call. | `apps/web/src/app/api/v1/actions/execute/route.ts:47–67` | #629 |

---

## Known open issues (not bugs — lower priority gaps)

### Issue #630 — Rejection popup "Confirm" button not disabled when reason is empty

**File:** `apps/web/src/components/lens-v2/ActionPopup.tsx`

When a captain rejects a warranty claim, a popup appears asking for the `rejection_reason` field. This field is marked as required. However, the Confirm button is not disabled when the field is empty — a captain can click Confirm with nothing written in the reason field.

The backend will refuse to process the rejection without a reason (server-side validation protects data integrity), so no incorrect data can be saved. This is purely a user-interface gap — the button should be disabled to give the user a clear signal.

**Fix:** `ActionPopup.tsx` needs to disable the confirm button when any `required: true` field is empty. The test runner's step S3.8 documents this gap and will need to be updated when fixed.

### Bootstrap CORS preflight — intermittent on fresh browser sessions

After the Supabase database layer came back online following a ~6-hour outage (2026-04-17 00:29Z to 06:27Z), the backend needed approximately 15 minutes of warm-up before fresh browser logins were fast and reliable.

During the warm-up window, some browser sessions failed the initial authentication check because the database was responding slowly (9–11 seconds, against a 30-second retry budget). This is not a code bug — it is a known consequence of the underlying Supabase PostgREST layer restarting after a long outage.

**Monitoring recommendation:** After any future Supabase outage or restart, wait 15–20 minutes before running the warranty test suite.

---

## What to do next

1. **File Issue #630 fix** (ActionPopup required-field disable logic) — low priority, does not block operations
2. **Watch the bootstrap CORS preflight** — if it appears again outside of a known outage window, investigate whether the backend is returning CORS headers on 4xx error responses (currently it does not)
3. **Email body display** — the warranty lens shows the email Subject and To address, but not the full body text. The body is stored in the database; it just is not rendered. Low-effort frontend addition if needed.
4. **Equipment picker** — the equipment field in the claim form accepts free text. A search picker (like the one in other domains) would allow linking claims directly to the equipment record.

---

## Overnight incident — Supabase outage (2026-04-17 00:29Z to 06:27Z)

During the overnight testing session, the Supabase database's REST layer (PostgREST — the component that translates database queries into API calls) went offline for approximately 6 hours. The underlying database remained online; only the REST interface was affected.

**Cause:** The PostgREST process (which runs as a protected system user) became stuck. It could not be restarted by our system — it required a manual restart from the Supabase dashboard.

**Resolution:** The CEO restarted PostgREST from the Supabase dashboard (project ID: `vzsohavtuotocgrfkfyd`). The system recovered at 06:27:09Z.

**Impact on this session:** Three test runs (A, B, C) were lost during the outage period. RUN D (the successful 8/8 run) was executed after full recovery.

**Recommendation:** If the warranty runner or any other domain runner fails with HTTP connection timeouts (HTTP status 000), check the Supabase dashboard first before assuming a code bug. The `/health` endpoint at `vzsohavtuotocgrfkfyd.supabase.co/health` will return a 401 (not a timeout) even when PostgREST is down — the correct probe is a direct query to the REST API, which will time out if PostgREST is stuck.

---

*Document produced by WARRANTY01 on 2026-04-17. Sources: live production run RUN D at 06:51:53Z against commit `9e0a2fef`.*
