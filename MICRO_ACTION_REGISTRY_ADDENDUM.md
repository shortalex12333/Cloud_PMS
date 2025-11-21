# 📝 Micro-Action Registry Addendum - Missing EDIT Actions

**Version:** 1.1
**Date:** 2025-11-21
**Status:** HIGH PRIORITY ADDITIONS

---

## Executive Summary

**Gap Identified:** The original 57 micro-actions lacked comprehensive **EDIT** capabilities for existing records.

**Issue:** Users can CREATE and VIEW, but cannot easily EDIT existing data (work orders, equipment details, invoice amounts, etc.)

**Solution:** Add **10 high-priority EDIT actions** → **Total: 67 micro-actions**

---

## 10 HIGH PRIORITY ADDITIONS

### EDIT ACTIONS (Core Entity Modifications)

| action_name | label | cluster | card_type | side_effect_type | short_description |
|-------------|-------|---------|-----------|------------------|-------------------|
| **edit_work_order_details** | Edit Work Order | do_maintenance | work_order | mutation_heavy | Modify WO title, description, priority, due date, assigned crew |
| **edit_equipment_details** | Edit Equipment | manage_equipment | equipment | mutation_heavy | Update equipment info (serial, location, model, install date) |
| **edit_part_details** | Edit Part Info | control_inventory | part | mutation_light | Update part details (location, min/max levels, supplier) |
| **edit_purchase_details** | Edit Purchase | procure_suppliers | purchase | mutation_heavy | Modify PO items, quantities, supplier, delivery date |
| **edit_invoice_amount** | Edit Invoice Amount | procure_suppliers | purchase | mutation_heavy | Modify invoice total with required audit justification |
| **edit_fault_details** | Edit Fault | fix_something | fault | mutation_light | Update fault description, resolution notes, severity |
| **edit_note** | Edit Note | communicate_status | fault, work_order, equipment | mutation_light | Modify existing note content (with edit history) |
| **delete_item** | Delete Item | communicate_status | fault, work_order, part, purchase | mutation_heavy | Soft-delete item with audit trail (notes, photos, attachments) |

### APPROVAL & WORKFLOW ACTIONS

| action_name | label | cluster | card_type | side_effect_type | short_description |
|-------------|-------|---------|-----------|------------------|-------------------|
| **approve_work_order** | Approve Task | do_maintenance | work_order | mutation_heavy | HOD approval before WO execution (role-based) |

### MOBILE & EFFICIENCY ACTIONS

| action_name | label | cluster | card_type | side_effect_type | short_description |
|-------------|-------|---------|-----------|------------------|-------------------|
| **scan_equipment_barcode** | Scan Equipment | manage_equipment | equipment, smart_summary | read_only | QR/barcode lookup for equipment |

---

## Detailed Action Specifications

### 1. edit_work_order_details

**Purpose:** Allow users to modify work order information after creation

**Editable Fields:**
- title (text)
- description (textarea)
- priority (dropdown: low/medium/high/urgent)
- due_date (datepicker)
- assigned_to (crew selector)
- equipment_id (equipment selector - rare edit)

**Not Editable:**
- created_by
- created_at
- completed_at (use mark_work_order_complete)
- status (use mark_work_order_complete)

**Role Restrictions:**
- Crew: Can edit own WOs only
- HOD: Can edit all WOs

**Audit Requirements:**
- Log all changed fields: `{ field: "title", old: "Service engine", new: "Service main engine coolant" }`
- Capture timestamp and user_id
- Show edit history on WO card

**UI Pattern:**
- Click "Edit" button → Opens inline form with current values
- Save button: Calls `edit_work_order_details` action
- Cancel button: Reverts to display mode

**n8n Payload Example:**
```json
{
  "action_name": "edit_work_order_details",
  "work_order_id": "uuid-123",
  "changes": {
    "title": "Service main engine coolant system",
    "priority": "high",
    "due_date": "2025-11-25"
  },
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:30:00Z"
}
```

---

### 2. edit_equipment_details

**Purpose:** Update equipment information (location changes, serial corrections, model updates)

**Editable Fields:**
- name (text)
- model (text)
- serial_number (text)
- location (text: deck, room, zone)
- install_date (date)
- manufacturer (text)
- notes (textarea)

**Not Editable:**
- id
- created_at
- running_hours (updated automatically or via separate action)

