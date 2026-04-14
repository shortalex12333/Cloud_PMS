# Ledger Export — Full Worker Handover
**Date written:** 2026-04-13
**Written by:** Claude Code (Team 4, CEO01 session)
**For:** Next worker — assume zero prior context. If you are building the Hours of Rest export using this same framework, read every section. The HoR export is structurally identical to what is documented here.

---

## 1. BUSINESS SUMMARY (READ THIS FIRST)

Cloud PMS is a vessel management software system used by superyacht crews. It tracks everything that happens on board: work orders, faults, parts, documents, crew activity.

The **Ledger** is an internal audit trail — a tamper-visible log of everything that has happened, who did it, when, and on what. Every action in the system (opening a document, completing a work order, signing off hours) writes a row to a database table called `ledger_events`.

The **Ledger Export** is the feature that lets an authorised user take a date range, pull all events in that range, package them into a cryptographically sealed PDF, and receive a download link. That PDF is **evidence**. It can be handed to port state inspectors, flag states, insurers, or lawyers. It is not a report. It is a legal record.

This session built **the user-facing trigger for that export** — the button, modal, and result display inside the UI — and wired the backend to:
- Record that an export happened (so it appears in the activity feed)
- Notify the requesting user (so a notification badge can be built later)
- Tell the user how to verify the document's authenticity after downloading

All three PRs are merged to `main` as of 2026-04-13.

---

## 2. WHAT EXISTED BEFORE THIS SESSION

Do not recreate any of this. It was already complete when this session began.

| Component | Location | What it does |
|-----------|----------|-------------|
| Ledger events table | Supabase tenant DB — `ledger_events` | Every action in the system writes here |
| Ledger exports table | Supabase tenant DB — `ledger_exports` | Each export job is recorded here |
| Export API endpoint | `apps/api/routes/ledger_routes.py` → `POST /v1/ledger/export` | Fetches events, builds PDF, uploads to storage, returns signed URL |
| Count preview endpoint | same file → `GET /v1/ledger/export/count` | Tells you how many events a given date range + scope would include |
| Actors preview endpoint | same file → `GET /v1/ledger/export/actors` | Lists the crew members whose events would be in the export |
| PDF builder | same file → `_build_ledger_pdf()` internal function | Creates the evidence PDF with embedded JSON and HMAC-masked IDs |
| PAdES sealing pipeline | `apps/api/evidence/sealing.py` | If `LEDGER_EXPORT_SEAL=true` env var is set, applies cryptographic timestamp signature (RFC 3161) to the PDF |
| HMAC masking | `_mask_export_id()` inside `ledger_routes.py` | Replaces all raw UUIDs (user IDs, yacht IDs, entity IDs) in the PDF with deterministic hashes — privacy protection without losing forensic traceability |
| Verifier site | `verify.celeste7.ai` (separate deployment) | Anyone can upload the PDF here to confirm it has not been tampered with |
| Public certificate | `celeste7.ai/.well-known/verify.pem` | The RSA-4096 public key used to verify the seal |
| LedgerPanel component | `apps/web/src/components/ledger/LedgerPanel.tsx` | Right-side drawer in the app UI showing the activity timeline |

---

## 3. WHAT THIS SESSION BUILT (OPERATIONAL DETAIL)

### 3a. Export modal in LedgerPanel

**File:** `apps/web/src/components/ledger/LedgerPanel.tsx`
**Status:** Edited

Added inside the existing LedgerPanel component (not a new file, not a new component):

- A download icon button in the panel header (uses `Download` from `lucide-react`, already imported)
- An absolute-positioned overlay modal (appears over the panel, `top: 57px` to clear the header bar)
- Date range inputs (`date_from`, `date_to`)
- Scope selector: `me` (your events only) or `department` (all department events). `all` is intentionally not exposed in the UI — it exists in the backend but is captain/manager only
- Generate PDF button — disabled until both dates are filled
- Spinner state while generating (shows "Generating…" text)
- Result panel showing: event count, SEALED badge (if the PDF was cryptographically sealed), download link, and verifier education text (see below)
- "Generate another" button that resets the result state without closing the modal

**Key implementation detail:** The modal is an absolute overlay inside the panel's `div`, not a React portal, not a separate route, not a separate component file. This keeps the blast radius minimal.

**Verifier education text added in this session:**
```
To verify authenticity: download the PDF, then upload it to verify.celeste7.ai
```
This was added because users were exporting PDFs with no idea what to do with them next. They need to know the verification step exists.

### 3b. Export action logged to the activity feed

