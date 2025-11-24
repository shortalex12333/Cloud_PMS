# 🌐 **api-spec.md — CelesteOS Cloud API Specification**

**Version:** 1.0
**Owner:** Backend Engineering
**Status:** Approved for MVP

---

# # 📌 **Overview**

CelesteOS uses a **REST API** between:

* Local Agent → Cloud
* Mobile App → Cloud
* Web App → Cloud

This API powers:

* Document ingestion
* Search
* Work order actions
* Handover writing
* Token management
* Predictive logic

All endpoints require:

* `yacht_signature`
* `Authorization: Bearer <token>` (except upload init)
* `Content-Type: application/json` (unless uploading chunks)

---

# # 🔐 **0. Authentication Model**

## **0.1 Required Headers (All Endpoints)**

All CelesteOS backend endpoints require the following headers:

```
Authorization: Bearer <supabase_jwt>
X-Yacht-Signature: <sha256(yacht_id + YACHT_SALT)>
Content-Type: application/json
```

## **0.2 Identity Extraction (Backend Responsibility)**

The backend extracts identity directly from JWT claims:

* `user_id`
* `yacht_id`
* `role`
* `email`
* `expires`

**The frontend MUST NOT send `user_id` or `yacht_id` in the request body.**

## **0.3 Yacht Signature Validation**

* Yacht signature = `sha256(yacht_id + YACHT_SALT)`
* The `yacht_id` used to compute the signature MUST match the `yacht_id` claim in the JWT
* If signature does not match JWT claim → request rejected (403)
* Used to validate yacht identity and route storage to the correct bucket/schema

## **0.4 Request Body Rules**

The request body must **never** contain:

* Raw JWT tokens
* `NEXT_PUBLIC_*` environment variables
* `user_id`
* `yacht_id`
* Any frontend configuration values

Only domain-specific payload fields are allowed in the body.

## **0.5 User Token Details**

Token validity: 24h
Refresh token: 30 days

## **0.6 Device Tokens (Mobile)**

Mobile uploads (photos/notes) use device-scoped token with limited privileges.

---

# # 📥 **1. Ingestion API (NAS → Cloud)**

These endpoints are called **only by the Local Agent**.

## **1.1 `POST /v1/ingest/init`**

Initiates a new upload session.

### **Request**

```json
{
  "filename": "MTU_Cooling_Manual.pdf",
  "sha256": "a1b2c3...",
  "size_bytes": 534553000,
  "source": "nas"
}
```

### **Response**

```json
{
  "upload_id": "uuid",
  "storage_key": "yachts/<yacht_id>/temp/<upload_id>/",
  "expected_chunks": 17
}
```

---

## **1.2 `PATCH /v1/ingest/upload_chunk`**

Uploads a single chunk of a document.

### **Headers**

```
Content-Type: application/octet-stream
X-Yacht-Signature: <signature>
Upload-ID: <upload_uuid>
Chunk-Index: <number>
Chunk-SHA256: <sha>
```

### **Body**

Raw chunk bytes.

### **Response**

```json
{"status": "ok"}
```

---

## **1.3 `POST /v1/ingest/complete`**

After final chunk uploaded, signal the cloud to assemble + verify.

### **Request**

```json
{
  "upload_id": "uuid",
  "total_chunks": 17,
  "sha256": "a1b2c3...",
  "filename": "MTU_Cooling_Manual.pdf"
}
```

### **Response**

```json
{
  "document_id": "uuid",
  "status": "received",
  "queued_for_indexing": true
}
```

Backend triggers indexing-pipeline via internal task queue.

---

# # 🔁 **2. Cron API (Internal Use)**

Used by n8n or cloud scheduler to trigger indexing steps.

## **2.1 `POST /internal/indexer/start`**

Starts the indexing pipeline for a given document.

```json
{
  "document_id": "uuid",
  "yacht_id": "uuid"
}
```

## **2.2 `POST /internal/indexer/retry_failed`**

Retries failed jobs.

---

# # 🔍 **3. Search API**

The universal search bar calls this endpoint.

## **3.1 `POST /v1/search`**

### **Headers (Required)**

```
Authorization: Bearer <supabase_jwt>
X-Yacht-Signature: <sha256(yacht_id + YACHT_SALT)>
Content-Type: application/json
```

### **Request Body (Minimal)**

```json
{
  "query": "fault code 123 on main engine"
}
```

### **Request Body (With Optional Filters)**

```json
{
  "query": "fault code 123 on main engine",
  "mode": "auto",
  "filters": {
    "equipment_id": "uuid",
    "document_type": "manual"
  }
}
```

**Note:** `user_id` and `yacht_id` are extracted from the JWT by the backend. Do NOT include them in the request body.

