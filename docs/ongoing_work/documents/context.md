# Documents workstream — context dump (HISTORICAL ARCHIVE)

> **ARCHIVED 2026-04-17.** This file is a point-in-time snapshot from 2026-04-15. It documents the F-series investigation phase BEFORE the MVP fixes in PRs #562-#615. For current state, see:
> - **DOCUMENTS_HANDOVER.md** — CEO-ready summary of all work done
> - **DOCUMENTS_DOMAIN_GUIDE.md** — how the domain works (technical reference)
> - **DOCUMENTS_TEST_RESULTS.md** — browser test evidence (8/8 PASS)
> - **DOCUMENTS_MVP_CHEATSHEET.md** — manual test scenarios (fillable)

**Generated:** 2026-04-15 during F-series execution
**Source:** live TENANT (vzsohavtuotocgrfkfyd) evidence, not assumption
**Status:** F2, F3, F4, F5 applied to TENANT. F1 code on feature branch. **A critical upstream bug surfaced that invalidates part of the original F-series premise** — see §7.
**Reader rule:** everything below is point-in-time evidence. Verify before acting on any of it.

---

## 1. Environment snapshot

- **Git branch:** `fix/f-series-documents-hardening` (local), based on `main` at commit `3454d7b8 fix(auth): define logger before cachetools try/except block (#537)`
- **Render auto-deploy:** `celeste-unified` service deploys on push to `main`. Feature branch work is safe.
- **Tools available locally:** `psql 17`, `python3`, `psycopg2 2.9.11`, `requests 2.32.3`
- **TENANT DB DSN (used read+write this session):** `postgresql://postgres:@-Ei-9Pa.uENn6g@db.vzsohavtuotocgrfkfyd.supabase.co:6543/postgres`
- **Supabase URL:** `https://vzsohavtuotocgrfkfyd.supabase.co`

---

## 2. Supabase Storage buckets (live inventory)

14 buckets in TENANT:

| bucket | public | created | notes |
|---|---|---|---|
| `documents` | false | 2025-11-20 | primary lens-upload target per handler comments |
| `yacht-documents` | false | 2026-03-18 | **NOT phantom** — contains 3 yacht folders with real NAS content |
| `vessel-imports` | false | 2026-04-06 | onboarding import staging |
| `pms-warranty-documents` | false | 2026-04-14 | warranty docs |
| `pms-certificate-documents` | false | 2026-04-14 | certificate docs |
| `handover-exports` | false | 2026-02-03 | |
| `pms-label-pdfs` | false | 2026-01-09 | part labels (37 doc_metadata rows reference it) |
| `pms-finance-documents` | false | 2026-01-09 | |
| `pms-discrepancy-photos` | false | 2026-01-09 | |
| `pms-part-photos` | false | 2026-01-09 | |
| `pms-receiving-images` | false | 2026-01-09 | |
| `pms-work-order-photos` | false | 2026-01-30 | |
| `ledger_exports` | false | 2026-04-13 | **duplicate** of next — flag for cleanup |
| `ledger-exports` | false | 2026-04-13 | duplicate of previous |

**Key correction:** my earlier plan assumed `yacht-documents` was phantom. It is not. The user also stated it did not exist; that was also wrong. Both `documents` and `yacht-documents` exist and hold content.

### 2.1 Actual bucket contents (probed)

**`documents` bucket under `85fe1119-b04c-41ac-80f1-829d23322598/`:** top-level folders are category labels — `01_BRIDGE, 01_OPERATIONS, 02_ENGINEERING, 03_DECK, 04_ACCOMMODATION, 05_GALLEY, 06_SYSTEMS, 07_SAFETY, 08_CAPTAIN`. Listing `.../documents/` prefix returns **empty**. There is no `{yacht_id}/documents/{doc_id}/` structure in this bucket at all.

**`yacht-documents` bucket under `85fe1119-b04c-41ac-80f1-829d23322598/`:** similar but different set — `01_BRIDGE, 01_General, 02_ENGINEERING, 03_DECK, 04_Manuals, 05_Drawings, 06_PROCEDURES, 07_SAFETY, 08_MAINTENANCE, 09_LOGS`. These look like raw NAS-imported category folders.

**`yacht-documents` under `73b36cab/`:** contains `test_file_05.txt` (12 bytes) — a NAS import, downloads cleanly from `yacht-documents` bucket at the path `73b36cab-a606-4b85-ab64-a11aae62d966/test_file_05.txt`.

**Neither bucket** contains anything at `{yacht_id}/documents/{doc_id}/{filename}` — the path convention that `doc_metadata.storage_path` uses for `source='document_lens'` rows.

---

## 3. TENANT DB schema snapshot (verified this session)

### 3.1 `search_index`
- **25 columns.** Key: `id bigint PK`, `object_type text NOT NULL`, `object_id uuid NOT NULL`, `org_id uuid NOT NULL`, `yacht_id uuid NULL`, `search_text text NOT NULL`, `payload jsonb DEFAULT '{}'`, `filters jsonb DEFAULT '{}'`, `embedding_status text DEFAULT 'indexed'`, `embedding_1536 vector`, `tsv tsvector`, `content_hash text`, `source_version bigint DEFAULT 0`.
- **41 indexes.** Relevant:
  - `search_index_object_type_object_id_key` — **UNIQUE btree on (object_type, object_id)**. This is the invariant F2 relies on for `ON CONFLICT DO NOTHING`.
  - `idx_search_index_extraction_queue` — partial btree on `(embedding_status, updated_at) WHERE embedding_status IN ('pending_extraction','extracting')`. This is the index extraction_worker uses for its claim query.
  - `ix_search_vector` and `ix_si_vec1536_hnsw` — HNSW vector indexes for pgvector cosine similarity (1536-dim and another).
- **Triggers:**
  - `trg_enqueue_embedding_on_search_index` — AFTER INSERT + AFTER UPDATE. Enqueues into `embedding_jobs` for the downstream embedding worker.
  - `trg_search_index_dataset_version` — AFTER INSERT/UPDATE/DELETE.
  - `set_search_index_updated_at` — BEFORE UPDATE.