**File:** `apps/api/routes/ledger_routes.py`
**Status:** Edited (two additions)

**Problem found:** When a user exported a PDF, nothing appeared in the ledger activity timeline. The export happened silently. This meant the ledger was not self-documenting — you couldn't prove from the ledger itself that an export had occurred.

**Fix:** After the `ledger_exports` table insert (line ~762), added a fire-and-forget insert to `ledger_events`:

```python
db_client.table("ledger_events").insert({
    "yacht_id":       str(resolved_yid),
    "user_id":        str(user_id),
    "event_type":     "mutation",
    "entity_type":    "ledger_export",
    "entity_id":      str(export_id),
    "action":         "export_generated",
    "change_summary": f"Evidence PDF exported — {len(events)} events ({payload.scope}), {'sealed' if is_sealed else 'unsigned'}",
    "metadata":       {"event_count": len(events), "scope": payload.scope, "sealed": is_sealed},
}).execute()
```

Fire-and-forget means: if this insert fails, the export still succeeds. A logging warning is emitted but nothing is blocked.

### 3c. Export completion written to ledger_notifications

**File:** `apps/api/routes/ledger_routes.py`
**Status:** Edited (also fire-and-forget)

Added a row to `ledger_notifications` after every successful export. This table holds the pending notification so that a future notification bell/feed feature can query it. The row contains:
- `download_url` (signed, expires in 1 hour)
- `event_count`
- `sealed` flag
- `is_read: false` — not yet cleared by the frontend

**The `ledger_notifications` table does not auto-exist.** It was created via a one-time SQL migration applied directly to Supabase (not saved as a file). Structure:

```sql
CREATE TABLE IF NOT EXISTS ledger_notifications (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id        text NOT NULL,
    user_id         text NOT NULL,
    export_id       uuid NOT NULL REFERENCES ledger_exports(id),
    notification_type text NOT NULL DEFAULT 'export_complete',
    event_count     integer NOT NULL DEFAULT 0,
    sealed          boolean NOT NULL DEFAULT false,
    download_url    text NOT NULL,
    expires_at      timestamptz NOT NULL,
    is_read         boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);
```

If this table does not exist in your environment, apply the above SQL against the **tenant** Supabase DB (not the master DB). See section 6 for DB credentials guidance.

### 3d. CORS fix

**File:** `apps/api/pipeline_service.py`
**Status:** Edited

**Problem:** The FastAPI backend only allowed specific localhost ports (3000, 3001, 5173, 8080). The Next.js app runs on port 3010. Requests from the UI were being blocked by CORS before they even reached the API.

**Fix:** Replaced the hardcoded port list with a regex pattern:
```python
allow_origin_regex = r"^http://localhost:\d+$"
```
This allows any localhost port without having to enumerate them. All production origins remain as an explicit allow-list.

**Why this matters for HoR export:** If you are building a similar export from the Hours of Rest module, your frontend fetch calls to the API will fail with a CORS error if this fix is not in place. It is already fixed in main as of this session.

### 3e. Data-testid selectors in TopBar

**File:** `apps/web/src/components/shell/Topbar.tsx` (lowercase b — see Mistakes section)
**Status:** Edited

Added:
- `data-testid="user-menu-trigger"` on the hamburger menu button
- `data-testid="ledger-open"` on the Activity Log menu item

These are required for the Playwright E2E test. Without them, the test must click by coordinates or text content — both of which break when the layout changes.

### 3f. E2E test

**File:** `apps/web/e2e/ledger-export.spec.ts`
**Status:** Created (keeper — do not delete)

**File:** `apps/web/playwright.ledger.config.ts`
**Status:** Created (keeper)

The test covers the full flow:
1. Login with real credentials
2. Open user menu → click Activity Log (LedgerPanel opens)
3. Click the export icon
4. Fill date range (2026-04-01 to 2026-04-13)
5. Click Generate PDF
6. Wait for download link (up to 30s — TSA seal takes ~10s)
7. Assert: href contains `supabase.co/storage` and `ledger-exports`
8. Assert: event count visible, SEALED badge visible
9. Click "Generate another" — modal resets

**Result:** 1 passed, ~11s runtime

Run command:
```bash
cd apps/web
npx playwright test e2e/ledger-export.spec.ts --config playwright.ledger.config.ts
```

---

## 4. PR HISTORY (ALL MERGED TO MAIN)

