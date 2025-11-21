# Phase 4 Progress Tracker

**Last Updated:** 2025-11-21
**Branch:** `claude/read-repo-files-01TwqiaKXUk14frUXUPkVKTj`
**Overall Progress:** 5/15 modals complete (33%)

---

## Modal Components Status

### ✅ High-Priority CREATE Modals (4/4 Complete)

#### 1. ✅ ReportFaultModal
**Status:** COMPLETE
**File:** `frontend/src/components/modals/ReportFaultModal.tsx`
**Action:** `report_fault`
**Lines:** 350

**SQL Requirements:**
```sql
-- master-create-workflow.json
INSERT INTO faults (
  yacht_id, equipment_id, title, description,
  severity, status, deck, room, created_by, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.equipment_id}}',
  '{{$json.context.title}}',
  '{{$json.context.description}}',
  '{{$json.context.severity}}',
  'open',
  '{{$json.context.deck}}',
  '{{$json.context.room}}',
  '{{$json.user_id}}',
  NOW()
) RETURNING id, title, severity;

-- If create_work_order = true, also INSERT INTO work_orders
```

**n8n Workflow Node:** `master-create-workflow.json` → Switch case for `report_fault`
**Status:** ⚠️ SQL NOT YET ADDED

---

#### 2. ✅ AddPartModal
**Status:** COMPLETE
**File:** `frontend/src/components/modals/AddPartModal.tsx`
**Action:** `add_part`
**Lines:** 425

**SQL Requirements:**
```sql
-- master-create-workflow.json
INSERT INTO parts (
  yacht_id, part_name, part_number, stock_quantity,
  min_stock_level, location, deck, room, storage,
  unit_cost, supplier, category, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.part_name}}',
  '{{$json.context.part_number}}',
  {{$json.context.stock_quantity}},
  {{$json.context.min_stock_level}},
  '{{$json.context.location}}',
  '{{$json.context.deck}}',
  '{{$json.context.room}}',
  '{{$json.context.storage}}',
  {{$json.context.unit_cost}},
  '{{$json.context.supplier}}',
  '{{$json.context.category}}',
  NOW()
) RETURNING id, part_name, part_number;
```

**n8n Workflow Node:** `master-create-workflow.json` → Switch case for `add_part`
**Status:** ⚠️ SQL NOT YET ADDED

---

#### 3. ✅ OrderPartModal
**Status:** COMPLETE
**File:** `frontend/src/components/modals/OrderPartModal.tsx`
**Action:** `order_part`
**Lines:** 460

**SQL Requirements:**
```sql
-- master-create-workflow.json
INSERT INTO part_orders (
  yacht_id, part_id, quantity, supplier,
  expected_delivery, status, urgency, notes,
  ordered_by, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.part_id}}',
  {{$json.context.quantity}},
  '{{$json.context.supplier}}',
  '{{$json.context.expected_delivery}}',
  'pending',
  '{{$json.context.urgency}}',
  '{{$json.context.notes}}',
  '{{$json.user_id}}',
  NOW()
) RETURNING id, part_id, quantity, supplier;
```

**n8n Workflow Node:** `master-create-workflow.json` → Switch case for `order_part`
**Status:** ⚠️ SQL NOT YET ADDED

---

#### 4. ✅ LogPartUsageModal
**Status:** COMPLETE
**File:** `frontend/src/components/modals/LogPartUsageModal.tsx`
**Action:** `log_part_usage`
**Lines:** 440