**Role Restrictions:**
- Crew: View only
- HOD: Can edit all fields
- Management: Can edit all fields

**Audit Requirements:**
- Critical for asset tracking - log all changes
- Flag serial_number changes for verification
- Notify management if equipment relocated

**UI Pattern:**
- Click "Edit Details" on equipment card
- Inline edit form with validation (serial must be unique)
- Save → audit log → update display

**n8n Payload Example:**
```json
{
  "action_name": "edit_equipment_details",
  "equipment_id": "uuid-789",
  "changes": {
    "location": "Engine Room - Starboard",
    "serial_number": "CAT3512-2019-5678"
  },
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:35:00Z"
}
```

---

### 3. edit_part_details

**Purpose:** Update inventory part information (location, reorder levels, supplier)

**Editable Fields:**
- part_name (text)
- part_number (text)
- storage_location (text: deck, locker, bin, shelf)
- min_stock_level (number)
- max_stock_level (number)
- reorder_quantity (number)
- preferred_supplier (text)
- notes (textarea)

**Not Editable:**
- current_stock (use log_part_usage or receive_delivery)
- usage_history

**Role Restrictions:**
- Crew: View only
- HOD: Can edit all fields
- Management: Can edit all fields

**Audit Requirements:**
- Log changes to stock levels and reorder thresholds
- Flag supplier changes

**UI Pattern:**
- Click "Edit Part" on part card
- Form with validation (min <= max, reorder > 0)
- Save → update inventory system

**n8n Payload Example:**
```json
{
  "action_name": "edit_part_details",
  "part_id": "uuid-321",
  "changes": {
    "storage_location": "Deck 2 - Locker 5 - Shelf B",
    "min_stock_level": 3,
    "reorder_quantity": 10
  },
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:40:00Z"
}
```

---

### 4. edit_purchase_details

**Purpose:** Modify purchase order details before approval or after supplier changes

**Editable Fields:**
- items (line items array)
- quantities (numbers)
- supplier (dropdown/text)
- delivery_address (text)
- delivery_date (date)
- notes (textarea)

**Not Editable:**
- total_amount (calculated from items)
- created_by
- approved_by
- invoice_amount (use edit_invoice_amount)

**Role Restrictions:**
- Crew: Can edit draft POs only
- HOD: Can edit draft and submitted POs
- Management: Can edit any PO

**Audit Requirements:**
- Log all item changes (added/removed/qty changed)
- Flag major cost changes (>10% of original)

**UI Pattern:**
- Click "Edit Purchase" on purchase card
- Line item grid (add/remove/edit quantities)
- Save → recalculate total → update PO

**Conditions:**
- Cannot edit if status = delivered
- Cannot edit if status = approved (without re-approval)

**n8n Payload Example:**
```json
{
  "action_name": "edit_purchase_details",
  "purchase_id": "uuid-555",
  "changes": {
    "items": [
      {"part_id": "uuid-111", "quantity": 5, "unit_price": 45.00},
      {"part_id": "uuid-222", "quantity": 2, "unit_price": 120.00}
    ],
    "delivery_date": "2025-12-01"
  },
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:45:00Z"
}
```

---

### 5. edit_invoice_amount ⚠️ **HIGHLY AUDIT-SENSITIVE**

**Purpose:** Correct invoice amount discrepancies (requires justification)

**Editable Fields:**
- invoice_amount (number)
- reason (required textarea, min 20 chars)

**Not Editable:**
- original_amount (preserved for audit)

**Role Restrictions:**
- Crew: DENIED
- HOD: Can edit with required justification
- Management: Can edit with justification

**Audit Requirements:**
- **HIGH PRIORITY AUDIT FLAG**
- Log old amount, new amount, reason, timestamp, user
- Notify management if change > $500 or >10% of original
- Require second approval if change > $5,000

**UI Pattern:**
- Click invoice amount → Modal appears (not inline)
- Modal shows:
  - Original Amount: $1,250.00 (read-only, red background)
  - New Amount: [_______] (input)
  - Reason for Change: [__________] (required textarea)
  - [Cancel] [Confirm Change]
- Confirmation prompt: "This change will be logged and may require management approval."

**n8n Payload Example:**
```json
{
  "action_name": "edit_invoice_amount",
  "purchase_id": "uuid-555",
  "invoice_id": "uuid-666",
  "old_amount": 1250.00,
  "new_amount": 1320.00,
  "reason": "Corrected based on final supplier quote - shipping cost was underestimated",
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:50:00Z"
}
```

