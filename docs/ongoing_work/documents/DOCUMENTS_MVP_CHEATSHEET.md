# Documents — Manual Test Log

**Tester:** ___________________  
**Date:** 2026-04-16  
**App URL:** https://app.celeste7.ai  
**Backend:** https://pipeline-core.int.celeste7.ai  
**Render commit:** `72d0f38f` (ledger + notification fix deployed)

Fill in Y / N / ERR for each check. Paste console errors directly into the ERR cells or the notes section at the bottom of each scenario.

---

## Pre-flight

| # | Check | Result | Console / Notes |
|---|-------|--------|-----------------|
| P1 | App loads at `app.celeste7.ai` — no blank screen | | |
| P2 | Log in as **chief_engineer** (`hod.test@alex-short.com` / `Password2!`) — lands on dashboard | | |
| P3 | Sidebar shows **Documents** link | | |
| P4 | Open DevTools → Console tab. No red errors on load | | |

---

## Scenario 1 — Chief Engineer uploads a document (HOD happy path)

**Login:** `hod.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 1.1 | Click **Documents** in sidebar | Sidebar nav | Documents list loads, existing docs visible | | |
| 1.2 | Click **Upload** / **Add Document** button | Top-right area or primary action | Upload modal opens with fields: file picker, title, doc_type, tags | | |
| 1.3 | Select a PDF file (< 15 MB) | File picker in modal | File name appears, no error | | |
| 1.4 | Fill optional fields | Modal fields | Title: "Test Engine Manual"<br>Doc type: "manual"<br>Tags: "engine, test" | | |
| 1.5 | Submit the upload | **Upload** / **Submit** button in modal | Modal closes, new document appears in list | | |
| 1.6 | New doc row visible in list | Documents list | Row shows filename, doc_type, date | | |
| 1.7 | Click the new document row | Document row in list | Detail panel / lens opens with document info | | |
| 1.8 | Download button works | Detail panel — download or view button | Clicking opens/downloads the PDF via signed URL | | |

**Notes / errors for Scenario 1:**
```

```

---

## Scenario 2 — Chief Engineer updates document metadata

**Stay on same document from Scenario 1.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 2.1 | Open the document detail | Click document row | Detail panel open | | |
| 2.2 | Find metadata edit / ⋯ menu | Detail panel or dropdown | "Update" or "Edit" option visible | | |
| 2.3 | Change the title | Edit field or modal | Change to "Test Engine Manual — Updated" | | |
| 2.4 | Save changes | **Save** / **Update** button | Success feedback, title updated in view | | |
| 2.5 | Confirm title changed in list | Back to document list | Row shows new title | | |

**Notes / errors for Scenario 2:**
```

```

---

## Scenario 3 — Chief Engineer adds tags

**Stay on same document.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 3.1 | Open ⋯ menu or tags section | Detail panel | "Add Tags" option or tag input visible | | |
| 3.2 | Add tags | Tag input or modal | Enter: "maintenance", "critical" | | |
| 3.3 | Save tags | **Save** / **Confirm** | Tags appear on document detail | | |
| 3.4 | Verify tags persisted | Refresh page, reopen document | Tags still visible after refresh | | |

**Notes / errors for Scenario 3:**
```

```

---

## Scenario 4 — Captain deletes a document (SIGNED action)

**Switch to:** `captain.tenant@alex-short.com` / `Password2!` (or `x@alex-short.com`)

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 4.1 | Log in as captain | Auth screen | Dashboard loads | | |
| 4.2 | Navigate to Documents | Sidebar | Documents list loads | | |
| 4.3 | Open the test document from Scenario 1 | Document row | Detail panel opens | | |
| 4.4 | Find **Delete** in ⋯ menu or dropdown | Dropdown arrow or ⋯ | "Delete Document" option visible | | |
| 4.5 | Click **Delete Document** | Dropdown menu | **Signature popup opens** — requires reason + name + timestamp | | |
| 4.6 | Popup has required reason field | Popup modal | "Reason" field visible, marked required | | |
| 4.7 | Try to submit without reason | **Confirm** with blank reason | Validation blocks — cannot delete without reason | | |
| 4.8 | Enter reason and sign | Popup fields | Reason: "Test cleanup — verified doc no longer needed" | | |
| 4.9 | Submit deletion | **Confirm** / **Delete** in popup | Document removed from list (soft-deleted) | | |
| 4.10 | Document no longer in list | Documents list | Row gone or marked as deleted | | |

**Notes / errors for Scenario 4:**
```

