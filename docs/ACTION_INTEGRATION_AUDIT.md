# CelesteOS Action Integration Audit

**Worker 9 - Action Integration Engineer**
**Date:** 2025-11-20
**Status:** Complete Audit

---

## 1. Complete Action Audit Table

This table maps EVERY micro-action to its card type, endpoint, payload, and requirements.

| # | Card Type | Action ID | Label | Endpoint | Method | Required Payload Fields | Role Required | Notes |
|---|-----------|-----------|-------|----------|--------|------------------------|---------------|-------|
| 1 | equipment | `add_note` | Add Note | `/v1/notes/create` | POST | yacht_id, equipment_id, note_text | Engineer, HOD | Fast internal handler |
| 2 | equipment | `create_work_order` | Create Work Order | `/v1/work-orders/create` | POST | yacht_id, equipment_id, title, description, priority | Engineer, HOD | n8n workflow |
| 3 | equipment | `view_history` | View History | `/v1/work-orders/history` | GET | equipment_id | All | Read-only |
| 4 | equipment | `add_to_handover` | Add to Handover | `/v1/handover/add-item` | POST | yacht_id, equipment_id, summary_text | Engineer, HOD | Appends to current handover |
| 5 | equipment | `show_related_documents` | Show Documents | `/v1/search` | GET | q=<equipment manual> | All | Triggers new search |
| 6 | document | `open_document` | Open Document | `/v1/documents/open` | POST | storage_path | All | Returns signed URL |
| 7 | document | `add_document_to_handover` | Add to Handover | `/v1/handover/add-document` | POST | yacht_id, document_id, context | Engineer, HOD | Links document to handover |
| 8 | document | `view_full_document` | View Full Manual | `/v1/documents/full` | GET | document_id | All | For chunked docs |
| 9 | fault | `diagnose_fault` | Diagnose Fault | `/v1/search` | GET | q=fault <code> | All | Triggers diagnostic search |
| 10 | fault | `create_work_order_fault` | Create Work Order | `/v1/work-orders/create` | POST | yacht_id, equipment_id, suspected_fault_code, description | Engineer, HOD | Pre-filled with fault context |
| 11 | fault | `add_note` | Add Note | `/v1/notes/create` | POST | yacht_id, equipment_id, note_text | Engineer, HOD | Same as equipment add_note |
| 12 | fault | `related_documents` | Related Docs | `/v1/search` | GET | q=<fault code> documentation | All | Search for fault docs |
| 13 | work_order | `add_note_to_work_order` | Add Note | `/v1/work-orders/add-note` | POST | yacht_id, work_order_id, note_text | Engineer, HOD | Adds note to existing WO |
| 14 | work_order | `close_work_order` | Mark Complete | `/v1/work-orders/close` | POST | yacht_id, work_order_id | HOD | Only HOD can close |
| 15 | work_order | `view_work_order_history` | View History | `/v1/work-orders/history` | GET | work_order_id | All | Full WO history |
| 16 | part | `view_stock` | Check Stock | `/v1/inventory/stock` | GET | part_id | All | Current stock levels |
| 17 | part | `order_part` | Order Part | `/v1/inventory/order-part` | POST | yacht_id, part_id, qty | Engineer, HOD | Creates purchase order |
| 18 | part | `add_part_to_handover` | Add to Handover | `/v1/handover/add-part` | POST | yacht_id, part_id, reason | Engineer, HOD | Notes part shortage/issue |
| 19 | predictive | `add_predictive_to_handover` | Add to Handover | `/v1/handover/add-predictive` | POST | yacht_id, equipment_id, insight_id, summary | Engineer, HOD | Captures predictive insight |
| 20 | predictive | `view_equipment` | View Equipment | `/v1/search` | GET | q=<equipment name> | All | Navigate to equipment |
| 21 | handover | `edit_handover_section` | Edit Section | `/v1/handover/edit-section` | POST | yacht_id, handover_id, section_name, new_text | HOD | Only HOD can edit |
| 22 | handover | `export_handover` | Export Handover | `/v1/handover/export` | POST | yacht_id | HOD | Generates PDF |

---

## 2. Action → Endpoint Mapping

### 2.1 Notes Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| add_note | `/v1/notes/create` | `{ yacht_id, equipment_id, note_text }` | Internal (Supabase direct) |
| add_note_to_work_order | `/v1/work-orders/add-note` | `{ yacht_id, work_order_id, note_text }` | Internal (Supabase direct) |