### **Backend Steps**

1. Validate JWT + yacht signature
2. Extract `user_id`, `yacht_id`, `role` from JWT claims
3. Entity extraction
4. Intent detection
5. Standard RAG retrieval
6. Graph RAG (if needed)
7. Fusion + ranking
8. Generate standardised result cards

### **Response**

```json
{
  "query_id": "uuid",
  "intent": "diagnose_fault",
  "entities": {
    "equipment_id": "uuid",
    "fault_code": "123"
  },
  "results": [
    {
      "type": "document_chunk",
      "document_id": "uuid",
      "chunk_index": 5,
      "score": 0.92,
      "text_preview": "Cooling pressure for CAT3516..."
    },
    {
      "type": "history_event",
      "work_order_id": "uuid",
      "summary": "Replaced temp sensor due to repeated E047 fault",
      "score": 0.87
    }
  ],
  "actions": [
    {
      "label": "Create Work Order",
      "action": "create_work_order",
      "equipment_id": "uuid"
    },
    {
      "label": "Add to Handover",
      "action": "add_to_handover",
      "context": {"fault_code": "123"}
    }
  ]
}
```

---

# # 📝 **4. Notes & Comments API**

## **4.1 `POST /v1/notes/create`**

```json
{
  "text": "Oil leak observed at 14:23",
  "equipment_id": "uuid"
}
```

---

# # ⚙️ **5. Work Order API**

## **5.1 `POST /v1/work-order/create`**

Triggered from search result micro-actions.

```json
{
  "equipment_id": "uuid",
  "title": "Fix stabiliser pump leak",
  "description": "...",
  "priority": "high"
}
```

Response:

```json
{"work_order_id": "uuid"}
```

---

# # 📄 **6. Handover API**

## **6.1 `POST /v1/handover/add-item`**

Adds an item (fault, note, doc) to a handover draft.

### **Request**

```json
{
  "handover_id": "uuid",
  "source_type": "fault",
  "source_id": "uuid",
  "summary": "Main engine E047 overheat behaviour"
}
```

### **Response**

```json
{
  "item_id": "uuid",
  "status": "added"
}
```

---

## **6.2 `POST /v1/handover/create`**

Creates a new handover draft.

```json
{
  "title": "Weekly Handover — Engineering",
  "period_start": "2024-11-01",
  "period_end": "2024-11-07"
}
```

---

## **6.3 `POST /v1/handover/export`**

Exports the final document (PDF/HTML).

```json
{
  "handover_id": "uuid",
  "format": "pdf"
}
```

Response:

```json
{
  "url": "https://celesteos.io/signed/.../handover.pdf"
}
```

---

# # 📧 **7. Email Integration API**

Used for ingesting relevant engineering emails.

## **7.1 `POST /v1/email/ingest`**

```json
{
  "message_id": "123abc",
  "subject": "MTU Coolant Advisory",
  "body": "...",
  "attachments": ["uuid1", "uuid2"]
}
```

Embeddings + indexing triggered automatically.

---

# # 📸 **8. Mobile Upload (Photos/Snapshots)**

## **8.1 `POST /v1/mobile/upload-photo` (multipart)**

Headers:

```
Authorization: Bearer <device_token>
X-Yacht-Signature: <signature>
```

Form-data:

* `photo`
* `note` (optional)
* `equipment_id` (optional)

Response:

```json
{"document_id": "uuid"}
```

---

# # 🔐 **9. User & Token API**

## **9.1 `POST /v1/auth/login`**

```json
{
  "email": "alex@yacht.com",
  "password": "..."
}
```

Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "jwt"
}
```

---

## **9.2 `POST /v1/auth/refresh`**

```json
{"refresh_token": "jwt"}
```

---

## **9.3 `POST /v1/auth/revoke`**

Revokes all tokens for a user.

---

# # 🧪 **10. Health & Diagnostics**

## **10.1 `GET /v1/health`**

Returns:

```json
{
  "status": "ok",
  "uptime": 123456,
  "load": {...}
}
```

---

# # 🎛️ **11. System Cron Hooks**

These endpoints are triggered by n8n or internal schedulers.

### **11.1 Re-index outdated docs**

```
POST /internal/cron/reindex_stale
```

### **11.2 Clean failed uploads**

```
POST /internal/cron/cleanup_uploads
```

### **11.3 Refresh predictive models**

```
POST /internal/cron/predictive_refresh
```

---

# # 🏁 **12. Summary**

This API provides:

* secure ingestion
* full RAG search
* micro-action workflows
* handover creation
* mobile/photo uploads
* token management
* cron automation

It is the backend behind the **one search bar** philosophy.

---