```

---

## Scenario 5 — Crew can view/download but CANNOT upload/edit/delete

**Login:** `crew.test@alex-short.com` / `Password2!`

| # | Step | Expected | Y / N / ERR | Console errors |
|---|------|----------|-------------|----------------|
| 5.1 | Log in as crew | Dashboard loads, no error | | |
| 5.2 | Navigate to Documents | Documents list loads, existing docs visible | | |
| 5.3 | Open an existing document | Detail panel opens — read-only view | | |
| 5.4 | Download button works | Clicking download opens/downloads the file | | |
| 5.5 | No **Upload** button visible (or greyed out) | Correct — crew cannot upload (HOD+ only) | | |
| 5.6 | No **Delete** option visible | Correct — crew cannot delete (captain/manager only) | | |
| 5.7 | No **Edit** / **Update** option visible | Correct — crew cannot edit metadata | | |
| 5.8 | Try upload via API (optional — needs curl) | Returns 403 Forbidden | | |

**Notes / errors for Scenario 5:**
```
If the upload button IS visible but 403s on click, that is a frontend bug (button should be hidden
for crew role). The backend correctly blocks it — proven in automated wirewalk.
```

---

## Scenario 6 — Link document to entity (work order, equipment, etc.)

**Login:** `hod.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 6.1 | Open any document | Document detail | Detail panel open | | |
| 6.2 | Find "Link to..." / "Related" section | Detail panel or ⋯ menu | Link option visible | | |
| 6.3 | Select entity type | Dropdown | Options include: work_order, equipment, handover, fault, part, receiving, purchase_order, warranty_claim | | |
| 6.4 | Select target entity | Search or list | Pick an existing work order or equipment | | |
| 6.5 | Confirm link | **Link** / **Save** | Link appears in Related section | | |
| 6.6 | Navigate to the linked entity | Click through from Related | The entity's detail shows the document in its attachments | | |

**Notes / errors for Scenario 6:**
```

```

---

## Scenario 7 — Edge cases

**Login:** `hod.test@alex-short.com` / `Password2!`

| # | Step | Expected | Y / N / ERR | Console errors |
|---|------|----------|-------------|----------------|
| 7.1 | Upload a file > 15 MB | Error message: "File exceeds maximum size" (413) | | |
| 7.2 | Upload an unsupported file type (.exe, .pages) | Error message: "Unsupported file type" (415) | | |
| 7.3 | Upload an empty file (0 bytes) | Error message: "Uploaded file is empty" (400) | | |
| 7.4 | Upload a file with special characters in name (`test (1).pdf`, `résumé.pdf`) | File uploads successfully with sanitized filename | | |
| 7.5 | Upload two files with the same name | Both succeed — each gets unique UUID path | | |
| 7.6 | Try to update a deleted document | Error: "Cannot update a deleted document" | | |

**Notes / errors for Scenario 7:**
```

```

---

## Scenario 8 — Signature popup verification

| # | Check | Expected | Y / N / ERR | Console errors |
|---|-------|----------|-------------|----------------|
| 8.1 | Upload document (any HOD) | **No popup** — fires directly | | |
| 8.2 | Update metadata (any HOD) | **No popup** — fires directly | | |
| 8.3 | Add tags (any HOD) | **No popup** — fires directly | | |
| 8.4 | Delete document (captain) | **Popup opens** — reason + signature required | | |
| 8.5 | Archive document (HOD+) | **Popup opens** — signature required | | |
| 8.6 | Add comment (HOD+) | **No popup** — fires directly | | |
| 8.7 | Link to entity (HOD+) | **No popup** — fires directly | | |

**Notes / errors for Scenario 8:**
```

```

---

## DB / Ledger spot check (backend curl — optional but strongly recommended)

Run these after completing Scenarios 1–4. Replace `<DOC_ID>` with the document ID from the URL bar or API response.

```bash
# Acquire captain token
TOKEN=$(curl -s -X POST "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw" \
  -H "Content-Type: application/json" \
  -d '{"email":"captain.tenant@alex-short.com","password":"Password2!"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

DOC_ID="<paste document UUID from URL or response>"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# Check doc_metadata row exists
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT id, filename, storage_bucket, storage_path, source, deleted_at FROM doc_metadata WHERE id='$DOC_ID';"

# Check ledger_events for all document actions on this doc
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT event_type, action, user_role, change_summary, created_at FROM ledger_events WHERE entity_type='document' AND entity_id='$DOC_ID' ORDER BY created_at;"

# Check notifications were pushed
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT notification_type, title, body, created_at FROM pms_notifications WHERE entity_type='document' AND entity_id='$DOC_ID' ORDER BY created_at;"

# Check search_index pipeline status (F2 trigger fired)
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT object_id, embedding_status, payload->>'bucket' AS bucket FROM search_index WHERE object_type='document' AND object_id='$DOC_ID';"

# Check storage blob exists (should return 200 for non-deleted docs)
curl -sI "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/documents/$YACHT_ID/documents/$DOC_ID/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY" \
  | head -3
```

