# Documents Domain — Technical Guide

> How the Documents lens works, end-to-end. For engineers picking up this domain.

---

## 1. What it is

The Documents page (`/documents`) is a vessel-scoped document management system. Crew upload, browse, download, tag, link, and delete files. Every action is audit-logged to `ledger_events` and notified to `pms_notifications`.

**Primary table:** `doc_metadata` (tenant DB `vzsohavtuotocgrfkfyd`)
**Storage:** Supabase Storage bucket `documents`
**Storage path convention:** `{yacht_id}/documents/{document_id}/{sanitized_filename}`

---

## 2. Upload flow (the main path)

```
User clicks "Upload Document" button
  → AppShell.tsx:216 handleDocumentUpload(file, metadata)
    → POST /v1/documents/upload (multipart/form-data)
      → document_routes.py:581 upload_document()
        1. Role gate (HOD+ only) — line 617
        2. MIME type gate (12 accepted types) — line 630
        3. Size gate (15 MB max) — line 656
        4. Build storage path: {yacht_id}/documents/{uuid}/{filename} — line 668
        5. Upload blob to Supabase Storage — line 677
        6. Insert doc_metadata row — line 732
           → F2 trigger fires (trg_doc_metadata_extraction_enqueue)
           → search_index row created: embedding_status='pending_extraction'
        7. Write pms_audit_log — line 783
        8. Write ledger_events — line 790
        9. Write pms_notifications — line 805
        10. Return {success, document_id, storage_path, ...}
    → queryClient.invalidateQueries(['documents'])
    → New document appears in list
```

**If storage upload fails:** No doc_metadata row written (no ghost). 500 returned.
**If doc_metadata insert fails:** Compensating delete of the storage blob. 500 returned. (`document_routes.py:741-754`)

---

## 3. Search extraction pipeline

After a document is uploaded, the extraction pipeline processes it:

```
doc_metadata INSERT
  → F2 trigger: trg_doc_metadata_extraction_enqueue
    → search_index row: embedding_status='pending_extraction', payload={bucket, path}
      → extraction_worker.py claims row (FOR UPDATE SKIP LOCKED)
        → Downloads from Supabase Storage (bucket='documents')
        → Extracts text (PyMuPDF for PDF, raw for text)
        → Writes search_document_chunks (document_id, yacht_id, org_id, chunk_index, content)
        → Flips to embedding_status='pending'
          → projection_worker.py claims row
            → Fetches doc_metadata source row
            → Aggregates chunk keywords (line 807 — doc_metadata-specific path)
            → Upserts search_index (refreshed search_text)
              → embedding_worker_1536 computes vectors (cosine/HNSW 1536-dim)
```

**Key files:**
- Extraction: `apps/api/workers/extraction_worker.py`
- Projection: `apps/api/workers/projection_worker.py:807`
- Embedding: `apps/api/workers/embedding_worker_1536.py`
- Chunk storage: table `search_document_chunks`

---

## 4. Action router handlers

Document CRUD goes through two paths:

### Path A: Direct upload route (frontend uses this)
- `POST /v1/documents/upload` — `apps/api/routes/document_routes.py:581`
- Multipart/form-data with real file bytes
- Writes storage blob + doc_metadata + audit + ledger + notification

### Path B: Action router (for update, tags, delete, comments, links)
- `POST /v1/actions/execute` with `action: "update_document"` etc.
- Dispatch: `apps/api/routes/p0_actions_routes.py:1115` → `_ACTION_HANDLERS`
- Handler: `apps/api/routes/handlers/document_handler.py`
- Inner adapters: `apps/api/handlers/document_handlers.py`

### Handler chain for each action:

| Action | Handler file:line | Ledger? | Notification? | Signature required? |
|--------|-------------------|---------|---------------|---------------------|
| `upload_document` (action router) | `document_handler.py:185-208` | Yes (direct) | Yes | No |
| `update_document` | `document_handler.py:211-250` | Yes (direct) | Yes | No |
| `add_document_tags` | `document_handler.py:280-310` | Yes (direct) | Yes | No |
| `delete_document` | `document_handler.py:252-278` | Yes (direct) | Yes | Yes (PIN) |
| `get_document_url` | `document_handler.py:312-317` | No (read) | No | No |
| `list_documents` | `document_handler.py:319-324` | No (read) | No | No |
| `add_document_comment` | via `ledger_metadata.py:57` safety net | Yes (safety net) | No | No |
| `archive_document` | via `ledger_metadata.py:60` safety net | Yes (safety net) | No | Yes (PIN) |
| `link_document_to_equipment` | `equipment_handlers.py:2020-2090` | Yes (via equipment domain) | No | No |

---

## 5. Role-based access control

### Backend RBAC (enforced at `document_handler.py:55-63`)

```python
_DOC_V2_ALLOWED_ROLES = {
    "upload_document": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "update_document": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "add_document_tags": ["chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "delete_document": ["captain", "manager"],
    "get_document_url": ["crew", "deckhand", "steward", "chef", "bosun", "engineer", "eto",
                         "chief_engineer", "chief_officer", "chief_steward", "purser", "captain", "manager"],
    "list_documents": [same as get_document_url],
}
```

### Frontend RBAC (enforced at `AppShell.tsx:145-148`)

```typescript
const primaryActionDisabled =
    (activeDomain === 'warranties' && !isHOD(user)) ||
    (activeDomain === 'documents' && !isHOD(user));
```

Crew sees a disabled Upload button with tooltip: "Only HOD / Captain can perform this action"

### Multipart upload route RBAC (enforced at `document_routes.py:73-76`)

```python
UPLOAD_DOCUMENT_ROLES = [
    'chief_engineer', 'chief_officer', 'chief_steward',
    'purser', 'captain', 'manager',
]
```

---

## 6. Ledger events

Every mutation writes to `ledger_events` via `build_ledger_event()` at `routes/handlers/ledger_utils.py:11-76`.

Fields written:
- `yacht_id` — vessel scope
- `user_id` — who did it
- `event_type` — create / update / delete
- `entity_type` — always `"document"` for this domain
- `entity_id` — `doc_metadata.id` UUID
- `action` — e.g. `upload_document`, `update_document`
- `user_role` — from JWT context
- `change_summary` — human-readable description
- `proof_hash` — SHA-256 of `{yacht_id, user_id, event_type, entity_type, entity_id, action, timestamp}`

**Known gap:** Signature payloads land in `pms_audit_log.signature` but NOT in `ledger_events.metadata`. Flagged to HMAC01 for receipt-layer integration.

---

## 7. Notifications

Every mutation writes to `pms_notifications` via `_push_doc_notification()` at `document_handler.py:40-65`.

| Action | notification_type | Table |
|--------|-------------------|-------|
| Upload | `document_uploaded` | `pms_notifications` |
| Update | `document_updated` | `pms_notifications` |
| Tags | `document_tags_updated` | `pms_notifications` |
| Delete | `document_deleted` | `pms_notifications` |

Each notification includes: `entity_type='document'`, `entity_id`, `cta_action_id='get_document_url'`, `triggered_by=user_id`.

**Known limitation:** Notifications target the acting user only. Captain doesn't get notified when HOD uploads. Future: fan out to captain/manager UIDs.

---

## 8. Storage security

- **Path construction:** `{yacht_id}/documents/{doc_id}/{filename}` — yacht_id comes from auth context (`resolve_yacht_id()`), never from user input (`document_routes.py:610,668`)
- **Path traversal defence:** `sanitize_storage_filename()` at `utils/filenames.py:17` strips all non-alphanumeric except `.`, `-`, `_`
- **Cross-yacht guard:** `internal_dispatcher.py:342` checks `storage_path.startswith(f"{yacht_id}/")`
- **Signed URLs:** Generated by `DocumentHandlers.get_document_url()` at `document_handlers.py:63-141`. Expire after 3600 seconds (1 hour).
- **Soft delete:** `delete_document` sets `doc_metadata.deleted_at` — does NOT remove the storage blob (preserved for compliance/evidence)

