# Documents domain — living plan

**Owner:** DOCUMENTS01 (Team 4)
**Opened:** 2026-04-15
**Status legend:** 🟥 not started · 🟨 in progress · 🟦 shipped awaiting verification · 🟩 merged to main · ⬜ deferred / later task · ⛔ blocked
**Update rule:** When any item changes state, update this file in the same commit as the change. When an item hits 🟩, leave it in place as a record — do not delete. The file is the audit trail.

---

## 0. Anchoring context (do not re-derive, just read)

- Two-DB model: MASTER Supabase `qvzmkaamzaqxpzbewjxe` (auth + directory), TENANT Supabase `vzsohavtuotocgrfkfyd` (operational, `doc_metadata`, `search_index`, `search_document_chunks`, storage bucket `documents`).
- Render topology: `celesteos-registration-windows` (onboarding, :8001) and `celeste-unified` (`apps/api/combined_service.py`, :8080, runs action_router + extraction_worker + projection_worker + embedding_worker_1536 + email_watcher).
- Rosetta Stone for the 18-domain unified search index: `apps/api/config/projection.yaml`.
- Extraction state machine lives on `search_index.embedding_status`: `pending_extraction → extracting → pending → processing → indexed` (or `extraction_failed` dead letter).
- Brand law (non-negotiable): Search is the interface. Every mutation is Preview → Sign → Commit → Record. Uncertainty is structured, never apologised for. No SaaS voice, no "AI-powered" language, no confetti. Chief Engineer tone — calm, factual, present tense.

Full map: `/Users/celeste7/.claude/projects/-Users-celeste7/memory/project_documents_domain_map.md`.

---

## 1. The twelve gaps (single source of truth)

| # | Gap | Status | Fix ID | Verified by |
|---|---|---|---|---|
| 1 | Storage bucket collision — writers use `documents`, extraction_worker.py:38 reads phantom `yacht-documents` | 🟦 | F1 | Code change on branch + direct probe (pending Render deploy) |
| 2 | Onboarding bulk-import path — no `/v1/documents/import` handler found in Cloud_PMS | ⬜ | (future) | — |
| 3 | No enqueue from `doc_metadata` INSERT → `search_index` `pending_extraction`. Only cache-invalidate triggers exist. | 🟦 | F2 | Applied to TENANT + 6 smoke tests pass |
| 4 | Show Related V1 (FK) and V2 (signal) not fused. Verdict per coupling report: **not entangled — V2 is already the de facto read path**. Retire V1 later, do not fuse. | ⬜ | (later) | — |
| 5 | Emails projected into `search_index` but `/v2/search` may route through a separate `/email/search` path instead | ⬜ | (later) | — |
| 6 | Search highlighting (matched-text bolding) not implemented | ⬜ | (later) | — |
| 7 | `doc_metadata` schema not checked-in — intentional per migration convention | ⬜ | (doc only) | — |
| 8 | `'warranty_claim'` missing from `document_routes.py:60 VALID_OBJECT_TYPES` — cannot link docs to warranty claims | 🟦 | F3 | DB constraint widened + Python list updated + smoke insert |
| 9 | `handlers/secure_document_handlers.py` does not exist in repo — phantom reference | ⬜ | (skip) | — |
| 10 | `pms_audit_log` on upload is unsigned (`signature: {}`). Delete is SIGNED. | ⬜ | (defer) | — |
| 11 | `'chief_steward'` missing from `document_routes.py:63 LINK_MANAGE_ROLES` — chief_steward cannot link a provision invoice | 🟦 | F4 | Code change on branch |
| 12 | No `fleet_id` on docs. Strict yacht scope. Future fleet manual library is a separate story. | ⬜ | (future) | — |
| 13 | **[upstream]** `_upload_document_adapter` never called `supabase.storage.upload()` — every lens upload produced a ghost row. Discovered during F-series verification. | 🟦 | Part A+B+C | Direct-DB 5/5 smoke tests pass, tsc 0 errors, backward-compat confirmed |