### 2.2 Work Order Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| create_work_order | `/v1/work-orders/create` | `{ yacht_id, equipment_id, title, description, priority }` | n8n workflow |
| create_work_order_fault | `/v1/work-orders/create` | `{ yacht_id, equipment_id, suspected_fault_code, description }` | n8n workflow |
| close_work_order | `/v1/work-orders/close` | `{ yacht_id, work_order_id }` | Internal |
| view_history | `/v1/work-orders/history?equipment_id=X` | N/A (GET) | Internal |
| view_work_order_history | `/v1/work-orders/history?work_order_id=X` | N/A (GET) | Internal |

### 2.3 Handover Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| add_to_handover | `/v1/handover/add-item` | `{ yacht_id, equipment_id, summary_text }` | n8n workflow |
| add_document_to_handover | `/v1/handover/add-document` | `{ yacht_id, document_id, context }` | n8n workflow |
| add_part_to_handover | `/v1/handover/add-part` | `{ yacht_id, part_id, reason }` | n8n workflow |
| add_predictive_to_handover | `/v1/handover/add-predictive` | `{ yacht_id, equipment_id, insight_id, summary }` | n8n workflow |
| edit_handover_section | `/v1/handover/edit-section` | `{ yacht_id, handover_id, section_name, new_text }` | Internal |
| export_handover | `/v1/handover/export` | `{ yacht_id }` | n8n workflow → PDF |

### 2.4 Document Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| open_document | `/v1/documents/open` | `{ storage_path }` | Internal (signed URL) |
| view_full_document | `/v1/documents/full?document_id=X` | N/A (GET) | Internal (signed URL) |

### 2.5 Fault/Diagnostic Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| diagnose_fault | `/v1/faults/diagnose?code=X&equipment_id=Y` | N/A (GET) | Search Engine (RAG+GraphRAG) |

### 2.6 Inventory Endpoints

| Action | Endpoint | Payload | Handler Type |
|--------|----------|---------|--------------|
| view_stock | `/v1/inventory/stock?part_id=X` | N/A (GET) | Internal (Supabase query) |
| order_part | `/v1/inventory/order-part` | `{ yacht_id, part_id, qty }` | n8n workflow |

### 2.7 Search Trigger Endpoints (Not mutations)

| Action | Endpoint | Purpose |
|--------|----------|---------|
| show_related_documents | `/v1/search?q=<equipment manual>` | New search |
| related_documents | `/v1/search?q=<fault code> documentation` | New search |
| view_equipment | `/v1/search?q=<equipment name>` | Navigate via search |

---

## 3. Missing Endpoints Analysis

Based on the action-endpoint-contract.md, these endpoints are SPECIFIED but NOT YET IMPLEMENTED:

### ✅ Already Defined (from integration layer)
- `/v1/search` - Exists (Task 9 integration layer)
- `/v1/work-orders` (list) - Exists (Task 9 integration layer)
- `/v1/equipment` - Exists (Task 9 integration layer)
- `/v1/predictive/state` - Exists (Task 9 integration layer)
- `/v1/predictive/insights` - Exists (Task 9 integration layer)

### ❌ MISSING - Need to implement

#### Notes
- ✅ POST `/v1/notes/create` - **NEED TO BUILD**

#### Work Orders
- ✅ POST `/v1/work-orders/create` - **NEED TO BUILD**
- ✅ POST `/v1/work-orders/add-note` - **NEED TO BUILD**
- ✅ POST `/v1/work-orders/close` - **NEED TO BUILD**
- ✅ GET `/v1/work-orders/history` - **NEED TO BUILD**

#### Handovers
- ✅ POST `/v1/handover/add-item` - **NEED TO BUILD**
- ✅ POST `/v1/handover/add-document` - **NEED TO BUILD**
- ✅ POST `/v1/handover/add-part` - **NEED TO BUILD** (new, not in original specs)
- ✅ POST `/v1/handover/add-predictive` - **NEED TO BUILD**
- ✅ POST `/v1/handover/edit-section` - **NEED TO BUILD**
- ✅ POST `/v1/handover/export` - **NEED TO BUILD**

