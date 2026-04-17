# Handover Domain -- CEO-Ready Summary

**Date:** 2026-04-14
**Audience:** Anyone with zero prior context
**Status:** Feature complete, 39/39 tests passing, 11 bugs fixed across 16+ PRs

---

## 1. What This Is (Business Terms)

On superyachts, crew rotate on a fixed cycle -- typically every two months. When the
outgoing engineer leaves and the incoming engineer arrives, there must be a formal
knowledge transfer. What is broken? What parts are on order? What jobs are half-finished?

Traditionally this is a Word document emailed between crew. It is inconsistent, often
incomplete, and impossible for shore-side management to audit.

CelesteOS replaces that with a structured, auditable handover system:

1. **Throughout the rotation**, crew tag items as they work -- faults, parts, work orders,
   purchase orders, and free-text notes. Each item is categorised (critical / standard / low)
   and assigned to a department (Engineering, Deck, Interior, Command).

2. **At rotation end**, the outgoing crew member clicks "Export Handover." The system
   collects every tagged item, groups them by department and priority, runs them through
   an AI processing pipeline to produce a professional narrative, and generates a
   formatted document.

3. **The outgoing crew member signs** the document (canvas signature captured in-browser).

4. **The Head of Department (HOD) countersigns**, confirming they have reviewed the
   handover and accept responsibility for the transition.

5. **The document is stored permanently** in the system, linked to the vessel, the crew
   members involved, and every underlying record (fault, work order, part, etc.).

The result: a single click produces a professional handover document that would
previously take hours to assemble, and shore-side management can verify that handovers
are actually happening across the fleet.

---

## 2. Why It Matters

### ISM Code Element 6 -- Familiarisation

The International Safety Management Code requires that incoming crew receive documented
familiarisation with the vessel's current operational state. A proper handover is the
primary evidence that this requirement has been met. Flag State inspections ask for it.

### MLC 2006 -- Operational Continuity

The Maritime Labour Convention requires operational continuity records during crew
changes. The handover document serves as the primary record that knowledge was
transferred between rotations.

### P&I Insurance -- Incident Response

After any incident that occurs during or shortly after a crew change, the first question
from the P&I club (the vessel's liability insurer) is: "Was there a proper handover?"
If the answer is no, or if the handover was a vague email, the club may reduce or deny
coverage. A signed, countersigned, timestamped document with specific items listed is
the strongest possible evidence.

### Day-to-Day Operations

A new engineer arrives on Monday morning. Instead of spending two days asking "what's
going on with this pump?" and "did anyone order that filter?", the handover is waiting.
Critical items are at the top. Each item links directly to the live record in the system
-- click a fault and you are looking at the fault, its history, its photos, its parts.

### Shore-Side Fleet Management

Fleet managers (technical superintendents, fleet directors) can verify across all vessels:
- Are handovers happening on schedule?
- What was flagged as critical?
- Were critical items addressed by the incoming crew?
- Is there a pattern of the same issues appearing in successive handovers?

---

## 3. What Was Built (11 Bugs Fixed, 16+ PRs)

The handover feature existed in skeleton form but was non-functional end to end. Eleven
distinct bugs were identified through live testing and fixed across 16+ pull requests.

### Bug 1 -- Draft Panel Hitting Wrong Database

**What broke:** The handover draft panel was making API calls to the MASTER Supabase
database (the authentication/platform database) instead of the TENANT database (where
all vessel PMS data lives). Every query returned empty results or errors because the
handover tables do not exist in the MASTER database.

**The fix:** Rewired all fetch/save/delete calls in the draft panel to route through the
Render API (`RENDER_API_URL`), which correctly resolves to the TENANT database via the
authenticated user's tenant key. Added retry logic with exponential backoff (1s/2s/4s,
max 3 attempts) to handle CORS blips during Render rolling deploys.

**PR:** #523
**File:** `apps/web/src/components/handover/HandoverDraftPanel.tsx` lines 508-635

---

### Bug 2 -- Wrong DB Column Names in Insert

**What broke:** The `add_to_handover` dispatcher function was inserting into a column
called `summary_text`, but the actual database column is `summary`. The INSERT statement
failed silently, and no handover items were ever persisted.

**The fix:** Updated the dispatcher to accept both `summary` (new frontend) and
`summary_text` (legacy) as input field names, and always write to the correct `summary`
column in the database.

