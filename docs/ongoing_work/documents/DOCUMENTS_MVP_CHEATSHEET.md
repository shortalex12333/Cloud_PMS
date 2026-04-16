# Documents Domain — MVP Test Cheat Sheet

> Owner: DOCUMENTS01 | Date: 2026-04-16 | PR #562 (ledger+notify fix)
> Wirewalk test: `scripts/one-off/documents01_real_pass_wirewalk.py`

---

## 1. Roles & Permissions Matrix

| Role | Upload | Update Metadata | Add Tags | Delete | Get URL / Download | List | Link to Entity | Comment |
|------|--------|-----------------|----------|--------|---------------------|------|----------------|---------|
| **captain** | Y | Y | Y | Y (SIGNED) | Y | Y | Y | Y |
| **manager** | Y | Y | Y | Y (SIGNED) | Y | Y | Y | Y |
| **chief_engineer** | Y | Y | Y | N | Y | Y | Y | Y |
| **chief_officer** | Y | Y | Y | N | Y | Y | Y | Y |
| **chief_steward** | Y | Y | Y | N | Y | Y | Y | Y |
| **purser** | Y | Y | Y | N | Y | Y | Y | Y |
| **crew** | N | N | N | N | Y | Y | N | N |
| **deckhand** | N | N | N | N | Y | Y | N | N |
| **steward** | N | N | N | N | Y | Y | N | N |
| **chef** | N | N | N | N | Y | Y | N | N |
| **bosun** | N | N | N | N | Y | Y | N | N |
| **engineer** | N | N | N | N | Y | Y | N | N |
| **eto** | N | N | N | N | Y | Y | N | N |

**Source:** `apps/api/routes/handlers/document_handler.py:55-63` (_DOC_V2_ALLOWED_ROLES)
**Source:** `apps/api/routes/document_routes.py:73-76` (UPLOAD_DOCUMENT_ROLES)
**Source:** `apps/api/action_router/registry.py:1752` (delete_document: captain, manager only)

---

## 2. Scenarios — Normal Operations

### S1: HOD uploads a document (chief_engineer, chief_officer, chief_steward, purser, captain, manager)

**Flow:**
1. User clicks Upload button on Documents page
2. `AppShell.tsx:handleDocumentUpload` fires
3. Frontend POSTs multipart to `POST /v1/documents/upload`
4. Backend validates: role gate (403 if crew), MIME type (415), size (413 if >15MB)
5. Storage blob written to `documents` bucket at `{yacht_id}/documents/{doc_id}/{filename}`
6. `doc_metadata` row inserted (source='document_lens')
7. F2 trigger `trg_doc_metadata_extraction_enqueue` fires AFTER INSERT
8. `search_index` row created: `embedding_status='pending_extraction'`, `payload={bucket:'documents', path, ...}`
9. `pms_audit_log` row written
10. `ledger_events` row written (event_type='create', entity_type='document', action='upload_document')
11. `pms_notifications` row written (notification_type='document_uploaded')
12. Response: `{success, document_id, storage_path, storage_bucket, filename, size_bytes, content_type}`

**Files:**
- Frontend: `apps/web/src/components/shell/AppShell.tsx` (handleDocumentUpload callback)
- Frontend modal: `apps/web/src/components/lens-v2/actions/AttachmentUploadModal.tsx`
- Backend route: `apps/api/routes/document_routes.py:581-802`
- F2 trigger: DB trigger `trg_doc_metadata_extraction_enqueue` (ON AFTER INSERT on doc_metadata)
- Extraction: `apps/api/workers/extraction_worker.py`
- Projection: `apps/api/workers/projection_worker.py:807`

**Y/N:** Y — 25/25 wirewalk PASS (live DB verified)

---

### S2: HOD updates document metadata