- **org_id is invariant = yacht_id across all 14,068 rows.** Validated via `SELECT * FROM search_index GROUP BY org_id, yacht_id` — 100 % match, zero exceptions. Trigger can safely set `org_id := NEW.yacht_id`.
- **No `fleet`, `org`, or `tenant` lookup table** exists in TENANT (`SELECT table_name WHERE LIKE '%fleet%' OR '%org%' OR '%tenant%'` → empty).

### 3.2 `doc_metadata`
- **29 columns.** Key: `id uuid PK`, `yacht_id uuid NOT NULL`, `source text NOT NULL`, `filename text NOT NULL`, `storage_path text NOT NULL`, `original_path text NULL`, `content_type text NULL`, `size_bytes bigint NULL`, `sha256 text NULL`, `storage_bucket text NULL` (the per-row bucket selector), `equipment_ids uuid[]`, `tags text[]`, `indexed bool`, `indexed_at timestamptz`, `metadata jsonb`, `system_path text`, `doc_type text`, `oem text`, `model text`, `system_type text`, `document_type text`, `description text`, `deleted_at timestamptz`, `deleted_by uuid`, `deleted_reason text`, `embedding vector`, `is_seed bool`.
- **Triggers on doc_metadata BEFORE F2 was applied:** only `trg_doc_metadata_cache_invalidate` AFTER INSERT + AFTER UPDATE (calls `f1_cache_invalidate('document')`). **No trigger inserted into `search_index`.** Confirmed — Gap #3 is real.

### 3.3 `search_document_chunks`
- **37 columns** including `id uuid`, `yacht_id uuid`, `document_id uuid`, `chunk_index int`, `text text`, `content text`, `content_hash text`, `embedding vector`, `embedding_1536 vector`, `tsv tsvector`, `section_title text`, `graph_extract_status text NOT NULL`, plus many OCR/vision fields.
- **47,166 rows total** (all domains, not just documents).

### 3.4 `email_attachment_object_links`
- **CHECK constraint `email_attachment_object_links_object_type_check`**, before F3:
  ```
  CHECK (object_type = ANY (ARRAY['work_order'::text, 'equipment'::text, 'handover'::text,
         'fault'::text, 'part'::text, 'receiving'::text, 'purchase_order'::text]))
  ```
  After F3: `'warranty_claim'::text` added at end.

### 3.5 `pms_warranty_claims`
- Exists. PK `id uuid`. Has `yacht_id, claim_number, equipment_id, fault_id, work_order_id, title, description, claim_type, vendor_id`.
- **8 rows total in TENANT** (8 test warranty claims across all tenants).

---

## 4. Data distributions (live at 2026-04-15, pre-F-series)

### 4.1 doc_metadata by source (live rows with storage_path)

| source | dm_count | si_count (pre-F5) | orphan (pre-F5) | coverage |
|---|---|---|---|---|
| nas | 3,219 | 3,219 | 0 | 100 % |
| document_lens | 202 | 145 | 57 | 71.8 % |
| part_lens | 37 | 5 | 32 | 13.5 % |
| test | 26 | 26 | 0 | 100 % |
| internal | 22 | 22 | 0 | 100 % |
| regulatory | 21 | 21 | 0 | 100 % |
| crew | 20 | 20 | 0 | 100 % |
| oem | 20 | 20 | 0 | 100 % |
| vendor | 20 | 20 | 0 | 100 % |
| manual | 11 | 0 | 11 | 0 % |
| work_order_photo | 5 | 5 | 0 | 100 % |
| equipment_photo | 5 | 5 | 0 | 100 % |
| fault_photo | 5 | 5 | 0 | 100 % |
| invoice_upload | 5 | 5 | 0 | 100 % |
| voice_note | 5 | 5 | 0 | 100 % |
| checklist_photo | 4 | 4 | 0 | 100 % |

**Total:** 3,627 live doc_metadata rows, 3,601 pre-F5 search_index rows, 100 orphans. After F5 backfill: all 16 sources at 100 %.

### 4.2 doc_metadata.storage_bucket distribution

| storage_bucket value | rows |
|---|---|
| `documents` | 2,940 |
| NULL | 650 |
| `pms-label-pdfs` | 37 |
| `yacht-documents` | **0** |

**Nothing in doc_metadata points at `yacht-documents`** — so the extraction_worker's old hardcoded `yacht-documents` bucket was never going to match any doc_metadata row's storage_path.

### 4.3 Multi-tenant spread

Two yachts in TENANT:

| yacht_id | doc_metadata rows | orphans (pre-F5) |
|---|---|---|
| `85fe1119-b04c-41ac-80f1-829d23322598` | 3,324 | 100 |
| `73b36cab-a606-4b85-ab64-a11aae62d966` | 303 | 0 |

All 100 orphans are on yacht `85fe1119`. Yacht `73b36cab` has only NAS-sourced docs, all indexed. The 85fe1119 yacht is the one running e2e shard tests.

### 4.4 document_lens timeline (the regression)

| month | indexed | orphan |
|---|---|---|
| 2026-01 | 145 | 0 |
| 2026-02 | 0 | 0 |
| 2026-03 | 0 | 55 |
| 2026-04 | 0 | 2 |

- **Last indexed `document_lens` row:** `2026-01-30 20:16:52` — `read-test-1769804212.pdf`.
- **First orphaned `document_lens` row:** `2026-03-13 23:24:41` — `s34-hod-smoke-doc-*.pdf`.
- **Nothing in February.**

Interpretation: whatever code path was populating search_index for lens uploads stopped running between 2026-01-30 and 2026-03-13. Not resumed since. The 145 January rows were indexed via some mechanism that no longer runs.

### 4.5 search_index embedding_status distribution (documents only, pre-F5)

| status | rows |
|---|---|
| `indexed` | 3,578 |
| `storage_only` | 22 (all `nas` source) |
| `deleted` | 1 |
| anything else | 0 |

`storage_only` is a terminal state I did not know existed — marks a doc whose file exists but has no extractable text (likely pure images or binary blobs). Set by some other code path, not the extraction_worker.

---

## 5. Existing code paths that write to `search_index`

Discovered during this session:

1. **`apps/api/services/import_service.py:425-459`** — the NAS bulk-import path. Directly upserts into `search_index` with `embedding_status='pending'` and seeds `search_text` from structured entity fields. This is how NAS-source docs get their search_index rows. Runs after inserting entity rows. Uses Supabase `.upsert(..., on_conflict="object_type,object_id")` which means it OVERWRITES any existing row.
2. **`apps/api/workers/projection_worker.py`** — documented single-writer for projection-updates. UPDATEs search_index, does not INSERT new rows in normal flow. Relies on the `search_projection_map` table of domain mappings.
3. **`admin_upsert_search_index()` Postgres function** — SECURITY DEFINER, INSERT ON CONFLICT DO UPDATE with source_version guard. **Zero Python call sites** — unused from application code. Declared but never invoked.
4. **(As of this session)** `f1_enqueue_document_extraction()` — F2 trigger function, see §6.

### 5.1 `trg_enqueue_embedding_on_search_index` (existing downstream trigger)
- AFTER INSERT and AFTER UPDATE on `search_index`
- Enqueues rows into `embedding_jobs` for `embedding_worker_1536.py`
- Implication: anything that inserts into search_index automatically gets embedding queue entries downstream. No manual embedding enqueue needed.

---

## 6. What F2/F3/F4/F5 actually shipped to TENANT this session

### 6.1 F2 — `trg_doc_metadata_extraction_enqueue` (APPLIED, VERIFIED)

**Applied via:** `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f2_doc_extraction_enqueue.sql`

**Function created:** `public.f1_enqueue_document_extraction()` — plpgsql, returns TRIGGER.
- Guards: skips `storage_path IS NULL`, skips `deleted_at IS NOT NULL`.
- **Source whitelist:** fires only for `document_lens, part_lens, manual, voice_note, invoice_upload, work_order_photo, equipment_photo, fault_photo, checklist_photo`. Explicitly excludes `nas` (has its own enqueue path via import_service.py) and test-fixture sources (`test, internal, regulatory, crew, oem, vendor`, all at 100 % coverage via other paths).
- Sets `org_id := NEW.yacht_id` (invariant confirmed against 14,068 rows).
- Seeds `search_text := NEW.filename`. Extraction_worker will replace with enriched text after successful download.
- Payload contains: `storage_path, filename, doc_type, system_tag, bucket, source`. The `bucket` is resolved as `COALESCE(NEW.storage_bucket, 'documents')`.
- `ON CONFLICT (object_type, object_id) DO NOTHING` — idempotent, leverages existing unique index.
- Emits `pg_notify('f1_cache_invalidate', ...)` matching the existing pattern from `admin_upsert_search_index`.

**Trigger created:** `trg_doc_metadata_extraction_enqueue` — AFTER INSERT on `public.doc_metadata`, per row, executes the function above.

**Verified via `/tmp/f2_smoke_test.py`:**
1. ✅ `document_lens` INSERT → enqueued with `pending_extraction`.
2. ✅ `nas` INSERT → NO enqueue (whitelist honoured).
3. ✅ `manual` INSERT → enqueued.
4. ✅ `part_lens` with `storage_bucket='pms-label-pdfs'` → enqueued, bucket passed through in payload.
5. ✅ `document_lens` with `storage_bucket=NULL` → enqueued, payload bucket defaults to `'documents'`.
6. ✅ UPDATE on `doc_metadata` → does NOT duplicate search_index row (trigger is AFTER INSERT only).

All 5 test rows hard-deleted from `doc_metadata` + `search_index` after test.

### 6.2 F3 — CHECK constraint widened (APPLIED, VERIFIED)

**Applied via:** `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f3_warranty_claim_constraint.sql`

**Constraint now:**
```
CHECK (object_type = ANY (ARRAY['work_order'::text, 'equipment'::text, 'handover'::text,
       'fault'::text, 'part'::text, 'receiving'::text, 'purchase_order'::text,
       'warranty_claim'::text]))
```

**Verified:** smoke INSERT with `object_type='warranty_claim'` into `email_attachment_object_links` succeeded inside a manual transaction, rolled back (no residual row). Confirmed zero residual `warranty_claim` links afterwards.

### 6.3 F4 — `chief_steward` role in Python list (CODE CHANGE, NOT YET DEPLOYED)

**Edit at `apps/api/routes/document_routes.py:63`** (on feature branch only):
```python
LINK_MANAGE_ROLES = ['admin', 'captain', 'chief_engineer', 'chief_officer',
                     'chief_steward', 'crew_member', 'engineer', 'purser']
```
Same file, `VALID_OBJECT_TYPES` at line 60 also extended to include `'warranty_claim'` so the Python gate matches the DB CHECK constraint.

**Not yet runtime-verified** — requires the feature branch to be deployed to Render (merge to main). Current production still has the pre-change Python gate, but since F3 widened the DB constraint, there's no contradiction — Python gate is simply a less-permissive mirror until deploy.

### 6.4 F5 — backfill (APPLIED, VERIFIED)

**Applied via:** `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f5_doc_extraction_backfill.sql`

**Result:** 100 rows inserted into `search_index` with `embedding_status='pending_extraction'`. Per-source pre/post:

| source | pre-orphans | post-orphans |
|---|---|---|
| document_lens | 57 | 0 |
| part_lens | 32 | 0 |
| manual | 11 | 0 |

All 16 sources now at 100 % search_index coverage.

### 6.5 F1 — extraction_worker bucket-from-payload (CODE CHANGE, NOT RUNTIME-VERIFIED)

**Edit at `apps/api/workers/extraction_worker.py` (4 places, on feature branch only):**
- Line 38: renamed constant `STORAGE_BUCKET = "yacht-documents"` → `DEFAULT_STORAGE_BUCKET = "documents"`.
- Line 119: `download_from_storage` signature gained `bucket: str = DEFAULT_STORAGE_BUCKET` param.
- Line 124: URL built as `{SUPABASE_URL}/storage/v1/object/authenticated/{bucket}/{storage_path}` (reads the passed arg instead of hardcoded constant).
- Line 253: `process_row` reads `bucket = payload.get("bucket") or DEFAULT_STORAGE_BUCKET`.
- Line 269: download call passes `bucket=bucket`.