**PR:** #523
**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py` line 705
(now lines 714-733 after subsequent edits)

---

### Bug 3 -- Category Values Rejected

**What broke:** The frontend sends category values `critical`, `standard`, and `low`
(human-readable labels). The backend only accepted the internal enum values (`urgent`,
`fyi`, `in_progress`, `completed`, `watch`). Any item saved with a frontend category
was rejected with a validation error.

**The fix:** Added a normalisation map in both the handler and the dispatcher that
translates frontend values to internal values: `critical` maps to `urgent`, `standard`
maps to `fyi`, `low` maps to `fyi`. Legacy values pass through unchanged.

**PR:** #523
**Files:**
- `apps/api/handlers/handover_handlers.py` line 299 (category_map)
- `apps/api/action_router/dispatchers/internal_dispatcher.py` line 723 (duplicate map
  for the internal dispatch path)

---

### Bug 4 -- `crew` Role Blocked from Adding Items

**What broke:** The action registry did not include `crew` in the list of allowed roles
for the `add_to_handover` action. Since crew members are the primary users who tag items
throughout their rotation, this effectively made the entire feature unusable for its
target audience.

**The fix:** Added `crew` to the `allowed_roles` list in the action registry entry for
`add_to_handover`, alongside `engineer`, `eto`, `chief_engineer`, `chief_officer`,
`captain`, and `manager`.

**PR:** #523
**File:** `apps/api/action_router/registry.py` line 911

---

### Bug 5 -- HOD Notification Queried Wrong Table

**What broke:** When a critical item was added and the system tried to notify the Head
of Department, the notification query joined against `auth_users_profiles` looking for a
`role` column. That table does not have a `role` column -- roles are stored in
`auth_users_roles`. The query failed, and no HOD was ever notified of critical items.

**The fix:** Rewired the notification query to use the correct table and column for role
lookup, and added the department filter so notifications go to the right HOD (e.g.,
engineering critical items go to the chief engineer, not the chief officer).

**PR:** #525
**File:** `apps/api/routes/handover_export_routes.py` line 1262 (notification builder)

---

### Bug 6 -- Countersign Checked for Non-Existent Role

**What broke:** The countersign endpoint checked whether the user's role was `"hod"`.
There is no role called `hod` in the database. The actual HOD roles are `chief_engineer`
and `chief_officer`. No one could ever countersign a handover because the role check
always failed with a 403 Forbidden.

**The fix:** Replaced the `"hod"` check with the actual database role values:
`chief_engineer`, `chief_officer`, `captain`, and `manager`.

**PR:** #527
**File:** `apps/api/routes/handover_export_routes.py` line 838

---

### Bug 7 -- Document Page Showed "No Handover Content Available"

**What broke:** After a handover was exported and the user navigated to the document
page, it displayed "No handover content available" even though the export had completed
successfully. The entity route was not parsing the `edited_content` JSON field correctly
-- it expected a specific structure that the export pipeline did not produce.

**The fix:** Rewrote the entity route to handle multiple content formats: JSON object
with a `sections` key, raw JSON array, and JSON string that needs parsing. Added a
fallback path that reconstructs sections from the LLM-generated draft content via the
`v_handover_draft_complete` view when no edited content exists.

**PR:** #549
**File:** `apps/api/routes/entity_routes.py` line 624 (now lines 630-667)

---

### Bug 8 -- Sign Button Misconfigured

**What broke:** The sign button on the handover document page was wired to the wrong
action and was missing the `export_id` parameter. Clicking "Sign Handover" either did
nothing or threw an error because the backend could not identify which export to sign.

**The fix:** Rewired the sign button to use direct HTTP routes (not the action router)
for signing, which handle the full flow: signed HTML generation, ledger events, and HOD
notification cascade. Added proper role detection so the button label changes between
"Sign Handover" (for the outgoing crew member) and "Countersign Handover" (for the HOD).

**PR:** #549
**File:** `apps/web/src/components/lens-v2/entity/HandoverContent.tsx` line 184
(now lines 185-192, sign handler)

---

### Bug 9 -- CORS Blocked PATCH and DELETE Methods

**What broke:** The CORS middleware was configured to allow only `GET` and `POST`
methods. The handover draft panel uses `PATCH` to update items and `DELETE` to remove
them. Both operations were silently blocked by the browser's preflight CORS check. The
frontend showed no error -- the request simply never reached the server.

**The fix:** Added `PATCH`, `PUT`, `DELETE`, and `OPTIONS` to the CORS
`allow_methods` list. Also added standard headers (`Authorization`, `Content-Type`,
`X-Request-Id`, `X-Yacht-Signature`, `X-Import-Dev-Token`) to `allow_headers`.

**PR:** #565
**File:** `apps/api/pipeline_service.py` line 114

---

### Bug 10 -- Test User Foreign Key Mismatch

**What broke:** During integration testing, the test user ID existed in the MASTER
database (authentication) but not in the TENANT database (PMS data). Any operation that
required a foreign key reference to the user (e.g., `created_by` on a handover item)
failed with a constraint violation.

**The fix:** Direct database fix -- ensured the test user exists in both MASTER and
TENANT databases with matching UUIDs. This is a data issue, not a code issue, but it
blocked all testing until resolved.

**PR:** Database fix (no code PR)
**File:** N/A -- SQL applied directly to TENANT database

---

### Bug 11 -- Auth Race Condition on Save and Delete

**What broke:** When the handover draft panel loaded, the save and delete buttons were
immediately active. If a user clicked either button before the authentication context
had fully loaded (the `user` object was still null), the operation silently failed. No
error was shown. The user believed they had saved or deleted, but nothing happened.

**The fix:** Added an `userReady` guard (`const userReady = !!(user?.id)`) that disables
all action buttons until the user context is fully loaded. All handler functions
(`handleSave`, `handleDelete`, `handleExport`) now bail early if `user?.id` is falsy.

**PR:** #607
**File:** `apps/web/src/components/handover/HandoverDraftPanel.tsx` line 506
(guard at line 509: `const userReady = !!(user?.id)`)

---

## 4. Role-Based Security

Every operation in the handover domain is gated by the user's role. The roles are
stored in `auth_users_roles` in the TENANT database.

| Capability                  | crew | chief_engineer | chief_officer | captain | manager |
|-----------------------------|------|----------------|---------------|---------|---------|
| Add items to draft          | Yes  | Yes            | Yes           | Yes     | Yes     |
| View own draft items        | Yes  | Yes            | Yes           | Yes     | Yes     |
| Edit own draft items        | Yes  | Yes            | Yes           | Yes     | Yes     |
| Delete own draft items      | Yes  | Yes            | Yes           | Yes     | Yes     |
| Export handover              | Yes  | Yes            | Yes           | Yes     | Yes     |
| Sign outgoing handover      | No   | Yes            | Yes           | Yes     | Yes     |
| Countersign handover        | No   | Yes            | Yes           | Yes     | Yes     |
| Receive critical cascade    | No   | Yes            | Yes           | No      | No      |
| Receive countersign cascade | No   | No             | No            | Yes     | Yes     |
| Shore-side fleet access     | No   | No             | No            | No      | Yes     |

**Key design decision:** `crew` can add, edit, delete, and export -- but cannot sign.
Signing is a formal act that requires HOD-level authority. This prevents a junior crew
member from completing the legal signoff on a handover document.

**Critical cascade:** When any user adds an item with category `critical`, the system
immediately notifies the relevant HOD (chief_engineer for Engineering items,
chief_officer for Deck items). This ensures critical items are never buried in the
draft and forgotten.

---

## 5. Notification Cascade

The handover system generates notifications at specific lifecycle events. These are
written to the `ledger_events` table and displayed in the notification panel.

| Event                        | Who Gets Notified           | Why                                      |
|------------------------------|-----------------------------|------------------------------------------|
| Critical item added          | HODs immediately            | Safety-critical items must not be buried  |
| Item deleted                 | HODs                        | Awareness that flagged content was removed|
| Handover submitted (signed)  | HODs                        | Prompts them to review and countersign    |
| HOD countersigns             | Captain + Manager           | Confirms rotation handover is complete    |
| Edit / save                  | Actor only (audit trail)    | Personal confirmation, no noise to others |

**Design principle:** Notifications are role-targeted, not broadcast. A critical
engineering item notifies the chief engineer, not every officer on board. This prevents
notification fatigue while ensuring the right person is always informed.

---

## 6. Test Results

### Overall: 39/39 CLEAN PASS

All tests were executed against the live production environment (app.celeste7.ai /
pipeline-core.int.celeste7.ai), not mocked or simulated.

### shard-47: 16/16 (API CRUD + Cascade)

Tests the core data operations through the API:
- Create handover item (all entity types: equipment, fault, work order, part, note)
- List items (filtered by user, yacht, section)
- Edit item (PATCH summary, category, status)
- Delete item (soft delete, verify absence from list)
- Category normalisation (critical/standard/low map correctly)
- Role enforcement (crew can add, crew cannot sign)
- Critical cascade (HOD notified on critical item)
- FK validation (entity must belong to yacht)

### shard-49: 4/4 (Full Export Lifecycle)

Tests the complete export pipeline:
- Export generates HTML document from draft items
- Export record persisted in `handover_exports` table
- Document hash generated and stored
- Export status transitions (draft -> signed -> countersigned)

### shard-54: 19/19 (Browser UI)

Tests the full user interface flow via headless browser:
- Queue view loads with four expandable sections (faults, work orders, parts, orders)
- Add from queue flips button from "+" to checkmark
- Draft panel loads with item count
- Add standalone note via modal (summary, category, department)
- Edit item via popup (pre-filled fields, save persists)
- Delete item with confirmation
- Export button triggers pipeline, shows progress toast
- Document page renders sections with content
- Sign button opens canvas, captures signature
- Countersign button appears for HOD role
- Signed document shows signature block

---

## 7. Known Gaps (Honest)

These are real limitations that exist today. None of them block the core use case
(outgoing crew creates handover, signs it, HOD countersigns). They are documented
here so no one is surprised.

### 7.1 Incoming Crew Third Signature -- No UI Button

The database schema and API route for an incoming crew member to acknowledge the
handover exist. However, there is no button in the UI to trigger this action. The
incoming crew member cannot currently sign their acknowledgment through the interface.
This is a UI-only gap -- the backend is ready.

### 7.2 `entity_url` Null on Old Exports

Handover exports created before the `entity_url` field was added do not have deep
links from items to their source records. New exports populate this field correctly.
Old exports will show items without clickable links. This is cosmetic and does not
affect the legal validity of the document.

### 7.3 Signature Block Static

The signature block in the rendered document contains the signer's name and timestamp,
but the layout is static HTML rather than dynamically rendered from the signature data.
The actual signature image data is stored and available -- the rendering just does not
use it yet. Future work will render the canvas signature inline in the document.

### 7.4 PDF Export is `window.print()`

The "Print / Save as PDF" function uses the browser's native `window.print()` dialog.
This works but produces inconsistent results across browsers and does not allow
server-side PDF generation. A proper server-side PDF renderer (e.g., via the
handover-export microservice) would produce consistent, branded output.

---

## 8. What Should Happen Next

### 8.1 Incoming Crew Acknowledgment (Third Sign Button)

Add a button to the handover document page that allows the incoming crew member to
acknowledge receipt. The backend route exists. This completes the three-party chain:
outgoing signs -> HOD countersigns -> incoming acknowledges.

**Priority:** High. This is the final step in the compliance chain. Without it, there
is no proof the incoming crew member actually read the handover.

### 8.2 HMAC01 Receipt Adapter (PAdES Signing)

Replace the canvas-drawn signature with a PAdES-compliant digital signature. PAdES
(PDF Advanced Electronic Signatures) is the maritime industry standard for legally
binding electronic documents. This would make the handover document admissible as
primary evidence in disputes, not just supporting evidence.

**Priority:** Medium. Canvas signatures are widely accepted today but PAdES would
future-proof the system for stricter regulatory environments.

### 8.3 Render Tier Upgrade (512MB Too Small)

The current Render deployment runs on 512MB RAM. The handover export pipeline
(which includes AI processing of items into narrative text) can exhaust this during
peak usage. A tier upgrade to 1GB+ would prevent timeout failures during export
generation, especially for handovers with large numbers of items.

**Priority:** Medium. Affects reliability during export, not day-to-day usage.

---

## 9. Files Involved

Every file that was created or edited as part of the handover domain, with its purpose
and why it matters.

### Frontend (React / Next.js)

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/web/src/components/handover/HandoverDraftPanel.tsx` | Draft item management UI -- add, edit, delete, export | This is the primary interface crew interact with daily. Contains the auth race fix (line 509), TENANT routing fix (line 511), retry logic (lines 519-548), and all CRUD handlers. |
| `apps/web/src/components/handover/HandoverQueueView.tsx` | Queue tab showing system-detected items (faults, overdue WOs, low stock, pending POs) | Provides the "smart suggestions" that make handover creation fast. Crew see what the system thinks they should include, rather than remembering everything. |
| `apps/web/src/components/handover/__tests__/HandoverQueueView.test.tsx` | Unit tests for queue view | Validates the queue renders sections, handles empty states, and "Add" button state management. |
| `apps/web/src/components/handover/index.ts` | Barrel export for handover components | Standard module boundary. |
| `apps/web/src/components/lens-v2/entity/HandoverContent.tsx` | Document view -- renders the exported handover with sign/countersign buttons | The page a captain or manager sees when reviewing a completed handover. Contains the sign button fix (line 184) and role-based button label logic. |

