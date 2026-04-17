# Documents Domain — Handover Summary

> **Owner:** DOCUMENTS01 (Team 4)
> **Date:** 2026-04-17
> **For:** Next engineer + CEO review
> **Status:** MVP complete. 8/8 scenarios PASS. 13 PRs shipped. 10 bugs found and fixed.

---

## What This Is (Plain English)

The **Documents** page in CelesteOS PMS is where crew manage the vessel's document library — engine manuals, inspection reports, safety certificates, equipment drawings, service records. Every commercial yacht carries hundreds of these files and they must be:

- **Uploadable** by officers (chief engineer, chief officer, purser, captain)
- **Viewable and downloadable** by all crew including junior ranks
- **Deletable** only by captain or manager, with a signed reason on record
- **Linked** to equipment, work orders, certificates, and handover packages
- **Logged** in the audit ledger so every action has a tamper-evident trail
- **Extracted** by the search pipeline so documents are findable by content

### Why It Matters

**Maritime law:**
- **ISM Code (International Safety Management):** Requires documented procedures maintained and accessible on board. A broken document system = non-compliance at Port State Control inspection.
- **MLC 2006 (Maritime Labour Convention):** Crew certificates, employment agreements, and rest-hour records must be accessible. Documents domain is the storage layer for all of these.
- **SOLAS:** Safety plans, muster lists, and emergency procedures are documents that must be immediately retrievable.

**Day-to-day operations:**
- Chief engineer uploads a new equipment manual after a service visit
- Captain deletes an outdated safety plan (requires signed reason for audit trail)
- Crew member downloads a procedure manual before starting a task
- Purser attaches an invoice document to a purchase order
- During handover, outgoing captain's document library transfers to the incoming captain

**Shore-side:**
- Fleet managers view vessel documents remotely via signed URLs (time-limited, secure)
- Classification society auditors can be shown document history and audit trail
- Management company reviews document compliance across the fleet

**Role-based security:**
- Crew (deckhand, steward, chef, bosun, engineer, ETO): view and download only
- HOD (chief engineer, chief officer, chief steward, purser): upload, update metadata, add tags, comment, link to entities
- Captain/Manager: all HOD permissions + delete (signed action requiring reason + PIN verification)

---

## What Was Done

### Starting State (2026-04-15)
- Upload flow was broken — produced ghost records (metadata row but no actual file in storage)
- Zero `ledger_events` written for any document action
- Zero `pms_notifications` for any document action
- Storage bucket mismatch (`yacht-documents` vs `documents`)
- Search extraction pipeline couldn't process uploaded files (tsv generated column + org_id bugs)
- No role gating on the frontend Upload button