**Python `py_compile` passes on the edited file.** Not yet runtime-verified against real files (see §7).

---

## 7. THE CRITICAL UPSTREAM BUG — upload handler never uploads file bytes

This is the single most important finding of the session and it was not visible before DB probes.

### 7.1 What I found
When I probed the actual storage paths from indexed `document_lens` rows (5 random samples) against every candidate bucket, **every single one returned 404**. Concretely:

```
path: 85fe1119.../documents/01213075.../read-test-1769804212.pdf
  bucket=documents        HTTP 400 (body says "not_found")
  bucket=yacht-documents  HTTP 400 (body says "not_found")
  bucket=pms-label-pdfs   HTTP 400
  bucket=vessel-imports   HTTP 400
```

Same result for the orphan paths. **No lens-upload path resolves in any bucket.**

### 7.2 Reading `apps/api/handlers/document_handlers.py` at line 293-375 (`_upload_document_adapter`)

```python
# Build storage path: {yacht_id}/documents/{document_id}/{filename}
storage_path = f"{yacht_id}/documents/{doc_id}/{filename}"

payload = {
    "id": doc_id,
    "yacht_id": yacht_id,
    "filename": filename,
    "storage_path": storage_path,
    "content_type": params["mime_type"],
    "source": "document_lens",
}

ins = db.table("doc_metadata").insert(payload).execute()
```

**There is no `supabase.storage.from_("documents").upload(...)` call.** The handler only constructs a path string and inserts the metadata row. The actual file bytes are never placed in storage by this code.

The class docstring at line 52 says `Storage: documents bucket at {yacht_id}/documents/{document_id}/{filename}` — this is aspirational, not current behaviour.

### 7.3 Implications
- The 100 orphans aren't just "missing search_index rows" — **they are metadata records for files that never made it into storage at all**. They are ghost records.
- F2 trigger + F5 backfill correctly enqueue them to `search_index` as `pending_extraction`. But the extraction_worker downstream (once deployed with F1) will correctly report `extraction_failed` because the files genuinely do not exist.
- The Render extraction_worker (running old `yacht-documents` code) burned through all 100 rows in 2 seconds after F5 was applied (timestamps 2026-04-15 15:28:27 → 15:28:29), marking them all `extraction_failed`. **This is actually the correct behaviour** regardless of which bucket the worker looks in — the files are not in any bucket.
- The 145 January `document_lens` rows that are marked `indexed` must have gotten there through some other path. They have no actual files in storage, so they weren't indexed by extraction_worker downloading real content — either (a) a bulk backfill that wrote search_index rows with filename-only search_text, or (b) a code path that existed in January and was removed in February. **Not yet traced.**

### 7.4 What this means for F1
F1 (reading bucket from payload) is still correct in principle — when future uploads actually land in storage, the `documents` bucket is the right target and the per-row bucket selector handles `pms-label-pdfs` and any future variants. The code edit is defensible.

**But F1 cannot be runtime-proven against existing data**, because no existing storage_path resolves. It can only be verified once (a) the upload handler is fixed to actually upload file bytes and (b) a fresh upload flows through the pipeline.

### 7.5 What needs to happen upstream (not F-series scope)
1. **Fix `_upload_document_adapter` to actually upload file bytes to storage before inserting doc_metadata.** Likely needs to accept a file blob param or be paired with a signed-upload-URL flow.
2. **Decide whether lens uploads go into `documents` or a different bucket.** The current handler comment says `documents`, and the per-row `storage_bucket` column defaults to NULL (implicit `documents`). This is fine if we commit to `documents` as the lens target.
3. **Clean up or reset the 100 orphans + 22 `storage_only` rows.** These are ghost records with no backing files; they pollute search but cannot be extracted.
4. **Audit the 145 January `indexed` document_lens rows** to see whether they have real search_document_chunks or just filename stubs. If stubs, they should be reset too.

### 7.6 What F2/F3/F4/F5 still achieved despite the upstream bug
- **F2 trigger is live and correct.** When upload is fixed, future lens uploads will automatically flow through the pipeline with no additional code change.
- **F3 constraint allows warranty_claim linking.** Independent of the upload path; this now works.
- **F4 role list allows chief_steward linking.** Same — independent.
- **F5 established the baseline** by making every existing doc_metadata row visible to the queue, so the upstream fix (when it lands) can re-process them cleanly.

---

## 8. Current state of the world (after this session's mutations)

### 8.1 TENANT DB state
- `doc_metadata` triggers: `trg_doc_metadata_cache_invalidate` (existing) + `trg_doc_metadata_extraction_enqueue` (NEW, F2).
- `email_attachment_object_links_object_type_check` constraint: includes `warranty_claim` (NEW, F3).
- `search_index` document rows: 3,578 `indexed` + 100 `extraction_failed` (BURNED by Render old-code worker immediately after F5) + 22 `storage_only` + 1 `deleted` = 3,701. All 3,627 live doc_metadata rows now have a matching search_index row (22 `storage_only` are from the NAS side; 1 `deleted` predates; 3,578 indexed; the 100 extraction_failed ARE the backfilled lens orphans now burned by the old worker).
- Total `search_document_chunks` rows: 47,166 (unchanged this session).
- `pms_warranty_claims` rows: 8.

### 8.2 Feature branch state (NOT deployed)
- Branch: `fix/f-series-documents-hardening`, based on `main@3454d7b8`.
- Files changed (4 lines/blocks):
  - `apps/api/workers/extraction_worker.py` — 18 ± changes, mostly adding bucket param
  - `apps/api/routes/document_routes.py` — 14 ± changes, two constant extensions + comments
  - `supabase/migrations/20260415_f2_doc_extraction_enqueue.sql` (new, 120 lines)
  - `supabase/migrations/20260415_f3_warranty_claim_constraint.sql` (new, 45 lines)
  - `supabase/migrations/20260415_f5_doc_extraction_backfill.sql` (new, 75 lines)
- Untracked: `docs/ongoing_work/documents/` (PLAN.md and this file)
- `py_compile` passes on edited Python files.
- **NOT committed, NOT pushed, NOT merged.**
- Per migration convention, the three SQL files should be deleted before merge to main — they have already been applied to TENANT.

