# CELESTEOS COMPLETE SITUATIONAL STATE ARCHITECTURE V4

**Version:** 4.0
**Date:** 2026-01-11
**Purpose:** Define HOW the backend dynamically adapts for EVERY situational state, which tables to pull from, which buckets to use, and how micro-actions within micro-actions work

---

## CRITICAL UNDERSTANDING

**SITUATIONAL STATE = Current context that determines:**
1. Which tables to query
2. Which buckets to access
3. Which actions are available
4. Which data to prefill
5. Which validations to enforce
6. Which follow-up actions trigger

**NOT just "what page am I on" - it's "what is the user DOING right now and what data do they need?"**

---

## TABLE OF CONTENTS

1. [EXISTING DATABASE TABLES](#1-existing-database-tables)
2. [EXISTING STORAGE BUCKETS](#2-existing-storage-buckets)
3. [ALL SITUATIONAL STATES](#3-all-situational-states)
4. [SITUATIONAL STATE MATRIX](#4-situational-state-matrix)
5. [BACKEND QUERY PATTERNS PER STATE](#5-backend-query-patterns-per-state)
6. [CROSS-ENTITY DATA PULLING](#6-cross-entity-data-pulling)
7. [NESTED MICRO-ACTIONS](#7-nested-micro-actions)
8. [STORAGE BUCKET USAGE MATRIX](#8-storage-bucket-usage-matrix)
9. [RPC FUNCTION ORGANIZATION](#9-rpc-function-organization)
10. [EXAMPLE: COMPLETE USER JOURNEY](#10-example-complete-user-journey)

---

## 1. EXISTING DATABASE TABLES

Based on your migrations, here are ALL tables in your database:

### Core Tables
- `yachts` - Vessel registry
- `user_profiles` / `auth_users_profiles` - User accounts
- `user_roles` - Role definitions
- `yacht_signatures` - Digital signatures for approvals

### Equipment & Faults
- `equipment` / `pms_equipment` - Physical assets
- `faults` - Fault reports
- `work_orders` / `pms_work_orders` - Work order management
- `work_order_notes` / `pms_work_order_notes` - WO comments
- `work_order_parts` - Parts used in WOs

### Parts & Inventory
- `parts` / `pms_parts` - Parts catalog
- `part_usage` / `pms_part_usage` - Parts consumption tracking
- `attachments` - File attachments (photos, documents)

### Communication
- `handover` / `pms_handover` - Shift handover items

### Documents & Search
- `documents` - Document metadata
- `doc_metadata` - Document metadata (alternative table)
- `document_sections` - Document sections/chapters
- `search_document_chunks` - RAG chunks with embeddings

### Audit
- `audit_log` / `pms_audit_log` - Audit trail

### API
- `api_tokens` / `user_tokens` - API authentication

---

## 2. EXISTING STORAGE BUCKETS

From your screenshot, you have **6 storage buckets:**

### Bucket 1: `documents`
**PURPOSE:** General documents (manuals, SOPs, drawings, certificates)
**FOLDER STRUCTURE:**
```
documents/
  {yacht_id}/
    manuals/
      {document_id}.pdf
    sops/
      {document_id}.pdf
    drawings/
      {document_id}.pdf
    certificates/
      {document_id}.pdf
```

### Bucket 2: `pms-finance-documents`
**PURPOSE:** Financial documents (invoices, receipts, PO confirmations)
**FOLDER STRUCTURE:**
```
pms-finance-documents/
  {yacht_id}/
    invoices/
      {invoice_id}.pdf
    receipts/
      {receipt_id}.pdf
    po-confirmations/
      {po_id}.pdf
```

### Bucket 3: `pms-part-photos`
**PURPOSE:** Photos of spare parts (for identification, condition documentation)
**FOLDER STRUCTURE:**
```
pms-part-photos/
  {yacht_id}/
    {part_id}/
      {photo_id}.jpg
```

### Bucket 4: `pms-label-pdfs`
**PURPOSE:** Generated labels for parts (QR codes, barcodes, shelf labels)
**FOLDER STRUCTURE:**
```
pms-label-pdfs/
  {yacht_id}/
    {part_id}/
      label_{timestamp}.pdf
```

### Bucket 5: `pms-discrepancy-photos`
**PURPOSE:** Photos of receiving discrepancies (damage, wrong item, quantity mismatch)
**FOLDER STRUCTURE:**
```
pms-discrepancy-photos/
  {yacht_id}/
    receiving-sessions/
      {session_id}/
        {item_id}/
          {photo_id}.jpg
```

### Bucket 6: `pms-receiving-images`
**PURPOSE:** General photos during receiving process (packaging, delivery condition)
**FOLDER STRUCTURE:**
```
pms-receiving-images/
  {yacht_id}/
    {session_id}/
      {photo_id}.jpg
```

---

## 3. ALL SITUATIONAL STATES

### 3.1 Fault Lifecycle States

| State | Description | Tables Queried | Actions Available |
|-------|-------------|----------------|-------------------|
| `VIEWING_FAULT_LIST` | User viewing all faults | `faults`, `equipment` | `report_fault` |
| `VIEWING_FAULT_DETAIL` | User viewing specific fault | `faults`, `equipment`, `work_orders`, `handover`, `audit_log` | `acknowledge_fault`, `diagnose_fault`, `create_work_order_from_fault`, `close_fault` |
| `REPORTING_FAULT` | User creating new fault | `equipment` (prefill) | `submit_fault_report` |
| `DIAGNOSING_FAULT` | User diagnosing fault | `faults`, `equipment`, `documents` (manuals), `search_document_chunks` | `save_diagnosis`, `create_work_order` |
| `FAULT_ACKNOWLEDGED` | Fault acknowledged by engineer | `faults`, `user_profiles` | `diagnose_fault` |
| `FAULT_WORK_CREATED` | Work order created from fault | `faults`, `work_orders` | View WO, update fault |

### 3.2 Work Order Lifecycle States

| State | Description | Tables Queried | Actions Available |
|-------|-------------|----------------|-------------------|
| `VIEWING_WO_LIST` | User viewing all work orders | `work_orders`, `equipment`, `user_profiles` | `create_work_order` |
| `VIEWING_WO_DETAIL` | User viewing specific WO | `work_orders`, `equipment`, `faults`, `work_order_parts`, `work_order_notes`, `user_profiles` | `assign_work_order`, `update_wo_hours`, `add_wo_note`, `add_wo_part`, `close_work_order` |
| `CREATING_WO` | User creating new WO | `equipment`, `faults` (if from fault) | `save_work_order` |
| `CREATING_WO_FROM_FAULT` | User creating WO from fault (NESTED) | `faults`, `equipment`, `parts` | `save_work_order` |
| `EXECUTING_WO` | User working on WO | `work_orders`, `parts`, `documents` (procedures) | `update_hours`, `add_parts`, `add_notes` |
| `CLOSING_WO` | User closing WO | `work_orders`, `work_order_parts`, `faults` | `sign_and_close` |

### 3.3 Parts & Inventory States

| State | Description | Tables Queried | Actions Available |
|-------|-------------|----------------|-------------------|
| `VIEWING_PARTS_CATALOG` | User browsing parts | `parts`, `attachments` (photos) | `add_part`, `edit_part` |
| `VIEWING_PART_DETAIL` | User viewing specific part | `parts`, `part_usage`, `equipment`, `work_orders`, `attachments` | `adjust_quantity`, `add_photo`, `generate_label`, `add_to_shopping_list` |
| `ADDING_PART_TO_WO` | User linking part to WO | `parts`, `work_orders` | `save_part_usage` |
| `ADJUSTING_INVENTORY` | User manually adjusting stock | `parts` | `save_adjustment`, `create_audit_log` |
| `GENERATING_PART_LABEL` | User generating QR label | `parts` | `generate_pdf`, `upload_to_pms-label-pdfs` |

### 3.4 Receiving States (COMPLEX - Multi-step)

| State | Description | Tables Queried | Buckets Used | Actions Available |
|-------|-------------|----------------|--------------|-------------------|
| `VIEWING_RECEIVING_SESSIONS` | User viewing all receiving sessions | `receiving_sessions`, `purchase_orders` | None | `start_receiving_session` |
| `STARTING_RECEIVING_SESSION` | User creating new session | `purchase_orders`, `shopping_list` | None | `create_session` |
| `ACTIVE_RECEIVING_SESSION` | User checking in items | `receiving_sessions`, `receiving_items`, `shopping_list`, `parts` | `pms-receiving-images`, `pms-discrepancy-photos` | `check_in_item`, `upload_photo`, `mark_discrepancy` |
| `CHECKING_IN_ITEM` | User verifying specific item | `receiving_items`, `shopping_list`, `parts` | `pms-part-photos`, `pms-discrepancy-photos` | `toggle_checkbox`, `add_notes`, `upload_discrepancy_photo` |
| `REVIEWING_DISCREPANCIES` | User reviewing items before commit | `receiving_items`, `receiving_sessions` | `pms-discrepancy-photos` | `add_discrepancy_notes`, `adjust_quantities` |
| `SIGNING_RECEIVING` | User signing off session | `receiving_sessions`, `receiving_items`, `user_profiles` | None | `capture_signature`, `finalize` |
| `COMMITTING_RECEIVING` | Backend processing commit | `receiving_sessions`, `receiving_items`, `parts`, `shopping_list`, `inventory_transactions`, `audit_log` | None | (Automatic) |
| `RECEIVING_COMMITTED` | Session immutably committed | `receiving_sessions`, `receiving_items`, `parts` | All receiving buckets (read-only) | View only |

### 3.5 Handover States

| State | Description | Tables Queried | Actions Available |
|-------|-------------|----------------|-------------------|
| `VIEWING_HANDOVER_LIST` | User viewing shift handover | `handover`, `faults`, `work_orders`, `equipment` | `create_handover`, `acknowledge_handover` |
| `CREATING_HANDOVER` | User creating handover item | `faults`, `work_orders`, `equipment` (context) | `save_handover` |
| `ACKNOWLEDGING_HANDOVER` | User acknowledging handover | `handover`, `user_profiles` | `acknowledge` |
| `HANDOVER_PENDING` | Handover awaiting acknowledgment | `handover`, `user_profiles` (on-duty crew) | `acknowledge` |

### 3.6 Document States

| State | Description | Tables Queried | Buckets Used | Actions Available |
|-------|-------------|----------------|--------------|-------------------|
| `VIEWING_DOCUMENTS_LIST` | User browsing documents | `documents`, `doc_metadata` | None | `upload_document` |
| `VIEWING_DOCUMENT_DETAIL` | User viewing document | `doc_metadata`, `search_document_chunks` | `documents` (PDF) | `semantic_search`, `download` |
| `DOCUMENT_VIEWER` | User viewing PDF + search | `doc_metadata`, `search_document_chunks`, `document_sections` | `documents` | `semantic_search`, `jump_to_section` |
| `SEMANTIC_SEARCH` | User searching within document | `search_document_chunks` (vector similarity) | None | `show_results`, `jump_to_chunk` |
| `UPLOADING_DOCUMENT` | User uploading new document | None (yet) | `documents` | `upload_file`, `save_metadata` |
| `PROCESSING_DOCUMENT` | Backend chunking/embedding | `documents`, `search_document_chunks` | `documents` | (Automatic) |

### 3.7 Finance States

| State | Description | Tables Queried | Buckets Used | Actions Available |
|-------|-------------|----------------|--------------|-------------------|
| `VIEWING_FINANCE_DASHBOARD` | User viewing financial overview | `shopping_list`, `purchase_orders`, `receiving_sessions`, `parts` | `pms-finance-documents` | `upload_invoice` |
| `VIEWING_INVOICE` | User viewing specific invoice | `purchase_orders`, `receiving_sessions` | `pms-finance-documents` | `download`, `attach_to_po` |
| `UPLOADING_INVOICE` | User uploading invoice PDF | `purchase_orders` | `pms-finance-documents` | `upload_file`, `link_to_po` |

---

## 4. SITUATIONAL STATE MATRIX

This matrix shows **WHICH TABLES AND BUCKETS** are accessed for each primary situational state:

| Situational State | Primary Tables | Secondary Tables | Buckets | RPC Functions |
|-------------------|----------------|------------------|---------|---------------|
| **VIEWING_FAULT_DETAIL** | `faults` | `equipment`, `work_orders`, `handover`, `audit_log`, `attachments` | None | `get_fault_details` |
| **DIAGNOSING_FAULT** | `faults`, `equipment` | `documents`, `search_document_chunks` | `documents` (manuals) | `diagnose_fault`, `semantic_search` |
| **VIEWING_WO_DETAIL** | `work_orders` | `equipment`, `faults`, `work_order_parts`, `work_order_notes`, `user_profiles` | None | `get_work_order_details` |
| **EXECUTING_WO** | `work_orders`, `parts` | `documents`, `work_order_parts`, `part_usage` | `documents` (procedures) | `update_wo_hours`, `add_wo_part` |
| **VIEWING_PART_DETAIL** | `parts` | `part_usage`, `equipment`, `work_orders`, `attachments` | `pms-part-photos` | `get_part_details` |
| **GENERATING_PART_LABEL** | `parts` | None | `pms-label-pdfs` | `generate_part_label_pdf` |
| **ACTIVE_RECEIVING_SESSION** | `receiving_sessions`, `receiving_items` | `shopping_list`, `parts`, `purchase_orders` | `pms-receiving-images`, `pms-discrepancy-photos` | `get_receiving_session`, `check_in_item` |
| **CHECKING_IN_ITEM** | `receiving_items` | `shopping_list`, `parts` | `pms-part-photos`, `pms-discrepancy-photos` | `toggle_item_checkbox`, `upload_discrepancy_photo` |
| **COMMITTING_RECEIVING** | `receiving_sessions`, `receiving_items`, `parts` | `shopping_list`, `inventory_transactions`, `audit_log` | All receiving buckets (finalize) | `commit_receiving_session` |
| **DOCUMENT_VIEWER** | `doc_metadata`, `search_document_chunks` | `document_sections` | `documents` | `get_document_storage_path`, `semantic_search` |
| **UPLOADING_INVOICE** | `purchase_orders` | `receiving_sessions` | `pms-finance-documents` | `upload_invoice_metadata` |

---

## 5. BACKEND QUERY PATTERNS PER STATE

### 5.1 VIEWING_FAULT_DETAIL

**User Action:** User clicks on a fault to view details

**Backend Query Flow:**
```sql
-- Step 1: Get fault details
SELECT f.*, e.name as equipment_name, e.location as equipment_location
FROM faults f
JOIN equipment e ON f.equipment_id = e.id
WHERE f.id = {fault_id}
  AND f.yacht_id = {user_yacht_id}
  AND f.deleted_at IS NULL;

-- Step 2: Get related work orders
SELECT wo.*
FROM work_orders wo
WHERE wo.fault_id = {fault_id}
  AND wo.yacht_id = {user_yacht_id}
  AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC;

-- Step 3: Get handover items mentioning this fault
SELECT h.*
FROM handover h
WHERE h.entity_type = 'fault'
  AND h.entity_id = {fault_id}
  AND h.yacht_id = {user_yacht_id}
  AND h.acknowledged_at IS NULL;

-- Step 4: Get audit trail
SELECT al.*
FROM audit_log al
WHERE al.entity_type = 'fault'
  AND al.entity_id = {fault_id}
  AND al.yacht_id = {user_yacht_id}
ORDER BY al.created_at DESC
LIMIT 50;

-- Step 5: Get attachments (photos of fault)
SELECT a.*
FROM attachments a
WHERE a.entity_type = 'fault'
  AND a.entity_id = {fault_id}
  AND a.yacht_id = {user_yacht_id};
```

**Data Returned to Frontend:**
```typescript
{
  fault: {
    id: UUID,
    equipment_id: UUID,
    equipment_name: string,
    equipment_location: string,
    fault_type: string,
    description: string,
    severity: string,
    status: string,
    reported_by_name: string,
    reported_at: timestamp,
    diagnosis: string,
    diagnosed_by_name: string,
    diagnosed_at: timestamp,
  },
  related_work_orders: WorkOrder[],
  handover_items: HandoverItem[],
  audit_trail: AuditLogEntry[],
  attachments: Attachment[]
}
```

**Actions Available (based on state + user role):**
```typescript
// Crew can only view
if (user.role === 'crew') {
  actions = [];
}

// Engineer+ can acknowledge if status = 'reported'
if (['engineer', '2nd_engineer', 'chief_engineer'].includes(user.role) && fault.status === 'reported') {
  actions.push('acknowledge_fault');
}

// Engineer+ can diagnose if status = 'acknowledged'
if (['engineer', '2nd_engineer', 'chief_engineer'].includes(user.role) && fault.status === 'acknowledged') {
  actions.push('diagnose_fault');
}

// Engineer+ can create WO if status = 'diagnosed'
if (['engineer', '2nd_engineer', 'chief_engineer'].includes(user.role) && fault.status === 'diagnosed') {
  actions.push('create_work_order_from_fault');
}
```

### 5.2 DIAGNOSING_FAULT (With Document Context)

**User Action:** Engineer diagnosing fault, needs manual reference

**Backend Query Flow:**
```sql
-- Step 1: Get fault + equipment details
SELECT f.*, e.name, e.manufacturer, e.model, e.serial_number
FROM faults f
JOIN equipment e ON f.equipment_id = e.id
WHERE f.id = {fault_id};

-- Step 2: Search for relevant manual sections (SEMANTIC SEARCH)
-- User query: "generator coolant pressure low troubleshooting"
-- Backend generates embedding, then:
SELECT
  sdc.id as chunk_id,
  sdc.document_id,
  sdc.chunk_text,
  sdc.page_number,
  dm.filename,
  dm.storage_path,
  1 - (sdc.embedding <=> {query_embedding}) AS similarity
FROM search_document_chunks sdc
JOIN doc_metadata dm ON sdc.document_id = dm.id
WHERE dm.yacht_id = {user_yacht_id}
  AND dm.equipment_id = {equipment_id}  -- Filter to this equipment's manuals
  AND 1 - (sdc.embedding <=> {query_embedding}) > 0.7
ORDER BY sdc.embedding <=> {query_embedding}
LIMIT 5;

-- Step 3: Get signed URL for document PDF
-- (Done via RPC: get_document_storage_path)
```

**Frontend Displays:**
- Fault details (left panel)
- Diagnosis form (center)
- Semantic search results (right panel)
  - Top 5 relevant manual sections
  - Click to open PDF viewer at specific page
  - Inline chunk text preview

**Action Flow:**
```typescript
// 1. User types diagnosis
diagnosis = "Coolant pump seal failure. Pressure drops to 1.2 bar after 30min runtime."

// 2. User searches manual
semanticSearch("coolant pump seal replacement procedure")
  → Backend returns chunks from manual pages 45-48

// 3. User reads manual, confirms diagnosis

// 4. User saves diagnosis
await diagnoseFault(fault_id, {
  diagnosis,
  root_cause: "Coolant pump seal wear",
  recommended_action: "Replace coolant pump seal. Part #GEN-SEAL-001",
  manual_reference: "Generator Manual p.45-48"
})

// 5. Fault status → 'diagnosed'
// 6. Action 'create_work_order_from_fault' becomes available
```

### 5.3 ACTIVE_RECEIVING_SESSION (Multi-table, Multi-bucket)

**User Action:** Chief Engineer checking in delivered parts

**Backend Query Flow:**
```sql
-- Step 1: Get receiving session
SELECT rs.*
FROM receiving_sessions rs
WHERE rs.id = {session_id}
  AND rs.yacht_id = {user_yacht_id};

-- Step 2: Get all items in session
SELECT
  ri.*,
  sl.part_number,
  sl.description,
  sl.quantity_requested,
  p.name as part_name,
  p.current_quantity_onboard
FROM receiving_items ri
JOIN shopping_list sl ON ri.shopping_list_item_id = sl.id
LEFT JOIN parts p ON sl.part_id = p.id
WHERE ri.receiving_session_id = {session_id}
ORDER BY ri.created_at;

-- Step 3: Get purchase order details
SELECT po.*
FROM purchase_orders po
WHERE po.id = {rs.purchase_order_id};

-- Step 4: Get existing photos for this session
SELECT a.*
FROM attachments a
WHERE a.entity_type = 'receiving_session'
  AND a.entity_id = {session_id}
ORDER BY a.created_at;
```

**Buckets Accessed:**
- `pms-receiving-images`: General delivery photos
- `pms-discrepancy-photos`: Photos of damaged/wrong items
- `pms-part-photos`: Reference photos of parts for comparison

**Action Flow (Nested Micro-actions):**
```typescript
// MACRO-ACTION: check_in_all_items
// Contains MULTIPLE micro-actions:

for each item in receiving_items:
  // MICRO-ACTION 1: View item details
  displayItem(item)

  // MICRO-ACTION 2: User verifies item physically
  // (No database action, just user looking at physical part)

  // MICRO-ACTION 3: User ticks checkbox (CHECKBOX = TRUTH)
  await toggleItemCheckbox(item.id, true)

  // MICRO-ACTION 4a: If item matches, move to next
  if (item_matches) {
    continue;
  }

  // MICRO-ACTION 4b: If discrepancy, user takes photo
  if (discrepancy) {
    // Upload to pms-discrepancy-photos bucket
    photo_url = await uploadDiscrepancyPhoto(session_id, item.id, photo_file)

    // Update item with discrepancy notes
    await addDiscrepancyNotes(item.id, {
      condition: 'damaged',
      notes: "Packaging damaged, pump casing cracked",
      photo_urls: [photo_url]
    })

    // Uncheck item (won't be committed to inventory)
    await toggleItemCheckbox(item.id, false)
  }

// After all items checked:
// MACRO-ACTION: commit_receiving_session
// This triggers MULTIPLE backend operations:
await commitReceivingSession(session_id)
  // Backend atomically:
  // 1. Validates signature
  // 2. Processes ONLY checked items
  // 3. Creates inventory_transactions
  // 4. Updates parts.current_quantity_onboard
  // 5. Updates shopping_list.status = 'fulfilled'
  // 6. Updates receiving_session.status = 'committed' (IMMUTABLE)
  // 7. Creates audit_log entries
```

### 5.4 VIEWING_PART_DETAIL (Cross-entity data pulling)

**User Action:** User views a specific part

**Backend Query Flow:**
```sql
-- Step 1: Get part details
SELECT p.*
FROM parts p
WHERE p.id = {part_id}
  AND p.yacht_id = {user_yacht_id};

-- Step 2: Get usage history
SELECT
  pu.*,
  wo.title as work_order_title,
  wo.status as work_order_status,
  e.name as equipment_name
FROM part_usage pu
JOIN work_orders wo ON pu.work_order_id = wo.id
JOIN equipment e ON wo.equipment_id = e.id
WHERE pu.part_id = {part_id}
  AND pu.yacht_id = {user_yacht_id}
ORDER BY pu.created_at DESC
LIMIT 50;

-- Step 3: Get equipment this part is used on
SELECT DISTINCT
  e.*
FROM equipment e
JOIN work_orders wo ON wo.equipment_id = e.id
JOIN part_usage pu ON pu.work_order_id = wo.id
WHERE pu.part_id = {part_id}
  AND e.yacht_id = {user_yacht_id};

-- Step 4: Get photos of this part
SELECT a.*
FROM attachments a
WHERE a.entity_type = 'part'
  AND a.entity_id = {part_id}
ORDER BY a.created_at DESC;

-- Step 5: Check if part is in active shopping list
SELECT sl.*
FROM shopping_list sl
WHERE sl.part_id = {part_id}
  AND sl.status IN ('candidate', 'active', 'approved')
  AND sl.yacht_id = {user_yacht_id};

-- Step 6: Get generated labels
-- (Query pms-label-pdfs bucket via storage API)
```

**Data Returned:**
```typescript
{
  part: {
    id: UUID,
    part_number: string,
    name: string,
    current_quantity_onboard: number,
    reorder_point: number,
    unit_cost_usd: number,
    location: string,
    manufacturer: string,
  },
  usage_history: PartUsage[], // Last 50 uses
  used_on_equipment: Equipment[], // Which equipment uses this part
  photos: Attachment[], // From pms-part-photos bucket
  active_shopping_items: ShoppingListItem[], // Is this part on order?
  labels: LabelFile[] // Generated QR labels from pms-label-pdfs
}
```

**Actions Available:**
```typescript
actions = [];

// All users can view
// Engineer+ can adjust inventory
if (['engineer', '2nd_engineer', 'chief_engineer'].includes(user.role)) {
  actions.push('adjust_inventory');
  actions.push('add_photo');
  actions.push('generate_label');
  actions.push('add_to_shopping_list');
}

// Check if stock is low
if (part.current_quantity_onboard <= part.reorder_point) {
  actions.push('add_to_shopping_list'); // Highlighted/suggested action
}
```

---

## 6. CROSS-ENTITY DATA PULLING

**CRITICAL CONCEPT:** When viewing ANY entity, the backend pulls related data from ALL relevant tables.

### 6.1 Equipment Detail View

**Query Pattern:**
```sql
-- Equipment details
SELECT * FROM equipment WHERE id = {equipment_id};

-- Related faults (last 6 months)
SELECT * FROM faults
WHERE equipment_id = {equipment_id}
AND created_at > NOW() - INTERVAL '6 months'
ORDER BY created_at DESC;

-- Related work orders
SELECT * FROM work_orders
WHERE equipment_id = {equipment_id}
ORDER BY created_at DESC
LIMIT 20;

-- Parts used on this equipment
SELECT DISTINCT p.*
FROM parts p
JOIN part_usage pu ON pu.part_id = p.id
JOIN work_orders wo ON wo.id = pu.work_order_id
WHERE wo.equipment_id = {equipment_id};

-- Handover items about this equipment
SELECT * FROM handover
WHERE entity_type = 'equipment'
AND entity_id = {equipment_id}
AND acknowledged_at IS NULL;

-- Equipment manual
SELECT * FROM doc_metadata
WHERE equipment_id = {equipment_id}
AND document_type = 'manual';
```

### 6.2 Work Order Detail View

**Query Pattern:**
```sql
-- Work order details
SELECT wo.*, e.name as equipment_name, f.description as fault_description
FROM work_orders wo
LEFT JOIN equipment e ON wo.equipment_id = e.id
LEFT JOIN faults f ON wo.fault_id = f.id
WHERE wo.id = {wo_id};

-- Parts used
SELECT wp.*, p.part_number, p.name
FROM work_order_parts wp
JOIN parts p ON wp.part_id = p.id
WHERE wp.work_order_id = {wo_id};

-- Notes/comments
SELECT * FROM work_order_notes
WHERE work_order_id = {wo_id}
ORDER BY created_at;

-- Related fault (if exists)
SELECT * FROM faults WHERE id = {wo.fault_id};

-- Handover items about this WO
SELECT * FROM handover
WHERE entity_type = 'work_order'
AND entity_id = {wo_id};

-- Procedure documents
SELECT dm.* FROM doc_metadata dm
WHERE dm.equipment_id = {wo.equipment_id}
AND dm.document_type = 'procedure';
```

---

## 7. NESTED MICRO-ACTIONS

### 7.1 CREATE_WORK_ORDER_FROM_FAULT (Nested Action)

**Parent Action:** `create_work_order_from_fault`
**Child Actions:** `diagnose_fault` (optional), `create_work_order`, `update_fault_status`

**Flow:**
```typescript
// STEP 1: PREFILL (Read from fault)
const fault = await getFaultDetails(fault_id);
const equipment = await getEquipmentDetails(fault.equipment_id);

const prefillData = {
  equipment_id: fault.equipment_id,
  equipment_name: equipment.name,
  title: `Fix: ${fault.description.substring(0, 50)}`,
  description: fault.diagnosis || fault.description,
  priority: mapSeverityToPriority(fault.severity),
  fault_id: fault.id,
};

// STEP 2: USER EDITS (No mutation yet)
// User can modify title, description, add parts, etc.

// STEP 3: PREVIEW (Read-only calculation)
const preview = {
  estimated_hours: calculateEstimatedHours(workOrderData),
  required_parts: getRequiredParts(workOrderData),
  total_cost: calculateTotalCost(workOrderData),
};

// STEP 4: EXECUTE (ATOMIC TRANSACTION)
await createWorkOrderFromFault({
  fault_id,
  work_order_data: userEditedData,
})
// Backend RPC does ATOMICALLY:
// 1. INSERT into work_orders
// 2. UPDATE faults SET status = 'work_created'
// 3. INSERT into audit_log (2 entries: WO created, fault updated)
// 4. IF parts specified, INSERT into work_order_parts
// 5. RETURN success with new WO ID

// STEP 5: SUCCESS
// Navigate user to new work order detail page
```

### 7.2 COMMIT_RECEIVING_SESSION (Multi-step with Checkpoints)

**Parent Action:** `commit_receiving_session`
**Child Actions:** `review_items`, `verify_discrepancies`, `capture_signature`, `execute_commit`

**Flow:**
```typescript
// CHECKPOINT 1: Review
const sessionData = await getReceivingSessionDetails(session_id);
// Display:
// - Total items: 15
// - Checked items: 12 (will be committed)
// - Unchecked items: 3 (discrepancies, won't commit)
// - Total value: $4,567.89

// CHECKPOINT 2: Verify discrepancies
const uncheckedItems = sessionData.items.filter(i => !i.checked);
for (item of uncheckedItems) {
  // Must have discrepancy notes
  if (!item.discrepancy_notes) {
    throw Error("Unchecked item must have discrepancy explanation");
  }
}

// CHECKPOINT 3: Signature (if required)
if (sessionData.total_value > 1000) {
  const signature = await captureSignature(user_id);
  await addSignatureToSession(session_id, signature);
}

// CHECKPOINT 4: Execute (IMMUTABLE COMMIT)
await commitReceivingSession(session_id);
// Backend RPC does ATOMICALLY (in transaction):
// 1. Validate session.status = 'review'
// 2. Validate signature exists (if required)
// 3. FOR EACH checked item:
//    a. INSERT into inventory_transactions
//    b. UPDATE parts SET current_quantity_onboard += quantity
//    c. UPDATE shopping_list SET status = 'fulfilled'
// 4. UPDATE receiving_session SET status = 'committed' (IMMUTABLE)
// 5. INSERT into audit_log
// 6. COMMIT TRANSACTION

// After commit, session CANNOT be modified (immutable audit trail)
```

### 7.3 DIAGNOSE_FAULT with SEMANTIC_SEARCH (Nested Read Action)

**Parent Action:** `diagnose_fault`
**Child Actions:** `semantic_search`, `view_manual_section`

**Flow:**
```typescript
// User is on diagnose fault page
const fault = await getFaultDetails(fault_id);
const equipment = await getEquipmentDetails(fault.equipment_id);

// NESTED ACTION 1: Semantic search for relevant manual sections
const query = "coolant pump low pressure troubleshooting";
const searchResults = await semanticSearch({
  query,
  equipment_id: fault.equipment_id,
  document_type: 'manual',
  limit: 5,
});

// Display search results:
// 1. "Coolant System Troubleshooting" (p.45, 87% match)
// 2. "Pump Seal Inspection Procedure" (p.48, 82% match)
// 3. "Low Pressure Symptoms" (p.51, 78% match)

// NESTED ACTION 2: User clicks result to view manual
await viewManualSection({
  document_id: searchResults[0].document_id,
  page_number: searchResults[0].page_number,
});

// Opens PDF viewer in modal:
// - Left: PDF at page 45
// - Right: Highlighted chunk text

// User reads manual, identifies: "Pump seal wear"

// PARENT ACTION CONTINUES: Save diagnosis
await diagnoseFault(fault_id, {
  diagnosis: "Coolant pump seal failure confirmed. Manual ref: Generator Manual p.45",
  root_cause: "Seal wear after 12,000 operating hours",
  recommended_action: "Replace pump seal. Part #GEN-SEAL-001",
  manual_reference: searchResults[0].document_id + "#page=" + searchResults[0].page_number,
});

// Fault status → 'diagnosed'
```

---

## 8. STORAGE BUCKET USAGE MATRIX

| Bucket | Used In Situations | File Types | Uploaded By | Access Control |
|--------|-------------------|------------|-------------|----------------|
| `documents` | Document viewer, semantic search, fault diagnosis, WO execution | PDF, DOCX | Engineer+ | RLS: `{yacht_id}/category/` |
| `pms-finance-documents` | Invoice upload, PO attachment, receiving verification | PDF, JPG | Chief Engineer+, Captain | RLS: `{yacht_id}/invoices/` |
| `pms-part-photos` | Part detail view, part catalog, receiving verification | JPG, PNG | Engineer+ | RLS: `{yacht_id}/{part_id}/` |
| `pms-label-pdfs` | Part label generation, print labels | PDF | Auto-generated | RLS: `{yacht_id}/{part_id}/` |
| `pms-discrepancy-photos` | Receiving check-in, discrepancy reporting | JPG, PNG | All users during receiving | RLS: `{yacht_id}/receiving-sessions/{session_id}/` |
| `pms-receiving-images` | Receiving session, delivery documentation | JPG, PNG | All users during receiving | RLS: `{yacht_id}/{session_id}/` |

### 8.1 Bucket Access Patterns

**documents:**
```typescript
// READ: Get signed URL for PDF viewer
const { data } = await supabase.storage
  .from('documents')
  .createSignedUrl(`${yacht_id}/manuals/${document_id}.pdf`, 3600);

// WRITE: Upload new manual
await supabase.storage
  .from('documents')
  .upload(`${yacht_id}/manuals/${document_id}.pdf`, file);
```

**pms-discrepancy-photos:**
```typescript
// WRITE: Upload discrepancy photo during receiving
await supabase.storage
  .from('pms-discrepancy-photos')
  .upload(`${yacht_id}/receiving-sessions/${session_id}/${item_id}/${photo_id}.jpg`, file);

// READ: Display discrepancy photos in review step
const { data } = await supabase.storage
  .from('pms-discrepancy-photos')
  .list(`${yacht_id}/receiving-sessions/${session_id}`);
```

**pms-label-pdfs:**
```typescript
// WRITE: Generate and store part label
const labelPdf = await generatePartLabelPDF(part);
await supabase.storage
  .from('pms-label-pdfs')
  .upload(`${yacht_id}/${part_id}/label_${timestamp}.pdf`, labelPdf);

// READ: Download label for printing
const { data } = await supabase.storage
  .from('pms-label-pdfs')
  .download(`${yacht_id}/${part_id}/label_${timestamp}.pdf`);
```

---

## 9. RPC FUNCTION ORGANIZATION

### 9.1 Situational RPC Mapping

Each situational state may call MULTIPLE RPCs:

| Situational State | RPC Functions Called |
|-------------------|---------------------|
| `VIEWING_FAULT_DETAIL` | `get_fault_details(fault_id)` |
| `DIAGNOSING_FAULT` | `get_fault_details(fault_id)`, `semantic_search(query, equipment_id)`, `diagnose_fault(fault_id, diagnosis_data)` |
| `CREATING_WO_FROM_FAULT` | `get_fault_details(fault_id)`, `create_work_order_from_fault(fault_id, wo_data)` |
| `ACTIVE_RECEIVING_SESSION` | `get_receiving_session_details(session_id)`, `toggle_item_checkbox(item_id, checked)`, `upload_discrepancy_photo(...)` |
| `COMMITTING_RECEIVING` | `commit_receiving_session(session_id)` |
| `DOCUMENT_VIEWER` | `get_document_storage_path(document_id)`, `semantic_search(query, document_id)` |
| `GENERATING_PART_LABEL` | `get_part_details(part_id)`, `generate_part_label_pdf(part_id)` |

### 9.2 RPC Function Template (with Situational Awareness)

```sql
-- RPC: get_fault_details (Situational: VIEWING_FAULT_DETAIL)
CREATE OR REPLACE FUNCTION get_fault_details(p_fault_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_yacht_id UUID;
  v_result JSON;
BEGIN
  -- Validate yacht access
  SELECT yacht_id INTO v_yacht_id
  FROM user_profiles
  WHERE id = auth.uid();

  -- Build response with ALL related data for this situation
  SELECT json_build_object(
    'fault', (
      SELECT row_to_json(f)
      FROM (
        SELECT f.*, e.name as equipment_name, e.location
        FROM faults f
        JOIN equipment e ON f.equipment_id = e.id
        WHERE f.id = p_fault_id AND f.yacht_id = v_yacht_id
      ) f
    ),
    'related_work_orders', (
      SELECT json_agg(row_to_json(wo))
      FROM work_orders wo
      WHERE wo.fault_id = p_fault_id AND wo.yacht_id = v_yacht_id
    ),
    'handover_items', (
      SELECT json_agg(row_to_json(h))
      FROM handover h
      WHERE h.entity_type = 'fault' AND h.entity_id = p_fault_id
      AND h.acknowledged_at IS NULL
    ),
    'audit_trail', (
      SELECT json_agg(row_to_json(al))
      FROM audit_log al
      WHERE al.entity_type = 'fault' AND al.entity_id = p_fault_id
      ORDER BY al.created_at DESC LIMIT 50
    ),
    'available_actions', (
      -- Compute which actions are available based on state + role
      SELECT json_build_array(
        CASE WHEN f.status = 'reported' AND up.role IN ('engineer', 'chief_engineer')
          THEN 'acknowledge_fault' ELSE NULL END,
        CASE WHEN f.status = 'acknowledged' AND up.role IN ('engineer', 'chief_engineer')
          THEN 'diagnose_fault' ELSE NULL END,
        CASE WHEN f.status = 'diagnosed' AND up.role IN ('engineer', 'chief_engineer')
          THEN 'create_work_order_from_fault' ELSE NULL END
      )
      FROM faults f, user_profiles up
      WHERE f.id = p_fault_id AND up.id = auth.uid()
    )
  ) INTO v_result;

  RETURN v_result;
END;
$$;
```

---

## 10. EXAMPLE: COMPLETE USER JOURNEY

### Journey: Report Fault → Diagnose → Create WO → Execute → Close

**Situation 1: REPORTING_FAULT**

```typescript
// User clicks "Report Fault" button

// BACKEND QUERY 1: Prefill equipment list
const equipment = await supabase.rpc('get_equipment_list', { yacht_id });

// FRONTEND: Display modal with form
<ReportFaultModal>
  <Select name="equipment_id" options={equipment} />
  <Select name="fault_type" options={['mechanical', 'electrical', ...]} />
  <Textarea name="description" minLength={10} />
  <Select name="severity" options={['low', 'medium', 'high', 'critical']} />
</ReportFaultModal>

// User submits form
await supabase.rpc('report_fault', {
  equipment_id: 'uuid-123',
  fault_type: 'mechanical',
  description: 'Generator coolant pressure dropping to 1.2 bar after 30min runtime',
  severity: 'high'
});

// BACKEND:
// 1. INSERT into faults
// 2. INSERT into audit_log
// 3. IF severity = 'critical', INSERT into handover (auto-trigger)
// 4. RETURN fault_id

// Navigate to fault detail
```

**Situation 2: VIEWING_FAULT_DETAIL**

```typescript
// User navigates to /faults/{fault_id}

// BACKEND QUERY:
const faultData = await supabase.rpc('get_fault_details', { fault_id });

// FRONTEND displays:
// - Fault details
// - Equipment details
// - Related work orders: []
// - Handover items: [{ summary: "HIGH severity fault on Generator..." }]
// - Audit trail: [{ action: "report_fault", user: "John Doe", ... }]
// - Available actions: ['acknowledge_fault']

// Engineer clicks "Acknowledge Fault"
```

**Situation 3: ACKNOWLEDGING_FAULT**

```typescript
await supabase.rpc('acknowledge_fault', {
  fault_id,
  notes: "Acknowledged. Will investigate coolant system."
});

// BACKEND:
// 1. UPDATE faults SET status = 'acknowledged', acknowledged_by = user_id, acknowledged_at = NOW()
// 2. INSERT into audit_log
// 3. RETURN success

// Fault detail page refreshes
// Available actions: ['diagnose_fault']
```

**Situation 4: DIAGNOSING_FAULT (with Semantic Search)**

```typescript
// User clicks "Diagnose Fault"

// BACKEND QUERY 1: Get equipment manual
const manual = await supabase
  .from('doc_metadata')
  .select('*')
  .eq('equipment_id', fault.equipment_id)
  .eq('document_type', 'manual')
  .single();

// FRONTEND: Split screen
// Left: Diagnosis form
// Right: Semantic search panel

// User types in search: "coolant pressure low troubleshooting"
const searchResults = await supabase.rpc('semantic_search', {
  query: "coolant pressure low troubleshooting",
  document_id: manual.id,
  limit: 5
});

// Results:
// 1. Page 45: "Coolant System Troubleshooting" (87% match)
// 2. Page 48: "Pump Seal Inspection" (82% match)
// 3. Page 51: "Low Pressure Symptoms" (78% match)

// User clicks result #1
// Opens PDF viewer at page 45

// User reads manual, identifies: "Pump seal failure"

// User fills diagnosis form
await supabase.rpc('diagnose_fault', {
  fault_id,
  diagnosis: "Coolant pump seal failure confirmed per manual page 45",
  root_cause: "Pump seal wear (12,000 operating hours)",
  recommended_action: "Replace pump seal. Part #GEN-SEAL-001"
});

// BACKEND:
// 1. UPDATE faults SET status = 'diagnosed', diagnosis = ..., diagnosed_by = user_id
// 2. INSERT into audit_log
// 3. RETURN success

// Available actions: ['create_work_order_from_fault']
```

**Situation 5: CREATING_WO_FROM_FAULT (Nested Action)**

```typescript
// User clicks "Create Work Order"

// STEP 1: PREFILL (Backend queries fault)
const prefillData = await supabase.rpc('prefill_work_order_from_fault', { fault_id });
// Returns:
// {
//   equipment_id: 'uuid-123',
//   equipment_name: 'Port Generator',
//   title: 'Fix: Generator coolant pressure dropping...',
//   description: 'Coolant pump seal failure confirmed...',
//   priority: 'high',
//   estimated_hours: 3.5,
//   required_parts: [{ part_id: 'uuid-456', part_number: 'GEN-SEAL-001', quantity: 1 }]
// }

// STEP 2: USER EDITS
// User can modify title, add labor hours, add more parts, etc.

// STEP 3: PREVIEW
const preview = calculateWorkOrderCost(userEditedData);
// {
//   labor_cost: $350 (3.5 hours × $100/hr),
//   parts_cost: $125 (GEN-SEAL-001),
//   total_cost: $475
// }

// STEP 4: EXECUTE
await supabase.rpc('create_work_order_from_fault', {
  fault_id,
  work_order_data: userEditedData
});

// BACKEND (ATOMIC TRANSACTION):
// BEGIN;
//   1. INSERT into work_orders
//   2. INSERT into work_order_parts (for each part)
//   3. UPDATE faults SET status = 'work_created', work_order_id = new_wo_id
//   4. INSERT into audit_log (2 entries: WO created, fault updated)
// COMMIT;

// STEP 5: SUCCESS
// Navigate to /work-orders/{new_wo_id}
```

**Situation 6: EXECUTING_WO**

```typescript
// User views WO detail
const woData = await supabase.rpc('get_work_order_details', { wo_id });

// User starts work
await supabase.rpc('start_work_order', { wo_id });
// Updates: status = 'in_progress', started_at = NOW()

// User logs hours
await supabase.rpc('add_work_order_hours', {
  wo_id,
  hours: 2.5,
  notes: "Removed old pump seal, cleaned housing"
});

// User adds part usage
await supabase.rpc('use_part_on_work_order', {
  wo_id,
  part_id: 'uuid-456',
  quantity: 1
});

// BACKEND:
// 1. INSERT into work_order_parts
// 2. INSERT into part_usage
// 3. UPDATE parts SET current_quantity_onboard -= 1
// 4. RETURN success
```

**Situation 7: CLOSING_WO**

```typescript
// User completes work
await supabase.rpc('close_work_order', {
  wo_id,
  completion_notes: "Replaced coolant pump seal. Pressure now stable at 2.8 bar. Tested for 2 hours.",
  actual_hours: 3.0
});

// BACKEND (ATOMIC):
// BEGIN;
//   1. UPDATE work_orders SET status = 'completed', completed_at = NOW()
//   2. UPDATE faults SET status = 'resolved' (if linked)
//   3. INSERT into audit_log
//   4. IF fault was recurring, UPDATE fault SET recurrence_count, add to handover
// COMMIT;

// Journey complete: Fault resolved, WO closed, parts consumed, audit trail complete
```

---

## CONCLUSION

This architecture defines **EXACTLY** how the backend adapts for **EVERY** situational state:

✅ **Which tables to query** for each state
✅ **Which buckets to access** for each state
✅ **Which actions are available** based on state + user role
✅ **How data flows** across related entities (faults → equipment → work orders → parts)
✅ **How nested actions work** (create WO from fault, commit receiving, etc.)
✅ **How multi-step journeys** are orchestrated (report → diagnose → create WO → execute → close)

**This is the foundation for implementing all 67+ micro-actions with dynamic, context-aware backend queries.**