#### Documents
- ✅ POST `/v1/documents/open` - **NEED TO BUILD**
- ✅ GET `/v1/documents/full` - **NEED TO BUILD**

#### Faults
- ✅ GET `/v1/faults/diagnose` - **NEED TO BUILD**

#### Inventory
- ✅ GET `/v1/inventory/stock` - **NEED TO BUILD**
- ✅ POST `/v1/inventory/order-part` - **NEED TO BUILD**

#### Predictive (for actions)
- GET `/v1/predictive/state?equipment_id=X` - Already exists from Task 9
- GET `/v1/predictive/insight?id=X` - **NEED TO BUILD**

**Total Missing Endpoints:** 18

---

## 4. Action Router Integration Points

The Action Router (backend) will be at:
```
POST /v1/actions/execute
```

This single endpoint receives ALL action requests and routes them.

### Request Format:
```json
{
  "action": "add_note",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid"
  },
  "payload": {
    "note_text": "Leak found near coolant outlet."
  }
}
```

### Response Format:
```json
{
  "status": "success",
  "action": "add_note",
  "result": { "note_id": "uuid" }
}
```

---

## 5. Security Requirements

Every action MUST:

1. **Validate JWT** - Extract user_id, yacht_id, role from Supabase JWT
2. **Yacht Isolation** - Ensure `context.yacht_id == user.yacht_id`
3. **Role Check** - Verify `user.role` in `action.allowed_roles`
4. **Required Fields** - Validate all required fields present
5. **Schema Validation** - Validate payload against JSON schema
6. **RLS Enforcement** - Supabase RLS policies prevent cross-yacht access
7. **Action Logging** - Log to `action_logs` table
8. **Sanitization** - Prevent SQL injection, XSS
9. **Rate Limiting** - Prevent abuse

---

## 6. Role Permission Matrix

| Action | Crew | ETO | Engineer | HOD | Manager |
|--------|------|-----|----------|-----|---------|
| add_note | ❌ | ✅ | ✅ | ✅ | ✅ |
| create_work_order | ❌ | ❌ | ✅ | ✅ | ✅ |
| close_work_order | ❌ | ❌ | ❌ | ✅ | ✅ |
| add_to_handover | ❌ | ✅ | ✅ | ✅ | ✅ |
| edit_handover_section | ❌ | ❌ | ❌ | ✅ | ✅ |
| export_handover | ❌ | ❌ | ❌ | ✅ | ✅ |
| order_part | ❌ | ❌ | ✅ | ✅ | ✅ |
| view_* (read-only) | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 7. n8n Workflow Mapping

Actions that require n8n workflows:

| Action | n8n Webhook | Purpose |
|--------|-------------|---------|
| create_work_order | `/webhook/create_work_order` | Complex WO creation + notifications |
| add_to_handover | `/webhook/add_to_handover` | Aggregate handover content |
| add_document_to_handover | `/webhook/add_document` | Link doc + extract metadata |
| add_predictive_to_handover | `/webhook/add_predictive` | Format predictive insight |
| export_handover | `/webhook/export_handover` | Generate PDF with formatting |
| order_part | `/webhook/order_part` | Create PO + notify suppliers |

**Internal (no n8n):**
- add_note
- close_work_order
- open_document
- view_* (all read operations)

---

## 8. Frontend Action Button Locations

### Search Results Page
- Equipment cards: add_note, create_work_order, add_to_handover, view_history
- Document cards: open_document, add_document_to_handover, view_full_document
- Fault cards: diagnose_fault, create_work_order_fault, add_note
- Part cards: view_stock, order_part, add_part_to_handover
- Work order cards: add_note_to_work_order, close_work_order, view_work_order_history
- Predictive cards: add_predictive_to_handover, view_equipment

### Dashboard Page
- Equipment widgets: create_work_order, view_history
- Predictive alerts: add_predictive_to_handover
- Work order list: close_work_order, add_note_to_work_order
- Inventory alerts: order_part

### Handover Page
- Handover draft: edit_handover_section, export_handover
- Suggested items: add_to_handover (various types)

---

## 9. Optimistic UI Requirements

Actions with optimistic UI (update before server response):

| Action | Optimistic Update | Rollback on Error |
|--------|-------------------|-------------------|
| add_note | Show note immediately | Remove note + show error |
| add_to_handover | Show "Added to handover" checkmark | Remove checkmark |
| close_work_order | Mark as "Completed" | Revert to previous status |
| order_part | Decrement stock estimate | Restore stock count |

