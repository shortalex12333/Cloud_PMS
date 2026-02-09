# API Contracts

## Endpoint Specifications for Handover Export

All endpoints enforce:
- Authenticated user (JWT)
- Yacht isolation (yacht_id from context)
- Role-based access where specified
- Immutable audit logging

---

## Authentication

All endpoints require:
```
Authorization: Bearer <jwt_token>
```

Yacht context derived from:
1. JWT `sub` claim → lookup `auth_users_profiles.yacht_id`
2. Validated against request body `yacht_id` if provided

---

## Draft Endpoints

### Create or Fetch Active Draft

```
POST /v1/handover/draft/generate
```

**Purpose:** Trigger draft generation from current handover items.

**Request:**
```json
{
  "period_start": "2026-02-03T00:00:00Z",
  "period_end": "2026-02-03T23:59:59Z",
  "shift_type": "day",
  "department": "engineering",
  "incoming_user_id": "uuid"  // optional
}
```

**Response:**
```json
{
  "status": "success",
  "draft_id": "uuid",
  "state": "DRAFT",
  "total_items": 13,
  "sections_count": 4,
  "created": true  // false if existing draft returned
}
```

**Rules:**
- If DRAFT exists for same period/user → return existing
- If no new entries since last draft → return existing
- If draft in ACCEPTED or SIGNED → reject with 409

---

### Get Draft

```
GET /v1/handover/draft/{draft_id}
```

**Response:**
```json
{
  "id": "uuid",
  "yacht_id": "uuid",
  "period_start": "2026-02-03T00:00:00Z",
  "period_end": "2026-02-03T23:59:59Z",
  "state": "DRAFT",
  "total_entries": 13,
  "critical_count": 2,
  "sections": [
    {
      "id": "uuid",
      "bucket_name": "Engineering",
      "section_order": 1,
      "items": [
        {
          "id": "uuid",
          "summary_text": "Generator 2 cooling issue...",
          "domain_code": "ENG-01",
          "is_critical": true,
          "item_order": 1,
          "source_entry_ids": ["uuid1", "uuid2"],
          "edit_count": 0,
          "entity_link": {
            "type": "fault",
            "id": "uuid",
            "display": "F-2024-0031",
            "url": "/faults/uuid"
          }
        }
      ]
    }
  ],
  "edits": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "edited_by": "John Smith",
      "original_text": "...",
      "edited_text": "...",
      "created_at": "2026-02-03T10:30:00Z"
    }
  ]
}
```

---

### Enter Review State

```
POST /v1/handover/draft/{draft_id}/review
```

**Purpose:** Transition DRAFT → IN_REVIEW

**Request:**
```json
{}  // No body required
```

**Response:**
```json
{
  "status": "success",
  "draft_id": "uuid",
  "state": "IN_REVIEW",
  "message": "Draft now in review mode"
}
```

**Rules:**
- Only allowed if state = DRAFT
- Records reviewer identity

---

### Edit Draft Item

```
PATCH /v1/handover/draft/{draft_id}/item/{item_id}
```

**Request:**
```json
{
  "edited_text": "Updated summary text...",
  "edit_reason": "Clarified terminology"  // optional
}
```

**Response:**
```json
{
  "status": "success",
  "item_id": "uuid",
  "edit_id": "uuid",
  "edit_count": 1
}
```

**Rules:**
- Only allowed in IN_REVIEW
- Creates edit record in `handover_draft_edits`
- Cannot modify source references
- Cannot change classification

---

### Merge Draft Items

```
POST /v1/handover/draft/{draft_id}/merge
```

**Request:**
```json
{
  "item_ids": ["uuid1", "uuid2"],
  "merged_text": "Combined summary covering both items..."
}
```

**Response:**
```json
{
  "status": "success",
  "merged_item_id": "uuid",
  "source_items_archived": ["uuid1", "uuid2"]
}
```

**Rules:**
- Only allowed in IN_REVIEW
- Source references combined
- Original items soft-deleted (retained in history)

---

## Acceptance Endpoints

### Accept Draft (Outgoing Signatory)

```
POST /v1/handover/draft/{draft_id}/accept
```