**Flow:**
1. User edits title/doc_type/notes via Documents detail panel
2. Frontend calls `POST /v1/actions/execute` with `{action: "update_document", payload: {document_id, title, ...}}`
3. `document_handler.py:update_document` → RBAC gate → delegates to `document_handlers.py:_update_document_adapter`
4. Adapter verifies doc exists (404 if not), checks not soft-deleted
5. Writes `pms_audit_log` with old/new values
6. `ledger_events` row written (event_type='update', entity_type='document', action='update_document')
7. `pms_notifications` row written
8. Returns `{status:'success', document_id, updated_fields}`

**Files:**
- Handler dispatch: `apps/api/routes/handlers/document_handler.py:211-250`
- Inner adapter: `apps/api/handlers/document_handlers.py:381-454`
- Ledger metadata: `apps/api/action_router/ledger_metadata.py:63` (safety net)

**Y/N:** Y — wirewalk verified 200 response + pms_audit_log row

---

### S3: HOD adds tags to a document

**Flow:**
1. User adds tags via document detail panel
2. `POST /v1/actions/execute` with `{action: "add_document_tags", payload: {document_id, tags: [...], replace: false}}`
3. `document_handler.py:add_document_tags` → RBAC gate → `document_handlers.py:_add_document_tags_adapter`
4. Current tags fetched, merged (or replaced if `replace=true`), written to `doc_metadata.tags`
5. `ledger_events` row written
6. `pms_notifications` row written

**Files:**
- Handler: `apps/api/routes/handlers/document_handler.py:280-310`
- Inner: `apps/api/handlers/document_handlers.py:457-510`

**Y/N:** Y — wirewalk verified tags=['wirewalk','documents01'] persisted to doc_metadata

---

### S4: Captain/Manager deletes a document (SIGNED action)

**Flow:**
1. User clicks Delete — **signature popup appears** (reason + name + timestamp required)
2. `POST /v1/actions/execute` with `{action: "delete_document", payload: {document_id, reason, signature: {name, timestamp}}}`
3. `document_handler.py:delete_document` → RBAC gate (captain/manager ONLY)
4. Delegates to `document_handlers.py:_delete_document_adapter` → sets `deleted_at` (soft delete), `deleted_by`, `delete_reason`
5. `ledger_events` row written (event_type='delete')
6. `pms_notifications` row written
7. Response includes `_ledger_written: true`

**Signature popup is required because:**
- `action_router/registry.py:1752` defines `variant=ActionVariant.SIGNED`
- Frontend renders a signature pad when `variant=SIGNED`
- The payload must include `signature: {name, timestamp}` or the action router rejects (400)

**Files:**
- Handler: `apps/api/routes/handlers/document_handler.py:252-278`
- Inner: `apps/api/handlers/document_handlers.py` (_delete_document_adapter)
- Registry: `apps/api/action_router/registry.py:1752-1769`

**Y/N:** Y — wirewalk verified: response 200, deleted_at set, ledger row present

---

### S5: Any crew member downloads/views a document

**Flow:**
1. User clicks document row → detail panel → Download button
2. `POST /v1/actions/execute` with `{action: "get_document_url", payload: {document_id}}`
3. `document_handler.py:get_document_url` → RBAC gate (ALL roles including crew/deckhand/etc.)
4. `document_handlers.py:DocumentHandlers.get_document_url` → queries `doc_metadata` → generates signed URL from Supabase Storage
5. Security: `internal_dispatcher.py:342` enforces `storage_path.startswith(f"{yacht_id}/")` — cross-yacht blocked
6. Returns `{signed_url, expires_in: 3600}`

**Files:**
- Handler: `apps/api/routes/handlers/document_handler.py:312-317`
- Inner: `apps/api/handlers/document_handlers.py:63-141`
- Path security: `apps/api/action_router/dispatchers/internal_dispatcher.py:342`

**Y/N:** Y — wirewalk verified for crew role (200 + signed_url returned)

---

### S6: HOD links a document to an entity (work order, equipment, certificate, etc.)