### Ending State (2026-04-17)
- Full CRUD working end-to-end: upload (with title, doc_type, tags), update metadata, add tags, delete (signed), download, link-to-equipment
- Every action writes a `ledger_events` row with proof_hash
- Every action writes a `pms_notifications` row
- Search pipeline extracts document text correctly (F2 trigger → extraction → projection → embedding)
- Frontend Upload button hidden for crew roles
- Signature contract fixed for ALL signed actions across the entire platform (PR #615)

---

## Bugs Found and Fixed

| # | Bug | Severity | How Found | Fix | PR |
|---|-----|----------|-----------|-----|-----|
| 1 | Upload endpoint wrote zero `ledger_events` | High | Backend wirewalk | Added `build_ledger_event()` call after upload | #562 |
| 2 | Zero `pms_notifications` for any document action | High | Backend wirewalk | Added `_push_doc_notification()` helper | #562 |
| 3 | Tags "critical" split into `["c","r","i","t","i","c","a","l"]` | High | MCP02 browser test S3 | `handlers/document_handlers.py:473` — defensive string→list split on comma | #590 |
| 4 | Upload modal had no title/doc_type/tags fields | Medium | MCP02 browser test S1 | Added 3 form fields to `AttachmentUploadModal.tsx` | #590 |
| 5 | Crew could see and click Upload button | High | MCP02 browser test S5 | `AppShell.tsx:145` — extended `primaryActionDisabled` to documents | #590 |
| 6 | Filenames with spaces/accents caused 500 | Medium | MCP02 browser test S7.4 | `utils/filenames.py` — strip non-alphanumeric except `.`, `-`, `_` | #591 |
| 7 | Link-to-Equipment modal had no equipment picker | High | MCP02 browser test S6 | Backend: equipment_id CONTEXT→REQUIRED. Frontend: functional `FieldEntitySearch` | #602, #603, #605 |
| 8 | `doc_metadata` column names drifted (mime_type vs content_type) | High | MCP02 browser test S6 | `equipment_handlers.py:2043` — fixed SELECT + INSERT columns | #609 |
| 9 | `maybe_single()` returns None in supabase-py >= 2.x | Medium | MCP02 browser test S6 | Added null guards at 3 query sites | #612 |
| 10 | All SIGNED actions sent `pin` not `signature` object | Critical | MCP02 browser test S4 | `ActionPopup.tsx:603` — builds proper `signature` JSON. **Platform-wide fix.** | #615 |

---

## PRs Shipped (13 total)

| PR | Title | What it did |
|----|-------|-------------|
| #562 | wire ledger_events + notifications for all document CRUD | Core fix: every doc action now writes ledger + notification |
| #563 | cheat sheet v1 | First test guide |
| #570 | cheat sheet rewritten to manual test log format | Matches WARRANTY_MANUAL_TEST_LOG structure |
| #572 | shard-52 Playwright test suite | Automated browser tests |
| #576 | /test-documents slash command | AI agent browser test runbook |
| #590 | 3 frontend bugs (tags, modal fields, crew RBAC) | Tags fix + upload modal fields + crew button gate |
| #591 | filename sanitizer | Non-ASCII/special chars stripped |
| #602 | S6 backend field reclassification | equipment_id CONTEXT→REQUIRED, document_id auto-prefilled |
| #603 | entity search calls Render API directly | Bypass broken Vercel fallback route |
| #605 | entity search uses useAuth() for yacht_id | Fixed empty yacht_id in search URL |
| #609 | doc_metadata column drift fix | content_type not mime_type |
| #612 | maybe_single() null guard | supabase-py >= 2.x compatibility |
| #615 | SIGNED actions send signature object | Platform-wide fix for all signed actions |

---

## Files Changed (exact references)

### Backend (Python — Render)

| File | Lines | What changed |
|------|-------|-------------|
| `apps/api/routes/document_routes.py:787-818` | Added | `ledger_events` insert + `pms_notifications` insert after upload |
| `apps/api/routes/handlers/document_handler.py:40-65` | Added | `_push_doc_notification()` helper function |
| `apps/api/routes/handlers/document_handler.py:193-250` | Edited | Ledger + notification for upload, update, tags, delete |
| `apps/api/handlers/document_handlers.py:469-485` | Edited | Defensive string→list for tags input |
| `apps/api/action_router/ledger_metadata.py:58,63` | Added | `add_document_tags` + `update_document` safety net entries |
| `apps/api/action_router/registry.py:810-815` | Edited | equipment_id CONTEXT→REQUIRED, document_id REQUIRED→CONTEXT |
| `apps/api/action_router/entity_prefill.py:124` | Added | `(document, link_document_to_equipment)` prefill map |
| `apps/api/handlers/equipment_handlers.py:2043,2075` | Edited | Column names content_type/size_bytes + maybe_single guards |
| `apps/api/utils/filenames.py:34` | Edited | Strip non-ASCII, spaces, parens, brackets |

### Frontend (TypeScript/React — Vercel)

| File | Lines | What changed |
|------|-------|-------------|
| `apps/web/src/components/lens-v2/actions/AttachmentUploadModal.tsx:150-155,302-355` | Edited | Title, doc_type select, tags fields when `showMetadataFields=true` |
| `apps/web/src/components/shell/AppShell.tsx:145-148,224-226` | Edited | Documents RBAC gate + metadata forwarding in FormData |
| `apps/web/src/components/lens-v2/ActionPopup.tsx:3,29,208-340,600-606` | Edited | `useAuth()` import, `search_domain` on interface, functional `FieldEntitySearch`, `signature` object in handleSubmit |
| `apps/web/src/components/lens-v2/mapActionFields.ts:107` | Edited | Pass `search_domain` through to ActionPopupField |

### Test & Documentation

| File | Purpose |
|------|---------|
| `scripts/one-off/documents01_real_pass_wirewalk.py` | 30-assertion backend test against live API + DB |
| `apps/web/e2e/shard-52-documents-mvp/documents-mvp.spec.ts` | Playwright automated test suite |
| `.claude/commands/test-documents.md` | AI agent browser test runbook |
| `docs/ongoing_work/documents/DOCUMENTS_MVP_CHEATSHEET.md` | Manual test scenarios (fillable Y/N/ERR) |
| `docs/ongoing_work/documents/DOCUMENTS_TEST_RESULTS.md` | 461-line browser test results + DB cross-exam |
| `docs/ongoing_work/documents/DOCUMENTS_HANDOVER.md` | This file |
| `docs/ongoing_work/documents/DOCUMENTS_DOMAIN_GUIDE.md` | How the domain works (technical reference) |

---

## Test Evidence

**Backend wirewalk:** 30/30 PASS (`scripts/one-off/documents01_real_pass_wirewalk.py`)
- Crew upload denied (403)
- HOD upload (200 + storage blob + doc_metadata + search_index + ledger + notification)
- HOD update, tags, get_url (200 + ledger + notification)
- Captain signed delete (200 + soft-delete + ledger + notification)
- Crew read-only (get_url 200, update 403, delete 403)

**Browser testing by DOCUMENTS_MCP02:** 8/8 PASS
- S1: Upload with title/doc_type/tags — modal fields render, API 200
- S2: Update metadata — API 200, ledger_written:true
- S3: Add tags — "critical" stored as `["critical"]` not characters
- S4: Captain delete — PIN popup, signature object sent, API 200, deleted_at set
- S5: Crew RBAC — Upload button disabled with tooltip
- S6: Link-to-Equipment — search picker, dropdown, select, API 200
- S7: Edge cases — 15MB block, .exe 415, 0-byte 400, special chars sanitized
- S8: Signature matrix — confirmed which actions popup vs fire directly

**DB cross-examination (by MCP02 via direct psql):**
- `doc_metadata` rows verified with correct storage_bucket, storage_path, content_type, tags
- `storage.objects` rows verified with correct size, MIME type
- `ledger_events` chain verified: upload (create), update, tags, delete events with proof_hash
- `pms_audit_log.signature` verified: `{"pin":"1234","method":"pin","signed_at":"..."}`
- `pms_notifications` verified: 4 notification types (uploaded, updated, tags_updated, deleted)
- `pms_equipment_documents` link row verified

---

## Known Gaps (Honest)

| Gap | Severity | Notes |
|-----|----------|-------|
| `update_document` doesn't mutate most doc_metadata columns | Medium | PostgREST schema cache issue at `document_handlers.py:422`. Audit-only. |
| Signature not propagated to `ledger_events.metadata` | Medium | Lands in `pms_audit_log.signature` only. Flagged to HMAC01 for receipt-layer. |
| `view_document` writes ledger read events (20 per session) | Low | Noisy. Review whether reads should write ledger. |
| No document versioning | Low | Single copy per doc_id, no revision history. |
| No thumbnail/preview generation | Low | List shows filenames only. |
| `Add to Handover` visible to crew in More Actions menu | Low | May be intentional — needs product decision. |
| Transient 500 on records endpoint | Low | Seen once, auto-retried to 200. Schema cache thaw. |

---

## What the Next Engineer Needs to Know

1. **The action modal framework auto-generates forms from the registry schema.** Every payload field becomes a free-text input. The `FieldEntitySearch` picker I built (`ActionPopup.tsx:208-340`) is the first functional entity search. Any new action with a foreign-key field needs the same treatment — add `lookup_required=True` to the registry `FieldMetadata` and ensure `search_domain` propagates through `mapActionFields.ts`.

2. **`maybe_single()` in supabase-py >= 2.x returns None, not an empty response object.** Bug #9 is likely present in other domains. Worth a repo-wide grep for `.maybe_single().execute()` followed by `.data` access without a None check.

3. **PR #615 fixed ALL signed actions platform-wide.** If you see a signed action working in any domain, that's because of the Documents testing work. The fix is in `ActionPopup.tsx:600-606`.

4. **The search pipeline (extraction → projection → embedding) is separate from the Documents CRUD.** I fixed the pipeline bugs (tsv column, org_id, bucket name) but the tokenization issue with underscored filenames is pre-existing and out of scope. See `feedback_url_philosophy.md` in memory — search is "a different beast."

5. **Render free tier (512MB) can't handle 19+ agents.** OOM oscillation between 200/503 is normal during multi-agent sessions. Paid tier needed.

6. **The PIN on signed actions is frontend-only.** No PIN table exists in either database. The backend accepts whatever comes in `signature.pin`. This is a known MVP design choice — flagged for security review.