**Backend Logic:**
```javascript
// n8n workflow: "Action - Edit Invoice Amount"
if (Math.abs(new_amount - old_amount) > 500 ||
    Math.abs((new_amount - old_amount) / old_amount) > 0.1) {

  // Send notification to management
  sendEmail({
    to: management_email,
    subject: "Invoice Amount Changed - Requires Review",
    body: `Invoice ${invoice_id} amount changed from $${old_amount} to $${new_amount}
           Reason: ${reason}
           Changed by: ${user_name}
           Purchase Order: ${purchase_id}`
  });

  // Flag for review
  updatePurchase(purchase_id, { requires_review: true });
}

// Log to high-priority audit table
insertAuditLog({
  entity: 'invoice',
  entity_id: invoice_id,
  action: 'edit_invoice_amount',
  severity: 'high',
  old_value: old_amount,
  new_value: new_amount,
  reason: reason,
  user_id: user_id,
  timestamp: timestamp
});
```

---

### 6. edit_fault_details

**Purpose:** Update fault description, add resolution notes, change severity

**Editable Fields:**
- description (textarea)
- resolution_notes (textarea)
- severity (dropdown: minor/medium/critical)

**Not Editable:**
- fault_code (immutable - defines the fault)
- equipment_id
- timestamp_occurred

**Role Restrictions:**
- All crew: Can edit

**Audit Requirements:**
- Log description changes
- Flag severity escalations (minor → critical)

**UI Pattern:**
- Click "Edit" on fault card
- Inline edit form
- Save → update fault record

**n8n Payload Example:**
```json
{
  "action_name": "edit_fault_details",
  "fault_id": "uuid-777",
  "changes": {
    "description": "Engine coolant temperature alarm - sensor reading 95°C at idle",
    "severity": "medium"
  },
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T15:55:00Z"
}
```

---

### 7. edit_note

**Purpose:** Allow users to correct or update existing notes (typos, clarifications)

**Editable Fields:**
- note_text (textarea)

**Not Editable:**
- created_by
- created_at
- linked_entity (fault/WO/equipment)

**Role Restrictions:**
- Own notes: Can edit
- Others' notes: Cannot edit (except HOD/Management)

**Audit Requirements:**
- Preserve edit history (show "Edited" badge)
- Log original text + new text

**UI Pattern:**
- Hover over note → "Edit" icon appears
- Click edit → Note becomes textarea
- Save → Update with "Edited" timestamp

**n8n Payload Example:**
```json
{
  "action_name": "edit_note",
  "note_id": "uuid-888",
  "old_text": "Replaced coolant sensor",
  "new_text": "Replaced coolant sensor - Part #CAT-CS-2019",
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T16:00:00Z"
}
```

---

### 8. delete_item

**Purpose:** Soft-delete items (notes, photos, attachments) with audit trail

**Deletable Items:**
- Notes (fault notes, WO notes, equipment notes)
- Photos (attachments)
- Draft work orders (not completed)
- Draft handover items

**NOT Deletable:**
- Completed work orders (archive only)
- Faults (archive only)
- Equipment records (archive only)
- Approved purchases (cancel only)

**Role Restrictions:**
- Own items: Can delete (with confirmation)
- Others' items: HOD/Management only

**Audit Requirements:**
- **Soft delete** - mark deleted=true, preserve data
- Log: item_type, item_id, deleted_by, timestamp
- Allow "undo" within 5 minutes

**UI Pattern:**
- Hover over item → "Delete" icon (trash can)
- Click → Confirmation: "Delete this note? (Can be undone within 5 min)"
- [Cancel] [Delete]
- Show "Undo" toast notification for 5 minutes

**n8n Payload Example:**
```json
{
  "action_name": "delete_item",
  "item_type": "note",
  "item_id": "uuid-999",
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T16:05:00Z"
}
```

**Backend Logic:**
```sql
-- Soft delete (preserve data)
UPDATE notes
SET deleted = true,
    deleted_by = 'uuid-456',
    deleted_at = NOW()
WHERE id = 'uuid-999';

-- Audit log
INSERT INTO audit_log (action, entity_type, entity_id, user_id, timestamp)
VALUES ('delete_item', 'note', 'uuid-999', 'uuid-456', NOW());
```