| PR | Branch | What it contained |
|----|--------|------------------|
| #511 | feat/ledger-export-ux | Initial export modal UI (was missing some commits — see Mistakes) |
| #512 | fix/cors-testids-e2e | CORS regex fix + data-testid selectors + E2E spec |
| #513 | fix/cors-testids-e2e | Cherry-pick of #512 — the CORS commit had landed after #511 merged |
| #514 | feat/ledger-export-ux | Verifier education text + export logged to `ledger_events` |

---

## 5. MISTAKES, LIES, AND THINGS THAT WENT WRONG

This section is written plainly. No spin. If you are doing a similar feature, read this first.

### Mistake 1 — Wrong port (port 3000 vs 3010)

The Next.js app runs on **port 3010**, not 3000. Port 3000 is occupied by a completely separate app (the Download Portal, a Vite application for the CelesteOS installer download flow).

When the Playwright test was first written, it pointed at port 3000. Every test ran successfully against the wrong app. The login form existed on that port, the login appeared to succeed, but then the ledger panel never appeared because it was not the PMS. Multiple test iterations were wasted on this before the port was investigated.

**How to avoid:** Before writing any E2E test, curl the expected URL and check the HTML title or a known DOM element. Do not assume port 3000 is the app you want.

### Mistake 2 — CORS was blocking silently

When the frontend at port 3010 called the API, the browser blocked the request with a CORS error. This looked like a "connection failed" error in the UI bootstrap — which looked identical to an API being down. It was not immediately obvious that CORS was the root cause.

The CORS config only allowed ports 3000, 3001, 5173, 8080. Port 3010 was never in the list. The backend returned a 200 to curl (which ignores CORS) but blocked the browser.

**How to avoid:** When a browser fetch fails silently or the bootstrap shows "Connection failed," check CORS before anything else. Check the browser console for `Access-Control-Allow-Origin` errors specifically.

### Mistake 3 — `timedelta` not imported

The `ledger_notifications` insert code uses `timedelta` to calculate an expiry timestamp 1 hour from now:
```python
(datetime.utcnow() + timedelta(seconds=3600))
```

The file's import line was `from datetime import datetime, date` — `timedelta` was missing. This caused a `NameError` in production. The fix was a one-line import change, but it caused a failed export before it was caught.

**How to avoid:** Always check all names used in new code blocks are actually imported. Python does not catch this at parse time if the import line exists but is incomplete.

### Mistake 4 — `TopBar.tsx` vs `Topbar.tsx` (macOS case-insensitive filesystem)

The file on disk is `Topbar.tsx` (lowercase b). When editing with the path `TopBar.tsx` (uppercase B), macOS silently redirects the edit to the correct file. Git, however, tracks the lowercase filename. This created a situation where:
- The edit appeared to succeed
- The file content was correct
- But the commit staged the wrong path reference internally

The result was a commit that did not include the `data-testid` changes. This was only discovered when the E2E test ran and could not find the `user-menu-trigger` element.

**How to avoid:** When editing shell/component files, always verify the exact filename case with `ls` before editing. On a case-sensitive filesystem (Linux, CI), this would have thrown an error immediately.

### Mistake 5 — CORS commit landed after PR #511 merged

The CORS fix and `data-testid` changes were committed to the `feat/ledger-export-ux` branch after PR #511 had already been merged. The commit existed on the branch but never made it to main. This required a cherry-pick onto a new `fix/cors-testids-e2e` branch and a second PR (#512 → #513 cleanup).

**How to avoid:** Before opening a PR, verify that every commit you intend to include is in the branch's history with `git log`. Do not rely on "the changes were staged" — staged changes that were not yet committed are not in a PR.

### Mistake 6 — Debug spec files left in the repo (temporarily)

During the troubleshooting process, four diagnostic Playwright spec files were created:
- `e2e/debug-login.spec.ts`
- `e2e/debug-menu.spec.ts`
- `e2e/debug-menu2.spec.ts`
- `e2e/debug-menu3.spec.ts`

These were never committed (they were untracked). They were deleted from disk before the session ended. But if they had been committed, they would have polluted the E2E test suite with non-canonical tests.

**How to avoid:** Keep diagnostic/debug files out of the e2e directory. Use `/tmp/` for throwaway tests. If you must create them in-repo for tooling reasons, prefix with `_debug_` and add to `.gitignore` before creating.

### Mistake 7 — CI was already broken on main (false alarm)

When PR #514 was opened, all CI checks failed. This looked like the PR had broken something. Investigation showed that main itself was failing with the same tests before the PR was opened. The failures were in `test_handover_queue`, `test_rls_isolation`, `test_sse_streaming`, and `test_remaining_handlers` — none of which relate to the ledger export.