---

## 9. Signed actions (delete + archive)

Delete and archive require a signature popup with 4-digit PIN.

**Frontend flow:**
1. User clicks Delete → `ActionPopup` renders with `signatureLevel === 3`
2. Popup shows: reason textarea + 4-digit PIN boxes
3. On submit: `ActionPopup.tsx:600-606` builds `signature: { method: 'pin', pin: '1234', signed_at: ISO timestamp }`
4. Payload sent as `{ document_id, reason, signature: {...} }`

**Backend validation:**
- `registry.py:1752-1769` defines `variant=ActionVariant.SIGNED` + `required_fields` includes `signature`
- Action router checks `signature` is present in payload — returns 400 if missing

**Note:** PIN is frontend-only validation. No PIN table exists in either database. Backend accepts whatever comes in `signature.pin`. MVP design choice — flagged for security review.

---

## 10. Entity search picker (FieldEntitySearch)

For linking documents to equipment, the modal uses a functional search picker:

**Frontend:** `ActionPopup.tsx:208-340` (`FieldEntitySearch` component)
- Uses `useAuth()` hook for `yacht_id` + `session.access_token`
- Debounced search (250ms) against Render backend: `GET /api/vessel/{yacht_id}/domain/{domain}/records?search={query}&limit=15`
- Renders dropdown of results, click to select sets UUID as field value
- `search_domain` comes from `ActionPopupField.search_domain` (passed via `mapActionFields.ts:107`)

**Backend:** `registry.py:810-815`
- `equipment_id` classified as `REQUIRED` with `lookup_required=True` — triggers `entity-search` field type
- `document_id` classified as `CONTEXT` with `auto_populate_from="document"` — auto-prefilled from open doc

---

## 11. Key database tables

| Table | DB | Purpose |
|-------|-----|---------|
| `doc_metadata` | TENANT | Primary document records (id, filename, storage_path, content_type, tags, deleted_at) |
| `search_index` | TENANT | Unified search index — F2 trigger enqueues on doc_metadata INSERT |
| `search_document_chunks` | TENANT | Extracted text chunks per document (for search + projection) |
| `ledger_events` | TENANT | Audit trail — every mutation writes a row with proof_hash |
| `pms_audit_log` | TENANT | Secondary audit (includes signature JSON for signed actions) |
| `pms_notifications` | TENANT | Notification bell — every mutation writes a row |
| `pms_equipment_documents` | TENANT | Join table for document-to-equipment links |
| `email_attachment_object_links` | TENANT | Join table for document-to-entity links (work_order, fault, etc.) |
| `auth_users_roles` | TENANT | Role lookup — queried by auth middleware for RBAC |
| `user_accounts` | MASTER | User→yacht mapping — queried by auth middleware |
| `fleet_registry` | MASTER | Yacht active status + tenant_key_alias |

---

## 12. Configuration constants

| Constant | Value | File:Line |
|----------|-------|-----------|
| `MAX_UPLOAD_BYTES` | 15 MB | `document_routes.py:79` |
| `ACCEPTED_UPLOAD_MIME_TYPES` | 12 types (PDF, images, Office, text, zip) | `document_routes.py:80-90` |
| `DOCUMENTS_BUCKET` | `"documents"` | `document_routes.py:94` |
| `DEFAULT_STORAGE_BUCKET` | `"documents"` | `extraction_worker.py:38` |
| Signed URL expiry | 3600 seconds | `document_handlers.py:80` |
| List page size | 50 per request | `document_handlers.py:164` |
