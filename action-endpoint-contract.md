## **action-endpoint-contract.md**

**CelesteOS — Action Endpoint Contract (V1)**
*The canonical API specification for every action that the Action Router can execute.*

---

# ## 1. Purpose

This document defines:

* every supported action
* the backend endpoint it maps to
* the required payload schema
* yacht/role validation requirements
* expected response formats
* n8n workflow mapping where applicable
* error patterns

Search Engine → Frontend → Action Router → Endpoint → n8n/Supabase.

No other part of the system may mutate data.

---

# ## 2. Architecture Overview

All mutating operations flow through:

```
Frontend Button  
    → POST /v1/actions/execute  
        → Action Router  
            → Endpoint Handler  
                → n8n Workflow or Internal Logic  
                    → Supabase  
```

Endpoints below are not called directly by the frontend.
The frontend ONLY calls:

```
POST /v1/actions/execute
```

The Action Router then calls these endpoints.

---

# ## 3. Endpoint Catalogue

Below is the **complete list** of required backend endpoints, grouped by action category.

These MUST be implemented exactly.
No extra fields.
No missing fields.
No variants.

---

# ------------------------------------------

# ## 4. Notes Endpoints

# ------------------------------------------

## **4.1 Create Note**

```
POST /v1/notes/create
```

### Required Payload

```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid",
  "note_text": "string"
}
```

### Behaviour

* Insert into `notes` table
* Link to equipment
* Log action
* Trigger recalculation of predictive signals for that equipment

### Response

```json
{ "note_id": "uuid" }
```

---

# ------------------------------------------

# ## 5. Work Orders Endpoints

# ------------------------------------------

## **5.1 Create Work Order**

```
POST /v1/work-orders/create
```

### Required Payload

```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid",
  "title": "string",
  "description": "string",
  "priority": "low | medium | high | critical"
}
```

### Behaviour

* Insert row into `work_orders`
* Generate WO number
* Link to equipment
* Notify predictive engine

### Response

```json
{ "work_order_id": "uuid" }
```

---

## **5.2 Add Note to Work Order**

```
POST /v1/work-orders/add-note
```

### Payload

```json
{
  "yacht_id": "uuid",
  "work_order_id": "uuid",
  "note_text": "string"
}
```

### Response

```json
{ "note_id": "uuid" }
```

---

## **5.3 Close Work Order**

```
POST /v1/work-orders/close
```

### Payload

```json
{
  "yacht_id": "uuid",
  "work_order_id": "uuid"
}
```

### Response

```json
{ "status": "closed" }
```

---

## **5.4 Work Order History**

```
GET /v1/work-orders/history?work_order_id=<uuid>
```

### Response

```json
{
  "work_order_id": "uuid",
  "history": [...]
}
```

---

# ------------------------------------------

# ## 6. Handover Endpoints

# ------------------------------------------

## **6.1 Add Equipment to Handover**

```
POST /v1/handover/add-item
```

### Payload

```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid",
  "summary_text": "string"
}
```

### Response

```json
{ "handover_item_id": "uuid" }
```

---

## **6.2 Add Document to Handover**

```
POST /v1/handover/add-document
```

Payload:

```json
{
  "yacht_id": "uuid",
  "document_id": "uuid",
  "context": "optional string"
}
```

---

## **6.3 Add Predictive Insight to Handover**

```
POST /v1/handover/add-predictive
```

Payload:

```json
{
  "yacht_id": "uuid",
  "equipment_id": "uuid",
  "insight_id": "uuid",
  "summary": "string"
}
```

---

## **6.4 Edit Handover Section**

```
POST /v1/handover/edit-section
```

Payload:

```json
{
  "yacht_id": "uuid",
  "handover_id": "uuid",
  "section_name": "string",
  "new_text": "string"
}
```

---

## **6.5 Export Handover**

```
POST /v1/handover/export
```

Payload:

```json
{
  "yacht_id": "uuid"
}
```

Response:

```json
{ "download_url": "signed-url" }
```

---

# ------------------------------------------

# ## 7. Document Endpoints

# ------------------------------------------

## **7.1 Open Document**

```
POST /v1/documents/open
```

Payload:

```json
{
  "storage_path": "string"
}
```

Response:

```json
{
  "url": "signed-url"
}
```

---

## **7.2 View Full Manual**

```
GET /v1/documents/full?document_id=<uuid>
```

Response:

```json
{
  "document_id": "uuid",
  "url": "signed-url"
}
```

---

# ------------------------------------------

# ## 8. Fault / Diagnostic Endpoints

# ------------------------------------------

## **8.1 Diagnose Fault**

```
GET /v1/faults/diagnose?code=<string>&equipment_id=<uuid>
```

Response:

```json
{
  "code": "E122",
  "equipment_id": "uuid",
  "likely_causes": [...],
  "related_parts": [...],
  "documents": [...]
}
```

(This endpoint wraps RAG + GraphRAG specialised for faults.)

---

# ------------------------------------------

# ## 9. Inventory Endpoints

# ------------------------------------------

## **9.1 View Stock**

```
GET /v1/inventory/stock?part_id=<uuid>
```

Response:

```json
{
  "part_id": "uuid",
  "current_qty": 4,
  "min_qty": 2
}
```

---

## **9.2 Order Part**

```
POST /v1/inventory/order-part
```

Payload:

```json
{
  "yacht_id": "uuid",
  "part_id": "uuid",
  "qty": 3
}
```

Response:

```json
{
  "purchase_order_id": "uuid"
}
```

---

# ------------------------------------------

# ## 10. Predictive Endpoints (Used by Micro-Actions)

# ------------------------------------------

## **10.1 Add Predictive Insight to Handover**

(Already defined above — included twice intentionally for dependency clarity.)

---

## **10.2 View Predictive State**

```
GET /v1/predictive/state?equipment_id=<uuid>
```

Response:

```json
{
  "risk_score": 0.73,
  "trend": "up",
  "signals": {...}
}
```

---

## **10.3 View Predictive Insight Detail**

```
GET /v1/predictive/insight?id=<uuid>
```

---

# ## 11. Security Contract for All Action Endpoints

Every endpoint must:

1. Validate **Supabase JWT**
2. Load **user from auth.users**
3. Load **user.yacht_id**
4. Ensure `payload.yacht_id == user.yacht_id`
5. Validate role:

   ```
   user.role ∈ action.roles
   ```
6. Validate all required fields exist
7. Sanitise strings (prevent injection)
8. Check RLS policies on Supabase writes
9. Log action in `action_logs`

---

# ## 12. Error Format (Uniform)

All errors return:

```json
{
  "status": "error",
  "error_code": "string",
  "message": "human readable message"
}
```

Examples:

* `missing_field`
* `invalid_role`
* `yacht_mismatch`
* `schema_invalid`
* `workflow_failed`

---

# ## 13. n8n Integration Mapping

Actions that require workflow-level processing must map to n8n webhooks:

```
n8n/add_work_order
n8n/add_document_to_handover
n8n/order_part
n8n/close_work_order
```

These are triggered by:

```
internal_dispatcher → httpx → n8n webhook
```

---

# ## 14. Summary

This contract ensures:

* every micro-action has a clear API endpoint
* frontend has zero ambiguity
* search engine + action router are aligned
* permissions are consistent
* error patterns are predictable
* workflows are safe and auditable

CelesteOS remains:

* deterministic
* secure
* clean
* expandable
* easy for new engineers to reason about

---