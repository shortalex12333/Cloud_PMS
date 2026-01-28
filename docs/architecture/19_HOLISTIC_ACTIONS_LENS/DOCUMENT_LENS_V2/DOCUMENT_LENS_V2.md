# Document Lens v2 - Architecture Document

## Overview

Document Lens v2 provides role-gated document management with signature-required delete operations. Backend defines all actions, validation rules, and RLS enforcement.

**Tag:** `document-lens-gold` at commit `583b24a`
**Staging CI:** 17/17 tests passing
**Status:** Production-grade

---

## Actions Summary

| Action | Variant | Allowed Roles | Signature |
|--------|---------|---------------|-----------|
| `upload_document` | MUTATE | HOD roles | No |
| `update_document` | MUTATE | HOD roles | No |
| `add_document_tags` | MUTATE | HOD roles | No |
| `delete_document` | SIGNED | captain, manager | Yes |
| `get_document_url` | READ | All crew | No |
| `list_documents` | READ | All crew | No |

**HOD Roles:** chief_engineer, chief_officer, chief_steward, purser, captain, manager

---

## Action Definitions

### 1. upload_document (MUTATE)

Creates document metadata and returns signed upload URL.

**Request:**
```json
{
  "action": "upload_document",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "file_name": "manual.pdf",
    "mime_type": "application/pdf",
    "title": "Engine Manual",
    "doc_type": "manual"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "{uuid}",
  "storage_path": "{yacht_id}/documents/{doc_id}/{filename}",
  "upload_url": "https://...signed-url...",
  "expires_in": 3600
}
```

**Validation:**
- `file_name` required, sanitized (no path traversal)
- `mime_type` required
- Storage path: `{yacht_id}/documents/{document_id}/{sanitized_filename}`

**Audit:** `signature: {}` (non-signed)

---

### 2. update_document (MUTATE)

Updates document metadata fields.

**Request:**
```json
{
  "action": "update_document",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "document_id": "{uuid}",
    "title": "Updated Title",
    "doc_type": "report"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "{uuid}",
  "updated_fields": ["title", "doc_type"]
}
```

**Validation:**
- Document must exist and belong to yacht
- Cannot update deleted documents

**Audit:** `signature: {}` (non-signed)

**Schema Note:** Handler logs intent to audit without modifying schema-dependent columns. Full update enabled after migration.

---

### 3. add_document_tags (MUTATE)

Adds or replaces tags on a document.

**Request:**
```json
{
  "action": "add_document_tags",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "document_id": "{uuid}",
    "tags": ["engine", "maintenance", "critical"],
    "replace": false
  }
}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "{uuid}",
  "tags": ["engine", "maintenance", "critical"]
}
```

**Validation:**
- Document must exist
- `tags` must be array of strings
- `replace: true` replaces all tags; `false` merges

**Audit:** `signature: {}` (non-signed)

---

### 4. delete_document (SIGNED)

Soft-deletes a document with captain/manager signature.

**Request:**
```json
{
  "action": "delete_document",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "document_id": "{uuid}",
    "reason": "Superseded by updated manual",
    "signature": {
      "signature_type": "delete_document",
      "role_at_signing": "captain",
      "signed_at": "2026-01-28T18:00:00Z",
      "signature_hash": "{hash}"
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "document_id": "{uuid}",
  "deleted_at": "2026-01-28T18:00:00Z",
  "reason": "Superseded by updated manual",
  "is_signed": true
}
```

**Validation:**
- `reason` required
- `signature` required (non-empty JSON object)
- Only captain/manager roles allowed
- Document must exist and not already deleted

**Audit:** `signature: {signature_type, role_at_signing, signed_at, signature_hash}` (signed)

**Schema Note:** Soft-delete (`deleted_at` column) disabled pending migration. Handler logs to audit only.

---

### 5. get_document_url (READ)

Generates signed download URL for a document.

