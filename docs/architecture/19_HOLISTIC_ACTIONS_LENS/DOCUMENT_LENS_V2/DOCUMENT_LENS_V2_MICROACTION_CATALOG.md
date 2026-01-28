# Document Lens v2 - Microaction Catalog

## Overview

6 document actions organized by variant (READ, MUTATE, SIGNED).

---

## Action Index

| # | Action | Variant | Roles |
|---|--------|---------|-------|
| 1 | upload_document | MUTATE | HOD |
| 2 | update_document | MUTATE | HOD |
| 3 | add_document_tags | MUTATE | HOD |
| 4 | delete_document | SIGNED | captain, manager |
| 5 | get_document_url | READ | All |
| 6 | list_documents | READ | All |

---

## 1. upload_document

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | upload_document |
| **Variant** | MUTATE |
| **Domain** | documents |
| **Trigger** | User initiates document upload |
| **Preconditions** | User has HOD role; yacht_id in context |
| **Required Fields** | file_name, mime_type |
| **Optional Fields** | title, doc_type |
| **Validation Rules** | Filename sanitized; mime_type valid |
| **Side Effects** | Creates doc_metadata row; generates signed upload URL |
| **Audit Entry** | action=upload_document, signature={} |
| **Related Actions** | update_document, add_document_tags, get_document_url |
| **Error Codes** | 400 (validation), 403 (role denied) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -d '{
    "action": "upload_document",
    "context": {"yacht_id": "..."},
    "payload": {
      "file_name": "engine-manual.pdf",
      "mime_type": "application/pdf",
      "title": "Main Engine Manual"
    }
  }'
```

---

## 2. update_document

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | update_document |
| **Variant** | MUTATE |
| **Domain** | documents |
| **Trigger** | User edits document metadata |
| **Preconditions** | Document exists; not deleted; user has HOD role |
| **Required Fields** | document_id |
| **Optional Fields** | title, doc_type, oem, notes |
| **Validation Rules** | Document must exist and belong to yacht |
| **Side Effects** | Logs update intent to audit |
| **Audit Entry** | action=update_document, signature={}, old_values, new_values |
| **Related Actions** | upload_document, add_document_tags |
| **Error Codes** | 400 (validation), 403 (role denied), 404 (not found) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -d '{
    "action": "update_document",
    "context": {"yacht_id": "..."},
    "payload": {
      "document_id": "7c9e6679-...",
      "title": "Updated Engine Manual v2",
      "doc_type": "manual"
    }
  }'
```

---

## 3. add_document_tags

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | add_document_tags |
| **Variant** | MUTATE |
| **Domain** | documents |
| **Trigger** | User adds/modifies document tags |
| **Preconditions** | Document exists; user has HOD role |
| **Required Fields** | document_id, tags |
| **Optional Fields** | replace (boolean, default false) |
| **Validation Rules** | tags must be array of strings |
| **Side Effects** | Updates tags array (merge or replace) |
| **Audit Entry** | action=add_document_tags, signature={} |
| **Related Actions** | update_document, list_documents |
| **Error Codes** | 400 (validation), 403 (role denied), 404 (not found) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -d '{
    "action": "add_document_tags",
    "context": {"yacht_id": "..."},
    "payload": {
      "document_id": "7c9e6679-...",
      "tags": ["engine", "critical", "maintenance"],
      "replace": false
    }
  }'
```

---

## 4. delete_document (SIGNED)

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | delete_document |
| **Variant** | SIGNED |
| **Domain** | documents |
| **Trigger** | Captain/manager initiates document deletion |
| **Preconditions** | Document exists; not already deleted; user is captain/manager |
| **Required Fields** | document_id, reason, signature |
| **Optional Fields** | None |
| **Validation Rules** | signature must be non-empty JSON; reason required |
| **Side Effects** | Logs signed delete to audit (soft-delete pending migration) |
| **Audit Entry** | action=delete_document, signature={signature_type, role_at_signing, signed_at, signature_hash} |
| **Related Actions** | upload_document |
| **Error Codes** | 400 (missing signature/reason), 403 (role denied), 404 (not found) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $CAPTAIN_JWT" \
  -d '{
    "action": "delete_document",
    "context": {"yacht_id": "..."},
    "payload": {
      "document_id": "7c9e6679-...",
      "reason": "Superseded by updated version",
      "signature": {
        "signature_type": "delete_document",
        "role_at_signing": "captain",
        "signed_at": "2026-01-28T18:00:00Z",
        "signature_hash": "abc123..."
      }
    }
  }'
```

---

## 5. get_document_url

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | get_document_url |
| **Variant** | READ |
| **Domain** | documents |
| **Trigger** | User requests document download |
| **Preconditions** | Document exists; file exists in storage |
| **Required Fields** | document_id |
| **Optional Fields** | expires_in (seconds, default 3600) |
| **Validation Rules** | Document must exist in metadata |
| **Side Effects** | None |
| **Audit Entry** | None (read action) |
| **Related Actions** | list_documents, upload_document |
| **Error Codes** | 404 (not found), 500 (storage error if file missing) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -d '{
    "action": "get_document_url",
    "context": {"yacht_id": "..."},
    "payload": {
      "document_id": "7c9e6679-...",
      "expires_in": 3600
    }
  }'
```

---

## 6. list_documents

### Dimensions

| Dimension | Value |
|-----------|-------|
| **Action ID** | list_documents |
| **Variant** | READ |
| **Domain** | documents |
| **Trigger** | User browses document library |
| **Preconditions** | User authenticated with valid yacht_id |
| **Required Fields** | None |
| **Optional Fields** | doc_type, oem, system_path, limit, offset |
| **Validation Rules** | Pagination limits enforced |
| **Side Effects** | None |
| **Audit Entry** | None (read action) |
| **Related Actions** | get_document_url, upload_document |
| **Error Codes** | 403 (role denied) |

### Example

```bash
curl -X POST https://api/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -d '{
    "action": "list_documents",
    "context": {"yacht_id": "..."},
    "payload": {
      "doc_type": "manual",
      "limit": 50,
      "offset": 0
    }
  }'
```

---

## Role Matrix

| Action | crew | deckhand | steward | chef | bosun | engineer | eto | chief_* | purser | captain | manager |
|--------|------|----------|---------|------|-------|----------|-----|---------|--------|---------|---------|
| upload_document | - | - | - | - | - | - | - | Y | Y | Y | Y |
| update_document | - | - | - | - | - | - | - | Y | Y | Y | Y |
| add_document_tags | - | - | - | - | - | - | - | Y | Y | Y | Y |
| delete_document | - | - | - | - | - | - | - | - | - | Y | Y |
| get_document_url | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| list_documents | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |

---

## Document Types

Standard values for `doc_type`:
- `manual` - Equipment/system manuals
- `report` - Inspection/survey reports
- `certificate` - Compliance certificates
- `procedure` - SOPs and procedures
- `drawing` - Technical drawings
- `photo` - Reference photos
- `invoice` - Purchase/service invoices
- `other` - Uncategorized