**SQL Requirements:**
```sql
-- master-create-workflow.json
-- Step 1: Log the usage
INSERT INTO part_usage (
  yacht_id, part_id, work_order_id, quantity_used,
  notes, logged_by, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.part_id}}',
  '{{$json.context.work_order_id}}',
  {{$json.context.quantity_used}},
  '{{$json.context.notes}}',
  '{{$json.user_id}}',
  NOW()
) RETURNING id;

-- Step 2: Update stock quantity
UPDATE parts
SET stock_quantity = stock_quantity - {{$json.context.quantity_used}},
    updated_at = NOW()
WHERE id = '{{$json.context.part_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING stock_quantity, min_stock_level;

-- Step 3: Check if now low stock (trigger alert if needed)
SELECT CASE
  WHEN stock_quantity < min_stock_level THEN 'low_stock_alert'
  WHEN stock_quantity = 0 THEN 'out_of_stock_alert'
  ELSE 'ok'
END as stock_status
FROM parts WHERE id = '{{$json.context.part_id}}';
```

**n8n Workflow Node:** `master-create-workflow.json` → Switch case for `log_part_usage`
**Status:** ⚠️ SQL NOT YET ADDED

---

### ✅ Audit-Sensitive EDIT Modals (1/5 Complete)

#### 5. ✅ EditInvoiceAmountModal ⚠️ AUDIT-SENSITIVE
**Status:** COMPLETE
**File:** `frontend/src/components/modals/EditInvoiceAmountModal.tsx`
**Action:** `edit_invoice_amount`
**Lines:** 300

**SQL Requirements:**
```sql
-- master-update-workflow.json
-- Step 1: Update the invoice
UPDATE invoices
SET amount = {{$json.context.new_amount}},
    updated_at = NOW(),
    updated_by = '{{$json.user_id}}'
WHERE id = '{{$json.context.invoice_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING id, amount, purchase_id;

-- Step 2: Create audit log (HIGH severity)
INSERT INTO audit_logs (
  yacht_id, user_id, action, entity_type, entity_id,
  old_value, new_value, reason, severity, timestamp
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.user_id}}',
  'edit_invoice_amount',
  'invoice',
  '{{$json.context.invoice_id}}',
  {{$json.context.old_amount}},
  {{$json.context.new_amount}},
  '{{$json.context.reason}}',
  'HIGH',
  NOW()
) RETURNING id;

-- Step 3: Check if notification threshold exceeded
-- If |new - old| > 500 OR |(new-old)/old| > 0.1:
--   → Send email notification (next node)
```

**n8n Workflow Node:** `master-update-workflow.json` → Switch case for `edit_invoice_amount`
**Additional Node:** Email notification node (conditional)
**Status:** ⚠️ SQL NOT YET ADDED

---

#### 6. ❌ EditWorkOrderDetailsModal
**Status:** PENDING
**Action:** `edit_work_order_details`
**Estimated Lines:** 380

**SQL Requirements:**
```sql
-- master-update-workflow.json
UPDATE work_orders
SET title = COALESCE('{{$json.context.changes.title}}', title),
    description = COALESCE('{{$json.context.changes.description}}', description),
    priority = COALESCE('{{$json.context.changes.priority}}', priority),
    due_date = COALESCE('{{$json.context.changes.due_date}}', due_date),
    assigned_to = COALESCE('{{$json.context.changes.assigned_to}}', assigned_to),
    updated_at = NOW(),
    updated_by = '{{$json.user_id}}'
WHERE id = '{{$json.context.work_order_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING *;

-- Audit log (MEDIUM severity)
INSERT INTO audit_logs (...) VALUES (...);
```

**Features Needed:**
- Show change diff (old vs new)
- Validate: Can't change completed work orders
- Audit logging with MEDIUM severity
- Pre-fill all current values

---

#### 7. ❌ EditPartQuantityModal
**Status:** PENDING
**Action:** `edit_part_quantity`
**Estimated Lines:** 320

**SQL Requirements:**
```sql
-- master-update-workflow.json
UPDATE parts
SET stock_quantity = {{$json.context.new_quantity}},
    updated_at = NOW()
WHERE id = '{{$json.context.part_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING stock_quantity, min_stock_level;

-- Audit log (MEDIUM severity)
INSERT INTO audit_logs (
  yacht_id, user_id, action, entity_type, entity_id,
  old_value, new_value, reason, severity, timestamp
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.user_id}}',
  'edit_part_quantity',
  'part',
  '{{$json.context.part_id}}',
  {{$json.context.old_quantity}},
  {{$json.context.new_quantity}},
  '{{$json.context.adjustment_reason}}',
  'MEDIUM',
  NOW()
);
```