**Flow:**
1. User selects "Link to..." from document actions
2. `POST /v1/documents/link` with `{document_id, object_type, object_id}`
3. `document_routes.py:link_document` → role gate → validates object_type against allowed list
4. Inserts into `email_attachment_object_links` (upserts if duplicate)
5. `pms_audit_log` written

**Allowed object_types:** work_order, equipment, handover, fault, part, receiving, purchase_order, warranty_claim
**Source:** `apps/api/routes/document_routes.py:65` (VALID_OBJECT_TYPES)

**Y/N:** Y — existing functionality, not modified in this PR

---

## 3. Edge Cases & Failure Modes

### E1: Upload file too large (>15 MB)
- **Expected:** 413 Request Entity Too Large
- **Source:** `document_routes.py:79` MAX_UPLOAD_BYTES = 15 * 1024 * 1024
- **Why it would fail:** Frontend may not enforce the same limit; backend is the gate

### E2: Upload unsupported MIME type
- **Expected:** 415 Unsupported Media Type
- **Accepted types:** PDF, JPEG, PNG, HEIC, WebP, TIFF, DOC, DOCX, XLS, XLSX, TXT, ZIP, octet-stream
- **Source:** `document_routes.py:80-90` ACCEPTED_UPLOAD_MIME_TYPES
- **Why it would fail:** Some browsers report different MIME types for the same file (e.g., .pages files)

### E3: Upload empty file (0 bytes)
- **Expected:** 400 "Uploaded file is empty"
- **Source:** `document_routes.py:651-655`

### E4: crew tries to upload
- **Expected:** 403 "Insufficient permissions to upload documents"
- **Source:** `document_routes.py:617-624`
- **Y/N:** Y — wirewalk scenario 1 confirmed

### E5: crew tries to update/delete
- **Expected:** 403
- **Source:** `document_handler.py:_enforce_doc_rbac` at line 275
- **Y/N:** Y — wirewalk scenario 4 confirmed (403 for both)

### E6: Storage upload succeeds but doc_metadata insert fails
- **Expected:** Compensating delete of the storage blob, then 500 to caller
- **Source:** `document_routes.py:736-754`
- No ghost record is left (no doc_metadata row)
- If compensating delete fails → orphan blob logged at WARNING level

### E7: Delete a document that's already deleted
- **Expected:** ValueError "Cannot update a deleted document" → 400
- **Source:** `document_handlers.py:419-420`

### E8: Get URL for non-existent document
- **Expected:** `{status: "success", error: "NOT_FOUND"}` (ResponseBuilder pattern, not HTTP 404)
- **Source:** `document_handlers.py:97-99`

### E9: Concurrent uploads of same filename
- **Expected:** Each gets a unique `doc_id` (UUID v4), so paths never collide
- Path format: `{yacht_id}/documents/{uuid}/{filename}` — UUID is unique per upload
- **Source:** `document_routes.py:665-668`

### E10: Path traversal attempt (filename = `../../etc/passwd`)
- **Expected:** `sanitize_storage_filename` strips path separators
- **Source:** `apps/api/utils/filenames.py`

### E11: Cross-yacht access attempt
- **Expected:** 403 or empty results — `yacht_id` comes from JWT via `resolve_yacht_id()`, never from user input
- RLS also enforces at DB layer

---

## 4. Ledger Events — What Gets Written

| Action | event_type | entity_type | Written By | File:Line |
|--------|-----------|-------------|------------|-----------|
| `upload_document` (multipart route) | create | document | `document_routes.py:790-800` | Direct write |
| `upload_document` (action router) | create | document | `document_handler.py:193-207` | Direct write + `_ledger_written=True` |
| `update_document` | update | document | `document_handler.py:220-234` | Direct write + safety net at `ledger_metadata.py:63` |
| `add_document_tags` | update | document | `document_handler.py:291-305` | Direct write + safety net at `ledger_metadata.py:58` |
| `delete_document` | delete | document | `document_handler.py:261-275` | Direct write + `_ledger_written=True` |
| `add_document_comment` | update | document | Safety net | `ledger_metadata.py:57` |
| `add_document_note` | update | document | Safety net | `ledger_metadata.py:58` |
| `archive_document` | update | document | Safety net | `ledger_metadata.py:60` |