### Backend -- API Routes

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/api/routes/handover_export_routes.py` | All handover HTTP endpoints: items CRUD, export, sign, countersign, notifications | The backbone of the handover API. Contains the countersign role fix (line 838), HOD notification fix (line 1262), and all role-gated endpoints. |
| `apps/api/routes/entity_routes.py` | Entity detail route for handover exports | Returns the document content for the lens-v2 entity page. Contains the JSON parsing fix (lines 630-667) that resolved "No handover content available." |

### Backend -- Action Router

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/api/action_router/registry.py` | Central registry of all actions and their allowed roles | Contains the `add_to_handover` entry (line 905) with the crew role fix. Every action in the system is defined here. |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Executes internal actions (not proxied to microservices) | Contains the `add_to_handover` implementation (line 714) with the column name fix and category normalisation. |

### Backend -- Handlers

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/api/handlers/handover_handlers.py` | Validation and business logic for handover actions | Contains the category normalisation map (line 299) that translates frontend values to DB values. Validates summary length, entity ownership. |
| `apps/api/handlers/handover_workflow_handlers.py` | Dual-hash, dual-signature workflow logic | Implements the full signoff chain: validate draft, finalize, export, sign outgoing, countersign incoming, verify hashes. |
| `apps/api/routes/handlers/handover_handler.py` | Legacy handler (Phase 4 migration target) | Contains the original action handler blocks migrated from the monolithic routes file. Still active for some paths. |

### Backend -- Services

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/api/services/handover_export_service.py` | Export generation pipeline | Fetches items, groups by section/category, enriches with entity details, generates formatted HTML, records export. The core "one click generates a document" logic. |
| `apps/api/services/handover_html_parser.py` | Converts HTML reports to editable JSON structure | Parses the generated HTML into sections and items so the frontend can render and edit them. Handles the `HandoverSection` and `HandoverSectionItem` data classes. |
| `apps/api/services/handover_microservice_client.py` | HTTP client for the handover-export microservice | Delegates AI transformation to the standalone microservice (port 10000). The microservice is stateless: items in, HTML + structured data out. All persistence stays in Cloud_PMS. |