**Features Needed:**
- Show old quantity (read-only) vs new
- Adjustment types (addition, correction, write-off)
- Reason field (required)
- Low stock warning if new < min

---

#### 8. ❌ EditEquipmentDetailsModal
**Status:** PENDING
**Action:** `edit_equipment_details`
**Estimated Lines:** 400

**SQL Requirements:**
```sql
-- master-update-workflow.json
UPDATE equipment
SET name = COALESCE('{{$json.context.changes.name}}', name),
    model = COALESCE('{{$json.context.changes.model}}', model),
    serial_number = COALESCE('{{$json.context.changes.serial_number}}', serial_number),
    location = COALESCE('{{$json.context.changes.location}}', location),
    manufacturer = COALESCE('{{$json.context.changes.manufacturer}}', manufacturer),
    updated_at = NOW()
WHERE id = '{{$json.context.equipment_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING *;

-- Audit log (LOW severity, or HIGH if serial_number changed)
```

**Features Needed:**
- Highlight critical field changes (serial_number)
- Change diff display
- Audit logging with severity based on what changed

---

#### 9. ❌ EditFaultDetailsModal
**Status:** PENDING
**Action:** `edit_fault_details`
**Estimated Lines:** 350

**SQL Requirements:**
```sql
-- master-update-workflow.json
UPDATE faults
SET title = COALESCE('{{$json.context.changes.title}}', title),
    description = COALESCE('{{$json.context.changes.description}}', description),
    severity = COALESCE('{{$json.context.changes.severity}}', severity),
    status = COALESCE('{{$json.context.changes.status}}', status),
    updated_at = NOW()
WHERE id = '{{$json.context.fault_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING *;

-- Validation: If reopening closed fault, require reason
-- Audit log (MEDIUM severity)
```