**Request:**
```json
{
  "confirmation_flag": true,
  "sections_viewed": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:**
```json
{
  "status": "success",
  "draft_id": "uuid",
  "state": "ACCEPTED",
  "accepted_by": {
    "user_id": "uuid",
    "name": "John Smith",
    "role": "Chief Engineer"
  },
  "accepted_at": "2026-02-03T10:30:00Z"
}
```

**Rules:**
- Only allowed in IN_REVIEW
- Requires `confirmation_flag: true`
- All sections must be in `sections_viewed`
- Records `outgoing_user_id` and timestamp

---

### Countersign Draft (Incoming Signatory)

```
POST /v1/handover/draft/{draft_id}/sign
```

**Request:**
```json
{
  "confirmation_flag": true
}
```

**Response:**
```json
{
  "status": "success",
  "draft_id": "uuid",
  "state": "SIGNED",
  "signoff": {
    "outgoing_user": {
      "id": "uuid",
      "name": "John Smith",
      "signed_at": "2026-02-03T10:30:00Z"
    },
    "incoming_user": {
      "id": "uuid",
      "name": "Jane Doe",
      "signed_at": "2026-02-03T10:35:00Z"
    },
    "document_hash": "sha256:abc123..."
  }
}
```

**Rules:**
- Only allowed in ACCEPTED
- Requires `confirmation_flag: true`
- Must be different user from outgoing
- Creates `handover_signoffs` record
- Triggers export preparation

---

## Export Endpoints

### Request Export

```
POST /v1/handover/draft/{draft_id}/export
```

**Request:**
```json
{
  "export_type": "pdf",      // "pdf" | "html" | "email"
  "recipients": [            // Required for email
    "captain@yacht.com",
    "manager@shore.com"
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "export_id": "uuid",
  "export_type": "pdf",
  "storage_path": "85fe1119.../handover/uuid/2026-02-03T10-30-00Z.pdf",
  "document_hash": "sha256:abc123...",
  "download_url": "https://storage.../signed-url",
  "expires_at": "2026-02-04T10:30:00Z"
}
```

**Rules:**
- Only allowed in SIGNED
- Creates `handover_exports` record
- Triggers background rendering
- For email: sends via configured SMTP

---

### Get Export

```
GET /v1/handover/export/{export_id}
```

**Response:**
```json
{
  "id": "uuid",
  "draft_id": "uuid",
  "export_type": "pdf",
  "export_status": "completed",
  "storage_path": "...",
  "file_name": "Handover_2026-02-03_Engineering.pdf",
  "file_size_bytes": 245678,
  "document_hash": "sha256:abc123...",
  "exported_by": {
    "id": "uuid",
    "name": "John Smith"
  },
  "exported_at": "2026-02-03T10:35:00Z",
  "download_url": "https://storage.../signed-url",
  "recipients": []
}
```

---

### Fetch Signed Handover

```
GET /v1/handover/signed/{draft_id}
```

**Response:**
```json
{
  "draft": {
    "id": "uuid",
    "period_start": "...",
    "period_end": "...",
    "state": "SIGNED",
    "total_entries": 13
  },
  "signoffs": {
    "outgoing": {
      "user_id": "uuid",
      "name": "John Smith",
      "role": "Chief Engineer",
      "signed_at": "2026-02-03T10:30:00Z"
    },
    "incoming": {
      "user_id": "uuid",
      "name": "Jane Doe",
      "role": "2nd Engineer",
      "signed_at": "2026-02-03T10:35:00Z"
    },
    "document_hash": "sha256:abc123..."
  },
  "exports": [
    {
      "id": "uuid",
      "export_type": "pdf",
      "created_at": "2026-02-03T10:36:00Z",
      "download_url": "..."
    }
  ]
}
```

---

## Compatibility Bridge Endpoints

### Import from Legacy

```
POST /v1/handover/import-from-legacy
```

**Purpose:** Pull existing `handovers` + `handover_items` into draft workflow.

**Request:**
```json
{
  "handover_id": "uuid",      // Existing handover to import
  "create_draft": true        // Create new draft from items
}
```

**Response:**
```json
{
  "status": "success",
  "imported_items": 13,
  "draft_id": "uuid",
  "sections_created": 4
}
```

**Rules:**
- Reads from `handovers` + `handover_items`
- Creates `handover_drafts` → `handover_draft_sections` → `handover_draft_items`
- Preserves all source references
- Original data unchanged

---

### Import from Quick-Add

```
POST /v1/handover/import-from-quickadd
```

**Purpose:** Pull `pms_handover` items into draft.

**Request:**
```json
{
  "date_from": "2026-02-03",
  "date_to": "2026-02-03",
  "draft_id": "uuid"          // Optional: add to existing draft
}
```

**Response:**
```json
{
  "status": "success",
  "imported_items": 5,
  "draft_id": "uuid"
}
```

---

## Query Endpoints

### List Drafts

```
GET /v1/handover/drafts?state=DRAFT&limit=20
```

**Query Parameters:**
- `state`: Filter by state
- `period_start`: Filter by period
- `limit`: Max results (default 20)
- `offset`: Pagination offset

---

### List History (Signed Handovers)

```
GET /v1/handover/history?limit=50
```

**Response:**
```json
{
  "handovers": [
    {
      "draft_id": "uuid",
      "period_start": "...",
      "period_end": "...",
      "outgoing_user": "John Smith",
      "incoming_user": "Jane Doe",
      "signed_at": "2026-02-03T10:35:00Z",
      "export_count": 2
    }
  ],
  "total": 127
}
```

---

## Error Responses

All errors return structured response:

```json
{
  "status": "error",
  "error_code": "INVALID_STATE_TRANSITION",
  "message": "Cannot accept draft without review",
  "details": {
    "current_state": "DRAFT",
    "attempted_transition": "accept",
    "required_state": "IN_REVIEW"
  }
}
```

**Error Codes:**
- `INVALID_STATE_TRANSITION` (409)
- `DRAFT_NOT_FOUND` (404)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `VALIDATION_ERROR` (400)
- `EXPORT_FAILED` (500)

---