---

### 9. approve_work_order

**Purpose:** HOD approval before work order execution (some yachts require sign-off)

**When Required:**
- High-priority WOs
- WOs requiring parts >$1,000
- WOs involving contractors
- Safety-critical work

**Role Restrictions:**
- Crew: Cannot approve
- HOD/Chief: Can approve
- Management: Can approve

**Audit Requirements:**
- Log approval timestamp, approver
- Cannot mark complete until approved (if approval required)

**UI Pattern:**
- WO card shows "Pending Approval" badge
- HOD sees "Approve" button
- Click → Confirmation: "Approve this work order?"
- [Reject] [Approve]

**n8n Payload Example:**
```json
{
  "action_name": "approve_work_order",
  "work_order_id": "uuid-123",
  "approved": true,
  "approver_notes": "Approved - parts in stock, schedule for tomorrow",
  "user_id": "uuid-HOD",
  "timestamp": "2025-11-21T16:10:00Z"
}
```

---

### 10. scan_equipment_barcode

**Purpose:** Quick equipment lookup via QR/barcode (mobile efficiency)

**Use Cases:**
- Scan equipment QR → View equipment card
- Scan during rounds → Quick note/photo
- Scan for work order creation

**Role Restrictions:**
- All crew: Can scan

**Audit Requirements:**
- None (read-only action)

**UI Pattern:**
- Mobile app: Camera icon → Scan QR code
- Successful scan → Equipment card appears
- Failed scan → "Equipment not found" + manual search

**n8n Payload Example:**
```json
{
  "action_name": "scan_equipment_barcode",
  "barcode_value": "EQ-CAT3512-001",
  "user_id": "uuid-456",
  "timestamp": "2025-11-21T16:15:00Z"
}
```

**Backend Response:**
```json
{
  "success": true,
  "equipment_id": "uuid-789",
  "equipment_name": "CAT 3512 Main Engine #1",
  "card_type": "equipment"
}
```

---

## Updated Micro-Action Count

### Original Registry: 57 actions

### Additions: +10 actions

### **New Total: 67 micro-actions**

---

## Distribution After Additions

| Cluster | Original | Added | New Total | % of Total |
|---------|----------|-------|-----------|------------|
| fix_something | 7 | +1 (edit_fault_details) | 8 | 12% |
| do_maintenance | 8 | +2 (edit_work_order_details, approve_work_order) | 10 | 15% |
| manage_equipment | 6 | +2 (edit_equipment_details, scan_equipment_barcode) | 8 | 12% |
| control_inventory | 7 | +1 (edit_part_details) | 8 | 12% |
| communicate_status | 9 | +2 (edit_note, delete_item) | 11 | 16% |
| comply_audit | 5 | 0 | 5 | 7% |
| procure_suppliers | 7 | +2 (edit_purchase_details, edit_invoice_amount) | 9 | 13% |
| **TOTAL** | **57** | **+10** | **67** | **100%** |

---

## Side Effect Distribution After Additions

| Type | Original | Added | New Total | % |
|------|----------|-------|-----------|---|
| read_only | 28 | +1 | 29 | 43% |
| mutation_light | 20 | +3 | 23 | 34% |
| mutation_heavy | 9 | +6 | 15 | 22% |

**Analysis:** Edit actions are primarily `mutation_heavy` (require confirmation/audit), which is appropriate for data integrity.

---

## Next Steps

1. **Update MICRO_ACTION_REGISTRY.md** - Add 10 new actions to main registry
2. **Update ACTION_OFFERING_MAP.md** - Define when/where edit actions appear
3. **Update ACTION_OFFERING_RULES.md** - Add decision rules for edit intents
4. **Update MICRO_ACTIONS_VALIDATION.md** - Re-validate completeness

---

## Implementation Priority

### Phase 1 (Critical - Implement First)
1. ✅ edit_work_order_details
2. ✅ edit_equipment_details
3. ✅ edit_invoice_amount
4. ✅ delete_item

### Phase 2 (Important - Implement Soon)
5. ✅ edit_purchase_details
6. ✅ edit_part_details
7. ✅ approve_work_order

### Phase 3 (Nice to Have - Implement Later)
8. ✅ edit_fault_details
9. ✅ edit_note
10. ✅ scan_equipment_barcode

---

**This addendum addresses the gap identified: Users can now EDIT existing database values with proper audit trails.**