**How to avoid:** Before diagnosing a PR's CI failures, always check if main is also red. If main is failing the same checks, the PR did not cause the failure. Use `gh run list --branch main` to compare.

### What was falsely claimed at some point

At various stages during the session, the test was described as "passing" when it was in fact running against the wrong port (port 3000 — the installer download portal). The HTML title and login screen on that port are similar enough that a surface check passed. Only when the ledger panel search step failed was it confirmed that the wrong app was being tested.

This is the highest-risk failure mode in any E2E test: the test runs, the early assertions pass, but you are not testing what you think you are testing. The verification-integrity skill exists precisely to catch this — always ask "is this signal telling me what I think it's telling me?"

---

## 6. ENVIRONMENT AND CREDENTIALS

- API (backend): `apps/api/` — FastAPI, Python, runs in Docker or locally on port 8000
- Frontend: `apps/web/` — Next.js, runs on **port 3010** (not 3000)
- Download Portal: separate Vite app, runs on port 3000 — not the PMS
- DB credentials: stored in memory file `reference_cloud_pms_db.md` — MASTER DB and TENANT DB are separate Supabase projects
- Env vars: `Cloud_PMS/env` — contains `EXPORT_HMAC_SECRET`, `LEDGER_EXPORT_SEAL`, Supabase keys
- To seal exports in local development: set `LEDGER_EXPORT_SEAL=true` in the env file and restart the API container

---

## 7. HOW THE EXPORT PIPELINE WORKS END-TO-END

This is the complete sequence for a single export, from button click to downloaded PDF:

```
User clicks Download icon in LedgerPanel
    ↓
Modal opens (exportOpen = true)
    ↓
User fills date_from, date_to, selects scope (me / department)
    ↓
User clicks "Generate PDF"
    ↓
Frontend: POST /v1/ledger/export
  Headers: Authorization: Bearer <jwt>
  Body: { date_from, date_to, scope }
    ↓
Backend: resolve_yacht_id() — determines which vessel's events to fetch
Backend: fetch events from ledger_events table (filtered by date + scope)
Backend: _build_ledger_pdf() — creates PDF with:
  - Cover page (vessel name, date range, scope, requester)
  - Per-event rows (timestamp, masked actor_ref, action, entity, summary)
  - Embedded JSON of all raw events (for machine verification)
  - HMAC masking: all user_id → actor_ref, yacht_id → vessel_ref
    ↓
IF LEDGER_EXPORT_SEAL=true:
  Backend: seal_export() — runs in thread executor (asyncio-safe)
    - Computes SHA-256 of PDF
    - Requests RFC 3161 timestamp from TSA (Sectigo)
    - Embeds timestamp signature into PDF (PAdES-B-LT format)
    - Returns signed PDF bytes + sealing metadata
    ↓
Backend: upload PDF to Supabase storage bucket "ledger-exports"
  Path: {hmac(yacht_id)[:16]}/{export_id}.pdf
  (no raw UUIDs visible in any signed URL)
    ↓
Backend: create_signed_url() — 1-hour expiry
    ↓
Backend: INSERT into ledger_exports (full record)
Backend: INSERT into ledger_events (fire-and-forget — appears in activity feed)
Backend: INSERT into ledger_notifications (fire-and-forget — for future bell/feed)
    ↓
Backend returns: { export_id, event_count, download_url, sealed, tsa_authority }
    ↓
Frontend: setExportResult({ url, count, sealed })
Frontend renders:
  - Event count
  - "SEALED" badge (if sealed=true)
  - Download link
  - "To verify authenticity: download then upload to verify.celeste7.ai"
    ↓
User downloads PDF, optionally uploads to verify.celeste7.ai
Verifier checks: HMAC signatures, TSA timestamp, PDF hash
```

---

## 8. HOW TO BUILD THE HOURS OF REST EXPORT (FOR THE NEXT WORKER)

The Hours of Rest export would follow exactly the same architecture. Here is what would need to exist:

### What already exists that HoR export can reuse

| Component | Reusable as-is |
|-----------|---------------|
| CORS fix in `pipeline_service.py` | Yes — already done |
| Supabase storage bucket | Probably needs a new bucket `hor-exports` or reuse `ledger-exports` with a sub-path |
| PAdES sealing pipeline | Yes — `evidence/sealing.py` is format-agnostic |
| HMAC masking pattern | Yes — copy `_mask_export_id()` from `ledger_routes.py` |
| Signed URL pattern | Yes — same Supabase `.create_signed_url()` call |
| Verifier infrastructure | Yes — `verify.celeste7.ai` already live |