Actions WITHOUT optimistic UI (wait for confirmation):
- create_work_order (redirect to new WO)
- export_handover (download file)
- open_document (open in new tab)

---

## 10. Error Handling Patterns

### User-Facing Errors

| Error Code | User Message | UI Behavior |
|------------|--------------|-------------|
| `missing_field` | "Please fill in all required fields" | Highlight missing field |
| `invalid_role` | "You don't have permission to perform this action" | Disable button |
| `yacht_mismatch` | "This item belongs to a different yacht" | Hide button |
| `workflow_failed` | "Action failed. Please try again." | Show retry button |
| `network_error` | "Network error. Retrying..." | Auto-retry 3x |

### Developer Errors (logged, not shown)

- `schema_invalid`
- `jwt_expired`
- `n8n_timeout`
- `supabase_error`

---

## 11. Action Lifecycle Example

**User Flow: "Create Work Order from Search Result"**

1. **User types:** "port generator vibration"
2. **Search returns:** Equipment card for "Port Generator" + Fault card for "Excessive Vibration"
3. **User clicks:** "Create Work Order" button on equipment card
4. **Frontend:**
   - Opens work order modal
   - Pre-fills: equipment_id, title="Fix Port Generator", description="Excessive vibration detected"
   - User adds priority="high"
   - Clicks "Submit"
5. **Frontend posts to:**
   ```
   POST /v1/actions/execute
   {
     "action": "create_work_order",
     "context": { "yacht_id": "...", "equipment_id": "..." },
     "payload": { "title": "...", "description": "...", "priority": "high" }
   }
   ```
6. **Action Router:**
   - Validates JWT → extracts user_id, yacht_id, role="Engineer"
   - Validates yacht_id matches
   - Validates role="Engineer" in allowed_roles
   - Validates payload schema
   - Dispatches to n8n workflow `/webhook/create_work_order`
7. **n8n workflow:**
   - Generates work order number
   - Inserts into `work_orders` table
   - Links to equipment
   - Notifies predictive engine
   - Logs action
8. **Response:**
   ```
   { "status": "success", "result": { "work_order_id": "uuid" } }
   ```
9. **Frontend:**
   - Shows success toast: "Work order created"
   - Redirects to work order detail page
   - Updates dashboard work order count

---

## 12. Testing Requirements

### Unit Tests
- Action Router registry loading
- JWT validation
- Yacht isolation enforcement
- Role permission checks
- Schema validation
- Payload sanitization

### Integration Tests
- POST /v1/actions/execute with valid action → success
- POST /v1/actions/execute with invalid role → 403
- POST /v1/actions/execute with cross-yacht access → 403
- POST /v1/actions/execute with missing field → 400

### End-to-End Tests
- Create work order from search
- Add note to equipment
- Export handover
- Order part

---

## 13. Implementation Priority

### Phase 1 - Core Actions (Immediate)
1. ✅ add_note
2. ✅ create_work_order
3. ✅ add_to_handover
4. ✅ open_document

### Phase 2 - Work Order Management
5. ✅ add_note_to_work_order
6. ✅ close_work_order
7. ✅ view_history

### Phase 3 - Handover Complete
8. ✅ add_document_to_handover
9. ✅ add_predictive_to_handover
10. ✅ edit_handover_section
11. ✅ export_handover

### Phase 4 - Inventory
12. ✅ view_stock
13. ✅ order_part

### Phase 5 - Diagnostics
14. ✅ diagnose_fault
15. ✅ view_full_document

---

## 14. Summary

- **Total Actions Defined:** 22
- **Unique Endpoints:** 18
- **Card Types:** 6 (equipment, document, fault, work_order, part, predictive, handover)
- **Role Types:** 5 (Crew, ETO, Engineer, HOD, Manager)
- **n8n Workflows:** 6
- **Internal Handlers:** 12

All actions route through `/v1/actions/execute` for:
- Centralized validation
- Consistent error handling
- Audit logging
- Easy extensibility

**Next Steps:**
1. Build Action Router Service (backend)
2. Build Action Client (frontend)
3. Implement missing endpoints
4. Create tests
5. Document integration

---

**End of Action Integration Audit**