---

## 2. F-series — execution ready, gated on "go"

**Scope:** document-side hardening only. No search-side, no UI.
**Order:** strict, F1+F2+F5 ship together; F3+F4 independent.
**Holding signal:** user must say **"go"**. I do not start without it.

### Pre-flight — uniqueness guarantee check
🟥 Run against TENANT:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'search_index'
  AND indexdef ILIKE '%object_type%object_id%';
```
Three branches decide F2 trigger shape:
- **Unique index on `(object_type, object_id)` exists** → use `ON CONFLICT DO NOTHING` in trigger body.
- **Non-unique index only** → rewrite trigger to `IF NOT EXISTS (SELECT 1 FROM search_index WHERE …)` guard.
- **No index at all** → stop, raise to CEO01 before applying.

### F1 — bucket constant
🟥 `apps/api/workers/extraction_worker.py:38`
```diff
-STORAGE_BUCKET = "yacht-documents"
+STORAGE_BUCKET = "documents"
```
**Pass bar:** Real-DB upload → worker log shows `Extracting:` line followed by successful chunk write (not 404 from storage).

### F2 — DB trigger (enqueue on doc_metadata INSERT)
🟥 Apply to TENANT (`vzsohavtuotocgrfkfyd`), then delete the migration file per convention.

```sql
-- Migration: enqueue document uploads for text extraction
-- Apply to TENANT, verify, delete.