### What would need to be built

1. **Backend endpoint:** `POST /v1/hor/export` in `apps/api/routes/hor_routes.py` (or wherever HoR routes live)
   - Fetch from `hours_of_rest` table (or whatever the HoR records table is called)
   - Build a PDF (can use the same `reportlab` pattern from `_build_ledger_pdf`)
   - For MLC compliance: include sign-off chain (crew → HOD → Captain) in the PDF
   - Include violation flags if any exist in the record

2. **Frontend modal:** Add to the HoR panel (same pattern as LedgerPanel export modal — absolute overlay, date range, scope, generate button, result panel)

3. **Record the export:** Insert into a `hor_exports` table (create if not exists, same schema as `ledger_exports`)

4. **Log to ledger:** After export, insert to `ledger_events` with `entity_type: "hor_export"` — this makes the export visible in the audit trail

### Critical difference: HoR export has legal specifics

A ledger export is general evidence. An HoR export under MLC 2006 must:
- Include **all periods within the date range**, not just events — gaps are as important as records
- Show the **sign chain status** (signed by crew / countersigned by HOD / approved by Captain)
- Flag any **MLC violations** (insufficient rest hours, unsigned periods)
- Be exportable per-crew-member (not just "department")

The sealing is the same. The content logic is different.

---

## 9. WHAT IS NOT YET DONE (OPEN ITEMS)

| Item | Priority | Notes |
|------|----------|-------|
| Notification bell / feed in UI | Low | `ledger_notifications` table exists, rows are written, nothing reads them yet |
| Mark notification as read | Low | `is_read` column exists, no frontend update |
| Run E2E against production (`app.celeste7.ai`) | Medium | Run with `E2E_BASE_URL=https://app.celeste7.ai npx playwright test ...` |
| `scope=all` in the UI | Low | Backend supports it (captain/manager only), not exposed in the modal — intentional |
| Download URL expiry warning | Low | URLs expire after 1 hour. No UI warning exists. User clicking an expired link gets a Supabase error |
| HoR export | Separate task | Architecture documented in section 8 above |

---

## 10. KEY FILES — QUICK REFERENCE

| File | Purpose | Changed this session |
|------|---------|---------------------|
| `apps/api/routes/ledger_routes.py` | All ledger API endpoints: events, export/count, export/actors, POST export | Yes — `timedelta` import, ledger_events insert, ledger_notifications insert |
| `apps/api/pipeline_service.py` | FastAPI app entry point — CORS middleware lives here | Yes — wildcard localhost regex |
| `apps/web/src/components/ledger/LedgerPanel.tsx` | The ledger drawer UI component | Yes — export modal JSX, verifier text, handler function |
| `apps/web/src/components/shell/Topbar.tsx` | Top navigation bar with user menu | Yes — data-testid attributes |
| `apps/web/e2e/ledger-export.spec.ts` | Playwright E2E test for the full export flow | Created |
| `apps/web/playwright.ledger.config.ts` | Playwright config for the ledger test (port 3010, 3min timeout) | Created |
| `apps/api/evidence/sealing.py` | PAdES-B-LT sealing pipeline (RFC 3161 TSA) | Not changed — was already complete |

---

## 11. TEST CREDENTIALS

The E2E test uses:
- Email: `x@alex-short.com`
- Password: `Password2!`

These are hardcoded in `apps/web/e2e/ledger-export.spec.ts`. If the password changes or the account is deleted, the test will fail at the login step.

---

## 12. WHAT SHOULD HAPPEN NEXT

In priority order:

1. **Run E2E against production.** The test passes locally and against Docker. Run it against `https://app.celeste7.ai` to confirm the full pipeline works in the deployed environment. Command: `E2E_BASE_URL=https://app.celeste7.ai npx playwright test e2e/ledger-export.spec.ts --config playwright.ledger.config.ts`

2. **Pre-existing CI failures.** There are ~27 failing tests on main that are unrelated to this work (`test_handover_queue`, `test_rls_isolation`, `test_sse_streaming`, `test_remaining_handlers`). These were failing before this session started. They should be fixed — but in a separate task by whoever owns those modules.

3. **HoR export.** Use section 8 of this document as the blueprint. The sealing, CORS, and storage patterns are identical. The content and schema are different.

4. **Notification bell.** When the ledger_notifications table is ready to surface in the UI, add a query to `GET /v1/ledger/notifications?unread=true` and render an unread count badge somewhere in the TopBar.