---

## 5. Notification Events

| Action | notification_type | Title | Priority |
|--------|-------------------|-------|----------|
| Upload (multipart) | document_uploaded | Document uploaded | normal |
| Upload (action router) | document_uploaded | Document uploaded | normal |
| Update metadata | document_updated | Document updated | normal |
| Add tags | document_tags_updated | Document tags updated | normal |
| Delete | document_deleted | Document deleted | normal |

**Table:** `pms_notifications` (tenant DB)
**Idempotency:** unique constraint on `(yacht_id, user_id, idempotency_key)`
**CTA:** `cta_action_id='get_document_url'` so clicking the notification opens the document

---

## 6. Extraction / Search Pipeline (Projection-Worker Integration)

**Chain:**
```
doc_metadata INSERT
  → F2 trigger trg_doc_metadata_extraction_enqueue
    → search_index row (embedding_status='pending_extraction', payload={bucket, path})
      → extraction_worker claims row (FOR UPDATE SKIP LOCKED)
        → downloads from Supabase Storage (bucket='documents')
        → extracts text (fitz/PyMuPDF for PDF, raw for text)
        → writes search_document_chunks (document_id, yacht_id, org_id, chunk_index, content)
        → flips to embedding_status='pending'
          → projection_worker claims row
            → fetches doc_metadata source row
            → aggregates chunk keywords (doc_metadata-specific path at line 807)
            → upserts search_index (refreshed search_text)
              → embedding_worker_1536 computes vectors (cosine/HNSW)
```

**Key files:**
- F2 trigger: DB trigger on `doc_metadata` (created by migration, not in codebase files)
- Extraction: `apps/api/workers/extraction_worker.py`
- Chunk write fix: PR #542 (tsv generated column) + PR #543 (org_id NOT NULL)
- Projection: `apps/api/workers/projection_worker.py:807` (doc_metadata-specific branch)
- Embedding: `apps/api/workers/embedding_worker_1536.py`

**Y/N:** Y — wirewalk verified: search_index row present with `embedding_status='pending_extraction'` and `payload.bucket='documents'` immediately after upload

---

## 7. Storage Layout

```
Supabase Storage bucket: "documents"

{yacht_id}/
  documents/
    {document_id}/
      {sanitized_filename}
```

- Bucket name: `documents` (NOT `yacht-documents`)
- Path prefix: `{yacht_id}/` — enforced by code, not user input
- Path security: `internal_dispatcher.py:342` checks `startswith(f"{yacht_id}/")`
- New upload route: `document_routes.py:668` builds path from auth-derived yacht_id

---

## 8. Where Signature Popups Belong

| Action | Variant | Popup? | Why |
|--------|---------|--------|-----|
| `upload_document` | MUTATE | No | Normal data entry |
| `update_document` | MUTATE | No | Metadata edit |
| `add_document_tags` | MUTATE | No | Tag management |
| `delete_document` | **SIGNED** | **Yes** | Destructive, needs accountability trail |
| `archive_document` | **SIGNED** | **Yes** | Reversible but notable |
| `link_document_*` | MUTATE | No | Cross-entity linking |
| `add_document_comment` | MUTATE | No | Free-text annotation |

**Source:** `apps/api/action_router/registry.py` — search for `variant=ActionVariant.SIGNED` in the Documents section

---

## 9. Size Limits & Constraints