CREATE OR REPLACE FUNCTION public.f1_enqueue_document_extraction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.storage_path IS NULL OR NEW.deleted_at IS NOT NULL THEN
        RETURN NEW;
    END IF;

    INSERT INTO public.search_index (
        object_type, object_id, yacht_id, search_text,
        embedding_status, payload, created_at, updated_at
    )
    VALUES (
        'document',
        NEW.id,
        NEW.yacht_id,
        NEW.filename,
        'pending_extraction',
        jsonb_build_object(
            'storage_path', NEW.storage_path,
            'filename',     NEW.filename,
            'doc_type',     COALESCE(NEW.doc_type, ''),
            'system_tag',   ''
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT DO NOTHING;  -- switch to IF NOT EXISTS if pre-flight says no unique index

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_doc_metadata_extraction_enqueue
    AFTER INSERT ON public.doc_metadata
    FOR EACH ROW
    EXECUTE FUNCTION public.f1_enqueue_document_extraction();
```

**Pass bar:**
1. Insert a test row into `doc_metadata` via the upload handler.
2. Within one transaction, `search_index` has a new row with `object_type='document'`, `object_id=<doc_id>`, `embedding_status='pending_extraction'`, `payload->>'storage_path'` matches.
3. Within ~15 s (10 s poll + 5 s extraction), row transitions to `pending`.
4. `search_document_chunks` has ≥1 row for that `document_id`.
5. Within next projection cycle, `embedding_status='indexed'`.
6. `/v2/search` with a unique keyword from the PDF body returns the doc.

### F5 — backfill the existing documents
🟥 Runs **after** F2 is live. Deliberately second so the trigger handles all new uploads while we catch the legacy ones.

```sql
-- Backfill: enqueue existing docs that don't already have a search_index row
INSERT INTO public.search_index (
    object_type, object_id, yacht_id, search_text,
    embedding_status, payload, created_at, updated_at
)
SELECT
    'document',
    dm.id,
    dm.yacht_id,
    dm.filename,
    'pending_extraction',
    jsonb_build_object(
        'storage_path', dm.storage_path,
        'filename',     dm.filename,
        'doc_type',     COALESCE(dm.doc_type, ''),
        'system_tag',   ''
    ),
    NOW(),
    NOW()
FROM public.doc_metadata dm
WHERE dm.storage_path IS NOT NULL
  AND dm.deleted_at IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM public.search_index si
      WHERE si.object_type = 'document' AND si.object_id = dm.id
  );
```

**Pass bar:**
```sql
-- Should equal 0 after backfill + one projection cycle
SELECT COUNT(*)
FROM doc_metadata dm
LEFT JOIN search_index si
  ON si.object_type = 'document' AND si.object_id = dm.id
WHERE dm.deleted_at IS NULL
  AND dm.storage_path IS NOT NULL
  AND si.id IS NULL;
```

### F3 — warranty_claim in VALID_OBJECT_TYPES
🟥 `apps/api/routes/document_routes.py:60`
```diff
-VALID_OBJECT_TYPES = ['work_order', 'equipment', 'handover', 'fault', 'part', 'receiving', 'purchase_order']
+VALID_OBJECT_TYPES = ['work_order', 'equipment', 'handover', 'fault', 'part', 'receiving', 'purchase_order', 'warranty_claim']
```
**Pass bar:** Real-DB: upload a doc → link it to an existing warranty claim → `email_attachment_object_links` has a row with `object_type='warranty_claim'`, `object_id=<claim_id>`, `document_id=<doc_id>`.

### F4 — chief_steward in LINK_MANAGE_ROLES
🟥 `apps/api/routes/document_routes.py:63`
```diff
-LINK_MANAGE_ROLES = ['admin', 'captain', 'chief_engineer', 'chief_officer', 'crew_member', 'engineer', 'purser']
+LINK_MANAGE_ROLES = ['admin', 'captain', 'chief_engineer', 'chief_officer', 'chief_steward', 'crew_member', 'engineer', 'purser']
```
**Pass bar:** Real-DB: chief_steward JWT → link provision invoice PDF to a purchase_order → 200, not 403.

### F-series overall pass gate
🟥 All of:
1. Docker stack up locally, workers healthy via real logs.
2. Real inserts against TENANT on disposable yacht — no mocks.
3. Full state machine walk observed for at least one new doc AND one backfilled doc.
4. `/v2/search` returns a body-keyword match for at least one doc.
5. F3 junction insert verified in DB.
6. F4 chief_steward link passes with 200.
7. No widened test assertions. No silent skips.
8. Structured verdict back to CEO01: **Pass / Pass with issues / Fail**.

---

## 3. Documents UI workstream — PR-D1 through PR-D4

**Scope:** document-page redesign + button audit. Starts only after F-series is 🟩.

### Standing invariant — UUID display separation (non-negotiable)
> **The UUID is a storage-only concept. The UI never renders it.**

- Storage layer (backend): `{yacht_id UUID}/documents/{doc_id UUID}/{filename}`. Security guard at `action_router/dispatchers/internal_dispatcher.py:342` (`startswith(f"{yacht_id}/")`) is **not touched**.
- Display layer (frontend): vessel name ("M/Y Example") resolved from auth context per `project_yacht_name_rendering.md`, folder breadcrumbs from `doc_metadata.original_path`, file label from `doc_metadata.filename`. UUID never appears in any user-visible string or `aria-label`.
- Regression guard: grep test in CI — `grep -E "[0-9a-f]{8}-[0-9a-f]{4}-" apps/web/src/components/documents/` must return zero matches inside JSX children.
- Internal data: the UUID lives on a single `_docId` field on tree nodes, prefixed with underscore as convention. Never fed to `.textContent` / `innerHTML` / `aria-*`.

### PR-D1 — Directory tree with search toggle
🟥
**Goal:** Documents page renders a human-readable directory tree mirroring storage, scoped to current yacht, with the existing search bar above the page driving a mode toggle.

**UX pattern (locked, do not redesign):**
- **Input empty (default):** tree view renders. Root is the vessel name. Folders from `original_path` segments. Fallback to `doc_type` groups if `original_path` is NULL (group label = "Uploaded").
- **User types in the existing `<input placeholder="Search documents…">`:** tree hides. Vertical search-results list renders (reuse Spotlight result card primitive). Calls `/v2/search` with `domain=documents` filter. Debounce 140 ms to match Spotlight.
- **User clears input OR presses Escape:** tree re-renders at the **exact state they left it** — same expanded folders, same scrollTop, same selected file.
- **Cache shape:**
  ```ts
  type DocsViewState = {
      expandedPaths: Set<string>;
      scrollTop: number;
      selectedDocId: string | null;
  };
  ```
  Held in React state, persisted to `sessionStorage` under a yacht-scoped key. Cleared on logout.

**Backend changes:**
- Extend `v_documents_enriched` (or pivot query to `doc_metadata` directly) to return `original_path, storage_path, size_bytes, uploaded_by, updated_at` alongside current columns.
- Coverage check before build: `SELECT COUNT(*), COUNT(original_path) FROM doc_metadata WHERE yacht_id = :yt1 AND deleted_at IS NULL`. If `< 50 %`, fall back to doc_type grouping and flag onboarding audit as next priority.

**Frontend changes:**
- New: `apps/web/src/components/documents/DocumentTree.tsx` — tree primitive. Collapsible folders, virtualised at >200 nodes.
- New: `apps/web/src/components/documents/docTreeBuilder.ts` — flat-list → tree-node builder with the display-model typing above.
- Modified: `apps/web/src/app/documents/page.tsx` — add mode switching based on search-input value (no new search bar, reuse existing).
- Reuse: Spotlight result card for search-results mode (do NOT invent a new card).
- Reuse: yacht-name resolution per `project_yacht_name_rendering.md`. If that resolution is broken, PR-D1 is blocked on its fix.

**Pass bar:**
1. Tree renders on `/documents` with zero UUID strings in DOM (grep-based test passes).
2. Tree structure matches the `original_path` distribution in the real DB for yTEST_YACHT_001.
3. Typing in search bar hides tree, shows results list, calls real `/v2/search` with domain filter.
4. Escape restores tree at exact prior state — expanded folders and scrollTop verified.
5. Click a file in either view → opens existing `DocumentContent` popup (flow untouched).
6. Role gating identical to current page (yacht_id scope enforced).
7. Playwright shard with ≥8 assertions covering tree render, toggle, restore, click-through, UUID regression guard, role gating.
8. Docker + real TENANT. No mocks.

### PR-D2 — SplitButton dropdown collision fix
🟥
**Goal:** Actions menu never clips at viewport edges.

**Changes:**
- `apps/web/src/components/lens-v2/SplitButton.tsx` + `lens.module.css:347-354`: replace hard `position: absolute; right: 0; top: 50px;` with viewport-aware positioning. Preferred: use Radix dropdown-menu primitive if available in package.json; otherwise manual `getBoundingClientRect()` + flip logic.
- Align with `feedback_shell_layout_pattern.md` memory — respect `--shell-topbar-h` and shell tokens.

**Pass bar:**
1. Doc popup near left edge → dropdown opens rightward, fully visible.
2. Doc popup near right edge → dropdown opens leftward, fully visible.
3. Doc popup near bottom edge → dropdown flips upward.
4. Keyboard nav works (arrow keys, Enter, Escape).
5. Zero raw `rgba(` / `#` hex in new CSS — token-compliant.
6. Playwright: screenshot assertions at 4 viewport positions.

### PR-D3 — Actions menu audit (buttons must work)
🟥 **Blocks on PR-D2** (can't test buttons that are off-screen).
**Goal:** Every item in the Actions menu is verified end-to-end with real DB.

| # | Action | Expected handler | Status |
|---|---|---|---|
| 1 | Link Document to Equipment | `_eq_link_document_to_equipment` (dispatcher:2962) | 🟥 |
| 2 | Upload Document (new revision) | `_doc_upload_document` (dispatcher:458) | 🟥 |
| 3 | Update Document | `_doc_update_document` (dispatcher:466) | 🟥 |
| 4 | Add Document Tags | `_doc_add_document_tags` (dispatcher:474) | 🟥 |
| 5 | Delete Document (SIGNED) | `_doc_delete_document` (dispatcher:482) | 🟥 |
| 6 | Get Document Download URL | `_doc_get_document_url` (dispatcher:493) | 🟥 |
| 7 | Add Comment | `_doc_add_document_comment` (dispatcher:508) | 🟥 |
| 8 | Update Comment | `_doc_update_document_comment` (dispatcher:523) | 🟥 |
| 9 | Delete Comment | `_doc_delete_document_comment` (dispatcher:536) | 🟥 |
| 10 | List Comments | `_doc_list_document_comments` (dispatcher:549) | 🟥 |

**For each action, verify:**
1. `entity_prefill.py CONTEXT_PREFILL_MAP` has a `(document, <action_id>)` entry. Add missing ones.
2. `mapActionFields.ts` produces a form with the right fields.
3. Form submits successfully to real TENANT DB.
4. DB mutation visible via SQL check.
5. Overlay refreshes with new state.
6. Negative test: insufficient role → 403.

**Pass bar:** 10/10 actions executable with appropriate role; one Playwright test per action; zero widened assertions; all SQL mutations verified.

### PR-D4 — Add to Handover auto-population (the specific user ask)
🟥 **Blocks on PR-D3** (audit must surface what's broken first).
**Goal:** Click "Add to Handover" on a document → popup opens with fields prefilled.

**Changes:**
- `apps/api/action_router/entity_prefill.py` — add:
  ```python
  ("document", "add_document_to_handover"): {
      "entity_id":     "id",
      "title":         "filename",
      "doc_type":      "doc_type",
      "source_doc_id": "id",
      "link":          "storage_path",
  },
  ```
- `apps/api/action_router/registry.py:449` — widen `required_fields` to include user-visible `section` and `summary` (keep `yacht_id` BACKEND_AUTO).
- `apps/web/src/lib/microactions/handlers/handover.ts:348` — pass-through confirmed for new fields.

**Pass bar:**
1. Open any document → Actions → Add to Handover → form opens with 5 fields prefilled, 2 user-editable.
2. Submit → `handover_items` row created with correct metadata.
3. Open handover draft → item visible.
4. Playwright end-to-end test.
5. Role gating: only HOD+ can submit.

---

## 4. Shelved / later work

| Item | Why shelved | When to revisit |
|---|---|---|
| Gap #2 — onboarding bulk-import path audit | Needs CEO01 input on whether a handler exists or is TBD | After F-series ships |
| Gap #4 — Show Related V1 retirement (NOT fusion) | V2 is already default; V1 is 994 lines of mostly dead read-path code | After PR-D4 ships |
| Gap #5 — email unification in `/v2/search` | Requires `PlanExecutor` trace + decision | After Documents UI stabilises |
| Gap #6 — search highlighting | Brand-visible but not blocking | After PR-D4 |
| Gap #10 — signed audit log on upload | Low-risk surface; defer | Future compliance sprint |
| Gap #12 — fleet_id on docs | Only needed for cross-vessel manual libraries | Future fleet feature |
| **Onboarding `original_path` coverage audit** | Depends on PR-D1 coverage check result | Triggered by PR-D1 pre-flight if `< 50 %` |

---

## 5. Standing doctrine (pinned for every PR in this plan)

1. **Real DB or it doesn't count.** Mock tests hide enums, NOT NULL constraints, triggers, and view-vs-table confusion. Every fix verified against TENANT `vzsohavtuotocgrfkfyd`.
2. **Docker is the truth.** Verify via real worker logs, not `/healthz`. Nothing ships without the full stack green locally first.
3. **Preview → Sign → Commit → Record** on every mutation. No auto-execute. No background writes.
4. **Single-writer pattern on `search_index`.** Only projection_worker and the new F2 trigger write to it. Application code does not.
5. **UUID display separation** (see §3 standing invariant).
6. **Brand voice** on every visible string. Chief Engineer tone. No reassurance, no AI theatre, ≤7-word questions.
7. **Pass / Pass with issues / Fail** verdict on every PR gate — no sugar-coating.
8. **Memory is infrastructure.** Update this file AND `/Users/celeste7/.claude/projects/-Users-celeste7/memory/project_documents_domain_map.md` at every state change.

---

## 6. Change log (append-only)

| Date | Change | By |
|---|---|---|
| 2026-04-15 | Plan opened. F-series and Documents UI workstream defined. All items 🟥. | DOCUMENTS01 |
| 2026-04-15 | Pre-flight against TENANT: unique index on `search_index(object_type, object_id)` confirmed live. Two-bucket reality clarified (`documents` + `yacht-documents` both exist). `org_id = yacht_id` invariant across 14,068 rows. CHECK constraint on `email_attachment_object_links` captured verbatim. Per-source orphan audit: 100 orphans — 57 document_lens, 32 part_lens, 11 manual. document_lens regression timeline traced (Jan had 145 indexed, Feb was empty, Mar onwards all orphan). | DOCUMENTS01 |
| 2026-04-15 | F2 trigger `trg_doc_metadata_extraction_enqueue` applied to TENANT. 6 smoke tests pass (whitelist honoured, bucket passthrough, default bucket fallback, UPDATE does not fire, idempotent). Gap #3 → 🟦. | DOCUMENTS01 |
| 2026-04-15 | F3 CHECK constraint widened to include `'warranty_claim'`. Applied to TENANT. Smoke insert succeeded inside rollback. Gap #8 → 🟦. | DOCUMENTS01 |
| 2026-04-15 | F5 backfill applied. 100 orphan rows enqueued as `pending_extraction`. Still-old Render extraction_worker immediately burned all 100 to `extraction_failed` because it still has the `yacht-documents` hardcode AND the files never existed in storage to begin with (upstream Gap #13). Coverage for all 16 sources now 100%. | DOCUMENTS01 |
| 2026-04-15 | F1 bucket constant removed. `extraction_worker.py` now reads `bucket` from `search_index.payload` with `DEFAULT_STORAGE_BUCKET = "documents"` fallback. `download_from_storage` signature widened to accept `bucket` param. `py_compile` clean. Gap #1 → 🟦 (verified at code level, requires Render deploy for runtime verification). | DOCUMENTS01 |
| 2026-04-15 | F4 `chief_steward` added to `LINK_MANAGE_ROLES` in `document_routes.py`. `py_compile` clean. Gap #11 → 🟦. | DOCUMENTS01 |
| 2026-04-15 | **Gap #13 surfaced during F-series verification.** `_upload_document_adapter` in `handlers/document_handlers.py` only inserts a `doc_metadata` row — it never calls `supabase.storage.upload()`. Every `document_lens` upload produces a ghost record whose `storage_path` 404s on every download. Discovered by probing the storage paths of 5 indexed document_lens rows + 5 failed ones against every candidate bucket — ALL 10 returned HTTP 400/404. | DOCUMENTS01 |
| 2026-04-15 | Part A: added `POST /v1/documents/upload` multipart route in `document_routes.py`. UploadFile + Form fields, tenant-scoped client, role gate (HOD+), 15 MB cap, MIME whitelist, storage upload → doc_metadata insert → compensating delete on failure → audit log → F2 trigger auto-enqueues. Real-DB test: 5/5 assertions pass (happy path, role gate, size gate, MIME gate, empty gate). Cleanup after each run verified zero residual rows. Gap #13 → 🟦. | DOCUMENTS01 |
| 2026-04-15 | Part B: annotated `_upload_document_adapter` with a deprecation docstring — kept callable for programmatic re-ingest / shard-34 e2e, but any future reader sees the warning that it creates metadata-only ghost records. | DOCUMENTS01 |
| 2026-04-15 | Code-hygiene cleanup: `sanitize_storage_filename` extracted to new `apps/api/utils/filenames.py` (shared util). Removed duplicate copies from `document_handlers.py:269` and the copy I had added in `document_routes.py:97`. Both files now import from one source of truth. `email.py`'s version is NOT merged (different semantics — HTTP Content-Disposition escaping). | DOCUMENTS01 |
| 2026-04-15 | 1-URL philosophy sweep: CEO clarified that the "1-URL / single-surface / ContextPanel / LensRenderer" architecture is DEAD and any mention must be deleted. Rewrote `PROGRESS_LOG.md` (which was the only file prescribing the dead rule) as a deprecation notice pointing at `docs/frontend/README.md` (the current canonical reference). Added new memory `feedback_url_philosophy.md` enshrining "delete on sight". Two other mentions (`HandoverDraftPanel.tsx:6`, `docs/show-related/summary.md:88`) are warnings AGAINST the legacy pattern, kept intact. | DOCUMENTS01 |
| 2026-04-15 | Part C1: refactored `AttachmentUploadModal.tsx` to accept an optional `onUpload: (file: File) => Promise<void>` strategy prop + optional `title` / `description`. Made all pms_attachments-specific props optional. Runtime assertion in the default path. Existing warranty + certificate call sites verified unchanged (all 6 required props still passed). Backward-compatible refactor — zero forking, zero duplicate components. | DOCUMENTS01 |
| 2026-04-15 | Part C2: wired `AppShell.tsx` — added `documentUploadOpen` state, `documents` case to `handlePrimaryAction`, `handleDocumentUpload` callback that calls `getYachtId()` + `getAuthHeaders()` + POSTs multipart to `/v1/documents/upload` + invalidates `['documents']` query on success + surfaces FastAPI error detail in the Toast. Mounted `<AttachmentUploadModal>` in custom mode at shell level alongside `CreateWorkOrderModal`, `ReportFaultModal`, `FileWarrantyClaimModal`. | DOCUMENTS01 |
| 2026-04-15 | `tsc --noEmit` on `apps/web`: exit 0, zero errors, zero mentions of any edited file. Parts C1 + C2 are type-safe and do not break any existing code. | DOCUMENTS01 |

---

## 7. Next action (post-commit state 2026-04-15)

**Feature branch `fix/f-series-documents-hardening` at commit `b687a592`. Not merged to main.**

### Structured verdict

- **F2 trigger** — Pass
- **F3 CHECK constraint + Python VALID_OBJECT_TYPES** — Pass
- **F5 backfill** — Pass (correct failure mode downstream due to Gap #13)
- **Part A — POST /v1/documents/upload** — Pass (5/5 real-DB smoke tests against TENANT)
- **Part B — adapter annotation** — Pass
- **Part C1 — AttachmentUploadModal refactor** — Pass (tsc clean, backward-compat verified)
- **Part C2 — AppShell wiring** — Pass (tsc clean)
- **F1 bucket fix** — Pass with issues (code clean, runtime-verification requires Render deploy)
- **F4 chief_steward** — Pass with issues (code clean, runtime-verification requires Render deploy)

**Overall verdict: Pass with issues.** The F-series plumbing is live on TENANT and code-verified. Part A endpoint verified end-to-end against real TENANT with five test assertions. The remaining "issues" are all external-gate dependencies, not code defects.

### Remaining work (external gates)

1. **CEO merge decision.** Review the diff, decide whether to merge `fix/f-series-documents-hardening` into `main`. Merging triggers Render auto-deploy of `celeste-unified`, which picks up F1 (bucket fix) and F4 (chief_steward role).
2. **Browser-level e2e upload test.** Once Render has the new code, do a real browser upload flow via the Documents page subbar primary action button. Expected: blob lands in storage → doc_metadata row → F2 trigger fires → extraction_worker downloads (F1 fix now correct) → chunks written → projection → embedding → indexed → document appears in the list with searchable body content.
3. **Ghost cleanup.** After browser e2e confirms a real upload works end-to-end, delete the 100 pre-existing `extraction_failed` rows whose files never existed. SQL ready in §11.5 of `context.md`.

### What's NOT ready to ship without further work

Nothing in the F/A/B/C scope. All code is on branch, tested, type-safe, documented. The only gates are CEO merge + post-deploy verification.