| # | DB check | Expected | Y / N / ERR |
|---|----------|----------|-------------|
| DB1 | `doc_metadata` row exists with correct `storage_bucket='documents'` | Row present | |
| DB2 | `ledger_events` has `upload_document` row (event_type=create) | Row present after Scenario 1 | |
| DB3 | `ledger_events` has `update_document` row (event_type=update) | Row present after Scenario 2 | |
| DB4 | `ledger_events` has `add_document_tags` row (event_type=update) | Row present after Scenario 3 | |
| DB5 | `ledger_events` has `delete_document` row (event_type=delete) | Row present after Scenario 4 | |
| DB6 | `pms_notifications` has rows for upload, update, tags, delete | 4 notification rows | |
| DB7 | `search_index` has row with `embedding_status` in (pending_extraction, pending, embedded) | Row present | |
| DB8 | Storage blob accessible (200 for non-deleted) | HEAD returns 200 | |

---

## Automated wirewalk (run this for quick pass/fail)

```bash
python3 scripts/one-off/documents01_real_pass_wirewalk.py
```

Last verified: 2026-04-16, **30/30 PASS**. Tests: crew denied (403), HOD full CRUD, captain signed delete, crew read-only, ledger_events present for all 4 actions, pms_notifications present for all 4 actions.

---

## Role matrix (quick reference)

| Role | Upload | Update | Tags | Delete | Download | List | Link | Comment |
|------|--------|--------|------|--------|----------|------|------|---------|
| captain | Y | Y | Y | Y (SIGNED) | Y | Y | Y | Y |
| manager | Y | Y | Y | Y (SIGNED) | Y | Y | Y | Y |
| chief_engineer | Y | Y | Y | N | Y | Y | Y | Y |
| chief_officer | Y | Y | Y | N | Y | Y | Y | Y |
| chief_steward | Y | Y | Y | N | Y | Y | Y | Y |
| purser | Y | Y | Y | N | Y | Y | Y | Y |
| crew / deckhand / steward / chef / bosun / engineer / eto | N | N | N | N | Y | Y | N | N |

---

## Limits

| Constraint | Value |
|-----------|-------|
| Max upload size | 15 MB |
| Accepted file types | PDF, JPEG, PNG, HEIC, WebP, TIFF, DOC, DOCX, XLS, XLSX, TXT, ZIP |
| Signed URL expiry | 1 hour (3600s) |
| Max list page size | 50 docs per request |
| Delete requires | captain/manager + signature popup (reason + name) |

---

## HMAC01 notes (receipt-layer integration)

| # | What HMAC01 needs to know |
|---|--------------------------|
| H1 | Ledger `entity_type` = `document`, `entity_id` = `doc_metadata.id` (UUID) |
| H2 | Key actions: `upload_document`, `update_document`, `add_document_tags`, `delete_document`, `add_document_comment`, `archive_document` |
| H3 | `proof_hash` generated by `routes/handlers/ledger_utils.py:64-74` — SHA-256 |
| H4 | Primary table: `doc_metadata` (tenant DB) |
| H5 | Signed actions: `delete_document` + `archive_document` require signature payload |
| H6 | Receipt shape: **single** (one doc = one receipt), **scope** for bulk handover |
| H7 | Adapter should query `doc_metadata` + `search_document_chunks` for extracted text |
| H8 | Storage: bucket `documents`, path `{yacht_id}/documents/{doc_id}/{filename}` — do NOT embed blob in receipt PDF |
| H9 | No raw UUIDs in sealed PDFs — use HMAC refs per CLAUDE.md rule |

---

## Known gaps (honest)

| Gap | Impact | Notes |
|-----|--------|-------|
| Notifications target acting user only | Captain not notified when HOD uploads | Phase 2: fan out to captain/manager UIDs |
| `update_document` doesn't mutate all doc_metadata columns | Audit-only for some fields | PostgREST schema cache issue — `document_handlers.py:422` |
| No document versioning | One copy per doc_id, no revisions | Would need `doc_versions` table |
| No thumbnail/preview | List shows filenames only | Would need image processing worker |
| Comments via action_router only | No REST endpoint | Must use `/v1/actions/execute` |