| Constraint | Value | Source |
|-----------|-------|--------|
| Max upload size | 15 MB | `document_routes.py:79` |
| Accepted MIME types | 12 types (PDF, images, Office, text, zip) | `document_routes.py:80-90` |
| Filename sanitization | strips path separators, non-printable chars | `utils/filenames.py` |
| Signed URL expiry | 3600 seconds (1 hour) | `document_handlers.py:80` |
| Max list page size | 50 docs per page (default) | `document_handlers.py:164` |
| search_text max length | Configurable via projection_worker CONFIG | `projection_worker.py` |
| Tags array | Postgres text[] — no explicit max, but PostgREST limits apply | doc_metadata.tags |

---

## 10. HMAC01 Notes — For Receipt-Layer Integration

**What HMAC01 needs to know about Documents:**

1. **Ledger entity_type:** `document` (consistently used across all handlers)
2. **entity_id:** `doc_metadata.id` (UUID)
3. **Key ledger actions:** `upload_document`, `update_document`, `add_document_tags`, `delete_document`, `add_document_comment`, `add_document_note`, `archive_document`
4. **proof_hash:** Generated by `build_ledger_event()` at `routes/handlers/ledger_utils.py:64-74` — SHA-256 of `{yacht_id, user_id, event_type, entity_type, entity_id, action, timestamp}`
5. **Primary table:** `doc_metadata` (tenant DB)
6. **Signed actions:** `delete_document` and `archive_document` require signature payload
7. **Receipt shape:** Documents would use **single** shape (one document = one receipt) for individual doc events, and **scope** shape for "all documents" handover export
8. **Adapter contract:** The domain adapter for documents should answer:
   - *What records?* → Query `doc_metadata` by entity_id, join `search_document_chunks` for extracted text
   - *Which ledger events?* → `SELECT * FROM ledger_events WHERE entity_type='document' AND entity_id=$1`
9. **Storage reference:** Bucket `documents`, path `{yacht_id}/documents/{doc_id}/{filename}` — the receipt PDF should reference this path but NOT embed the blob (too large)
10. **No raw UUIDs** in sealed PDFs per CLAUDE.md rule — use HMAC refs

---

## 11. Known Limitations (Honest Gaps)

| Gap | Status | Impact | Notes |
|-----|--------|--------|-------|
| Notifications target acting user only | By design for MVP | Captain doesn't get notified when HOD uploads | Phase 2: query auth_users_roles for captain/manager UIDs and fan out |
| update_document doesn't actually mutate doc_metadata columns | Existing | Audit-only — PostgREST schema cache issues | `document_handlers.py:422-424` explains why |
| /v2/search underscore tokenization | Pre-existing | Compound filenames like `Turbocharger_Inspection_2024.pdf` become single lexeme | Search pipeline issue, not Documents domain |
| No document versioning | Not built | Only one copy per doc_id; updates don't create revisions | Would need a doc_versions table |
| No thumbnail generation | Not built | Documents page shows filenames only, no previews | Would need an image processing worker |
| Comments via action_router only | By design | No REST endpoint for comments — must use /v1/actions/execute | Consistent with other domains |

---

## 12. Quick Test Commands

```bash
# Full automated wirewalk (25 assertions, 4 scenarios)
python3 scripts/one-off/documents01_real_pass_wirewalk.py

# Manual: check ledger_events for a specific document
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT id, event_type, action, user_role, created_at FROM ledger_events WHERE entity_type='document' ORDER BY created_at DESC LIMIT 10;"

# Manual: check pms_notifications
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT notification_type, title, entity_id, created_at FROM pms_notifications WHERE entity_type='document' ORDER BY created_at DESC LIMIT 10;"

# Manual: check search_index pipeline status
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT object_id, embedding_status, payload->>'bucket' AS bucket FROM search_index WHERE object_type='document' ORDER BY updated_at DESC LIMIT 10;"

# Render deploy status
curl -s -H "Authorization: Bearer rnd_gDiifPw9rGRfRRmelxRZzIn0ghmu" \
  "https://api.render.com/v1/services/srv-d727k663jp1c73e9eblg/deploys?limit=1" | python3 -m json.tool

# API version check
curl -s https://pipeline-core.int.celeste7.ai/version
```