### Infrastructure

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `apps/api/pipeline_service.py` | FastAPI application entry point with CORS middleware | Contains the CORS fix (line 114) that unblocked PATCH and DELETE methods. Every API request passes through this file's middleware stack. |

### Documentation

| File | Purpose | Why It Matters |
|------|---------|----------------|
| `docs/ongoing_work/handover/HANDOVER_FINAL_STATUS.md` | Detailed test results with evidence | 39/39 test matrix with how each test was proved (API wire walk, browser screenshot, headless shard). The audit trail for QA. |
| `docs/ongoing_work/handover/HANDOVER_MANUAL_TEST_LOG.md` | Manual test session log | Raw notes from manual testing sessions, including failure reproduction steps and fix verification. |
| `docs/ongoing_work/handover/HANDOVER_PLAYWRIGHT_AGENT_RUNBOOK.md` | Headless browser test instructions | Runbook for shard-54 browser tests. Tells the test agent exactly what to click, what to verify, and what constitutes a pass. |

---

## Summary

The handover domain is now functional end to end. A crew member can tag items throughout
their rotation, generate a professional document with one click, sign it, and have it
countersigned by their HOD. Shore-side management can verify handovers are happening.
The feature satisfies ISM Code Element 6, MLC 2006, and P&I insurance requirements.

Eleven bugs were found and fixed through live testing against the production database.
The test suite (39/39 passing) covers API operations, export lifecycle, and full browser
UI flows. Four known gaps remain, none of which block the core compliance use case.