**Features Needed:**
- Status change validation (can't reopen closed without reason)
- Change diff display
- Severity change warnings

---

### ❌ LINKING Selection Modals (0/3 Complete)

#### 10. ❌ AddToHandoverModal
**Status:** PENDING
**Action:** `add_to_handover`
**Estimated Lines:** 450

**SQL Requirements:**
```sql
-- master-linking-workflow.json
INSERT INTO handover_items (
  handover_id, source_type, source_id,
  summary, added_by, created_at
) VALUES (
  '{{$json.context.handover_id}}',
  '{{$json.context.source_type}}',
  '{{$json.context.source_id}}',
  '{{$json.context.summary}}',
  '{{$json.user_id}}',
  NOW()
) RETURNING id;
```

**Features Needed:**
- Entity type selector (fault/work_order/equipment/part/document)
- Search/filter entities by type
- Multi-select support
- Preview selected entities
- Add summary/notes

---

#### 11. ❌ LinkEquipmentToFaultModal
**Status:** PENDING
**Action:** `link_equipment_to_fault`
**Estimated Lines:** 320

**SQL Requirements:**
```sql
-- master-linking-workflow.json
UPDATE faults
SET equipment_id = '{{$json.context.equipment_id}}',
    updated_at = NOW()
WHERE id = '{{$json.context.fault_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING *;

-- Optional: Create work order if requested
```

**Features Needed:**
- Search equipment by name/location
- Equipment details preview
- Optional: Create work order checkbox

---

#### 12. ❌ LinkPartsToWorkOrderModal
**Status:** PENDING
**Action:** `link_parts_to_work_order`
**Estimated Lines:** 380

**SQL Requirements:**
```sql
-- master-linking-workflow.json
INSERT INTO work_order_parts (
  work_order_id, part_id, quantity_required,
  notes, created_at
) VALUES
-- Multiple inserts for each selected part
RETURNING *;

-- Optional: Reserve parts (decrease available_quantity)
```

**Features Needed:**
- Multi-select parts from inventory
- Shows stock levels for each
- Quantity input per part
- Optional: Reserve parts checkbox

---

### ❌ Additional CREATE Modals (0/1 Complete)

#### 13. ❌ CreatePurchaseRequestModal
**Status:** PENDING
**Action:** `create_purchase_request`
**Estimated Lines:** 480

**SQL Requirements:**
```sql
-- master-create-workflow.json
INSERT INTO purchase_requests (
  yacht_id, requested_by, justification,
  urgency, budget_code, status, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.user_id}}',
  '{{$json.context.justification}}',
  '{{$json.context.urgency}}',
  '{{$json.context.budget_code}}',
  'pending_approval',
  NOW()
) RETURNING id;

-- Then insert line items
INSERT INTO purchase_request_items (...) VALUES (...);
```

**Features Needed:**
- Multi-line item support (parts/equipment)
- Budget code selection
- Urgency levels
- Justification text area
- Estimated total cost calculation

---

### ❌ Specialized Modals (0/1 Complete)

#### 14. ❌ DiagnoseFaultModal (RAG-powered)
**Status:** PENDING - Advanced (Phase 5?)
**Action:** `diagnose_fault`
**Estimated Lines:** 550

**SQL Requirements:**
```sql
-- master-rag-workflow.json
-- Step 1: Retrieve fault details
SELECT * FROM faults WHERE id = '{{$json.context.fault_id}}';

-- Step 2: Vector search for similar faults
SELECT * FROM fault_embeddings
WHERE yacht_id = '{{$json.yacht_id}}'
ORDER BY embedding <-> '{{embedding_vector}}'
LIMIT 5;

-- Step 3: Retrieve equipment manuals
SELECT * FROM documents WHERE equipment_id = ...;

-- Step 4: Send to AI for diagnosis (OpenAI/Claude)
-- Step 5: Stream response back
```

**Features Needed:**
- AI streaming response
- Show similar past faults
- Manual section references
- Suggested parts
- Create work order from diagnosis

---

## Summary Statistics

### Modal Progress
- **Total Modals Planned:** 15
- **Completed:** 5 (33%)
- **In Progress:** 0
- **Pending:** 10 (67%)

### By Category
| Category | Complete | Pending | Total |
|----------|----------|---------|-------|
| CREATE (High-Priority) | 4 | 1 | 5 |
| EDIT (Audit-Sensitive) | 1 | 4 | 5 |
| LINKING | 0 | 3 | 3 |
| RAG/Advanced | 0 | 1 | 1 |

### n8n Workflow Status
| Workflow | Modals Using | SQL Added | Status |
|----------|--------------|-----------|--------|
| master-create-workflow.json | 5 | 0/5 | ❌ Empty |
| master-update-workflow.json | 5 | 0/5 | ❌ Empty |
| master-linking-workflow.json | 3 | 0/3 | ❌ Empty |
| master-rag-workflow.json | 1 | 0/1 | ❌ Empty |

---

## Next Steps

### Immediate (Build Remaining Modals)
1. ❌ EditWorkOrderDetailsModal
2. ❌ EditPartQuantityModal
3. ❌ EditEquipmentDetailsModal
4. ❌ EditFaultDetailsModal
5. ❌ AddToHandoverModal

### After Modals Complete
1. Expand n8n workflows with SQL logic for all 13 actions
2. Add audit logging to UPDATE workflow
3. Add email notification node for threshold edits
4. Build specialized hooks (useFaultActions, useInventoryActions)
5. End-to-end testing

---

## Notes

- All modals follow consistent pattern (react-hook-form + Zod)
- Audit-sensitive modals require reason field (min 15 chars)
- High-value edits (invoice >$500 or >10%) trigger notifications
- Stock operations check availability and warn on low stock
- All SQL uses RLS (yacht_id filtering) for multi-tenancy

**Last Commit:** `479d2c3` - "[Phase 4 Start] Add 5 high-priority modal components"