**Request:**
```json
{
  "action": "get_document_url",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "document_id": "{uuid}",
    "expires_in": 3600
  }
}
```

**Response:**
```json
{
  "signed_url": "https://...signed-url...",
  "expires_in": 3600
}
```

**Validation:**
- Document must exist in metadata
- File must exist in storage (returns error if missing)

---

### 6. list_documents (READ)

Lists documents with pagination and filters.

**Request:**
```json
{
  "action": "list_documents",
  "context": { "yacht_id": "{uuid}" },
  "payload": {
    "doc_type": "manual",
    "limit": 50,
    "offset": 0
  }
}
```

**Response:**
```json
{
  "documents": [...],
  "document_types": ["manual", "report", "certificate", ...],
  "pagination": {
    "offset": 0,
    "limit": 50,
    "total_count": 123
  }
}
```

---

## Database Schema

### Table: doc_metadata

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| yacht_id | uuid | FK, RLS enforced |
| filename | text | Sanitized filename |
| storage_path | text | Full storage path |
| content_type | text | MIME type |
| source | text | NOT NULL, e.g. "document_lens" |
| created_at | timestamptz | Auto |

**Pending Migration Columns:**
- `title` (text)
- `doc_type` (text)
- `tags` (text[])
- `system_path` (text)
- `equipment_ids` (uuid[])
- `deleted_at` (timestamptz)
- `deleted_by` (uuid)
- `deleted_reason` (text)

---

## Storage Paths

Format: `{yacht_id}/documents/{document_id}/{sanitized_filename}`

Example: `550e8400-e29b-41d4-a716-446655440000/documents/7c9e6679-7425-40de-944b-e07fc1f90ae7/engine-manual.pdf`

**Rules:**
- No nesting beyond document_id
- Filename sanitized (no path traversal)
- Yacht isolation via path prefix

---

## Role Enforcement

### Mutation Actions (upload, update, tags)
```python
ALLOWED_ROLES = [
    "chief_engineer", "chief_officer", "chief_steward",
    "purser", "captain", "manager"
]
```

### Signed Actions (delete)
```python
ALLOWED_ROLES = ["captain", "manager"]
```

### Read Actions (get_url, list)
```python
ALLOWED_ROLES = [
    "crew", "deckhand", "steward", "chef", "bosun",
    "engineer", "eto", "chief_engineer", "chief_officer",
    "chief_steward", "purser", "captain", "manager"
]
```

---

## Audit Log Invariants

| Action Type | signature Field |
|-------------|-----------------|
| Non-signed (upload, update, tags) | `{}` |
| Signed (delete) | `{signature_type, role_at_signing, signed_at, signature_hash}` |

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/handlers/document_handlers.py` | Handler implementations |
| `apps/api/routes/p0_actions_routes.py` | Route definitions, role gating |
| `tests/ci/staging_documents_acceptance.py` | Staging CI tests |
| `.github/workflows/staging-documents-acceptance.yml` | CI workflow |

---

## Testing

### Staging CI (17 tests)

1. JWT acquisition (crew, HOD, captain)
2. CREW upload denied (403)
3. HOD upload allowed (200)
4. CREW update denied (403)
5. HOD update allowed (200)
6. HOD add tags allowed (200)
7. Invalid doc_id rejected (400/404)
8. HOD delete denied (403)
9. Delete without signature (400)
10. Captain delete with signature (200)
11. Audit: upload signature={}
12. Audit: delete signature=JSON
13. Action list: HOD sees upload_document
14. Action list: CREW no mutations
15-17. CREW get_url role check

---

## Follow-Up Items

| Item | Priority |
|------|----------|
| Migration: add doc_metadata columns | High |
| Re-enable soft-delete flow | High |
| Storage 404 mapping | Medium |
| upload_document alias (create_document) | Low |

---

## Deployment

**Commit:** 583b24a
**Tag:** document-lens-gold
**Workflow:** Staging Documents Acceptance (mark as required)