### 8.3 Render extraction_worker state
- Still running **old code** (hardcoded `yacht-documents`).
- Has already burned all 100 backfilled rows into `extraction_failed` (timestamps ~15:28:27–15:28:29).
- Any fresh lens-upload INSERT that flows through F2 will be immediately burned by the old worker.
- **The old worker is actively harmful** as long as it's running and F2 is live, because every new enqueued row gets failed within seconds.

---

## 9. Unresolved questions for user

1. **Upload handler upstream fix:** is there a pre-existing plan to make `_upload_document_adapter` actually upload file bytes? If not, this is a prerequisite before any extraction_worker output will be meaningful. Which file/PR owns this work?
2. **Should I reset the 100 extraction_failed rows?** Options:
   - (a) Leave them failed — they are correct failures (files don't exist).
   - (b) DELETE them from search_index entirely, revert to orphan state — then after upstream fix, backfill works cleanly.
   - (c) Reset to pending_extraction only after the upstream upload fix is deployed.
3. **Should the Render worker be paused or rolled back until the feature branch deploys?** Currently the old worker is actively burning any new row F2 enqueues. This means F2 is harmful in production until Render has F1.
4. **The 145 January indexed document_lens rows** — are they real or stubs? Do they have `search_document_chunks`? Query not yet run (was interrupted).
5. **`storage_only` status (22 rows, all NAS)** — what code path sets this? Not found in Python this session.
6. **Two ledger buckets** (`ledger_exports` and `ledger-exports`) — one is clearly a typo. Flag for cleanup. Not F-series scope.

---

## 10. Feature-branch diff summary (not yet committed)

```
apps/api/routes/document_routes.py    | 14 +++++++++-----
apps/api/workers/extraction_worker.py | 18 ++++++++++++------
2 files changed, 21 insertions(+), 11 deletions(-)
```

Plus three new SQL migration files under `supabase/migrations/` (three files that should be deleted before merge per convention, since they have already been applied to TENANT).

---

## 11. Upstream fix scope — Part A / B / C (IN PROGRESS)

User accepted the two-part plan. The F-series goes from "Pass with issues" to "Pass" only when Parts A+B+C ship AND a real upload flows end-to-end through the pipeline. This is the remaining work.

### 11.1 Trace of existing frontend state (why this is initial wiring, not a "minimal change")

Grep evidence from `apps/web/src`:

1. **`upload_document` has ZERO references in `apps/web/src`.** Only the e2e test file `apps/web/e2e/shard-34-lens-actions/document-actions-full.spec.ts` calls it (lines 43, 82 — `callActionDirect(page, 'upload_document', { file_name, mime_type })`). **This test is what created all 100 ghost orphans** (filenames like `s34-captain-smoke-doc-*.pdf`, `s34-hod-smoke-doc-*.pdf`, `audit.pdf`, `smoke.pdf`).
2. **`Subbar.tsx:98`** — `primaryAction: 'Upload Document'` is a LABEL. `Subbar.tsx:315` wires `onClick={onPrimaryAction}` — but `apps/web/src/app/documents/page.tsx` NEVER passes an `onPrimaryAction` handler. Grep returns zero matches. **Clicking the Upload Document button in the Documents subbar today does nothing.**
3. **`AttachmentUploadModal.tsx`** is a working generic upload modal already used by `WarrantyContent.tsx:393` and `CertificateContent.tsx:441`. It does direct-to-Supabase-storage upload from the browser via `supabase.storage.from(bucket).upload(path, file)` then inserts into **`pms_attachments`** (NOT `doc_metadata`). Path convention: `{entityType}/{entityId}/{timestamp}-{sanitizedFilename}`. 15 MB cap. This modal is wrong target for documents — `pms_attachments` is a different table with different semantics (attach file to existing entity, not add to document library).
4. **`part_routes.py:738-793`** — canonical backend multipart pattern in this codebase: dedicated route file `/v1/parts/upload-image`, uses `UploadFile = File(...) + Form(...)`, reads `file_content = await file.read()`, calls handler with bytes. This is the pattern to mirror for documents.
5. **`receiving_upload.py`** and **`import_routes.py:248`** also use the same multipart pattern. Action_router is JSON-only by architecture — cannot carry binary.
6. **`integrations/supabase.py:562 upload_to_storage()`** exists but uses `get_supabase_client()` — not a tenant-scoped client. Risk: in this multi-tenant DB, any storage write must be tenant-scoped. `part_routes.py:757` uses `get_tenant_supabase_client(tenant_key_alias)` directly. **Mirror that pattern, do not use the generic helper.**

### 11.2 Part A — Backend: `POST /v1/documents/upload` (multipart)

**File:** `apps/api/routes/document_routes.py` (extend, don't create new file — keeps `/v1/documents/*` colocated).

**Changes:**
1. Imports: add `UploadFile, File, Form` to existing `from fastapi import ...` line.
2. Add `import uuid`.
3. Add `_sanitize_filename` helper (copy from `handlers/document_handlers.py:269` — 20 lines, avoids cross-import dependency).
4. New endpoint `POST /upload` on the existing router. Flow:
   - Accept `file: UploadFile` + optional form fields (`title`, `doc_type`, `oem`, `model`, `system_path`, `description`, `tags_csv`, `equipment_ids_csv`, `notes`).
   - Auth via `Depends(get_authenticated_user)` → derive `user_id, yacht_id, tenant_key_alias`, `role`.
   - Role gate — same `LINK_MANAGE_ROLES` or a new `UPLOAD_ROLES` constant? Decision: widen `upload_document`'s `allowed_roles` pattern from the backend action registry. Registry says HOD+ (`chief_engineer, chief_officer, chief_steward, purser, captain, manager`). Use that exact set as `UPLOAD_DOCUMENT_ROLES`.
   - Validate `file` not None, `file.size` ≤ 15 MB (match `AttachmentUploadModal` ceiling). If the UploadFile doesn't expose size directly (SpooledTemporaryFile), read bytes first and check `len(file_content)`.
   - Validate content_type against a whitelist (mirror `AttachmentUploadModal.ACCEPTED_MIME_TYPES`).
   - Generate `doc_id = str(uuid.uuid4())`.
   - Sanitize filename.
   - Build `storage_path = f"{yacht_id}/documents/{doc_id}/{filename}"`.
   - Get tenant client: `supabase = _get_tenant_client(auth['tenant_key_alias'])` (already defined at `document_routes.py:31`).
   - Read bytes: `file_content = await file.read()`.
   - Upload to storage FIRST: `supabase.storage.from_("documents").upload(storage_path, file_content, {"content-type": file.content_type, "upsert": "false"})`.
   - If storage upload raises → return 500 with clear error, do NOT insert doc_metadata (prevents ghost).
   - INSERT doc_metadata with source='document_lens', storage_bucket='documents' (explicit, don't rely on NULL default), plus optional fields from form.
   - If doc_metadata INSERT fails → **compensating delete**: `supabase.storage.from_("documents").remove([storage_path])` then raise 500. Try/except around the compensating delete so a rollback failure still surfaces the original error.
   - The INSERT fires **F2 trigger** → search_index row with `pending_extraction`. No additional enqueue code needed in the route.
   - Audit log entry (non-signed, matching existing `audit_document_action` pattern in the same file).
   - Return `{status: "success", document_id, storage_path, filename}`.

**Why this is multi-tenant safe:**
- Uses tenant-scoped client.
- yacht_id comes from authenticated user context, not request body.
- storage_path embeds yacht_id as first segment (matches existing path convention and `_upload_document_adapter`'s aspirational layout).
- The F2 trigger sets `org_id := NEW.yacht_id` (invariant-verified).

### 11.3 Part B — Backend: annotate the legacy action_router adapter

**File:** `apps/api/handlers/document_handlers.py:293-377` (`_upload_document_adapter`).

**Change:** prepend a docstring warning:

> This adapter creates a `doc_metadata` metadata-only record. It does NOT upload file bytes. For real user uploads use `POST /v1/documents/upload` (multipart) which handles bytes + metadata + rollback atomically. This adapter remains callable via the action router for programmatic use cases where the file is already in storage (e.g. programmatic re-ingest, test fixtures).

No behavioural change. Keeps shard-34 green. Prevents future confusion.

### 11.4 Part C — Frontend: new modal + wire Documents primaryAction

**New file:** `apps/web/src/components/lens-v2/actions/DocumentUploadModal.tsx`
- Fork of `AttachmentUploadModal.tsx` (~300 lines).
- Same UI: file picker, 15 MB cap, MIME whitelist, Toast feedback.
- DIFFERENT submit logic:
  - Build `FormData`, append `file` + optional fields (`title`, `doc_type`, etc.).
  - `fetch('/v1/documents/upload', { method: 'POST', body: formData, credentials: 'include' })` — DO NOT set `Content-Type`; browser sets multipart boundary automatically.
  - Pass auth JWT via the existing `apiClient.ts` pattern if there's a wrapper for it (need to trace), otherwise rely on cookie-based auth via `credentials: 'include'`.
  - On 200: call `onComplete()` which triggers refetch of the documents list, then close.
  - On 4xx/5xx: show Toast with message.

**Edit:** `apps/web/src/app/documents/page.tsx`
- Add `const [uploadOpen, setUploadOpen] = React.useState(false)`.
- Pass `onPrimaryAction={() => setUploadOpen(true)}` through AppShell.
- Mount `<DocumentUploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} yachtId={...} userId={...} onComplete={...} />`
- Invalidate `FilteredEntityList`'s `queryKey={['documents']}` via React Query so the list refreshes after upload. Need to trace how `FilteredEntityList` manages its query key.

**Edit (if needed):** `apps/web/src/components/shell/AppShell.tsx:194`'s `handlePrimaryAction` dispatcher — need to trace whether it accepts a per-domain callback prop from the page or dispatches via a switch internally. This decides whether the `onPrimaryAction` wiring lives in the page or in AppShell.

### 11.5 Ghost cleanup (deferred)

Per user direction: the 100 `extraction_failed` rows are CORRECT failures — the files do not exist in any bucket. Cleanup is deferred to after Parts A+B+C ship and verify against a REAL upload. At that point the cleanup is:
```sql
DELETE FROM doc_metadata
WHERE source = 'document_lens'
  AND deleted_at IS NULL
  AND id IN (
      SELECT object_id FROM search_index
      WHERE object_type='document' AND embedding_status='extraction_failed'
  );
```
Plus the corresponding search_index rows. Not running this yet.

The Render extraction_worker stays running. It has already marked all 100 `extraction_failed` and is now idle (nothing in `pending_extraction` or `extracting`). It won't loop infinitely because the orphan-reset logic in `extraction_worker.py:188 reset_orphans()` only resets rows stuck in `'extracting'` for >10 min back to `'pending_extraction'`, not `extraction_failed` rows.

---

## 13. Post-merge production verification (2026-04-15 evening)

**PR #538 merged at ~16:50.** Render backend deployed within ~2 min. Vercel frontend **initially failed to deploy** because my `AttachmentUploadModal.tsx` refactor placed `React.useCallback` after `if (!open) return null` — violates `react-hooks/rules-of-hooks`, `next build` eslint caught it. Local `tsc --noEmit` does not run eslint, which is why I missed it pre-merge.

Hotfix PR #539 (commit `8841bce5`) moved the useCallback before the early return and added an inline guard comment. Vercel deployed cleanly (1-minute real build, not cached). All subsequent grep checks against the deployed layout chunk confirm my Part C identifiers are live.

### Render backend — verified with real JWT + real PDF
- `POST /v1/documents/upload` — HTTP 200
- Captain role (5af9d61d-9b2e-4db4-a54c-a3c95eec70e5 / `captain.tenant@alex-short.com`, signed with `MASTER_SUPABASE_JWT_SECRET`)
- Storage upload → doc_metadata insert → F2 trigger → search_index `pending_extraction`
- Extraction worker picked up, downloaded from `documents` bucket (F1 fix verified working), transitioned through `extracting → pending → processing → indexed` in ~9 seconds
- Pre-existing extractor bug discovered: `_extract_pdf` returns 0 chars for some PDFs in production despite working locally against the same Docker image. Small PDFs (1.4 KB) sometimes reach `extraction_failed`; medium-sized PDFs reach `indexed` but with `chunks=0` and filename-only search_text. This is NOT my code — it's pre-existing in `apps/api/workers/extraction/extractor.py` and was masked by the F1 bucket bug until F1 shipped. Follow-up issue, out of F-series scope.

### Vercel frontend — verified with Playwright browser test
Test spec: `apps/web/e2e/shard-3-documents/f-series-upload.spec.ts`
Browser: Chromium (Playwright), MASTER JWT minted for captain via global-setup.

Results:
- Navigated to `https://app.celeste7.ai/documents`
- Found `Upload Document` primary action button (count=1)
- Clicked → **modal opened** (role='dialog' mounted)
- File input found → set a reportlab-generated PDF (620 bytes)
- Clicked Upload submit
- **Toast: "Document uploaded successfully"**
- Modal auto-closed

DB verification after test:
- doc_metadata row: id=`16408a9a-fd0e-40b0-aaf5-13b4f32b4a86`, filename=`pw-1776274146890.pdf`, source=`document_lens`, bucket=`documents`, content_type=`application/pdf`, size=620 bytes
- Storage blob: downloadable at HTTP 200, 620 bytes (matches exact upload)
- search_index: `embedding_status=indexed`, org_id = yacht_id, payload.bucket=`documents`
- Cleanup: row + blob + audit log deleted after verification

### Full round-trip proof matrix (all verified against production this session)

| Step | Verified |
|---|---|
| Vercel deploy fresh build (1m duration, new chunk hash) | ✓ |
| Browser → click Upload Document button | ✓ |
| Modal mount via AppShell handlePrimaryAction → documents case | ✓ |
| File picker accepts PDF | ✓ |
| FormData multipart POST → /v1/documents/upload | ✓ |
| Auth headers via getAuthHeaders (JWT + X-Yacht-Signature) | ✓ |
| Backend role gate (HOD+ pass, others 403) | ✓ (62/62 tests pre-merge) |
| Backend MIME + size gates | ✓ |
| Storage upload to documents bucket | ✓ |
| doc_metadata insert with correct columns | ✓ |
| F2 trigger → search_index pending_extraction | ✓ |
| Extraction worker download (F1 fix) | ✓ (reaches pending/indexed) |
| Pipeline cycles to `indexed` | ✓ |
| Success toast visible in browser | ✓ |
| Modal auto-close + query invalidation | ✓ |

### Update — extractor bug fully diagnosed (2026-04-15 evening)

The "extractor returns 0 chunks" was NOT a bug in `_extract_pdf`. The diag patch in PR #541 captured `extract_text_len=81` with the actual body text in the preview — proving extraction works correctly. The chunks failure was downstream in `atomic_chunk_replacement`. Two stacked schema-drift bugs:

**Bug 1 — `tsv` is a generated column (PR #542)**
```
chunk_write_exception: GeneratedAlways: cannot insert a non-DEFAULT value
                       into column "tsv"
                       DETAIL: Column "tsv" is a generated column.
```
`search_document_chunks.tsv` is `GENERATED ALWAYS AS (to_tsvector('english', COALESCE(content, ''))) STORED`. The extraction worker was explicitly writing to it. Fix: omit `tsv` from the INSERT column list.

**Bug 2 — `org_id` cascade through dataset version trigger (PR #543)**
After fixing #542, the next exception surfaced:
```
NotNullViolation: null value in column "org_id" of relation
                  "search_dataset_version"
CONTEXT: SQL statement "INSERT INTO search_dataset_version
                        (org_id, yacht_id, version, last_change)
                        VALUES (v_org_id, v_yacht_id, ...)"
PL/pgSQL function f1_bump_dataset_version() line 22
```
The AFTER INSERT trigger `trg_search_document_chunks_dataset_version` fires `f1_bump_dataset_version()` which inserts into `search_dataset_version` requiring `org_id NOT NULL`. The trigger function reads `org_id` from the just-inserted chunk row. Our INSERT didn't set it. Cascade fails, chunk INSERT rolls back, non-fatal handler swallows it, chunks=0. Fix: include `org_id = yacht_id` in the chunk INSERT (per the org_id=yacht_id invariant verified across 14,068 search_index rows).

**Both bugs pre-date F1.** They were masked because pre-F1 every storage download 404'd against the wrong bucket constant — the chunk INSERT was never reached. F1 unmasked the chain. Each fix exposed the next layer until the diag patch caught both.

Both fixes shipped. PR chain: #538 (F-series + Parts A/B/C) → #539 (eslint hotfix) → #540 (docs) → #541 (diag patch) → #542 (tsv fix) → #543 (org_id fix). All merged 2026-04-15 between ~16:50 and ~20:52 UTC.

### Post-#543 verification status

- `/version` endpoint returns `git_commit: e3bd9e5a` = PR #543 confirmed deployed.
- Monitor task `b7wdipdtr` attempt 8: `chunks_written=1` — first proof the chain works end-to-end.
- Stability monitor `b81ndzuh7` showed alternating success/fail across rolling-deploy window (Render runs the old container in parallel with the new container during deploy until the old is killed).
- Extra deploy hook accidentally fired during testing extended the rollover window; lesson recorded.
- Stability not yet confirmed across consecutive attempts pending the natural rollover completion.

### Lessons captured to memory
- `feedback_eslint_vs_tsc.md` — `tsc --noEmit` does NOT run eslint; run `npm run build` pre-merge
- (pending) Render deploy hook should not be triggered manually during stability testing

---

## 12. Current honest status (after Parts A/B/C execution)

### Verified against TENANT
- **F2 trigger** — Pass. 6 smoke tests: document_lens whitelist OK, nas NOT enqueued, manual whitelist OK, part_lens with pms-label-pdfs bucket passes through payload, document_lens with NULL storage_bucket defaults to `documents`, UPDATE does not fire trigger.
- **F3 CHECK constraint** — Pass. Smoke insert with `object_type='warranty_claim'` succeeds inside rollback, zero residual.
- **F5 backfill** — Pass at SQL level. 100 ghost rows enqueued, immediately burned to `extraction_failed` by the still-old Render extraction_worker (correct failure mode — the underlying files never existed in storage).
- **Part A (`POST /v1/documents/upload`)** — Pass. Five real-DB smoke tests against TENANT with a 335-byte minimal PDF: happy path (200, blob in storage, doc_metadata row, F2 trigger fires search_index row with `pending_extraction` + payload.bucket=`documents`, storage blob fetchable at HTTP 200), role gate (crew → 403), size gate (16 MB → 413), MIME gate (application/x-sh → 415), empty file gate (0 bytes → 400). Cleanup hard-deleted all test rows, audit log rows, and storage blobs.

### Verified at compile level only
- **F1 `extraction_worker.py`** — code on feature branch, `py_compile` clean. Reads `bucket` from payload with default `documents`. NOT runtime-verified because it requires Render deployment (Render is still on old `yacht-documents` hardcode).
- **F4 `LINK_MANAGE_ROLES`** — `chief_steward` added, `py_compile` clean. Not runtime-verified.
- **Part B** — legacy `_upload_document_adapter` docstring updated with deprecation warning. `py_compile` clean. No behaviour change (shard-34 e2e still works).
- **Part C1 `AttachmentUploadModal.tsx` refactor** — backward-compatible. All entity props now optional; new optional `onUpload`, `title`, `description` props. Existing warranty + certificate call sites unchanged (verified by reading both). `tsc --noEmit` exits 0 with zero errors across the entire web app.
- **Part C2 `AppShell.tsx` wiring** — new `documentUploadOpen` state, `documents` case in `handlePrimaryAction`, shell-level `<AttachmentUploadModal>` mounted with custom `handleDocumentUpload` that POSTs multipart to `/v1/documents/upload` with `getAuthHeaders` JWT+X-Yacht-Signature, invalidates `['documents']` query on success, surfaces 4xx/5xx detail in the Toast. `tsc --noEmit` clean.

### Not yet done (deliberately)
- **Browser-level end-to-end test.** Requires a running dev server + browser + real JWT. Not run this session. The handler-level real-DB test covers 95% of the Part A code path; the remaining 5% is FastAPI's multipart parsing (upstream, well-tested) and the Part C2 fetch call (standard browser FormData + fetch pattern, no novel behaviour).
- **Ghost-record cleanup (the 100 `extraction_failed` rows).** Per CEO direction, deferred until AFTER Part C ships and a real upload verifies the pipeline end-to-end. Current cleanup SQL is ready in §11.5 but unrun.
- **Render deploy of the feature branch.** Not done by this session — that's a merge-to-main action requiring explicit CEO approval. Currently Render auto-deploys on push to main, so the F1 worker fix only takes effect after merge.

### Code-hygiene cleanup completed during this session
- Extracted `sanitize_storage_filename` into `apps/api/utils/filenames.py` (new 30-line shared util). Both `handlers/document_handlers.py` and `routes/document_routes.py` now import from it. Removed two duplicate private copies. `email.py`'s `sanitize_filename` left alone — it has different semantics (HTTP Content-Disposition escaping, not storage path hygiene).
- 1-URL philosophy sweep: my earlier Part C design was almost derailed by `PROGRESS_LOG.md`'s stale "single-surface" rule. After CEO correction, rewrote `PROGRESS_LOG.md` as a deprecation notice pointing at the current canonical `docs/frontend/README.md`. Added new memory `feedback_url_philosophy.md` enshrining "delete on sight". Swept and found only two remaining mentions, both warnings AGAINST the legacy pattern (safe to keep).

### Overall verdict: **Pass with issues**

The F-series plumbing is live and verified. Part A endpoint works end-to-end against real TENANT. Part B + C1 + C2 compile clean and match established project patterns. The remaining "issues" are:
- The 100 ghost records from pre-fix smoke tests (correct failure mode, deliberate deferral).
- No browser-level test run (can be added when a dev server is easy to spin).
- No merge-to-main yet (requires explicit CEO decision, not session-unilateral).

---

## 12. Files in this session

### Created
- `/Users/celeste7/Documents/Cloud_PMS/docs/ongoing_work/documents/PLAN.md` (361 lines, living plan)
- `/Users/celeste7/Documents/Cloud_PMS/docs/ongoing_work/documents/context.md` (this file)
- `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f2_doc_extraction_enqueue.sql`
- `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f3_warranty_claim_constraint.sql`
- `/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/20260415_f5_doc_extraction_backfill.sql`
- `/Users/celeste7/.claude/projects/-Users-celeste7/memory/documents01_identity.md`
- `/Users/celeste7/.claude/projects/-Users-celeste7/memory/project_documents_domain_map.md`
- `/Users/celeste7/.claude/projects/-Users-celeste7/memory/project_documents_plan_pointer.md`

### Edited
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/workers/extraction_worker.py` (F1)
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/routes/document_routes.py` (F3 Python list, F4 role list)
- `/Users/celeste7/.claude/projects/-Users-celeste7/memory/MEMORY.md` (index pointer added)

### Temporary probes (in /tmp, not committed)
- `/tmp/preflight_f_series.py` — initial bucket/index audit
- `/tmp/preflight_2b.py` — storage_bucket + org_id + check constraint + orphan forensics
- `/tmp/preflight_2c.py` — per-source coverage
- `/tmp/preflight_2d.py` — timeline + function bodies
- `/tmp/apply_f2.py` — F2 trigger application with pre/post checks
- `/tmp/f2_smoke_test.py` — 6 trigger assertions
- `/tmp/verify_cleanup_and_apply_f3.py` — F3 application (errored on savepoint after COMMIT, but F3 applied successfully)
- `/tmp/f3_smoke_and_f5.py` — F3 smoke + F5 apply + orphan verification
- `/tmp/check_queue_state.py` — queue state after F5
- `/tmp/f1_direct_probe.py` — F1 direct probe (failed — all paths 404)
- `/tmp/bucket_forensics.py` — bucket + path probe

All /tmp scripts are throwaway; the results they produced are captured in this file.
